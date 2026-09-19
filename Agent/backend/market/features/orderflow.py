from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from Agent.backend.market.schemas.market_result import OrderflowState

# --------------------------------------------------------------------------- #
# Fail-closed thresholds for treating a tick-derived flow_bias as trustworthy.
#
# The underlying problem this guards against: 100 trade prints on a hot pair
# might span ~2 seconds, while the same 100 prints on a quiet pair can span
# many hours. A buy/sell ratio computed from either sample *looks* like the
# same kind of number, but the two describe wildly different observation
# windows and are not comparable -- putting them side by side (or next to a
# CEX taker-flow figure that always covers a fixed hour) silently compares
# apples to oranges. Rather than let a too-thin sample manufacture a
# confident-looking BUY_PRESSURE/SELL_PRESSURE label, both thresholds below
# must be satisfied before from_aggregate() will emit a real bias; otherwise
# it reports UNKNOWN with a stated reason (see insufficiency_reason()).
#
# _MIN_TICKS_FOR_VALID_FLOW = 20: below this, one or two oversized trades (a
# single whale buy, a wash trade) can flip the buy/sell ratio outright -- the
# "sample size" is really "how many independent decisions did we observe",
# and single digits of trades is not enough to call that a distribution.
#
# _MIN_COVERAGE_RATIO_FOR_VALID_FLOW = 0.5: this compares the window a
# pagination walk *actually* covered (TickAggregator.window_ms) against the
# window it was *asked* to cover (TickAggregator.target_window_ms). If a
# safety cap (max pages / max wall-clock seconds, see
# Agent/backend/sources/market_source.py) cuts a backfill off after covering
# only, say, 10% of the requested window, the resulting ratio describes that
# 10%-sized slice, not the full window the caller configured -- presenting it
# with the same confidence as a fully-covered window would reintroduce the
# exact "different windows, same-looking number" bug this module exists to
# fix. 50% is a deliberately simple round-number cutoff: enough slack that a
# pair which finishes just shy of the target (OKX ran out of trades, or the
# walk landed a few pages short) is not needlessly discarded, while still
# rejecting samples that are mostly a page-cap/time-cap artifact rather than
# a real measurement of the configured window.
# --------------------------------------------------------------------------- #
_MIN_TICKS_FOR_VALID_FLOW = 20
_MIN_COVERAGE_RATIO_FOR_VALID_FLOW = 0.5


def _parse_tick_row(
    tick: Dict[str, Any],
) -> Tuple[Optional[float], Optional[str], Optional[int]]:
    """Extract (notional_usd, side, ts_ms) from one raw OKX trade-print dict.

    Shared by from_ticks() (the whole-list path, used by FileMarketDataSource's
    fixed 100-tick files) and TickAggregator.add_page() (the streaming path,
    used by a windowed live backfill) so the two ingestion paths can never
    silently drift apart on what counts as a valid tick -- that shared
    behaviour is exactly what test_tick_stream.py's "both paths agree on the
    same data" test is checking.

    Returns (None, None, ts) style tuples on partial failure rather than
    raising: a single malformed row (bad px/sz, unrecognised side) must not
    abort aggregation of the other 99 rows in the same page.
    """
    try:
        notional: Optional[float] = float(tick.get("px", 0.0)) * float(
            tick.get("sz", 0.0)
        )
    except (TypeError, ValueError):
        notional = None

    side: Optional[str] = str(tick.get("side", "")).strip().lower()
    if side not in ("buy", "sell"):
        side = None

    ts_raw = tick.get("ts")
    try:
        ts: Optional[int] = int(ts_raw) if ts_raw is not None else None
    except (TypeError, ValueError):
        ts = None

    return notional, side, ts


