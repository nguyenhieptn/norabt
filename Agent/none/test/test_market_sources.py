"""On-chain and derivatives feeds carry traps; the crawlers must not walk into them."""

from __future__ import annotations

import json
from pathlib import Path

from Agent.none.scripts.crawl_market_data import CEX_ASSETS, DEX_ASSETS, select_pool

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _pair(dex, price, liquidity, chain="ethereum"):
    return {
        "chainId": chain,
        "dexId": dex,
        "priceUsd": str(price),
        "liquidity": {"usd": liquidity},
    }


def test_a_manipulated_pool_is_rejected_however_deep_it_claims_to_be():
    # Real case: UNI came back with a UNI/REN pair quoting 43,159,691 USD per UNI
    # and 1.3 B of claimed liquidity, ahead of the honest 6.28 pool.
    pairs = [
        _pair("uniswap", 43_159_691.52, 1_349_424_699.0),
        _pair("0xF028F723", 8_817_260.19, 162_220_055.0),
        _pair("uniswap", 6.28, 13_990_387.0),
        _pair("uniswap", 6.28, 4_387_750.0),
    ]

    chosen, rejected = select_pool(pairs, "ETHEREUM", reference=6.25)

    assert rejected == 2
    liquidity, price, _ = chosen
    assert price == 6.28
    assert liquidity == 13_990_387.0


def test_no_pool_is_chosen_when_every_price_disagrees():
    pairs = [_pair("uniswap", 43_159_691.52, 1_349_424_699.0)]

    chosen, rejected = select_pool(pairs, "ETHEREUM", reference=6.25)

    assert chosen is None and rejected == 1


def test_pools_on_another_chain_are_not_considered():
    pairs = [
        _pair("raydium", 6.28, 99_000_000.0, chain="solana"),
        _pair("uniswap", 6.28, 1_000.0, chain="ethereum"),
    ]

    chosen, _ = select_pool(pairs, "ETHEREUM", reference=6.25)

    assert chosen[0] == 1_000.0


def test_derivatives_feeds_are_stored_at_instrument_level():
    """A ccy-wide feed sums every contract and read up to 32 % above the pair."""
    for asset in CEX_ASSETS:
        oi = DATA_DIR / "market" / "cex" / asset / f"delta_oi_{asset}-USDT-SWAP.json"
        taker = DATA_DIR / "market" / "cex" / asset / f"taker_volume_{asset}.json"
        if not oi.exists() or not taker.exists():
            continue
        assert json.loads(oi.read_text())["basis"] == "INSTRUMENT_LEVEL", asset
        assert json.loads(taker.read_text())["basis"] == "INSTRUMENT_LEVEL", asset


def test_every_dex_pool_on_disk_agrees_with_its_exchange_reference():
    for asset in DEX_ASSETS:
        path = DATA_DIR / "market" / "dex" / asset / "pool_liquidity.json"
        if not path.exists():
            continue
        pool = json.loads(path.read_text())
        gap = pool.get("price_gap_pct")
        assert gap is not None, f"{asset} chưa ghi độ lệch so với giá tham chiếu"
        assert abs(gap) <= 20.0, f"{asset} lệch {gap:.1f}% so với sàn"
