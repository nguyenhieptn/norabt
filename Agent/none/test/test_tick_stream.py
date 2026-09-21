"""Tests for the windowed tick backfill + streaming aggregator fix.

Diagnosis this addresses (see the task this file was written for): DEX/tick
flow_bias used to be computed from a fixed COUNT of trade prints ("the last
100"), which gives every instrument a different TIME window -- ~2 seconds on
a hot pair, many hours on a quiet one -- while a CEX asset's flow_bias always
covers a fixed 1H bucket. Comparing those numbers side by side compares
apples to oranges. The fix pages by TIME instead of by COUNT
(LiveMarketDataSource.fetch_ticks_windowed, in
Agent/backend/sources/market_source.py) and aggregates in O(1) memory
(TickAggregator, in Agent/backend/market/features/orderflow.py) instead of
holding every tick fetched in a list.

No real network calls anywhere in this file: every OKX interaction goes
through FakeTradesClient below, a stand-in for OkxClient.public_get() that
answers from an in-memory synthetic trade timeline. This mirrors the FakeOkxClient
pattern already used in Agent/none/test/test_market_source.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from Agent.backend.market.features.orderflow import (
    OrderflowFeatureExtractor,
    TickAggregator,
)
from Agent.backend.sources.market_source import CandleCache, LiveMarketDataSource

REPO_ROOT = Path(__file__).resolve().parents[3]
PEPE_TICKS_FIXTURE = (
    REPO_ROOT / "Agent" / "data" / "dex" / "PEPE" / "market" / "ticks_100ms_stream.json"
)


def _no_delay_source(client: Any, **kwargs: Any) -> LiveMarketDataSource:
    kwargs.setdefault("candle_cache", CandleCache(enabled=False))
    kwargs.setdefault("request_delay_seconds", 0.0)
    return LiveMarketDataSource(client=client, **kwargs)


def _make_row(
    idx: int, ts: int, side: str, px: float = 1.0, sz: float = 1.0
) -> Dict[str, Any]:
    return {
        "instId": "TEST-USDT",
        "tradeId": str(idx),
        "px": str(px),
        "sz": str(sz),
        "side": side,
        "ts": str(ts),
    }


def _descending_timeline(
    n: int, *, start_ts: int = 1_800_000_000_000, interval_ms: int = 250
) -> List[Dict[str, Any]]:
    """n trade rows, newest first, `interval_ms` apart -- alternating buy/sell."""
    return [
        _make_row(i, start_ts - i * interval_ms, "buy" if i % 2 == 0 else "sell")
        for i in range(n)
    ]


class FakeTradesClient:
    """Stands in for OkxClient across /market/trades + /market/history-trades.

    Backed by a single descending (newest-first) timeline: the first page
    (path == /market/trades) always returns the newest `limit` rows; every
    later page (path == /market/history-trades) returns the next `limit`
    rows strictly older than the `after` cursor, mirroring OKX's documented
    "after = earlier than this ts" semantics for type=2 pagination.
    """

    def __init__(self, timeline_desc: List[Dict[str, Any]]) -> None:
        self.timeline = timeline_desc
        self.calls: List[tuple] = []

    def public_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        params = dict(params or {})
        self.calls.append((path, params))
        limit = int(params.get("limit", 100))
        if path == "/api/v5/market/trades":
            return self.timeline[:limit]
        if path == "/api/v5/market/history-trades":
            after_ts = int(params["after"])
            assert params.get("type") == "2", "history-trades must use type=2 here"
            older = [r for r in self.timeline if int(r["ts"]) < after_ts]
            return older[:limit]
        raise AssertionError(f"unexpected OKX path requested in test: {path}")


# --------------------------------------------------------------------------- #
# TickAggregator vs from_ticks: must agree byte-for-byte on the same data.
# --------------------------------------------------------------------------- #


def test_tick_aggregator_matches_from_ticks_on_same_data() -> None:
    ticks = json.loads(PEPE_TICKS_FIXTURE.read_text(encoding="utf-8"))["ticks"]
    assert len(ticks) == 100  # sanity: this is the real fixed-count fixture

    via_list = OrderflowFeatureExtractor.from_ticks(ticks)

    agg = TickAggregator()  # no target_window_ms -> coverage_ratio check is skipped
    agg.add_page(ticks)
    via_aggregate = OrderflowFeatureExtractor.from_aggregate(agg)

    assert via_list.taker_buy_vol == pytest.approx(via_aggregate.taker_buy_vol)
    assert via_list.taker_sell_vol == pytest.approx(via_aggregate.taker_sell_vol)
    assert via_list.taker_ratio == pytest.approx(via_aggregate.taker_ratio)
    assert via_list.flow_bias == via_aggregate.flow_bias
    assert via_list.cvd == pytest.approx(via_aggregate.cvd)
    assert via_list.cvd_delta == pytest.approx(via_aggregate.cvd_delta)
    assert via_list.cvd_slope == pytest.approx(via_aggregate.cvd_slope)
    assert via_list.cvd_divergence == via_aggregate.cvd_divergence


def test_tick_aggregator_splitting_into_many_pages_still_matches_from_ticks() -> None:
    """Same data, but folded into the aggregator 10 ticks at a time -- proves
    add_page() is a true fold (order/chunking of pages must not matter)."""
    ticks = json.loads(PEPE_TICKS_FIXTURE.read_text(encoding="utf-8"))["ticks"]
    via_list = OrderflowFeatureExtractor.from_ticks(ticks)

    agg = TickAggregator()
    for start in range(0, len(ticks), 10):
        agg.add_page(ticks[start : start + 10])
    via_aggregate = OrderflowFeatureExtractor.from_aggregate(agg)

    assert via_list.flow_bias == via_aggregate.flow_bias
    assert via_list.taker_buy_vol == pytest.approx(via_aggregate.taker_buy_vol)
    assert via_list.taker_sell_vol == pytest.approx(via_aggregate.taker_sell_vol)


# --------------------------------------------------------------------------- #
# O(1) memory: 100,000 ticks across many pages, aggregator never grows a list.
# --------------------------------------------------------------------------- #


def test_tick_aggregator_is_o1_memory_over_100k_ticks() -> None:
    agg = TickAggregator(target_window_ms=60_000)

    # __slots__ is the structural guarantee: it is a hard error to attach any
    # attribute beyond the fixed set below, so there is no way for a list to
    # sneak onto this object even by accident.
    assert TickAggregator.__slots__ == (
        "buy_notional",
        "sell_notional",
        "tick_count",
        "earliest_ts",
        "latest_ts",
        "pages_added",
        "target_window_ms",
    )
    assert not hasattr(agg, "__dict__")

    size_before = sys.getsizeof(agg)

    total_fed = 0
    n_pages = 1_000
    page_size = 100
    for page_idx in range(n_pages):
        # Each page is a fresh, disposable list -- built, folded in, then
        # eligible for garbage collection immediately. Nothing here is ever
        # retained by `agg`.
        page = [
            _make_row(
                page_idx * page_size + i,
                1_800_000_000_000 - (page_idx * page_size + i),
                "buy" if i % 2 == 0 else "sell",
            )
            for i in range(page_size)
        ]
        agg.add_page(page)
        total_fed += page_size

    assert total_fed == 100_000
    assert agg.tick_count == 100_000
    assert agg.pages_added == n_pages

    # Every attribute is a scalar (or None) -- never a container that could
    # have grown with the 100,000 ticks just fed in.
    for slot in TickAggregator.__slots__:
        value = getattr(agg, slot)
        assert not isinstance(value, (list, dict, tuple, set, frozenset)), (
            f"TickAggregator.{slot} is a container ({type(value)}) -- "
            "memory would scale with tick count, defeating the point of this class"
        )

    size_after = sys.getsizeof(agg)
    # A slotted object's shallow size never depends on the *values* stored in
    # its slots, only on the fixed number of slots -- this is the concrete,
    # measurable proof that ingesting 100,000 ticks left the aggregator's own
    # footprint completely unchanged.
    assert size_after == size_before


# --------------------------------------------------------------------------- #
# Pagination: stops once the configured time window has been covered.
# --------------------------------------------------------------------------- #


def test_pagination_stops_once_window_covered() -> None:
    # 250ms apart -> each 100-row page spans 24,750ms. Three pages span
    # 74,750ms, crossing the 60,000ms default target on the third page.
    timeline = _descending_timeline(1_000, interval_ms=250)
    client = FakeTradesClient(timeline)
    source = _no_delay_source(client)

    agg, stop_reason = source.fetch_ticks_windowed(
        "TEST-USDT", target_window_ms=60_000, max_pages=20, max_wall_seconds=30.0
    )

    assert stop_reason == "window_covered"
    assert agg.window_ms >= 60_000
    assert agg.pages_added == 3
    assert len(client.calls) == 3
    assert client.calls[0][0] == "/api/v5/market/trades"
    assert client.calls[1][0] == "/api/v5/market/history-trades"
    assert client.calls[2][0] == "/api/v5/market/history-trades"
    assert agg.tick_count == 300


# --------------------------------------------------------------------------- #
# Pagination: a hyperactive pair (window never fills fast) is bounded by max_pages.
# --------------------------------------------------------------------------- #


def test_pagination_max_pages_caps_a_runaway_walk() -> None:
    # 1ms apart -> even after many pages the window covered stays tiny
    # relative to the (default 60s) target, so only the page cap can stop it.
    timeline = _descending_timeline(10_000, interval_ms=1)
    client = FakeTradesClient(timeline)
    source = _no_delay_source(client)

    agg, stop_reason = source.fetch_ticks_windowed(
        "TEST-USDT", target_window_ms=60_000, max_pages=5, max_wall_seconds=30.0
    )

    assert stop_reason == "max_pages"
    assert agg.pages_added == 5
    assert len(client.calls) == 5
    assert agg.window_ms < 60_000  # confirms the cap fired before coverage did


def test_pagination_max_wall_seconds_caps_a_runaway_walk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Independent of the page cap: a wall-clock cap also bounds the walk."""
    timeline = _descending_timeline(10_000, interval_ms=1)
    client = FakeTradesClient(timeline)
    source = _no_delay_source(client)

    # Simulate elapsed wall-clock time advancing one full budget per page,
    # without an actual sleep -- keeps the test instant while still
    # exercising the max_wall_seconds branch deterministically.
    fake_now = [0.0]

    def fake_monotonic() -> float:
        fake_now[0] += 100.0
        return fake_now[0]

    import Agent.backend.sources.market_source as market_source_module

    monkeypatch.setattr(market_source_module.time, "monotonic", fake_monotonic)

    agg, stop_reason = source.fetch_ticks_windowed(
        "TEST-USDT", target_window_ms=60_000, max_pages=1_000, max_wall_seconds=30.0
    )

    assert stop_reason == "max_wall_seconds"
    assert agg.pages_added == 1
    assert len(client.calls) == 1


