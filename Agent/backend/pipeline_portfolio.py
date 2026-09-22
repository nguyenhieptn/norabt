"""Orchestrate one portfolio run: N bots through the normal vertical, then the
portfolio layer on top.

WHY THIS IS A SEPARATE PIPELINE. `RiskSupervisionPipeline.run()` is one bot's
whole vertical, and it already accepts `portfolio_bots` -- but that argument
is a chicken and egg: it needs every OTHER bot's `BotResult`, which does not
exist until each of them has been run. Doing this inside `run()` would mean
one bot's call fetching the other bots, which is exactly the coupling the
single-bot pipeline is kept free of.

So the order here is: run each member normally, THEN re-score each member's
QC with the full member list in hand. The second pass is pure computation --
`QCCoreService.assess_bot` reads only the `MarketResult` and `BotResult` this
process already holds, with no network and no OKX call -- and only the
`portfolio_risk` lens can change, because it is the only one that takes
`portfolio_bots` at all. Everything else about each member's assessment is
bit-identical to what the single-bot path produces.

HISTORY. The inner pipeline is run with `persist_history=False` and this class
appends the re-scored assessment instead. That is not an optimisation, it is
required: `assessment_id` digests only the market and the bot (see
`RiskFusionEngine.fuse`), so the first-pass and second-pass assessments share
an id, and `AssessmentHistoryStore.append` deduplicates on exactly that id. If
the first pass were allowed to write, the stored assessment would permanently
be the one with the EMPTY portfolio context, and the re-scored one would be
silently dropped.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

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
from Agent.backend.report.qc.service import QCCoreService

logger = logging.getLogger(__name__)


class PortfolioBotRequest(BaseModel):
    """One member to analyse, addressed the same way `RiskSupervisionPipeline`
    addresses a bot: by asset folder and bot folder, not by uniqueCode.

    Resolving a uniqueCode to this pair is the web layer's job (it already
    does it for the single-bot path), which keeps this pipeline usable from
    the CLI against on-disk fixtures with no lookup involved.
    """

    asset: str
    bot_folder_name: str
    venue_type: str = "CEX"


class PortfolioMemberFailure(BaseModel):
    """A member that could not be analysed, kept rather than dropped.

    A portfolio silently analysed as two bots when the user asked for three is
    a wrong answer, not a partial one.
    """

    asset: str
    bot_folder_name: str
    error: str


class PortfolioSupervisionResult(BaseModel):
    members: List[RiskSupervisionResult] = Field(default_factory=list)
    failures: List[PortfolioMemberFailure] = Field(default_factory=list)
    # `None` when fewer than two members survived: there is no portfolio to
    # assess, and a one-member "portfolio" assessment would be a per-bot
    # report wearing the wrong schema.
    portfolio_assessment: Optional[PortfolioRiskAssessment] = None
    portfolio_unavailable_reason: Optional[str] = None


class PortfolioSupervisionPipeline:
    # Members run concurrently because each one is dominated by OKX round
    # trips. The bound is deliberate: `resolve_planned_markets` already fans
    # out inside each member, so an unbounded pool here would multiply into
    # the shared OKX throttle rather than going faster.
    DEFAULT_MAX_WORKERS = 4

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
        # Enforced, not assumed, even on an injected pipeline -- see this
        # module's docstring for why a first-pass write is not recoverable.
        self.pipeline.persist_history = False
        self.history = history or self.pipeline.history
        self.portfolio_history = portfolio_history or PortfolioHistoryStore()
        self.persist_history = persist_history
        self.max_workers = max_workers or self.DEFAULT_MAX_WORKERS

    # ------------------------------------------------------------------ #

    def run(
        self,
        requests: Sequence[PortfolioBotRequest],
        seed: int = 42,
        as_of_ms: Optional[int] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: int = 500,
        portfolio_iterations: int = JointMonteCarloEngine.DEFAULT_ITERATIONS,
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

        _notify("members")
        results: List[Optional[RiskSupervisionResult]] = [None] * len(requests)
        failures: List[PortfolioMemberFailure] = []

        def _one(index: int) -> None:
            request = requests[index]
            try:
                results[index] = self.pipeline.run(
                    request.asset,
                    request.bot_folder_name,
                    venue_type=request.venue_type,
                    seed=seed,
                    as_of_ms=as_of_ms,
                    simulation_iterations=simulation_iterations,
                    simulation_horizon=simulation_horizon,
                )
            except Exception as exc:  # noqa: BLE001
                # One unreachable bot must not take the other members' work
                # with it; the caller is told exactly which one failed and why.
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

        workers = max(1, min(self.max_workers, len(requests)))
        if workers == 1:
            for index in range(len(requests)):
                _one(index)
        else:
            with ThreadPoolExecutor(
                max_workers=workers, thread_name_prefix="norabt-portfolio-member"
            ) as pool:
                list(pool.map(_one, range(len(requests))))

        survivors = [result for result in results if result is not None]
        return self.assemble(
            survivors,
            failures=failures,
            portfolio_iterations=portfolio_iterations,
            seed=seed,
            as_of_ms=as_of_ms,
            progress=_notify,
        )

    # ------------------------------------------------------------------ #

    def assemble(
        self,
        results: Sequence[RiskSupervisionResult],
        failures: Optional[Sequence[PortfolioMemberFailure]] = None,
        portfolio_iterations: int = JointMonteCarloEngine.DEFAULT_ITERATIONS,
        seed: Optional[int] = 42,
        as_of_ms: Optional[int] = None,
        progress: Optional[Callable[[str], None]] = None,
    ) -> PortfolioSupervisionResult:
        """Cross-score already-run members, then assess them as a portfolio.

        Split out from `run()` so the web layer can reuse it: that path builds
        each `RiskSupervisionResult` through its own live wiring (a scratch
        data_dir per uniqueCode, see `web/data.py`) and has nothing to gain
        from this class re-running them.
        """
        failures = list(failures or [])

        def _notify(stage: str) -> None:
            if progress is not None:
                progress(stage)

        # De-duplicate by uniqueCode. The same bot reached through two folders
        # is one position, and counting it twice would manufacture a perfect
        # correlation that says nothing about the portfolio.
        unique: Dict[str, RiskSupervisionResult] = {}
        duplicates: List[str] = []
        for result in results:
            code = result.bot_result.identity.unique_code
            if code in unique:
                duplicates.append(code)
                continue
            unique[code] = result
        members = list(unique.values())

        if len(members) < 2:
            return PortfolioSupervisionResult(
                members=members,
                failures=failures,
                portfolio_unavailable_reason=(
                    f"Only {len(members)} of {len(members) + len(failures)} bots "
                    "could be analysed; a portfolio needs at least two"
                ),
            )

        _notify("cross_scoring")
        bots = [result.bot_result for result in members]
        rescored: List[RiskSupervisionResult] = []
        for result in members:
            assessment = QCCoreService.assess_bot(
                result.market_result,
                result.bot_result,
                previous_assessment=self.history.latest(
                    result.bot_result.identity.bot_id
                ),
                portfolio_bots=bots,
            )
            if self.persist_history:
                self.history.append(assessment)
            rescored.append(result.model_copy(update={"risk_assessment": assessment}))

        _notify("correlation")
        portfolio = PortfolioQCService.assess_portfolio(
            [
                PortfolioCandidate(
                    bot=result.bot_result, assessment=result.risk_assessment
                )
                for result in rescored
            ],
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
                f"[{failure.bot_folder_name}] could not be analysed and is missing "
                f"from every figure below: {failure.error}"
            )

        if self.persist_history:
            self.portfolio_history.append(portfolio)

        _notify("decision")
        return PortfolioSupervisionResult(
            members=rescored,
            failures=failures,
            portfolio_assessment=portfolio,
        )
