"""Data layer behind the risk-supervisor web dashboard: reads pre-scored
bots/markets off disk, looks up an arbitrary uniqueCode cheaply, and scores
it live (expensively) only once a user opts in.

Four data sources feed the dashboard:

  1. `list_bots()` / `list_markets()` -- plain reads of what the batch report
     (`Agent/backend/run_report.py`) already wrote to `data/assessment/**`
     and `data/analysis/**`. No network, no live scoring.
  2. `leaderboard()` -- OKX's own lead-trader ranking, fetched live and
     cached briefly, used to power a search-box "did you mean" suggestion
     for `POST /api/analyze`.
  3. `lookup()` -- the CHEAP half of the two-step flow the dashboard uses:
     "who is this uniqueCode, and what does it look like it's trading" --
     at most 3 OKX requests (see `lookup`'s own docstring), no scoring
     engine at all. Meant to be called on every keystroke-driven search
     without the ~8-15s cost `analyze()` pays.
  4. `analyze()` -- the EXPENSIVE half: score ONE bot, by uniqueCode, live,
     never on disk before this call. See `WebDataService.analyze`'s own
     docstring for how it reuses `RiskSupervisionPipeline` (the exact class
     `run_report.py --source live` and `agent_server.py`'s `assess_bot` tool
     already use) for a bot that was never crawled. The dashboard's own flow
     is meant to be: type a code -> `lookup()` -> user clicks "Phân tích bot
     này?" -> only THEN `analyze()`; this module enforces none of that
     sequencing itself (nothing here rejects a bare `analyze()` call), it
     only makes sure `lookup()` alone is cheap enough that doing it on every
     keystroke is fine.

Every user-supplied string in this module (a `code` from an HTTP request) is
untrusted input: validated once, in `validate_unique_code`, before it can
reach a path join or a network call.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import math
import os
import re
import threading
import time
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlsplit

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.live.ratelimit import TokenBucket
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.mcp.service import BotObservationService
from Agent.backend.okx.client import OkxApiError, OkxClient, OkxError
from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.qc.evaluator.common import tier_for
from Agent.backend.qc.reporting import narrative
from Agent.backend.qc.scoring.verdict import VERDICT_BASIS_VI, label_from_scores
from Agent.backend.sources.bot_source import (
    HISTORY_PATH,
    LEAD_TRADERS_PATH,
    LEADERBOARD_PAGE_SIZE,
    PAGE_SIZE,
    POSITIONS_PATH,
    STATS_LAST_DAYS,
    STATS_PATH,
    TRADER_NOT_EXIST_CODE,
    BotDataSource,
    BotSourceError,
    LedgerUnavailableError,
    LiveBotDataSource,
)
from Agent.backend.sources.bot_source import STATUS_NOT_FOUND as _SOURCE_NOT_FOUND
from Agent.backend.sources.market_source import LiveMarketDataSource, MarketDataSource

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Soft seam with Agent/backend/analysis/limited.py.
#
# That module is written by another agent, in parallel with this one, to
# score a bot whose order book OKX refuses to disclose (error 60004 on the
# copytrading ledger endpoints -- see `LedgerUnavailableError` in
# sources/bot_source.py, which classifies that into LIMITED vs NOT_FOUND
# using leaderboard/profile data this module never has to look at itself).
# It may not exist yet at import time, so this import is soft: when it is
# missing, `_handle_ledger_unavailable` below still returns the RIGHT status
# (LedgerUnavailableError.status already carries that, independent of this
# module) with a clear Vietnamese fallback message instead of the detailed
# scoring `assess_from_error` would otherwise add, and the FULL branch (this
# module's own responsibility) is completely unaffected either way.
#
# `assess_from_error(exc)` is the confirmed real signature (see
# Agent/backend/analysis/limited.py and Agent/none/test/test_limited_assessment.py):
# it takes the `LedgerUnavailableError` itself (duck-typed on
# .status/.code/.profile/.stats/.weekly/str(exc)) and returns the exact
# `/api/analyze` response contract dict. Still wrapped in its own broad
# `try/except` below -- a future signature drift in that module must fail
# closed (a clean Vietnamese error) rather than crash this endpoint.
# --------------------------------------------------------------------------- #
try:
    from Agent.backend.analysis.limited import assess_from_error  # type: ignore
except ImportError:
    assess_from_error = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #

# OKX uniqueCode is either hex (e.g. "BB3398A957270A39") or a plain numeric
# id (e.g. "811997770117827919") -- alnum only, per the codebase's other
# uniqueCode validators (see agent_server.py's _SAFE_TOKEN, which is looser
# because it also has to accept folder-style tokens). 64 chars is generous
# headroom over every real code observed in this dataset (longest is 18
# chars) while still bounding the size of a hostile payload. Rejecting
# anything outside [A-Za-z0-9] also rejects "." and "/" outright, which is
# what makes a path-traversal payload like "../../etc" fail here before it
# can ever reach a path join (see WebDataService._analyze_full).
_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,64}$")


class InvalidCodeError(ValueError):
    """A `code` from the network failed validation -- maps to HTTP 400, never 500."""


def validate_unique_code(raw: Any) -> str:
    if not isinstance(raw, str):
        raise InvalidCodeError("Missing 'code' field as a string in the JSON body")
    code = raw.strip()
    if not code:
        raise InvalidCodeError("Bot code (uniqueCode) must not be empty")
    if not _CODE_RE.match(code):
        raise InvalidCodeError(
            "Invalid bot code: only letters and digits are accepted (an OKX "
            "code is hex or numeric), up to 64 characters -- rejected to "
            "block stray characters/path traversal"
        )
    return code


# --------------------------------------------------------------------------- #
# TTL cache + per-IP rate limiter
# --------------------------------------------------------------------------- #


class _TTLCache:
    """Tiny per-key cache with a fixed time-to-live, safe to share across threads.

    Why this exists: `/api/analyze` costs several seconds of CPU plus several
    OKX round-trips (see module docstring), and `/api/leaderboard` pages the
    OKX ranking -- neither should be paid for again just because a user
    clicked the same thing twice in a row. TTL is short (a few minutes, see
    the DEFAULT_* constants below) because both a bot's own state (new
    trades, new positions) and the leaderboard ranking genuinely change on
    that timescale; a longer cache would start showing stale verdicts.
    """

    def __init__(
        self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._store: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if self._clock() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (self._clock() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class PerIpRateLimiter:
    """Sliding-window request cap per source IP, enforced inside the app.

    WHY in the app and not only in nginx: this process may not even be
    behind a reverse proxy (a bare `python3 -m Agent.backend.run_web` on a
    dev box, or a first deploy), and one `/api/analyze` call alone spends
    several seconds of CPU and several requests against OKX's own 5-req/2s
    copytrading budget (shared with every other caller of this process, see
    WebDataService._rate_limiter) -- a caller that can bypass an
    app-external limiter could starve every other user of that shared OKX
    budget. `max_requests` per `window_seconds`, per IP; deliberately simple
    (an in-memory sliding window) since this is a single-process service,
    not a fleet that would need a shared store.
    """

    def __init__(
        self,
        max_requests: int = 5,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._clock = clock
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self._window]
            if len(hits) >= self._max:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


# --------------------------------------------------------------------------- #
# Per-asset trading-state classification -- shared between POST /api/lookup
# (built entirely from a fresh, cheap OKX probe) and POST /api/analyze's
# `assets` field (built from the ledger/positions the scoring pass already
# fetched). One set of rules, so a dashboard never has to reconcile two
# different definitions of "is this bot still trading X".
# --------------------------------------------------------------------------- #

# "quá 7 ngày" (past 7 days) per the task's own three-state definition:
#   - a closed trade INSIDE this window -> the asset is being actively traded
#   - an open position with no close inside this window -> merely being held
#     (a real, measured risk pattern: holding a loser hoping it recovers
#     rather than cutting it -- see the "CHỈ ĐANG ÔM" note text below)
#   - no open position and no close inside this window -> abandoned
# A named float constant (not inlined) so the boundary is documented in one
# place and comparable exactly against a fractional last_close_days
# (0.2, 38.7, ...) instead of being silently re-typed at each call site.
ASSET_ACTIVE_WINDOW_DAYS = 7.0

ASSET_STATE_TRADING = "TRADING"
ASSET_STATE_HOLDING = "HOLDING ONLY"
ASSET_STATE_LEFT = "EXITED"

_MS_PER_DAY = 24 * 3_600 * 1_000


def _float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    as_float = _float(value)
    return None if as_float is None else int(round(as_float))


def _base_symbol(inst_id: Any) -> Optional[str]:
    """ "ETH-USDT-SWAP" -> "ETH". Mirrors
    Agent/backend/mcp/positions/snapshot.py's identical helper of the same
    name (off-limits to import from here -- see this module's own docstring
    on the sources/analysis/mcp boundary), kept in lock-step deliberately: a
    trade ledger row's `instId` and an open position's `instId` use the same
    "<BASE>-<QUOTE>-<TYPE>" shape on OKX, so both must resolve to the same
    base symbol or /api/lookup and /api/analyze's own `assets` field could
    silently disagree about what to call the same asset.
    """
    if not inst_id:
        return None
    base = str(inst_id).split("-")[0].strip().upper()
    return base or None


def _asset_state(open_positions: int, last_close_days: Optional[float]) -> str:
    if last_close_days is not None and last_close_days <= ASSET_ACTIVE_WINDOW_DAYS:
        return ASSET_STATE_TRADING
    if open_positions > 0:
        return ASSET_STATE_HOLDING
    return ASSET_STATE_LEFT


def _build_asset_states(
    open_symbols: List[str],
    closed_records: List[Tuple[str, Optional[int]]],
    now_ms: int,
) -> List[Dict[str, Any]]:
    """Turn a flat list of open-position symbols and (symbol, close_time_ms)
    closed-trade pairs into the `assets` contract both routes expose.

    `closed_records` may repeat a symbol many times (one entry per closed
    trade) -- every occurrence counts toward `closed_seen`, but only the
    MOST RECENT close per symbol decides `last_close_days`/state. A symbol
    with no recorded close at all (open, but never closed -- see the task's
    own "vị thế mở nhưng chưa từng đóng" case) gets `last_close_days=None`,
    which `_asset_state` treats as "not recently closed" rather than as
    "recently closed", so it still correctly falls through to CHỈ ĐANG ÔM.
    """
    open_counts: Dict[str, int] = {}
    for symbol in open_symbols:
        if symbol:
            open_counts[symbol] = open_counts.get(symbol, 0) + 1

    closed_counts: Dict[str, int] = {}
    last_close_ms: Dict[str, int] = {}
    for symbol, close_ms in closed_records:
        if not symbol:
            continue
        closed_counts[symbol] = closed_counts.get(symbol, 0) + 1
        if close_ms is not None:
            last_close_ms[symbol] = max(close_ms, last_close_ms.get(symbol, 0))

    rows: List[Dict[str, Any]] = []
    for symbol in sorted(set(open_counts) | set(closed_counts)):
        open_positions = open_counts.get(symbol, 0)
        close_ms = last_close_ms.get(symbol)
        last_close_days = (
            round((now_ms - close_ms) / _MS_PER_DAY, 1)
            if close_ms is not None
            else None
        )
        rows.append(
            {
                "asset": symbol,
                "state": _asset_state(open_positions, last_close_days),
                "open_positions": open_positions,
                "closed_seen": closed_counts.get(symbol, 0),
                "last_close_days": last_close_days,
            }
        )
    return rows


def _holding_assets_note(assets: List[Dict[str, Any]]) -> Optional[str]:
    """CHỈ ĐANG ÔM is a risk signal in its own right (see module docstring) --
    surfaced here as a Vietnamese `note` sentence whenever it shows up, so a
    caller never has to re-derive "does this bot hold stale losers" from the
    raw `assets` array itself. Returns None when nothing needs flagging,
    which both /api/lookup (an explicit `note` field) and a future dashboard
    can render as "no warning" rather than an empty string.
    """
    holding = [a["asset"] for a in assets if a["state"] == ASSET_STATE_HOLDING]
    if not holding:
        return None
    window = int(ASSET_ACTIVE_WINDOW_DAYS)
    return (
        f"Warning: {', '.join(holding)} is in the HOLDING ONLY state (still "
        f"has an open position but no trade closed in over {window} days) -- "
        "this state is itself a risk signal, commonly seen in a pattern of "
        "holding a loss and waiting for it to recover."
    )


# --------------------------------------------------------------------------- #
# /api/bots, /api/markets -- plain reads of what run_report.py already wrote
# --------------------------------------------------------------------------- #


def _read_json_documents(root: Path, pattern: str) -> List[Dict[str, Any]]:
    """Read every JSON object matching `pattern` under `root`, skipping any
    file that fails to parse rather than letting one bad file 500 the route.
    """
    out: List[Dict[str, Any]] = []
    if not root.is_dir():
        return out
    for path in sorted(root.glob(pattern)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            out.append(payload)
    return out


def list_scored_bots(data_dir: Path) -> List[Dict[str, Any]]:
    """The bots step 3 already scored: one assessment.json per bot, read
    straight off disk (data/assessment/<venue>/<asset>/bot/<name>/assessment.json).

    Raw documents, Vietnamese-keyed (`bot`, `khuyen_nghi`, `cham_diem`,
    `bang_chung`, ...) exactly as `run_report.py` wrote them -- NOT the
    normalized shape a screen renders. See `list_bot_listing_rows` below for
    that; this function stays a plain disk read so `GET /healthz`'s
    `bots_on_disk` check (which only ever counts the list, see
    `WebDataService.list_bots`) never pays for normalization it does not
    need.
    """
    return _read_json_documents(Path(data_dir) / "assessment", "**/assessment.json")


# --------------------------------------------------------------------------- #
# Bot listing row -- the ONE normalized shape a screen renders, built from a
# raw `assessment.json` document. Việc 1's own fix: before this function
# existed, `GET /api/bots` hasnded back the raw document above verbatim, and
# BOTH `Agent/backend/web/admin_page.py`'s server-rendered `/admin` page and
# `Agent/frontend/src/pages/AdminHome.jsx` (client-side JavaScript) each
# independently re-derived a row from it -- in particular each independently
# decided what verdict label to show, and the JavaScript copy read
# `khuyen_nghi.ket_luan` (the RETIRED single-axis label frozen on disk at
# scoring time) instead of recomputing from the scores next to it, producing
# a different label on the SPA than every other surface for the same bot.
# `GET /api/bots` (see app.py's `api_bots`) is now the ONE place a raw
# document is turned into a row -- the SPA and, previously, admin_page.py's
# own listing both consumed its OUTPUT rather than re-deriving one, so a
# future change to this mapping only has to be made here.
# --------------------------------------------------------------------------- #


def _venue_asset_label(bot: Mapping[str, Any]) -> Optional[str]:
    venue = bot.get("venue_type")
    asset = bot.get("traded_symbol") or bot.get("asset_context")
    parts = [p for p in (venue, asset) if isinstance(p, str) and p.strip()]
    return " · ".join(parts) if parts else None


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def bot_listing_row(doc: Any) -> Optional[Dict[str, Any]]:
    """One `/api/bots` row from one `assessment.json`-shaped document, or
    `None` when `doc` is too malformed to even carry a bot code -- a
    document this broken cannot be shown OR deduplicated against, so it is
    silently dropped rather than crashing the whole listing over one bad
    file (same "skip, don't crash" rule `_read_json_documents` above already
    applies one layer below this).

    The verdict is ALWAYS recomputed via `label_from_scores` from the scores
    and hidden-risk flags sitting next to it in the same file, never read
    verbatim off disk (`khuyen_nghi.ket_luan` is the retired single-axis
    label frozen at scoring time -- see `label_from_scores`'s own docstring
    for why that string alone cannot be trusted to carry today's meaning).
    This is the exact same function `GET /bot/<code>`'s own live scoring
    (`verdict.decide`) bottoms out on for the SAME risk/quality/hidden-flags
    triple, so the two surfaces can never show a different label for
    numbers that agree.
    """
    if not isinstance(doc, dict):
        return None
    bot = doc.get("bot")
    bot = bot if isinstance(bot, dict) else {}
    code = bot.get("unique_code")
    if not isinstance(code, str) or not code.strip():
        return None

    khuyen_nghi = doc.get("recommendation")
    khuyen_nghi = khuyen_nghi if isinstance(khuyen_nghi, dict) else {}
    cham_diem = doc.get("scoring")
    cham_diem = cham_diem if isinstance(cham_diem, dict) else {}
    bang_chung = doc.get("evidence")
    bang_chung = bang_chung if isinstance(bang_chung, dict) else {}

    risk = cham_diem.get("risk_score")
    if not _is_finite_number(risk):
        risk = khuyen_nghi.get("risk_score")
    quality = cham_diem.get("quality_score")
    if not _is_finite_number(quality):
        quality = khuyen_nghi.get("quality_score")
    confidence = khuyen_nghi.get("confidence")
    total_pnl = bang_chung.get("total_pnl")
    trade_count = bang_chung.get("trade_count")

    decided_by = cham_diem.get("score_decided_by")
    is_veto = isinstance(decided_by, str) and decided_by != "WEIGHTED_AVERAGE"
    veto_reasons_raw = cham_diem.get("veto_reasons")
    veto_reasons = (
        [r for r in veto_reasons_raw if isinstance(r, str) and r.strip()]
        if isinstance(veto_reasons_raw, list)
        else []
    )
    hidden_flags_raw = cham_diem.get("hidden_risk_flags")
    hidden_flags = (
        [f for f in hidden_flags_raw if isinstance(f, str) and f.strip()]
        if isinstance(hidden_flags_raw, list)
        else []
    )

    risk_val = float(risk) if _is_finite_number(risk) else None
    quality_val = float(quality) if _is_finite_number(quality) else None
    verdict = label_from_scores(risk_val, quality_val, hidden_flags)

    return {
        "code": code,
        "name": bot.get("nick_name") if isinstance(bot.get("nick_name"), str) else None,
        "venue_asset": _venue_asset_label(bot),
        "verdict": verdict,
        "risk": risk_val,
        "quality": quality_val,
        "confidence": float(confidence) if _is_finite_number(confidence) else None,
        "trade_count": int(round(float(trade_count)))
        if _is_finite_number(trade_count)
        else None,
        "generated_at_ms": doc.get("generated_at_ms"),
        "is_veto": is_veto,
        "veto_reasons": veto_reasons,
        "total_pnl": float(total_pnl) if _is_finite_number(total_pnl) else None,
    }


def list_bot_listing_rows(data_dir: Path) -> List[Dict[str, Any]]:
    """Every `list_scored_bots(data_dir)` document, normalized via
    `bot_listing_row` -- see that function's own docstring. This is what
    `GET /api/bots` (app.py's `api_bots`, via `WebDataService.list_bot_rows`)
    actually serves.

    Deduplicated by code, first occurrence wins -- a malformed dataset with
    two `assessment.json` files somehow sharing one `unique_code` must not
    double-count that bot in a listing or in any total computed from it.
    """
    rows: List[Dict[str, Any]] = []
    seen: set = set()
    for doc in list_scored_bots(data_dir):
        row = bot_listing_row(doc)
        if row is None or row["code"] in seen:
            continue
        seen.add(row["code"])
        rows.append(row)
    return rows


def list_markets(data_dir: Path) -> List[Dict[str, Any]]:
    """The assets step 2 already analysed: one market.json per asset
    (data/analysis/<venue>/<asset>/market/market.json).
    """
    return _read_json_documents(Path(data_dir) / "analysis", "**/market/market.json")


# --------------------------------------------------------------------------- #
# GET /bot/<code> / GET /<userref>_<code> without re-analyzing -- "trang chi
# tiết đang 504 timeout" fix.
#
# Before this section existed, `app.py`'s `_bot_report_response` always fell
# back to `service.analyze(code)` on a snapshot-cache miss, EVEN for a code
# `run_report.py` had already scored minutes earlier: an OKX ledger fetch, a
# 10k-iteration Monte Carlo, and (when configured) an LLM narrative call,
# ~70s total, just to reproduce a verdict already sitting in
# `data/assessment/**/assessment.json`. That is the bug this section fixes --
# read the already-computed verdict back off disk instead of recomputing it.
#
# `assessment_to_analyze_result` below turns one `assessment.json` document
# (see `Agent/backend/qc/reporting/assessment_store.py`'s `build_assessment`
# for the exact Vietnamese-keyed shape it writes) into the SAME dict shape
# `WebDataService.analyze()` returns for a FULL bot (see `_full_result`
# above), so `report_page.py`'s `render_bot_report_html` renders either one
# without knowing which it got. It is a pure, deterministic RESHAPING of
# numbers that are already fully computed -- no OKX call, no Monte Carlo
# re-run, no LLM call. The one exception is `tier_for(score)` (imported from
# the QC evaluator -- the same pure score->tier threshold function every
# lens already used to assign that tier at scoring time): that is
# presentation logic operating on an already-final number, not analysis.
#
# `evidence.closed_trade_series` (the per-trade ledger behind the equity-
# curve chart), `mc.horizon_scenarios` (the SHORT/MEDIUM/LONG comparison),
# and the top-level `assets` (the "Tài sản đang giao dịch" table) USED to be
# three fields that never survived this round trip -- none was ever written
# into assessment.json's `bang_chung`/`mo_phong`, so a file-sourced
# `/bot/<code>` page was permanently stuck at 5 `<svg>`/8 `<details>`
# instead of the 7/12 a live or snapshot-sourced page has (the first two
# cost the 2 missing `<svg>`; `assets` is a table, not a chart, so it only
# cost 1 of the 4 missing `<details>` -- found by actually counting tags on
# both paths, not by assuming the two known chart fields were the whole
# gap). Fixed at the source: `run_report.py`'s `build_assessment_extras` now
# re-fetches each row's own `BotResult` (same mechanism already used for the
# strategy/behavioural evidence just below) and `assessment_store.
# build_assessment` persists all three (`bang_chung.closed_trade_series`,
# `bang_chung.assets`, `mo_phong.horizon_scenarios`, schema
# `bot_assessment.v2`) -- see that function's own docstring. This block
# below just reads them back with the SAME defensive `isinstance(...,
# list)` degrade every other optional field here already uses, so an
# assessment.json written BEFORE this fix (schema v1, none of the three
# keys present) still loads fine -- it only keeps missing the two charts and
# the table, exactly like before, never an error. Everything else --
# verdict, both scores, all measured risk dimensions, the strategy/
# behavioural profile, the phase x performance cross-tab, Monte Carlo
# percentiles, statistical inference, the Vietnamese recommendation text,
# and the Claude narrative -- already round-tripped in full.
#
# `sibling_analysis_documents` (optional, best-effort) additionally reads
# the SAME bot's step-2 `data/analysis/**/bot/<name>__<code>/{performance,
# monte_carlo}.json` (written by the same run_report.py pass, one directory
# over from `assessment/`) to recover a few fields step 3 does not itself
# carry (`average_win`/`average_loss` for the win/loss profit pie;
# `sharpe_per_trade`/`sample_size`/`inference_notes` for the statistical
# inference table). Missing/unreadable/malformed -- an older assessment
# written before step 2 persisted these, or a bot scored without step 2
# ever running -- degrades to simply not adding those extra fields, never
# an error: the assessment.json-derived result is already complete without
# it.
# --------------------------------------------------------------------------- #

_ASSESSMENT_STRATEGY_KEYS: Tuple[str, ...] = (
    "observed_profile",
    "declared_strategy",
    "directional_bias",
    "entry_style",
    "entry_style_evidence",
    "phase_coverage_pct",
    "regime_dependence_pct",
    "best_phase",
    "worst_phase",
    "tested_in_downtrend",
    "tested_in_trend",
)
_ASSESSMENT_STRATEGY_LIST_KEYS: Tuple[str, ...] = ("losing_phases", "untested_phases")
_ASSESSMENT_BEHAVIORAL_KEYS: Tuple[str, ...] = (
    "martingale_escalation_detected",
    "averaging_down_detected",
    "loss_chasing_score",
    "overtrading_score",
    "reentry_loop_detected",
    "size_escalation_score",
    "leverage_escalation_detected",
    "behavioral_risk_tier",
)
_ASSESSMENT_PERFORMANCE_KEYS: Tuple[str, ...] = (
    "trade_count",
    "win_rate",
    "profit_factor",
    "marked_profit_factor",
    "payoff_ratio",
    "expectancy",
    "total_pnl",
    "max_drawdown_pct",
    "sharpe_ratio",
    "sortino_ratio",
    "pnl_skew",
    "pnl_kurtosis",
    "open_positions",
    "open_loss",
    "open_loss_to_capital_pct",
    "capital_at_risk",
    "capital_basis",
    "measurement_mode",
    "reconciliation_status",
    "ledger_coverage_days",
    "declared_lead_days",
)
# Sibling-analysis enrichment only -- see the module comment above.
_ANALYSIS_PERFORMANCE_ENRICH_KEYS: Tuple[str, ...] = (
    "average_win",
    "average_loss",
    "calmar_ratio",
    "max_win_streak",
    "max_loss_streak",
)


def _find_bot_subpath(
    data_dir: Path, root_name: str, code: str, filename: str
) -> Optional[Path]:
    """One file for `code` under `data_dir/<root_name>/**/bot/*__<code>/<filename>`
    -- the shared lookup both `assessment/.../assessment.json` (the
    canonical step-3 record) and `analysis/.../{performance,monte_carlo}.json`
    (the optional step-2 enrichment) use below. `code` has already passed
    `validate_unique_code` (alnum-only) by the time either caller reaches
    this, so it is safe to interpolate directly into a glob pattern -- no
    path-traversal characters (`.`, `/`) can survive that validation.
    """
    root = Path(data_dir) / root_name
    if not root.is_dir():
        return None
    try:
        matches = sorted(root.glob(f"**/bot/*__{code}/{filename}"))
    except OSError:
        return None
    return matches[0] if matches else None


def _read_json_document(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def find_assessment_document(data_dir: Path, code: str) -> Optional[Dict[str, Any]]:
    """The one `assessment.json` already scored for `code`, or `None` when
    this bot has never been through `run_report.py` -- the ONE signal
    `_bot_report_response` (app.py) needs to decide "read from disk" vs.
    "analyze live".
    """
    return _read_json_document(
        _find_bot_subpath(data_dir, "assessment", code, "assessment.json")
    )


def sibling_analysis_documents(
    data_dir: Path, code: str
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Best-effort `(performance.json, monte_carlo.json)` for the SAME `code`
    from `data/analysis/**` -- see this module's section docstring above.
    Either or both come back `None` when not on disk/unreadable; never
    raises.
    """
    perf = _read_json_document(
        _find_bot_subpath(data_dir, "analysis", code, "performance.json")
    )
    mc = _read_json_document(
        _find_bot_subpath(data_dir, "analysis", code, "monte_carlo.json")
    )
    return perf, mc


def find_bot_market_document(
    data_dir: Path, code: str, symbol: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Best-effort `market.json` from `data/analysis/<venue>/<symbol>/market/market.json`
    associated with this bot's dominant traded market."""
    perf_path = _find_bot_subpath(data_dir, "analysis", code, "performance.json")
    if perf_path is not None:
        try:
            market_candidate = perf_path.parent.parent.parent / "market" / "market.json"
            if market_candidate.is_file():
                return _read_json_document(market_candidate)
        except (ValueError, OSError):
            pass
    if symbol:
        sym_clean = symbol.strip().upper()
        root = Path(data_dir) / "analysis"
        if root.is_dir():
            try:
                for candidate in sorted(
                    root.glob(f"**/{sym_clean}/market/market.json")
                ):
                    doc = _read_json_document(candidate)
                    if doc is not None:
                        return doc
            except OSError:
                pass
    return None


def assessment_generated_at_ms(doc: Dict[str, Any]) -> Optional[int]:
    value = doc.get("generated_at_ms") if isinstance(doc, dict) else None
    return int(value) if _is_finite_number(value) else None


def _dimensions_from_cham_diem(cham_diem: Dict[str, Any]) -> Dict[str, Any]:
    dims: Dict[str, Any] = {}
    scores = cham_diem.get("dimension_scores")
    if isinstance(scores, dict):
        for key, value in scores.items():
            if not isinstance(key, str) or not _is_finite_number(value):
                continue
            score = float(value)
            dims[key] = {
                "dimension_name": key,
                "score": score,
                "tier": tier_for(score).value,
                "status": "AVAILABLE",
                "key_findings": [],
            }
    unknown = cham_diem.get("unknown_dimensions")
    # Lý do "vì sao chiều này không đo được" do chính ống kính sinh ra. Bản
    # ghi cũ (trước khi khoá này tồn tại) không có nó; khi đó `key_findings`
    # rỗng và trang báo cáo lui về đúng hành vi trước đây -- chỉ ghi "not
    # measured" mà không bịa ra lý do.
    unknown_reasons = cham_diem.get("unknown_dimension_reasons")
    if not isinstance(unknown_reasons, dict):
        unknown_reasons = {}
    if isinstance(unknown, list):
        for key in unknown:
            if isinstance(key, str) and key not in dims:
                reason = unknown_reasons.get(key)
                dims[key] = {
                    "dimension_name": key,
                    "score": None,
                    "tier": "UNKNOWN",
                    "status": "UNKNOWN",
                    "key_findings": (
                        [reason] if isinstance(reason, str) and reason.strip() else []
                    ),
                }
    # Gắn trọng số/độ tin cậy vào ĐÚNG chiều tương ứng. Bản ghi cũ không có
    # hai khoá này; khi đó trường vẫn vắng và trang báo cáo lui về câu
    # "weight not present in the saved record" như trước, không bịa số.
    for source_key, target_key in (
        ("dimension_weights", "weight"),
        ("dimension_confidence", "confidence"),
    ):
        source = cham_diem.get(source_key)
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if key in dims and _is_finite_number(value):
                dims[key][target_key] = float(value)
    return dims


def _string_list(value: Any) -> List[str]:
    return (
        [v for v in value if isinstance(v, str) and v.strip()]
        if isinstance(value, list)
        else []
    )


def assessment_to_analyze_result(
    doc: Dict[str, Any],
    *,
    analysis_doc: Optional[
        Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]
    ] = None,
    market_doc: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Reshape one `assessment.json` document (see
    `Agent/backend/qc/reporting/assessment_store.py`'s `build_assessment` for
    the exact shape written) into the SAME dict `WebDataService.analyze()`
    returns for a FULL bot -- see this module's section docstring above for
    the full contract and its one honest gap (no `closed_trade_series`, no
    per-horizon Monte Carlo scenarios).

    `analysis_doc`, when given, is `(performance.json, monte_carlo.json)`
    read from the SAME bot's sibling `data/analysis/**` entry (see
    `sibling_analysis_documents` above) -- purely additive enrichment, never
    required for a valid result.

    Returns `None` only when `doc` is too malformed to even carry a bot code
    (mirrors `bot_listing_row`'s own "too broken to show OR key" rule) --
    every other partial/missing field degrades to `None`/empty exactly the
    way `report_page.py` already expects from a live FULL result.
    """
    if not isinstance(doc, dict):
        return None
    bot = doc.get("bot") if isinstance(doc.get("bot"), dict) else {}
    code = bot.get("unique_code")
    if not isinstance(code, str) or not code.strip():
        return None

    cham_diem = doc.get("scoring") if isinstance(doc.get("scoring"), dict) else {}
    bang_chung = (
        doc.get("evidence") if isinstance(doc.get("evidence"), dict) else {}
    )
    mo_phong = doc.get("simulation") if isinstance(doc.get("simulation"), dict) else {}
    khuyen_nghi = (
        doc.get("recommendation") if isinstance(doc.get("recommendation"), dict) else {}
    )

    risk = cham_diem.get("risk_score")
    if not _is_finite_number(risk):
        risk = khuyen_nghi.get("risk_score")
    quality = cham_diem.get("quality_score")
    if not _is_finite_number(quality):
        quality = khuyen_nghi.get("quality_score")
    confidence = khuyen_nghi.get("confidence")
    risk_val = float(risk) if _is_finite_number(risk) else None
    quality_val = float(quality) if _is_finite_number(quality) else None
    hidden_flags = _string_list(cham_diem.get("hidden_risk_flags"))
    # Same recomputation `bot_listing_row` above already does for the
    # listing table, for the same reason (`label_from_scores`'s own
    # docstring): the frozen `khuyen_nghi.ket_luan` string is the retired
    # single-axis label, not today's two-axis one.
    verdict = label_from_scores(risk_val, quality_val, hidden_flags)

    strategy: Dict[str, Any] = {k: bang_chung.get(k) for k in _ASSESSMENT_STRATEGY_KEYS}
    for key in _ASSESSMENT_STRATEGY_LIST_KEYS:
        strategy[key] = _string_list(bang_chung.get(key))
    phase_breakdown = bang_chung.get("phase_breakdown")
    strategy["phase_breakdown"] = (
        phase_breakdown if isinstance(phase_breakdown, list) else []
    )
    behavioral: Dict[str, Any] = {
        k: bang_chung.get(k) for k in _ASSESSMENT_BEHAVIORAL_KEYS
    }

    performance: Dict[str, Any] = {
        k: bang_chung[k] for k in _ASSESSMENT_PERFORMANCE_KEYS if k in bang_chung
    }

    mc: Dict[str, Any] = {
        "iterations": mo_phong.get("iterations"),
        "horizon_trades": mo_phong.get("horizon_trades"),
        "profit_pct_worst": mo_phong.get("profit_pct_worst"),
        "profit_pct_p05": mo_phong.get("profit_pct_p05"),
        "profit_pct_p50": mo_phong.get("profit_pct_p50"),
        "profit_pct_p95": mo_phong.get("profit_pct_p95"),
        "profit_pct_p25": mo_phong.get("profit_pct_p25"),
        "profit_pct_p75": mo_phong.get("profit_pct_p75"),
        "median_max_drawdown": mo_phong.get("median_max_drawdown"),
        "p90_max_drawdown": mo_phong.get("p90_max_drawdown"),
        "p99_max_drawdown": mo_phong.get("p99_max_drawdown"),
        "sample_is_thin": mo_phong.get("sample_is_thin"),
        "warnings": mo_phong.get("warnings"),
        "observed_span_days": mo_phong.get("observed_span_days"),
        "horizon_calendar_days": mo_phong.get("horizon_calendar_days"),
        "horizon_exceeds_observed": mo_phong.get("horizon_exceeds_observed"),
        "horizon_stability_label": mo_phong.get("horizon_stability_label"),
        "p95_max_drawdown": mo_phong.get("p95_max_drawdown"),
        "worst_percentile_drawdown": mo_phong.get("worst_drawdown"),
        "p_ruin": mo_phong.get("p_ruin"),
        "p_loss_after_horizon": mo_phong.get("p_loss_after_horizon"),
        "p_5_loss_streak": mo_phong.get("p_5_loss_streak"),
        "p_10_loss_streak": mo_phong.get("p_10_loss_streak"),
        "p_5_loss_streak_baseline": mo_phong.get("p_5_loss_streak_baseline"),
        "p_10_loss_streak_baseline": mo_phong.get("p_10_loss_streak_baseline"),
        "p_5_loss_streak_excess": mo_phong.get("p_5_loss_streak_excess"),
        "p_10_loss_streak_excess": mo_phong.get("p_10_loss_streak_excess"),
        "deferred_loss_bias": mo_phong.get("deferred_loss_bias"),
        "probabilistic_sharpe": mo_phong.get("psr"),
        "deflated_sharpe": mo_phong.get("deflated_sharpe"),
        "min_track_record_trades": mo_phong.get("min_track_record_trades"),
        "selection_trials": mo_phong.get("selection_trials"),
        "inference_reliable": mo_phong.get("inference_reliable"),
    }
    # Việc mới: SHORT/MEDIUM/LONG comparison -- see this section's own module
    # comment above. Absent (older schema-v1 file, or the re-fetch that
    # would have produced it failed at write time) degrades to `[]`, same
    # value `report_page.py::_render_horizon_comparison`/
    # `_render_horizon_probability_chart` already treat as "hide the
    # section" for a live result with zero scenarios.
    horizon_scenarios = mo_phong.get("horizon_scenarios")
    mc["horizon_scenarios"] = (
        [s for s in horizon_scenarios if isinstance(s, dict)]
        if isinstance(horizon_scenarios, list)
        else []
    )

    if analysis_doc is not None:
        perf_doc, mc_doc = analysis_doc
        if isinstance(perf_doc, dict):
            for key in _ANALYSIS_PERFORMANCE_ENRICH_KEYS:
                if key in perf_doc:
                    performance[key] = perf_doc[key]
        if isinstance(mc_doc, dict):
            if _is_finite_number(mc_doc.get("sharpe_per_trade")):
                mc["sharpe_per_trade"] = mc_doc["sharpe_per_trade"]
            if _is_finite_number(mc_doc.get("mc_sample_size")):
                mc["sample_size"] = mc_doc["mc_sample_size"]
            notes = _string_list(mc_doc.get("inference_notes"))
            if notes:
                mc["inference_notes"] = notes

    # Việc mới: chuỗi lệnh đã chốt cho đường vốn tích luỹ -- see this
    # section's own module comment above. Same `[]`-on-absent degrade as
    # `horizon_scenarios` above (report_page.py's own `_extract_trade_pnls`
    # already treats an empty/missing list as "hide the chart").
    closed_trade_series = bang_chung.get("closed_trade_series")
    closed_trade_series = (
        [row for row in closed_trade_series if isinstance(row, dict)]
        if isinstance(closed_trade_series, list)
        else []
    )
    # Việc mới: per-asset trading state for `report_page.py`'s "Tài sản
    # đang giao dịch" table (`_render_assets`) -- the THIRD field this same
    # fix turned out to need (see this section's own module comment above):
    # `_render_assets` is gated on a non-empty top-level `assets` list, and
    # this used to be hard-coded to `[]` unconditionally below, independent
    # of `closed_trade_series`/`horizon_scenarios`. Same `[]`-on-absent
    # degrade.
    assets = bang_chung.get("assets")
    assets = (
        [a for a in assets if isinstance(a, dict)] if isinstance(assets, list) else []
    )

    # Việc 1: trường bị rơi khi phục vụ từ FILE (đo được thật: bot
    # 72AFDC179D66D034 giao dịch SNDK nhưng `/api/analyze` trả
    # `traded_symbol: null` khi đọc từ assessment.json vì khoá này chưa
    # từng được gán ở đây) -- ưu tiên `bot.traded_symbol`, lùi về
    # `bot.asset_context` khi thiếu, giống hệt `_venue_asset_label` ở trên
    # đã làm cho `GET /api/bots`. Sống trong `evidence` (không phải top
    # level) vì đó là nơi `_full_result` (nhánh live) đặt nó và cũng là nơi
    # `app.py::_analyze_summary_for_wire` đọc lại (`evidence.get(
    # "traded_symbol")`) để đưa ra khoá `traded_symbol` ở gốc JSON trả về.
    traded_symbol = bot.get("traded_symbol") or bot.get("asset_context")

    # Việc 2: `bot.identity.symbol_exposure_share`/`observed_symbols`
    # (Agent/backend/mcp/service.py::_resolve_identity_market) được
    # `assessment_store.py::build_assessment` ghi xuống `bang_chung` từ Việc
    # này trở đi -- đọc lại nguyên trạng, degrade về `[]`/`{}`/`None` cho
    # file CŨ (ghi trước khi ba khoá này tồn tại) thay vì lỗi.
    observed_symbols = _string_list(bang_chung.get("observed_symbols"))
    _raw_share = bang_chung.get("symbol_exposure_share")
    symbol_exposure_share = (
        {k: float(v) for k, v in _raw_share.items() if _is_finite_number(v)}
        if isinstance(_raw_share, dict)
        else {}
    )
    primary_share_pct = bang_chung.get("primary_share_pct")
    primary_share_pct = (
        float(primary_share_pct) if _is_finite_number(primary_share_pct) else None
    )
    # Việc 3: thị trường đứng thứ hai -- xem
    # `assessment_store.py::_secondary_market_payload` cho hình dạng chính
    # xác; `None` khi bot chỉ giao dịch một mã, mã thứ hai không có dữ liệu
    # thị trường, hoặc file được ghi trước khi Việc 3 tồn tại.
    _raw_secondary_market = bang_chung.get("secondary_market")
    secondary_market = (
        _raw_secondary_market if isinstance(_raw_secondary_market, dict) else None
    )
    # Phủ sóng theo mục tiêu -- xem
    # `assessment_store.py::_resolved_markets_payload`/
    # `_unresolved_markets_payload` cho hình dạng chính xác; `[]`/`None` cho
    # file được ghi trước khi tính năng này tồn tại (đơn giản không có ba
    # khoá này trong `bang_chung`), giống hệt cách ba khoá Việc 2/3 ở trên
    # degrade.
    _raw_resolved_markets = bang_chung.get("resolved_markets")
    resolved_markets = (
        [m for m in _raw_resolved_markets if isinstance(m, dict)]
        if isinstance(_raw_resolved_markets, list)
        else []
    )
    _raw_unresolved_markets = bang_chung.get("unresolved_markets")
    unresolved_markets = (
        [m for m in _raw_unresolved_markets if isinstance(m, dict)]
        if isinstance(_raw_unresolved_markets, list)
        else []
    )
    coverage_achieved_pct = bang_chung.get("coverage_achieved_pct")
    coverage_achieved_pct = (
        float(coverage_achieved_pct)
        if _is_finite_number(coverage_achieved_pct)
        else None
    )

    text = _string_list(khuyen_nghi.get("text"))
    narrative_text = doc.get("expert_assessment")
    narrative_text = (
        narrative_text
        if isinstance(narrative_text, str) and narrative_text.strip()
        else None
    )

    return {
        "status": "FULL",
        "code": code,
        "name": bot.get("nick_name") if isinstance(bot.get("nick_name"), str) else code,
        "limited_reason": None,
        "unavailable": [],
        "verdict": verdict,
        "verdict_basis": VERDICT_BASIS_VI,
        "risk": risk_val,
        "quality": quality_val,
        "confidence": float(confidence) if _is_finite_number(confidence) else None,
        "evidence": {
            "traded_symbol": traded_symbol,
            "dimensions": _dimensions_from_cham_diem(cham_diem),
            "score_breakdown": {
                "decided_by": cham_diem.get("score_decided_by"),
                "veto_reasons": _string_list(cham_diem.get("veto_reasons")),
                "weighted_average": cham_diem.get("weighted_average"),
                # Hai số này để câu giải thích nói được CỤ THỂ "N chiều,
                # tổng trọng số W" thay vì câu chung chung tự nhận là
                # không có chi tiết trọng số -- câu mà nay đã mâu thuẫn
                # với chính bảng liệt kê trọng số ngay phía trên nó.
                "total_weight": cham_diem.get("total_weight"),
                "applicable_dimensions": cham_diem.get("applicable_dimensions"),
                # Mang theo ra ngoài, không chỉ dùng nội bộ để tính nhãn:
                # nhãn "RỦI RO BỊ CHE" tự nó không nói được điều gì, người
                # đọc chỉ hiểu khi thấy ĐÚNG thứ đang bị che -- ví dụ "lỗ
                # chưa chốt bằng 43% vốn" hay "chốt hết sổ mở thì profit
                # factor rơi từ 1.09 xuống 0.27". Trước đây JSON trả về đủ
                # 22 trường mà KHÔNG có danh sách này, nên người mua đọc
                # được bốn chữ kết luận mà không biết vì sao.
                "hidden_risk_flags": _string_list(cham_diem.get("hidden_risk_flags")),
            },
            "strategy": strategy,
            "behavioral": behavioral,
            "performance": performance,
            "closed_trade_series": closed_trade_series,
            "observed_symbols": observed_symbols,
            "symbol_exposure_share": symbol_exposure_share,
            "primary_share_pct": primary_share_pct,
            "secondary_market": secondary_market,
            "resolved_markets": resolved_markets,
            "unresolved_markets": unresolved_markets,
            "coverage_achieved_pct": coverage_achieved_pct,
            # Chuyển tiếp nguyên tên khoá đường chấm sống dùng, để khối giải
            # thích ĐỘ TIN CẬY nói được con số thật thay vì "bản ghi đã lưu
            # không mang chi tiết này". Bản ghi cũ (ghi trước khi khoá này
            # tồn tại) không có -> `{}` và trang lui về đúng hành vi cũ.
            "market_available": bang_chung.get("market_available", True),
            "data_quality": (
                bang_chung.get("data_quality")
                if isinstance(bang_chung.get("data_quality"), dict)
                else {}
            ),
            "market_analysis": market_doc or {},
        },
        # KHÔNG lặp lại `market_analysis` ở cấp cao nhất. Nó đã nằm trong
        # `evidence` ngay trên, và `report_page.py` đọc được ở cả hai chỗ.
        # Để bản trùng ở đây khiến nhánh đọc-từ-file có thêm một khoá mà nhánh
        # chạy sống không có -- tức hai nhánh trả về hình dạng JSON khác nhau
        # cho cùng một bot, đúng thứ `test_analyze_from_disk_tier_has_identical
        # _key_set_to_live_tier` sinh ra để chặn.
        "mc": mc,
        "assets": assets,
        "text": text,
        "narrative": narrative_text,
    }


# --------------------------------------------------------------------------- #
# Result-shape helpers for POST /api/analyze
# --------------------------------------------------------------------------- #

# Metrics a LIMITED assessment cannot produce without a visible ledger --
# used only for the "assess_from_error unavailable/failed" fallback below;
# once Agent/backend/analysis/limited.py's own result comes back cleanly, its
# own `unavailable` list replaces this wholesale (see the soft-import block's
# docstring).
_LIMITED_UNAVAILABLE_FIELDS = [
    "profit_factor",
    "deferred_loss",
    "phase_analysis",
    "monte_carlo",
    "psr_dsr",
]


def _empty_result(status: str, code: str, text: List[str]) -> Dict[str, Any]:
    """The shared skeleton of every non-FULL response -- see the `/api/analyze`
    contract: NOT_FOUND and LIMITED both carry every key FULL does, just with
    the scoring fields empty, so a dashboard can render one code path for all
    three statuses instead of branching on which keys exist.
    """
    return {
        "status": status,
        "code": code,
        "name": None,
        "limited_reason": None,
        "unavailable": [],
        "verdict": None,
        "verdict_basis": None,
        "risk": None,
        "quality": None,
        "confidence": None,
        "evidence": {},
        "mc": None,
        # Same per-asset contract /api/lookup exposes (see the shared
        # _build_asset_states above) -- empty here because NOT_FOUND/LIMITED
        # both mean "no visible ledger to derive it from" (see
        # _asset_states_from_bot_result's docstring for the FULL case, which
        # is the only one that ever has something to put here).
        "assets": [],
        "text": text,
        # `None` for every non-FULL status: the narrative feature (see
        # Agent/backend/qc/reporting/narrative.py) is only ever generated
        # from a FULL result's own scored numbers -- NOT_FOUND/LIMITED have
        # no such numbers to narrate. The key is always PRESENT (never
        # omitted), same "giữ khoá để người gọi không phải đoán" contract
        # every other optional-looking field in this dict already follows
        # -- so a caller can check `"narrative" in result` unconditionally
        # rather than guessing whether this status ever produces one.
        "narrative": None,
    }


# A real OKX copy-trading uniqueCode is either hex (e.g.
# "BB3398A957270A39") or a LONG plain-numeric id -- the numeric example in
# `_CODE_RE`'s own comment above ("811997770117827919") is 18 digits. OKX.AI
# Marketplace Agent IDs (a completely different identifier space -- see
# `Agent/backend/web/access.py`'s module docstring for this same
# fee=0/agentId=13753 listing) are, by observed contrast, short: 1-8 plain
# digits (measured live: `{"code":"13753"}` -> NOT_FOUND, while a real
# uniqueCode like `EF1CC6F40E834D1A` -> FULL). A user who copies "13753"
# out of the marketplace UI and pastes it here as if it were a bot code is
# an easy, observed mistake -- this regex is deliberately narrow (short AND
# all-digit) so it only ever fires for a string that plausibly IS an Agent
# ID, never for a genuine long numeric uniqueCode or a hex one.
_AGENT_ID_LOOKALIKE_RE = re.compile(r"^[0-9]{1,8}$")

_AGENT_ID_HINT_VI = (
    " Note: a short, all-digit code like this (1-8 characters) is more "
    "likely an Agent ID on the OKX AI Marketplace (e.g. '13753'), NOT the "
    "uniqueCode of an OKX copy-trading bot -- a uniqueCode is usually a hex "
    "string or a much LONGER numeric string, e.g. 'EF1CC6F40E834D1A'. If "
    "you want to analyse a copy-trading bot, enter that bot's uniqueCode."
)


def _agent_id_lookalike_hint_vi(code: str) -> str:
    """A leading-space Vietnamese sentence to append to a NOT_FOUND
    message when `code` looks like an Agent ID rather than a uniqueCode
    (see `_AGENT_ID_LOOKALIKE_RE`'s own comment) -- empty string otherwise,
    so every existing call site can unconditionally concatenate this onto
    its own message with no extra branching.
    """
    return _AGENT_ID_HINT_VI if _AGENT_ID_LOOKALIKE_RE.match(code) else ""


def _not_found_result(code: str, reason: str) -> Dict[str, Any]:
    return _empty_result(
        "NOT_FOUND",
        code,
        [
            f"Bot with code {code!r} was not found on OKX, or OKX "
            f"temporarily failed to respond for this code. Detail: {reason}"
            f"{_agent_id_lookalike_hint_vi(code)}"
        ],
    )


# Trạng thái thứ tư (bên cạnh FULL/LIMITED/NOT_FOUND) cho hạn cứng đồng bộ
# của POST /api/analyze -- xem app.py's ANALYZE_SYNC_DEADLINE_SECONDS's
# comment cho toàn bộ bối cảnh đo thật (CLI OKX chỉ ĐỌC THÂN phản hồi trong
# ~10s, quá hạn thì bỏ dở thân nhưng vẫn coi endpoint "sống"). PENDING nghĩa
# là service.analyze() CHƯA xong khi chạm hạn -- KHÔNG PHẢI một lỗi, KHÔNG
# PHẢI một kết quả chấm điểm rút gọn (khác hẳn LIMITED) -- pipeline vẫn chạy
# tiếp ở nền, chỉ là response này không thể chờ nó xong nữa.
ANALYZE_STATUS_PENDING = "PENDING"


def pending_result(code: str, text: List[str]) -> Dict[str, Any]:
    """Hình dạng raw giống hệt `_not_found_result`/`_limited_fallback_result`
    ở trên (cùng dùng chung `_empty_result`) nhưng cho `ANALYZE_STATUS_PENDING`
    -- app.py dựng response này khi `/api/analyze` chạm hạn cứng
    `ANALYZE_SYNC_DEADLINE_SECONDS` trước khi `service.analyze()` xong.

    Tái dùng NGUYÊN XI bộ khung rỗng đã có sẵn cho NOT_FOUND/LIMITED (mọi
    khoá chấm điểm -- `verdict`/`risk`/`quality`/`confidence`/`verdict_basis`
    -- đều `None`) thay vì viết một bộ khoá mới có nguy cơ lệch hình dạng:
    đây chính là cách bảo đảm "không bịa điểm rủi ro/điểm chất lượng giả"
    mà không cần một đường logic riêng dễ trôi khỏi ba trạng thái kia.
    `text` là câu tiếng Việt trung thực báo "đang chạy nền, xem link report_url"
    (xem app.py's `ANALYZE_PENDING_TEXT_VI`) -- caller truyền vào thay vì
    hard-code ở đây, vì `app.py` là nơi hằng số user-facing text này sống
    (cùng khuôn mọi câu tiếng Việt hiển thị khác trong module đó).
    """
    return _empty_result(ANALYZE_STATUS_PENDING, code, text)


def _limited_fallback_result(code: str, detail: str) -> Dict[str, Any]:
    """LIMITED response used whenever Agent/backend/analysis/limited.py is
    missing, raises, or returns something that is not the expected contract
    shape -- see the soft-import block's docstring for why this must never
    itself raise.
    """
    result = _empty_result(
        "LIMITED",
        code,
        [
            "This bot does not disclose its order book on OKX, so it cannot "
            "be scored FULL.",
            detail,
        ],
    )
    result["limited_reason"] = "OKX does not disclose this bot's order book (error 60004)"
    result["unavailable"] = list(_LIMITED_UNAVAILABLE_FIELDS)
    return result


def _explanation_vi(code: str, result: Any) -> List[str]:
    """A short Vietnamese narrative for a freshly-scored (FULL) bot.

    Deliberately NOT `Agent.backend.qc.reporting.reasons.recommendation_vi`:
    that function takes a `BotEvaluationRow`, a shape only
    `CohortAssessmentService.scan()` builds (it fills ~100 fields from a
    cohort-wide scan pass -- rank among other bots, portfolio-relative
    dimensions, etc., see cohort.py). Reproducing that here for a single
    ad-hoc live bot would mean duplicating cohort.py's row-construction
    logic, which is off-limits to edit and not meant to be re-implemented
    outside it. This is a smaller, self-contained Vietnamese summary built
    straight from the one bot's own `RiskSupervisionResult` instead.
    """
    assessment = result.risk_assessment
    bot = result.bot_result
    perf = bot.performance
    lines = [
        f"{bot.identity.nick_name} ({code}) — trades {result.traded_symbol}, "
        f"{perf.trade_count} closed trades, win rate {perf.win_rate:.0f}%.",
    ]
    if assessment.quality_score is not None:
        lines.append(
            f"Risk score {assessment.risk_score:.1f}/100, quality score "
            f"{assessment.quality_score:.1f}/100, confidence "
            f"{assessment.confidence:.0f}/100."
        )
    else:
        lines.append(
            f"Risk score {assessment.risk_score:.1f}/100 (not enough "
            "evidence yet to compute a quality score)."
        )
    reason = f"Verdict: {assessment.verdict}"
    if assessment.verdict_reason:
        reason += f" — {assessment.verdict_reason}"
    lines.append(reason)
    if not result.market_available:
        lines.append(
            f"No market data yet for {result.traded_symbol}; market-dependent "
            "risk dimensions are left as UNKNOWN rather than guessed."
        )
    if assessment.hidden_risk_flags:
        lines.append("Hidden risk: " + "; ".join(assessment.hidden_risk_flags))
    if assessment.limitations:
        lines.append("Data limitation: " + "; ".join(assessment.limitations))
    return lines


def _asset_states_from_bot_result(bot: Any) -> List[Dict[str, Any]]:
    """The `assets` field for a FULL /api/analyze result -- built ENTIRELY
    from the ledger/positions `_analyze_full` already fetched to score this
    bot (`bot.current_state.open_positions`, `bot.trade_ledger_summary`), so
    adding it costs no extra OKX request and no extra network round trip.

    TODO(market-context): this does not enrich each asset with live market
    data (current price, liquidity, order-flow, ...) -- deliberately
    deferred per the task's own instruction, specifically to avoid adding
    per-asset market calls to /api/analyze's already-tight latency budget
    (see module docstring's "several seconds of CPU and several OKX
    round-trips"). A caller that wants that context today already has
    GET /api/markets for the assets this project tracks; wiring that
    together with THIS field is future work, not part of this change.

    `open_positions` entries already carry a resolved base symbol (see
    Agent/backend/mcp/positions/snapshot.py's own `_base_symbol`), but
    `trade_ledger_summary` entries keep the raw OKX instId shape
    ("ETH-USDT-SWAP", see TradeLedgerManager.parse_trade_list_with_diagnostics)
    -- hence `_base_symbol` is applied here only to the closed side.
    """
    now_ms = int(time.time() * 1000)
    open_symbols = [p.symbol for p in bot.current_state.open_positions if p.symbol]
    closed_records = [
        (_base_symbol(item.symbol), item.close_time)
        for item in bot.trade_ledger_summary
    ]
    return _build_asset_states(open_symbols, closed_records, now_ms)


def _live_performance_evidence(bot: Any) -> Dict[str, Any]:
    """`evidence["performance"]` của ĐƯỜNG CHẤM SỐNG, ghép cho khớp hình
    dạng mà đường ĐỌC TỪ ĐĨA (`assessment_to_analyze_result`) vẫn trả.

    LỖI ĐƯỢC SỬA (đo thật 18/09): một bot mới chấm sống và một bot đã có
    `assessment.json` cho ra trang báo cáo KHÔNG giống nhau -- bot chấm
    sống thiếu hẳn mục "Kiểm toán vị thế mở & Phân phối lợi nhuận" (13 mục
    so với 14), dù chính bot đó đang có 10 vị thế mở. Nguyên nhân: mục đó
    (`report_page._render_open_positions_audit`) đọc năm trường ngay trong
    `evidence["performance"]`, nhưng ở đường chấm sống `performance` là bản
    dump thuần của `BotPerformanceMetrics` -- nơi KHÔNG hề có năm trường
    đó. Chúng nằm rải ở ba object khác của cùng `BotResult`:

        open_positions           <- current_state.open_positions_count
        open_loss                <- deferred_loss.open_loss
        open_loss_to_capital_pct <- deferred_loss.open_loss_to_capital_pct
        marked_profit_factor     <- deferred_loss.marked_profit_factor
        pnl_skew / pnl_kurtosis  <- trade_statistics.*

    Đường đọc từ đĩa vô tình đúng vì `bang_chung` của assessment.json gom
    sẵn cả năm vào một chỗ. Hàm này lấy đúng từng trường từ đúng nguồn của
    nó -- KHÔNG tính lại, KHÔNG suy diễn, thiếu thì để `None` -- nên hai
    đường cho ra cùng một bộ khoá và cùng một trang.

    Chỉ THÊM khoá còn thiếu, không ghi đè khoá `BotPerformanceMetrics` đã
    có (ví dụ `profit_factor` chốt sổ), để không đổi bất kỳ con số nào mà
    trang đang hiển thị đúng từ trước.
    """
    payload: Dict[str, Any] = bot.performance.model_dump(mode="json")
    extra = {
        "open_positions": getattr(bot.current_state, "open_positions_count", None),
        "open_loss": getattr(bot.deferred_loss, "open_loss", None),
        "open_loss_to_capital_pct": getattr(
            bot.deferred_loss, "open_loss_to_capital_pct", None
        ),
        "marked_profit_factor": getattr(
            bot.deferred_loss, "marked_profit_factor", None
        ),
        "pnl_skew": getattr(bot.trade_statistics, "pnl_skew", None),
        "pnl_kurtosis": getattr(bot.trade_statistics, "pnl_kurtosis", None),
        "capital_at_risk": getattr(bot.capital, "capital_at_risk", None),
        "capital_basis": getattr(bot.capital, "basis", None),
    }
    for key, value in extra.items():
        if payload.get(key) is None:
            payload[key] = value
    return payload


def _closed_trade_series_from_bot_result(bot: Any) -> List[Dict[str, Any]]:
    """The minimal, chart-ready closed-trade sequence
    `report_page.py`'s cumulative equity curve needs -- just
    `close_time`/`realized_pnl`, nothing else from the ledger.

    `bot.trade_ledger_summary` (`List[TradeLedgerItem]`, see
    Agent/backend/mcp/schemas/bot_result.py) already IS exactly the right
    population: one row per CLOSED trade, both `close_time` and
    `realized_pnl` are non-optional fields on that model, and the lenses
    already scoring this bot (`return_r_quality.py`, `behavioral_risk.py`)
    already read the same list for the same reason. Open positions live
    separately in `bot.current_state.open_positions` and are never touched
    here -- this project's own rule throughout (see e.g. the Monte Carlo
    section's own "chỉ dùng lệnh ĐÃ CHỐT" note) is that an unclosed position
    has no realized P&L to plot, so mixing it in would misrepresent it as a
    completed result rather than an open, still-changing one.

    Sorted ascending by `close_time` so `report_page.py` never has to
    re-derive the right order itself -- it only has to trust this one
    contract.
    """
    rows = [
        {"close_time": item.close_time, "realized_pnl": item.realized_pnl}
        for item in bot.trade_ledger_summary
    ]
    rows.sort(key=lambda row: row["close_time"])
    return rows


# --------------------------------------------------------------------------- #
# Strategy/behavioural evidence -- Việc 1's own bug report: `bot.
# strategy_observations`/`bot.behavioral_observations` (Agent/backend/mcp/
# schemas/bot_result.py) are fully computed for every bot (see
# Agent/backend/mcp/analytics/strategy/profile.py /
# Agent/backend/mcp/analytics/behavior/detector.py) and already drive two QC
# lenses (strategy_drift.py, behavioral_risk.py) -- but neither ever reached
# `evidence`, so a reader could see the SCORE those lenses produced without
# ever seeing the underlying "how does this bot actually trade" observation
# the score was computed from. Everything below is read-only reshaping of
# fields that already exist on those two models -- no new statistic, no new
# judgement -- kept to the handful of fields that actually describe HOW the
# bot plays (never a raw `model_dump()` of the whole schema).
# --------------------------------------------------------------------------- #

# Kept local to this module rather than imported from qc/reporting/** or
# mcp/analytics/**, on purpose: those trees are off-limits to touch for this
# task, and translating a handful of enum values into report-facing
# Vietnamese is a presentation concern this module already owns for other
# fields (see e.g. `report_page.py`'s own, independently-kept
# `DIMENSION_LABEL_VI`/`TIER_LABEL_VI` for the same reasoning). Every value
# below is plain, already-fixed Vietnamese prose with NO digit in it -- see
# `_narrative_strategy_profile_vi`'s own docstring for why that matters.
_MARKET_PHASE_VI: Dict[str, str] = {
    "UPTREND_CALM": "uptrend, calm",
    "UPTREND_VOLATILE": "uptrend, highly volatile",
    "DOWNTREND_CALM": "downtrend, calm",
    "DOWNTREND_VOLATILE": "downtrend, highly volatile",
    "RANGE_CALM": "ranging, calm",
    "RANGE_VOLATILE": "ranging, highly volatile",
    "UNKNOWN": "phase not identified",
}

_DIRECTIONAL_BIAS_VI: Dict[str, str] = {
    "LONG_ONLY": "long only, no short trades",
    "SHORT_ONLY": "short only, no long trades",
    "LONG_TILTED": "tilted toward long",
    "SHORT_TILTED": "tilted toward short",
    "TWO_WAY": "trades both directions, fairly balanced",
    "UNKNOWN": "not enough evidence to determine",
}

_ENTRY_STYLE_VI: Dict[str, str] = {
    "TREND_FOLLOWING": (
        "trend-following (buys after price has just risen, sells after it has just fallen)"
    ),
    "MEAN_REVERSION": ("mean-reversion (buys after price has just fallen, sells after it has just risen)"),
    "MIXED": "a mix of both styles, no clear leaning",
    "UNKNOWN": "not enough evidence to determine",
}

# `observed_profile` is a DIFFERENT vocabulary from the three maps above --
# it comes from `BotObservationService._strategy_observations`
# (Agent/backend/mcp/service.py), kept in English there because it doubles
# as the normalization key matched against a bot's own declared strategy
# text (see that function's own comment: translating it would silently
# change which declared strings match, a scoring input this task must not
# touch). This map only translates it for DISPLAY; the underlying value on
# the model is left exactly as that service produces it.
_OBSERVED_PROFILE_VI: Dict[str, str] = {
    "Scalping": "short-term scalping",
    "Swing": "holds trades over swings",
    "DayTrading": "day trading",
    "Grid/Martingale-like": "grid / stacking style (grid, martingale)",
    "UNKNOWN": "not identified",
}

_BEHAVIORAL_TIER_VI: Dict[str, str] = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
    "UNKNOWN": "not measured",
}

# Below this, most of the ledger never got assigned a market phase at all --
# the cross-tab is a strong hint, not a firm conclusion. Deliberately a
# stricter bar than profile.py's own 30% (which only gates whether an
# ENTRY_STYLE gets characterised at all): a reader staring at a table needs
# the warning next to it even when there is just enough coverage to label
# an entry style.
_PHASE_COVERAGE_WARN_PCT = 60.0


def _phase_label_vi(phase: Optional[str]) -> str:
    return _MARKET_PHASE_VI.get(
        str(phase or "UNKNOWN").upper(), "phase not identified"
    )


# Three-tier confidence per phase row -- same vocabulary/thresholds as
# `Agent/backend/web/report_page.py`'s own `_phase_confidence_vi` (kept as a
# separate literal here, same off-limits-tree reasoning as every other
# duplicated vocab/threshold in this module): N>=10 "đủ mẫu" (rút ra được quy
# luật), 3<=N<10 "mẫu mỏng" (chỉ tham khảo), N<3 "chưa đủ ý nghĩa" (không đại
# diện). Used to tag each row of the textual phase table handed to the
# narrative prompt (Việc 2) so the model can see WHICH rows are too thin to
# generalise from, without ever being told to read the raw trade count as a
# rule on its own.
_PHASE_CONFIDENCE_ENOUGH_TRADES = 10
_PHASE_CONFIDENCE_THIN_TRADES = 3
# Import chứ KHÔNG chép lại: prompt của `narrative.py` nhắc đích danh nhãn
# "mẫu quá mỏng", nên hai nơi giữ hai bản chép riêng là cách chắc chắn để
# chúng trôi khỏi nhau (đã xảy ra thật khi dịch sang tiếng Anh).
_PHASE_CONFIDENCE_ENOUGH_VI = narrative.PHASE_CONFIDENCE_ENOUGH
_PHASE_CONFIDENCE_THIN_VI = narrative.PHASE_CONFIDENCE_THIN
_PHASE_CONFIDENCE_INSUFFICIENT_VI = narrative.PHASE_CONFIDENCE_INSUFFICIENT


def _phase_confidence_vi(trades: Any) -> str:
    if (
        not isinstance(trades, (int, float))
        or isinstance(trades, bool)
        or not math.isfinite(trades)
    ):
        return _PHASE_CONFIDENCE_INSUFFICIENT_VI
    if trades >= _PHASE_CONFIDENCE_ENOUGH_TRADES:
        return _PHASE_CONFIDENCE_ENOUGH_VI
    if trades >= _PHASE_CONFIDENCE_THIN_TRADES:
        return _PHASE_CONFIDENCE_THIN_VI
    return _PHASE_CONFIDENCE_INSUFFICIENT_VI


def _strategy_evidence(strategy: Any) -> Dict[str, Any]:
    """Compact `evidence["strategy"]` slice of a `StrategyObservations` --
    only the fields that describe how the bot plays, never the raw
    `model_dump()` of the whole schema (task's own explicit "gọn" request).
    `phase_breakdown` is the one nested list kept in full: it is exactly the
    per-phase cross-tab `report_page.py`'s section ① renders, and each row
    is already small (8 scalar fields).
    """
    return {
        "observed_profile": strategy.observed_profile,
        "declared_strategy": strategy.declared_strategy,
        "directional_bias": strategy.directional_bias,
        "long_share_pct": strategy.long_share_pct,
        "entry_style": strategy.entry_style,
        "entry_style_evidence": strategy.entry_style_evidence,
        "phase_coverage_pct": strategy.phase_coverage_pct,
        "regime_dependence_pct": strategy.regime_dependence_pct,
        "best_phase": strategy.best_phase,
        "worst_phase": strategy.worst_phase,
        "losing_phases": list(strategy.losing_phases),
        "untested_phases": list(strategy.untested_phases),
        "tested_in_downtrend": strategy.tested_in_downtrend,
        "tested_in_trend": strategy.tested_in_trend,
        "phase_breakdown": [
            row.model_dump(mode="json") for row in strategy.phase_breakdown
        ],
    }


def _behavioral_evidence(behavioral: Any) -> Dict[str, Any]:
    """Compact `evidence["behavioral"]` slice of a `BehavioralObservations`
    -- the destructive-pattern flags/scores a reader needs to answer "does
    this bot gồng lỗ / nhồi lệnh / tăng đòn bẩy sau lỗ", never the raw
    `model_dump()` of the whole schema.
    """
    return {
        "martingale_escalation_detected": behavioral.martingale_escalation_detected,
        "averaging_down_detected": behavioral.averaging_down_detected,
        "loss_chasing_score": behavioral.loss_chasing_score,
        "overtrading_score": behavioral.overtrading_score,
        "reentry_loop_detected": behavioral.reentry_loop_detected,
        "size_escalation_score": behavioral.size_escalation_score,
        "leverage_escalation_detected": behavioral.leverage_escalation_detected,
        "behavioral_risk_tier": behavioral.behavioral_risk_tier,
    }


def _narrative_strategy_profile_vi(bot: Any) -> str:
    """The Vietnamese, digit-free strategy/behaviour profile that becomes
    `narrative.NarrativeContext.strategy_profile_vi` -- see that field's own
    docstring for why it must never contain a digit (every actual NUMBER
    describing how this bot plays is carried separately, as a `NumberSpec`,
    by `_phase_breakdown_numbers` below, so the number-lock gate can verify
    it). Built entirely from fixed-vocabulary translations
    (`_DIRECTIONAL_BIAS_VI` etc.) and boolean flags -- never an interpolated
    float -- so it is digit-free BY CONSTRUCTION, not by post-hoc scrubbing;
    see `Agent/none/test/test_narrative.py`'s
    `test_prompt_strategy_profile_context_never_contains_a_digit` for the
    regression guard.

    Explicitly says "chưa đủ bằng chứng" rather than guessing whenever the
    underlying observation is `UNKNOWN` or (for entry style specifically)
    phase coverage was too low to characterise it -- task's own explicit
    "đừng đoán" requirement.
    """
    strategy = bot.strategy_observations
    behavioral = bot.behavioral_observations
    sentences: List[str] = []

    profile_label = _OBSERVED_PROFILE_VI.get(strategy.observed_profile, "not identified")
    sentences.append(f"Trading profile observed from closed trades: {profile_label}.")

    bias_label = _DIRECTIONAL_BIAS_VI.get(
        strategy.directional_bias, "not enough evidence to determine"
    )
    sentences.append(f"Directional bias: {bias_label}.")

    if strategy.entry_style == "UNKNOWN":
        sentences.append("Entry style: not enough evidence to determine.")
    else:
        style_label = _ENTRY_STYLE_VI.get(
            strategy.entry_style, "not enough evidence to determine"
        )
        sentences.append(f"Entry style: {style_label}.")

    if strategy.best_phase:
        sentences.append(
            f"Performs best in the {_phase_label_vi(strategy.best_phase)} market phase."
        )
    if strategy.worst_phase:
        sentences.append(
            f"Performs worst in the {_phase_label_vi(strategy.worst_phase)} market phase."
        )
    if strategy.untested_phases:
        phases = ", ".join(_phase_label_vi(p) for p in strategy.untested_phases)
        sentences.append(f"Has never traded through these market phases: {phases}.")
    if not strategy.tested_in_downtrend:
        sentences.append("No evidence this bot has ever traded through a downtrend.")

    flags: List[str] = []
    if behavioral.martingale_escalation_detected:
        flags.append(
            "shows signs of martingale-style stacking (increasing size after a losing trade)"
        )
    if behavioral.averaging_down_detected:
        flags.append(
            "shows signs of holding losers by adding to a losing position in the same direction"
        )
    if behavioral.leverage_escalation_detected:
        flags.append("shows signs of increasing leverage after a losing trade")
    if behavioral.reentry_loop_detected:
        flags.append("shows signs of repeatedly re-entering trades in a loop")
    if flags:
        sentences.append("Trading behaviour: " + "; ".join(flags) + ".")
    else:
        sentences.append(
            "Trading behaviour: no signs of holding losers, martingale-style "
            "stacking, or increasing leverage after a losing trade found in the "
            "closed-trade data."
        )
    tier_label = _BEHAVIORAL_TIER_VI.get(
        behavioral.behavioral_risk_tier, "not measured"
    )
    # Gọi đúng tên: đây là tier THÔ do bộ dò hành vi xếp từ sổ lệnh/vị thế,
    # KHÁC với điểm chiều "Hành vi giao dịch" đã tính trọng số trong phần chấm
    # điểm. Hai thứ này có thể lệch nhau, và cách gọi cũ ("rủi ro hành vi tổng
    # hợp") khiến tín hiệu thô đọc như kết luận cuối cùng: đo được trên dữ liệu
    # thật là bot có điểm chiều 55 (ELEVATED) nhưng câu này lại nói "nghiêm
    # trọng", rồi Claude chép nguyên vào nhận định. Câu dưới đây vào thẳng
    # prompt sinh nhận định nên phải tự nó đã rõ nghĩa.
    sentences.append(
        f"Raw behaviour signal from the order book (not the scored value): {tier_label}."
    )

    if (
        strategy.phase_coverage_pct is not None
        and strategy.phase_coverage_pct < _PHASE_COVERAGE_WARN_PCT
    ):
        sentences.append(
            "Most trades could not be matched to a specific market phase -- "
            "this is because some of the symbols this bot trades lack a "
            "reference candle series to determine the phase, not because of a "
            "timing mismatch or a phase-transition zone -- so the phase-based "
            "observations are only a suggestion, not a firm conclusion."
        )

    return " ".join(sentences)


def _phase_breakdown_numbers(strategy: Any) -> List["narrative.NumberSpec"]:
    """Every per-phase cross-tab figure the narrative prompt is allowed to
    mention, sorted the same way `report_page.py`'s own table is (profit
    share descending -- the phase that made the money leads). Labels are
    built entirely from `_phase_label_vi` (digit-free) plus a fixed,
    digit-free metric name -- the coordinator's own explicit requirement
    ("không chứa chữ số nào trong phần nhãn/tiêu đề — số chỉ nằm ở giá
    trị"). The values themselves become ordinary `NumberSpec`s, so the
    number-lock gate can verify a narrative did not invent a per-phase
    figure it was never given.
    """
    N = narrative.make_number
    specs: List["narrative.NumberSpec"] = []

    def add(spec: Optional["narrative.NumberSpec"]) -> None:
        if spec is not None:
            specs.append(spec)

    rows = sorted(
        strategy.phase_breakdown,
        key=lambda row: (
            row.profit_share_pct if row.profit_share_pct is not None else float("-inf")
        ),
        reverse=True,
    )
    for row in rows:
        label = _phase_label_vi(row.phase)
        add(N(f"Market phase {label} — trade count", row.trades, decimals=0))
        add(
            N(
                f"Market phase {label} — win rate",
                row.win_rate,
                decimals=1,
                percent=True,
            )
        )
        add(
            N(f"Market phase {label} — profit/loss", row.total_pnl, decimals=0, money=True)
        )
        add(
            N(
                f"Market phase {label} — share of long trades in this phase",
                row.long_share_pct,
                decimals=0,
                percent=True,
            )
        )
        add(
            N(
                f"Market phase {label} — average leverage",
                row.average_leverage,
                decimals=1,
                multiplier=True,
            )
        )
        add(
            N(
                f"Market phase {label} — median holding time in minutes",
                row.median_hold_minutes,
                decimals=0,
            )
        )
        add(
            N(
                f"Market phase {label} — share of total profit contributed",
                row.profit_share_pct,
                decimals=0,
                percent=True,
            )
        )
    if strategy.phase_coverage_pct is not None:
        add(
            N(
                "Share of trades matched to a specific market phase",
                strategy.phase_coverage_pct,
                decimals=0,
                percent=True,
            )
        )
    if strategy.regime_dependence_pct is not None:
        add(
            N(
                "Share of total profit concentrated in a single market phase",
                strategy.regime_dependence_pct,
                decimals=0,
                percent=True,
            )
        )
    return specs


def _phase_breakdown_table_vi(strategy: Any) -> str:
    """Digit-free-LABELLED, human-readable text rendering of the exact same
    per-phase cross-tab `_phase_breakdown_numbers` turns into `NumberSpec`s --
    handed to the narrative prompt as `NarrativeContext.phase_table_vi`
    (Việc 2, "đưa bảng vào prompt Claude") so the model sees the table SHAPE
    (one row per phase, same order, same confidence tags `report_page.py`'s
    own HTML table shows) instead of a flat bag of bullet points, and can
    name a cross-phase PATTERN in one sentence instead of reading every row
    back.

    Every number in a row comes from `narrative.make_number` called with the
    exact same label root and `decimals`/`percent`/`money`/`multiplier`
    flags `_phase_breakdown_numbers` uses for that same field -- so every
    digit this table ever displays is GUARANTEED to be a value already
    placed into `allowed_values` by that function (same deterministic
    rounding, computed from the same `PhasePerformance` row); nothing here
    can trip the number-lock gate the way a re-derived or differently-
    rounded figure could (coordinator's own explicit "bẫy" to avoid: mọi con
    số trong bảng phải nằm trong tập số cấp cho cổng khoá số).

    The header row and every confidence tag are fixed, digit-free Vietnamese
    strings (coordinator's own second explicit "bẫy": nhãn/tiêu đề đưa vào
    prompt không được chứa chữ số -- the historical "phân vị 95" bug this
    project already hit once). Only the per-row VALUES contain digits, and
    those are always one of the allowed `NumberSpec` values above.
    """
    rows = sorted(
        strategy.phase_breakdown,
        key=lambda row: (
            row.profit_share_pct if row.profit_share_pct is not None else float("-inf")
        ),
        reverse=True,
    )
    if not rows:
        return ""
    N = narrative.make_number

    def d(spec: Optional["narrative.NumberSpec"]) -> str:
        return spec.display if spec is not None else "n/a"

    lines = [
        "Market phase | Trade count | Win rate | Profit/loss | Long trade "
        "share | Average leverage | Median hold (min) | Profit share | "
        "Confidence"
    ]
    for row in rows:
        label = _phase_label_vi(row.phase)
        trades = N(f"Market phase {label} — trade count", row.trades, decimals=0)
        win = N(
            f"Market phase {label} — win rate",
            row.win_rate,
            decimals=1,
            percent=True,
        )
        pnl = N(
            f"Market phase {label} — profit/loss", row.total_pnl, decimals=0, money=True
        )
        long_share = N(
            f"Market phase {label} — share of long trades in this phase",
            row.long_share_pct,
            decimals=0,
            percent=True,
        )
        leverage = N(
            f"Market phase {label} — average leverage",
            row.average_leverage,
            decimals=1,
            multiplier=True,
        )
        hold = N(
            f"Market phase {label} — median holding time in minutes",
            row.median_hold_minutes,
            decimals=0,
        )
        share = N(
            f"Market phase {label} — share of total profit contributed",
            row.profit_share_pct,
            decimals=0,
            percent=True,
        )
        confidence = _phase_confidence_vi(row.trades)
        lines.append(
            f"{label} | {d(trades)} | {d(win)} | {d(pnl)} | {d(long_share)} | "
            f"{d(leverage)} | {d(hold)} | {d(share)} | {confidence}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Narrative (Agent/backend/qc/reporting/narrative.py) -- an OPTIONAL, off-by-
# default LLM-authored paragraph that turns this FULL result's own already-
# scored numbers into readable Vietnamese prose. See that module's own
# docstring for the full design (feature flag, gates, fail-closed
# fallback); this section only builds the two inputs it needs FROM this
# bot's own `RiskSupervisionResult` (`assessment`/`bot`, the exact same
# objects `_full_result` below already has in scope) -- it computes no new
# statistic of its own beyond a couple of clearly-labelled RATIOS between
# numbers the engine already produced (see `_narrative_numbers`'s own
# comments), never a new judgement.
# --------------------------------------------------------------------------- #


def _narrative_numbers(result: Any) -> List["narrative.NumberSpec"]:
    """Every number `Agent/backend/qc/reporting/narrative.py`'s prompt is
    allowed to mention for this bot, pulled straight from the same
    `BotRiskAssessment`/`BotResult` objects `_full_result` below reads --
    never re-derived from the trimmed JSON shape that function BUILDS, so
    there is no risk of this list and the rendered report disagreeing about
    what the engine actually computed.

    A missing figure (`None` on the source model -- an unrun simulation, a
    bot with no deferred-loss profile, ...) is skipped outright via
    `narrative.make_number`'s own `None` return, never guessed at or
    defaulted to zero.
    """
    assessment = result.risk_assessment
    bot = result.bot_result
    perf = bot.performance
    mc = bot.simulation_results
    deferred = bot.deferred_loss
    capital = bot.capital
    state = bot.current_state
    breakdown = assessment.score_breakdown

    N = narrative.make_number
    specs: List["narrative.NumberSpec"] = []

    def add(spec: Optional["narrative.NumberSpec"]) -> None:
        if spec is not None:
            specs.append(spec)

    # Deliberately worded WITHOUT the numeric scale ("thang 0-100") in these
    # two labels: narrative.build_prompt only ever allows a narrative to use
    # a NUMBER (a `NumberSpec.value`), never text scanned out of a label --
    # so a label containing "0-100" would put "100" in front of the model
    # on every single call, without it ever being an actual measured figure
    # for THIS bot. See narrative.py's own `build_prompt` comment for the
    # full reasoning (this is exactly the exemption the task forbids).
    add(
        N(
            "Risk score (a composite score, not a percentage -- higher means riskier)",
            assessment.risk_score,
            decimals=1,
        )
    )
    add(
        N(
            "Quality score (a composite score, not a percentage)",
            assessment.quality_score,
            decimals=1,
        )
    )
    add(N("Confidence level of this assessment", assessment.confidence, decimals=0, percent=True))
    add(N("Closed trades", perf.trade_count, decimals=0))
    add(N("Win rate", perf.win_rate, decimals=1, percent=True))
    add(N("Loss rate", perf.loss_rate, decimals=1, percent=True))
    add(N("Profit factor on closed trades", perf.profit_factor, decimals=2))
    add(
        N("Max drawdown recorded", perf.max_drawdown_pct, decimals=1, percent=True)
    )
    add(N("Sharpe ratio", perf.sharpe_ratio, decimals=2))
    add(
        N(
            "Payoff ratio (average win divided by average loss)",
            perf.payoff_ratio,
            decimals=2,
        )
    )
    add(N("Longest losing streak", perf.max_loss_streak, decimals=0))

    if deferred.marked_profit_factor is not None:
        add(
            N(
                "Profit factor if the open book were closed now",
                deferred.marked_profit_factor,
                decimals=2,
            )
        )
    if deferred.open_loss_to_capital_pct is not None:
        add(
            N(
                "Unrealised loss on the open book as a share of reference capital",
                deferred.open_loss_to_capital_pct,
                decimals=1,
                percent=True,
            )
        )

    if mc.p_ruin is not None:
        add(
            N(
                "Probability of account ruin in the simulation",
                mc.p_ruin,
                decimals=1,
                percent=True,
            )
        )
    if mc.p95_max_drawdown is not None:
        # Same reasoning as the risk/quality labels above: "phân vị 95"
        # would put a bare "95" in front of the model that is not itself a
        # `NumberSpec` value -- worded as "nhóm kịch bản xấu" instead so no
        # digit reaches the prompt except the actual measured figure.
        add(
            N(
                "Simulated drawdown in the bad-case band (tail of the distribution)",
                mc.p95_max_drawdown,
                decimals=1,
                percent=True,
            )
        )
    if mc.p_loss_after_horizon is not None:
        add(
            N(
                "Probability of still being in a loss after the simulation horizon",
                mc.p_loss_after_horizon,
                decimals=1,
                percent=True,
            )
        )
    if mc.probability_of_profit is not None:
        add(
            N(
                "Probability of being profitable in the simulation",
                mc.probability_of_profit,
                decimals=1,
                percent=True,
            )
        )
    if mc.deflated_sharpe is not None:
        add(
            N(
                "Probability the edge is real after removing selection effects (Deflated Sharpe)",
                mc.deflated_sharpe * 100.0,
                decimals=1,
                percent=True,
            )
        )
    if mc.selection_trials is not None:
        add(
            N(
                "Number of candidate bots this one was selected from",
                mc.selection_trials,
                decimals=0,
            )
        )
    if mc.iterations:
        add(N("Number of Monte Carlo simulation scenarios", mc.iterations, decimals=0))
    if mc.horizon_trades:
        add(N("Simulation horizon", mc.horizon_trades, decimals=0))
    if mc.trades_per_day is not None:
        add(N("Average trading frequency", mc.trades_per_day, decimals=1))

    if capital.capital_at_risk is not None:
        add(
            N(
                "Reference capital inferred from the actual equity curve",
                capital.capital_at_risk,
                decimals=0,
                money=True,
            )
        )
    if capital.reported_aum is not None:
        add(N("Self-reported AUM on OKX", capital.reported_aum, decimals=0, money=True))
    # Derived ratio (Việc 1's own explicit request; direction fixed by Việc
    # 4 -- see that task's own bug report). The old version unconditionally
    # divided `reported_aum / capital_at_risk`, silently assuming the AUM
    # was always the bigger number. For a bot where the ledger-derived
    # reference capital is actually the BIGGER one (a real observed case:
    # AUM 8,998 vs reference capital 1,436,724), that produced ~0.0063 --
    # rounded to 1 decimal that is "0.0x", which `make_number`'s own text
    # cleanup collapses to the bare digit "0" (see that function's `text in
    # ("", "-")` fallback) -- a narrative then dutifully repeated "bội số
    # 0x", a meaningless claim to a reader who has no idea which number was
    # divided by which. Fixed by always dividing the BIGGER of the two
    # figures by the SMALLER one (a ratio >= 1.0, decimals=1 can therefore
    # never round to "0") and by giving each direction its OWN,
    # unambiguous label naming which figure is the multiple of which -- the
    # model is told the direction directly instead of having to infer (or
    # get backwards) a symmetric "so với" phrasing. Skipped entirely (never
    # a fabricated "gấp 0 lần") when `reported_aum` is exactly 0 or missing,
    # since neither direction is a meaningful multiple of a zero/absent
    # figure.
    if (
        capital.capital_at_risk is not None
        and capital.capital_at_risk > 0
        and capital.reported_aum is not None
        and capital.reported_aum > 0
    ):
        capital_at_risk = capital.capital_at_risk
        reported_aum = capital.reported_aum
        if capital_at_risk >= reported_aum:
            add(
                N(
                    "How many times the inferred reference capital is larger than the self-reported AUM",
                    capital_at_risk / reported_aum,
                    decimals=1,
                    multiplier=True,
                )
            )
        else:
            add(
                N(
                    "How many times the self-reported AUM is larger than the inferred reference capital",
                    reported_aum / capital_at_risk,
                    decimals=1,
                    multiplier=True,
                )
            )
    # Derived ratio: how much of the closed-book profit factor evaporates
    # once every still-open position is marked to market -- the same
    # relationship Agent/backend/qc/reporting/reasons.py's own
    # `_proof_points` highlights by hand for the offline batch report,
    # precomputed here for the same reason as the AUM ratio above.
    if (
        perf.profit_factor is not None
        and perf.profit_factor > 0
        and deferred.marked_profit_factor is not None
    ):
        drop_pct = max(
            0.0,
            (perf.profit_factor - deferred.marked_profit_factor)
            / perf.profit_factor
            * 100.0,
        )
        add(
            N(
                "Share of the edge lost if the open book were closed now",
                drop_pct,
                decimals=0,
                percent=True,
            )
        )
    # Derived ratio: with a payoff ratio below 1, a single loss erases more
    # than one win -- spelling out "bao nhiêu lần" up front means the model
    # never has to compute 1/payoff_ratio itself to make the same point.
    if perf.payoff_ratio is not None and 0 < perf.payoff_ratio < 1:
        add(
            N(
                "How many average wins one average loss wipes out",
                1.0 / perf.payoff_ratio,
                decimals=1,
                multiplier=True,
            )
        )

    if state.gross_exposure is not None:
        add(N("Current total exposure", state.gross_exposure, decimals=0, money=True))
    if state.current_leverage is not None:
        add(N("Current leverage", state.current_leverage, decimals=1, multiplier=True))

    if breakdown.decided_by and breakdown.decided_by != "WEIGHTED_AVERAGE":
        # "10 chiều" dropped from the label for the same reason as the
        # risk/quality/p95 labels above -- see narrative.build_prompt's
        # comment: only an actual `NumberSpec` value may reach the model as
        # a number, never incidental digits sitting inside a label string.
        add(
            N(
                "Weighted average across risk dimensions before any veto/emergency override",
                breakdown.weighted_average,
                decimals=1,
            )
        )
        if breakdown.veto_floor is not None:
            add(
                N(
                    "Veto floor that set the final risk score",
                    breakdown.veto_floor,
                    decimals=1,
                )
            )

    # Việc 3: neo prompt vào cách bot chơi trước khi neo vào rủi ro -- the
    # per-phase cross-tab (Việc bổ sung of the same task) is numbers just
    # like everything else above, so it goes through the exact same
    # `NumberSpec`/number-lock path rather than being smuggled into
    # `NarrativeContext.strategy_profile_vi` as free text.
    specs.extend(_phase_breakdown_numbers(bot.strategy_observations))

    return specs


def _narrative_context(result: Any) -> "narrative.NarrativeContext":
    assessment = result.risk_assessment
    bot = result.bot_result
    return narrative.NarrativeContext(
        verdict=assessment.verdict or "",
        traded_symbol=result.traded_symbol or "",
        # OKX account holder's own free-text display name -- fully
        # attacker-controlled, see narrative.py's own module docstring for
        # why this is the one field that goes through its fenced,
        # explicitly-labelled "this is DATA, not instructions" block rather
        # than the prompt's ordinary trusted context section.
        untrusted_nick_name=bot.identity.nick_name or "",
        strategy_profile_vi=_narrative_strategy_profile_vi(bot),
        phase_table_vi=_phase_breakdown_table_vi(bot.strategy_observations),
    )


# Việc 3 (đưa phần sinh nhận định RA KHỎI đường chờ của người dùng): câu
# TRUNG THỰC thay cho "narrative": None mỗi khi lượt phân tích này VỪA
# CHẤM SỐNG (chưa từng có assessment.json/snapshot nào lưu sẵn nhận định)
# VÀ tính năng narrative có bật (`NORABT_NARRATIVE_BACKEND`) -- xem
# `_narrative_field_for_full_result` bên dưới. Đo thật (project owner,
# 2026-09-17): backend CLI mất ~14.6-14.8s cho một prompt NGẮN, một prompt
# thật (dài hơn nhiều, cộng thêm một lần thử lại nếu bị cổng kiểm duyệt
# chặn) còn lâu hơn -- không có cách nào nhét vừa ngân sách phản hồi
# `/api/analyze` mong muốn, nên endpoint trả kết quả ngay và soạn câu này
# ở NỀN thay vì bắt người gọi chờ. KHÔNG BAO GIỜ dùng cho trường hợp nhận
# định đã có sẵn (đọc từ assessment.json hay từ `_analyze_cache` còn hạn) --
# hai trường hợp đó vẫn trả kèm nhận định thật như cũ, xem
# `assessment_to_analyze_result`/`WebDataService.analyze`'s cache.
NARRATIVE_PENDING_VI = (
    "The written assessment for this bot is being drafted by the language "
    "model in the background (usually 15-45 seconds) and will appear as soon "
    "as it is ready -- revisit the report_url/detail_url of this same analysis "
    "in a few minutes, or call the endpoint again. Every figure and conclusion "
    "in the other sections of this response is already complete and does not "
    "depend on or wait for this text."
)



def _start_background_narrative(
    payload: Dict[str, Any],
    result: Any,
    *,
    backend: Optional["narrative.NarrativeBackend"],
) -> None:
    """Sinh nhận định ở một luồng NỀN (daemon, không giữ tiến trình sống
    nếu nó chưa xong khi tiến trình bị tắt), rồi GHI ĐÈ TẠI CHỖ
    `payload["narrative"]` khi xong -- `payload` là chính dict
    `WebDataService.analyze()` sẽ đưa vào `self._analyze_cache` ngay sau
    khi hàm này trả về (xem `_full_result`), nên bất kỳ lần đọc nào sau đó
    trúng cache đó trong TTL (180s, xem `DEFAULT_ANALYZE_CACHE_TTL_SECONDS`)
    -- một `/api/analyze` gọi lại, hay trang chi tiết `GET /bot/<code>` --
    đều thấy nhận định THẬT một khi luồng nền đã xong, không phải mãi mãi
    thấy `NARRATIVE_PENDING_VI`.

    Tôn trọng ĐÚNG trần đồng thời đã có (`narrative._SEMAPHORE`,
    `threading.BoundedSemaphore`, xem module đó cho lý do KHÔNG được đổi
    sang `asyncio.Semaphore`): luồng này gọi thẳng
    `_generate_narrative_for_full_result` (đồng bộ) -> `generate_narrative_
    sync` -> `asyncio.run(generate_narrative(...))`, mà `generate_narrative`
    tự chờ `_SEMAPHORE` trước khi gọi CLI -- một luồng nền như thế này
    hoàn toàn tương đương một request `/api/analyze` CŨ (trước Việc 3) tự
    chờ semaphore đó trên chính luồng threadpool của Starlette, chỉ khác là
    giờ không ai (không request nào) phải NGỒI CHỜ nó nữa.

    Không rò tài nguyên: nhiều nhất N luồng nền tồn tại đồng thời, với N bị
    chặn TRÊN bởi `narrative.MAX_CONCURRENT_CALLS` (2) -- một luồng thứ ba
    trở đi đơn giản BỊ CHẶN ở bước acquire semaphore bên trong
    `generate_narrative`, không tạo thêm subprocess `claude` nào, và tự
    thoát khi CLI_TIMEOUT_SECONDS hết hạn like mọi lần gọi khác.
    """

    def _run() -> None:
        try:
            text = _generate_narrative_for_full_result(result, backend=backend)
        except Exception:  # noqa: BLE001 - một luồng nền phải không bao giờ
            # ném ra ngoài (không ai đang `await`/bắt exception của nó) --
            # degrade về câu dự phòng tĩnh giống mọi lỗi khác của module này.
            logger.exception(
                "norabt narrative: unexpected error in the background "
                "narrative-generation thread"
            )
            text = narrative.FALLBACK_NARRATIVE_VI
        if text is not None:
            payload["narrative"] = text

    threading.Thread(target=_run, name="norabt-narrative-bg", daemon=True).start()


def _narrative_field_for_full_result(
    payload: Dict[str, Any],
    result: Any,
    *,
    backend: Optional["narrative.NarrativeBackend"] = None,
) -> Optional[str]:
    """Giá trị NGAY LẬP TỨC cho `payload["narrative"]` của một lượt chấm
    SỐNG (`_full_result`, nhánh live/chưa từng chấm) -- `None` khi tính
    năng tắt hẳn (giữ NGUYÊN hành vi trước Việc 3: không luồng nào được
    tạo, không subprocess nào được gọi -- xem `narrative.select_backend_
    from_env`'s docstring, "unset => off" là mặc định được test khoá
    chặt), hoặc `NARRATIVE_PENDING_VI` khi tính năng có bật -- việc sinh
    nhận định thật được đẩy hẳn sang `_start_background_narrative`, không
    bao giờ chạy đồng bộ trên đường chờ của người gọi nữa.
    """
    resolved_backend = (
        backend if backend is not None else narrative.select_backend_from_env()
    )
    if resolved_backend is None:
        return None
    _start_background_narrative(payload, result, backend=resolved_backend)
    return NARRATIVE_PENDING_VI


def _generate_narrative_for_full_result(
    result: Any, *, backend: Optional["narrative.NarrativeBackend"] = None
) -> Optional[str]:
    """`None` when the narrative feature is unconfigured (see
    `narrative.select_backend_from_env`) -- the common case, and the one
    that costs this call nothing beyond building two small Python lists,
    since `narrative.generate_narrative_sync` itself returns `None`
    immediately without spawning anything (see that function's own
    docstring). Any OTHER exception here (e.g. a future schema change on
    `BotRiskAssessment`/`BotResult` this function has not been updated for)
    is caught and degraded to narrative.py's own static
    `FALLBACK_NARRATIVE_VI` rather than failing the whole `/api/analyze`
    call over what is meant to be a purely additive field.
    """
    try:
        numbers = _narrative_numbers(result)
        context = _narrative_context(result)
        return narrative.generate_narrative_sync(numbers, context, backend=backend)
    except Exception:  # noqa: BLE001 - see docstring: additive field, must not
        # take down the rest of an otherwise-successful analysis.
        logger.exception(
            "norabt narrative: unexpected error building numbers/context for a "
            "FULL result -- falling back"
        )
        return narrative.FALLBACK_NARRATIVE_VI


def _secondary_market_evidence(result: Any) -> Optional[Dict[str, Any]]:
    """Việc 3: thị trường đứng thứ hai theo `symbol_exposure_share` cho
    nhánh LIVE (`RiskSupervisionPipeline.run`, pipeline.py) -- CHỈ để trình
    bày, không hề đi qua `QCCoreService.assess_bot()` (chỉ nhận `market`
    chính, xem pipeline.py). `None` khi `pipeline.py` đã tự lọc (bot chỉ
    giao dịch một mã, hoặc mã thứ hai không có dữ liệu thị trường) -- cùng
    hình dạng dict `assessment_store.py::_secondary_market_payload` ghi
    xuống assessment.json, để `report_page.py` đọc một hình dạng duy nhất
    bất kể FULL result đến từ file hay từ lần chấm sống này.
    """
    symbol = getattr(result, "secondary_traded_symbol", None)
    market = getattr(result, "secondary_market_result", None)
    if not symbol or market is None:
        return None
    share = result.bot_result.identity.symbol_exposure_share.get(symbol)
    return {
        "symbol": symbol,
        "share_pct": share * 100.0 if isinstance(share, (int, float)) else None,
        "venue_type": market.venue_type,
        "trend": market.structure_state.trend_state.value,
        "volatility": market.structure_state.volatility_state.value,
        "liquidity_tier": market.liquidity_state.state_tier.value,
        "flow_bias": market.orderflow_state.flow_bias,
        "last_price": market.price_state.last_price,
    }


def _market_coverage_evidence(result: Any) -> Dict[str, Any]:
    """Phủ sóng theo mục tiêu cho nhánh LIVE (`RiskSupervisionPipeline.run`,
    pipeline.py) -- CHỈ để trình bày/đo độ phủ, không hề đi qua
    `QCCoreService.assess_bot()`. Cùng hình dạng dict
    `assessment_store.py::_resolved_markets_payload`/
    `_unresolved_markets_payload` ghi xuống assessment.json, để
    `report_page.py` đọc một hình dạng duy nhất bất kể FULL result đến từ
    file hay từ lần chấm sống này. `[]`/`None` khi bot không đo được
    exposure nào (pipeline.py chỉ giải được đúng thị trường CHÍNH).
    """
    resolved = getattr(result, "resolved_markets", None) or []
    unresolved = getattr(result, "unresolved_markets", None) or []
    return {
        "resolved_markets": [
            {
                "symbol": item.symbol,
                "share_pct": round(item.share_pct, 2),
                "venue_type": item.market.venue_type,
                "trend": item.market.structure_state.trend_state.value,
                "volatility": item.market.structure_state.volatility_state.value,
                "liquidity_tier": item.market.liquidity_state.state_tier.value,
                "flow_bias": item.market.orderflow_state.flow_bias,
                "last_price": item.market.price_state.last_price,
            }
            for item in resolved
        ],
        "unresolved_markets": [
            {
                "symbol": item.symbol,
                "share_pct": round(item.share_pct, 2),
                "reason": item.reason,
            }
            for item in unresolved
        ],
        "coverage_achieved_pct": getattr(result, "coverage_achieved_pct", None),
    }


def _insights_evidence(result: Any) -> Dict[str, Any]:
    """Serialize the deterministic insight modules for the report layer.

    Derived from the SAME `AnalysisDossier` the JSON endpoint and MCP publish,
    not rebuilt here. Rebuilding them independently is what let the two drift:
    this function used to call `build_risk_twin(bot)` without the scenario
    states, so the page showed an empty stressed state while the dossier had
    four, and it omitted claims, user questions and the source ledger
    altogether.

    Never raises: a report must still render if the dossier cannot be built for
    an unusual bot. An absent payload makes each section render its "not
    available" shell, which is the behaviour the renderer already has.
    """
    try:
        from Agent.backend.qc.reporting.dossier import build_analysis_dossier

        dossier = build_analysis_dossier(result)
        payload = dossier.model_dump(mode="json")
        return {
            key: payload[key]
            for key in (
                "executive_essence",
                "behavioral_dna",
                "risk_twin",
                "market_compatibility",
                "failure_modes",
                "scenario_laboratory",
                "validation",
                "uncertainty",
                "claims",
                "user_questions",
                "source_ledger",
            )
        }
    except Exception:  # noqa: BLE001 - see docstring
        logger.exception("could not build insight evidence; sections will be hidden")
        return {}


def _full_result(
    code: str,
    result: Any,
    *,
    narrative_backend: Optional["narrative.NarrativeBackend"] = None,
) -> Dict[str, Any]:
    assessment = result.risk_assessment
    bot = result.bot_result
    _primary_share = bot.identity.symbol_exposure_share.get(result.traded_symbol)
    payload: Dict[str, Any] = {
        "status": "FULL",
        "code": code,
        "name": bot.identity.nick_name,
        "limited_reason": None,
        # The only thing a FULL result can still be missing is market
        # context, when the bot trades an instrument this process has no
        # market data for -- resolve_market() already degrades to
        # market_available=False for that instead of raising (see
        # pipeline.py), so it is surfaced here rather than silently dropped.
        "unavailable": [] if result.market_available else ["market_context"],
        "verdict": assessment.verdict,
        # The fixed sentence answering "sở cứ ở đâu" for the label above --
        # same wording for every bot, because it is evidence about what the
        # SCORE was validated to predict (out-of-sample, 36 bots -- see
        # Agent/docs/out_of_sample_validation.md), not a per-bot computation.
        "verdict_basis": VERDICT_BASIS_VI,
        # Kept on BotRiskAssessment's own 0-100 scale (not rescaled to 0-1):
        # every other consumer of this model in the codebase (agent_server.py's
        # assess_bot tool, the assessment.json files /api/bots serves) uses
        # the same scale, so rescaling only here would make the two
        # endpoints disagree about what "risk": 60 means.
        "risk": assessment.risk_score,
        "quality": assessment.quality_score,
        "confidence": assessment.confidence,
        "evidence": {
            "traded_symbol": result.traded_symbol,
            "market_available": result.market_available,
            "market_resolution": result.market_resolution,
            "universe_eligible": result.universe_eligible,
            "eligibility_reason": result.eligibility_reason,
            "performance": _live_performance_evidence(bot),
            # The deterministic insight modules (Agent/backend/qc/reporting/).
            # They are attached here, once, so the HTML report renders the SAME
            # objects the dossier and the JSON endpoint publish -- rather than
            # re-deriving a second, slightly different version of each in the
            # rendering layer.
            "insights": _insights_evidence(result),
            "current_state": bot.current_state.model_dump(mode="json"),
            "reconciliation": bot.reconciliation.model_dump(mode="json"),
            "data_quality": bot.data_quality.model_dump(mode="json"),
            "dimensions": assessment.dimensions.model_dump(mode="json"),
            "score_breakdown": assessment.score_breakdown.model_dump(mode="json"),
            # Việc 1: how the bot actually plays, computed for every bot and
            # already driving strategy_drift/behavioral_risk's own scores --
            # see `_strategy_evidence`/`_behavioral_evidence`'s own
            # docstrings for why only a compact subset of each schema is
            # kept here.
            "strategy": _strategy_evidence(bot.strategy_observations),
            "behavioral": _behavioral_evidence(bot.behavioral_observations),
            # Chart-only data for report_page.py's cumulative equity curve --
            # NOT part of the public /api/analyze JSON contract: app.py's
            # api_analyze strips this key back out of a COPY of this dict
            # before responding (see _without_closed_trade_series there),
            # because the OKX AI Marketplace response is meant to stay a
            # compact report+recommendation, not a raw per-trade dump running
            # to hundreds of rows. Computed here UNCONDITIONALLY (not behind
            # an opt-in parameter) specifically so WebDataService's own
            # analyze_cache keeps using `code` alone as its key -- both the
            # stripped API response and the full HTML report (GET
            # /bot/<code> / GET /r/<ref>) are derived from the SAME cached
            # result, just presented differently by their own callers.
            "closed_trade_series": _closed_trade_series_from_bot_result(bot),
            # Việc 2/3: xem `assessment_to_analyze_result`'s tương ứng --
            # cùng bốn khoá, để `report_page.py`/`app.py::_analyze_
            # warnings_vi` đọc một hình dạng duy nhất bất kể FULL result đến
            # từ file (assessment.json) hay từ lần chấm sống này.
            "observed_symbols": bot.identity.observed_symbols,
            "symbol_exposure_share": bot.identity.symbol_exposure_share,
            "primary_share_pct": (
                _primary_share * 100.0
                if isinstance(_primary_share, (int, float))
                else None
            ),
            "secondary_market": _secondary_market_evidence(result),
            # Phủ sóng theo mục tiêu (xem Agent/backend/market/coverage.py)
            # -- danh sách ĐẦY ĐỦ mọi thị trường đã/chưa giải được và độ
            # phủ THẬT đã đạt, không chỉ một mã phụ như `secondary_market`
            # ở trên (vẫn giữ nguyên cho tương thích ngược).
            **_market_coverage_evidence(result),
            "market_analysis": (
                result.market_result.model_dump(mode="json")
                if getattr(result, "market_result", None) is not None
                and hasattr(result.market_result, "model_dump")
                else {}
            ),
        },
        # Cùng lý do như nhánh đọc-từ-file: `market_analysis` đã nằm trong
        # `evidence` ngay trên, `report_page.py` đọc được ở cả hai chỗ, và bản
        # trùng ở cấp cao nhất bị `_analyze_summary_for_wire` cuốn thẳng vào
        # JSON trả về -- làm phình hợp đồng wire bằng một khoá không ai khai
        # báo. Bỏ ở cả hai nhánh để hình dạng JSON giống hệt nhau.
        "mc": bot.simulation_results.model_dump(mode="json"),
        # See _asset_states_from_bot_result's own docstring, including the
        # TODO on why this deliberately stops short of live market context.
        "assets": _asset_states_from_bot_result(bot),
        "text": _explanation_vi(code, result),
        # Việc 3: giá trị NGAY LẬP TỨC, không bao giờ chờ CLI Claude --
        # `None` khi tính năng tắt hẳn (giữ nguyên hành vi cũ, xem
        # narrative.py's module docstring), `NARRATIVE_PENDING_VI` khi bật
        # (việc sinh thật diễn ra ở nền, xem `_narrative_field_for_full_
        # result`/`_start_background_narrative` ngay phía trên), rồi tự
        # được GHI ĐÈ bởi câu dự phòng tĩnh hoặc đoạn văn LLM thật một khi
        # luồng nền xong -- nhưng chỉ những caller SAU đó trúng cache mới
        # thấy giá trị mới, KHÔNG BAO GIỜ phản hồi của chính request này
        # (đã trả về từ lâu trước khi luồng nền kịp xong).
        "narrative": None,
    }
    payload["narrative"] = _narrative_field_for_full_result(
        payload, result, backend=narrative_backend
    )
    return payload


# --------------------------------------------------------------------------- #
# report_markdown / report_url -- polish added on top of the already-valid
# `/api/analyze` contract above (OKX's own Marketplace spec only requires
# "HTTP 200 with the result directly" for a free endpoint; every key above
# this point already satisfies that). The buyer-side agent that calls this
# service receives raw JSON and decides for itself how to show it to a
# human -- these two fields save it from having to hand-assemble a write-up
# out of `text[]`/`evidence` itself:
#
#   - `report_markdown`: a ready-to-paste Markdown document. See
#     `build_report_markdown` below for the structure.
#   - `report_url`: a link to this exact bot's own HTML report, served by
#     `GET /bot/<code>` in app.py (which itself just calls `analyze()` again
#     -- the TTL cache above means a click right after the API call costs no
#     extra OKX/CPU work). Included ONLY when it would resolve for an
#     outside caller -- see `report_url_is_usable` below, and the comment in
#     `WebDataService.analyze` where the key is actually added or omitted.
# --------------------------------------------------------------------------- #

# Overridable via env because the right base URL is different on a dev box
# (this default, matching run_web.py's own DEFAULT_HOST/DEFAULT_PORT) than
# once this service sits behind a real domain/reverse proxy -- same
# reasoning as run_web.py's NORABT_WEB_DASHBOARD env var for the dashboard
# path. Read at call time (not module import time) so a test can flip it
# with monkeypatch.setenv without needing to reload this module.
REPORT_BASE_URL_ENV = "NORABT_WEB_REPORT_BASE_URL"
DEFAULT_REPORT_BASE_URL = "http://127.0.0.1:8770"


def report_base_url() -> str:
    return os.environ.get(REPORT_BASE_URL_ENV, DEFAULT_REPORT_BASE_URL).rstrip("/")


def build_report_url(code: str) -> str:
    """`code` is expected to already have passed `validate_unique_code`
    (alnum-only, bounded length) by the time this is called from
    `WebDataService.analyze` -- so, unlike the Markdown builder below, this
    never has to defend against a hostile path segment itself.
    """
    return f"{report_base_url()}/bot/{code}"


# --------------------------------------------------------------------------- #
# Whether `report_base_url()` is something an EXTERNAL caller could actually
# reach -- this gates whether `analyze()` includes `report_url` in its
# response at all (see the comment there).
#
# WHY this matters here specifically: this service is listed on the OKX AI
# Marketplace, so the process reading this JSON is a STRANGER's agent,
# running on a STRANGER's machine -- never this host. When
# NORABT_WEB_REPORT_BASE_URL is unset, `report_base_url()` falls back to
# DEFAULT_REPORT_BASE_URL ("http://127.0.0.1:8770"), and "127.0.0.1" means
# something completely different to that caller than it does here: it
# points at THEIR OWN box, where nothing is listening for this. Handing that
# out as `report_url` is not a harmless placeholder, it is actively WRONG --
# a syntactically normal http:// URL a buyer-side agent/UI has every reason
# to render as a clickable link, only for a human to click it and land on
# nothing. The same reasoning applies to any other loopback/private-network
# address (`localhost`, `0.0.0.0`, `10.0.0.0/8`, `172.16.0.0/12`,
# `192.168.0.0/16`, and their IPv6 equivalents): every one of them is only
# meaningful on whoever is running THIS process, never on the caller. The
# real public domain (agent.expsolution.io) is not live yet (DNS pending);
# until an operator points NORABT_WEB_REPORT_BASE_URL at a real,
# externally-routable address, no `report_url` should be handed out at all.
# --------------------------------------------------------------------------- #


def _is_public_report_host(hostname: Optional[str]) -> bool:
    """True only for a hostname/address an outside caller could plausibly
    reach. `localhost` and anything `ipaddress` classifies as loopback,
    unspecified (`0.0.0.0`), link-local, or a private-use range (`10/8`,
    `172.16/12`, `192.168/16`, and their IPv6 equivalents -- all covered by
    `is_private`) come back False. A hostname that fails to parse as an IP
    address at all (e.g. a real DNS name like "agent.expsolution.io") is
    assumed to be a normal public domain: this module has no DNS resolver of
    its own to check further, and a real domain is exactly what an operator
    is expected to configure once one exists.
    """
    if not hostname:
        return False
    host = hostname.strip().lower()
    if host in ("localhost", "localhost.localdomain"):
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        addr.is_loopback
        or addr.is_unspecified
        or addr.is_link_local
        or addr.is_private
        or addr.is_reserved
    )


def report_url_is_usable() -> bool:
    """Gate for including `report_url` (and any report-embedded link built
    from the same base) in an `/api/analyze` response -- see the block
    comment above. Reads `report_base_url()` at call time, same as
    `build_report_url`, so it always reflects whatever the response is about
    to embed rather than a stale snapshot from process start.
    """
    base = report_base_url()
    if not base:
        return False
    try:
        hostname = urlsplit(base).hostname
    except ValueError:
        return False
    return _is_public_report_host(hostname)


# Markdown characters `_md_escape` always backslash-escapes, regardless of
# WHERE in the string they land -- these are the ones CommonMark gives
# mid-line meaning to (emphasis */_, code spans `, links/images [](), GFM
# tables |, GFM strikethrough ~~) plus the escape character itself (\\),
# which must go first or it would re-activate whatever this function
# escapes afterwards. `#` is included too even though ATX headings are only
# special at the true start of a line -- see `build_report_markdown`'s own
# docstring for why every untrusted value it embeds is already guaranteed
# to land after a non-empty literal prefix on the same line (so a leading
# "#" from untrusted input could never actually BE a line's first
# character); escaping it anyway is a free extra guard specifically against
# the highest-impact spoof (a fake section heading), at effectively zero
# readability cost since '#' essentially never occurs in a real bot name.
#
# Deliberately NOT in this set: `-` `+` `.` `!` `{` `}` `>`. The first four
# are CommonMark-special ONLY as the very first characters of a line (list
# markers, ordered-list ".", or -- for "!" -- only immediately before an
# unescaped "["), which the same line-start guarantee above already rules
# out; escaping them regardless of position would just litter ordinary
# names/sentences ("Modern-dAPI-Manatee", "v1.2", full stops) with visible
# backslashes for no safety gain. `{`/`}` have no meaning in CommonMark at
# all. `>` is handled separately, by the HTML-escape step below (`&gt;`),
# which also neutralizes it as a blockquote marker.
_MD_STRUCTURAL_CHARS_RE = re.compile(r"([\\`*_\[\]()#|~])")
# Every flavour of line break/paragraph separator a hostile bot name could
# smuggle in, collapsed to a single space. This is the important half of
# the defence: every *block-level* Markdown construct (heading, list item,
# blockquote, fence, table row, horizontal rule) requires being at the
# start of a line, so a string that can never contain a newline can never
# open a new block, no matter what characters remain in it.
_MD_LINE_BREAK_RE = re.compile(r"[\r\n  \v\f]+")
# Remaining C0/DEL control characters (line breaks already handled above) --
# dropped outright, they have no legitimate display purpose in a report.
_MD_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Hard cap on any single untrusted string embedded in the report. A bot's
# display name is set by whoever registered that OKX copy-trading account --
# not by this service -- and this Markdown is meant to be pasted verbatim
# into another agent's own context, so there is no reason to forward an
# arbitrarily long payload just because OKX's API would accept one.
MD_UNTRUSTED_MAX_LEN = 200
# Narrative lines (from `text[]`) are naturally longer prose, not a single
# field like a name -- given more room before truncating.
MD_NARRATIVE_MAX_LEN = 500


def _md_escape(value: Any, *, max_len: int = MD_UNTRUSTED_MAX_LEN) -> str:
    """Make an arbitrary, untrusted string safe to embed inline in the
    Markdown report built by `build_report_markdown`.

    The concrete threat: a bot's nick_name (or, less critically, other
    OKX-sourced free text) is attacker-controlled and flows into a document
    another LLM/agent is expected to read, and quite possibly render. Left
    unescaped, a nick_name containing e.g. a leading "# " (fake heading), a
    fake ```` ``` ```` fence, a fake "| Verdict | SAFE |" table row, or
    embedded newlines fabricating extra sections could make the pasted-in
    report say something this service never computed -- a markdown/prompt
    injection, not just a rendering glitch. Every step here is defensive,
    never merely cosmetic:

      1. Truncate: bound how much of a hostile payload ever reaches the
         document at all.
      2. Collapse every line-break-like character to a space -- kills every
         block-level injection (see `_MD_LINE_BREAK_RE`'s own docstring).
      3. Drop remaining control characters.
      4. HTML-escape `&`/`<`/`>`, in case the Markdown is ever rendered to
         HTML with inline-HTML passthrough (so a literal `<script>` or
         `<img onerror=...>` in a name can never become live markup).
      5. Backslash-escape every CommonMark structural character, even
         mid-line (see `_MD_STRUCTURAL_CHARS_RE`).
    """
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "…"
    text = _MD_LINE_BREAK_RE.sub(" ", text)
    text = _MD_CONTROL_CHARS_RE.sub("", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _MD_STRUCTURAL_CHARS_RE.sub(r"\\\1", text)
    return text


def _fmt_score(value: Any, digits: int = 1) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    return f"{value:.{digits}f}"


def _fmt_pct(value: Any, digits: int = 1) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    return f"{value:.{digits}f}%"


def _fmt_int(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    return str(int(round(value)))


# Vietnamese labels for every code `unavailable` can carry -- both the FULL
# pipeline's own ("market_context", see `_full_result`) and
# Agent/backend/analysis/limited.py's (the rest; see that module's
# ALWAYS_UNAVAILABLE/MONTE_CARLO_KEY/PSR_DSR_KEY and the extra keys it
# appends per-bot: "drawdown_pct", "win_ratio", "profile"). A key this dict
# does not recognise (future field added on either side) still renders --
# see `_unavailable_label`'s fallback -- so this list is convenience, not a
# contract either side must keep in sync with this module.
_UNAVAILABLE_LABELS_VI = {
    "profit_factor": "Profit factor",
    "deferred_loss": "Deferred loss analysis",
    "phase_analysis": "Market-phase analysis",
    "monte_carlo": "Monte Carlo simulation",
    "psr_dsr": "PSR / DSR (statistical confidence)",
    "market_context": "Market context (price, liquidity, order flow)",
    "drawdown_pct": "Exact per-trade max drawdown",
    "win_ratio": "Exact per-trade win rate",
    "profile": "Lead-trader leaderboard profile",
}


def _unavailable_label(key: str) -> str:
    return _UNAVAILABLE_LABELS_VI.get(key) or _md_escape(key, max_len=60)


def _mc_section_lines(mc: Optional[Dict[str, Any]]) -> List[str]:
    """Bullet lines summarising `mc` (either FULL's `SimulationResults` dump
    or Agent/backend/analysis/limited.py's own, smaller Monte Carlo payload
    -- both are plain dicts using the same field names, since the latter is
    `result.model_dump()` of a result from the very same simulation engine,
    see that module's `_monte_carlo_component_and_payload`). Every field is
    read with `.get()` and formatted defensively, so neither shape's extra
    or missing keys can raise.
    """
    if not isinstance(mc, dict) or not mc:
        return ["No Monte Carlo simulation data for this bot."]
    lines: List[str] = []
    iterations = mc.get("iterations")
    horizon = mc.get("horizon_trades")
    if iterations:
        line = f"Simulated scenarios: {_fmt_int(iterations)}"
        if horizon:
            line += f", horizon {_fmt_int(horizon)} trades"
        lines.append(line)
    p05, p50, p95 = (
        mc.get("profit_pct_p05"),
        mc.get("profit_pct_p50"),
        mc.get("profit_pct_p95"),
    )
    if p05 is not None or p50 is not None or p95 is not None:
        lines.append(
            "Simulated profit percentile (P05 / P50 / P95): "
            f"{_fmt_pct(p05)} / {_fmt_pct(p50)} / {_fmt_pct(p95)}"
        )
    if mc.get("p_ruin") is not None:
        lines.append(f"Probability of ruin (p_ruin): {_fmt_pct(mc.get('p_ruin'))}")
    if mc.get("probability_of_profit") is not None:
        lines.append(f"Probability of profit: {_fmt_pct(mc.get('probability_of_profit'))}")
    if mc.get("median_max_drawdown") is not None:
        lines.append(
            f"Median simulated max drawdown: {_fmt_pct(mc.get('median_max_drawdown'))}"
        )
    if mc.get("is_valid") is False:
        lines.append(
            "Note: the simulation is flagged is_valid=False (the input "
            "sample is not yet large enough to be reliable)."
        )
    return lines or ["A simulation ran but there are not enough figures to summarise."]


REPORT_DISCLAIMER_VI = (
    "This is an automated risk assessment based on OKX's public data, NOT "
    "investment advice. The reader is solely responsible for their own "
    "decisions."
)

# The exact Vietnamese call-to-action line appended to BOTH
# `report_markdown` (via `build_report_markdown`'s own `detail_url`
# parameter below) and the `text` array of /api/analyze's JSON response
# (see app.py's `_with_detail_link`) whenever a "chi tiết trực quan" page
# actually exists for this response -- either GET /bot/<code> or, once
# access-token protection is on, the obscure GET /r/<ref> (see
# Agent/backend/web/access.py). Built through this ONE shared function so
# both places can only ever say the exact same thing, rather than two
# independently hand-typed copies of the same sentence drifting apart over
# time. Neither this constant nor this function knows or cares which of
# those two URL shapes `url` is -- that decision belongs entirely to
# app.py's api_analyze, which is the only place that knows whether THIS
# request was authenticated with a token.
DETAIL_LINK_LABEL_VI = (
    "View the full visual detail (charts, complete metrics, per-item evidence)"
)


def detail_link_line(url: str) -> str:
    return f"{DETAIL_LINK_LABEL_VI}: {url}"


def build_report_markdown(
    result: Dict[str, Any],
    *,
    generated_at: Optional[str] = None,
    detail_url: Optional[str] = None,
) -> str:
    """Build the ready-to-paste Markdown added to `/api/analyze`'s response
    as `result["report_markdown"]`.

    `result` is this endpoint's own response dict (FULL, LIMITED or
    NOT_FOUND shape -- see `_full_result`/`_limited_fallback_result`/
    `_not_found_result`/`assess_from_error`, all of which share the same
    key set -- or `pending_result`'s PENDING shape, app.py's own hard-
    deadline branch, which shares that exact same skeleton via
    `_empty_result` and therefore renders here with no special-casing:
    `status` simply falls through both the LIMITED/NOT_FOUND `elif`
    branches below untouched). Every free-text field pulled from it that
    can trace back to
    OKX-supplied, attacker-controlled data (today: just `name`, a bot's own
    nick_name, and the `text[]` narrative lines, which embed that same name
    -- see `_explanation_vi`) is passed through `_md_escape` before being
    interpolated; every other field here (verdict/scores/metrics/`code`) is
    either a number or was already validated alnum-only by
    `validate_unique_code`, so it needs no escaping of its own.

    `generated_at` is injectable so a test can assert on it deterministically
    instead of racing wall-clock time; defaults to now (UTC).

    `detail_url`, when given, appends exactly ONE more line at the very end
    of the document (after the disclaimer) via `detail_link_line` above.
    This function has -- and needs -- no notion of access tokens or of
    which URL shape (`/bot/<code>` vs the obscure `/r/<ref>`) is correct
    for a given caller; it only knows how to render whatever URL string it
    is handed (see app.py's `_with_detail_link`, the sole caller that ever
    passes this). `None`, the default, renders nothing extra -- purely
    additive, so every call site/test written before this parameter existed
    keeps working unchanged.

    Structural invariant every call site below relies on (see
    `_MD_STRUCTURAL_CHARS_RE`'s own comment): every `_md_escape(...)` result
    is interpolated immediately after a non-empty literal string this
    function itself writes on the SAME output line ("# " for the title,
    "> " for a LIMITED reason, "- " for a bullet, ...) -- so even though
    `_md_escape` does not escape line-start-only markers like "-"/"."/"!",
    untrusted input can never actually reach a true line start to trigger
    one. If a future edit ever appends an escaped value as a line's very
    first character, this invariant -- and the reasoning behind
    `_MD_STRUCTURAL_CHARS_RE`'s exclusions -- must be revisited.
    """
    status = result.get("status") or "NOT_FOUND"
    code = result.get("code") or "?"
    name = _md_escape(result.get("name") or code)
    verdict = _md_escape(result.get("verdict")) or "—"
    risk = _fmt_score(result.get("risk"))
    quality = _fmt_score(result.get("quality"))
    confidence = _fmt_score(result.get("confidence"))

    lines: List[str] = [f"# {name} (`{code}`)", ""]
    lines.append(
        f"**Verdict: {verdict} · Risk score: {risk} · Quality score: "
        f"{quality} · Confidence: {confidence}**"
    )
    lines.append("")

    if status == "LIMITED":
        lines.append(
            "> ⚠️ **LIMITED** — this bot does NOT disclose its order book on "
            "OKX, so this is a REDUCED assessment, not a FULL score."
        )
        reason = _md_escape(result.get("limited_reason"), max_len=300)
        if reason:
            lines.append(f"> {reason}")
        lines.append("")
    elif status == "NOT_FOUND":
        lines.append(
            "> ❌ **Bot not found** with this code on OKX, or OKX "
            "temporarily failed to respond for this code."
        )
        lines.append("")

    unavailable = result.get("unavailable") or []
    if unavailable:
        lines.append("**Could not be computed** (missing data or bot not public):")
        lines.extend(f"- {_unavailable_label(str(key))}" for key in unavailable)
        lines.append("")

    evidence = result.get("evidence")
    perf = evidence.get("performance") if isinstance(evidence, dict) else None
    if isinstance(perf, dict) and perf:
        lines.append("## Key metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Closed trades | {_fmt_int(perf.get('trade_count'))} |")
        lines.append(f"| Win rate | {_fmt_pct(perf.get('win_rate'))} |")
        lines.append(f"| Profit factor | {_fmt_score(perf.get('profit_factor'), 2)} |")
        lines.append(f"| Max drawdown | {_fmt_pct(perf.get('max_drawdown_pct'))} |")
        lines.append(f"| Sharpe ratio | {_fmt_score(perf.get('sharpe_ratio'), 2)} |")
        lines.append("")

    text_lines = result.get("text") or []
    if text_lines:
        lines.append("## Why")
        lines.append("")
        lines.extend(
            f"- {escaped}"
            for item in text_lines
            if (escaped := _md_escape(item, max_len=MD_NARRATIVE_MAX_LEN))
        )
        lines.append("")

    mc = result.get("mc")
    if mc:
        lines.append("## Simulation")
        lines.append("")
        lines.extend(_mc_section_lines(mc))
        lines.append("")

    lines.append("---")
    lines.append(
        "Data source: OKX copy-trading public order book, scored "
        "automatically by the norabt system."
    )
    iterations = mc.get("iterations") if isinstance(mc, dict) else None
    if iterations:
        lines.append(f"Simulated scenarios: {_fmt_int(iterations)}.")
    when = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines.append(f"Report generated at: {when}.")
    lines.append("")
    lines.append(f"*{REPORT_DISCLAIMER_VI}*")

    if detail_url:
        lines.append("")
        lines.append(detail_link_line(detail_url))

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The service
# --------------------------------------------------------------------------- #

# "Vài phút" per the task's own cache requirement -- long enough that mashing
# the same button twice costs nothing, short enough that a bot's live state
# (new trades, new positions) is never shown stale for long.
DEFAULT_ANALYZE_CACHE_TTL_SECONDS = 180.0
DEFAULT_LEADERBOARD_CACHE_TTL_SECONDS = 180.0
# Same "vài phút" reasoning as the two above, specifically so that typing a
# uniqueCode into the search box and then clicking "Phân tích bot này?"
# right after never re-pays lookup()'s own (already cheap) OKX calls -- see
# the task's own cache requirement 3.
DEFAULT_LOOKUP_CACHE_TTL_SECONDS = 180.0

# How many pages of OKX's lead-trader ranking to pull for the search-box
# suggestion list (LEADERBOARD_PAGE_SIZE traders each, see bot_source.py).
# 3 pages (~60 traders) is a small, fast, cheap-on-the-shared-OKX-budget
# slice of the full ~259-trader board -- enough to make the suggestion box
# useful without turning every cache-miss into the ~13-request full-board
# pass LiveBotDataSource's own internal leaderboard map pays once per
# process (see that class's _leaderboard_map docstring).
DEFAULT_LEADERBOARD_PAGES = 3

# Fixed venue/asset label used only to satisfy
# BotObservationService._find_bot_dir()'s on-disk directory check -- see
# WebDataService._analyze_full's docstring. Never read back for anything:
# LiveBotDataSource ignores bot_dir entirely, and the bot's real traded
# instrument is derived from its own ledger, not from this label.
_SCRATCH_ASSET = "LIVE_LOOKUP"
_SCRATCH_VENUE = "CEX"


# --------------------------------------------------------------------------- #
# Result-shape helpers for POST /api/lookup -- see WebDataService.lookup's own
# docstring for the endpoint's behaviour; these three functions are just the
# response contract, kept separate from the fetching logic for the same
# reason _not_found_result/_full_result are kept separate from analyze().
# --------------------------------------------------------------------------- #

LOOKUP_STATUS_OK = "OK"
LOOKUP_STATUS_LIMITED = "LIMITED"
LOOKUP_STATUS_NOT_FOUND = "NOT_FOUND"


def _profile_payload(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize one public-lead-traders-shaped row (from the on-disk
    snapshot) into /api/lookup's `profile` contract. `row=None` (bot absent
    from the snapshot -- dropped rank, too new, or LIMITED-with-no-fallback)
    still returns the full key set with every value None, so a dashboard
    never has to branch on whether `profile` itself is present.
    """
    row = row or {}
    return {
        "aum": _float(row.get("aum")),
        "pnl": _float(row.get("pnl")),
        "pnl_ratio": _float(row.get("pnlRatio")),
        "lead_days": _int(row.get("leadDays")),
        "rank": _int(row.get("rank")),
        "copy_traders": _int(row.get("copyTraderNum")),
    }


def _lookup_not_found_result(code: str, reason: str) -> Dict[str, Any]:
    return {
        "status": LOOKUP_STATUS_NOT_FOUND,
        "code": code,
        "name": None,
        "profile": _profile_payload(None),
        "assets": [],
        "closed_sample": 0,
        "open_total": 0,
        "note": (
            f"Bot with code {code!r} was not found on OKX. {reason}."
            f"{_agent_id_lookalike_hint_vi(code)}"
        ),
    }


def _lookup_limited_result(
    code: str, profile_row: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "status": LOOKUP_STATUS_LIMITED,
        "code": code,
        "name": (profile_row or {}).get("nickName") or code,
        "profile": _profile_payload(profile_row),
        "assets": [],
        "closed_sample": 0,
        "open_total": 0,
        "note": (
            "This bot does not disclose its order book on OKX (error 60004 "
            "on the positions/trade-history endpoint), so which asset it is "
            "trading cannot be seen -- only the general profile above (if "
            "found) is available."
        ),
    }


class WebDataService:
    """Backs every `/api/*` route: disk reads for the pre-scored dataset,
    live OKX calls (cached + rate-limited) for the leaderboard and for
    scoring an arbitrary bot on demand.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        *,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        client_factory: Callable[[], OkxClient] = OkxClient,
        bot_source_factory: Optional[
            Callable[[OkxClient, TokenBucket], BotDataSource]
        ] = None,
        market_source_factory: Optional[Callable[[OkxClient], MarketDataSource]] = None,
        analyze_cache_ttl: float = DEFAULT_ANALYZE_CACHE_TTL_SECONDS,
        leaderboard_cache_ttl: float = DEFAULT_LEADERBOARD_CACHE_TTL_SECONDS,
        leaderboard_pages: int = DEFAULT_LEADERBOARD_PAGES,
        lookup_cache_ttl: float = DEFAULT_LOOKUP_CACHE_TTL_SECONDS,
        # Injectable purely for tests (a fake `narrative.NarrativeBackend`,
        # so a test can assert on the generated result without ever
        # touching `NORABT_NARRATIVE_BACKEND`/spawning a real subprocess --
        # see Agent/none/test/test_narrative.py and the narrative-related tests
        # in Agent/none/test/test_web_app.py). `None` (the default) means
        # "resolve from the environment on every call" -- see
        # `narrative.select_backend_from_env`'s own docstring for why that
        # is read live rather than once here.
        narrative_backend: Optional["narrative.NarrativeBackend"] = None,
        clock: Callable[[], float] = time.monotonic,
        # Separate from `clock`: `clock` is a monotonic clock used only for
        # cache expiry bookkeeping (see _TTLCache), while this is wall-clock
        # epoch milliseconds used to compute "how many days ago did this
        # asset last close" -- injectable so a test can hit the
        # ASSET_ACTIVE_WINDOW_DAYS boundary (6.9 vs 7.1 days) exactly instead
        # of racing real wall-clock time.
        wall_clock_ms: Callable[[], int] = lambda: int(time.time() * 1000),
    ) -> None:
        self.data_dir = (
            Path(data_dir) if data_dir is not None else Path(config.DATA_DIR)
        )
        self.evaluation_mode = evaluation_mode
        # Shared across every OKX call this service makes -- ledger fetches
        # AND leaderboard paging alike -- because OKX's 5-req/2s cap on the
        # copytrading group is per source IP, not per object (see
        # Agent/backend/live/ratelimit.py's own docstring for the identical
        # reasoning behind the live poller's single shared bucket).
        self._rate_limiter = TokenBucket()
        # Built ONCE for the lifetime of this service, not per analyze()
        # call -- LiveBotDataSource lazily builds and caches a uniqueCode ->
        # lead-trader-ranking map the first time any bot needs its profile
        # (see that class's own `_leaderboard_map` docstring: ~13 requests to
        # page the whole board once, then free for every bot after). A fresh
        # LiveBotDataSource per call would pay that ~13-request cost on
        # every single `/api/analyze`, blowing well past the measured
        # "under 8s total" budget -- reusing one instance is what makes a
        # SECOND bot lookup actually land in the 1.5-5s range that budget
        # assumes. Overridable so tests can inject in-memory fakes instead
        # (still built once) -- see Agent/none/test/test_web_app.py.
        self._client = client_factory()
        bot_source_factory = bot_source_factory or (
            lambda client, bucket: LiveBotDataSource(client=client, rate_limiter=bucket)
        )
        market_source_factory = market_source_factory or (
            lambda client: LiveMarketDataSource(client=client)
        )
        self._bot_source = bot_source_factory(self._client, self._rate_limiter)
        self._market_source = market_source_factory(self._client)
        self._narrative_backend = narrative_backend
        self._analyze_cache = _TTLCache(analyze_cache_ttl, clock=clock)
        self._leaderboard_cache = _TTLCache(leaderboard_cache_ttl, clock=clock)
        self._leaderboard_pages = leaderboard_pages
        self._lookup_cache = _TTLCache(lookup_cache_ttl, clock=clock)
        self._wall_clock_ms = wall_clock_ms
        # Lazily parsed once per service instance -- see _profile_snapshot()'s
        # own docstring for why this file (not an OKX call) is what backs
        # /api/lookup's "hồ sơ" budget item.
        self._profile_snapshot_cache: Optional[Dict[str, Dict[str, Any]]] = None
        # One scratch directory for the lifetime of this service -- see
        # _analyze_full's docstring for exactly what it is for. An OS temp
        # dir, never under data_dir: CohortAssessmentService.scan() (run by
        # the batch report and the live poller) walks data_dir/<venue>/ on
        # disk, so anything created under the REAL data_dir here could later
        # get swept into an unrelated batch run. Cheap to leak for the life
        # of the process (each code adds one empty directory, nothing more);
        # cleaned up by the OS the normal way temp dirs are.
        self._scratch_dir = Path(mkdtemp(prefix="norabt_web_live_"))

    # -- GET /api/bots, GET /api/markets ------------------------------------

    def list_bots(self) -> List[Dict[str, Any]]:
        return list_scored_bots(self.data_dir)

    def list_bot_rows(self) -> List[Dict[str, Any]]:
        """The normalized `GET /api/bots` rows -- see `list_bot_listing_rows`'s
        own docstring for why this, and not `list_bots` above, is what that
        route actually serves.
        """
        return list_bot_listing_rows(self.data_dir)

    def list_markets(self) -> List[Dict[str, Any]]:
        return list_markets(self.data_dir)

    # -- GET /bot/<code>, GET /<userref>_<code> (no re-analysis) -------------

    def find_scored_report(self, code: str) -> Optional[Tuple[Dict[str, Any], int]]:
        """`(result, generated_at_ms)` reshaped from this bot's already-scored
        `assessment.json`, or `None` when `code` has never been through
        `run_report.py` -- see `assessment_to_analyze_result`'s own module
        docstring for the full contract. `app.py`'s `_bot_report_response`
        uses this to skip `analyze()` -- and the ~70s live pipeline it runs
        -- entirely for a bot that has already been scored, which is this
        task's own fix for `GET /bot/<code>` timing out behind nginx.
        """
        doc = find_assessment_document(self.data_dir, code)
        if doc is None:
            return None
        generated_at_ms = assessment_generated_at_ms(doc)
        if generated_at_ms is None:
            return None
        bot = doc.get("bot") if isinstance(doc.get("bot"), dict) else {}
        code_clean = bot.get("unique_code") or code
        sym = bot.get("traded_symbol") or bot.get("asset_context")
        market_doc = find_bot_market_document(self.data_dir, code_clean, sym)
        result = assessment_to_analyze_result(
            doc,
            analysis_doc=sibling_analysis_documents(self.data_dir, code),
            market_doc=market_doc,
        )
        if result is None:
            return None
        return result, generated_at_ms

    # -- GET /api/leaderboard ------------------------------------------------

    def leaderboard(self) -> List[Dict[str, Any]]:
        cached = self._leaderboard_cache.get("all")
        if cached is not None:
            return cached
        rows: List[Dict[str, Any]] = []
        for page in range(1, self._leaderboard_pages + 1):
            self._rate_limiter.acquire()
            try:
                data = self._client.public_get(
                    LEAD_TRADERS_PATH,
                    {
                        "instType": "SWAP",
                        "limit": LEADERBOARD_PAGE_SIZE,
                        "page": page,
                    },
                )
            except OkxError:
                # A failure on page 1 means no leaderboard at all this
                # round -- let the caller see it and decide how to report
                # it. A failure on a later page still leaves an earlier,
                # real partial list, which is still useful for
                # autocomplete, so it is kept rather than discarded.
                if page == 1:
                    raise
                break
            if not isinstance(data, list) or not data:
                break
            block = data[0]
            block_rows = block.get("ranks") if isinstance(block, dict) else None
            if not isinstance(block_rows, list) or not block_rows:
                break
            rows.extend(
                {
                    "unique_code": row.get("uniqueCode"),
                    "nick_name": row.get("nickName"),
                    "aum": row.get("aum"),
                    "pnl_ratio": row.get("pnlRatio"),
                    "lead_days": row.get("leadDays"),
                }
                for row in block_rows
                if isinstance(row, dict) and row.get("uniqueCode")
            )
        self._leaderboard_cache.set("all", rows)
        return rows

    # -- POST /api/lookup ------------------------------------------------------

    def _profile_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """The already-crawled lead-trader ranking snapshot on disk
        (`<data_dir>/universe/lead_traders.json`, the same file
        Agent/none/scripts/crawl_bots.py and Agent/none/scripts/backfill_bot_profiles.py
        already read/write) -- this is the "cache bảng xếp hạng đã có" the
        task's /api/lookup budget assumes for profile data. Reading it costs
        one local JSON parse, never an OKX request, which is what keeps
        profile lookup free relative to the 3-OKX-request ceiling `lookup()`
        is held to (see that method's own docstring).

        Lazily parsed once per WebDataService instance -- the file is easily
        a megabyte for the ~259-trader board this project has observed, and
        every /api/lookup call after the first reuses this dict instead of
        re-reading/re-parsing it. A missing or corrupt file degrades to an
        empty map (profile enrichment just comes back None, exactly like a
        bot that dropped off the ranking -- see
        LiveBotDataSource._profile_provenance's identical reasoning) rather
        than raising: a stale/absent snapshot must never break lookup().
        """
        if self._profile_snapshot_cache is None:
            path = self.data_dir / "universe" / "lead_traders.json"
            rows: List[Dict[str, Any]] = []
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    rows = [row for row in payload if isinstance(row, dict)]
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                rows = []
            self._profile_snapshot_cache = {
                row["uniqueCode"]: row for row in rows if row.get("uniqueCode")
            }
        return self._profile_snapshot_cache

    def lookup(self, raw_code: Any) -> Dict[str, Any]:
        """POST /api/lookup: identify a uniqueCode and its per-asset trading
        state WITHOUT running the scoring engine -- the cheap first step of
        the task's two-step flow (type a code -> lookup() -> user clicks
        "Phân tích bot này?" -> only then analyze()).

        Costs at most 3 OKX requests for the bot itself (see
        _lookup_live/_lookup_blocked_result for exactly when each is spent):
        one page of closed-order history, the current open positions, and --
        ONLY when neither the on-disk ranking snapshot nor those two calls
        identify the bot -- one public-stats probe. Profile data costs
        nothing when the on-disk snapshot already has it (see
        _profile_snapshot); when it does NOT (a bot that joined the ranking
        after the last crawl -- see _profile_from_leaderboard for the real
        case this fixes), ONE leaderboard load
        (DEFAULT_LEADERBOARD_PAGES = 3 requests) is spent on top, so a
        successful lookup with a cold leaderboard cache costs 5 in total.
        That load is TTL-cached and shared by every later lookup inside the
        window; a NOT_FOUND lookup never triggers it at all. Same
        input validation and TTL-cache shape as analyze() (see
        validate_unique_code/_TTLCache), just far cheaper per call.
        """
        code = validate_unique_code(raw_code)
        cached = self._lookup_cache.get(code)
        if cached is not None:
            return cached
        result = self._lookup_live(code)
        self._lookup_cache.set(code, result)
        return result

    def _profile_for_result(
        self, code: str, snapshot_row: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Hồ sơ cuối cùng gắn vào MỘT kết quả tra cứu thật (OK hoặc
        LIMITED): ảnh chụp trên đĩa trước, thiếu thì mới tới bảng xếp hạng
        sống.

        Gọi ở ĐÂY chứ không phải đầu `_lookup_live` là có chủ đích: một mã
        rác kết thúc ở NOT_FOUND không bao giờ chạm tới nhánh này, nên nó
        vẫn tốn đúng 3 request như trước (vị thế -> lịch sử -> public-stats)
        và không ai có thể ép máy chủ nạp bảng xếp hạng bằng một mã bịa.

        CHI PHÍ THẬT khi có chạm: `leaderboard()` nạp
        `DEFAULT_LEADERBOARD_PAGES` (3) trang, nên một lượt tra cứu THÀNH
        CÔNG với cache bảng xếp hạng đang nguội tốn 2 + 3 = 5 request chứ
        không phải 3. Đây là con số đã đo bằng test, không phải ước lượng.
        Chấp nhận được vì: chỉ xảy ra khi ảnh chụp trên đĩa trượt, kết quả
        nạp được cache theo TTL nên mọi lượt tra cứu sau trong cửa sổ đó
        dùng chung (0 request), và bản thân kết quả tra cứu từng mã cũng
        được `_lookup_cache` giữ lại.
        """
        if snapshot_row is not None:
            return snapshot_row
        return self._profile_from_leaderboard(code)

    def _profile_from_leaderboard(self, code: str) -> Optional[Dict[str, Any]]:
        """Hồ sơ lấy từ BẢNG XẾP HẠNG SỐNG (đã cache theo TTL), dùng khi ảnh
        chụp trên đĩa không có mã này.

        VÌ SAO CẦN: `_profile_snapshot()` đọc `universe/lead_traders.json`
        -- một file TĨNH do lượt crawl gần nhất ghi ra. Bot mới lên bảng xếp
        hạng sau lượt crawl đó đơn giản là KHÔNG có trong file (đo thật:
        file 259 dòng, crawl 13/09; bot `807517291536749293` có trên bảng
        xếp hạng hiện tại nhưng không có trong file). Hệ quả người dùng thấy
        được: bấm "Tìm bot" ra một thẻ tóm tắt rỗng trơn -- tên bot hiển thị
        chính là dãy mã, AUM/PnL/hạng/số người copy đều `—` -- trong khi
        chính trang này có sẵn `GET /api/leaderboard` biết thừa tên bot đó.

        CHI PHÍ: chỉ chạm tới khi ảnh chụp trên đĩa TRƯỢT, và `leaderboard()`
        tự cache theo TTL nên nhiều lượt tra cứu liên tiếp chia nhau đúng
        một lần nạp (tối đa `DEFAULT_LEADERBOARD_PAGES` = 3 request OKX khi
        cache nguội). Lỗi mạng/OKX ở đây KHÔNG được phép làm hỏng lượt tra
        cứu: nuốt lỗi và trả `None`, đúng như khi bot rớt khỏi bảng xếp hạng.

        Bảng xếp hạng chỉ mang 4 trường (`nick_name`/`aum`/`pnl_ratio`/
        `lead_days`), KHÔNG có `pnl`/`rank`/`copyTraderNum` -- ba trường đó
        vẫn để trống thay vì suy ra từ vị trí trong danh sách: danh sách này
        có thể là bản KHUYẾT (xem `leaderboard()`: trang lỗi giữa chừng vẫn
        giữ phần đã lấy được), nên thứ tự trong đó không chắc là thứ hạng
        thật.
        """
        try:
            rows = self.leaderboard()
        except Exception:  # noqa: BLE001 - xem docstring: không bao giờ phá lookup
            return None
        for row in rows:
            if isinstance(row, dict) and row.get("unique_code") == code:
                return {
                    "nickName": row.get("nick_name"),
                    "aum": row.get("aum"),
                    "pnlRatio": row.get("pnl_ratio"),
                    "leadDays": row.get("lead_days"),
                }
        return None

    def _lookup_live(self, code: str) -> Dict[str, Any]:
        # CHỈ ảnh chụp trên đĩa ở đây (miễn phí). Bổ sung từ bảng xếp hạng
        # sống được hoãn tới ĐÚNG nhánh sắp trả kết quả thật, để một mã rác
        # (kết thúc ở NOT_FOUND) không tiêu thêm request nào -- xem
        # `_profile_for_result`.
        profile_row = self._profile_snapshot().get(code)

        # Positions first, exactly like LiveBotDataSource.get_ledger's own
        # call order (see bot_source.py) -- OKX answers 60004 on both
        # endpoints together for a ledger-hidden bot, so a block on this
        # first call means history would only spend a second request to
        # learn the same thing.
        positions, positions_blocked = self._lookup_fetch(POSITIONS_PATH, code)
        if positions_blocked:
            return self._lookup_blocked_result(code, profile_row)

        history, history_blocked = self._lookup_fetch(
            HISTORY_PATH, code, extra_params={"limit": PAGE_SIZE}
        )
        if history_blocked:
            return self._lookup_blocked_result(code, profile_row)

        if positions is None or history is None:
            # A non-60004 OKX failure (transport error, malformed body, ...)
            # on either call. From this endpoint's perspective that is
            # indistinguishable from a bad uniqueCode, so it folds into
            # NOT_FOUND rather than a 500 -- exactly how /api/analyze's own
            # BotSourceError handling already treats the same ambiguity (see
            # _analyze_live).
            return _lookup_not_found_result(
                code, "OKX could not return order-book data for this code right now"
            )

        if not positions and not history:
            # Mirrors LiveBotDataSource.get_ledger's own fail-closed guard: a
            # uniqueCode that is OKX-listed at all must have traded SOMETHING
            # to be listed, so an all-empty response here is far more likely
            # a wrong/garbage code than a genuinely untraded bot.
            return _lookup_not_found_result(
                code,
                "OKX returned a completely empty order book for this code "
                "(0 open positions, 0 closed trades)",
            )

        now_ms = self._wall_clock_ms()
        open_symbols = [_base_symbol(p.get("instId")) for p in positions]
        closed_records = [
            (_base_symbol(t.get("instId")), _int(t.get("closeTime"))) for t in history
        ]
        assets = _build_asset_states(open_symbols, closed_records, now_ms)
        profile_row = self._profile_for_result(code, profile_row)
        return {
            "status": LOOKUP_STATUS_OK,
            "code": code,
            "name": (profile_row or {}).get("nickName") or code,
            "profile": _profile_payload(profile_row),
            "assets": assets,
            "closed_sample": len(history),
            "open_total": len(positions),
            "note": _holding_assets_note(assets),
        }

    def _lookup_blocked_result(
        self, code: str, profile_row: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """OKX answered 60004 on the ledger for `code` -- a bot that hides
        its order book, or a code that does not exist at all (see
        TRADER_NOT_EXIST_CODE in bot_source.py for the same ambiguity that
        module's own LedgerUnavailableError resolves for /api/analyze).

        Told apart here WITHOUT re-paging the full ~259-trader board the way
        LiveBotDataSource._classify_blocked_ledger does (that alone can cost
        up to ~13 OKX requests -- far past this endpoint's 3-request
        ceiling): the on-disk ranking snapshot already answers "is this a
        real, previously-seen lead trader" for free, and public-stats is the
        one remaining endpoint in this group confirmed to actually respect a
        `uniqueCode` filter (see STATS_PATH's own docstring), so it is the
        correct single extra request to spend here instead.
        """
        # KHÔNG bổ sung từ bảng xếp hạng sống ở nhánh này (khác nhánh OK):
        # ở đây vẫn còn phải tiêu một request public-stats để phân biệt "bot
        # thật đang giấu sổ lệnh" với "mã sai", nên thêm một lần nạp bảng
        # xếp hạng nữa sẽ đẩy kịch bản tệ nhất lên 4 request, vượt trần 3 mà
        # `lookup()` cam kết. Đánh đổi: một bot giấu sổ lệnh VÀ mới lên bảng
        # xếp hạng sau lượt crawl gần nhất vẫn hiện tên bằng chính dãy mã --
        # chấp nhận được vì thẻ tóm tắt của nhánh này đã có sẵn một câu giải
        # thích rõ vì sao gần như không có số liệu nào.
        if profile_row is not None:
            return _lookup_limited_result(code, profile_row)
        stats_row = self._lookup_fetch_stats(code)
        if stats_row is not None:
            return _lookup_limited_result(code, None)
        return _lookup_not_found_result(
            code,
            f"Code {code} was not found in the saved lead-trader leaderboard "
            "or OKX public-stats -- this is likely a wrong uniqueCode",
        )

    def _lookup_fetch(
        self,
        path: str,
        code: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
        """One rate-limited OKX call for lookup()'s cheap probe.

        Returns `(rows, blocked)`. `blocked=True` means OKX answered
        TRADER_NOT_EXIST_CODE specifically -- a real bot hiding its order
        book, not a fetch failure (`rows` is meaningless in that case). Any
        OTHER failure (transport error, a different API error code, a
        malformed non-list body) comes back as `(None, False)` -- see
        _lookup_live's own docstring for why that folds into NOT_FOUND
        rather than raising.
        """
        params: Dict[str, Any] = {"uniqueCode": code, "instType": "SWAP"}
        if extra_params:
            params.update(extra_params)
        self._rate_limiter.acquire()
        try:
            data = self._client.public_get(path, params)
        except OkxApiError as exc:
            if exc.code == TRADER_NOT_EXIST_CODE:
                return None, True
            return None, False
        except OkxError:
            return None, False
        if not isinstance(data, list):
            return None, False
        # Drop any record carrying a different uniqueCode -- mirrors
        # LiveBotDataSource._owned_by's identical guard against OKX
        # occasionally handing back a neighbouring trader's row.
        owned = [
            row
            for row in data
            if isinstance(row, dict) and row.get("uniqueCode") in (None, "", code)
        ]
        return owned, False

    def _lookup_fetch_stats(self, code: str) -> Optional[Dict[str, Any]]:
        """Best-effort, single-request existence probe -- see
        _lookup_blocked_result's docstring for why public-stats specifically.
        A failure here just means "no evidence from this endpoint", exactly
        like LiveBotDataSource._fetch_public_stats's identical reasoning.
        """
        self._rate_limiter.acquire()
        try:
            data = self._client.public_get(
                STATS_PATH,
                {"uniqueCode": code, "instType": "SWAP", "lastDays": STATS_LAST_DAYS},
            )
        except OkxError:
            return None
        if not isinstance(data, list) or not data:
            return None
        row = data[0]
        return row if isinstance(row, dict) else None

    # -- POST /api/analyze ----------------------------------------------------

    def analyze(
        self,
        raw_code: Any,
        force: bool = False,
        progress: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Score `raw_code`, or replay the cached score from the last
        `analyze_cache_ttl` seconds.

        `force=True` (the "Phân tích lại" button's `?refresh=1`, see
        `app.py`'s `bot_report`) skips the READ from `self._analyze_cache`
        below so a fresh `_analyze_live` call always runs, but the fresh
        result is still WRITTEN into that same cache afterward -- so the
        very next view (by this caller or anyone else) is cheap again,
        rather than every subsequent request re-running the pipeline until
        the TTL happens to expire on its own. Before this parameter existed,
        `?refresh=1` only bypassed the Redis snapshot one layer up (see
        `Agent/backend/web/snapshot.py`), never this in-process cache, so a
        second click inside the TTL window silently replayed the exact same
        cached dict -- the reported bug this fixes.

        `progress` (plan_progress.md mục A/B): optional real-stage callback,
        threaded straight down into `RiskSupervisionPipeline.run()` (via
        `_analyze_live`/`_analyze_full`) when this call actually has to run
        the live pipeline -- `app.py` wires it to
        `Agent/backend/web/progress.py`'s registry so `GET
        /api/analyze/status` can report real stages, never a fake clock.
        `None` by default, and NEVER called at all on a cache hit above (a
        cache hit has no stages left to report -- the caller already knows
        the whole thing finished the moment `analyze()` returns).
        """
        code = validate_unique_code(raw_code)
        if not force:
            cached = self._analyze_cache.get(code)
            if cached is not None:
                return cached
        result = self._analyze_live(code, progress=progress)
        # Added on top of every status (FULL/LIMITED/NOT_FOUND alike, and
        # regardless of whether Agent/backend/analysis/limited.py produced
        # the LIMITED payload or the in-module fallback did) -- see
        # build_report_markdown/build_report_url's own docstrings. Attached
        # here, once, before caching: a cache hit within the TTL window then
        # replays byte-for-byte the same report (including its
        # "generated_at" line) the original call produced, exactly like
        # every other field in this dict already does on a cache hit (see
        # test_analyze_caches_result_so_source_is_called_once).
        result["report_markdown"] = build_report_markdown(result)
        # `report_url` is included ONLY when `report_base_url()` is something
        # an outside caller could actually reach -- see
        # `report_url_is_usable`/`_is_public_report_host`'s own comments for
        # why. In short: this endpoint is called by OTHER agents on the OKX
        # AI Marketplace, running on OTHER people's machines, so a loopback
        # or private-network default (e.g. unset -> "http://127.0.0.1:8770")
        # would hand them a URL that resolves on THEIR OWN box, not this
        # one -- a wrong link, not merely an absent one, and more misleading
        # than no link at all. The key is left OUT of the dict entirely
        # (never set to "" or None) so a caller's most natural check,
        # `"report_url" in result`, is exactly correct: no extra "is it
        # empty/null" branch to remember, and no dead link to render either.
        if report_url_is_usable():
            result["report_url"] = build_report_url(code)
        # Deliberately NOT where the optional access-token-gated "detail"
        # link (build_report_markdown's `detail_url` param / the
        # `text`-array line, see app.py's `_with_detail_link`) gets added --
        # this cached dict has no access to, and no business knowing, which
        # token (if any) authenticated the CURRENT caller, and it is shared
        # byte-for-byte across every caller who hits the cache for the same
        # `code` within the TTL window below. app.py adds that line, fresh,
        # on a per-request COPY of whatever this method returns, precisely
        # so this cache never has to be aware tokens exist at all (see this
        # module's own docstring / the task's "core logic không dùng token"
        # requirement).
        self._analyze_cache.set(code, result)
        return result

    def _analyze_live(
        self, code: str, *, progress: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        try:
            return self._analyze_full(code, progress=progress)
        except LedgerUnavailableError as exc:
            # OKX answered 60004 on the ledger endpoints -- LedgerUnavailableError
            # already classified this into LIMITED (a real, opaque bot) or
            # NOT_FOUND (no endpoint knows this code at all), see that
            # class's own docstring. That classification does NOT depend on
            # Agent/backend/analysis/limited.py; only the detailed scoring
            # for the LIMITED case does (see _handle_ledger_unavailable).
            return self._handle_ledger_unavailable(exc)
        except BotSourceError as exc:
            # Anything else BotSourceError raises for -- the fail-closed
            # "sổ lệnh trống hoàn toàn" guard, a transport error, a
            # malformed OKX response -- is treated the same way: this
            # process could not observe the bot, which is exactly what
            # NOT_FOUND means in this contract (see the top-level docstring
            # for why NOT_FOUND/LIMITED are valid results, not HTTP errors).
            return _not_found_result(code, str(exc))
        except (MarketDataUnavailableError, ValueError) as exc:
            # RiskSupervisionPipeline.resolve_market() already swallows
            # MarketDataUnavailableError/ValueError internally (see
            # pipeline.py) -- reachable here only if BotObservationService's
            # own asset/venue validation ever rejected the fixed
            # "_SCRATCH_ASSET"/"_SCRATCH_VENUE" arguments this module always
            # passes, which never happens. Kept as a second line of defence
            # per the module's fail-closed-JSON contract, not dead code.
            return _not_found_result(code, str(exc))

    def _analyze_full(
        self, code: str, *, progress: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Score a bot that may never have been crawled, by reusing the exact
        LiveBotDataSource + RiskSupervisionPipeline wiring
        `run_report.py --source live` and `agent_server.py`'s `assess_bot`
        tool already use (see both for the pattern this mirrors).

        The one thing neither of those callers had to solve:
        `BotObservationService.get_bot_result()` insists a real directory
        exist on disk at `<data_dir>/<venue>/<asset>/bot/<folder>` before it
        will even ask its bot_source for anything (see `_find_bot_dir` in
        `Agent/backend/mcp/service.py`, off-limits here) -- true even when
        that source is a LiveBotDataSource that never reads the directory's
        *contents*. Every existing caller only ever asks about bots that
        were already crawled once, so that directory already exists for
        them; a code typed into this dashboard was very possibly never
        crawled at all.

        The fix is to give BotObservationService a `data_dir` of its own --
        `self._scratch_dir`, a private OS temp directory, never the real
        dataset -- and create just the one empty leaf directory
        `<scratch>/cex/LIVE_LOOKUP/bot/bot_<code>` that satisfies
        `_find_bot_dir`'s existence check. LiveBotDataSource never reads that
        directory's contents (it fetches straight from OKX by uniqueCode),
        so the directory being otherwise empty is fine. Crucially, this
        scratch data_dir is used ONLY for the bot side: `market_service` and
        the pipeline's own `data_dir` (used for `UniverseRegistry` eligibility
        checks) both still point at the real `self.data_dir`, since neither
        of those has an equivalent on-disk-existence gate to work around.

        One more thing the scratch directory must NOT be used for:
        `BotObservationService._phase_timelines` reads read-only reference
        candle series (`<venue>/<symbol>/market/ohlcv_1h_*.json`,
        `phases/<symbol>.json`) to label which market phase each of the
        bot's own trades happened in. Those files live under the real
        dataset, never under this empty scratch directory -- pointing that
        lookup at `self._scratch_dir` silently starved every phase label
        (every trade resolved to `MarketPhase.UNKNOWN`), which is exactly
        why phase coverage/breakdown came back 0%/empty for every bot
        analyzed through this live path, even though the very same bot's
        phase coverage computes correctly when read straight off disk.
        `reference_data_dir=self.data_dir` below keeps that read-only lookup
        on the real dataset while `data_dir` itself stays the isolated
        scratch directory for the bot's own read/write side.

        `progress`, when given, is threaded straight into
        `RiskSupervisionPipeline.run()` (its own 4 real stages -- "ledger",
        "markets", "scoring", "decision", see pipeline.py) and then called
        twice more here, after `run()` returns: "narrative" right before
        `_full_result()` kicks off the (already-backgrounded, see
        `_start_background_narrative`) narrative step, and "done" right
        before this method returns -- the 5th and last of the 5 stages this
        task's progress bar reports (plan_progress.md mục A).
        """
        bot_dir = (
            self._scratch_dir
            / _SCRATCH_VENUE.lower()
            / _SCRATCH_ASSET
            / "bot"
            / f"bot_{code}"
        )
        bot_dir.mkdir(parents=True, exist_ok=True)
        bot_service = BotObservationService(
            self._scratch_dir,
            self.evaluation_mode,
            bot_source=self._bot_source,
            reference_data_dir=self.data_dir,
        )
        market_service = MarketService(
            self.data_dir,
            self.evaluation_mode,
            market_source=self._market_source,
        )
        pipeline = RiskSupervisionPipeline(
            data_dir=self.data_dir,
            market_service=market_service,
            bot_service=bot_service,
            evaluation_mode=self.evaluation_mode,
            # A dashboard lookup of an arbitrary code is exploratory, exactly
            # like agent_server.py's assess_bot tool -- it must never feed
            # the real risk-trend history a batch report reads on its next
            # run (same reasoning as that tool's own persist_history=False).
            persist_history=False,
        )
        result = pipeline.run(
            _SCRATCH_ASSET,
            f"bot_{code}",
            venue_type=_SCRATCH_VENUE,
            progress=progress,
        )
        if progress is not None:
            progress("narrative")
        payload = _full_result(code, result, narrative_backend=self._narrative_backend)
        if progress is not None:
            progress("done")
        return payload

    def _handle_ledger_unavailable(self, exc: LedgerUnavailableError) -> Dict[str, Any]:
        """Turn a `LedgerUnavailableError` into the final `/api/analyze`
        response.

        `exc.status` (LIMITED or NOT_FOUND) is already the right answer --
        `LiveBotDataSource._classify_blocked_ledger` decided it by checking
        whether the leaderboard/stats/weekly endpoints still know this code,
        which has nothing to do with `Agent/backend/analysis/limited.py`.
        That module only adds the DETAILED scoring/text for the LIMITED
        case (a full risk/quality/confidence assessment built from whatever
        survives 60004); its absence -- or a failure inside it -- degrades
        to a plain but still correctly-classified fallback, never to a crash
        or to the wrong status.
        """
        code = exc.code
        if assess_from_error is None:
            return self._ledger_unavailable_fallback(
                exc,
                "The reduced-scoring module (Agent/backend/analysis/limited.py) "
                "is not ready in this version of the service, so a more "
                "detailed LIMITED result cannot be returned for this bot yet.",
            )
        try:
            # `data_dir`: quần thể bot đã chấm nằm trên đĩa, là cơ sở để
            # chấm điểm bằng HẠNG PHÂN VỊ thay vì ngưỡng tự đặt (xem
            # `Agent/backend/analysis/population_reference.py`). Không
            # truyền thì module kia tự rơi về nhánh "chưa đủ quần thể".
            payload = assess_from_error(exc, data_dir=self.data_dir)
        except Exception as inner:  # noqa: BLE001 - a sibling module must
            # never be able to crash this endpoint; see the soft-import
            # block's docstring.
            return self._ledger_unavailable_fallback(
                exc,
                f"The reduced-scoring module reported an error while "
                f"processing code {code!r}: {inner}",
            )
        if not isinstance(payload, dict) or payload.get("status") not in (
            "FULL",
            "LIMITED",
            "NOT_FOUND",
        ):
            return self._ledger_unavailable_fallback(
                exc,
                "The reduced-scoring module returned data that does not "
                "match the /api/analyze contract shape.",
            )
        # Agent/backend/analysis/limited.py is off-limits here and owned by a
        # parallel task -- it predates this task's `assets` field and has no
        # reason to know about it. A LIMITED/NOT_FOUND bot has no visible
        # ledger by definition (that is what LedgerUnavailableError means),
        # so "no known assets" is the only honest value regardless; this
        # just guarantees the key exists rather than silently omitting it.
        payload.setdefault("assets", [])
        # Same reasoning as `assets` immediately above, for the narrative
        # feature (see `_empty_result`'s own comment): a LIMITED/NOT_FOUND
        # bot never has the FULL scored-numbers set a narrative is built
        # from, and `Agent/backend/analysis/limited.py` predates this
        # field entirely, so this only guarantees the key is present.
        payload.setdefault("narrative", None)
        return payload

    @staticmethod
    def _ledger_unavailable_fallback(
        exc: LedgerUnavailableError, detail: str
    ) -> Dict[str, Any]:
        """Fallback used whenever assess_from_error is missing, raises, or
        returns something malformed -- still correctly LIMITED vs NOT_FOUND
        from `exc.status` alone (see _handle_ledger_unavailable's docstring).
        """
        if exc.status == _SOURCE_NOT_FOUND:
            return _not_found_result(exc.code, str(exc))
        return _limited_fallback_result(exc.code, detail)
