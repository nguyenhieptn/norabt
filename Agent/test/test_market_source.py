"""Tests for the file/live market data source abstraction.

No real network calls: every OKX interaction goes through FakeOkxClient, a stand-in
for OkxClient.public_get() that answers from a table the test supplies and records
every call made against it. See Agent/backend/sources/market_source.py for the
abstraction itself and the design rationale (immutable-candle caching, fail-closed
OKX errors, opt-in DEX support). Live DEX-specific coverage (dex_registry.py,
get_ticks/get_pool_liquidity/get_token_security, select_pool) lives in
Agent/test/test_dex_source.py; this file keeps the CEX-path tests plus the
handful of DEX-adjacent regressions that touch code shared with CEX (resolve_venue,
get_candles's wrapped-underlying lookup).
"""

from __future__ import annotations

import inspect
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

import Agent.backend.sources.market_source as market_source
from Agent.backend.market.features import structure as structure_module
from Agent.backend.market.features.liquidity import LiquidityFeatureExtractor
from Agent.backend.market.features.orderflow import OrderflowFeatureExtractor
from Agent.backend.market.features.structure import StructureFeatureExtractor
from Agent.backend.mcp.analytics.strategy.phases import build_timeline
from Agent.backend.okx.client import OkxApiError
from Agent.backend.sources.market_source import (
    AdaptiveThrottle,
    CandleCache,
    FileMarketDataSource,
    LiveMarketDataSource,
    MarketDataUnavailableError,
)

_BAR_MS = market_source._BAR_MS
BASE_TS = 1_700_000_000_000  # arbitrary fixed hour boundary, not tied to "now"


class FakeOkxClient:
    """Stands in for OkxClient: routes by request path, records every call made.

    `routes` maps a request path to either a fixed value or a `callable(params)`
    that computes one. An unmapped path raises immediately, so a test can never
    accidentally pass because some *other* untested endpoint silently answered.
    """

    def __init__(self, routes: Dict[str, Any]) -> None:
        self.routes = routes
        self.calls: List[Tuple[str, Dict[str, Any]]] = []

    def public_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self.calls.append((path, dict(params or {})))
        if path not in self.routes:
            raise AssertionError(f"unexpected OKX path requested in test: {path}")
        handler = self.routes[path]
        return handler(params or {}) if callable(handler) else handler


_CT_VALS = {
    "ADA-USDT-SWAP": "100",
    "XRP-USDT-SWAP": "100",
    "DOGE-USDT-SWAP": "1000",
    "BTC-USDT-SWAP": "0.01",
}


def _instruments_handler(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"ctVal": _CT_VALS[params["instId"]]}]


def _row(
    ts: int, o: float, hi: float, lo: float, c: float, confirm: str = "1"
) -> List[Any]:
    """One OKX candle row: [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]."""
    return [ts, o, hi, lo, c, 1.0, 1.0, 1.0, confirm]


def _no_delay_source(client: Any, **kwargs: Any) -> LiveMarketDataSource:
    kwargs.setdefault("candle_cache", CandleCache(enabled=False))
    kwargs.setdefault("request_delay_seconds", 0.0)
    # Every pre-existing test in this file (and in the sibling test files
    # test_dex_source.py / test_tick_stream.py this task must not touch) uses
    # a helper exactly like this one to mean "no throttling at all, this is a
    # fake client" -- adaptive pacing is an orthogonal feature under test
    # only in the dedicated AdaptiveThrottle tests below, so it stays off
    # here to keep every other test's timing (and page-count assertions)
    # byte-for-byte what they were before Việc 2 existed.
    kwargs.setdefault("adaptive_throttle", False)
    return LiveMarketDataSource(client=client, **kwargs)


# --------------------------------------------------------------------------- #
# FileMarketDataSource: behaviour must be unchanged from the pre-abstraction code.
# --------------------------------------------------------------------------- #


def test_file_source_reads_existing_files_and_resolves_venue(tmp_path: Path) -> None:
    market_dir = tmp_path / "cex" / "BTC" / "market"
    market_dir.mkdir(parents=True)
    candles_payload = {"candles": [{"timestamp": 1, "close": 100.0}], "exchange": "OKX"}
    (market_dir / "ohlcv_1h_2023_present.json").write_text(json.dumps(candles_payload))
    orderbook_payload = {"bids": [["100", "1", "5"]], "asks": [["101", "1", "5"]]}
    (market_dir / "orderbook_l2.json").write_text(json.dumps(orderbook_payload))

    source = FileMarketDataSource(tmp_path)
    assert source.resolve_venue("BTC", None) == "CEX"

    payload, error = source.get_candles("BTC", "CEX")
    assert error is None
    assert payload == candles_payload

    payload, error = source.get_orderbook("BTC", "CEX")
    assert error is None
    assert payload == orderbook_payload

    # A file that was never collected is tolerated (matches the original
    # _read_json contract), not an error -- MarketService grades this MISSING.
    payload, error = source.get_sentiment("BTC", "CEX")
    assert payload == {}
    assert error == "file not found"


def test_file_source_missing_asset_raises_market_data_unavailable(
    tmp_path: Path,
) -> None:
    source = FileMarketDataSource(tmp_path)
    with pytest.raises(MarketDataUnavailableError):
        source.resolve_venue("ZZZNOPE", None)


def test_file_source_rejects_bad_venue_type(tmp_path: Path) -> None:
    source = FileMarketDataSource(tmp_path)
    with pytest.raises(ValueError):
        source.resolve_venue("BTC", "SPOT")


