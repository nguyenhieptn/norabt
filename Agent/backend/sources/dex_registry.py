"""Static lookup table for the 5 DEX assets LiveMarketDataSource can serve.

Why this exists: `Agent/scripts/crawl_pool_liquidity.py`'s live equivalent
(`crawl_pool_liquidity()` in `Agent/scripts/crawl_market_data.py`) reads the
token contract address it needs from *the crawl's own previous output*
(`existing["base_token"]["address"]` in `pool_liquidity.json`) -- there is no
way to derive an ERC-20/SPL contract address from an asset's ticker the way
`BTC -> BTC-USDT-SWAP` can be derived for OKX instrument IDs. A live source
that has never crawled anything has no such file to read from, so the address
has to come from somewhere else.

The "somewhere else" used here is a small hardcoded table, and that is a
deliberate, safe choice rather than a shortcut: a token's on-chain contract
address is an immutable constant of the token itself (redeploying PEPE at a
new address would mean it is a different token), exactly the same category of
fact this project already hardcodes elsewhere for a fixed, small universe
(e.g. `_CT_VALS` in Agent/test/test_market_source.py stands in for OKX's own
per-instrument `ctVal` table in tests -- a fixed physical/contractual fact
about the instrument, safe to pin down for a known, closed set of assets).
DEX_ASSETS in crawl_market_data.py is exactly such a closed set: 5 named
assets (WBTC, WETH, SOL, UNI, PEPE), not an open-ended universe, so a static
table does not need to "scale" to anything -- it only needs to be correct for
these 5.

Every field below was copied byte-for-byte out of the crawl output already
committed to this repo, not invented or guessed:
  - `chain` / `token_address`: Agent/data/dex/<ASSET>/market/pool_liquidity.json
    -> top-level `chain`, `base_token.address`. `chain` is upper-cased
    ("ETHEREUM", "SOLANA") because that is the exact casing the file already
    uses, and it is also the casing `select_pool()` compares against
    DexScreener's (lower-cased) `chainId` via `.lower()`, and the casing
    `crawl_token_security.py`'s `EVM_CHAIN_IDS` dict keys use.
  - `chain_label` / `pool_label`: Agent/data/dex/<ASSET>/market/
    ticks_100ms_stream.json -> top-level `chain`, `pool` (identical values
    also appear in ohlcv_1h_2023_present.json as `chain` / `dex_pool`). These
    are purely descriptive strings copied into this module's `get_ticks()`
    payload so its shape matches the file's; they are NOT used for any
    chain-matching logic (that always goes through the upper-cased `chain`
    field above) and are never refreshed by the crawler itself (compare
    `refresh_dex_ticks()` in crawl_market_data.py, which only ever rewrites
    `ticks`/`total_ticks`/`updated_at` and leaves `pool`/`chain` as whatever
    they were set to once) -- so treating them as a static label here matches
    the original crawl's own treatment of these two fields, not a shortcut.

WRAPPED_UNDERLYING is the same wrap/underlying map already defined as
`MarketRegimeService.WRAPPED_UNDERLYING` in
Agent/backend/qc/reporting/market_report.py. It is duplicated here (not
imported) because importing it would create a circular import: market_report
imports Agent.backend.market.service, which imports
Agent.backend.sources.market_source (this module's sibling and the module
that imports this file) -- market_source.py importing back from
market_report.py would close that loop. Both copies must be kept in sync by
hand if OKX ever lists a new wrapped-asset perpetual; there are only two
entries today, so this is a small, explicit price for staying import-cycle
free rather than restructuring an unrelated module for this change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DexAssetInfo:
    """Everything LiveMarketDataSource needs to serve one DEX asset live."""

    chain: str  # DexScreener chainId (upper-cased) / GoPlus EVM_CHAIN_IDS key
    chain_label: str  # human-readable chain name, as ticks_100ms_stream.json stores it
    token_address: str  # base token contract/mint address (immutable)
    pool_label: str  # descriptive "<BASE>/<QUOTE> <dex> <fee>" string, display only


# Source for every field: see module docstring above. One entry per asset in
# `Agent/scripts/crawl_market_data.py::DEX_ASSETS`.
DEX_ASSET_REGISTRY: Dict[str, DexAssetInfo] = {
    "PEPE": DexAssetInfo(
        chain="ETHEREUM",
        chain_label="Ethereum",
        token_address="0x6982508145454Ce325dDbE47a25d4ec3d2311933",
        pool_label="PEPE/WETH Uniswap v2",
    ),
    "SOL": DexAssetInfo(
        chain="SOLANA",
        chain_label="Solana",
        token_address="So11111111111111111111111111111111111111112",
        pool_label="SOL/USDC Raydium CLMM",
    ),
    "UNI": DexAssetInfo(
        chain="ETHEREUM",
        chain_label="Ethereum",
        token_address="0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        pool_label="UNI/WETH Uniswap v3 0.3%",
    ),
    "WBTC": DexAssetInfo(
        chain="ETHEREUM",
        chain_label="Ethereum",
        token_address="0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        pool_label="WBTC/USDC Uniswap v3 0.05%",
    ),
    "WETH": DexAssetInfo(
        chain="ETHEREUM",
        chain_label="Ethereum",
        token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        pool_label="WETH/USDC Uniswap v3 0.05%",
    ),
}

# Wrapped-token -> underlying-CEX-perp map, duplicated from
# MarketRegimeService.WRAPPED_UNDERLYING (see module docstring for why this is
# a duplicate, not an import). Used to turn a DEX asset's ticker into the OKX
# instrument that actually prices it: WBTC has no "WBTC-USDT-SWAP" on OKX, it
# is priced off BTC-USDT-SWAP (same for WETH/ETH). Every other DEX asset here
# (PEPE, SOL, UNI) already has its own OKX perpetual, so it maps to itself.
WRAPPED_UNDERLYING: Dict[str, str] = {"WBTC": "BTC", "WETH": "ETH"}


def underlying_symbol(symbol: str) -> str:
    """The OKX-tradable symbol backing `symbol` (itself, unless wrapped)."""
    return WRAPPED_UNDERLYING.get(symbol, symbol)


def spot_benchmark_pair(symbol: str) -> str:
    """The instId `refresh_dex_ticks()` calls `/market/trades` with.

    Verified against the 5 DEX assets' own ticks_100ms_stream.json files
    (each one's `benchmark_pair`): PEPE -> PEPE-USDT, SOL -> SOL-USDT,
    UNI -> UNI-USDT, WBTC -> BTC-USDT, WETH -> ETH-USDT. Spot-style
    "<COIN>-USDT", deliberately without the "-SWAP" suffix the candle/
    orderbook/OI endpoints use -- that suffix is what the crawler's own fixed
    `benchmark_pair` values omit, and OKX's public trade-print endpoint is
    keyed by instId exactly as stored there.
    """
    return f"{underlying_symbol(symbol)}-USDT"


def swap_reference_inst_id(symbol: str) -> str:
    """The instId `crawl_pool_liquidity()` reads its CEX reference price from.

    Verified against the 5 DEX assets' own ohlcv_1h_2023_present.json files
    (each one's `price_benchmark`): PEPE -> PEPE-USDT-SWAP, ...,
    WBTC -> BTC-USDT-SWAP, WETH -> ETH-USDT-SWAP.
    """
    return f"{underlying_symbol(symbol)}-USDT-SWAP"