class TickAggregator:
    """Folds a stream of raw trade-print pages into running buy/sell totals.

    Why this exists: a time-windowed live backfill (see
    Agent/backend/sources/market_source.py::LiveMarketDataSource) can walk
    many pages of trades on a busy instrument before it has covered its
    configured time window. Holding every row from every page in a Python
    list just to sum two numbers at the end would mean memory scales with
    however many trades happened to print during that window -- for a very
    liquid pair that list keeps growing for as long as the backfill runs.

    Instead, this class keeps only a fixed handful of scalars: two running
    notional totals, a tick counter, two timestamp bounds, and a page
    counter. `add_page()` folds one page into those scalars and then returns;
    the caller is free to let the page's rows be garbage collected
    immediately (LiveMarketDataSource never keeps a reference to a page past
    the add_page() call that consumed it). Whether the stream backing this
    object is 100 ticks or 100 million, `TickAggregator`'s own memory
    footprint is identical -- a few floats and ints, never a list that grows
    with the input. `__slots__` enforces this at the interpreter level: it
    is a hard error to attach any attribute -- list or otherwise -- beyond
    the fixed set declared below.
    """

    __slots__ = (
        "buy_notional",
        "sell_notional",
        "tick_count",
        "earliest_ts",
        "latest_ts",
        "pages_added",
        "target_window_ms",
    )

    def __init__(self, target_window_ms: Optional[int] = None) -> None:
        self.buy_notional: float = 0.0
        self.sell_notional: float = 0.0
        self.tick_count: int = 0
        self.earliest_ts: Optional[int] = None
        self.latest_ts: Optional[int] = None
        self.pages_added: int = 0
        # Informational only (what window this aggregator was *asked* to
        # cover) -- used solely to compute coverage_ratio below. Storing one
        # more int does not change the O(1)-in-tick-count memory story: this
        # value is fixed at construction time and never grows with input.
        self.target_window_ms = target_window_ms

    def add_page(self, rows: List[Dict[str, Any]]) -> None:
        """Fold one page of raw OKX trade rows into the running totals.

        `rows` is only ever read here, never stored -- once this call
        returns, the caller can drop every reference to `rows` and this
        aggregator's memory footprint will not reflect that page having ever
        existed.
        """
        for row in rows:
            notional, side, ts = _parse_tick_row(row)
            if ts is not None:
                # Track the full time span actually walked over, independent
                # of whether a given row's side/notional was parseable --
                # "how much wall-clock time did this backfill cover" is a
                # property of the pagination walk, not of trade validity.
                self.earliest_ts = (
                    ts if self.earliest_ts is None else min(self.earliest_ts, ts)
                )
                self.latest_ts = (
                    ts if self.latest_ts is None else max(self.latest_ts, ts)
                )
            if notional is None or side is None:
                continue
            if side == "buy":
                self.buy_notional += notional
            else:
                self.sell_notional += notional
            self.tick_count += 1
        self.pages_added += 1

    @property
    def total_notional(self) -> float:
        return self.buy_notional + self.sell_notional

    @property
    def window_ms(self) -> Optional[int]:
        """Time span actually covered so far, or None if no tick had a usable ts."""
        if self.earliest_ts is None or self.latest_ts is None:
            return None
        return self.latest_ts - self.earliest_ts

    @property
    def coverage_ratio(self) -> Optional[float]:
        """window_ms / target_window_ms, or None if no target was configured."""
        if not self.target_window_ms:
            return None
        if self.window_ms is None:
            return 0.0
        return self.window_ms / self.target_window_ms


