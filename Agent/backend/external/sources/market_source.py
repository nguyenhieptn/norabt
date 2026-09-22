"""Where MarketService's per-asset inputs come from: files on disk, or OKX live.

Why this exists: Logic 1 (MarketService) used to be hardwired to read pre-crawled
JSON files under Agent/data/<venue>/<asset>/market/. Filling those files required a
crawl step that downloaded the asset's *entire* candle history on every run -- for
the 15-asset universe that is ~475k candles / 91 MB, ~92% of total volume, even
though an hourly candle never changes once its hour has closed (the candle for
2024-03-12 03:00 UTC is fixed forever the moment 04:00 UTC arrives). Re-downloading
it on every run just to get byte-identical bytes back is pure waste.

This module lets MarketService read the exact same shape of data either from those
files (FileMarketDataSource, the default, byte-for-byte the old behaviour) or
straight from OKX (LiveMarketDataSource). The live path caches the immutable
historical portion of the candle series on disk (Agent/data/cache/candles/, kept
apart from the crawl-and-dump dataset in Agent/data/cex|dex so the two are never
confused) and only ever calls OKX for the still-open candle plus whatever closed
candles have appeared since the cache was last written. Every other input this
service needs (order book, open interest, taker flow, sentiment) describes the
current instant, not history, so those are always fetched live -- there is nothing
in them to cache.

Fail-closed by design: a `get_*` method either returns a payload OKX actually
answered with, or raises `MarketDataUnavailableError`. It never manufactures an
empty dict to paper over an OKX error, because an empty-but-present market_result
input is exactly what makes Logic 2 grade an asset UNKNOWN instead of surfacing the
failure that produced it.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import threading
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from Agent.backend.infra.config import config
from Agent.backend.market.features.orderflow import (
    OrderflowFeatureExtractor,
    TickAggregator,
)
from Agent.backend.bot.mcp.analytics.strategy.phases import (
    VOLATILITY_WINDOW_HOURS as _PHASE_VOLATILITY_WINDOW_HOURS,
    WARMUP_HOURS as _PHASE_WARMUP_HOURS,
)
from Agent.backend.external.okx.client import (
    DEFAULT_USER_AGENT,
    OkxApiError,
    OkxClient,
    OkxTransportError,
)
from Agent.backend.external.sources.dex_registry import (
    DexAssetInfo,
    spot_benchmark_pair,
    swap_reference_inst_id,
    underlying_symbol,
)


class MarketDataUnavailableError(ValueError):
    """A source could not produce a market input a caller asked for.

    Defined here rather than in Agent/backend/market/service.py so this module
    never has to import back from that one (market/service.py imports
    MarketDataSource/FileMarketDataSource from here for its default source --
    importing the other way too would be a circular import). market/service.py
    re-exports this exact class under its own name, so every existing
    `from Agent.backend.market.service import MarketDataUnavailableError` in the
    codebase (pipeline.py, agent_server.py, the QC reporting modules, ...) keeps
    resolving to the same class and catching it exactly as before.

    Kept as a ValueError subclass because every one of those call sites catches
    `(MarketDataUnavailableError, ValueError)` or `ValueError` outright.
    """


class MarketDataSource(ABC):
    """One method per market input MarketService reads for a single asset.

    Every getter returns `(payload, error)`, mirroring the old
    `_read_json(path) -> (payload, error)` contract byte for byte: `error` is
    `None` on success or a short human-readable reason on failure, and
    MarketService grades a source as MISSING/INVALID/NOT_APPLICABLE purely from
    that string. Preserving the tuple contract (instead of switching to
    exceptions for every getter) means MarketService's grading logic in
    `get_market_result` did not need to change at all when this abstraction was
    introduced -- only *where* each payload comes from changed.

    The one input that behaves differently is `get_candles`: both
    implementations raise `MarketDataUnavailableError` instead of returning an
    error string, because MarketService already treats missing/empty candles as
    fatal (candles are the one input `get_market_result` cannot proceed without),
    so returning a string there would just be re-raised one line later anyway.

    `LiveMarketDataSource.get_ticks` / `get_pool_liquidity` / `get_token_security`
    follow the same two-mode pattern as every other getter for the
    "structurally not applicable" case (wrong venue, or DEX support not
    configured -- still a normal `(payload, error)` tuple), but ALSO raise
    `MarketDataUnavailableError` instead of returning an error string once a
    live DEX fetch is actually attempted and fails (OKX/DexScreener/GoPlus
    error, or no pool survives price validation) -- see those methods'
    docstrings for why: an error paired with an empty dict is still an empty
    dict to a caller that only checks the payload, and for a DEX asset that
    would grade the asset UNKNOWN instead of surfacing the real failure.
    """

    @abstractmethod
    def resolve_venue(self, symbol: str, venue_type: Optional[str]) -> str:
        """Return 'CEX' or 'DEX' for this asset, or raise if neither applies."""

    @abstractmethod
    def get_candles(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_orderbook(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_open_interest(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_taker_volume(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_sentiment(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_ticks(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_pool_liquidity(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_token_security(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...

    @abstractmethod
    def get_macro_context(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]: ...


# --------------------------------------------------------------------------- #
# File source -- unchanged behaviour, just relocated out of MarketService.
# --------------------------------------------------------------------------- #


class FileMarketDataSource(MarketDataSource):
    """Reads the same on-disk JSON files MarketService always read.

    This is the default source and its behaviour is byte-for-byte identical to
    the pre-abstraction code: same file names, same fallback (2023_present ->
    2026), same "file not found" / "invalid JSON" error strings.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(config.DATA_DIR)

    def _market_dir(self, symbol: str, venue_type: str) -> Path:
        return self.data_dir / "market" / venue_type.lower() / symbol

    def resolve_venue(self, symbol: str, venue_type: Optional[str]) -> str:
        requested = venue_type.upper() if venue_type else None
        if requested not in (None, "CEX", "DEX"):
            raise ValueError("venue_type must be CEX or DEX")
        for kind in (requested,) if requested else ("CEX", "DEX"):
            if self._market_dir(symbol, kind).is_dir():
                return kind
        suffix = f" on {requested}" if requested else ""
        raise MarketDataUnavailableError(f"No market dataset for {symbol}{suffix}")

    @staticmethod
    def _read_json(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
        if not path.exists():
            return {}, "file not found"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return {}, "root JSON value is not an object"
            return payload, None
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return {}, f"invalid JSON: {exc}"

    def get_candles(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        payload, error = self._read_json(market_dir / "ohlcv_1h_2023_present.json")
        if error:
            payload, error = self._read_json(market_dir / "ohlcv_1h_2026.json")
        return payload, error

    def get_orderbook(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        return self._read_json(
            self._market_dir(symbol, venue_type) / "orderbook_l2.json"
        )

    def get_open_interest(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        return self._read_json(market_dir / f"delta_oi_{symbol}-USDT-SWAP.json")

    def get_taker_volume(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        return self._read_json(market_dir / f"taker_volume_{symbol}.json")

    def get_sentiment(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        return self._read_json(market_dir / f"sentiment_{symbol}.json")

    def get_ticks(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        return self._read_json(market_dir / "ticks_100ms_stream.json")

    def get_pool_liquidity(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        return self._read_json(market_dir / "pool_liquidity.json")

    def get_token_security(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        return self._read_json(market_dir / "token_security.json")

    def get_macro_context(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        market_dir = self._market_dir(symbol, venue_type)
        return self._read_json(market_dir / "macro_context.json")


# --------------------------------------------------------------------------- #
# Live source -- OKX for every CEX/perp input, plus DexScreener + GoPlus for
# the 3 DEX-only inputs (dex_ticks still comes from OKX itself: DEX flow is
# benchmarked off the same CEX instrument the crawler benchmarks it against,
# see spot_benchmark_pair()). DEX support is opt-in via the `dex_registry`
# constructor argument (default None): a live DEX read needs a token address
# DexScreener/GoPlus can look up, and there is no way to derive one from a
# ticker (see Agent/backend/sources/dex_registry.py's docstring) -- so unlike
# every CEX input, which needs nothing beyond the symbol itself, DEX support
# needs this extra static table supplied before it can do anything. Leaving
# it unset keeps this class's default behaviour (resolve_venue rejects "DEX",
# exactly as before this asset-registry table existed) unchanged for any
# existing caller that constructs `LiveMarketDataSource()` with no arguments.
# --------------------------------------------------------------------------- #

_BAR = "1H"
_BAR_MS = 3_600_000
_HISTORY_PAGE_SIZE = 100  # OKX hard-caps `limit` at 100 rows/call on both endpoints
_PROGRESS_EVERY = 10  # print a progress line every N pages during a long backfill

# OKX market-data endpoints (candles/books/rubik stats) sit in a different
# rate-limit bucket than the signed copytrading endpoints OkxClient's retry/
# backoff was tuned for, so this module throttles itself instead of relying on
# OkxClient. 0.6s matches the delay Agent/none/scripts/crawl_market_data.py already
# uses against these same endpoints in production without ever being throttled
# by OKX -- reused here as a conservative, field-proven STARTING pace (see
# AdaptiveThrottle below) rather than a number ever confirmed against OKX's
# real limit for these endpoints. Deliberately never probed by firing
# requests faster until OKX complains: getting rate-limited or IP-banned
# would break every other process sharing this host's OKX connection, not
# just this one backfill.
_REQUEST_DELAY_SECONDS = 0.6

# --------------------------------------------------------------------------- #
# Việc 2 -- adaptive request pacing (see AdaptiveThrottle below for the
# mechanism). These are just its tunable ceilings/floors and step sizes.
# --------------------------------------------------------------------------- #

# Fastest this module will ever pace itself to, no matter how long a clean
# streak runs: OKX's public docs describe roughly 20 requests / 2s (10 req/s)
# for most market-data endpoints; 5 req/s keeps real margin under that even
# though the exact bucket used by the endpoints below (candles, books, rubik
# stats) is not individually documented -- see the _REQUEST_DELAY_SECONDS
# comment above for why this module does not probe for the real number
# instead of assuming a margin.
_ADAPTIVE_MIN_DELAY_SECONDS = 0.2
# Slowest this module will ever back off to -- a floor under the backoff so a
# noisy run of blocks can never wind the pace down to "effectively stopped".
_ADAPTIVE_MAX_DELAY_SECONDS = 5.0
# Only nudge the pace up after this many CONSECUTIVE clean responses, so one
# lucky request right after a backoff can't immediately start climbing again.
_ADAPTIVE_SPEEDUP_AFTER_CLEAN = 20
# Gentle: each nudge shaves 5% off the delay. Deliberately much smaller than
# the backoff step below -- see AdaptiveThrottle's docstring for why speeding
# up must cost far more clean requests to earn than backing off costs to lose.
_ADAPTIVE_SPEEDUP_FACTOR = 0.95
# Decisive: any block signal immediately DOUBLES the delay (halves the pace),
# per this task's explicit instruction ("lùi phải dứt khoát, ví dụ giảm một
# nửa") -- an unnecessary extra backoff costs a few seconds; an insufficient
# one risks the shared-IP ban this whole design exists to avoid.
_ADAPTIVE_BACKOFF_FACTOR = 2.0

# Escape hatch: MARKET_SOURCE_ADAPTIVE_THROTTLE=false reverts every instance
# constructed without an explicit `adaptive_throttle=` argument back to the
# exact fixed-delay behaviour this replaces, in case OKX's real rate-limit
# behaviour ever stops matching what this module assumes about it.
_ADAPTIVE_THROTTLE_ENABLED_DEFAULT = os.getenv(
    "MARKET_SOURCE_ADAPTIVE_THROTTLE", "true"
).strip().lower() not in ("false", "0", "no")

# OKX's documented rate-limit error code ("Requests too frequent", see
# https://www.okx.com/docs-v5/en/#error-code). OkxClient
# (Agent/backend/okx/client.py) never surfaces the raw HTTP status to
# callers, only OKX's own JSON `code`/`msg` -- parsed even from a non-2xx
# response, see OkxClient._send -- so this is the only reliable
# machine-readable rate-limit signal available from here; _looks_rate_limited()
# below also matches "429"/"too many requests" in the error text as a
# fallback, in case OKX (or a proxy in front of it) ever answers with a bare
# HTTP 429 whose body's `code` field doesn't carry 50011.
_RATE_LIMIT_OKX_CODES = {"50011"}

# --------------------------------------------------------------------------- #
# Việc 1 -- how many 1H candles get_candles() actually needs, instead of
# hardcoding "everything since 2023" (~32,439 candles / 325 pages for a
# 3.7-year-old instrument, ~49 minutes of throttled OKX calls -- measured on
# a real run; see the task this was written for). Required depth is
# COVERAGE (how far back the analysis needs to look) + a WARMUP BUFFER (how
# much MORE history must exist before that, so every indicator reads
# identically to the untruncated series):
#
#   COVERAGE -- a caller that knows exactly how far back it needs (e.g. it's
#   analysing one specific bot's ledger) should pass `coverage_window_hours`
#   itself. Absent that, DEFAULT_COVERAGE_WINDOW_HOURS is the fallback:
#   measured directly against real bot ledgers, the longest-lived bot order
#   book on record spans 93 days and the median is 68 days -- every candle
#   older than that has never once been read by a bot's trade history, yet
#   the old fixed "since 2023" depth downloaded it every run regardless. 120
#   days is used as the default (not exactly 93) to leave headroom for a
#   future bot outliving every one seen so far without silently losing
#   warmup accuracy; override via MARKET_SOURCE_COVERAGE_WINDOW_HOURS if
#   that stops being enough margin.
#
#   WARMUP BUFFER -- read directly from get_candles()'s two consumers, never
#   guessed:
#
#     Agent/backend/mcp/analytics/strategy/phases.py::build_timeline()
#       - WARMUP_HOURS (imported above as _PHASE_WARMUP_HOURS): an hour
#         needs this many candles of EMA200 history behind it before
#         build_timeline will even label it -- everything earlier is
#         UNKNOWN by construction.
#       - VOLATILITY_WINDOW_HOURS (imported above as
#         _PHASE_VOLATILITY_WINDOW_HOURS): the ATR percentile-rank window
#         looks back this many hours from each labelled hour. Fewer hours
#         available before the coverage window starts means a NARROWER
#         percentile window than the full-history version would have used
#         for those early hours -- a silent accuracy regression, not a
#         crash.
#       => needs >= _PHASE_WARMUP_HOURS + _PHASE_VOLATILITY_WINDOW_HOURS
#          candles of runway before the first hour of interest.
#
#     Agent/backend/market/features/structure.py::StructureFeatureExtractor.extract()
#       - already self-limits to `candles_1h[-300:]` internally (see
#         _STRUCTURE_MAX_LOOKBACK_HOURS below and
#         test_structure_lookback_assumption_still_holds, which pins this
#         exact literal against the live source file), so it never needs
#         more than 300 trailing candles up to "now" to reproduce its
#         full-history answer exactly -- subsumed by the phases.py
#         requirement above.
#
#   920 hours (_PHASE_WARMUP_HOURS + _PHASE_VOLATILITY_WINDOW_HOURS) is the
#   BARE-MINIMUM candle count for every category/label to come out right, but
#   not enough to make the underlying EMA float values bit-identical: EMA is
#   an IIR filter with geometrically-decaying but technically-infinite
#   memory, so a truncated series' EMA only *converges toward* the
#   full-history EMA, never reaches it exactly, no matter how much buffer is
#   added. What actually has to match is the CATEGORICAL output (MarketPhase
#   / TrendState / VolatilityState), since that -- not the raw float -- is
#   what every downstream decision reads.
#   test_market_source.py::test_history_depth_reproduces_full_history_phases
#   sweeps buffer sizes against real build_timeline() output over 150
#   independent synthetic price paths: 920 (the bare minimum above)
#   mislabelled 1 hour out of 150 seeds' worth near an ATR-percentile-rank
#   tie; 1000 still mislabelled 1; every buffer >= 1200 tested clean across
#   all 150 seeds. _WARMUP_SAFETY_MARGIN_HOURS adds comfortable headroom past
#   that empirically-found threshold.
_STRUCTURE_MAX_LOOKBACK_HOURS = 300
_MIN_FUNCTIONAL_WARMUP_HOURS = max(
    _PHASE_WARMUP_HOURS + _PHASE_VOLATILITY_WINDOW_HOURS,
    _STRUCTURE_MAX_LOOKBACK_HOURS,
)
_WARMUP_SAFETY_MARGIN_HOURS = 600
CANDLE_WARMUP_BUFFER_HOURS = _MIN_FUNCTIONAL_WARMUP_HOURS + _WARMUP_SAFETY_MARGIN_HOURS

DEFAULT_COVERAGE_WINDOW_HOURS = int(
    os.getenv("MARKET_SOURCE_COVERAGE_WINDOW_HOURS", str(120 * 24))
)

# -- windowed tick backfill (fixes flow_bias measured over inconsistent windows) --
#
# The bug this fixes: taking a fixed *count* of trade prints (e.g. "the last
# 100") gives every instrument a different *time* window -- ~2 seconds of
# prints on a hot pair, potentially many hours on a quiet one -- yet the
# resulting buy/sell ratio gets treated as the same kind of number regardless,
# and compared directly against a CEX taker-flow figure that always covers a
# fixed 1H bucket. The fix is to page by TIME instead of by COUNT: keep
# fetching pages of trades, oldest-first walk backward from "now", until a
# configured wall-clock window has been covered, not until N rows have been
# seen.
#
# _TICK_TARGET_WINDOW_MS_DEFAULT = 60_000 (60 seconds): chosen so every
# instrument's flow_bias describes the same slice of real time, which is the
# entire point of this fix. 60s specifically because: (a) it is short enough
# that a single get_market_result() call does not stall for long even on a
# quiet pair before the safety caps below kick in; (b) it is long enough on
# a typical perp instrument to accumulate well over the
# _MIN_TICKS_FOR_VALID_FLOW threshold (see orderflow.py) instead of racing
# past it in a fraction of a second; (c) it matches the cadence of every
# other "current instant" read in this class (order book, OI, sentiment) --
# none of those describe history either, they describe "right now", and 60s
# is a reasonable definition of "right now" for a flow measurement refreshed
# on every run.
#
# Safety valves -- a single hyperactive pair must never be allowed to turn a
# get_market_result() call into an unbounded loop of OKX requests:
#   _TICK_MAX_PAGES_DEFAULT: hard cap on HTTP calls per backfill, independent
#   of how long the window takes to cover. At _HISTORY_PAGE_SIZE=100 rows/page
#   this bounds a single backfill to at most 2,000 trade prints fetched,
#   however far short of the target window that leaves it (window_covered_ms
#   in the resulting payload will simply read low, and
#   OrderflowFeatureExtractor.insufficiency_reason() will say why the bias
#   is UNKNOWN if that undershoot is severe enough).
#   _TICK_MAX_WALL_SECONDS_DEFAULT: a second, independent cap on elapsed
#   wall-clock time, since _REQUEST_DELAY_SECONDS throttling means "number of
#   pages" and "how long this takes" are only loosely related. 30s leaves
#   headroom over the ~12s a full _TICK_MAX_PAGES_DEFAULT=20 pages would take
#   at the 0.6s/request throttle, while still bounding the worst case added
#   to a single call.
#
# OKX v5 docs uncertainty (verified from documentation only -- this module
# never calls OKX to confirm; see the task's "KHÔNG GỌI OKX" constraint):
#   - Pagination scheme assumed here mirrors the candle pagination already
#     implemented in _paginate_candles_raw() above: first page from
#     `/api/v5/market/trades` (the "latest N trades" endpoint, which serves
#     the newest prints without requiring a cursor), every subsequent page
#     from `/api/v5/market/history-trades` with `type=2` (timestamp-based
#     pagination) and `after=<oldest ts seen so far>` (docs describe `after`
#     as "return records earlier than the requested ts", i.e. walking
#     backward/older -- consistent with going further into the past on each
#     page, the same direction _paginate_candles_raw() walks).
#   - `before` is documented as only applicable to `type=1` (tradeId-based)
#     pagination, so it is not used here -- `after` alone drives the
#     backward walk for `type=2`.
#   - NOT CONFIRMED: whether `/api/v5/market/trades` truly needs no `type`/
#     `after` params for its first page (assumed yes, matching
#     `/api/v5/market/candles`'s behaviour), and whether `history-trades`
#     silently ignores an unrecognised trailing page vs. returning an empty
#     list vs. erroring -- this module treats an empty or short
#     (< page_size) response as "no more data" (`stop_reason="no_more_data"`),
#     the same convention `_paginate_candles_raw()` already uses for candles.
#   - NOT CONFIRMED: the exact `limit` ceiling for `/api/v5/market/trades`
#     itself (some OKX docs versions allow more than 100 there). This module
#     deliberately reuses `_HISTORY_PAGE_SIZE` (100) for both endpoints
#     rather than assuming a higher first-page limit that isn't confirmed --
#     conservative (more pages, never fewer than needed), never wrong.
# Anything else about `/api/v5/market/history-trades` behaviour should be
# re-verified against the live docs (not by calling OKX) before this code
# path is ever pointed at production traffic.
_TICK_TARGET_WINDOW_MS_DEFAULT = 60_000
_TICK_MAX_PAGES_DEFAULT = 20
_TICK_MAX_WALL_SECONDS_DEFAULT = 30.0

_MACRO_REFERENCE_SYMBOL = "BTC"
_MACRO_DEFAULT_WINDOW_HOURS = (
    720  # 30 days of hourly candles, matches build_macro_context.py
)
_MACRO_MIN_OVERLAP = 200
_MACRO_TREND_PCT = 3.0
_MACRO_HIGH_VOL_ANNUALISED_PCT = 80.0

_DEX_UNSUPPORTED_REASON = (
    "not applicable: LiveMarketDataSource only reads CEX via OKX; DEX needs a separate source"
)

# Raised (well, returned as the tuple's error string -- these three getters
# still follow the (payload, error) contract when the reason is structural,
# not a failed live fetch; see the "fail-closed" comment above get_ticks())
# whenever a DEX-only getter is asked about a symbol this instance cannot
# serve on DEX: either `dex_registry` was never supplied (this instance's
# default state -- see the class docstring) or the symbol is not one of the
# 5 assets DEX_ASSET_REGISTRY covers. Kept as one shared string (matching the
# pre-existing `_DEX_UNSUPPORTED_REASON`'s behaviour of not distinguishing
# these two cases either) so a caller cannot come to depend on wording that
# would need to change the day a 6th DEX asset is added to the registry.
_DEX_ASSET_NOT_IN_REGISTRY_REASON = (
    "not applicable: LiveMarketDataSource has no dex_registry configured for "
    "this asset (no token address to look up on DexScreener/GoPlus)"
)

# get_orderbook/get_open_interest/get_taker_volume/get_sentiment are CEX-only
# inputs not because OKX cannot answer a DEX asset's own instrument (PEPE-USDT-SWAP
# genuinely exists on OKX), but because the crawl this class must match never
# populated them for a DEX asset in the first place: `run_dex()` in
# Agent/none/scripts/crawl_market_data.py only ever calls candles/ticks/pool for a
# DEX asset, never orderbook/flow -- those steps only run inside `run_cex()`.
# Fabricating a live orderbook/OI/taker-flow/sentiment reading for a DEX asset
# would be new data the original crawl standard never had an equivalent for,
# exactly the kind of "cải tiến" that would make a live-vs-crawl comparison
# meaningless. market/service.py already grades all four NOT_APPLICABLE for a
# DEX asset regardless of what is returned here (see its `skip = is_dex`), so
# returning early costs nothing and, as a bonus, avoids 4 pointless OKX calls
# per DEX asset once DEX support is enabled.
_CEX_ONLY_INPUT_NOT_APPLICABLE_TO_DEX_REASON = (
    "not applicable: the original crawl never collected CEX-style orderbook/OI/"
    "taker-flow/sentiment for a DEX asset -- see dex_ticks for DEX order flow"
)

# Mirror of the reason above for the opposite direction: get_ticks/
# get_pool_liquidity/get_token_security are DEX-only inputs (the crawl only
# ever writes ticks_100ms_stream.json / pool_liquidity.json / token_security.json
# under Agent/data/dex/, never under Agent/data/cex/), so a CEX venue_type
# gets the same structural "not applicable" answer FileMarketDataSource would
# give (file not found) rather than this class attempting a DEX-shaped fetch
# for a CEX asset.
_DEX_ONLY_INPUT_NOT_APPLICABLE_TO_CEX_REASON = (
    "not applicable: dex_ticks/pool_liquidity/token_security only exist for "
    "the DEX venue in the original crawl"
)

# -- DexScreener + GoPlus: the two non-OKX providers the original crawl uses
# for pool_liquidity.json and token_security.json (see
# Agent/none/scripts/crawl_market_data.py::crawl_pool_liquidity() and
# Agent/none/scripts/crawl_token_security.py::crawl_asset()). Endpoint URLs, the
# price-tolerance constant, and the EVM chain-id map below are copied
# byte-for-byte from those two scripts so a live read walks the exact same
# request shape the crawl standard does.
_DEXSCREENER_TOKENS_URL = "https://api.dexscreener.com/latest/dex/tokens"
_GOPLUS_URL = "https://api.gopluslabs.io/api/v1"
_DEX_HTTP_TIMEOUT_SECONDS = 20

# Ported verbatim from crawl_market_data.py::POOL_PRICE_TOLERANCE. This is
# the exact bound that rejects a UNI/REN-style manipulated pool (see
# select_pool() below) -- changing it would change which pools pass, which is
# precisely the kind of "cải tiến" that would make a live-vs-crawl comparison
# meaningless.
_POOL_PRICE_TOLERANCE = 0.20

# Ported verbatim from crawl_token_security.py::EVM_CHAIN_IDS.
_GOPLUS_EVM_CHAIN_IDS = {
    "ETHEREUM": "1",
    "BSC": "56",
    "BASE": "8453",
    "ARBITRUM": "42161",
}

# Ported verbatim from crawl_market_data.py::refresh_dex_ticks()'s hardcoded
# `limit=100` -- see LiveMarketDataSource.get_ticks()'s docstring for why this
# must stay the default (fixed *count*, not the windowed/time-based fetch
# fetch_ticks_windowed() offers) despite that newer, arguably-more-consistent
# alternative existing right below in this same module.
_DEX_TICK_DEFAULT_COUNT = 100


def _dex_http_get_json(url: str, *, timeout: int = _DEX_HTTP_TIMEOUT_SECONDS) -> Any:
    """Minimal stdlib GET+JSON for DexScreener/GoPlus. No new dependency: uses
    `urllib.request`, the same stdlib module Agent/backend/okx/client.py's
    OkxClient is built on (reusing that pattern rather than the curl-subprocess
    `fetch()` helper the crawl scripts use, since that helper swallows any
    failure into a fake `{"code": "-1", ...}` payload -- fine for a crawler
    that already treats "no data" as "leave the file on disk alone", wrong
    here where fail-closed means a broken read must raise, never come back
    looking like a successful-but-empty one. Only the failure handling
    differs; the request itself -- same URL, same User-Agent -- is identical.

    Raises MarketDataUnavailableError (never returns a placeholder) on a
    connection failure, a non-2xx response, or a body that is not valid JSON.
    """
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise MarketDataUnavailableError(
            f"Could not connect to {url}: {exc}"
        ) from exc
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketDataUnavailableError(
            f"Response from {url} is not valid JSON: {exc}"
        ) from exc
    return payload


def _select_pool(
    pairs: List[Dict[str, Any]], chain: str, reference: float
) -> Tuple[Optional[Tuple[float, float, Dict[str, Any]]], int]:
    """Deepest pool on the chain whose price agrees with the exchange reference.

    Ported verbatim from crawl_market_data.py::select_pool() (same tolerance
    constant, same "check price before liquidity" order, same tie-break) --
    this is the exact fix for the UNI/REN case referenced in this module's
    class docstring: sorting by liquidity alone walks straight into the
    manipulated pool claiming 43,000,000 USD/UNI and 1.3B of liquidity, so
    every pool whose price disagrees with the CEX reference is discarded
    before liquidity is even looked at.

    Returns ((liquidity_usd, price_usd, pair), rejected_count).
    """
    wanted = chain.lower()
    accepted: List[Tuple[float, float, Dict[str, Any]]] = []
    rejected = 0
    for pair in pairs:
        if wanted and str(pair.get("chainId", "")).lower() != wanted:
            continue
        try:
            price = float(pair["priceUsd"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0 or abs(price - reference) / reference > _POOL_PRICE_TOLERANCE:
            rejected += 1
            continue
        liquidity = float((pair.get("liquidity") or {}).get("usd") or 0.0)
        accepted.append((liquidity, price, pair))
    if not accepted:
        return None, rejected
    return max(accepted, key=lambda item: item[0]), rejected


def _as_bool(raw: Any) -> Optional[bool]:
    """Ported verbatim from crawl_token_security.py::as_bool(). GoPlus answers
    "1"/"0"; anything else means the provider did not answer."""
    if raw in ("1", 1, True):
        return True
    if raw in ("0", 0, False):
        return False
    return None


def _as_float(raw: Any) -> Optional[float]:
    """Ported verbatim from crawl_token_security.py::as_float()."""
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _top10_holder_pct(holders: Any) -> Optional[float]:
    """Ported verbatim from crawl_token_security.py::top10_pct()."""
    if not isinstance(holders, list) or not holders:
        return None
    rows = [h for h in holders[:10] if isinstance(h, dict)]
    shares = [_as_float(h.get("percent")) for h in rows]
    shares = [s for s in shares if s is not None]
    if not shares:
        return None
    total = sum(shares)
    if total == 0.0 and any((_as_float(h.get("balance")) or 0.0) > 0.0 for h in rows):
        # Wrapped SOL reports total_supply 0, so GoPlus prints percent "0" for
        # every holder. Zero here means "could not compute", not "no
        # concentration".
        return None
    return min(100.0, total * 100.0)


def _lp_locked(lp_holders: Any) -> Optional[bool]:
    """Ported verbatim from crawl_token_security.py::lp_locked()."""
    if not isinstance(lp_holders, list) or not lp_holders:
        return None
    return any(
        str(h.get("is_locked")) == "1" for h in lp_holders if isinstance(h, dict)
    )


def _parse_evm_security(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ported verbatim from crawl_token_security.py::parse_evm()."""
    buy_tax, sell_tax = (
        _as_float(record.get("buy_tax")),
        _as_float(record.get("sell_tax")),
    )
    return {
        "is_honeypot": _as_bool(record.get("is_honeypot")),
        # GoPlus reports taxes as a fraction; the schema wants percent.
        "buy_tax": buy_tax * 100.0 if buy_tax is not None else None,
        "sell_tax": sell_tax * 100.0 if sell_tax is not None else None,
        "is_mintable": _as_bool(record.get("is_mintable")),
        "is_blacklisted": _as_bool(record.get("is_blacklisted")),
        "top10_holder_pct": _top10_holder_pct(record.get("holders")),
        "liquidity_locked": _lp_locked(record.get("lp_holders")),
        "holder_count": _as_float(record.get("holder_count")),
        "security_score": None,
    }


def _parse_solana_security(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ported verbatim from crawl_token_security.py::parse_solana()."""
    mintable = record.get("mintable")
    metadata = record.get("metadata_mutable")
    return {
        # Solana has no honeypot/tax equivalent in this feed; leave unanswered.
        "is_honeypot": None,
        "buy_tax": None,
        "sell_tax": None,
        "is_mintable": _as_bool((mintable or {}).get("status")),
        "is_blacklisted": _as_bool((record.get("freezable") or {}).get("status")),
        "top10_holder_pct": _top10_holder_pct(record.get("holders")),
        "liquidity_locked": None,
        "metadata_mutable": _as_bool((metadata or {}).get("status")),
        "security_score": None,
    }


def _now_ms() -> int:
    return int(time.time() * 1000)


def _looks_rate_limited(exc: BaseException) -> bool:
    """True if `exc` looks like OKX (or something in front of it) telling this
    client to slow down, rather than an ordinary request failure.

    Drives AdaptiveThrottle.record_blocked() (Việc 2) -- see that class's
    docstring for why this signal must never be missed: a false positive here
    just costs a bit of speed, a false negative risks the shared-IP ban this
    whole design exists to avoid. See _RATE_LIMIT_OKX_CODES above for why
    "50011" is the primary signal and "429"/"too many requests" text is only
    a fallback.
    """
    if isinstance(exc, OkxApiError):
        if str(exc.code) in _RATE_LIMIT_OKX_CODES:
            return True
        text = f"{exc.code} {exc.msg}".lower()
    elif isinstance(exc, OkxTransportError):
        text = str(exc).lower()
    else:
        return False
    return "429" in text or "too many request" in text or "rate limit" in text


def _flow_label(ratio: Optional[float]) -> str:
    if ratio is None:
        return "UNKNOWN"
    if ratio >= 1.2:
        return "BULLISH_AGGRESSIVE (aggressive buy pressure dominates)"
    if ratio <= 0.8:
        return "BEARISH_AGGRESSIVE (aggressive sell-off dominates)"
    return "BALANCED (buy and sell pressure balanced)"


def _sentiment_label(ls_ratio: float) -> str:
    if ls_ratio >= 1.2:
        return "BULLISH (longs dominate)"
    if ls_ratio <= 0.83:
        return "BEARISH (shorts dominate)"
    return "NEUTRAL (longs and shorts balanced)"


# -- macro correlation math, ported verbatim from Agent/none/scripts/build_macro_context.py --


def _log_returns(closes: Dict[int, float], stamps: List[int]) -> List[float]:
    out = []
    for prev, curr in zip(stamps[:-1], stamps[1:], strict=False):
        a, b = closes.get(prev), closes.get(curr)
        if a and b and a > 0 and b > 0:
            out.append(math.log(b / a))
    return out


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    # HAI CHUỖI PHẢI BẰNG ĐỘ DÀI. `n` lấy từ `xs` rồi dùng luôn để chia
    # trung bình của `ys`, nên lệch độ dài không chỉ làm `zip` cắt cụt mà
    # còn cho ra MỘT TRUNG BÌNH SAI -- hệ số tương quan khi đó sai âm thầm,
    # không có dấu hiệu nào. Nơi gọi duy nhất hiện cắt cả hai về
    # `min(len(...))` trước khi gọi, nên điều kiện này luôn đúng; khẳng định
    # nó ở đây để một nơi gọi mới không lặng lẽ phá.
    if len(xs) != len(ys):
        raise ValueError(
            f"_pearson cần hai chuỗi bằng độ dài, nhận {len(xs)} và {len(ys)}"
        )
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return max(-1.0, min(1.0, cov / math.sqrt(vx * vy)))


def _beta(asset_returns: List[float], ref_returns: List[float]) -> Optional[float]:
    # Cùng lý do như `_pearson` ngay trên: `n` lấy từ chuỗi thứ nhất nhưng
    # dùng để chia trung bình của chuỗi thứ hai. Beta nuôi ống kính
    # `market_alignment`, nên một con số sai ở đây đi thẳng vào điểm rủi ro.
    if len(asset_returns) != len(ref_returns):
        raise ValueError(
            f"_beta cần hai chuỗi bằng độ dài, nhận "
            f"{len(asset_returns)} và {len(ref_returns)}"
        )
    n = len(asset_returns)
    if n < 2:
        return None
    ma, mr = sum(asset_returns) / n, sum(ref_returns) / n
    cov = sum((a - ma) * (r - mr) for a, r in zip(asset_returns, ref_returns, strict=False))
    var = sum((r - mr) ** 2 for r in ref_returns)
    return cov / var if var > 0 else None


def _reference_regime(ref_returns: List[float]) -> Tuple[str, float, float]:
    total = math.exp(sum(ref_returns)) - 1.0
    trend_pct = total * 100.0
    n = len(ref_returns)
    mean = sum(ref_returns) / n
    hourly_sd = math.sqrt(sum((r - mean) ** 2 for r in ref_returns) / n)
    vol_pct = hourly_sd * math.sqrt(24 * 365) * 100.0

    if vol_pct >= _MACRO_HIGH_VOL_ANNUALISED_PCT:
        regime = "RISK_OFF_VOLATILE" if trend_pct < 0 else "RISK_ON_VOLATILE"
    elif trend_pct >= _MACRO_TREND_PCT:
        regime = "RISK_ON"
    elif trend_pct <= -_MACRO_TREND_PCT:
        regime = "RISK_OFF"
    else:
        regime = "NEUTRAL"
    return regime, trend_pct, vol_pct


class AdaptiveThrottle:
    """Runtime request pacing for LiveMarketDataSource's OKX calls (Việc 2).

    Replaces a single fixed inter-request delay with one that adapts: it
    starts at `initial_delay_seconds`, nudges GENTLY faster after a long run
    of clean responses, and snaps back HARD the instant OKX (or anything in
    front of it) signals it's unhappy. This asymmetry is deliberate, not an
    accident of tuning: one throttled/banned request is far more expensive
    (retries, cooldowns, or in the worst case an IP ban shared by every other
    process talking to OKX from this host) than running a few requests/second
    below the true ceiling for a while -- see the module comment above
    _ADAPTIVE_MIN_DELAY_SECONDS for the fuller reasoning this class
    implements. `enabled=False` on LiveMarketDataSource (or the
    MARKET_SOURCE_ADAPTIVE_THROTTLE=false env escape hatch) skips this class
    entirely and reverts to the plain fixed-delay behaviour it replaces.

    `clock`/`sleep` are injectable purely so tests can drive this with a fake
    clock instead of real wall-clock time (per this task's explicit "dùng
    đồng hồ giả, đừng sleep thật" requirement) -- production code never
    passes them, so both default to the real `time` functions.
    """

    def __init__(
        self,
        *,
        initial_delay_seconds: float = _REQUEST_DELAY_SECONDS,
        min_delay_seconds: float = _ADAPTIVE_MIN_DELAY_SECONDS,
        max_delay_seconds: float = _ADAPTIVE_MAX_DELAY_SECONDS,
        speedup_after_clean: int = _ADAPTIVE_SPEEDUP_AFTER_CLEAN,
        speedup_factor: float = _ADAPTIVE_SPEEDUP_FACTOR,
        backoff_factor: float = _ADAPTIVE_BACKOFF_FACTOR,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.delay_seconds = initial_delay_seconds
        self.min_delay_seconds = min_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.speedup_after_clean = speedup_after_clean
        self.speedup_factor = speedup_factor
        self.backoff_factor = backoff_factor
        self._clean_streak = 0
        self._last_request_at: Optional[float] = None
        self._clock = clock
        self._sleep = sleep
        # Việc 1 (song song hoá theo số nguồn dữ liệu): trước bản sửa này,
        # một `LiveMarketDataSource`/`AdaptiveThrottle` DUY NHẤT được
        # `WebDataService` tạo một lần rồi dùng lại cho mọi lời gọi -- kể cả
        # khi `pipeline.py`/`cohort.py` giờ giải thị trường CHÍNH và PHỤ trên
        # hai luồng cùng lúc, hay `mcp/service.py` giải nhiều mã song song.
        # Không có khoá, hai luồng cùng đọc `_last_request_at`/`delay_seconds`
        # rồi cùng kết luận "chưa tới hạn, đi luôn" -- phá nhịp thực tế đạt
        # được (có thể vượt xa ~1.8 req/s và khiến OKX chặn IP), đúng thứ
        # `_last_request_at`/`delay_seconds` tồn tại để ngăn. Khoá này CHỈ
        # bảo vệ đúng đoạn "đọc trạng thái + đặt chỗ lượt kế tiếp" (xem
        # `wait()`) -- việc `_sleep()` thật sự luôn nằm NGOÀI khoá, để một
        # luồng đang ngủ chờ tới lượt không chặn luồng khác đặt chỗ hay chặn
        # luồng khác đang chờ HTTP response của chính nó.
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block (via the injected `sleep`) until the current pace allows the
        next request to go out. An toàn khi gọi đồng thời từ nhiều luồng --
        xem `_lock` ở `__init__` cho lý do và cách khoá được dùng."""
        with self._lock:
            if self._last_request_at is not None:
                elapsed = self._clock() - self._last_request_at
                remaining = self.delay_seconds - elapsed
            else:
                remaining = 0.0
            remaining = max(remaining, 0.0)
            # Đặt chỗ lượt kế tiếp NGAY trong khoá, dùng thời điểm DỰ KIẾN
            # gửi request (bây giờ + remaining) chứ không phải thời điểm sau
            # khi ngủ xong -- để một luồng khác gọi wait() ngay sau đó thấy
            # đúng lượt đã bị chiếm và tự xếp hàng sau nó, thay vì cả hai
            # cùng thấy "còn trống" và cùng gửi request gần như đồng thời.
            self._last_request_at = self._clock() + remaining
        if remaining > 0:
            self._sleep(remaining)

    def record_success(self) -> None:
        """One more request went through clean. Only nudges the pace after a
        streak of `speedup_after_clean` in a row -- one lucky request right
        after a backoff must not immediately start climbing again -- and only
        ever moves DOWN toward `min_delay_seconds`, by `speedup_factor` at a
        time. See the class docstring for why this step must stay gentle.
        An toàn đa luồng: xem `_lock` ở `__init__`."""
        with self._lock:
            self._clean_streak += 1
            if self._clean_streak < self.speedup_after_clean:
                return
            self._clean_streak = 0
            new_delay = max(
                self.min_delay_seconds, self.delay_seconds * self.speedup_factor
            )
            if new_delay < self.delay_seconds:
                self.delay_seconds = new_delay
                changed = True
            else:
                changed = False
        if changed:
            print(
                f"  [OKX throttle] {self.speedup_after_clean} consecutive clean "
                f"requests -- speeding up to {self.rate_description()}."
            )

    def record_blocked(self) -> None:
        """OKX (or something in front of it) signalled it's unhappy. Backs
        off immediately by `backoff_factor`, capped at `max_delay_seconds` --
        never waits for a streak the way record_success() does, see the class
        docstring for why. An toàn đa luồng: xem `_lock` ở `__init__`."""
        with self._lock:
            self._clean_streak = 0
            self.delay_seconds = min(
                self.max_delay_seconds, self.delay_seconds * self.backoff_factor
            )
        print(
            f"  [OKX throttle] Rate-limit signal detected -- backing off "
            f"immediately to {self.rate_description()}."
        )

    def rate_description(self) -> str:
        """Human-readable current pace, for progress/backoff log lines (this
        task's "in ra nhịp thực tế đạt được" requirement)."""
        rate = (1.0 / self.delay_seconds) if self.delay_seconds > 0 else float("inf")
        return f"{rate:.2f} req/s ({self.delay_seconds:.3f}s/request)"


class CandleCache:
    """On-disk cache of CLOSED 1H candles, keyed by instrument.

    Candles are immutable once their hour has closed (the candle timestamped
    2024-03-12 03:00 UTC will never be revised), so once an hour is on disk it
    never needs to be re-fetched. Only the still-forming candle -- the one OKX
    itself flags with `confirm: "0"` -- is excluded, since its own OHLCV values
    keep changing until the hour closes; writing it to the cache would mean the
    cache silently going stale/wrong the moment the next trade prints.
    """

    def __init__(self, cache_dir: Optional[Path] = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self.cache_dir = (
            Path(cache_dir)
            if cache_dir
            else Path(config.DATA_DIR) / "market" / "cache" / "candles"
        )

    def _path(self, inst_id: str, bar: str) -> Path:
        return self.cache_dir / f"{inst_id}_{bar}.json"

    def load(self, inst_id: str, bar: str) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        path = self._path(inst_id, bar)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            # A corrupt cache file is treated as "no cache" -- re-fetching from
            # OKX is slow but always correct, whereas trusting a half-written
            # or truncated cache file could silently feed bad candles forward.
            return []
        candles = payload.get("candles")
        return candles if isinstance(candles, list) else []

    def save(
        self,
        inst_id: str,
        bar: str,
        candles: List[Dict[str, Any]],
        *,
        history_exhausted: bool = False,
    ) -> None:
        if not self.enabled or not candles:
            return
        path = self._path(inst_id, bar)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Monotonic: once a previous save recorded "OKX has no candles older
        # than this for this instrument" (Việc 3 -- see
        # is_history_exhausted()'s docstring), an ordinary tail-refresh save
        # that has no way to know that fact (it never walks back far enough
        # to find out) must not silently erase the record by defaulting
        # `history_exhausted` back to False.
        history_exhausted = history_exhausted or self.is_history_exhausted(inst_id, bar)
        payload = {
            "instId": inst_id,
            "bar": bar,
            "cached_through_ts": candles[-1]["timestamp"],
            "total_candles": len(candles),
            "history_exhausted": history_exhausted,
            "candles": candles,
        }
        # Atomic write: a crash or an interrupted process mid-write must never
        # leave a half-written JSON file that then makes every future run treat
        # the whole cache as corrupt (see load() above) and re-download it from
        # scratch. Writing to a sibling temp file first and only `os.replace`ing
        # it onto the real path once the write is complete means the real path
        # is always either the old complete file or the new complete file, and
        # os.replace is atomic on both POSIX and Windows.
        tmp_path = path.with_name(path.name + f".tmp{os.getpid()}")
        tmp_path.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp_path, path)

    def is_history_exhausted(self, inst_id: str, bar: str) -> bool:
        """True once a previous backfill walked all the way back to the
        oldest candle OKX has for this instrument (Việc 3).

        Used by LiveMarketDataSource._fetch_with_cache() to stop asking OKX
        for more history once there genuinely isn't any: without this, an
        instrument younger than the configured depth (e.g. a newly-listed
        asset, or any cache built before this task's depth limiting existed)
        would trigger a wasted "extend the cache backward" attempt on EVERY
        single call forever, since `len(cached) < required_count` stays true
        no matter how many times OKX is asked and answers with nothing more.
        """
        if not self.enabled:
            return False
        path = self._path(inst_id, bar)
        if not path.exists():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return False
        return bool(payload.get("history_exhausted", False))


class LiveMarketDataSource(MarketDataSource):
    """Reads CEX market inputs straight from OKX's public v5 REST API, and --
    when constructed with `dex_registry` -- the 5 DEX assets' inputs from
    OKX (dex_ticks) plus DexScreener and GoPlus (dex_pool_liquidity,
    token_security).

    Historical candles are served from `candle_cache` wherever possible (only
    the tail since the cache was last written, plus the still-open candle, is
    ever fetched from OKX); every other input describes the current instant and
    is always fetched live. Pass `cache_enabled=False` (or a `CandleCache` built
    with `enabled=False`) for a zero-cache mode that re-downloads the full
    history every call -- correct but slow, for anyone who wants it.

    `dex_registry` defaults to `None`, which keeps every pre-existing
    behaviour of this class exactly as it was before DEX support existed:
    `resolve_venue(..., "DEX")` still raises `MarketDataUnavailableError`, and
    the three DEX-only getters still answer with the structural
    "not applicable" tuple they always have. Pass
    `Agent.backend.external.sources.dex_registry.DEX_ASSET_REGISTRY` (or a subset of
    it) to enable live DEX reads for the symbols it covers -- see that
    module's docstring for why a static table is required at all (there is no
    way to derive a token's on-chain contract address from its ticker) and
    exactly where every value in it came from.
    """

    def __init__(
        self,
        client: Optional[OkxClient] = None,
        candle_cache: Optional[CandleCache] = None,
        cache_enabled: bool = True,
        max_history_candles: Optional[int] = None,
        coverage_window_hours: Optional[int] = None,
        as_of_ms: Optional[int] = None,
        macro_window_hours: int = _MACRO_DEFAULT_WINDOW_HOURS,
        page_size: int = _HISTORY_PAGE_SIZE,
        request_delay_seconds: float = _REQUEST_DELAY_SECONDS,
        adaptive_throttle: bool = _ADAPTIVE_THROTTLE_ENABLED_DEFAULT,
        throttle: Optional["AdaptiveThrottle"] = None,
        dex_registry: Optional[Mapping[str, DexAssetInfo]] = None,
    ) -> None:
        # OkxClient() never raises for missing credentials -- only the signed
        # get()/post() path needs them, and every call this class makes goes
        # through public_get(), which deliberately never sends auth headers.
        self._client = client or OkxClient()
        self._candle_cache = (
            candle_cache
            if candle_cache is not None
            else CandleCache(enabled=cache_enabled)
        )
        # Explicit hard cap only -- unchanged meaning from before this task.
        # A caller that leaves this at None (the default) gets a bounded
        # depth computed by _effective_depth_candles() instead of "fetch
        # everything OKX has" (Việc 1): see `coverage_window_hours`/
        # `as_of_ms` below and the constants block above this class.
        self.max_history_candles = max_history_candles
        self.coverage_window_hours = coverage_window_hours
        self.as_of_ms = as_of_ms
        self.macro_window_hours = macro_window_hours
        self._page_size = page_size
        self._request_delay_seconds = request_delay_seconds
        self._ct_val_cache: Dict[str, float] = {}
        self._last_request_monotonic: Optional[float] = None
        # Việc 2: adaptive pacing replaces the fixed per-request sleep unless
        # explicitly disabled. `min_delay_seconds` is clamped to never exceed
        # the caller's own `request_delay_seconds`: this matters because
        # every test in this repo that wants "no throttling at all, this is a
        # fake client" passes request_delay_seconds=0.0 -- without the clamp,
        # a long enough clean streak in one of those tests (including in
        # other test files this task must not modify, e.g. test_dex_source.py
        # / test_tick_stream.py) would eventually nudge the pace up to
        # _ADAPTIVE_MIN_DELAY_SECONDS and start sleeping for real.
        if throttle is not None:
            self._adaptive_throttle: Optional[AdaptiveThrottle] = throttle
        elif adaptive_throttle:
            self._adaptive_throttle = AdaptiveThrottle(
                initial_delay_seconds=request_delay_seconds,
                min_delay_seconds=min(
                    _ADAPTIVE_MIN_DELAY_SECONDS, request_delay_seconds
                ),
            )
        else:
            self._adaptive_throttle = None
        # Opt-in DEX support -- see the class docstring for why this defaults
        # to None (disabled) rather than to DEX_ASSET_REGISTRY.
        self._dex_registry = dex_registry

    def _effective_depth_candles(self) -> Optional[int]:
        """How many 1H candles get_candles() should ensure are on hand for
        this instrument, oldest included -- see the Việc 1 constants block
        above this class for exactly where every term below comes from.

        `max_history_candles` set explicitly always wins (unchanged from
        before this method existed -- a caller that wants a literal hard cap,
        e.g. a test bounding a fixture's page count, still gets exactly
        that). Otherwise the depth is COVERAGE (explicit
        `coverage_window_hours` or DEFAULT_COVERAGE_WINDOW_HOURS) +
        CANDLE_WARMUP_BUFFER_HOURS, widened further if `as_of_ms` names a
        moment in the past: this is a LIVE source, get_candles() always walks
        back from the real "now" regardless of `as_of_ms` (every hour between
        a past `as_of_ms` and now gets fetched anyway -- harmless, since
        extra recent candles never hurt either consumer this depth is sized
        for), so that gap has to be counted into the required depth or the
        warmup buffer *before* `as_of_ms` would silently come up short.
        """
        if self.max_history_candles is not None:
            return self.max_history_candles
        coverage_hours = (
            self.coverage_window_hours
            if self.coverage_window_hours is not None
            else DEFAULT_COVERAGE_WINDOW_HOURS
        )
        total_hours = coverage_hours + CANDLE_WARMUP_BUFFER_HOURS
        if self.as_of_ms is not None:
            staleness_ms = max(0, _now_ms() - int(self.as_of_ms))
            total_hours += staleness_ms // _BAR_MS
        return total_hours

    # -- DEX asset lookup ------------------------------------------------------ #

    def _dex_asset(self, symbol: str) -> Optional[DexAssetInfo]:
        if self._dex_registry is None:
            return None
        return self._dex_registry.get(symbol)

    # -- transport ---------------------------------------------------------- #

    def _throttle(self) -> None:
        if self._adaptive_throttle is not None:
            self._adaptive_throttle.wait()
            return
        # Fixed-pace fallback -- unchanged from before adaptive pacing
        # existed. Reached via adaptive_throttle=False or the
        # MARKET_SOURCE_ADAPTIVE_THROTTLE=false env escape hatch.
        if self._last_request_monotonic is not None:
            elapsed = time.monotonic() - self._last_request_monotonic
            if elapsed < self._request_delay_seconds:
                time.sleep(self._request_delay_seconds - elapsed)
        self._last_request_monotonic = time.monotonic()

    def _public_get(self, path: str, params: Dict[str, Any]) -> Any:
        self._throttle()
        try:
            data = self._client.public_get(path, params)
        except (OkxApiError, OkxTransportError) as exc:
            if self._adaptive_throttle is not None and _looks_rate_limited(exc):
                # Việc 2: back off decisively the instant OKX signals it's
                # unhappy, before this failure is even re-raised below.
                self._adaptive_throttle.record_blocked()
            # Fail-closed: an OKX error must surface as a raised exception, not
            # degrade into an empty payload that looks like "collected but
            # empty" to MarketService -- that is exactly what makes Logic 2
            # grade an asset UNKNOWN instead of reporting the real failure.
            raise MarketDataUnavailableError(
                f"OKX error calling {path} (params={params}): {exc}"
            ) from exc
        if self._adaptive_throttle is not None:
            self._adaptive_throttle.record_success()
        return data

    def _contract_size(self, inst_id: str) -> float:
        """Coins per contract (ctVal). OKX book/volume sizes are in contracts."""
        if inst_id in self._ct_val_cache:
            return self._ct_val_cache[inst_id]
        data = self._public_get(
            "/api/v5/public/instruments", {"instType": "SWAP", "instId": inst_id}
        )
        try:
            ct_val = float(data[0]["ctVal"])
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise MarketDataUnavailableError(
                f"Could not get ctVal for {inst_id}; cannot convert contracts to coins"
            ) from exc
        self._ct_val_cache[inst_id] = ct_val
        return ct_val

    def _last_price(self, inst_id: str) -> float:
        data = self._public_get("/api/v5/market/ticker", {"instId": inst_id})
        try:
            return float(data[0]["last"])
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise MarketDataUnavailableError(
                f"Could not get the latest price for {inst_id}"
            ) from exc

    # -- venue --------------------------------------------------------------- #

    def resolve_venue(self, symbol: str, venue_type: Optional[str]) -> str:
        requested = venue_type.upper() if venue_type else None
        if requested not in (None, "CEX", "DEX"):
            raise ValueError("venue_type must be CEX or DEX")
        if requested == "DEX":
            # Unconfigured (the default -- see class docstring) or an asset
            # DEX_ASSET_REGISTRY does not cover: identical to this method's
            # original unconditional raise, just now reached only when DEX
            # support genuinely cannot be served, not for every DEX request.
            if self._dex_asset(symbol) is None:
                raise MarketDataUnavailableError(
                    "LiveMarketDataSource only reads CEX via OKX; DEX (pool liquidity, "
                    "token security) needs DexScreener/a separate security provider "
                    "plus a static pool-address mapping -- there is no equivalent OKX "
                    "source, and it is out of scope for this data source."
                )
            return "DEX"
        # requested is None or "CEX": unchanged from before DEX support
        # existed. Auto-detect (requested is None) always resolves to CEX
        # here, never DEX -- a caller that wants a DEX read has to ask for it
        # explicitly, same as before this method could ever succeed for DEX.
        return "CEX"

    # -- candles (cached historical + live tail) ------------------------------ #

    @staticmethod
    def _to_candle_dict(row: List[Any]) -> Dict[str, Any]:
        ts = int(row[0])
        return {
            "timestamp": ts,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts / 1000)),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "vol": float(row[5]),
            "volCcy": float(row[6]),
            "volCcyQuote": float(row[7]),
        }

    def _paginate_candles_raw(
        self,
        inst_id: str,
        bar: str,
        *,
        target_count: Optional[int] = None,
        stop_at_ts: Optional[int] = None,
        progress_label: str = "",
    ) -> Tuple[List[List[Any]], str]:
        """Walk backward from "now" collecting raw OKX candle rows.

        Stops once `target_count` rows are collected, once the walk has gone
        back past `stop_at_ts`, or once OKX has no older data left -- whichever
        comes first. The first page always hits `market/candles` (the only
        endpoint willing to hand back the still-forming candle); every
        subsequent page switches to `history-candles`, since `market/candles`
        does not paginate arbitrarily far into the past on every bar size.

        Returns `(rows, stop_reason)` -- stop_reason is one of "target_count",
        "stop_at_ts", or "no_more_data" (OKX had nothing older left for this
        instrument), mirroring fetch_ticks_windowed()'s stop_reason
        convention elsewhere in this module. _fetch_with_cache uses
        "no_more_data" on a cold backfill to mark
        CandleCache.is_history_exhausted() (Việc 3): otherwise an instrument
        younger than the configured depth would trigger a wasted
        "extend the cache backward" attempt on every single future call.
        """
        collected: Dict[int, List[Any]] = {}
        cursor = ""
        page = 0
        endpoint = "/api/v5/market/candles"
        stop_reason = "no_more_data"
        while True:
            params: Dict[str, Any] = {
                "instId": inst_id,
                "bar": bar,
                "limit": self._page_size,
            }
            if cursor:
                params["after"] = cursor
            batch = self._public_get(endpoint, params)
            if not isinstance(batch, list) or not batch:
                stop_reason = "no_more_data"
                break
            oldest_in_batch = int(batch[-1][0])
            for row in batch:
                ts = int(row[0])
                if stop_at_ts is not None and ts <= stop_at_ts:
                    continue
                collected[ts] = row
            page += 1
            cursor = str(oldest_in_batch)
            endpoint = "/api/v5/market/history-candles"
            if page == 1 or page % _PROGRESS_EVERY == 0:
                print(
                    f"  [OKX candles] {inst_id} {progress_label}: "
                    f"{len(collected)} candles, page {page}..."
                )
            if target_count is not None and len(collected) >= target_count:
                stop_reason = "target_count"
                break
            if stop_at_ts is not None and oldest_in_batch <= stop_at_ts:
                stop_reason = "stop_at_ts"
                break
            if len(batch) < self._page_size:
                stop_reason = "no_more_data"  # OKX has no older data left
                break
        if page:
            print(
                f"  [OKX candles] {inst_id} {progress_label}: done "
                f"-- {len(collected)} candles, {page} pages.{self._pace_suffix()}"
            )
        return list(collected.values()), stop_reason

    def _pace_suffix(self) -> str:
        """ " -- nhịp hiện tại X req/s" for a completion log line, or "" when
        adaptive pacing is off (Việc 2's "in ra nhịp thực tế đạt được")."""
        if self._adaptive_throttle is None:
            return ""
        return f" Current pace: {self._adaptive_throttle.rate_description()}."

    def _paginate_candles_backward(
        self, inst_id: str, bar: str, *, before_ts: int, target_count: int
    ) -> Tuple[List[List[Any]], bool]:
        """Walk further into the past than `before_ts`, collecting up to
        `target_count` older raw OKX candle rows.

        Only used to grow an existing cache backward (Việc 3 -- see
        _fetch_with_cache below) when a later call needs more history than a
        previous run cached. Unlike _paginate_candles_raw, this never touches
        `/api/v5/market/candles` (the "latest" endpoint): every row wanted
        here is already older than `before_ts`, i.e. strictly historical, so
        it starts straight from `/api/v5/market/history-candles` with
        `after=before_ts` -- the exact continuation point history-candles
        pagination would have reached had the original backfill kept walking
        instead of stopping at `before_ts`.

        Returns `(rows, exhausted)` -- `exhausted=True` means OKX ran out of
        older data before `target_count` was reached, i.e. this instrument's
        entire history is now accounted for. _fetch_with_cache uses this to
        mark CandleCache.is_history_exhausted() so it never retries a request
        that can only ever come back short again.
        """
        collected: List[List[Any]] = []
        cursor = str(before_ts)
        page = 0
        exhausted = False
        while len(collected) < target_count:
            batch = self._public_get(
                "/api/v5/market/history-candles",
                {
                    "instId": inst_id,
                    "bar": bar,
                    "limit": self._page_size,
                    "after": cursor,
                },
            )
            if not isinstance(batch, list) or not batch:
                exhausted = True
                break
            collected.extend(batch)
            cursor = str(int(batch[-1][0]))
            page += 1
            if page == 1 or page % _PROGRESS_EVERY == 0:
                print(
                    f"  [OKX candles] {inst_id} backfilling older candles: "
                    f"{len(collected)}/{target_count}, page {page}..."
                )
            if len(batch) < self._page_size:
                exhausted = True
                break  # OKX has no older data left for this instrument
        if page:
            print(
                f"  [OKX candles] {inst_id} backfilling older candles: done -- "
                f"{len(collected)} candles, {page} pages.{self._pace_suffix()}"
            )
        return collected, exhausted

    def _fetch_full_history(
        self, inst_id: str, bar: str, required_count: Optional[int]
    ) -> List[Dict[str, Any]]:
        depth_msg = (
            f"fetching the {required_count} most recent candles from OKX (bounded by "
            "analysis needs instead of full history -- see CANDLE_WARMUP_BUFFER_HOURS "
            "/ DEFAULT_COVERAGE_WINDOW_HOURS in this module)..."
            if required_count is not None
            else "re-fetching the full history from OKX (a long-lived asset can take several minutes)..."
        )
        print(
            f"  [OKX candles] {inst_id}: zero-cache mode -- cache disabled, "
            f"{depth_msg}"
        )
        raw, _stop_reason = self._paginate_candles_raw(
            inst_id,
            bar,
            target_count=required_count,
            progress_label="zero-cache",
        )
        rows = sorted(raw, key=lambda r: int(r[0]))
        return [self._to_candle_dict(r) for r in rows]

    def _fetch_with_cache(
        self, inst_id: str, bar: str, required_count: Optional[int]
    ) -> List[Dict[str, Any]]:
        cached = self._candle_cache.load(inst_id, bar)
        newest_cached_ts = int(cached[-1]["timestamp"]) if cached else None

        if newest_cached_ts is None:
            depth_msg = (
                f"{required_count} most recent candles (bounded by analysis needs)"
                if required_count is not None
                else "the full history"
            )
            print(
                f"  [OKX candles] {inst_id}: no cache yet -- fetching {depth_msg} for "
                "the first time, then caching it (a one-time cost)..."
            )
        # 1) Always fetch the fresh tail: everything closed since the cache
        #    was last written, plus whatever candle is still open right now.
        #    For an empty cache this doubles as the very first backfill,
        #    bounded by `required_count` (Việc 1) instead of walking every
        #    page OKX has.
        cold_backfill = newest_cached_ts is None
        raw, stop_reason = self._paginate_candles_raw(
            inst_id,
            bar,
            target_count=required_count if cold_backfill else None,
            stop_at_ts=newest_cached_ts,
            progress_label="filling cache" if cold_backfill else "fetching tail",
        )
        rows = sorted(raw, key=lambda r: int(r[0]))
        # OKX's own `confirm` column (index 8): "1" once the hour has closed,
        # "0" while it is still forming. Only "1" rows are safe to persist.
        closed_rows = [r for r in rows if len(r) > 8 and str(r[8]) == "1"]
        open_rows = [r for r in rows if len(r) > 8 and str(r[8]) != "1"]

        if closed_rows:
            merged = cached + [self._to_candle_dict(r) for r in closed_rows]
            merged.sort(key=lambda c: c["timestamp"])
            # A cold backfill that ran out of OKX history before reaching
            # `required_count` means this instrument's ENTIRE history is now
            # cached -- record that so step 2 below never wastes a call
            # trying to fetch more of it on a future run (see
            # CandleCache.is_history_exhausted()'s docstring).
            self._candle_cache.save(
                inst_id,
                bar,
                merged,
                history_exhausted=cold_backfill and stop_reason == "no_more_data",
            )
            cached = merged

        # 2) Việc 3 -- backward extension: a later call may need MORE history
        #    than a previous run ever cached (coverage_window_hours grew, or
        #    the cache predates this depth-limiting change entirely and only
        #    holds however much an older run happened to fetch). Fetch only
        #    the missing OLDER slice, never the whole thing again, and never
        #    silently hand back fewer candles than `required_count` asks for
        #    -- either of those would turn Việc 1's depth limit into a
        #    silent accuracy regression instead of a speedup. Skipped once
        #    is_history_exhausted() is true: OKX has already proven there is
        #    nothing older to fetch, so retrying would only waste a call
        #    (and, unthrottled, retry it again on every future call forever).
        #
        #    `have` counts the still-open candle too (when one was fetched
        #    this call), not just what's in the closed-candle cache: a cold
        #    backfill's `target_count` above already counts that open candle
        #    as 1 of its `required_count` rows, so comparing `required_count`
        #    against `len(cached)` alone (which never includes the open
        #    candle -- see the cache-save step above) would come up exactly
        #    1 short on EVERY cold start and trigger a spurious extra
        #    backward fetch immediately after every fresh backfill.
        have = len(cached) + (1 if open_rows else 0)
        already_exhausted = self._candle_cache.is_history_exhausted(inst_id, bar)
        if (
            required_count is not None
            and cached
            and have < required_count
            and not already_exhausted
        ):
            deficit = required_count - have
            oldest_cached_ts = int(cached[0]["timestamp"])
            print(
                f"  [OKX candles] {inst_id}: cache has {len(cached)} candles but "
                f"current analysis needs {required_count} -- fetching {deficit} "
                f"more, older candles (not re-fetching what is already cached)..."
            )
            older_rows, backward_exhausted = self._paginate_candles_backward(
                inst_id, bar, before_ts=oldest_cached_ts, target_count=deficit
            )
            if older_rows:
                older_closed = [
                    self._to_candle_dict(r)
                    for r in older_rows
                    if len(r) > 8 and str(r[8]) == "1"
                ]
                merged = older_closed + cached
                merged.sort(key=lambda c: c["timestamp"])
                self._candle_cache.save(
                    inst_id, bar, merged, history_exhausted=backward_exhausted
                )
                cached = merged
            elif backward_exhausted:
                # Nothing older exists at all beyond what's already cached --
                # still record the exhaustion so this isn't retried forever.
                self._candle_cache.save(inst_id, bar, cached, history_exhausted=True)

        combined = list(cached)
        if open_rows:
            newest_open = max(open_rows, key=lambda r: int(r[0]))
            combined.append(self._to_candle_dict(newest_open))
        return combined

    def get_candles(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        # underlying_symbol() is the identity function for every CEX symbol
        # (WRAPPED_UNDERLYING only has WBTC/WETH as keys, and neither is a CEX
        # ticker), so this line changes nothing for venue_type == "CEX". For a
        # wrapped DEX asset it swaps in the instrument that actually prices it
        # -- there is no "WBTC-USDT-SWAP" on OKX, WBTC is benchmarked off
        # BTC-USDT-SWAP, exactly as Agent/data/dex/WBTC/market/
        # ohlcv_1h_2023_present.json's own `price_benchmark` field records.
        inst_id = f"{underlying_symbol(symbol)}-USDT-SWAP"
        required_count = self._effective_depth_candles()
        if self._candle_cache.enabled:
            candles = self._fetch_with_cache(inst_id, _BAR, required_count)
        else:
            candles = self._fetch_full_history(inst_id, _BAR, required_count)
        if not candles:
            raise MarketDataUnavailableError(f"OKX returned no candles for {inst_id}")
        payload = {
            "source": "OKX_PUBLIC_REST_API_LIVE",
            "endpoint": "/api/v5/market/candles + /api/v5/market/history-candles",
            "exchange": "OKX",
            "instId": inst_id,
            "instType": "SWAP",
            "bar": _BAR,
            "period_start": candles[0]["datetime"],
            "period_end": candles[-1]["datetime"],
            "total_candles": len(candles),
            "candles": candles,
        }
        return payload, None

    # -- current state: always live -------------------------------------------- #

    def get_orderbook(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        if venue_type.upper() == "DEX":
            return {}, _CEX_ONLY_INPUT_NOT_APPLICABLE_TO_DEX_REASON
        inst_id = f"{symbol}-USDT-SWAP"
        data = self._public_get("/api/v5/market/books", {"instId": inst_id, "sz": 50})
        if not data:
            raise MarketDataUnavailableError(f"OKX returned an empty order book for {inst_id}")
        book = data[0]
        bids_raw, asks_raw = book.get("bids") or [], book.get("asks") or []
        if not bids_raw or not asks_raw:
            raise MarketDataUnavailableError(f"OKX is missing bid/ask for {inst_id}")
        ct_val = self._contract_size(inst_id)

        # OKX rows are [price, size, deprecated, order_count] with size in
        # CONTRACTS. Sizes are converted to coins here -- otherwise a 100x-ctVal
        # asset like ADA reads 100x too thin and a 0.01-ctVal asset like BTC
        # reads 100x too deep, mislabelling a perfectly liquid book as ILLIQUID.
        def levels(raw: List[Any]) -> List[List[Any]]:
            return [
                [lv[0], f"{float(lv[1]) * ct_val:.10g}", lv[3]]
                for lv in raw
                if len(lv) >= 4
            ]

        payload = {
            "symbol": inst_id,
            "timestamp": int(book.get("ts") or _now_ms()),
            "source": "OKX_PUBLIC_REST_market_books_LIVE",
            "contract_size": ct_val,
            "size_unit": "BASE_COIN",
            "bids": levels(bids_raw),
            "asks": levels(asks_raw),
        }
        return payload, None

    def get_open_interest(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        if venue_type.upper() == "DEX":
            return {}, _CEX_ONLY_INPUT_NOT_APPLICABLE_TO_DEX_REASON
        inst_id = f"{symbol}-USDT-SWAP"
        # Instrument-level history, not the ccy-wide rubik series -- the latter
        # sums every contract on the currency and reads up to 32% above this
        # instrument's real OI.
        series = self._public_get(
            "/api/v5/rubik/stat/contracts/open-interest-history",
            {"instId": inst_id, "period": "5m", "limit": 100},
        )
        if len(series) < 3:
            raise MarketDataUnavailableError(
                f"{inst_id}'s OI series is too short to compute sigma/zscore"
            )
        try:
            oi = [float(row[3]) for row in series]
        except (IndexError, TypeError, ValueError) as exc:
            raise MarketDataUnavailableError(
                f"{inst_id}'s OI series is missing the USD column"
            ) from exc
        ts = int(series[0][0])
        current, previous = oi[0], oi[1]
        deltas = [a - b for a, b in zip(oi[:-1], oi[1:], strict=False)]
        sigma = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
        delta = current - previous
        zscore = delta / sigma if sigma else None
        buildup = zscore is not None and zscore >= 2.0
        payload = {
            "name": f"delta_oi_{inst_id}",
            "updated_at": ts,
            "source": "OKX_PUBLIC_REST_rubik_open_interest_history_LIVE",
            "basis": "INSTRUMENT_LEVEL",
            "data": {
                "symbol": inst_id,
                "period": "5m",
                "current_oi_usd": current,
                "prev_oi_usd": previous,
                "delta_oi_usd": delta,
                "delta_oi_pct": (delta / previous * 100.0) if previous else None,
                "sigma_oi": sigma,
                "zscore": zscore,
                "sample_size": len(oi),
                "is_liquidity_buildup": buildup,
                "buildup_type": "OI_SPIKE" if buildup else "NONE",
                "updated_at": ts,
            },
        }
        return payload, None

    def get_taker_volume(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        if venue_type.upper() == "DEX":
            return {}, _CEX_ONLY_INPUT_NOT_APPLICABLE_TO_DEX_REASON
        inst_id = f"{symbol}-USDT-SWAP"
        # Instrument-level (taker-volume-contract), matching the OI and price
        # reported beside it -- the ccy-wide feed (taker-volume) sums every
        # contract on the currency and describes a different universe.
        data = self._public_get(
            "/api/v5/rubik/stat/taker-volume-contract",
            {"instId": inst_id, "period": "1H", "limit": 24},
        )
        if not data:
            raise MarketDataUnavailableError(
                f"OKX returned an empty taker-volume-contract series for {inst_id}"
            )
        now = _now_ms()
        complete = [row for row in data if int(row[0]) + _BAR_MS <= now]
        if not complete:
            raise MarketDataUnavailableError(
                f"No closed taker-volume bucket yet for {inst_id}"
            )
        bucket = complete[0]
        ct_val = self._contract_size(inst_id)
        price = self._last_price(inst_id)

        # Row is [ts, sellVol, buyVol] in CONTRACTS -- verified empirically
        # against the live endpoint (a BTC row like 318752.85 contracts x 0.01
        # ctVal x ~77,000 USD/BTC lands in the hundreds-of-millions range that
        # matches real hourly BTC taker flow; treating that figure as already
        # being USD instead would be off by ~4 orders of magnitude). Do NOT
        # multiply an already-USD field by price again -- that specific mistake
        # inflated volume ~77,000x in an earlier version of this pipeline.
        ts, sell_ct, buy_ct = int(bucket[0]), float(bucket[1]), float(bucket[2])
        sell_usd, buy_usd = sell_ct * ct_val * price, buy_ct * ct_val * price
        net = buy_usd - sell_usd
        ratio = buy_usd / sell_usd if sell_usd else None
        payload = {
            "name": f"taker_volume_{symbol}",
            "updated_at": ts,
            "source": "OKX_PUBLIC_REST_rubik_taker_volume_contract_LIVE",
            "basis": "INSTRUMENT_LEVEL",
            "unit": "USD",
            "bucket_complete": True,
            "data": {
                "ccy": symbol,
                "symbol": inst_id,
                "period": "1H",
                "buy_vol_usd": buy_usd,
                "sell_vol_usd": sell_usd,
                "total_vol_usd": buy_usd + sell_usd,
                "buy_sell_ratio": ratio,
                "net_flow_usd": net,
                "flow_sentiment": _flow_label(ratio),
                "contract_size": ct_val,
                "reference_price": price,
                "updated_at": ts,
            },
        }
        return payload, None

    def get_sentiment(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        if venue_type.upper() == "DEX":
            return {}, _CEX_ONLY_INPUT_NOT_APPLICABLE_TO_DEX_REASON
        inst_id = f"{symbol}-USDT-SWAP"
        ls_rows = self._public_get(
            "/api/v5/rubik/stat/contracts/long-short-account-ratio",
            {"ccy": symbol, "period": "1H"},
        )
        funding = self._public_get("/api/v5/public/funding-rate", {"instId": inst_id})
        if not ls_rows or not funding:
            raise MarketDataUnavailableError(
                f"OKX is missing long/short or funding data for {inst_id}"
            )
        try:
            # Open interest here is a convenience field on the sentiment
            # snapshot, not the primary derivatives-OI series (that lives in
            # get_open_interest()). A hiccup on this one call must not take the
            # whole sentiment read down with it, matching the original
            # crawler's tolerance (`float(oi_now[0]["oiUsd"]) if oi_now else None`).
            oi_now = self._public_get(
                "/api/v5/public/open-interest", {"instType": "SWAP", "instId": inst_id}
            )
        except MarketDataUnavailableError:
            oi_now = []
        ls_ratio = float(ls_rows[0][1])
        observed = int(ls_rows[0][0])
        rate = float(funding[0]["fundingRate"])
        payload = {
            "symbol": inst_id,
            "updated_at": observed,
            "source": (
                "OKX_PUBLIC_REST_long_short_contract+funding_rate+open_interest_LIVE"
            ),
            "basis": "INSTRUMENT_LEVEL",
            "sentiment": {
                "symbol": inst_id,
                "base_ccy": symbol,
                "ls_ratio": f"{ls_ratio:.2f}",
                "sentiment_label": _sentiment_label(ls_ratio),
                "funding_rate": f"{rate * 100:+.4f}% / 8h",
                "next_funding_time": funding[0].get("nextFundingTime"),
                "open_interest_usd": float(oi_now[0]["oiUsd"]) if oi_now else None,
                "updated_at": observed,
            },
        }
        return payload, None

    # -- windowed ticks: time-bounded backfill via history-trades, O(1) memory - #

    def fetch_ticks_windowed(
        self,
        inst_id: str,
        *,
        target_window_ms: int = _TICK_TARGET_WINDOW_MS_DEFAULT,
        max_pages: int = _TICK_MAX_PAGES_DEFAULT,
        max_wall_seconds: float = _TICK_MAX_WALL_SECONDS_DEFAULT,
    ) -> Tuple[TickAggregator, str]:
        """Walk backward from "now" folding OKX trade prints into a TickAggregator.

        Replaces "fetch a fixed count of trades" with "fetch until a fixed
        TIME WINDOW is covered" -- see the module-level comment above
        _TICK_TARGET_WINDOW_MS_DEFAULT for why that distinction is the actual
        fix here. Each page is hashed into the aggregator's running totals by
        `agg.add_page(rows)` and then this function keeps no reference to
        `rows` at all -- memory used by this walk is O(1) in the number of
        trades covered, not O(n): see TickAggregator's own docstring in
        Agent/backend/market/features/orderflow.py for the full reasoning.
        Whether this walk covers 100 trades or 100,000, `agg` itself is
        always the same fixed handful of scalars.

        Stops on the first of: the target window is covered, `max_pages`
        pages have been fetched, `max_wall_seconds` of wall-clock time have
        elapsed, or OKX has no older data left for this instrument -- exactly
        the layered safety-valve design _paginate_candles_raw() already uses
        for candles, applied here to trades instead. Returns `(agg,
        stop_reason)` so a caller can tell *why* the walk stopped (useful for
        the resulting payload's provenance, and for tests asserting a
        specific cap was what stopped a given walk).
        """
        agg = TickAggregator(target_window_ms=target_window_ms)
        cursor = ""
        endpoint = "/api/v5/market/trades"
        page = 0
        started = time.monotonic()
        while True:
            params: Dict[str, Any] = {"instId": inst_id, "limit": self._page_size}
            if cursor:
                # type=2 => timestamp-based pagination; `after` means "older
                # than this ts" per OKX docs, which is exactly the backward
                # walk this needs. Only sent from the second page on, since
                # `/api/v5/market/trades` (the first-page endpoint) serves
                # the latest prints without needing a cursor at all.
                params["after"] = cursor
                params["type"] = "2"
            rows = self._public_get(endpoint, params)
            if not isinstance(rows, list) or not rows:
                return agg, "no_more_data"

            agg.add_page(rows)  # folded into scalars; `rows` is dropped below
            page += 1
            endpoint = "/api/v5/market/history-trades"

            if agg.earliest_ts is None:
                # Every row in every page so far failed to parse a `ts` --
                # nothing to page further back from. Bail rather than loop.
                return agg, "unparseable_page"
            cursor = str(agg.earliest_ts)

            if agg.window_ms is not None and agg.window_ms >= target_window_ms:
                return agg, "window_covered"
            if page >= max_pages:
                return agg, "max_pages"
            if time.monotonic() - started >= max_wall_seconds:
                return agg, "max_wall_seconds"
            if len(rows) < self._page_size:
                # OKX has no older data left for this instrument -- matches
                # the same convention _paginate_candles_raw() uses.
                return agg, "no_more_data"

    def get_ticks_windowed(
        self,
        symbol: str,
        venue_type: str,
        *,
        target_window_ms: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Time-windowed CEX trade-print aggregate for `symbol`, via OKX.

        Not part of the MarketDataSource abstract interface (this class's
        get_ticks() below stays a DEX-only "not applicable" stub, unchanged,
        for the structural reasons explained in that method and in the class
        docstring). This method exists as the actual fix requested for the
        "flow_bias measured over an inconsistent time window" problem: it is
        the reusable, directly-testable building block (paginate by time +
        aggregate in O(1) memory + report the window actually covered) that
        the diagnosis called for, exposed here so it can be exercised without
        threading it through MarketService/service.py (out of scope for this
        change -- see this module's other call sites for why DEX routing
        through this CEX-only source does not apply).

        Every field the diagnosis asked to be visible is here at the payload
        level (OrderflowState itself is not touched -- see
        OrderflowFeatureExtractor.insufficiency_reason()'s docstring for why):
        the window actually covered, the tick count, the page count, and (if
        the sample was too thin) the human reason why flow_bias would come
        back UNKNOWN.
        """
        inst_id = f"{symbol}-USDT-SWAP"
        window = (
            target_window_ms
            if target_window_ms is not None
            else _TICK_TARGET_WINDOW_MS_DEFAULT
        )
        agg, stop_reason = self.fetch_ticks_windowed(inst_id, target_window_ms=window)
        payload = {
            "source": "OKX_PUBLIC_REST_market_history_trades_LIVE",
            "endpoint": "/api/v5/market/trades + /api/v5/market/history-trades",
            "instId": inst_id,
            "target_window_ms": window,
            "window_covered_ms": agg.window_ms,
            "tick_count": agg.tick_count,
            "pages_fetched": agg.pages_added,
            "earliest_ts": agg.earliest_ts,
            "latest_ts": agg.latest_ts,
            "stop_reason": stop_reason,
            "buy_notional_usd": agg.buy_notional,
            "sell_notional_usd": agg.sell_notional,
            "flow_bias_unknown_reason": OrderflowFeatureExtractor.insufficiency_reason(
                agg
            ),
        }
        return payload, None

    # -- macro: derived from OKX candles, not an independent endpoint --------- #

    def _closes_by_ts(self, symbol: str, venue_type: str) -> Dict[int, float]:
        payload, error = self.get_candles(symbol, venue_type)
        if error:
            raise MarketDataUnavailableError(
                f"Could not get candles for {symbol} to compute macro: {error}"
            )
        return {
            int(c["timestamp"]): float(c["close"])
            for c in payload["candles"]
            if c.get("close")
        }

    def get_macro_context(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        ref_closes = self._closes_by_ts(_MACRO_REFERENCE_SYMBOL, "CEX")
        closes = (
            ref_closes
            if symbol == _MACRO_REFERENCE_SYMBOL
            else self._closes_by_ts(symbol, venue_type)
        )
        shared = sorted(set(closes) & set(ref_closes))[-self.macro_window_hours :]
        if len(shared) < _MACRO_MIN_OVERLAP:
            raise MarketDataUnavailableError(
                f"Not enough overlapping candles between {symbol} and "
                f"{_MACRO_REFERENCE_SYMBOL} to compute macro "
                f"({len(shared)} < {_MACRO_MIN_OVERLAP})"
            )
        asset_ret = _log_returns(closes, shared)
        ref_ret = _log_returns(ref_closes, shared)
        pairs = min(len(asset_ret), len(ref_ret))
        asset_ret, ref_ret = asset_ret[:pairs], ref_ret[:pairs]
        regime, trend_pct, vol_pct = _reference_regime(ref_ret)
        observed = min(max(closes), max(ref_closes))
        payload = {
            "asset": symbol,
            "venue": venue_type,
            "source": "DERIVED_FROM_LIVE_OHLCV_1H",
            "reference": f"CEX/{_MACRO_REFERENCE_SYMBOL}",
            "observed_at": observed,
            "updated_at": observed,
            "window_hours": len(shared),
            "sample_size": pairs,
            "macro": {
                "btc_correlation": _pearson(asset_ret, ref_ret),
                "btc_beta": _beta(asset_ret, ref_ret),
                "macro_regime": regime,
                "reference_trend_pct": trend_pct,
                "reference_annualised_vol_pct": vol_pct,
                # No economic calendar source exists in this dataset.
                "macro_event_risk": "UNKNOWN",
            },
        }
        return payload, None

    # -- DEX-only inputs: OKX ticks + DexScreener pool + GoPlus security ------ #
    #
    # All three follow a different error contract than every getter above:
    # a structural "this asset/venue is not served" answer still comes back
    # as the (payload, error) tuple every other getter uses (so a caller that
    # only ever asks about CEX symbols, or an unconfigured instance, sees
    # exactly the same NOT_APPLICABLE-shaped answer as before this class
    # supported DEX at all) -- but once a live fetch is actually attempted,
    # any failure RAISES MarketDataUnavailableError instead of returning an
    # error string. This mirrors get_candles() above (also raises, never
    # returns a tuple) and is deliberate, not an oversight: an empty dict
    # paired with an error string is still an empty dict to any caller that
    # forgets to check the second element, and for a DEX asset that
    # `market_result` a caller mistakenly trusted would grade the asset
    # UNKNOWN instead of surfacing that GoPlus/DexScreener/OKX actually
    # failed -- exactly the failure mode "fail-closed" is meant to prevent.

    def get_ticks(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Latest 100 trade prints on the asset's benchmark instrument.

        Deliberately a fixed *count* (100), not `fetch_ticks_windowed()`'s
        time-based window: ported to match crawl_market_data.py::
        refresh_dex_ticks() byte-for-byte (`limit=100` against
        `/api/v5/market/trades`), because the whole point of this method is
        that a live read and a crawl read of the same asset at the same
        moment must be comparable -- switching the default to the windowed
        fetch would change *what is being measured*, not just *how it is
        served*, which is precisely the deviation this task explicitly rules
        out. `fetch_ticks_windowed()`/`get_ticks_windowed()` above remain the
        opt-in alternative for a caller that wants a fixed *time* window
        instead of a fixed *count*; nothing here calls them.
        """
        if venue_type.upper() != "DEX":
            return {}, _DEX_ONLY_INPUT_NOT_APPLICABLE_TO_CEX_REASON
        info = self._dex_asset(symbol)
        if info is None:
            return {}, _DEX_ASSET_NOT_IN_REGISTRY_REASON

        pair = spot_benchmark_pair(symbol)
        trades = self._public_get(
            "/api/v5/market/trades", {"instId": pair, "limit": _DEX_TICK_DEFAULT_COUNT}
        )
        if not trades:
            raise MarketDataUnavailableError(
                f"OKX returned no trades for {pair} ({symbol}'s DEX tick source)"
            )
        ticks = sorted(trades, key=lambda t: int(t["ts"]))
        payload = {
            "source": "OKX_DEX_ROUTER_TICK_STREAM_LIVE",
            "asset": symbol,
            "pool": info.pool_label,
            "chain": info.chain_label,
            "benchmark_pair": pair,
            "tick_interval": "100ms",
            "updated_at": max(int(t["ts"]) for t in ticks),
            "total_ticks": len(ticks),
            "ticks": ticks,
        }
        return payload, None

    def get_pool_liquidity(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Deepest DexScreener pool for the asset whose price agrees with OKX.

        Ported from crawl_market_data.py::crawl_pool_liquidity(): the only
        structural difference is where the token address comes from (that
        function reads it back out of the file it is about to overwrite;
        this class has no such file, so the address comes from
        `dex_registry` instead -- see that module's docstring). The
        price-before-liquidity pool selection (`_select_pool()`) and the CEX
        reference-price lookup are otherwise identical.
        """
        if venue_type.upper() != "DEX":
            return {}, _DEX_ONLY_INPUT_NOT_APPLICABLE_TO_CEX_REASON
        info = self._dex_asset(symbol)
        if info is None:
            return {}, _DEX_ASSET_NOT_IN_REGISTRY_REASON

        reference_inst = swap_reference_inst_id(symbol)
        reference = self._last_price(reference_inst)  # raises on failure

        payload = _dex_http_get_json(f"{_DEXSCREENER_TOKENS_URL}/{info.token_address}")
        pairs = payload.get("pairs") or []
        if not pairs:
            raise MarketDataUnavailableError(
                f"DexScreener returned no pool for {symbol} ({info.token_address})"
            )
        chosen, rejected = _select_pool(pairs, info.chain, reference)
        if chosen is None:
            raise MarketDataUnavailableError(
                f"No pool for {symbol} matches the reference price "
                f"{reference:.6g} (rejected {rejected} pool(s) with a price gap over "
                f"{_POOL_PRICE_TOLERANCE:.0%})"
            )
        liquidity, price, pair = chosen
        observed = _now_ms()
        out = {
            "asset": symbol,
            "chain": info.chain,
            "dex_id": pair.get("dexId"),
            "pair_address": pair.get("pairAddress"),
            "base_token": {
                "address": (pair.get("baseToken") or {}).get("address"),
                "name": (pair.get("baseToken") or {}).get("name"),
                "symbol": (pair.get("baseToken") or {}).get("symbol"),
            },
            "quote_token": {
                "address": (pair.get("quoteToken") or {}).get("address"),
                "name": (pair.get("quoteToken") or {}).get("name"),
                "symbol": (pair.get("quoteToken") or {}).get("symbol"),
            },
            "price_usd": price,
            "reference_price_usd": reference,
            "reference_instrument": reference_inst,
            "price_gap_pct": (price - reference) / reference * 100.0,
            "tvl_usd": liquidity,
            "volume_24h_usd": float((pair.get("volume") or {}).get("h24") or 0.0),
            "pools_rejected_on_price": rejected,
            "observed_at": observed,
            "updated_at": observed,
            "source": "DEXSCREENER_PRICE_VALIDATED_LIVE",
        }
        return out, None

    def get_token_security(
        self, symbol: str, venue_type: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """On-chain contract-security evidence for the asset's token, from
        GoPlus. Ported from crawl_token_security.py::crawl_asset(): same two
        endpoints (Solana vs EVM), same per-chain parsers, same "no invented
        composite score" rule (a field GoPlus does not answer stays null).
        """
        if venue_type.upper() != "DEX":
            return {}, _DEX_ONLY_INPUT_NOT_APPLICABLE_TO_CEX_REASON
        info = self._dex_asset(symbol)
        if info is None:
            return {}, _DEX_ASSET_NOT_IN_REGISTRY_REASON

        address = info.token_address
        if info.chain == "SOLANA":
            payload = _dex_http_get_json(
                f"{_GOPLUS_URL}/solana/token_security?contract_addresses={address}"
            )
            parse, key = _parse_solana_security, address
        elif info.chain in _GOPLUS_EVM_CHAIN_IDS:
            chain_id = _GOPLUS_EVM_CHAIN_IDS[info.chain]
            payload = _dex_http_get_json(
                f"{_GOPLUS_URL}/token_security/{chain_id}?contract_addresses={address}"
            )
            parse, key = _parse_evm_security, address.lower()
        else:
            raise MarketDataUnavailableError(
                f"{symbol}'s chain {info.chain} is not supported by GoPlus "
                "in this lookup table"
            )

        if payload.get("code") != 1:
            raise MarketDataUnavailableError(
                f"GoPlus returned code={payload.get('code')} {payload.get('message')} "
                f"for {symbol}"
            )
        record = (payload.get("result") or {}).get(key)
        if not record:
            raise MarketDataUnavailableError(
                f"GoPlus has no security data for address {address} ({symbol})"
            )

        observed = _now_ms()
        out = {
            "asset": symbol,
            "chain": info.chain,
            "token_address": address,
            "source": "GOPLUS_TOKEN_SECURITY_API_LIVE",
            "observed_at": observed,
            "updated_at": observed,
            "security": parse(record),
        }
        return out, None
