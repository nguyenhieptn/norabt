from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Set, Tuple

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.service import MarketService
from Agent.backend.mcp.service import BotObservationService
from Agent.backend.okx.client import OkxClient
from Agent.backend.qc.reporting.analysis_store import persist as persist_analysis
from Agent.backend.qc.reporting.assessment_store import persist as persist_assessment
from Agent.backend.qc.reporting.cohort import CohortAssessmentService
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
            f"đang gọi OKX ({what})...",
            file=sys.stderr,
        )

    def get_overview(self, unique_code, bot_dir=None):
        self._mark(unique_code, "overview/profile")
        return self._inner.get_overview(unique_code, bot_dir)

    def get_ledger(self, unique_code, bot_dir=None):
        self._mark(unique_code, "sổ lệnh")
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
            f"  [live market #{self._seen[symbol]}] {symbol}: đang gọi OKX ({what})...",
            file=sys.stderr,
        )

    def resolve_venue(self, symbol, venue_type):
        return self._inner.resolve_venue(symbol, venue_type)

    def get_candles(self, symbol, venue_type):
        self._mark(symbol, "nến")
        return self._inner.get_candles(symbol, venue_type)

    def get_orderbook(self, symbol, venue_type):
        self._mark(symbol, "sổ lệnh")
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
        self._mark(symbol, "macro (nến BTC)")
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Đánh giá toàn bộ bot trong dataset và xếp hạng theo rủi ro"
    )
    parser.add_argument(
        "--venue",
        choices=("CEX", "DEX", "ALL"),
        default="ALL",
        help="Phạm vi venue cần quét",
    )
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument(
        "--horizon",
        type=int,
        default=None,
        help=(
            "số lệnh mỗi kịch bản Monte Carlo; bỏ trống thì dùng đúng số lệnh "
            "của chính bot, vì đó là quãng đời đã quan sát được"
        ),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--as-of-ms",
        type=int,
        default=None,
        help="Đồng hồ đánh giá cho replay xác định",
    )
    parser.add_argument(
        "--mode",
        choices=("SNAPSHOT", "LIVE"),
        default="SNAPSHOT",
        help="SNAPSHOT: chấm freshness theo mốc dataset crawl",
    )
    parser.add_argument(
        "--report",
        choices=("data", "market", "bot", "cohort", "qc", "gaps", "all"),
        default="all",
        help=(
            "data = bước 1 (kiểm kê dữ liệu market + bot), "
            "market/bot = hai phần của bước 2 (phân tích market và phân tích bot), "
            "qc = bước 3, cohort = danh sách phẳng mọi bot đã crawl, all = cả ba bước"
        ),
    )
    parser.add_argument(
        "--all-bots",
        action="store_true",
        help=("chấm mọi bot đã crawl thay vì đúng 30 bot bước 2 đã chọn"),
    )
    parser.add_argument(
        "--bot",
        help=(
            "chỉ chạy đúng một bot theo uniqueCode; bước 1 và 2 thu hẹp về asset "
            "của bot đó, bước 3 chỉ chấm bot đó"
        ),
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="không ghi kết quả bước 2/3 xuống data/analysis và data/assessment",
    )
    parser.add_argument(
        "--source",
        choices=("file", "live"),
        default="file",
        help=(
            "file (mặc định) = đọc dữ liệu đã crawl sẵn dưới data/, không đổi "
            "hành vi cũ; live = đọc thẳng OKX qua LiveBotDataSource/"
            "LiveMarketDataSource, không ghi gì xuống data/cex hay data/dex"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help=(
            "nơi ghi output bước 2/3 (data/analysis, data/assessment); mặc "
            "định giữ nguyên bên trong data/ -- đổi giá trị này khi chạy "
            "--source live để khỏi đè lên kết quả của đường file, phục vụ "
            "run_compare.py so sánh hai đường"
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
            "[nguồn] LIVE — đọc thẳng OKX qua LiveBotDataSource/"
            "LiveMarketDataSource, không dùng file đã crawl sẵn",
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
                    f"[bước 2] đã ghi {len(written)} file phân tích vào "
                    f"{out_dir / 'analysis'}",
                    file=sys.stderr,
                )

        if cohort is not None and want in ("qc", "all") and not args.no_write:
            # Step 3's verdict has to be readable one bot at a time as well; the
            # ranking table is a view of these files, not the other way round.
            written = persist_assessment(cohort, out_dir)
            print(
                f"[bước 3] đã ghi {len(written)} file đánh giá vào "
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
            f"[live] Lỗi khi lấy dữ liệu bot trực tiếp từ OKX: {exc}", file=sys.stderr
        )
        return 1
    except MarketDataUnavailableError as exc:
        # Defensive: every internal call site already catches this (see
        # DataReportService._market_row, MarketRegimeService.build,
        # CohortAssessmentService._resolve_market), so this should never
        # actually fire -- kept only so a future gap in that coverage still
        # degrades to a clear message instead of a traceback.
        print(
            f"[live] Lỗi khi lấy dữ liệu thị trường trực tiếp từ OKX: {exc}",
            file=sys.stderr,
        )
        return 1

    # Proof the sharing/memoisation above actually did something: how many of
    # the calls the four report services made for the same bot/asset+as_of_ms
    # were served from memory instead of asking the source (OKX under
    # --source live, disk under --source file) again.
    print(
        f"[cache] market: {shared_market_service.cache_hits} trúng / "
        f"{shared_market_service.cache_calls} lượt gọi get_market_result; "
        f"bot: {shared_bot_service.cache_hits} trúng / "
        f"{shared_bot_service.cache_calls} lượt gọi get_bot_result",
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