class OrderflowFeatureExtractor:
    """Normalize taker flow without converting missing evidence to neutral flow."""

    @staticmethod
    def extract(taker_vol_data: Optional[Dict[str, Any]] = None) -> OrderflowState:
        if not taker_vol_data:
            return OrderflowState(flow_bias="UNKNOWN")

        data = taker_vol_data.get("data", taker_vol_data)
        buy = data.get("buy_vol_usd", data.get("buyVol", data.get("taker_buy")))
        sell = data.get("sell_vol_usd", data.get("sellVol", data.get("taker_sell")))
        if buy is None or sell is None:
            return OrderflowState(flow_bias="UNKNOWN")

        buy_vol = max(0.0, float(buy))
        sell_vol = max(0.0, float(sell))
        total = buy_vol + sell_vol
        ratio = float(
            data.get(
                "buy_sell_ratio",
                data.get("taker_ratio", buy_vol / max(1e-12, sell_vol)),
            )
        )
        delta = float(data.get("net_flow_usd", buy_vol - sell_vol))
        slope = delta / total if total else 0.0

        bias = "NEUTRAL"
        if ratio > 1.2:
            bias = "BUY_PRESSURE"
        elif ratio < 0.8:
            bias = "SELL_PRESSURE"

        divergence = "NONE"
        if ratio > 1.3:
            divergence = "BULLISH_CVD_SURGE"
        elif ratio < 0.7:
            divergence = "BEARISH_CVD_SURGE"

        return OrderflowState(
            taker_buy_vol=buy_vol,
            taker_sell_vol=sell_vol,
            taker_ratio=ratio,
            flow_bias=bias,
            cvd=delta,
            cvd_delta=delta,
            cvd_slope=slope,
            cvd_divergence=divergence,
        )

    @staticmethod
    def from_ticks(ticks: List[Dict[str, Any]]) -> OrderflowState:
        """DEX venues publish trade prints, not a taker-volume aggregate.

        Kept exactly as before (byte-for-byte behaviour, just re-expressed
        through the shared _parse_tick_row() helper) for backward
        compatibility: FileMarketDataSource still hands this a fixed
        100-tick list read straight off disk, and that call site must keep
        producing the same OrderflowState it always has -- see
        test_dex_orderflow_is_derived_from_tick_prints in
        Agent/test/test_quality_and_safety.py and the file-source regression
        test in Agent/test/test_tick_stream.py.

        This path deliberately has no fail-closed "too thin" check, unlike
        from_aggregate() below: it has no notion of a target time window to
        compare coverage against (the file's 100 ticks are just "whatever
        the crawl captured"), so there is nothing principled to gate on
        beyond the existing total<=0 check.
        """
        buy_vol = 0.0
        sell_vol = 0.0
        for tick in ticks:
            notional, side, _ts = _parse_tick_row(tick)
            if notional is None or side is None:
                continue
            if side == "buy":
                buy_vol += notional
            else:
                sell_vol += notional
        total = buy_vol + sell_vol
        if total <= 0:
            return OrderflowState(flow_bias="UNKNOWN")

        ratio = buy_vol / sell_vol if sell_vol > 0 else float("inf")
        delta = buy_vol - sell_vol
        bias = "NEUTRAL"
        if ratio > 1.2:
            bias = "BUY_PRESSURE"
        elif ratio < 0.8:
            bias = "SELL_PRESSURE"
        return OrderflowState(
            taker_buy_vol=buy_vol,
            taker_sell_vol=sell_vol,
            taker_ratio=min(ratio, 1e6),
            flow_bias=bias,
            cvd=delta,
            cvd_delta=delta,
            cvd_slope=delta / total,
            cvd_divergence="NONE",
        )

    @staticmethod
    def insufficiency_reason(agg: TickAggregator) -> Optional[str]:
        """Human-readable reason a windowed sample is too thin to trust, or None.

        OrderflowState (Agent/backend/market/schemas/market_result.py) has no
        "reason" field -- it is a fixed pydantic schema shared with the
        CEX/file paths and is intentionally left unchanged by this fix. The
        reason text this returns is meant to travel in the *payload* dict a
        caller builds around the aggregate (see
        LiveMarketDataSource.get_ticks_windowed), not inside OrderflowState
        itself -- exactly the "OrderflowState (hoặc payload tick)" escape
        hatch this fix was scoped to use.
        """
        if agg.tick_count < _MIN_TICKS_FOR_VALID_FLOW:
            return (
                f"only {agg.tick_count} valid ticks aggregated "
                f"(< {_MIN_TICKS_FOR_VALID_FLOW}), too few to infer a reliable "
                "buy/sell bias -- a few large orders could flip the ratio"
            )
        ratio = agg.coverage_ratio
        if ratio is not None and ratio < _MIN_COVERAGE_RATIO_FOR_VALID_FLOW:
            covered = agg.window_ms or 0
            target = agg.target_window_ms or 0
            return (
                f"the actual window only covers {covered}ms while the configured "
                f"target is {target}ms ({ratio:.0%} < "
                f"{_MIN_COVERAGE_RATIO_FOR_VALID_FLOW:.0%}); likely cut short by "
                "a page/time cap, so the data is not representative of the "
                "configured window"
            )
        if agg.total_notional <= 0:
            return "could not aggregate any buy/sell notional from the tick data"
        return None

    @staticmethod
    def from_aggregate(agg: TickAggregator) -> OrderflowState:
        """Same math as from_ticks(), fed from an O(1)-memory TickAggregator.

        This is the streaming counterpart of from_ticks(): instead of a list
        of every tick, it reads only the running totals TickAggregator kept
        while pages were fetched and discarded one at a time (see
        LiveMarketDataSource._fetch_ticks_windowed). On the same underlying
        ticks, both paths must agree byte-for-byte -- test_tick_stream.py
        asserts exactly that by feeding one fixed tick list through
        from_ticks() directly and through TickAggregator + from_aggregate()
        and comparing every field.

        Fail-closed: if the sample is too thin (see insufficiency_reason()
        above) this returns flow_bias="UNKNOWN" rather than a bias computed
        from a handful of trades or a truncated window. The *reason* for
        that UNKNOWN is not carried on OrderflowState (see
        insufficiency_reason()'s docstring) -- callers that need it should
        call insufficiency_reason(agg) themselves, exactly as
        LiveMarketDataSource.get_ticks_windowed does when building its
        payload dict.
        """
        if OrderflowFeatureExtractor.insufficiency_reason(agg) is not None:
            return OrderflowState(flow_bias="UNKNOWN")

        buy_vol, sell_vol = agg.buy_notional, agg.sell_notional
        total = agg.total_notional
        ratio = buy_vol / sell_vol if sell_vol > 0 else float("inf")
        delta = buy_vol - sell_vol
        bias = "NEUTRAL"
        if ratio > 1.2:
            bias = "BUY_PRESSURE"
        elif ratio < 0.8:
            bias = "SELL_PRESSURE"
        return OrderflowState(
            taker_buy_vol=buy_vol,
            taker_sell_vol=sell_vol,
            taker_ratio=min(ratio, 1e6),
            flow_bias=bias,
            cvd=delta,
            cvd_delta=delta,
            cvd_slope=delta / total,
            cvd_divergence="NONE",
        )
