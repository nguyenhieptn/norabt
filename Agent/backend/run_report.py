from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.service import MarketService
from Agent.backend.mcp.service import BotDataUnavailableError, BotObservationService
from Agent.backend.okx.client import OkxClient
from Agent.backend.qc.reporting import narrative
from Agent.backend.qc.reporting.analysis_store import persist as persist_analysis
from Agent.backend.qc.reporting.assessment_store import persist as persist_assessment
from Agent.backend.qc.reporting.cohort import BotEvaluationRow, CohortAssessmentService
from Agent.backend.qc.reporting.data_report import DataReportService
from Agent.backend.qc.reporting.market_report import MarketRegimeService
from Agent.backend.qc.reporting.pair_report import PairedBotReportService
from Agent.backend.qc.reporting.render import (
    render_bot_report,
    render_data_report,
    render_gaps,
    render_market_report,
    render_pair_report,
    render_qc_ranking,
)
from Agent.backend.sources.bot_source import (
    BotDataSource,
    BotSourceError,
    LiveBotDataSource,
)
from Agent.backend.sources.market_source import (
    LiveMarketDataSource,
    MarketDataSource,
    MarketDataUnavailableError,
)
from Agent.backend.web.data import (

    _asset_states_from_bot_result,
    _behavioral_evidence,
    _closed_trade_series_from_bot_result,
    _narrative_strategy_profile_vi,
    _phase_breakdown_numbers,
    _strategy_evidence,
)

# Tham số Monte Carlo của BẢN CHẠY THẬT. Đặt thành hằng số vì có HAI đường
# vào chấm điểm -- lượt chấm cả đàn (`main`) và lượt người dùng bấm "Re-
# analyze" (`rescore_one_bot_complete`) -- và trước đây mỗi đường lấy một bộ
# mặc định khác nhau: đường lẻ không truyền gì nên rơi vào mặc định của
# `CohortAssessmentService.scan` (5.000 lượt, tầm CỐ ĐỊNH 500 lệnh), trong
# khi lượt chấm đàn truyền 10.000 lượt và tầm = số lệnh bot thật sự đã đóng.
# Cùng một bot, cùng một dữ liệu, ra hai báo cáo khác hẳn nhau: trung vị
# kết cục +216% theo đường lẻ so với +29% theo lượt chấm đàn, chỉ vì tầm dự
# phóng âm thầm nhảy từ 71 lên 500 lệnh. Đường lẻ còn là đường LẠC QUAN
# hơn, nên người dùng bấm nút lại nhận về bản đẹp hơn -- kiểu sai tệ nhất.
#
# `HORIZON = None` nghĩa là "dùng đúng số lệnh bot đã đóng", chứ không phải
# "không có tầm": chỉ dự phóng xa bằng đúng quãng đã quan sát được. Chiếu xa
# hơn thì `horizon_exceeds_observed` bật lên và báo cáo phải tự nói ra.
PRODUCTION_SIMULATION_ITERATIONS = 10_000
PRODUCTION_SIMULATION_HORIZON: Optional[int] = None
PRODUCTION_SIMULATION_SEED = 42


# --------------------------------------------------------------------------- #
# --source live wiring.
#
# Every *Service class under Agent/backend/qc/reporting (DataReportService,
# PairedBotReportService, MarketRegimeService, CohortAssessmentService) builds
# its own MarketService/BotObservationService inside __init__ and exposes the
# result as a plain public attribute -- self.market or self.market_service for
# the market side, self.bots or self.bot_service for the bot side, depending
# on the class. None of those constructors accept a source override, and this
# task's scope deliberately keeps qc/reporting/* untouched (see the top-level
# instructions this module was built against). Swapping the attribute right
# after construction is therefore the only extension point available: it
# hands the service a fresh MarketService/BotObservationService built around
# the live source, replacing the file-backed one the constructor made,
# without changing a single line inside qc/reporting itself. This is exactly
# what apply_live_source() below does; run_compare.py reuses it for the same
# reason.
#
# main()'s own four report services go one step further: apply_shared_services()
# and the two _Memoized* proxies right below it overwrite the same attribute
# with ONE already-built MarketService/BotObservationService instead of a
# freshly constructed one, so DataReportService/MarketRegimeService/
# PairedBotReportService/CohortAssessmentService stop each paying for their
# own copy of the same bot/asset data. See apply_shared_services()'s
# docstring for why that is a different function from apply_live_source()
# rather than a change to it.
# --------------------------------------------------------------------------- #


class _ProgressBotSource(BotDataSource):
    """Wrap a live bot source with per-call progress printing.

    A 30-bot cohort scan against OKX is a long sequence of short round-trips
    with nothing on screen otherwise -- exactly the silent-background-network-
    work this project's crawler-throttle preference forbids. LiveBotDataSource
    itself only prints for the one call that can be slow on its own (candle
    backfill lives in LiveMarketDataSource, not here), so this wrapper is what
    makes a live run's per-bot progress visible. It is additive only: it
    delegates every call unchanged and never alters what is returned.
    """

    def __init__(self, inner: BotDataSource) -> None:
        self._inner = inner
        self._seen: dict = {}

    def _mark(self, unique_code: str, what: str) -> None:
        if unique_code not in self._seen:
            self._seen[unique_code] = len(self._seen) + 1
        print(
            f"  [live bot #{self._seen[unique_code]}] {unique_code}: "
            f"calling OKX ({what})...",
            file=sys.stderr,
        )

    def get_overview(self, unique_code, bot_dir=None):
        self._mark(unique_code, "overview/profile")
        return self._inner.get_overview(unique_code, bot_dir)

    def get_ledger(self, unique_code, bot_dir=None):
        self._mark(unique_code, "ledger")
        return self._inner.get_ledger(unique_code, bot_dir)