# --------------------------------------------------------------------------- #
# Key parity: LiveMarketDataSource must answer every key FileMarketDataSource does
# for a CEX asset, or a field would silently go missing under a live rollout.
# --------------------------------------------------------------------------- #


def _write_cex_fixture(tmp_path: Path) -> FileMarketDataSource:
    market_dir = tmp_path / "cex" / "BTC" / "market"
    market_dir.mkdir(parents=True)
    (market_dir / "orderbook_l2.json").write_text(
        json.dumps(
            {
                "symbol": "BTC-USDT-SWAP",
                "timestamp": 1,
                "source": "s",
                "contract_size": 0.01,
                "size_unit": "BASE_COIN",
                "bids": [["100", "1", "1"]],
                "asks": [["101", "1", "1"]],
            }
        )
    )
    (market_dir / "delta_oi_BTC-USDT-SWAP.json").write_text(
        json.dumps(
            {
                "name": "n",
                "updated_at": 1,
                "source": "s",
                "basis": "INSTRUMENT_LEVEL",
                "data": {
                    "symbol": "s",
                    "period": "5m",
                    "current_oi_usd": 1,
                    "prev_oi_usd": 1,
                    "delta_oi_usd": 0,
                    "delta_oi_pct": 0.0,
                    "sigma_oi": 0.0,
                    "zscore": None,
                    "sample_size": 1,
                    "is_liquidity_buildup": False,
                    "buildup_type": "NONE",
                    "updated_at": 1,
                },
            }
        )
    )
    (market_dir / "taker_volume_BTC.json").write_text(
        json.dumps(
            {
                "name": "n",
                "updated_at": 1,
                "source": "s",
                "basis": "INSTRUMENT_LEVEL",
                "unit": "USD",
                "bucket_complete": True,
                "data": {
                    "ccy": "BTC",
                    "symbol": "s",
                    "period": "1H",
                    "buy_vol_usd": 1,
                    "sell_vol_usd": 1,
                    "total_vol_usd": 2,
                    "buy_sell_ratio": 1.0,
                    "net_flow_usd": 0.0,
                    "flow_sentiment": "x",
                    "contract_size": 0.01,
                    "reference_price": 1.0,
                    "updated_at": 1,
                },
            }
        )
    )
    (market_dir / "sentiment_BTC.json").write_text(
        json.dumps(
            {
                "symbol": "s",
                "updated_at": 1,
                "source": "s",
                "basis": "INSTRUMENT_LEVEL",
                "sentiment": {
                    "symbol": "s",
                    "base_ccy": "BTC",
                    "ls_ratio": "1.0",
                    "sentiment_label": "x",
                    "funding_rate": "x",
                    "next_funding_time": "1",
                    "open_interest_usd": 1.0,
                    "updated_at": 1,
                },
            }
        )
    )
    (market_dir / "ohlcv_1h_2023_present.json").write_text(
        json.dumps(
            {
                "source": "s",
                "endpoint": "e",
                "exchange": "OKX",
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "bar": "1H",
                "period_start": "a",
                "period_end": "b",
                "total_candles": 1,
                "candles": [
                    {
                        "timestamp": 1,
                        "datetime": "x",
                        "open": 1,
                        "high": 1,
                        "low": 1,
                        "close": 1,
                        "vol": 1,
                        "volCcy": 1,
                        "volCcyQuote": 1,
                    }
                ],
            }
        )
    )
    return FileMarketDataSource(tmp_path)


def _fully_mocked_live_source() -> LiveMarketDataSource:
    now = int(time.time() * 1000)
    client = FakeOkxClient(
        {
            "/api/v5/public/instruments": _instruments_handler,
            "/api/v5/market/books": lambda p: [
                {
                    "bids": [["100", "1", "0", "1"]],
                    "asks": [["101", "1", "0", "1"]],
                    "ts": "1",
                }
            ],
            "/api/v5/rubik/stat/contracts/open-interest-history": [
                [str(i), "1", "1", str(100.0 + i)] for i in range(5)
            ],
            "/api/v5/rubik/stat/taker-volume-contract": [
                [str(now - 2 * _BAR_MS), "1", "1"]
            ],
            "/api/v5/market/ticker": [{"last": "100"}],
            "/api/v5/rubik/stat/contracts/long-short-account-ratio": [["1", "1.5"]],
            "/api/v5/public/funding-rate": [
                {"fundingRate": "0.0001", "nextFundingTime": "1"}
            ],
            "/api/v5/public/open-interest": [{"oiUsd": "1"}],
            "/api/v5/market/candles": [_row(BASE_TS, 1, 1, 1, 1)],
            "/api/v5/market/history-candles": [],
        }
    )
    return _no_delay_source(client)


@pytest.mark.parametrize(
    "getter",
    ["get_orderbook", "get_open_interest", "get_taker_volume", "get_sentiment"],
)
def test_live_source_has_every_key_file_source_has(tmp_path: Path, getter: str) -> None:
    file_source = _write_cex_fixture(tmp_path)
    live_source = _fully_mocked_live_source()

    file_payload, file_error = getattr(file_source, getter)("BTC", "CEX")
    live_payload, live_error = getattr(live_source, getter)("BTC", "CEX")
    assert file_error is None
    assert live_error is None

    missing = set(file_payload) - set(live_payload)
    assert not missing, f"{getter}: live is missing top-level keys {missing}"

    for nested_key in ("data", "sentiment"):
        if nested_key in file_payload:
            nested_missing = set(file_payload[nested_key]) - set(
                live_payload.get(nested_key, {})
            )
            assert not nested_missing, (
                f"{getter}.{nested_key}: live missing {nested_missing}"
            )


