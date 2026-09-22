"""One portfolio run -> ONE report, the same shape a single bot produces.

THE SHAPE, AND WHY IT IS THIS ONE. Analysing three bots does not mean three
reports side by side. The owner of those three bots holds one account, and the
questions they ask -- what is my drawdown, how fat is the loss tail, is the
leverage sane, was the record earned in one regime -- are questions about that
one account. So this pipeline merges the members' ledgers into a single
synthetic bot (`bot.mcp.aggregate.PortfolioAggregator`), pushes it through the
ordinary vertical (`RiskSupervisionPipeline.assess_prepared`), and returns an
ordinary `RiskSupervisionResult`. Every existing reader of that type -- the
three report tabs included -- renders a portfolio with no changes at all.

The one thing a single-bot report cannot contain is attached alongside it:
whether the members move together, whether they trade the same way, and what
their co-movement costs the combined loss tail. That is
`PortfolioRiskAssessment`, and it deliberately carries no risk score of its
own -- the score is the combined assessment's, produced by the same ten lenses
as any bot's. Two scores for one portfolio would be two answers to one
question.

WHAT IS DELIBERATELY NOT PRODUCED. Per-member reports. The members' own
`BotResult`s are fetched (they are the raw material) and their observational
facts appear in the diversification section's member table, but no per-member
market resolution, QC pass or control decision is run. That work would produce
N reports nobody asked for, and would cost N market-coverage fan-outs against
the OKX throttle to do it.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from Agent.backend.bot.mcp.aggregate import PortfolioAggregator
from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.bot.mcp.service import BotObservationService
from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.pipeline import RiskSupervisionPipeline, RiskSupervisionResult
from Agent.backend.report.qc.history.portfolio_store import PortfolioHistoryStore
from Agent.backend.report.qc.history.store import AssessmentHistoryStore
from Agent.backend.report.qc.portfolio.joint_monte_carlo import JointMonteCarloEngine
from Agent.backend.report.qc.portfolio.schemas import PortfolioRiskAssessment
from Agent.backend.report.qc.portfolio.service import (
    PortfolioCandidate,
    PortfolioQCService,
)
from Agent.backend.bot.mcp.analytics.strategy.profile import base_symbol

logger = logging.getLogger(__name__)


class PortfolioBotRequest(BaseModel):
    """One member, addressed the way `RiskSupervisionPipeline` addresses a bot.

    Resolving a uniqueCode to an (asset, folder) pair is the web layer's job,
    which keeps this pipeline runnable from the CLI against on-disk fixtures
    with no lookup involved.
    """

    asset: str
    bot_folder_name: str
    venue_type: str = "CEX"


class PortfolioMemberFailure(BaseModel):
    """A member that could not be read, kept rather than dropped.

    A portfolio silently built from two bots when three were asked for is a
    wrong answer, not a partial one.
    """

    asset: str
    bot_folder_name: str
    error: str


class PortfolioSupervisionResult(BaseModel):
    # The report. An ordinary single-bot result whose subject is the merged
    # book -- this is what the renderer and its three tabs consume.
    combined: Optional[RiskSupervisionResult] = None
    # The section only a set of bots can have. Attached to, never instead of,
    # the report above.
    portfolio: Optional[PortfolioRiskAssessment] = None
    failures: List[PortfolioMemberFailure] = Field(default_factory=list)
    # Set only when no report could be produced at all.
    unavailable_reason: Optional[str] = None


class PortfolioSupervisionPipeline:
    # Members are read concurrently because each is dominated by OKX round
    # trips. Bounded on purpose: the combined bot's market coverage already
    # fans out later, and an unbounded pool here would multiply into the
    # shared OKX throttle rather than going faster.
    DEFAULT_MAX_WORKERS = 4
    # Members are read at FULL simulation quality even though this pipeline
    # never looks at their own `simulation_results` -- the portfolio's
    # simulation runs over the MERGED ledger in `PortfolioAggregator`, and the
    # cross-bot one over aligned buckets in `JointMonteCarloEngine`.
    #
    # Skipping it looked like the obvious saving and is not: measured on three
    # real members with the phase cache warm, a full 10k-run bootstrap costs
    # 3.68s per bot against 3.02s with the simulation stubbed out, because the
    # ledger fetch and analysis dominate. What the 0.66s buys is that a member
    # `BotResult` is INTERCHANGEABLE with one produced by the single-bot path,
    # so one cache can serve both directions. A stubbed-out member cached and
    # later served to a single-bot report would hand a reader a p_ruin and a
    # VaR computed from one iteration, and nothing in the payload would say so
    # -- a silent wrong number, bought for two thirds of a second.
    MEMBER_SIMULATION_ITERATIONS = 10_000
    MEMBER_SIMULATION_HORIZON = 500

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        pipeline: Optional[RiskSupervisionPipeline] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        history: Optional[AssessmentHistoryStore] = None,
        portfolio_history: Optional[PortfolioHistoryStore] = None,
        persist_history: bool = True,
        max_workers: Optional[int] = None,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.pipeline = pipeline or RiskSupervisionPipeline(
            data_dir=self.data_dir,
            evaluation_mode=evaluation_mode,
            history=history,
            persist_history=False,
        )
        # This class owns the decision to persist, because it is the one that
        # knows whether the assessment it is holding is the final one.
        self.pipeline.persist_history = False
        self.history = history or self.pipeline.history
        self.portfolio_history = portfolio_history or PortfolioHistoryStore()
        self.persist_history = persist_history
        self.max_workers = max_workers or self.DEFAULT_MAX_WORKERS

    @property
    def bot_service(self) -> BotObservationService:
        return self.pipeline.bot_service

    # ------------------------------------------------------------------ #

    def fetch_members(
        self,
        requests: Sequence[PortfolioBotRequest],
        seed: int = 42,
        as_of_ms: Optional[int] = None,
        simulation_iterations: Optional[int] = None,
        prefetched: Optional[Dict[str, BotResult]] = None,
    ) -> tuple[List[BotResult], List[PortfolioMemberFailure]]:
        """Read every member's ledger. Nothing is scored at this stage.

        `prefetched` maps `bot_folder_name` to a `BotResult` the caller
        already holds -- typically because that bot was analysed on its own
        minutes ago and the web layer still has it. A supplied member is used
        as-is and never re-fetched, which is the difference between a
        portfolio of already-seen bots costing one OKX round trip each and
        costing none. The caller owns the freshness decision: this pipeline
        cannot know how old the object it was handed is, so it does not
        second-guess it.
        """
        iterations = (
            simulation_iterations
            if simulation_iterations is not None
            else self.MEMBER_SIMULATION_ITERATIONS
        )
        supplied = prefetched or {}
        results: List[Optional[BotResult]] = [None] * len(requests)
        failures: List[PortfolioMemberFailure] = []

        def _one(index: int) -> None:
            request = requests[index]
            reused = supplied.get(request.bot_folder_name)
            if reused is not None:
                results[index] = reused
                return
            try:
                results[index] = self.bot_service.get_bot_result(
                    request.asset,
                    request.bot_folder_name,
                    seed=seed,
                    venue_type=request.venue_type,
                    as_of_ms=as_of_ms,
                    simulation_iterations=iterations,
                    simulation_horizon=(
                        1 if iterations <= 1 else self.MEMBER_SIMULATION_HORIZON
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                # One unreachable member must not take the others' work with
                # it; the caller is told exactly which one failed and why.
                logger.warning(
                    "PortfolioSupervisionPipeline: member %s/%s failed: %s",
                    request.asset,
                    request.bot_folder_name,
                    exc,
                )
                failures.append(
                    PortfolioMemberFailure(
                        asset=request.asset,
                        bot_folder_name=request.bot_folder_name,
                        error=str(exc),
                    )
                )

        # Only the members that actually have to be read decide the pool size.
        # Spinning up four threads to hand back four cached objects is pure
        # overhead, and the common case after a few single-bot views is that
        # every member is already in hand.
        to_fetch = [
            index
            for index, request in enumerate(requests)
            if request.bot_folder_name not in supplied
        ]
        for index, request in enumerate(requests):
            if request.bot_folder_name in supplied:
                _one(index)
        workers = max(1, min(self.max_workers, len(to_fetch) or 1))
        if workers == 1:
            for index in to_fetch:
                _one(index)
        elif to_fetch:
            with ThreadPoolExecutor(
                max_workers=workers, thread_name_prefix="norabt-portfolio-member"
            ) as pool:
                list(pool.map(_one, to_fetch))
        return [item for item in results if item is not None], failures

    # ------------------------------------------------------------------ #

    def run(
        self,
        requests: Sequence[PortfolioBotRequest],
        seed: int = 42,
        as_of_ms: Optional[int] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: Optional[int] = None,
        portfolio_iterations: int = JointMonteCarloEngine.DEFAULT_ITERATIONS,
        nick_name: Optional[str] = None,
        progress: Optional[Callable[[str], None]] = None,
    ) -> PortfolioSupervisionResult:
        if len(requests) < 2:
            raise ValueError(
                "A portfolio run needs at least two bots; use "
                "RiskSupervisionPipeline for one"
            )

        def _notify(stage: str) -> None:
            if progress is None:
                return
            try:
                progress(stage)
            except Exception:  # noqa: BLE001 - same contract as the single-bot pipeline
                logger.exception(
                    "PortfolioSupervisionPipeline: progress callback failed at "
                    "stage %r -- ignoring",
                    stage,
                )

        _notify("ledger")
        bots, failures = self.fetch_members(requests, seed=seed, as_of_ms=as_of_ms)
        return self.assemble(
            bots,
            failures=failures,
            simulation_iterations=simulation_iterations,
            simulation_horizon=simulation_horizon,
            portfolio_iterations=portfolio_iterations,
            nick_name=nick_name,
            seed=seed,
            as_of_ms=as_of_ms,
            notify=_notify,
        )

    # ------------------------------------------------------------------ #

    def assemble(
        self,
        bots: Sequence[BotResult],
        failures: Optional[Sequence[PortfolioMemberFailure]] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: Optional[int] = None,
        portfolio_iterations: int = JointMonteCarloEngine.DEFAULT_ITERATIONS,
        nick_name: Optional[str] = None,
        seed: int = 42,
        as_of_ms: Optional[int] = None,
        notify: Optional[Callable[[str], None]] = None,
    ) -> PortfolioSupervisionResult:
        """Merge, score once, and describe the diversification.

        Split out of `run()` so the web layer can reuse it: that path builds
        each member's `BotResult` through its own live wiring (a scratch
        data_dir per uniqueCode, see `web/data.py`) and has nothing to gain
        from this class re-reading them.
        """
        failures = list(failures or [])

        def _notify(stage: str) -> None:
            if notify is not None:
                notify(stage)

        # De-duplicate by uniqueCode. The same bot reached through two folders
        # is one position, and counting it twice would both double its weight
        # in every merged figure and manufacture a perfect correlation.
        unique: Dict[str, BotResult] = {}
        duplicates: List[str] = []
        for bot in bots:
            code = bot.identity.unique_code
            if code in unique:
                duplicates.append(code)
                continue
            unique[code] = bot
        members = list(unique.values())

        if len(members) < 2:
            return PortfolioSupervisionResult(
                failures=failures,
                unavailable_reason=(
                    f"Only {len(members)} of {len(members) + len(failures)} bots "
                    "could be read; a portfolio needs at least two"
                ),
            )

        _notify("merge")
        timelines = self.bot_service.phase_timelines(
            {
                base_symbol(trade.symbol)
                for bot in members
                for trade in bot.trade_ledger_summary
                if trade.symbol
            }
        )
        try:
            combined_bot = PortfolioAggregator.combine(
                members,
                timelines=timelines,
                nick_name=nick_name,
                simulation_iterations=simulation_iterations,
                simulation_horizon=simulation_horizon,
                seed=seed,
            )
        except ValueError as exc:
            return PortfolioSupervisionResult(
                failures=failures,
                unavailable_reason=f"The members could not be merged: {exc}",
            )

        # From here the combined bot walks the ordinary vertical, so the
        # portfolio is scored by exactly the rules a single bot is scored by.
        _notify("markets")
        combined = self.pipeline.assess_prepared(
            combined_bot,
            as_of_ms=as_of_ms,
            previous_assessment=self.history.latest(combined_bot.identity.bot_id),
            # The portfolio-risk lens asks how concentrated and how one-sided
            # the book is ACROSS bots -- the one lens whose whole input is the
            # member list. Withholding it here would leave the portfolio's own
            # report with that dimension UNKNOWN, which is the one report where
            # it is answerable.
            portfolio_bots=members,
            notify=_notify,
        )
        if self.persist_history:
            self.history.append(combined.risk_assessment)

        _notify("correlation")
        portfolio = PortfolioQCService.assess_portfolio(
            [PortfolioCandidate(bot=bot) for bot in members],
            combined=combined.risk_assessment,
            iterations=portfolio_iterations,
            seed=seed,
            as_of_ms=as_of_ms,
        )
        if duplicates:
            portfolio.warnings.append(
                "The same bot was submitted more than once and counted once: "
                + ", ".join(sorted(set(duplicates)))
            )
        for failure in failures:
            portfolio.warnings.append(
                f"[{failure.bot_folder_name}] could not be read and is missing from "
                f"every figure in this report: {failure.error}"
            )
        if self.persist_history:
            self.portfolio_history.append(portfolio)

        return PortfolioSupervisionResult(
            combined=combined,
            portfolio=portfolio,
            failures=failures,
        )