class _ProgressMarketSource(MarketDataSource):
    """Wrap a live market source with per-call progress printing.

    Candle backfill already prints its own progress (see
    LiveMarketDataSource._paginate_candles_raw); this wrapper adds visibility
    for the other, silent, per-asset calls (orderbook, open interest, taker
    flow, sentiment, macro) so a market-report run over many assets is never
    a long silent pause. DEX-only getters (ticks/pool liquidity/token
    security) make no network call on this source at all, so they are left
    unannounced.
    """

    def __init__(self, inner: MarketDataSource) -> None:
        self._inner = inner
        self._seen: dict = {}

    def _mark(self, symbol: str, what: str) -> None:
        if symbol not in self._seen:
            self._seen[symbol] = len(self._seen) + 1
        print(
            f"  [live market #{self._seen[symbol]}] {symbol}: calling OKX ({what})...",
            file=sys.stderr,
        )

    def resolve_venue(self, symbol, venue_type):
        return self._inner.resolve_venue(symbol, venue_type)

    def get_candles(self, symbol, venue_type):
        self._mark(symbol, "candles")
        return self._inner.get_candles(symbol, venue_type)

    def get_orderbook(self, symbol, venue_type):
        self._mark(symbol, "order book")
        return self._inner.get_orderbook(symbol, venue_type)

    def get_open_interest(self, symbol, venue_type):
        self._mark(symbol, "open interest")
        return self._inner.get_open_interest(symbol, venue_type)

    def get_taker_volume(self, symbol, venue_type):
        self._mark(symbol, "taker volume")
        return self._inner.get_taker_volume(symbol, venue_type)

    def get_sentiment(self, symbol, venue_type):
        self._mark(symbol, "sentiment")
        return self._inner.get_sentiment(symbol, venue_type)

    def get_macro_context(self, symbol, venue_type):
        self._mark(symbol, "macro (BTC candles)")
        return self._inner.get_macro_context(symbol, venue_type)

    # DEX-only inputs: no network call on this (CEX-only) source, see class docstring.
    def get_ticks(self, symbol, venue_type):
        return self._inner.get_ticks(symbol, venue_type)

    def get_pool_liquidity(self, symbol, venue_type):
        return self._inner.get_pool_liquidity(symbol, venue_type)

    def get_token_security(self, symbol, venue_type):
        return self._inner.get_token_security(symbol, venue_type)


def build_live_sources() -> Tuple[BotDataSource, MarketDataSource]:
    """Build the pair of live sources --source live wires into the report
    services, sharing one OkxClient (cheap: it is a stateless transport, and
    sharing it means one process-wide IPv4 preference / user-agent setup)."""
    client = OkxClient()
    return (
        _ProgressBotSource(LiveBotDataSource(client=client)),
        _ProgressMarketSource(LiveMarketDataSource(client=client)),
    )


def apply_live_source(
    service: object,
    *,
    data_dir: Path,
    mode: EvaluationMode,
    bot_source: Optional[BotDataSource] = None,
    market_source: Optional[MarketDataSource] = None,
) -> None:
    """Point an already-built qc/reporting service at live data instead of
    files -- see the module-level comment above for why this is a
    post-construction attribute swap rather than a constructor parameter."""
    if market_source is not None:
        for attr in ("market", "market_service"):
            if hasattr(service, attr):
                setattr(
                    service,
                    attr,
                    MarketService(data_dir, mode, market_source=market_source),
                )
    if bot_source is not None:
        for attr in ("bots", "bot_service"):
            if hasattr(service, attr):
                setattr(
                    service,
                    attr,
                    BotObservationService(data_dir, mode, bot_source=bot_source),
                )


# --------------------------------------------------------------------------- #
# Sharing one MarketService/BotObservationService across all four report
# services, with in-process memoisation on top.
#
# Measured on a real 63-minute --source live run: candles were fetched ~2.7x
# per asset and ledgers ~3.4x per bot, because DataReportService,
# MarketRegimeService, PairedBotReportService and CohortAssessmentService
# each build their own MarketService/BotObservationService in __init__ (see
# their constructors in Agent/backend/qc/reporting/*.py) -- so the same
# bot/asset touched by more than one of the four reports asked OKX for it
# again from scratch every time. The candle side already has an on-disk
# cache (see sources/market_source.py), which is why its ratio is lower;
# the bot side has none, so every one of those extra ledger fetches was
# paid for in full.
#
# The fix is two parts:
#   1. Build exactly one MarketService and one BotObservationService per
#      run (in main(), below) and hand every report service the same
#      instance via apply_shared_services() instead of letting each one
#      build its own.
#   2. That alone only removes the *construction* duplication. A call with
#      the exact same arguments made from two different report services
#      (e.g. the same bot scored by both step 2's pair report and step 3's
#      cohort scan, at the same as_of_ms) would still cost a full
#      get_bot_result()/get_market_result() each time, because neither
#      class remembers anything about a previous call. The two _Memoized*
#      proxies below add that memory, keyed on the exact arguments the real
#      call was made with.
# --------------------------------------------------------------------------- #


class _MemoCache:
    """Tiny memoisation helper shared by both proxies below.

    Deliberately does not cache a call that raised: if get_market_result/
    get_bot_result fails (MarketDataUnavailableError, BotDataUnavailableError,
    BotSourceError, ValueError -- every qc/reporting call site around these
    already catches its own), the next identical call retries from scratch,
    exactly like the unwrapped service would. Caching a failure would replace
    one call with a stale/fabricated success on a later retry with different
    live data behind it -- worse than the duplicate work this is meant to
    remove.
    """

    def __init__(self) -> None:
        self._store: Dict[tuple, Any] = {}
        self.hits = 0
        self.misses = 0

    @property
    def calls(self) -> int:
        return self.hits + self.misses

    def get_or_compute(self, key: tuple, compute) -> Any:
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.misses += 1
        value = compute()
        self._store[key] = value
        return value


class _MemoizedMarketService:
    """In-process memoisation wrapper around one MarketService instance.

    WHY A WRAPPER INSTEAD OF EDITING MarketService: Agent/backend/market/
    service.py is out of scope for this change, and MarketService has no
    notion of caching -- every get_market_result() call re-reads every input
    from market_source from scratch, live or file. Composing over one
    already-built instance here, in run_report.py, is the only extension
    point that does not touch that file: __getattr__ forwards anything this
    wrapper does not define itself (data_dir, evaluation_mode, market_source,
    ...) straight to the real instance, so it is a transparent stand-in
    wherever qc/reporting/* expects "something shaped like MarketService" --
    which in practice is only ever a call to get_market_result().

    WHY THE CACHE KEY IS THE FULL ARGUMENT TUPLE: get_market_result's
    resolved venue, anchor timestamp and every freshness grade in the result
    depend on all three of its arguments, as_of_ms especially -- SNAPSHOT
    grading is relative to it, so two calls that differ only in as_of_ms
    describe two different moments and must never share a cache entry.
    Keying on the full tuple, rather than a hand-picked subset, is what makes
    that guarantee automatic instead of something that has to be kept in
    sync with the method's signature by hand.
    """

    def __init__(self, inner: MarketService) -> None:
        self._inner = inner
        self._cache = _MemoCache()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    @property
    def cache_hits(self) -> int:
        return self._cache.hits

    @property
    def cache_calls(self) -> int:
        return self._cache.calls

    def get_market_result(
        self,
        symbol: str,
        venue_type: Optional[str] = None,
        as_of_ms: Optional[int] = None,
    ):
        key = (symbol, venue_type, as_of_ms)
        return self._cache.get_or_compute(
            key,
            lambda: self._inner.get_market_result(symbol, venue_type, as_of_ms),
        )