# --------------------------------------------------------------------------- #
# Fail-closed: a too-thin sample must report UNKNOWN with a reason, never a
# fabricated bias.
# --------------------------------------------------------------------------- #


def test_too_few_ticks_returns_unknown_with_reason() -> None:
    # Only 5 trades exist in this instrument's whole simulated history --
    # nowhere near the 20-tick floor, and the walk stops itself ("no more
    # data") well short of the configured window too.
    timeline = _descending_timeline(5, interval_ms=250)
    client = FakeTradesClient(timeline)
    source = _no_delay_source(client)

    agg, stop_reason = source.fetch_ticks_windowed("TEST-USDT", target_window_ms=60_000)

    assert stop_reason == "no_more_data"
    assert agg.tick_count == 5

    reason = OrderflowFeatureExtractor.insufficiency_reason(agg)
    assert reason is not None
    assert "5" in reason  # names the actual (too-low) tick count

    state = OrderflowFeatureExtractor.from_aggregate(agg)
    assert state.flow_bias == "UNKNOWN"
    # Fail-closed means no fabricated volumes either -- from_aggregate must
    # not report a buy/sell split it has no basis to stand behind.
    assert state.taker_buy_vol is None
    assert state.taker_sell_vol is None


def test_short_coverage_relative_to_target_returns_unknown_with_reason() -> None:
    """Enough ticks, but a page/time cap cut the walk off far short of the
    configured window -- the sample describes a much narrower slice of time
    than the caller asked for, so it must not be presented as if it covered
    the full window."""
    timeline = _descending_timeline(10_000, interval_ms=1)
    client = FakeTradesClient(timeline)
    source = _no_delay_source(client)

    # 1 page * 100 ticks * 1ms apart = ~99ms covered, vs a 60,000ms target --
    # comfortably over the 20-tick floor, comfortably under the 50% coverage
    # floor.
    agg, stop_reason = source.fetch_ticks_windowed(
        "TEST-USDT", target_window_ms=60_000, max_pages=1
    )
    assert stop_reason == "max_pages"
    assert agg.tick_count == 100  # well over the 20-tick floor

    reason = OrderflowFeatureExtractor.insufficiency_reason(agg)
    assert reason is not None
    assert "60000" in reason or "60,000" in reason or str(agg.window_ms) in reason

    state = OrderflowFeatureExtractor.from_aggregate(agg)
    assert state.flow_bias == "UNKNOWN"