def test_live_candles_has_every_key_file_candles_has(tmp_path: Path) -> None:
    file_source = _write_cex_fixture(tmp_path)
    file_payload, file_error = file_source.get_candles("BTC", "CEX")
    assert file_error is None

    client = FakeOkxClient(
        {
            "/api/v5/market/candles": [_row(BASE_TS, 1, 1, 1, 1)],
            "/api/v5/market/history-candles": [],
        }
    )
    live_source = _no_delay_source(client)
    live_payload, live_error = live_source.get_candles("BTC", "CEX")
    assert live_error is None

    missing = set(file_payload) - set(live_payload)
    assert not missing, f"live candles payload missing {missing}"
    assert set(file_payload["candles"][0]) == set(live_payload["candles"][0])


@pytest.mark.parametrize(
    "symbol,expected_inst_id",
    [
        ("BTC", "BTC-USDT-SWAP"),  # ordinary CEX asset: unaffected, maps to itself
        ("ADA", "ADA-USDT-SWAP"),  # another ordinary CEX asset: unaffected
        ("WBTC", "BTC-USDT-SWAP"),  # wrapped DEX asset: must unwrap to its underlying
        ("WETH", "ETH-USDT-SWAP"),  # wrapped DEX asset: must unwrap to its underlying
    ],
)
def test_get_candles_resolves_wrapped_underlying_without_touching_cex(
    symbol: str, expected_inst_id: str
) -> None:
    """get_candles() must query the underlying's OKX instrument for a wrapped
    DEX asset (there is no "WBTC-USDT-SWAP" on OKX -- see dex_registry.py's
    WRAPPED_UNDERLYING), while leaving every ordinary CEX symbol's instId
    exactly as before this lookup was added (WRAPPED_UNDERLYING's only keys
    are WBTC/WETH, neither a CEX ticker)."""

    def candles_handler(params: Dict[str, Any]) -> List[Any]:
        assert params["instId"] == expected_inst_id
        return [_row(BASE_TS, 1, 1, 1, 1)]

    client = FakeOkxClient(
        {
            "/api/v5/market/candles": candles_handler,
            "/api/v5/market/history-candles": [],
        }
    )
    source = _no_delay_source(client)
    payload, error = source.get_candles(symbol, "CEX")
    assert error is None
    assert payload["instId"] == expected_inst_id


def test_live_macro_context_has_every_key_file_macro_context_has(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The real 200-candle/720h overlap requirement is not worth simulating for
    # a unit test; only the threshold is lowered, the correlation math itself
    # is exercised for real against small synthetic series.
    monkeypatch.setattr(market_source, "_MACRO_MIN_OVERLAP", 3)

    btc_closes = {BASE_TS + i * _BAR_MS: 100.0 + i for i in range(6)}
    asset_closes = {BASE_TS + i * _BAR_MS: 10.0 + i * 0.5 for i in range(6)}

    def fake_get_candles(symbol: str, venue_type: str):
        closes = btc_closes if symbol == "BTC" else asset_closes
        candles = [
            {"timestamp": ts, "close": close} for ts, close in sorted(closes.items())
        ]
        return {"candles": candles}, None

    live_source = _no_delay_source(FakeOkxClient({}))
    monkeypatch.setattr(live_source, "get_candles", fake_get_candles)

    payload, error = live_source.get_macro_context("ADA", "CEX")
    assert error is None
    # Real on-disk shape, per Agent/data/cex/BTC/market/macro_context.json.
    expected_top = {
        "asset",
        "venue",
        "source",
        "reference",
        "observed_at",
        "updated_at",
        "window_hours",
        "sample_size",
        "macro",
    }
    expected_macro = {
        "btc_correlation",
        "btc_beta",
        "macro_regime",
        "reference_trend_pct",
        "reference_annualised_vol_pct",
        "macro_event_risk",
    }
    assert expected_top - set(payload) == set()
    assert expected_macro - set(payload["macro"]) == set()


# --------------------------------------------------------------------------- #
# ctVal: ADA/XRP=100, DOGE=1000, BTC=0.01 -- get it wrong and depth reads 100x off.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "symbol,ct_val", [("ADA", 100.0), ("XRP", 100.0), ("DOGE", 1000.0), ("BTC", 0.01)]
)
def test_ct_val_applied_correctly_to_orderbook_sizes(
    symbol: str, ct_val: float
) -> None:
    client = FakeOkxClient(
        {
            "/api/v5/public/instruments": _instruments_handler,
            "/api/v5/market/books": lambda p: [
                {
                    "bids": [["100", "2", "0", "1"]],  # 2 CONTRACTS
                    "asks": [["101", "3", "0", "1"]],  # 3 CONTRACTS
                    "ts": "1",
                }
            ],
        }
    )
    source = _no_delay_source(client)
    payload, error = source.get_orderbook(symbol, "CEX")
    assert error is None
    assert payload["contract_size"] == ct_val
    assert float(payload["bids"][0][1]) == pytest.approx(2.0 * ct_val)
    assert float(payload["asks"][0][1]) == pytest.approx(3.0 * ct_val)


# --------------------------------------------------------------------------- #
# Taker volume: contracts -> coins -> USD once, sell/buy columns not swapped.
# --------------------------------------------------------------------------- #