class _MemoizedBotObservationService:
    """In-process memoisation wrapper around one BotObservationService
    instance -- see _MemoizedMarketService's docstring for the wrapper-vs-edit
    reasoning and the __getattr__ forwarding, both identical here.

    The cache key mirrors get_bot_result's full signature, selection_trials
    included: it is optional and often equal across the report services that
    call it for the same bot, but "often equal" is not "always equal" (step 2
    and step 3 derive it from the same bot_selection.json field, yet nothing
    enforces the two derivations stay identical forever), and it does change
    the result (it feeds the deflated Sharpe calculation). Keying on the
    complete tuple, rather than the subset that happens to be the same today,
    is what keeps a future divergence from silently returning the wrong bot's
    inference numbers.
    """

    def __init__(self, inner: BotObservationService) -> None:
        self._inner = inner
        self._cache = _MemoCache()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    @property
    def cache_hits(self) -> int:
        return self._cache.hits

    @property
    def cache_calls(self) -> int:
        return self._cache.calls

    def get_bot_result(
        self,
        asset: str,
        bot_folder_name: str = "bot_top_performer",
        seed: Optional[int] = 42,
        venue_type: Optional[str] = None,
        as_of_ms: Optional[int] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: Optional[int] = None,
        selection_trials: Optional[int] = None,
    ):
        key = (
            asset,
            bot_folder_name,
            seed,
            venue_type,
            as_of_ms,
            simulation_iterations,
            simulation_horizon,
            selection_trials,
        )
        return self._cache.get_or_compute(
            key,
            lambda: self._inner.get_bot_result(
                asset,
                bot_folder_name,
                seed=seed,
                venue_type=venue_type,
                as_of_ms=as_of_ms,
                simulation_iterations=simulation_iterations,
                simulation_horizon=simulation_horizon,
                selection_trials=selection_trials,
            ),
        )


def build_shared_services(
    data_dir: Path,
    mode: EvaluationMode,
    *,
    bot_source: Optional[BotDataSource] = None,
    market_source: Optional[MarketDataSource] = None,
) -> Tuple[_MemoizedMarketService, _MemoizedBotObservationService]:
    """Build the one MarketService and one BotObservationService a whole
    run_report.py run shares across all four report services.

    bot_source/market_source is None for --source file (each memoized
    service then falls back to its own default file-backed source, exactly
    like every qc/reporting constructor already did on its own) and the live
    sources built by build_live_sources() for --source live -- either way,
    this is called exactly once per run, which is what apply_shared_services()
    then hands to every report service in place of the private instance its
    own constructor built.
    """
    return (
        _MemoizedMarketService(
            MarketService(data_dir, mode, market_source=market_source)
        ),
        _MemoizedBotObservationService(
            BotObservationService(data_dir, mode, bot_source=bot_source)
        ),
    )


def apply_shared_services(
    service: object,
    *,
    shared_market_service: _MemoizedMarketService,
    shared_bot_service: _MemoizedBotObservationService,
) -> None:
    """Point an already-built qc/reporting service at the single shared,
    memoized MarketService/BotObservationService this run built once (see
    build_shared_services()), overwriting the private instance the service's
    own constructor made.

    Structurally this is the same post-construction attribute swap
    apply_live_source() performs above, for the same reason (qc/reporting/*
    takes no service override and is out of scope here). It is a separate
    function rather than a reuse of apply_live_source() because the two have
    different contracts: apply_live_source()'s is "build me a brand new
    *Service around this raw source, or do nothing if there is none" --
    exactly what --source live's own call sites in run_compare.py still need,
    unchanged -- while this one's is "use this exact, already-built instance
    for every report service", which is the one thing that makes sharing (and
    therefore caching) possible. Called unconditionally for both --source
    modes, so --source file benefits from the sharing/caching too.
    """
    for attr in ("market", "market_service"):
        if hasattr(service, attr):
            setattr(service, attr, shared_market_service)
    for attr in ("bots", "bot_service"):
        if hasattr(service, attr):
            setattr(service, attr, shared_bot_service)


def default_selection_codes(
    data_dir: Path, *, bot: Optional[str], all_bots: bool
) -> Optional[Set[str]]:
    """The uniqueCode set step 3 should score: one bot, every crawled bot, or
    (the common case) exactly the 30 bots step 2 selected.

    Factored out of main() so run_compare.py can pick the same default cohort
    without duplicating the bot_selection.json lookup.
    """
    if bot:
        return {bot}
    if all_bots:
        return None
    selection_path = Path(data_dir) / "universe" / "bot_selection.json"
    if not selection_path.exists():
        return None
    return set(json.loads(selection_path.read_text(encoding="utf-8"))["unique_codes"])


# --------------------------------------------------------------------------- #
# Việc 1/4 -- carrying strategy/behavioural evidence and the LLM narrative
# into step 3's own persisted `assessment.json` files, which
# `CohortAssessmentService.scan()` cannot do on its own: `BotEvaluationRow`
# (cohort.py, off-limits to edit for this task) never carries
# `phase_breakdown`/the behavioural flags/scores, and `scan()` throws away
# the `BotResult`/`BotRiskAssessment` pair it computed for each bot once the
# row is flattened. Both fixes here work the SAME way: re-fetch exactly the
# one artefact `BotEvaluationRow` is missing, from the SAME snapshot the
# scan already read (same `asset`/`bot_folder`/`venue`, same
# `as_of_ms=cohort.generated_at_ms`), and read it OFF, never re-score
# anything -- the risk/quality/dimension numbers in the assessment always
# come from `row` alone, exactly as before this task.
#
# Deliberately NOT a second call to `QCCoreService.assess_bot`/
# `RiskSupervisionPipeline.run`: either would need this run's exact
# `portfolio_bots` list (whichever OTHER bots were in the same cohort scan)
# to reproduce the SAME `portfolio_risk` dimension score cohort.py's own
# call already computed, and nothing outside cohort.py has that list. Since
# `strategy_observations`/`behavioral_observations` are pure functions of
# one bot's own ledger + market timeline (see
# Agent/backend/mcp/analytics/strategy/profile.py's own module docstring --
# "Nothing here is inferred where the evidence is absent"), independent of
# portfolio, seed or Monte Carlo settings, a bare `get_bot_result` re-fetch
# reproduces them byte-for-byte without that risk -- see
# `test_run_report_narrative.py`'s own "matches the row's own numbers" test.
#
# `closed_trade_series`/`horizon_scenarios`/`assets` (added later, same fix
# that restores what `GET /bot/<code>` loses when it has to read
# assessment.json instead of running live -- verified by literally counting
# `<svg>`/`<details>` on both: file-sourced was 5/8, live is 7/12 -- see
# `assessment_store.build_assessment`'s own docstring) ride the SAME
# re-fetch. `trade_ledger_summary`/`current_state.open_positions` are just
# as pure/re-fetch-safe as the strategy/behavioural observations above, but
# `simulation_results.horizon_scenarios` is NOT -- it is genuine Monte Carlo
# output, so unlike the three observation-only objects, THIS one only
# reproduces the exact numbers already used to score the bot when the
# re-fetch uses the SAME `iterations`/`horizon`/`seed` `cohort_service.
# scan()` did. `main()` below passes those real values through
# `build_assessment_extras` for exactly this reason -- never the throwaway
# tiny settings a plain strategy/behavioural-only re-fetch could get away
# with. (`assets`' own `last_close_days`/`state` are frozen at THIS run's
# `as_of_ms`, same as every other bang_chung field already is -- the
# existing "quá 24 giờ" staleness banner on the assessment-file-served page
# is what tells a reader when that freeze is stale, not a live recompute.)
# --------------------------------------------------------------------------- #