# --------------------------------------------------------------------------- #
# The window actually covered (and tick/page counts) must be visible to callers.
# --------------------------------------------------------------------------- #


def test_get_ticks_windowed_reports_actual_coverage() -> None:
    timeline = _descending_timeline(1_000, interval_ms=250)
    client = FakeTradesClient(timeline)
    source = _no_delay_source(client)

    payload, error = source.get_ticks_windowed("TEST", "CEX", target_window_ms=60_000)

    assert error is None
    assert payload["target_window_ms"] == 60_000
    assert payload["window_covered_ms"] >= 60_000
    assert payload["tick_count"] == 300
    assert payload["pages_fetched"] == 3
    assert payload["stop_reason"] == "window_covered"
    assert payload["flow_bias_unknown_reason"] is None
    assert payload["earliest_ts"] is not None and payload["latest_ts"] is not None
    assert payload["latest_ts"] > payload["earliest_ts"]


def test_get_ticks_windowed_surfaces_unknown_reason_for_thin_sample() -> None:
    timeline = _descending_timeline(3, interval_ms=250)
    client = FakeTradesClient(timeline)
    source = _no_delay_source(client)

    payload, error = source.get_ticks_windowed("TEST", "CEX", target_window_ms=60_000)

    assert error is None
    assert payload["tick_count"] == 3
    assert payload["flow_bias_unknown_reason"] is not None
    assert (
        OrderflowFeatureExtractor.from_aggregate(
            # Rebuild an aggregator carrying the same totals to double check the
            # payload's reason lines up with what from_aggregate would decide.
            _aggregate_from_payload(payload)
        ).flow_bias
        == "UNKNOWN"
    )


def _aggregate_from_payload(payload: Dict[str, Any]) -> TickAggregator:
    agg = TickAggregator(target_window_ms=payload["target_window_ms"])
    agg.buy_notional = payload["buy_notional_usd"]
    agg.sell_notional = payload["sell_notional_usd"]
    agg.tick_count = payload["tick_count"]
    agg.earliest_ts = payload["earliest_ts"]
    agg.latest_ts = payload["latest_ts"]
    agg.pages_added = payload["pages_fetched"]
    return agg