def test_taker_volume_is_not_double_priced_and_not_swapped() -> None:
    now = int(time.time() * 1000)
    closed_ts = now - 2 * _BAR_MS
    client = FakeOkxClient(
        {
            "/api/v5/public/instruments": _instruments_handler,
            # [ts, sellVol=10 contracts, buyVol=20 contracts]
            "/api/v5/rubik/stat/taker-volume-contract": [[str(closed_ts), "10", "20"]],
            "/api/v5/market/ticker": [{"last": "50000"}],
        }
    )
    source = _no_delay_source(client)
    payload, error = source.get_taker_volume("BTC", "CEX")
    assert error is None
    data = payload["data"]
    # ctVal(BTC)=0.01, price=50000 -> sell=10*0.01*50000=5,000 buy=20*0.01*50000=10,000.
    # If the row were treated as already-USD (no ctVal/price conversion) these
    # would read 10 and 20; if swapped, sell_vol_usd would exceed buy_vol_usd.
    assert data["sell_vol_usd"] == pytest.approx(5_000.0)
    assert data["buy_vol_usd"] == pytest.approx(10_000.0)
    assert data["net_flow_usd"] == pytest.approx(5_000.0)


def test_taker_volume_rejects_still_open_bucket() -> None:
    """The most recent hour is still accumulating trades; using it would report
    a partial-hour volume as if it were the full hour's flow."""
    now = int(time.time() * 1000)
    still_open_ts = now - 100  # closes in the future relative to "now"
    client = FakeOkxClient(
        {
            "/api/v5/public/instruments": _instruments_handler,
            "/api/v5/rubik/stat/taker-volume-contract": [
                [str(still_open_ts), "1", "1"]
            ],
            "/api/v5/market/ticker": [{"last": "1"}],
        }
    )
    source = _no_delay_source(client)
    with pytest.raises(MarketDataUnavailableError):
        source.get_taker_volume("BTC", "CEX")


# --------------------------------------------------------------------------- #
# Depth must anchor on the book's own mid, not the (potentially stale) candle close.
# --------------------------------------------------------------------------- #


def test_orderbook_depth_anchors_on_book_mid_not_candle_close() -> None:
    client = FakeOkxClient(
        {
            "/api/v5/public/instruments": _instruments_handler,
            "/api/v5/market/books": lambda p: [
                {
                    "bids": [["1000", "10", "0", "1"]],
                    "asks": [["1002", "10", "0", "1"]],
                    "ts": "1",
                }
            ],
        }
    )
    source = _no_delay_source(client)
    payload, _ = source.get_orderbook("BTC", "CEX")

    # A candle close wildly different from the book: if depth were anchored on
    # it instead of the book's own (bid+ask)/2, every level would fall outside
    # the +/-0.2% band and total depth would read 0 -- the exact
    # everything-reads-ILLIQUID bug this project hit before the book-mid fix.
    far_off_close = 50.0
    state = LiquidityFeatureExtractor.extract(payload, last_price=far_off_close)
    assert state.total_depth_02_usd > 0
    assert state.bid_depth_02_usd > 0
    assert state.ask_depth_02_usd > 0


# --------------------------------------------------------------------------- #
# Candle cache: closed candles persist and are not re-fetched; the open one never is.
# --------------------------------------------------------------------------- #


def test_cache_second_call_fetches_only_the_tail(tmp_path: Path) -> None:
    cache = CandleCache(cache_dir=tmp_path / "cache", enabled=True)
    rows = [_row(BASE_TS + i * _BAR_MS, 1, 1, 1, 1, confirm="1") for i in range(5)]
    rows.append(_row(BASE_TS + 5 * _BAR_MS, 1, 1, 1, 1, confirm="0"))
    client = FakeOkxClient(
        {"/api/v5/market/candles": rows, "/api/v5/market/history-candles": []}
    )
    source = _no_delay_source(client, candle_cache=cache)

    source.get_candles("BTC", "CEX")
    calls_after_first = len(client.calls)
    assert calls_after_first == 1  # one page: fewer rows than page_size ends pagination

    source.get_candles("BTC", "CEX")
    calls_after_second = len(client.calls) - calls_after_first
    # The historical part (5 closed candles) is already cached; only a tail
    # probe is issued, not a full re-walk of history.
    assert calls_after_second == 1


def test_unclosed_candle_is_not_persisted_to_cache(tmp_path: Path) -> None:
    cache = CandleCache(cache_dir=tmp_path / "cache", enabled=True)
    rows = [_row(BASE_TS + i * _BAR_MS, 1, 1, 1, 1, confirm="1") for i in range(3)]
    rows.append(_row(BASE_TS + 3 * _BAR_MS, 1, 1, 1, 1, confirm="0"))
    client = FakeOkxClient(
        {"/api/v5/market/candles": rows, "/api/v5/market/history-candles": []}
    )
    source = _no_delay_source(client, candle_cache=cache)

    payload, error = source.get_candles("BTC", "CEX")
    assert error is None
    assert len(payload["candles"]) == 4  # 3 closed + the still-open one, for THIS call

    cached = cache.load("BTC-USDT-SWAP", "1H")
    assert len(cached) == 3  # the open candle must never reach the cache file
    assert max(c["timestamp"] for c in cached) == BASE_TS + 2 * _BAR_MS