def _fetch_bot_for_extras(
    bot_service: BotObservationService,
    row: BotEvaluationRow,
    as_of_ms: int,
    *,
    simulation_iterations: int = 100,
    simulation_horizon: Optional[int] = 1,
    seed: int = 42,
) -> Optional[Any]:
    """Re-fetch this ONE row's own `BotResult`, from the same snapshot
    `CohortAssessmentService.scan()` already scored it from -- `None` (never
    raises) when the snapshot has since become unreadable, so a flaky re-read
    degrades this bot's strategy/behavioural extras to absent rather than
    aborting the whole run.

    `simulation_iterations=100`/`simulation_horizon=1` are the historical
    defaults -- deliberately tiny, because the ONLY things this call used to
    be for (`.strategy_observations`/`.behavioral_observations`) never touch
    the Monte Carlo pass, so there was no reason to pay for a full
    10,000-iteration simulation a second time just to reach them. Now that
    this same re-fetch also supplies `.simulation_results.horizon_scenarios`
    (see the module comment above this function), `build_assessment_extras`
    passes the REAL `iterations`/`horizon`/`seed` the caller's `scan()` run
    used -- these three parameters stay at the old cheap defaults only so a
    caller that genuinely never needs `horizon_scenarios` (e.g. a future
    strategy/behavioural-only use) is unaffected.
    """
    try:
        return bot_service.get_bot_result(
            row.asset_context,
            row.bot_folder,
            seed=seed,
            venue_type=row.snapshot_venue,
            as_of_ms=as_of_ms,
            simulation_iterations=simulation_iterations,
            simulation_horizon=simulation_horizon,
        )
    except (BotDataUnavailableError, BotSourceError, ValueError) as exc:
        print(
            f"[step 3] {row.unique_code}: could not re-fetch BotResult to add "
            f"strategy/behavioural evidence -- {exc}",
            file=sys.stderr,
        )
        return None


def _simulation_full_evidence(bot: Any) -> Optional[Dict[str, Any]]:
    """`bot.simulation_results` in full, for `build_assessment`'s
    `simulation_full=`.

    The stored `simulation` block was assembled field by field from
    `BotEvaluationRow`, which carries only the subset the batch report needed.
    Thirty-one measured fields (`capital_at_risk`, `expected_terminal_equity`,
    `horizon_sensitivity`, `p10_outcome`, ...) were therefore computed on every
    run and then thrown away, so a page rebuilt from disk was permanently
    poorer than the live page for the same bot. Writing the engine's own dump
    keeps the two in step, and keeps them in step when the schema grows.

    `None` (never `{}`) when `bot` is absent -- same "absent, not fabricated"
    contract the other evidence helpers follow.
    """
    if bot is None:
        return None
    simulation = getattr(bot, "simulation_results", None)
    dump = getattr(simulation, "model_dump", None)
    if not callable(dump):
        # A stub or an older shape that is not the typed model: write nothing
        # rather than half a block.
        return None
    return dump(mode="json")


def _horizon_scenarios_evidence(bot: Any) -> Optional[List[Dict[str, Any]]]:
    """`bot.simulation_results.horizon_scenarios` (a `List[HorizonOutcome]`,
    Agent/backend/mcp/schemas/bot_result.py), reshaped to plain dicts for
    `assessment_store.build_assessment`'s `horizon_scenarios=` -- the exact
    same `model_dump(mode="json")` shape the LIVE path already exposes via
    `bot.simulation_results.model_dump(mode="json")["horizon_scenarios"]`
    (Agent/backend/web/data.py), so `report_page.py` reads identical keys
    (`label`, `horizon_trades`, `probability_of_profit`, ...) regardless of
    which path produced them.

    `None` (never `[]`) when `bot` is `None` or the simulation produced no
    scenarios (e.g. too few trades) -- same "absent, not fabricated" contract
    `_strategy_evidence`/`_behavioral_evidence` already follow, so
    `build_assessment` can tell "nothing to add" apart from "add an empty
    list" without a second signal.
    """
    if bot is None:
        return None
    sim = getattr(bot, "simulation_results", None)
    scenarios = getattr(sim, "horizon_scenarios", None) if sim is not None else None
    if not scenarios:
        return None
    return [
        scenario.model_dump(mode="json")
        for scenario in scenarios
        if hasattr(scenario, "model_dump")
    ] or None


def _closed_trade_series_evidence(bot: Any) -> Optional[List[Dict[str, Any]]]:
    """`_closed_trade_series_from_bot_result(bot)` (data.py), guarded for
    `bot is None`/a test double that never set `.trade_ledger_summary` at
    all (that attribute IS required on a real `BotResult`, so this guard
    only ever fires for the latter) -- same "absent, not fabricated"
    contract as `_horizon_scenarios_evidence` above.
    """
    if bot is None or not hasattr(bot, "trade_ledger_summary"):
        return None
    return _closed_trade_series_from_bot_result(bot) or None


def _assets_evidence(bot: Any) -> Optional[List[Dict[str, Any]]]:
    """`_asset_states_from_bot_result(bot)` (data.py) -- the third field
    this same re-fetch turned out to be necessary for: `report_page.py`'s
    "Tài sản đang giao dịch" table/theory-block (`_render_assets`) is gated
    on a non-empty top-level `assets` list, which
    `assessment_to_analyze_result` used to hard-code to `[]` unconditionally
    -- a THIRD, separate gap from `closed_trade_series`/`horizon_scenarios`
    (a table, not a chart, so it cost 0 `<svg>` but 1 `<details>`), found by
    actually counting tags rather than assuming the two known root causes
    were the whole gap. Guarded the same way the two helpers above are.
    """
    if (
        bot is None
        or not hasattr(bot, "current_state")
        or not hasattr(bot, "trade_ledger_summary")
    ):
        return None
    return _asset_states_from_bot_result(bot) or None


