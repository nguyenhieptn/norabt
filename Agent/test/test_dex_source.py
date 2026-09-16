"""Tests for live DEX support in Agent/backend/sources/market_source.py and the
static asset table in Agent/backend/sources/dex_registry.py.

No real network calls anywhere in this file: OKX interactions go through
FakeOkxClient (same pattern as Agent/test/test_market_source.py), and
DexScreener/GoPlus calls go through a monkeypatched
`market_source._dex_http_get_json` that answers from an in-memory table this
file supplies -- never `urllib.request` for real.

The single most important test here is
`test_live_dex_getters_match_file_source_key_sets`: LiveMarketDataSource must
answer every key FileMarketDataSource's on-disk crawl output does, for all 3
DEX-only inputs and all 5 DEX assets, or a field silently goes missing the
day a live read replaces the crawled files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

import Agent.backend.sources.market_source as market_source
from Agent.backend.sources.dex_registry import (
    DEX_ASSET_REGISTRY,
    WRAPPED_UNDERLYING,
    spot_benchmark_pair,
    swap_reference_inst_id,
    underlying_symbol,
)
from Agent.backend.sources.market_source import (
    CandleCache,
    FileMarketDataSource,
    LiveMarketDataSource,
    MarketDataUnavailableError,
    _select_pool,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "Agent" / "data"
DEX_ASSETS = ["PEPE", "SOL", "UNI", "WBTC", "WETH"]


class FakeOkxClient:
    """Same routing stand-in used by test_market_source.py: maps a request
    path to a fixed value or a callable(params), records every call made, and
    raises on any path the test didn't expect (so a bug can never "pass" by
    silently hitting some other untested endpoint)."""

    def __init__(self, routes: Dict[str, Any]) -> None:
        self.routes = routes
        self.calls: List[Tuple[str, Dict[str, Any]]] = []

    def public_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self.calls.append((path, dict(params or {})))
        if path not in self.routes:
            raise AssertionError(f"unexpected OKX path requested in test: {path}")
        handler = self.routes[path]
        return handler(params or {}) if callable(handler) else handler


class BoomOkxClient:
    """Any OKX call at all is a test failure -- used to prove a code path
    genuinely never touches OKX (e.g. CEX-only getters given venue_type=DEX)."""

    def public_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        raise AssertionError(f"must not call OKX, but got: {path} {params}")


def _dex_source(
    client: Any, dex_registry: Optional[Dict[str, Any]] = None, **kwargs: Any
) -> LiveMarketDataSource:
    kwargs.setdefault("candle_cache", CandleCache(enabled=False))
    kwargs.setdefault("request_delay_seconds", 0.0)
    return LiveMarketDataSource(client=client, dex_registry=dex_registry, **kwargs)


def _dex_pair(
    dex: str,
    price: float,
    liquidity: float,
    *,
    chain: str = "ethereum",
    base_addr: str = "0xBASE",
    base_symbol: str = "BASE",
    quote_addr: str = "0xQUOTE",
    quote_symbol: str = "QUOTE",
    volume_h24: float = 1000.0,
) -> Dict[str, Any]:
    return {
        "chainId": chain,
        "dexId": dex,
        "pairAddress": f"0xPAIR-{dex}-{price}",
        "baseToken": {"address": base_addr, "name": base_symbol, "symbol": base_symbol},
        "quoteToken": {
            "address": quote_addr,
            "name": quote_symbol,
            "symbol": quote_symbol,
        },
        "priceUsd": str(price),
        "liquidity": {"usd": liquidity},
        "volume": {"h24": volume_h24},
    }


def _patch_dexscreener(
    monkeypatch: pytest.MonkeyPatch, by_url: Dict[str, Dict[str, Any]]
) -> None:
    def fake(url: str, *, timeout: int = 20) -> Dict[str, Any]:
        if url not in by_url:
            raise AssertionError(f"unexpected DexScreener/GoPlus URL: {url}")
        return by_url[url]

    monkeypatch.setattr(market_source, "_dex_http_get_json", fake)


def _patch_dexscreener_raises(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    def fake(url: str, *, timeout: int = 20) -> Dict[str, Any]:
        raise exc

    monkeypatch.setattr(market_source, "_dex_http_get_json", fake)


# --------------------------------------------------------------------------- #
# dex_registry.py: benchmark_pair / underlying derivation for all 5 assets.
# --------------------------------------------------------------------------- #


def test_wrapped_underlying_table_is_exactly_wbtc_and_weth() -> None:
    # Pinned per Agent/backend/qc/reporting/market_report.py's
    # MarketRegimeService.WRAPPED_UNDERLYING (duplicated here on purpose --
    # see dex_registry.py's module docstring for why it isn't imported).
    assert WRAPPED_UNDERLYING == {"WBTC": "BTC", "WETH": "ETH"}


@pytest.mark.parametrize(
    "asset,expected_underlying,expected_spot,expected_swap",
    [
        ("PEPE", "PEPE", "PEPE-USDT", "PEPE-USDT-SWAP"),
        ("SOL", "SOL", "SOL-USDT", "SOL-USDT-SWAP"),
        ("UNI", "UNI", "UNI-USDT", "UNI-USDT-SWAP"),
        ("WBTC", "BTC", "BTC-USDT", "BTC-USDT-SWAP"),
        ("WETH", "ETH", "ETH-USDT", "ETH-USDT-SWAP"),
    ],
)
def test_benchmark_pair_derivation_matches_the_5_real_ticks_fixtures(
    asset: str, expected_underlying: str, expected_spot: str, expected_swap: str
) -> None:
    # Cross-checked directly against the `benchmark_pair` field already on
    # disk in each asset's own ticks_100ms_stream.json (WBTC and WETH are the
    # two that actually exercise the unwrap; the other three map to
    # themselves).
    assert underlying_symbol(asset) == expected_underlying
    assert spot_benchmark_pair(asset) == expected_spot
    assert swap_reference_inst_id(asset) == expected_swap

    fixture = json.loads(
        (DATA_DIR / "dex" / asset / "market" / "ticks_100ms_stream.json").read_text()
    )
    assert fixture["benchmark_pair"] == expected_spot

    ohlcv = json.loads(
        (DATA_DIR / "dex" / asset / "market" / "ohlcv_1h_2023_present.json").read_text()
    )
    assert ohlcv["price_benchmark"] == expected_swap


def test_dex_asset_registry_covers_exactly_the_5_dex_assets() -> None:
    assert set(DEX_ASSET_REGISTRY) == set(DEX_ASSETS)
    for asset, info in DEX_ASSET_REGISTRY.items():
        assert info.chain in ("ETHEREUM", "SOLANA")
        assert info.token_address  # non-empty
        pool_file = json.loads(
            (DATA_DIR / "dex" / asset / "market" / "pool_liquidity.json").read_text()
        )
        # The registry's chain/address must agree with what the crawl itself
        # observed for this asset (this is the "hardcoded but verified against
        # the real crawl output" claim the registry's docstring makes).
        assert info.chain == pool_file["chain"]
        assert info.token_address == pool_file["base_token"]["address"]


# --------------------------------------------------------------------------- #
# select_pool: ported-verbatim price-before-liquidity pool selection.
# --------------------------------------------------------------------------- #


def test_select_pool_rejects_manipulated_pool_even_at_highest_liquidity() -> None:
    # Real case cited in the task: UNI/REN quoting 43,159,691 USD/UNI with
    # 1.3B claimed liquidity, dwarfing the honest ~6.28 pool's liquidity.
    pairs = [
        _dex_pair("uniswap", 43_159_691.52, 1_349_424_699.0),
        _dex_pair("uniswap", 6.28, 13_990_387.0),
        _dex_pair("uniswap", 6.28, 4_387_750.0),
    ]
    chosen, rejected = _select_pool(pairs, "ETHEREUM", reference=6.25)
    assert rejected == 1
    liquidity, price, _ = chosen
    assert price == 6.28
    assert liquidity == 13_990_387.0  # the deepest pool that PASSED price, not overall


def test_select_pool_returns_none_when_every_price_disagrees() -> None:
    pairs = [_dex_pair("uniswap", 43_159_691.52, 1_349_424_699.0)]
    chosen, rejected = _select_pool(pairs, "ETHEREUM", reference=6.25)
    assert chosen is None and rejected == 1


def test_select_pool_ignores_pools_on_another_chain() -> None:
    pairs = [
        _dex_pair("raydium", 6.28, 99_000_000.0, chain="solana"),
        _dex_pair("uniswap", 6.28, 1_000.0, chain="ethereum"),
    ]
    chosen, _ = _select_pool(pairs, "ETHEREUM", reference=6.25)
    assert chosen[0] == 1_000.0


# --------------------------------------------------------------------------- #
# resolve_venue: DEX is opt-in via `dex_registry`; unconfigured default is
# byte-for-byte the pre-existing "DEX always raises" behaviour.
# --------------------------------------------------------------------------- #


def test_resolve_venue_dex_raises_when_unconfigured() -> None:
    source = _dex_source(BoomOkxClient())
    with pytest.raises(MarketDataUnavailableError) as excinfo:
        source.resolve_venue("PEPE", "DEX")
    message = str(excinfo.value)
    assert "DEX" in message
    assert "OKX" in message


def test_resolve_venue_dex_raises_for_an_asset_outside_the_registry() -> None:
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.resolve_venue(
            "DOGE", "DEX"
        )  # a real CEX asset, not in DEX_ASSET_REGISTRY


def test_resolve_venue_dex_succeeds_once_configured_for_a_known_asset() -> None:
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    assert source.resolve_venue("PEPE", "DEX") == "DEX"


def test_resolve_venue_cex_is_unaffected_by_dex_registry() -> None:
    # Passing dex_registry must never change the CEX path -- CEX_ASSETS are
    # not in DEX_ASSET_REGISTRY anyway, but this pins the venue precedence
    # itself: an explicit CEX request never consults the DEX table at all.
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    assert source.resolve_venue("BTC", "CEX") == "CEX"
    assert source.resolve_venue("BTC", None) == "CEX"


# --------------------------------------------------------------------------- #
# CEX-only getters must not attempt OKX at all for a DEX venue_type (the
# original crawl never populated these files for a DEX asset -- see
# _CEX_ONLY_INPUT_NOT_APPLICABLE_TO_DEX_REASON's comment in market_source.py).
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "getter",
    ["get_orderbook", "get_open_interest", "get_taker_volume", "get_sentiment"],
)
def test_cex_only_getters_never_call_okx_for_dex_venue(getter: str) -> None:
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    payload, error = getattr(source, getter)("PEPE", "DEX")
    assert payload == {}
    assert error is not None  # NOT_APPLICABLE-shaped, not a silent empty success


def test_cex_only_getters_are_unchanged_for_cex_venue() -> None:
    # Regression guard: adding the DEX early-return must not touch the CEX
    # branch at all. Exercise one representative getter end to end.
    client = FakeOkxClient(
        {
            "/api/v5/public/instruments": lambda p: [{"ctVal": "0.01"}],
            "/api/v5/market/books": lambda p: [
                {
                    "bids": [["100", "1", "0", "1"]],
                    "asks": [["101", "1", "0", "1"]],
                    "ts": "1",
                }
            ],
        }
    )
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)
    payload, error = source.get_orderbook("BTC", "CEX")
    assert error is None
    assert payload["contract_size"] == 0.01


# --------------------------------------------------------------------------- #
# get_ticks: fixed 100-count fetch, byte-for-byte matching
# crawl_market_data.py::refresh_dex_ticks()'s own request shape.
# --------------------------------------------------------------------------- #


def _trade(
    ts: int, side: str = "buy", px: str = "1.0", sz: str = "1.0"
) -> Dict[str, Any]:
    return {
        "instId": "PEPE-USDT",
        "tradeId": str(ts),
        "px": px,
        "sz": sz,
        "side": side,
        "ts": str(ts),
        "source": "0",
    }


def test_get_ticks_fetches_exactly_100_latest_trades_not_a_time_window() -> None:
    trades = [_trade(1_000 + i) for i in range(100)]

    def trades_handler(params: Dict[str, Any]) -> List[Dict[str, Any]]:
        assert params == {"instId": "PEPE-USDT", "limit": 100}
        return trades

    client = FakeOkxClient({"/api/v5/market/trades": trades_handler})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)

    payload, error = source.get_ticks("PEPE", "DEX")
    assert error is None
    assert len(client.calls) == 1  # one fixed-count call, no pagination/backfill
    assert payload["total_ticks"] == 100
    assert len(payload["ticks"]) == 100


def test_get_ticks_payload_has_every_key_the_on_disk_fixture_has() -> None:
    expected_keys = set(
        json.loads(
            (
                DATA_DIR / "dex" / "PEPE" / "market" / "ticks_100ms_stream.json"
            ).read_text()
        )
    )
    client = FakeOkxClient({"/api/v5/market/trades": lambda p: [_trade(1_000)]})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)
    payload, error = source.get_ticks("PEPE", "DEX")
    assert error is None
    assert expected_keys - set(payload) == set()


def test_get_ticks_wrong_venue_and_unconfigured_asset_return_tuple_not_raise() -> None:
    source_unconfigured = _dex_source(BoomOkxClient())
    payload, error = source_unconfigured.get_ticks("PEPE", "DEX")
    assert payload == {} and error is not None

    source_configured = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    payload, error = source_configured.get_ticks("BTC", "CEX")
    assert payload == {} and error is not None


def test_get_ticks_raises_when_okx_returns_no_trades() -> None:
    client = FakeOkxClient({"/api/v5/market/trades": lambda p: []})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_ticks("PEPE", "DEX")


# --------------------------------------------------------------------------- #
# get_pool_liquidity: DexScreener + price-validated pool selection.
# --------------------------------------------------------------------------- #


def test_get_pool_liquidity_picks_the_price_validated_deepest_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["UNI"]
    url = f"https://api.dexscreener.com/latest/dex/tokens/{info.token_address}"
    _patch_dexscreener(
        monkeypatch,
        {
            url: {
                "pairs": [
                    _dex_pair(
                        "uniswap", 43_159_691.52, 1_349_424_699.0, chain="ethereum"
                    ),
                    _dex_pair("uniswap", 6.28, 13_990_387.0, chain="ethereum"),
                ]
            }
        },
    )
    client = FakeOkxClient({"/api/v5/market/ticker": [{"last": "6.257"}]})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)

    payload, error = source.get_pool_liquidity("UNI", "DEX")
    assert error is None
    assert payload["price_usd"] == 6.28
    assert payload["tvl_usd"] == 13_990_387.0
    assert payload["pools_rejected_on_price"] == 1
    assert payload["chain"] == "ETHEREUM"
    assert payload["reference_instrument"] == "UNI-USDT-SWAP"


def test_get_pool_liquidity_payload_has_every_key_the_on_disk_fixture_has(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["UNI"]
    url = f"https://api.dexscreener.com/latest/dex/tokens/{info.token_address}"
    _patch_dexscreener(
        monkeypatch, {url: {"pairs": [_dex_pair("uniswap", 6.28, 1_000.0)]}}
    )
    client = FakeOkxClient({"/api/v5/market/ticker": [{"last": "6.28"}]})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)

    expected_keys = set(
        json.loads(
            (DATA_DIR / "dex" / "UNI" / "market" / "pool_liquidity.json").read_text()
        )
    )
    payload, error = source.get_pool_liquidity("UNI", "DEX")
    assert error is None
    assert expected_keys - set(payload) == set()
    expected_base_keys = {"address", "name", "symbol"}
    assert expected_base_keys - set(payload["base_token"]) == set()
    assert expected_base_keys - set(payload["quote_token"]) == set()


def test_get_pool_liquidity_raises_when_no_pool_passes_price_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["UNI"]
    url = f"https://api.dexscreener.com/latest/dex/tokens/{info.token_address}"
    _patch_dexscreener(
        monkeypatch,
        {url: {"pairs": [_dex_pair("uniswap", 43_159_691.52, 1_349_424_699.0)]}},
    )
    client = FakeOkxClient({"/api/v5/market/ticker": [{"last": "6.257"}]})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_pool_liquidity("UNI", "DEX")


def test_get_pool_liquidity_raises_when_dexscreener_returns_no_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["UNI"]
    url = f"https://api.dexscreener.com/latest/dex/tokens/{info.token_address}"
    _patch_dexscreener(monkeypatch, {url: {"pairs": []}})
    client = FakeOkxClient({"/api/v5/market/ticker": [{"last": "6.257"}]})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_pool_liquidity("UNI", "DEX")


def test_get_pool_liquidity_raises_when_dexscreener_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dexscreener_raises(
        monkeypatch, MarketDataUnavailableError("giả lập DexScreener sập")
    )
    client = FakeOkxClient({"/api/v5/market/ticker": [{"last": "6.257"}]})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_pool_liquidity("UNI", "DEX")


def test_get_pool_liquidity_raises_when_okx_reference_price_fails() -> None:
    client = FakeOkxClient({"/api/v5/market/ticker": lambda p: []})
    source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_pool_liquidity("UNI", "DEX")


# --------------------------------------------------------------------------- #
# get_token_security: GoPlus, EVM and Solana branches.
# --------------------------------------------------------------------------- #


def test_get_token_security_evm_maps_fields_like_the_crawler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["UNI"]
    url = f"https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses={info.token_address}"
    _patch_dexscreener(
        monkeypatch,
        {
            url: {
                "code": 1,
                "message": "OK",
                "result": {
                    info.token_address.lower(): {
                        "is_honeypot": "0",
                        "buy_tax": "0.01",
                        "sell_tax": "0.02",
                        "is_mintable": "0",
                        "is_blacklisted": "0",
                        "holder_count": "383790",
                        "holders": [{"percent": "0.5"}, {"percent": "0.02"}],
                        "lp_holders": [{"is_locked": "0"}],
                    }
                },
            }
        },
    )
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    payload, error = source.get_token_security("UNI", "DEX")
    assert error is None
    security = payload["security"]
    assert security["is_honeypot"] is False
    assert security["buy_tax"] == pytest.approx(1.0)  # fraction -> percent
    assert security["sell_tax"] == pytest.approx(2.0)
    assert security["top10_holder_pct"] == pytest.approx(52.0)
    assert security["liquidity_locked"] is False
    assert security["security_score"] is None  # never an invented composite score


def test_get_token_security_solana_maps_fields_like_the_crawler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["SOL"]
    url = (
        "https://api.gopluslabs.io/api/v1/solana/token_security"
        f"?contract_addresses={info.token_address}"
    )
    _patch_dexscreener(
        monkeypatch,
        {
            url: {
                "code": 1,
                "message": "OK",
                "result": {
                    info.token_address: {
                        "mintable": {"status": "0"},
                        "freezable": {"status": "0"},
                        "metadata_mutable": {"status": "1"},
                        "holders": [],
                    }
                },
            }
        },
    )
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    payload, error = source.get_token_security("SOL", "DEX")
    assert error is None
    security = payload["security"]
    assert security["is_mintable"] is False
    assert security["is_blacklisted"] is False
    assert security["metadata_mutable"] is True
    assert security["is_honeypot"] is None  # no EVM-style concept on Solana


def test_get_token_security_payload_has_every_key_the_on_disk_fixture_has(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["PEPE"]
    url = f"https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses={info.token_address}"
    _patch_dexscreener(
        monkeypatch,
        {
            url: {
                "code": 1,
                "result": {
                    info.token_address.lower(): {
                        "is_honeypot": "0",
                        "buy_tax": "0",
                        "sell_tax": "0",
                        "is_mintable": "0",
                        "is_blacklisted": "1",
                        "holder_count": "590428",
                        "holders": [],
                        "lp_holders": [{"is_locked": "1"}],
                    }
                },
            }
        },
    )
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    expected_keys = set(
        json.loads(
            (DATA_DIR / "dex" / "PEPE" / "market" / "token_security.json").read_text()
        )
    )
    expected_security_keys = set(
        json.loads(
            (DATA_DIR / "dex" / "PEPE" / "market" / "token_security.json").read_text()
        )["security"]
    )
    payload, error = source.get_token_security("PEPE", "DEX")
    assert error is None
    assert expected_keys - set(payload) == set()
    assert expected_security_keys - set(payload["security"]) == set()


def test_get_token_security_raises_on_goplus_error_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["UNI"]
    url = f"https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses={info.token_address}"
    _patch_dexscreener(monkeypatch, {url: {"code": 0, "message": "rate limited"}})
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_token_security("UNI", "DEX")


def test_get_token_security_raises_when_address_has_no_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = DEX_ASSET_REGISTRY["UNI"]
    url = f"https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses={info.token_address}"
    _patch_dexscreener(monkeypatch, {url: {"code": 1, "result": {}}})
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_token_security("UNI", "DEX")


def test_get_token_security_raises_when_goplus_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dexscreener_raises(
        monkeypatch, MarketDataUnavailableError("giả lập GoPlus sập")
    )
    source = _dex_source(BoomOkxClient(), dex_registry=DEX_ASSET_REGISTRY)
    with pytest.raises(MarketDataUnavailableError):
        source.get_token_security("UNI", "DEX")


# --------------------------------------------------------------------------- #
# The most important test: key parity between FileMarketDataSource (the real
# crawl output already on disk) and LiveMarketDataSource (mocked OKX/
# DexScreener/GoPlus), across all 5 DEX assets and all 3 DEX-only inputs.
# --------------------------------------------------------------------------- #


def _mocked_live_pool_and_security_for(
    monkeypatch: pytest.MonkeyPatch, asset: str
) -> None:
    info = DEX_ASSET_REGISTRY[asset]
    pool_url = f"https://api.dexscreener.com/latest/dex/tokens/{info.token_address}"
    if info.chain == "SOLANA":
        sec_url = (
            "https://api.gopluslabs.io/api/v1/solana/token_security"
            f"?contract_addresses={info.token_address}"
        )
        sec_body = {
            "code": 1,
            "result": {
                info.token_address: {
                    "mintable": {"status": "0"},
                    "freezable": {"status": "0"},
                    "metadata_mutable": {"status": "0"},
                    "holders": [],
                }
            },
        }
    else:
        chain_id = market_source._GOPLUS_EVM_CHAIN_IDS[info.chain]
        sec_url = (
            f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}"
            f"?contract_addresses={info.token_address}"
        )
        sec_body = {
            "code": 1,
            "result": {
                info.token_address.lower(): {
                    "is_honeypot": "0",
                    "buy_tax": "0",
                    "sell_tax": "0",
                    "is_mintable": "0",
                    "is_blacklisted": "0",
                    "holder_count": "1",
                    "holders": [],
                    "lp_holders": [],
                }
            },
        }
    _patch_dexscreener(
        monkeypatch,
        {
            pool_url: {
                "pairs": [_dex_pair("dex", 1.0, 1_000.0, chain=info.chain.lower())]
            },
            sec_url: sec_body,
        },
    )


@pytest.mark.parametrize("asset", DEX_ASSETS)
def test_live_dex_getters_match_file_source_key_sets(
    asset: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_source = FileMarketDataSource(DATA_DIR)
    client = FakeOkxClient(
        {
            "/api/v5/market/trades": lambda p: [_trade(1_000, side="buy")],
            "/api/v5/market/ticker": lambda p: [{"last": "1.0"}],
        }
    )
    _mocked_live_pool_and_security_for(monkeypatch, asset)
    live_source = _dex_source(client, dex_registry=DEX_ASSET_REGISTRY)

    for getter in ("get_ticks", "get_pool_liquidity", "get_token_security"):
        file_payload, file_error = getattr(file_source, getter)(asset, "DEX")
        live_payload, live_error = getattr(live_source, getter)(asset, "DEX")
        assert file_error is None, f"{asset}.{getter}: fixture file itself is broken"
        assert live_error is None, f"{asset}.{getter}: {live_error}"

        missing = set(file_payload) - set(live_payload)
        assert not missing, (
            f"{asset}.{getter}: live is missing top-level keys {missing}"
        )

        for nested_key in ("base_token", "quote_token", "security"):
            if nested_key in file_payload:
                nested_missing = set(file_payload[nested_key]) - set(
                    live_payload.get(nested_key) or {}
                )
                assert not nested_missing, (
                    f"{asset}.{getter}.{nested_key}: live missing {nested_missing}"
                )