def test_zero_cache_mode_never_touches_cache_dir(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = CandleCache(cache_dir=cache_dir, enabled=False)
    rows = [_row(BASE_TS, 1, 1, 1, 1, confirm="1")]
    client = FakeOkxClient(
        {"/api/v5/market/candles": rows, "/api/v5/market/history-candles": []}
    )
    source = _no_delay_source(client, candle_cache=cache)
    source.get_candles("BTC", "CEX")
    assert not cache_dir.exists()


# --------------------------------------------------------------------------- #
# Fail-closed: an OKX failure must raise, never degrade to an empty payload.
# --------------------------------------------------------------------------- #


class _BoomClient:
    def public_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        raise OkxApiError("50001", "simulated OKX failure")


def test_okx_error_raises_instead_of_returning_empty_payload() -> None:
    source = _no_delay_source(_BoomClient())
    with pytest.raises(MarketDataUnavailableError):
        source.get_orderbook("BTC", "CEX")
    with pytest.raises(MarketDataUnavailableError):
        source.get_candles("BTC", "CEX")
    with pytest.raises(MarketDataUnavailableError):
        source.get_open_interest("BTC", "CEX")


def test_resolve_venue_dex_is_out_of_scope_for_live_source() -> None:
    # This pins the DEFAULT-unconfigured behaviour, unchanged from before DEX
    # support existed: `dex_registry` defaults to None, so any DEX request
    # still raises exactly as it always has (existing callers -- e.g.
    # Agent/test/test_run_compare.py's `LiveMarketDataSource()` -- keep
    # working unmodified). See Agent/test/test_dex_source.py for the
    # opt-in-and-succeeds path (`dex_registry=DEX_ASSET_REGISTRY`) and every
    # other DEX-specific behaviour this class now supports.
    source = _no_delay_source(FakeOkxClient({}))
    with pytest.raises(MarketDataUnavailableError):
        source.resolve_venue("PEPE", "DEX")


# --------------------------------------------------------------------------- #
# Cache writes are atomic: a crash mid-write must leave the previous cache intact.
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# File-source tick regression: the fixed-count 100-tick file path must keep
# producing exactly the result it always has. The windowed live tick fetch
# added alongside this test (LiveMarketDataSource.fetch_ticks_windowed /
# get_ticks_windowed, see Agent/test/test_tick_stream.py) is new,
# additive surface -- it must not have changed a single number this path
# already produced.
# --------------------------------------------------------------------------- #


def test_file_source_ticks_and_from_ticks_are_unchanged() -> None:
    repo_root = Path(__file__).resolve().parents[2]  # .../norabt
    data_dir = repo_root / "Agent" / "data"
    assert (data_dir / "dex" / "PEPE" / "market" / "ticks_100ms_stream.json").exists()

    source = FileMarketDataSource(data_dir)
    payload, error = source.get_ticks("PEPE", "DEX")
    assert error is None
    ticks = payload["ticks"]
    assert len(ticks) == 100  # this file source's whole contract: fixed count

    state = OrderflowFeatureExtractor.from_ticks(ticks)
    # Independently-computed expected values (plain re-implementation of the
    # pre-existing formula, not calling any product code) for this exact
    # fixture file -- pins the historical behaviour so a future change to
    # from_ticks()/​_parse_tick_row() cannot silently drift it.
    buy = sell = 0.0
    for tick in ticks:
        try:
            notional = float(tick.get("px", 0.0)) * float(tick.get("sz", 0.0))
        except (TypeError, ValueError):
            continue
        side = str(tick.get("side", "")).strip().lower()
        if side == "buy":
            buy += notional
        elif side == "sell":
            sell += notional
    total = buy + sell
    expected_ratio = buy / sell if sell > 0 else float("inf")
    expected_delta = buy - sell

    assert state.taker_buy_vol == pytest.approx(buy)
    assert state.taker_sell_vol == pytest.approx(sell)
    assert state.taker_ratio == pytest.approx(min(expected_ratio, 1e6))
    assert state.flow_bias == "BUY_PRESSURE"  # this fixture is buy-heavy
    assert state.cvd == pytest.approx(expected_delta)
    assert state.cvd_delta == pytest.approx(expected_delta)
    assert state.cvd_slope == pytest.approx(expected_delta / total)
    assert state.cvd_divergence == "NONE"
    # Values pinned from the fixture as it exists on disk today -- if this
    # ever fails because the fixture file changed, that is real drift worth
    # noticing, not a false alarm.
    assert buy == pytest.approx(8672.668444977002)
    assert sell == pytest.approx(3814.4924673359997)


def test_cache_write_is_atomic_old_cache_survives_a_crash_midwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = CandleCache(cache_dir=tmp_path, enabled=True)
    good = [
        {
            "timestamp": 1,
            "datetime": "x",
            "open": 1,
            "high": 1,
            "low": 1,
            "close": 1,
            "vol": 1,
            "volCcy": 1,
            "volCcyQuote": 1,
        }
    ]
    cache.save("BTC-USDT-SWAP", "1H", good)
    cache_path = tmp_path / "BTC-USDT-SWAP_1H.json"
    original_bytes = cache_path.read_bytes()

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(market_source.os, "replace", boom)
    with pytest.raises(OSError):
        cache.save("BTC-USDT-SWAP", "1H", good + [{**good[0], "timestamp": 2}])

    assert cache_path.read_bytes() == original_bytes


# --------------------------------------------------------------------------- #
# Việc 1 -- history-depth limiting must not change analysis results. This is
# the load-bearing test group: every speedup this task makes only matters if
# these pass, so it gets more scrutiny than a typical unit test (many random
# price paths, not one; an explicit "cut too aggressively -> results actually
# change" control to prove the main test is not vacuous).
# --------------------------------------------------------------------------- #


def _synthetic_candles(
    seed: int, count: int, start_ts: int = BASE_TS
) -> List[Dict[str, Any]]:
    """A plausible-looking 1H candle series for exercising StructureFeatureExtractor
    / build_timeline -- not tied to any real asset, just needs realistic-looking
    variance so EMA/ATR/percentile-rank computations are non-degenerate (a flat
    price series would make every trend/volatility comparison a tie, hiding
    exactly the truncation-sensitivity this test group needs to exercise)."""
    rng = random.Random(seed)
    price = 100.0
    candles = []
    for i in range(count):
        price = max(1.0, price * (1 + rng.gauss(0, 0.012)))
        high = price * (1 + abs(rng.gauss(0, 0.004)))
        low = price * (1 - abs(rng.gauss(0, 0.004)))
        candles.append(
            {
                "timestamp": start_ts + i * _BAR_MS,
                "close": price,
                "high": high,
                "low": low,
            }
        )
    return candles


def test_structure_lookback_assumption_still_holds() -> None:
    """Pins the exact literal (`candles_1h[-300:]`) market_source.py's warmup
    -buffer formula (_STRUCTURE_MAX_LOOKBACK_HOURS) copied out of
    structure.py. If structure.py's own internal lookback window ever
    changes, this must fail HERE, not silently invalidate the depth formula
    in market_source.py."""
    source = inspect.getsource(structure_module)
    needle = f"candles_1h[-{market_source._STRUCTURE_MAX_LOOKBACK_HOURS}:]"
    assert needle in source, (
        f"expected {needle!r} in structure.py -- "
        "market_source._STRUCTURE_MAX_LOOKBACK_HOURS is now out of sync with it"
    )


def test_structure_extractor_matches_full_history_with_only_the_warmup_buffer() -> None:
    """StructureFeatureExtractor.extract() already self-limits to the last 300
    candles (see the test above), so handing it any depth >=
    CANDLE_WARMUP_BUFFER_HOURS candles up to "now" must reproduce EXACTLY
    what handing it the full history would -- not approximately, exactly,
    since both calls end up slicing to the identical last-300 rows."""
    candles = _synthetic_candles(seed=1, count=6000)
    last_price = candles[-1]["close"]

    full_result = StructureFeatureExtractor.extract(candles, last_price)
    truncated = candles[-market_source.CANDLE_WARMUP_BUFFER_HOURS :]
    truncated_result = StructureFeatureExtractor.extract(truncated, last_price)

    assert truncated_result == full_result


def test_history_depth_reproduces_full_history_phases() -> None:
    """The load-bearing correctness test for Việc 1: build_timeline() on the
    full history vs. on history cut to (coverage window + the warmup buffer
    this module actually ships) must label every hour in the coverage window
    identically. Swept over many independent synthetic price paths, not
    just one, since the failure mode this guards against (an ATR-percentile
    -rank tie flipping right at the truncation boundary) is a rare,
    data-dependent edge case -- a single seed passing would not be
    believable evidence that CANDLE_WARMUP_BUFFER_HOURS is actually enough.
    """
    coverage_hours = 2232  # 93 days: longest real bot ledger measured for this task
    buffer_hours = market_source.CANDLE_WARMUP_BUFFER_HOURS
    depth = coverage_hours + buffer_hours
    total_candles = depth + 3000  # headroom so "full history" is genuinely longer

    mismatched_seeds = []
    for seed in range(40):
        candles = _synthetic_candles(seed=seed, count=total_candles)
        full_timeline = build_timeline("TEST", candles)
        truncated = candles[-depth:]
        truncated_timeline = build_timeline("TEST", truncated)

        full_tail = full_timeline.phases[-coverage_hours:]
        truncated_tail = truncated_timeline.phases[-coverage_hours:]
        if full_tail != truncated_tail:
            mismatched_seeds.append(seed)

    assert not mismatched_seeds, (
        f"build_timeline() disagreed between full and depth-limited history "
        f"for seeds {mismatched_seeds} -- CANDLE_WARMUP_BUFFER_HOURS is too small"
    )


def test_history_depth_formula_is_actually_load_bearing_when_cut_too_aggressively() -> (
    None
):
    """The flip side of the test above: with a deliberately UNDERSIZED buffer
    (well under the 920-hour bare functional minimum -- WARMUP_HOURS +
    VOLATILITY_WINDOW_HOURS from phases.py -- with no safety margin at all),
    build_timeline() must disagree with the full-history run on at least one
    seed. Proves the previous test is actually sensitive to the buffer size,
    not vacuously passing regardless of what CANDLE_WARMUP_BUFFER_HOURS is
    set to -- i.e. this is the "cắt quá tay -> kết quả khác" control the
    task asked for.
    """
    coverage_hours = 2232
    undersized_buffer = 500
    depth = coverage_hours + undersized_buffer
    total_candles = depth + 3000

    mismatched_seeds = []
    for seed in range(40):
        candles = _synthetic_candles(seed=seed, count=total_candles)
        full_timeline = build_timeline("TEST", candles)
        truncated = candles[-depth:]
        truncated_timeline = build_timeline("TEST", truncated)

        full_tail = full_timeline.phases[-coverage_hours:]
        truncated_tail = truncated_timeline.phases[-coverage_hours:]
        if full_tail != truncated_tail:
            mismatched_seeds.append(seed)

    assert mismatched_seeds, (
        "expected an undersized warmup buffer to mislabel at least one seed -- "
        "if this fails, the test above may not actually be sensitive to the buffer"
    )


def test_effective_depth_prefers_explicit_max_history_candles() -> None:
    source = _no_delay_source(FakeOkxClient({}), max_history_candles=123)
    assert source._effective_depth_candles() == 123


def test_effective_depth_default_formula_uses_coverage_window_plus_buffer() -> None:
    source = _no_delay_source(FakeOkxClient({}), coverage_window_hours=1000)
    assert (
        source._effective_depth_candles()
        == 1000 + market_source.CANDLE_WARMUP_BUFFER_HOURS
    )


def test_effective_depth_falls_back_to_default_coverage_window() -> None:
    source = _no_delay_source(FakeOkxClient({}))
    expected = (
        market_source.DEFAULT_COVERAGE_WINDOW_HOURS
        + market_source.CANDLE_WARMUP_BUFFER_HOURS
    )
    assert source._effective_depth_candles() == expected


def test_effective_depth_widens_for_a_stale_as_of_ms() -> None:
    now = market_source._now_ms()
    ten_days_ago = now - 10 * 24 * _BAR_MS
    source = _no_delay_source(
        FakeOkxClient({}), coverage_window_hours=100, as_of_ms=ten_days_ago
    )
    depth = source._effective_depth_candles()
    base = 100 + market_source.CANDLE_WARMUP_BUFFER_HOURS
    # Staleness adds roughly 10*24 = 240 candles; allow slack for the (tiny)
    # amount of real time that elapses between computing `now` above and the
    # call inside _effective_depth_candles().
    assert base + 235 <= depth <= base + 245


# --------------------------------------------------------------------------- #
# Việc 3 -- cache correctness when the required depth changes between runs:
# already-cached history must be reused, only the missing (older) slice
# fetched, and the result must never come up short of what was asked for.
# --------------------------------------------------------------------------- #


def test_cache_extends_backward_when_required_depth_grows(tmp_path: Path) -> None:
    """A later call asking for MORE history than a previous run cached must
    fetch only the missing OLDER slice -- not redownload everything, and not
    silently return fewer candles than the new depth requires."""
    total_hours = 40
    rows: Dict[int, List[Any]] = {}
    ts_list = []
    for i in range(total_hours):
        ts = BASE_TS + i * _BAR_MS
        confirm = "0" if i == total_hours - 1 else "1"  # last hour still open
        rows[ts] = _row(ts, 1, 1, 1, 1, confirm=confirm)
        ts_list.append(ts)
    sorted_ts_desc = sorted(ts_list, reverse=True)

    def handler(params: Dict[str, Any]) -> List[Any]:
        limit = int(params.get("limit", 100))
        after = params.get("after")
        candidates = (
            [ts for ts in sorted_ts_desc if ts < int(after)]
            if after is not None
            else sorted_ts_desc
        )
        return [rows[ts] for ts in candidates[:limit]]

    client = FakeOkxClient(
        {"/api/v5/market/candles": handler, "/api/v5/market/history-candles": handler}
    )
    cache = CandleCache(cache_dir=tmp_path / "cache", enabled=True)

    # First run: a narrow depth is enough (page_size=1 so pagination proceeds
    # one candle at a time -- makes the exact call/candle counts below precise
    # instead of depending on how a bigger page happens to align).
    small_source = _no_delay_source(
        client, candle_cache=cache, page_size=1, max_history_candles=10
    )
    first_payload, error = small_source.get_candles("BTC", "CEX")
    assert error is None
    assert len(first_payload["candles"]) == 10  # 9 closed + the still-open one
    cached_after_first = cache.load("BTC-USDT-SWAP", "1H")
    assert len(cached_after_first) == 9  # the open candle never reaches the cache
    calls_after_first = len(client.calls)

    # Second run against the SAME cache: needs much more history now (e.g.
    # coverage_window_hours grew). Must fetch only the missing older slice.
    bigger_source = _no_delay_source(
        client, candle_cache=cache, page_size=1, max_history_candles=30
    )
    second_payload, error = bigger_source.get_candles("BTC", "CEX")
    assert error is None
    assert len(second_payload["candles"]) == 30  # never short of what was asked

    cached_after_second = cache.load("BTC-USDT-SWAP", "1H")
    assert len(cached_after_second) == 29
    # The 9 candles the first run cached must still be exactly the newest 9
    # of the extended cache -- not re-fetched, not duplicated, not dropped.
    assert cached_after_second[-len(cached_after_first) :] == cached_after_first

    # "Not tải lại từ đầu": the second run must not have redone anywhere near
    # the work of a fresh 30-candle backfill (which would need ~30 calls on
    # top of a fresh market/candles page) -- it should cost only the 1
    # tail-refresh page-pair plus the 20-candle deficit, i.e. far less.
    new_calls = len(client.calls) - calls_after_first
    assert new_calls < 25


# --------------------------------------------------------------------------- #
# Việc 2 -- adaptive request pacing. AdaptiveThrottle is tested directly here
# (fast, no OKX involved); the integration tests below confirm
# LiveMarketDataSource._public_get() actually wires OKX responses into it.
# Every test uses an injected fake clock/sleep -- never a real time.sleep.
# --------------------------------------------------------------------------- #


def test_adaptive_throttle_backs_off_immediately_on_block_signal() -> None:
    throttle = AdaptiveThrottle(
        initial_delay_seconds=0.6,
        max_delay_seconds=5.0,
        backoff_factor=2.0,
        clock=lambda: 0.0,
        sleep=lambda _seconds: None,
    )
    throttle.record_blocked()
    assert throttle.delay_seconds == pytest.approx(1.2)  # halved the pace immediately
    throttle.record_blocked()
    assert throttle.delay_seconds == pytest.approx(2.4)  # decisive every single time


def test_adaptive_throttle_backoff_is_capped_at_max_delay() -> None:
    throttle = AdaptiveThrottle(
        initial_delay_seconds=0.6,
        max_delay_seconds=5.0,
        backoff_factor=2.0,
        clock=lambda: 0.0,
        sleep=lambda _seconds: None,
    )
    for _ in range(20):
        throttle.record_blocked()
    assert throttle.delay_seconds == pytest.approx(5.0)  # never grinds past the ceiling


def test_adaptive_throttle_speeds_up_gently_after_a_clean_streak() -> None:
    throttle = AdaptiveThrottle(
        initial_delay_seconds=0.6,
        speedup_after_clean=20,
        speedup_factor=0.95,
        clock=lambda: 0.0,
        sleep=lambda _seconds: None,
    )
    for _ in range(19):
        throttle.record_success()
    assert throttle.delay_seconds == pytest.approx(
        0.6
    )  # one short of the streak: no move
    throttle.record_success()
    assert throttle.delay_seconds == pytest.approx(
        0.6 * 0.95
    )  # exactly one gentle nudge


def test_adaptive_throttle_speedup_never_exceeds_the_min_delay_ceiling() -> None:
    throttle = AdaptiveThrottle(
        initial_delay_seconds=0.6,
        min_delay_seconds=0.2,
        speedup_after_clean=20,
        speedup_factor=0.95,
        clock=lambda: 0.0,
        sleep=lambda _seconds: None,
    )
    for _ in range(20 * 500):  # far more than enough streaks to hit the floor
        throttle.record_success()
    assert throttle.delay_seconds == pytest.approx(0.2)


def test_adaptive_throttle_wait_uses_the_injected_clock_and_sleep_not_real_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves this class never calls the real time.sleep -- a fake clock/sleep
    pair drives it end to end, per this task's explicit "dùng đồng hồ giả,
    đừng sleep thật" requirement."""

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("AdaptiveThrottle.wait() must not call real time.sleep")

    monkeypatch.setattr(market_source.time, "sleep", boom)

    fake_now = [0.0]
    sleeps: List[float] = []

    def fake_clock() -> float:
        return fake_now[0]

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        fake_now[0] += seconds

    throttle = AdaptiveThrottle(
        initial_delay_seconds=1.0, clock=fake_clock, sleep=fake_sleep
    )
    throttle.wait()  # first call: nothing to wait for yet
    assert sleeps == []
    throttle.wait()  # immediately again: a full 1.0s behind the fake clock
    assert sleeps == pytest.approx([1.0])


def test_public_get_backs_off_the_throttle_on_okx_50011(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration: a real OkxApiError(code="50011") raised from
    LiveMarketDataSource._public_get() must reach AdaptiveThrottle.record_blocked()
    before the failure is re-raised as MarketDataUnavailableError."""

    class _FlakyOnceClient:
        def __init__(self) -> None:
            self.calls = 0

        def public_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
            self.calls += 1
            if self.calls == 1:
                raise OkxApiError("50011", "Requests too frequent")
            return [{"last": "100"}]

    monkeypatch.setattr(market_source.time, "sleep", lambda _s: None)
    throttle = AdaptiveThrottle(
        initial_delay_seconds=0.6, clock=lambda: 0.0, sleep=lambda _s: None
    )
    source = LiveMarketDataSource(
        client=_FlakyOnceClient(),
        candle_cache=CandleCache(enabled=False),
        throttle=throttle,
    )

    with pytest.raises(MarketDataUnavailableError):
        source._public_get("/api/v5/market/ticker", {"instId": "BTC-USDT-SWAP"})
    assert throttle.delay_seconds == pytest.approx(1.2)  # backed off immediately

    data = source._public_get("/api/v5/market/ticker", {"instId": "BTC-USDT-SWAP"})
    assert data == [{"last": "100"}]


def test_public_get_records_success_on_a_clean_call() -> None:
    throttle = AdaptiveThrottle(
        initial_delay_seconds=0.6, clock=lambda: 0.0, sleep=lambda _s: None
    )
    client = FakeOkxClient({"/api/v5/market/ticker": [{"last": "100"}]})
    source = LiveMarketDataSource(
        client=client, candle_cache=CandleCache(enabled=False), throttle=throttle
    )
    source._public_get("/api/v5/market/ticker", {"instId": "BTC-USDT-SWAP"})
    assert (
        throttle._clean_streak == 1
    )  # counted, even though not enough to speed up yet


def test_adaptive_throttle_disabled_reverts_to_fixed_delay_behaviour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MARKET_SOURCE_ADAPTIVE_THROTTLE-style opt-out (here via the constructor
    flag directly): must fall back to the exact pre-Việc-2 fixed-delay code
    path, with no AdaptiveThrottle involved at all."""
    client = FakeOkxClient({"/api/v5/market/ticker": [{"last": "100"}]})
    source = LiveMarketDataSource(
        client=client,
        candle_cache=CandleCache(enabled=False),
        adaptive_throttle=False,
        request_delay_seconds=0.6,
    )
    assert source._adaptive_throttle is None

    sleep_calls: List[float] = []
    # 1st call: only sets _last_request_monotonic (one monotonic() read, T0).
    # 2nd call: reads elapsed-since-T0 (T1 = T0+0.1s), then sets
    # _last_request_monotonic again (T1) -- three monotonic() reads total.
    monotonic_values = iter([100.0, 100.1, 100.1])

    monkeypatch.setattr(market_source.time, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(market_source.time, "monotonic", lambda: next(monotonic_values))

    source._public_get("/api/v5/market/ticker", {"instId": "BTC-USDT-SWAP"})
    source._public_get("/api/v5/market/ticker", {"instId": "BTC-USDT-SWAP"})
    # Fixed pace: 0.6s owed minus the 0.1s that already elapsed.
    assert sleep_calls == pytest.approx([0.5])