def _row_narrative_numbers(row: BotEvaluationRow) -> List["narrative.NumberSpec"]:
    """The row-sourced half of a batch narrative's `NumberSpec`s -- mirrors
    `Agent/backend/web/data.py`'s `_narrative_numbers` labels/roundings
    where the same figure exists on `BotEvaluationRow`, but reads
    EXCLUSIVELY from `row` (never a re-fetched/recomputed object): `row` is
    this exact assessment's own already-scored numbers, and Việc 4's own
    hard constraint is that a batch narrative must never drift from them.
    """
    N = narrative.make_number
    specs = []

    def add(spec: Optional["narrative.NumberSpec"]) -> None:
        if spec is not None:
            specs.append(spec)

    add(
        N(
            "Risk score (a composite score, not a percentage -- higher means riskier)",
            row.risk_score,
            decimals=1,
        )
    )
    add(
        N(
            "Quality score (a composite score, not a percentage)",
            row.quality_score,
            decimals=1,
        )
    )
    add(N("Confidence level of this assessment", row.confidence, decimals=0, percent=True))
    add(N("Closed trades", row.trade_count, decimals=0))
    add(N("Win rate", row.win_rate, decimals=1, percent=True))
    add(N("Profit factor on closed trades", row.profit_factor, decimals=2))
    add(N("Max drawdown recorded", row.max_drawdown_pct, decimals=1, percent=True))
    add(N("Sharpe ratio", row.sharpe_ratio, decimals=2))
    add(
        N(
            "Payoff ratio (average win divided by average loss)",
            row.payoff_ratio,
            decimals=2,
        )
    )
    add(N("Longest losing streak", row.max_loss_streak, decimals=0))
    add(
        N("Profit factor if the open book were closed now", row.marked_profit_factor, decimals=2)
    )
    add(
        N(
            "Unrealised loss on the open book as a share of reference capital",
            row.open_loss_to_capital_pct,
            decimals=1,
            percent=True,
        )
    )
    add(
        N(
            "Probability of account ruin in the simulation",
            row.p_ruin,
            decimals=1,
            percent=True,
        )
    )
    add(
        N(
            "Simulated drawdown in the bad-case band (tail of the distribution)",
            row.p95_max_drawdown,
            decimals=1,
            percent=True,
        )
    )
    add(
        N(
            "Probability of still being in a loss after the simulation horizon",
            row.p_loss_after_horizon,
            decimals=1,
            percent=True,
        )
    )
    if row.mc_iterations:
        add(N("Number of Monte Carlo simulation scenarios", row.mc_iterations, decimals=0))
    if row.mc_horizon:
        add(N("Simulation horizon", row.mc_horizon, decimals=0))
    if row.trades_per_day is not None:
        add(N("Average trading frequency", row.trades_per_day, decimals=1))
    if row.capital_at_risk is not None:
        add(
            N(
                "Reference capital inferred from the actual equity curve",
                row.capital_at_risk,
                decimals=0,
                money=True,
            )
        )
    if row.score_decided_by and row.score_decided_by != "WEIGHTED_AVERAGE":
        add(
            N(
                "Weighted average across risk dimensions before any veto/emergency override",
                row.weighted_average,
                decimals=1,
            )
        )
        if row.veto_floor is not None:
            add(
                N(
                    "Veto floor that set the final risk score",
                    row.veto_floor,
                    decimals=1,
                )
            )
    return specs


def _narrative_for_row(row: BotEvaluationRow, bot: Optional[Any]) -> Optional[str]:
    """`None` when the narrative feature is unconfigured (see
    `narrative.select_backend_from_env`) or `bot` could not be re-fetched
    (`_fetch_bot_for_extras` already logged why) -- the strategy-profile
    text needs the re-fetched `BotResult`, so without it there is nothing
    safe to build a narrative from. Any other unexpected error degrades to
    `narrative.FALLBACK_NARRATIVE_VI`, same "additive field, must never take
    down the rest of an otherwise-successful run" contract
    `_generate_narrative_for_full_result` (data.py) already follows for the
    live web path.
    """
    if bot is None:
        return None
    try:
        numbers = _row_narrative_numbers(row)
        numbers.extend(_phase_breakdown_numbers(bot.strategy_observations))
        context = narrative.NarrativeContext(
            verdict=row.verdict or "",
            traded_symbol=row.traded_symbol or "",
            untrusted_nick_name=row.nick_name or "",
            strategy_profile_vi=_narrative_strategy_profile_vi(bot),
        )
        return narrative.generate_narrative_sync(numbers, context)
    except Exception:  # noqa: BLE001 - additive field, must not abort the run.
        print(
            f"[step 3] {row.unique_code}: unexpected error generating the "
            "expert narrative -- using the default sentence",
            file=sys.stderr,
        )
        return narrative.FALLBACK_NARRATIVE_VI


