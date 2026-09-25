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
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from Agent.backend.bot.mcp.aggregate import PortfolioAggregator
from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.bot.mcp.service import BotObservationService
from Agent.backend.external.sources.bot_source import LedgerUnavailableError
from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.pipeline import RiskSupervisionPipeline, RiskSupervisionResult
from Agent.backend.report.qc.history.portfolio_store import PortfolioHistoryStore
from Agent.backend.report.qc.history.store import AssessmentHistoryStore
from Agent.backend.report.qc.portfolio.joint_monte_carlo import JointMonteCarloEngine
from Agent.backend.report.qc.portfolio.public_series import (
    PublicPnlProfile,
    parse_public_profile,
)
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
    # Why it could not be read, and the reason this field exists is that the
    # two values are not interchangeable.
    #
    # CONCEALED means the trader will not publish an order book (OKX 60004).
    # The single-bot path has always treated that as a finding about the bot
    # rather than an accident -- Agent/backend/bot/analysis/limited.py scores
    # every dimension the concealment costs as an ELEVATED risk contributor,
    # explicitly so that hiding a ledger can never read as "no evidence
    # either way". Dropping such a member from a portfolio quietly does the
    # opposite of that rule, and worse than it would in a single report: the
    # remaining members are all disclosers, so the portfolio's diversification
    # and joint-risk numbers come out looking BETTER for the presence of a bot
    # nobody can see into.
    #
    # ERROR means the read itself went wrong -- OKX unreachable, a corrupt
    # file, a timeout. That says nothing about the bot and must not be scored
    # against it; it is a defect in the run, to be retried.
    kind: Literal["concealed", "error"] = "error"
    # Best-effort AUM for a CONCEALED member, in USDT -- from
    # `LedgerUnavailableError.profile["aum"]`, the one figure OKX still
    # publishes for a bot that hides its order book (leaderboard/public-stats
    # survive 60004; only the ledger endpoints are blocked). `None` when even
    # that did not survive (the NOT_FOUND branch, or profile without an aum
    # field), which is common and must not be treated as "zero capital" --
    # `assess_portfolio` falls back to a per-bot COUNT ratio whenever this is
    # missing for any concealed member, precisely so a bot with unknown
    # capital cannot be silently weighted as if it held none.
    approx_capital_usdt: Optional[float] = None


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
    # trips and by reading candle files -- both are waits, not computation,
    # so threads help even on the two CPUs this container is given.
    #
    # Four, and NOT the six this project uses for its other parallel I/O
    # (`_PHASE_TIMELINE_MAX_WORKERS`, `MAX_MARKET_RESOLVE_WORKERS`). Six was
    # set here by analogy with those, and measuring it showed the analogy is
    # wrong: past four, members stop being pure waiting and start contending
    # for the same two CPUs this container is given, so the curve turns back
    # down. Median of three cold runs over six real members:
    #
    #   workers    1      2      3      4      6      8
    #   6 members  9.47   7.23   6.63   6.89   7.73   7.52
    #   3 members  5.54   5.04   4.36   4.45   4.26   4.26
    #
    # Six is not merely no better at the size that matters, it is a
    # regression: 7.73s against 6.63s, slower than half the workers. Three
    # and four are tied inside the spread of the runs (6.54-6.90 against
    # 6.79-7.04); four is the one kept because a single member stalling on a
    # slow disk read costs a quarter of the throughput rather than a third.
    #
    # Those other two ceilings stay at six because they bound work that
    # really is dominated by waiting. This one bounds whole member analyses,
    # each of which is mostly computation once its files are read.
    #
    # What keeps four members from becoming sixteen concurrent file readers
    # is that phase-timeline reads pass through a process-wide gate (see
    # `BotObservationService._phase_timeline_gate`), and market coverage runs
    # once for the merged bot rather than once per member.
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
                #
                # `kind` is decided here and nowhere else, because this is the
                # only place that still holds the exception TYPE. Everything
                # downstream sees a string, and a string cannot be asked
                # whether it meant "this bot hides its book" or "the network
                # dropped" -- which is the whole distinction the report has to
                # draw. See `PortfolioMemberFailure.kind`.
                concealed = isinstance(exc, LedgerUnavailableError)
                logger.warning(
                    "PortfolioSupervisionPipeline: member %s/%s %s: %s",
                    request.asset,
                    request.bot_folder_name,
                    "conceals its order book" if concealed else "failed",
                    exc,
                )
                approx_capital = None
                if concealed:
                    profile = getattr(exc, "profile", None) or {}
                    raw_aum = profile.get("aum")
                    if isinstance(raw_aum, (int, float)) and raw_aum > 0:
                        approx_capital = float(raw_aum)
                failures.append(
                    PortfolioMemberFailure(
                        asset=request.asset,
                        bot_folder_name=request.bot_folder_name,
                        error=str(exc),
                        kind="concealed" if concealed else "error",
                        approx_capital_usdt=approx_capital,
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

    def fetch_public_profiles(
        self,
        member_codes: Sequence[str],
        concealed_codes: Sequence[str] = (),
    ) -> Dict[str, PublicPnlProfile]:
        """OKX's public daily PnL for every member and every concealed code.

        Read concurrently on the same worker budget as `fetch_members` (three
        light public requests per bot, rate-limited by the source). Missing
        entries are simply absent: `assess_portfolio` decides from what came
        back whether the whole matrix can move to the mark-to-market basis,
        and keeps the ledger basis otherwise. Never raises -- a portfolio run
        must not fail because an aggregate endpoint did.
        """
        wanted = [(code, False) for code in member_codes] + [
            (code, True) for code in concealed_codes
        ]
        if not wanted:
            return {}
        profiles: Dict[str, PublicPnlProfile] = {}
        lock = threading.Lock()

        def _one(item) -> None:
            code, concealed = item
            raw = self.bot_service.public_profile(
                code, folder=f"bot_{code}", include_name=concealed
            )
            parsed = parse_public_profile(code, raw)
            if parsed is not None:
                with lock:
                    profiles[code] = parsed

        workers = max(1, min(self.max_workers, len(wanted)))
        if workers == 1:
            for item in wanted:
                _one(item)
        else:
            with ThreadPoolExecutor(
                max_workers=workers, thread_name_prefix="norabt-portfolio-public"
            ) as pool:
                list(pool.map(_one, wanted))
        return profiles

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
        concealed_codes = [
            failure.bot_folder_name.removeprefix("bot_")
            for failure in failures
            if failure.kind == "concealed"
        ]
        concealed_capital_usdt = {
            failure.bot_folder_name.removeprefix("bot_"): failure.approx_capital_usdt
            for failure in failures
            if failure.kind == "concealed" and failure.approx_capital_usdt is not None
        }
        error_codes = [
            failure.bot_folder_name.removeprefix("bot_")
            for failure in failures
            if failure.kind == "error"
        ]
        public_profiles = self.fetch_public_profiles(
            [bot.identity.unique_code for bot in members], concealed_codes
        )
        portfolio = PortfolioQCService.assess_portfolio(
            [PortfolioCandidate(bot=bot) for bot in members],
            combined=combined.risk_assessment,
            iterations=portfolio_iterations,
            seed=seed,
            as_of_ms=as_of_ms,
            concealed_members=concealed_codes,
            concealed_capital_usdt=concealed_capital_usdt,
            error_members=error_codes,
            public_profiles=public_profiles,
        )
        recovered = {
            member.unique_code: member.label
            for member in portfolio.members
            if member.ledger_hidden
        }
        if duplicates:
            portfolio.warnings.append(
                "The same bot was submitted more than once and counted once: "
                + ", ".join(sorted(set(duplicates)))
            )
        # `kind` decides the wording because the two are not the same claim.
        # CONCEALED is a finding about the bot (it will not publish an order
        # book) that the verdict above has already reacted to; ERROR is a
        # defect in this run (a timeout, a bad file) that says nothing about
        # the bot and just needs a retry. One template for both would either
        # under-state a concealment or falsely accuse a bot of hiding data
        # because OKX was slow.
        for failure in failures:
            if failure.bot_folder_name.removeprefix("bot_") in recovered:
                portfolio.warnings.append(
                    f"[{recovered[failure.bot_folder_name.removeprefix('bot_')]}] "
                    "hides its order book on OKX; it is "
                    "measured from OKX's public daily PnL for correlation and joint "
                    "risk, but its trades, open positions and exit behaviour are "
                    "not observable"
                )
            elif failure.kind == "concealed":
                portfolio.warnings.append(
                    f"[{failure.bot_folder_name}] hides its order book and is "
                    f"missing from every diversification figure in this report "
                    f"(reduces confidence, not just coverage): {failure.error}"
                )
            else:
                portfolio.warnings.append(
                    f"[{failure.bot_folder_name}] could not be read and is missing "
                    f"from every figure in this report: {failure.error}"
                )
        if self.persist_history:
            self.portfolio_history.append(portfolio)

        return PortfolioSupervisionResult(
            combined=combined,
            portfolio=portfolio,
            failures=failures,
        )