def build_assessment_extras(
    cohort: Any,
    bot_service: BotObservationService,
    *,
    generate_narrative_flag: bool = True,
    reuse_stored_narrative: bool = False,
    data_dir: Optional[Path] = None,
    simulation_iterations: int = 100,
    simulation_horizon: Optional[int] = 1,
    seed: int = 42,
) -> Dict[str, Dict[str, Any]]:
    """`{unique_code: {"strategy": {...}, "behavioral": {...}, "narrative":
    str|None, "closed_trade_series": [...]|None, "horizon_scenarios":
    [...]|None, "assets": [...]|None}}` for every scored row in `cohort` --
    fed straight into `assessment_store.persist(..., extra_by_code=...)`.

    `simulation_iterations`/`simulation_horizon`/`seed` default to the same
    historical cheap-refetch settings `_fetch_bot_for_extras` always used
    (so every pre-existing caller/test is unaffected), but `main()` below
    passes the REAL `--iterations`/`--horizon`/`--seed` this run's own
    `cohort_service.scan()` used -- required for `horizon_scenarios` to
    match the Monte Carlo actually used to score each bot (see
    `_fetch_bot_for_extras`'s own docstring).

    HAI PHA, và lý do chia pha là số đo chứ không phải sở thích:
    trên 30 bot thật, phần chấm điểm (nạp bot, Monte Carlo, dựng bằng chứng)
    tốn TRUNG VỊ 0,4 GIÂY mỗi bot -- tổng 14 giây -- trong khi phần sinh văn
    bằng mô hình ngôn ngữ tốn TRUNG VỊ 88 GIÂY mỗi bot. Tức 99,5% thời gian
    của cả lượt nằm ở đúng một chỗ.

      pha 1 (tuần tự) : nạp bot + dựng bằng chứng. Nhanh, giữ nguyên thứ tự.
      pha 2 (song song): sinh văn, tối đa `narrative.MAX_CONCURRENT_CALLS`
                         lượt cùng lúc.

    VÌ SAO SONG SONG LÀ AN TOÀN Ở ĐÂY, trong khi nguyên tắc của dự án là
    "chạy tuần tự, không đẩy nền": nguyên tắc đó sinh ra để chặn việc dội
    request vào OKX và việc chạy ngầm không ai thấy tiến độ. Sinh văn KHÔNG
    gọi OKX (nó gọi một tiến trình CLI cục bộ), và pha 2 dưới đây VẪN in
    tiến độ từng bot ngay khi bot đó xong. Trần đồng thời do chính
    `narrative._SEMAPHORE` giữ, nên số luồng ở đây không thể vượt qua nó --
    đặt nhiều luồng hơn cũng chỉ xếp hàng, không tạo thêm tiến trình nào.

    Không đổi một chữ nào trong prompt, model hay năm cổng kiểm duyệt: đây
    thuần tuý là bỏ việc bắt bot sau đứng chờ bot trước.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from Agent.backend.qc.reporting import narrative as _narrative

    extras: Dict[str, Dict[str, Any]] = {}
    rows = [r for r in cohort.rows if not r.error and r.verdict is not None]
    total = len(rows)

    # --- Pha 1: chấm điểm, tuần tự (trung vị 0,4s/bot) --------------------
    fetched: List[Tuple[Any, Any]] = []
    for index, row in enumerate(rows, start=1):
        started = time.monotonic()
        bot = _fetch_bot_for_extras(
            bot_service,
            row,
            cohort.generated_at_ms,
            simulation_iterations=simulation_iterations,
            simulation_horizon=simulation_horizon,
            seed=seed,
        )
        extras[row.unique_code] = {
            "strategy": _strategy_evidence(bot.strategy_observations) if bot else None,
            "behavioral": (
                _behavioral_evidence(bot.behavioral_observations) if bot else None
            ),
            "narrative": None,
            "closed_trade_series": _closed_trade_series_evidence(bot),
            "horizon_scenarios": _horizon_scenarios_evidence(bot),
            "simulation_full": _simulation_full_evidence(bot),
            "assets": _assets_evidence(bot),
        }
        fetched.append((row, bot))
        print(
            f"[step 3] ({index}/{total}) {row.nick_name} ({row.unique_code}): "
            f"strategy/behavioural evidence {'OK' if bot else 'MISSING'} "
            f"-- {time.monotonic() - started:.1f}s",
            file=sys.stderr,
        )

    if not generate_narrative_flag:
        if reuse_stored_narrative and data_dir is not None:
            # Ghi lại CÙNG những bot này chỉ vì hình dạng dữ liệu đổi (thêm
            # một trường bằng chứng, đổi tên một khoá) không làm đoạn văn cũ
            # sai đi -- nó nói về chiến lược và rủi ro của bot, không nói về
            # bố cục JSON. Nhưng `persist` ghi thẳng `narrative_text` xuống
            # `expert_assessment`, nên bỏ trống nó là XOÁ, không phải giữ.
            # Đọc lại từ chính file của bot là cách duy nhất giữ được văn mà
            # không tốn một giây gọi mô hình nào.
            # Tra theo MÃ BOT chứ không dựng lại đường dẫn từ venue/symbol:
            # `BotEvaluationRow` không mang tên thư mục tài sản (nó có
            # `traded_symbol` là mã hợp đồng, khác với tên ô lưu trữ), và
            # đoán sai đường dẫn ở đây sẽ âm thầm giữ được 0 đoạn văn rồi
            # xoá sạch -- đúng thứ cả nhánh này sinh ra để tránh.
            root = Path(data_dir) / "assessment"
            by_code = {
                path.parent.name.rpartition("__")[2]: path
                for path in root.glob("*/*/bot/*/assessment.json")
            }
            kept = 0
            for row in rows:
                path = by_code.get(row.unique_code)
                if path is None:
                    continue
                try:
                    stored = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                text = stored.get("expert_assessment")
                if isinstance(text, str) and text.strip():
                    extras[row.unique_code]["narrative"] = text
                    kept += 1
            print(
                f"[step 3] giữ lại {kept}/{total} nhận định đã lưu "
                f"(không gọi mô hình)",
                file=sys.stderr,
            )
        return extras

    # --- Pha 2: sinh văn, song song trong đúng trần đã có ------------------
    workers = max(1, _narrative.MAX_CONCURRENT_CALLS)
    print(
        f"[step 3] sinh nhận định cho {total} bot, tối đa {workers} lượt cùng lúc",
        file=sys.stderr,
    )
    started_all = time.monotonic()
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_narrative_for_row, row, bot): row for row, bot in fetched
        }
        for future in as_completed(futures):
            row = futures[future]
            done += 1
            try:
                text = future.result()
            except Exception:  # noqa: BLE001 - trường bổ sung, không được
                # làm hỏng cả lượt chấm; _narrative_for_row đã tự bắt lỗi,
                # đây chỉ là lưới cuối.
                text = _narrative.FALLBACK_NARRATIVE_VI
            extras[row.unique_code]["narrative"] = text
            print(
                f"[step 3] narrative ({done}/{total}) {row.nick_name}: "
                f"{'OK' if text and text != _narrative.FALLBACK_NARRATIVE_VI else 'FALLBACK'}"
                f" -- {time.monotonic() - started_all:.0f}s trôi qua",
                file=sys.stderr,
            )
    return extras


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate every bot in the dataset and rank them by risk"
    )
    parser.add_argument(
        "--venue",
        choices=("CEX", "DEX", "ALL"),
        default="ALL",
        help="Venue scope to scan",
    )
    parser.add_argument(
        "--iterations", type=int, default=PRODUCTION_SIMULATION_ITERATIONS
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=PRODUCTION_SIMULATION_HORIZON,
        help=(
            "trades per Monte Carlo scenario; leave blank to use the bot's own "
            "trade count, since that is the horizon actually observed"
        ),
    )
    parser.add_argument("--seed", type=int, default=PRODUCTION_SIMULATION_SEED)
    parser.add_argument(
        "--as-of-ms",
        type=int,
        default=None,
        help="Evaluation clock for a deterministic replay",
    )
    parser.add_argument(
        "--mode",
        choices=("SNAPSHOT", "LIVE"),
        default="SNAPSHOT",
        help="SNAPSHOT: grade freshness against the dataset crawl timestamp",
    )
    parser.add_argument(
        "--report",
        choices=("data", "market", "bot", "cohort", "qc", "gaps", "all"),
        default="all",
        help=(
            "data = step 1 (market + bot data inventory), "
            "market/bot = the two halves of step 2 (market analysis and bot analysis), "
            "qc = step 3, cohort = flat list of every crawled bot, all = all three steps"
        ),
    )
    parser.add_argument(
        "--all-bots",
        action="store_true",
        help=("score every crawled bot instead of just the 30 bots step 2 selected"),
    )
    parser.add_argument(
        "--bot",
        help=(
            "run exactly one bot by uniqueCode; steps 1 and 2 narrow down to "
            "that bot's asset, step 3 scores only that bot"
        ),
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="don't write step 2/3 output to data/analysis and data/assessment",
    )
    parser.add_argument(
        "--no-narrative",
        action="store_true",
        help=(
            "disable generating the expert (LLM) narrative when writing the "
            "step 3 assessment -- ON by default (if NORABT_NARRATIVE_BACKEND "
            "is configured); use this flag to run faster when the narrative "
            "isn't needed, e.g. when iterating repeatedly during development"
        ),
    )
    parser.add_argument(
        "--reuse-narrative",
        action="store_true",
        help=(
            "reuse the expert narrative already stored in each bot's "
            "assessment.json instead of generating a new one -- for re-"
            "persisting the same bots after a DATA-shape change (a new "
            "evidence field, a renamed key), where the prose is still "
            "correct and only the numbers around it need rewriting. Without "
            "it, --no-narrative writes expert_assessment=null and every "
            "stored narrative is lost; with it the same run costs no model "
            "time at all. Ignored when the narrative is being generated."
        ),
    )
    parser.add_argument(
        "--source",
        choices=("file", "live"),
        default="file",
        help=(
            "file (default) = read already-crawled data under data/, unchanged "
            "old behaviour; live = read straight from OKX via LiveBotDataSource/"
            "LiveMarketDataSource, without writing anything to data/cex or data/dex"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help=(
            "where to write step 2/3 output (data/analysis, data/assessment); "
            "defaults to staying inside data/ -- change this when running "
            "--source live so it doesn't overwrite the file path's results, "
            "for run_compare.py to compare the two paths"
        ),
    )
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--no-detail", dest="detail", action="store_false")
    args = parser.parse_args(argv)

    venues = ("CEX", "DEX") if args.venue == "ALL" else (args.venue,)
    mode = EvaluationMode(args.mode)
    want = args.report
    data_dir = Path(config.DATA_DIR)
    # Defaults to data_dir itself, i.e. the exact `Path(config.DATA_DIR)` every
    # persist call used before --out-dir existed -- so not passing the flag is
    # byte-for-byte the old behaviour.
    out_dir = Path(args.out_dir) if args.out_dir else data_dir

    live_bot_source: Optional[BotDataSource] = None
    live_market_source: Optional[MarketDataSource] = None
    if args.source == "live":
        print(
            "[source] LIVE -- reading straight from OKX via LiveBotDataSource/"
            "LiveMarketDataSource, not using already-crawled files",
            file=sys.stderr,
        )
        live_bot_source, live_market_source = build_live_sources()

    # Only build what was asked for: the cohort scan walks every bot folder and
    # is not needed to answer a question about markets or about the chosen pairs.
    needs_cohort = want in ("cohort", "qc", "gaps", "all")
    needs_pairs = want in ("bot", "all")
    needs_market = want in ("market", "all")
    needs_data = want in ("data", "all")

    # Built exactly once, regardless of --report/--source, and handed to every
    # report service below via apply_shared_services() instead of each one
    # building its own MarketService/BotObservationService -- see that
    # function's docstring and the block comment above build_shared_services()
    # for why. Both classes' __init__ do no I/O of their own (they only set
    # attributes), so building both unconditionally here costs nothing even
    # when e.g. --report data never touches the bot side.
    shared_market_service, shared_bot_service = build_shared_services(
        data_dir, mode, bot_source=live_bot_source, market_source=live_market_source
    )

    try:
        data_report = None
        if needs_data:
            data_service = DataReportService(evaluation_mode=mode)
            apply_shared_services(
                data_service,
                shared_market_service=shared_market_service,
                shared_bot_service=shared_bot_service,
            )
            data_report = data_service.build(
                as_of_ms=args.as_of_ms, only_codes={args.bot} if args.bot else None
            )

        cohort = None
        if needs_cohort:
            # Step 3 ranks what step 2 selected unless asked for the whole dataset.
            only_codes = default_selection_codes(
                data_dir, bot=args.bot, all_bots=args.all_bots
            )
            cohort_service = CohortAssessmentService(evaluation_mode=mode)
            apply_shared_services(
                cohort_service,
                shared_market_service=shared_market_service,
                shared_bot_service=shared_bot_service,
            )
            cohort = cohort_service.scan(
                as_of_ms=args.as_of_ms,
                venue_types=venues,
                seed=args.seed,
                simulation_iterations=args.iterations,
                simulation_horizon=args.horizon,
                only_codes=only_codes,
            )

        pair_report = None
        if needs_pairs:
            pair_service = PairedBotReportService(evaluation_mode=mode)
            apply_shared_services(
                pair_service,
                shared_market_service=shared_market_service,
                shared_bot_service=shared_bot_service,
            )
            pair_report = pair_service.build(
                as_of_ms=args.as_of_ms,
                simulation_iterations=args.iterations,
                simulation_horizon=args.horizon,
                only_codes={args.bot} if args.bot else None,
            )
            if not args.no_write:
                # Step 2's output is step 3's input, so it is written where a person
                # can open one bot and read what the decision was made from.
                written = persist_analysis(pair_report, out_dir)
                print(
                    f"[step 2] wrote {len(written)} analysis files to "
                    f"{out_dir / 'analysis'}",
                    file=sys.stderr,
                )

        if cohort is not None and want in ("qc", "all"):
            # Việc 1/4: fill in what BotEvaluationRow itself cannot carry
            # (phase_breakdown, behavioural flags/scores, the LLM narrative)
            # before persisting -- built even under --no-write, so a
            # single-bot dry run can still be inspected for its narrative
            # (task's own explicit test requirement) without ever touching
            # disk. Runs sequentially with its own per-bot progress/timing
            # output regardless of --report/--json (never pushed to the
            # background -- this project's own crawler-throttle preference).
            extras = build_assessment_extras(
                cohort,
                shared_bot_service,
                generate_narrative_flag=not args.no_narrative,
                reuse_stored_narrative=args.reuse_narrative,
                data_dir=data_dir,
                # Real params (not the historical cheap default) -- see
                # build_assessment_extras/_fetch_bot_for_extras's own
                # docstrings: horizon_scenarios must come from the SAME
                # Monte Carlo settings cohort_service.scan() above just used
                # to score these exact bots.
                simulation_iterations=args.iterations,
                simulation_horizon=args.horizon,
                seed=args.seed,
            )
            # Step 3's verdict has to be readable one bot at a time as well; the
            # ranking table is a view of these files, not the other way round.
            written = persist_assessment(
                cohort, out_dir, extra_by_code=extras, write=not args.no_write
            )
            if args.no_write:
                print(
                    f"[step 3] --no-write: {len(written)} assessment files (with "
                    "strategy/behavioural evidence and narrative if available) "
                    f"were built in memory for {out_dir / 'assessment'} -- NOT "
                    "written to disk",
                    file=sys.stderr,
                )
            else:
                print(
                    f"[step 3] wrote {len(written)} assessment files to "
                    f"{out_dir / 'assessment'}",
                    file=sys.stderr,
                )

        market_report = None
        if needs_market:
            market_service = MarketRegimeService(evaluation_mode=mode)
            apply_shared_services(
                market_service,
                shared_market_service=shared_market_service,
                shared_bot_service=shared_bot_service,
            )
            # Bot count comes from the ledgers, always: deriving it from whichever
            # cohort happened to run made the column mean different things depending
            # on the flags, and showed 0 bots on assets that have a selected pair.
            market_report = market_service.build(
                as_of_ms=args.as_of_ms,
                only_symbols=(
                    {block.symbol for block in pair_report.blocks}
                    if args.bot and pair_report
                    else None
                ),
            )
    except BotSourceError as exc:
        # Only reachable with --source live: a hard OKX failure (bad code,
        # empty ledger+positions, transport error) that the file source never
        # raises. cohort.py/pair_report.py only catch BotDataUnavailableError/
        # ValueError around each bot's own try/except (see their _resolve_market
        # and get_bot_result call sites), so this is the last line of defence
        # against a bare traceback -- it turns one bot's OKX failure into a
        # clear Vietnamese message and a non-zero exit instead of a crash.
        print(
            f"[live] Error fetching bot data directly from OKX: {exc}", file=sys.stderr
        )
        return 1
    except MarketDataUnavailableError as exc:
        # Defensive: every internal call site already catches this (see
        # DataReportService._market_row, MarketRegimeService.build,
        # CohortAssessmentService._resolve_market), so this should never
        # actually fire -- kept only so a future gap in that coverage still
        # degrades to a clear message instead of a traceback.
        print(
            f"[live] Error fetching market data directly from OKX: {exc}",
            file=sys.stderr,
        )
        return 1

    # Proof the sharing/memoisation above actually did something: how many of
    # the calls the four report services made for the same bot/asset+as_of_ms
    # were served from memory instead of asking the source (OKX under
    # --source live, disk under --source file) again.
    print(
        f"[cache] market: {shared_market_service.cache_hits} hits / "
        f"{shared_market_service.cache_calls} get_market_result calls; "
        f"bot: {shared_bot_service.cache_hits} hits / "
        f"{shared_bot_service.cache_calls} get_bot_result calls",
        file=sys.stderr,
    )

    if args.as_json:
        payload: dict = {}
        if data_report is not None:
            payload["data_report"] = data_report.model_dump(mode="json")
        if market_report is not None:
            payload["market_regime_report"] = market_report.model_dump(mode="json")
        if pair_report is not None:
            payload["paired_bot_report"] = pair_report.model_dump(mode="json")
        if cohort is not None:
            payload["cohort_report"] = cohort.model_dump(mode="json")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    blocks = []
    if data_report is not None:
        blocks.append(render_data_report(data_report))
    if market_report is not None:
        blocks.append(render_market_report(market_report, detail=args.detail))
    if pair_report is not None:
        blocks.append(render_pair_report(pair_report, detail=args.detail))
    if cohort is not None and want == "cohort":
        blocks.append(render_bot_report(cohort, detail=args.detail))
    if cohort is not None and want in ("qc", "all"):
        blocks.append(render_qc_ranking(cohort))
    if cohort is not None and want in ("gaps", "all"):
        gaps = render_gaps(cohort)
        if gaps:
            blocks.append(gaps)
    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



def rescore_one_bot_complete(
    data_dir: Path,
    unique_code: str,
    *,
    data_venue: Optional[str] = None,
) -> Optional[str]:
    """Chấm lại MỘT bot ĐẦY ĐỦ -- điểm số, bằng chứng VÀ đoạn nhận định --
    rồi ghi đè `assessment.json` của chính nó. Trả về đường dẫn đã ghi.

    VÌ SAO Ở ĐÂY chứ không ở `assessment_store`: bản trước đặt trong
    assessment_store chỉ chấm lại được ĐIỂM, vì đoạn nhận định cần đối
    tượng `bot` (hồ sơ chiến lược, phân rã theo pha) mà chỉ
    `_fetch_bot_for_extras` dựng ra, và nó sống ở file này cùng
    `_narrative_for_row`. Hệ quả của bản thiếu đó thấy ngay khi đo: bot vừa
    chạy lại có số mới nhưng MẤT đoạn văn cho tới lượt chấm hàng loạt kế
    tiếp -- tức người dùng bấm "Phân tích lại" rồi nhận về một báo cáo
    NGHÈO HƠN trước khi bấm.

    Dùng đúng những mảnh mà lượt chấm hàng loạt dùng (`build_assessment_
    extras` + `assessment_store.persist`), nên một bot chạy lại lẻ và một
    bot trong lượt chấm cả đàn cho ra cùng một hình dạng dữ liệu.
    """
    from Agent.backend.qc.reporting.assessment_store import persist as persist_assessment
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService

    root = Path(data_dir)

    market_service, bot_service = build_shared_services(root, EvaluationMode.SNAPSHOT)
    service = CohortAssessmentService(data_dir=root, persist_history=False)
    apply_shared_services(
        service,
        shared_market_service=market_service,
        shared_bot_service=bot_service,
    )

    # `scan()` duyệt cây data/<venue>/ THẬT. Mọi slot DEX đều do trader OKX
    # lấp và dữ liệu của họ nằm dưới cex/, nên phải thử cả hai thay vì đoán
    # theo venue của slot -- đúng con bug mà `live/poller.py` đã vấp.
    report = row = None
    # Nơi gọi đã biết venue THẬT (poller giải được từ cây dữ liệu) thì dùng
    # luôn, khỏi quét thừa một lượt; không biết thì thử cả hai.
    venues = (data_venue,) if data_venue else ("CEX", "DEX")
    for data_venue in venues:
        report = service.scan(
            venue_types=(data_venue,),
            only_codes={unique_code},
            seed=PRODUCTION_SIMULATION_SEED,
            simulation_iterations=PRODUCTION_SIMULATION_ITERATIONS,
            simulation_horizon=PRODUCTION_SIMULATION_HORIZON,
        )
        row = next(
            (r for r in report.rows if r.unique_code == unique_code and not r.error),
            None,
        )
        if row is not None:
            break
    if row is None or report is None:
        return None

    extras = build_assessment_extras(
        report,
        bot_service,
        generate_narrative_flag=True,
        # Phải TRÙNG với `scan` ngay trên: `horizon_scenarios` sinh ở đây,
        # còn điểm số sinh ở đó -- lệch tham số là hai nửa cùng một báo cáo
        # nói về hai lần mô phỏng khác nhau. Lượt chấm đàn đã làm đúng việc
        # này từ đầu (xem chỗ gọi trong `main`); đường lẻ thì chưa.
        simulation_iterations=PRODUCTION_SIMULATION_ITERATIONS,
        simulation_horizon=PRODUCTION_SIMULATION_HORIZON,
        seed=PRODUCTION_SIMULATION_SEED
    )
    # Giữ thứ hạng: `assessment_store.persist` lo, cho MỌI đường.
    written = persist_assessment(report, root, extra_by_code=extras, write=True)
    return written[0] if written else None
