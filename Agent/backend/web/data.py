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
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.live.ratelimit import TokenBucket
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.mcp.service import BotObservationService
from Agent.backend.okx.client import OkxApiError, OkxClient, OkxError
from Agent.backend.pipeline import RiskSupervisionPipeline
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
# Agent/backend/analysis/limited.py and Agent/test/test_limited_assessment.py):
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
        raise InvalidCodeError("Thiếu trường 'code' dạng chuỗi trong body JSON")
    code = raw.strip()
    if not code:
        raise InvalidCodeError("Mã bot (uniqueCode) không được để trống")
    if not _CODE_RE.match(code):
        raise InvalidCodeError(
            "Mã bot không hợp lệ: chỉ chấp nhận chữ và số (mã OKX là hex hoặc "
            "số), tối đa 64 ký tự -- từ chối để chặn ký tự lạ/path traversal"
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

ASSET_STATE_TRADING = "ĐANG GIAO DỊCH"
ASSET_STATE_HOLDING = "CHỈ ĐANG ÔM"
ASSET_STATE_LEFT = "ĐÃ RỜI"

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
        f"Cảnh báo: {', '.join(holding)} đang ở trạng thái CHỈ ĐANG ÔM (còn vị "
        f"thế mở nhưng quá {window} ngày không chốt lệnh nào) -- bản thân "
        "trạng thái này là một tín hiệu rủi ro, thường gặp ở mẫu ôm lỗ chờ gỡ."
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
    """
    return _read_json_documents(Path(data_dir) / "assessment", "**/assessment.json")


def list_markets(data_dir: Path) -> List[Dict[str, Any]]:
    """The assets step 2 already analysed: one market.json per asset
    (data/analysis/<venue>/<asset>/market/market.json).
    """
    return _read_json_documents(Path(data_dir) / "analysis", "**/market/market.json")


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
    " Lưu ý: mã toàn chữ số và ngắn (1-8 ký tự) như thế này nhiều khả năng "
    "là Agent ID trên chợ OKX AI Marketplace (ví dụ '13753'), KHÔNG PHẢI "
    "uniqueCode của bot copy-trading OKX -- uniqueCode thường là chuỗi hex "
    "hoặc một dãy số DÀI hơn nhiều, ví dụ 'EF1CC6F40E834D1A'. Nếu bạn muốn "
    "phân tích một bot copy-trading, hãy nhập đúng uniqueCode của bot đó."
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
            f"Không tìm thấy bot với mã {code!r} trên OKX, hoặc OKX tạm thời "
            f"không trả lời được cho mã này. Chi tiết: {reason}"
            f"{_agent_id_lookalike_hint_vi(code)}"
        ],
    )


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
            "Bot này không công khai sổ lệnh trên OKX nên không thể chấm điểm "
            "đầy đủ (FULL).",
            detail,
        ],
    )
    result["limited_reason"] = "OKX không công khai sổ lệnh của bot này (lỗi 60004)"
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
        f"{bot.identity.nick_name} ({code}) — giao dịch {result.traded_symbol}, "
        f"{perf.trade_count} lệnh đã chốt, tỉ lệ thắng {perf.win_rate:.0f}%.",
    ]
    if assessment.quality_score is not None:
        lines.append(
            f"Điểm rủi ro {assessment.risk_score:.1f}/100, điểm chất lượng "
            f"{assessment.quality_score:.1f}/100, độ tin cậy "
            f"{assessment.confidence:.0f}/100."
        )
    else:
        lines.append(
            f"Điểm rủi ro {assessment.risk_score:.1f}/100 (chưa đủ bằng chứng "
            "để tính điểm chất lượng)."
        )
    reason = f"Kết luận: {assessment.verdict}"
    if assessment.verdict_reason:
        reason += f" — {assessment.verdict_reason}"
    lines.append(reason)
    if not result.market_available:
        lines.append(
            f"Chưa có dữ liệu thị trường cho {result.traded_symbol}; các chiều rủi "
            "ro phụ thuộc thị trường được để UNKNOWN thay vì đoán."
        )
    if assessment.hidden_risk_flags:
        lines.append("Cảnh báo ẩn: " + "; ".join(assessment.hidden_risk_flags))
    if assessment.limitations:
        lines.append("Giới hạn dữ liệu: " + "; ".join(assessment.limitations))
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


def _full_result(code: str, result: Any) -> Dict[str, Any]:
    assessment = result.risk_assessment
    bot = result.bot_result
    return {
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
            "performance": bot.performance.model_dump(mode="json"),
            "current_state": bot.current_state.model_dump(mode="json"),
            "reconciliation": bot.reconciliation.model_dump(mode="json"),
            "data_quality": bot.data_quality.model_dump(mode="json"),
            "dimensions": assessment.dimensions.model_dump(mode="json"),
            "score_breakdown": assessment.score_breakdown.model_dump(mode="json"),
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
        },
        "mc": bot.simulation_results.model_dump(mode="json"),
        # See _asset_states_from_bot_result's own docstring, including the
        # TODO on why this deliberately stops short of live market context.
        "assets": _asset_states_from_bot_result(bot),
        "text": _explanation_vi(code, result),
    }


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
    "deferred_loss": "Phân tích lỗ trì hoãn (deferred loss)",
    "phase_analysis": "Phân tích theo pha thị trường",
    "monte_carlo": "Mô phỏng Monte Carlo",
    "psr_dsr": "PSR / DSR (độ tin cậy thống kê)",
    "market_context": "Bối cảnh thị trường (giá, thanh khoản, order-flow)",
    "drawdown_pct": "% sụt vốn chính xác theo từng lệnh",
    "win_ratio": "Tỉ lệ thắng chính xác theo từng lệnh",
    "profile": "Hồ sơ trên bảng xếp hạng lead trader",
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
        return ["Không có dữ liệu mô phỏng Monte Carlo cho bot này."]
    lines: List[str] = []
    iterations = mc.get("iterations")
    horizon = mc.get("horizon_trades")
    if iterations:
        line = f"Số kịch bản mô phỏng: {_fmt_int(iterations)}"
        if horizon:
            line += f", chân trời {_fmt_int(horizon)} lệnh"
        lines.append(line)
    p05, p50, p95 = (
        mc.get("profit_pct_p05"),
        mc.get("profit_pct_p50"),
        mc.get("profit_pct_p95"),
    )
    if p05 is not None or p50 is not None or p95 is not None:
        lines.append(
            "Phân vị lợi nhuận mô phỏng (P05 / P50 / P95): "
            f"{_fmt_pct(p05)} / {_fmt_pct(p50)} / {_fmt_pct(p95)}"
        )
    if mc.get("p_ruin") is not None:
        lines.append(f"Xác suất cháy vốn (p_ruin): {_fmt_pct(mc.get('p_ruin'))}")
    if mc.get("probability_of_profit") is not None:
        lines.append(f"Xác suất có lãi: {_fmt_pct(mc.get('probability_of_profit'))}")
    if mc.get("median_max_drawdown") is not None:
        lines.append(
            f"Sụt vốn trung vị theo mô phỏng: {_fmt_pct(mc.get('median_max_drawdown'))}"
        )
    if mc.get("is_valid") is False:
        lines.append(
            "Lưu ý: mô phỏng được đánh dấu is_valid=False (mẫu dữ liệu đầu vào "
            "chưa đủ lớn để tin cậy)."
        )
    return lines or ["Có chạy mô phỏng nhưng không đủ trường số liệu để tóm tắt."]


REPORT_DISCLAIMER_VI = (
    "Đây là đánh giá rủi ro tự động dựa trên dữ liệu công khai của OKX, KHÔNG "
    "PHẢI lời khuyên đầu tư. Người đọc tự chịu trách nhiệm với quyết định của "
    "mình."
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
    "Xem chi tiết trực quan (biểu đồ, thông số đầy đủ, sở cứ từng mục)"
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
    key set). Every free-text field pulled from it that can trace back to
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
        f"**Xếp loại: {verdict} · Điểm rủi ro: {risk} · Điểm chất lượng: "
        f"{quality} · Độ tin cậy: {confidence}**"
    )
    lines.append("")

    if status == "LIMITED":
        lines.append(
            "> ⚠️ **LIMITED** — bot này KHÔNG công khai sổ lệnh trên OKX, "
            "nên đây là đánh giá RÚT GỌN, không phải chấm điểm FULL."
        )
        reason = _md_escape(result.get("limited_reason"), max_len=300)
        if reason:
            lines.append(f"> {reason}")
        lines.append("")
    elif status == "NOT_FOUND":
        lines.append(
            "> ❌ **Không tìm thấy bot** với mã này trên OKX, hoặc OKX tạm "
            "thời không trả lời được cho mã này."
        )
        lines.append("")

    unavailable = result.get("unavailable") or []
    if unavailable:
        lines.append("**Không tính được** (thiếu dữ liệu hoặc bot không công khai):")
        lines.extend(f"- {_unavailable_label(str(key))}" for key in unavailable)
        lines.append("")

    evidence = result.get("evidence")
    perf = evidence.get("performance") if isinstance(evidence, dict) else None
    if isinstance(perf, dict) and perf:
        lines.append("## Số liệu chính")
        lines.append("")
        lines.append("| Chỉ số | Giá trị |")
        lines.append("|---|---|")
        lines.append(f"| Số lệnh đã chốt | {_fmt_int(perf.get('trade_count'))} |")
        lines.append(f"| Tỉ lệ thắng | {_fmt_pct(perf.get('win_rate'))} |")
        lines.append(f"| Profit factor | {_fmt_score(perf.get('profit_factor'), 2)} |")
        lines.append(f"| Sụt vốn tối đa | {_fmt_pct(perf.get('max_drawdown_pct'))} |")
        lines.append(f"| Sharpe ratio | {_fmt_score(perf.get('sharpe_ratio'), 2)} |")
        lines.append("")

    text_lines = result.get("text") or []
    if text_lines:
        lines.append("## Vì sao")
        lines.append("")
        lines.extend(
            f"- {escaped}"
            for item in text_lines
            if (escaped := _md_escape(item, max_len=MD_NARRATIVE_MAX_LEN))
        )
        lines.append("")

    mc = result.get("mc")
    if mc:
        lines.append("## Mô phỏng")
        lines.append("")
        lines.extend(_mc_section_lines(mc))
        lines.append("")

    lines.append("---")
    lines.append(
        "Nguồn dữ liệu: sổ lệnh công khai OKX copy-trading, hệ thống norabt "
        "tự động chấm điểm."
    )
    iterations = mc.get("iterations") if isinstance(mc, dict) else None
    if iterations:
        lines.append(f"Số kịch bản mô phỏng: {_fmt_int(iterations)}.")
    when = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines.append(f"Thời điểm tạo báo cáo: {when}.")
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
            f"Không tìm thấy bot với mã {code!r} trên OKX. {reason}."
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
            "Bot này không công khai sổ lệnh trên OKX (lỗi 60004 ở endpoint "
            "vị thế/lịch sử lệnh) nên không xem được đang trade asset nào -- "
            "chỉ có hồ sơ tổng quan (nếu tìm thấy) ở trên."
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
        # (still built once) -- see Agent/test/test_web_app.py.
        self._client = client_factory()
        bot_source_factory = bot_source_factory or (
            lambda client, bucket: LiveBotDataSource(client=client, rate_limiter=bucket)
        )
        market_source_factory = market_source_factory or (
            lambda client: LiveMarketDataSource(client=client)
        )
        self._bot_source = bot_source_factory(self._client, self._rate_limiter)
        self._market_source = market_source_factory(self._client)
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

    def list_markets(self) -> List[Dict[str, Any]]:
        return list_markets(self.data_dir)

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
        Agent/scripts/crawl_bots.py and Agent/scripts/backfill_bot_profiles.py
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

        Costs at most 3 OKX requests (see _lookup_live/_lookup_blocked_result
        for exactly when each is spent): one page of closed-order history,
        the current open positions, and -- ONLY when neither the on-disk
        ranking snapshot nor those two calls identify the bot -- one
        public-stats probe. Profile data itself never costs a request when
        the on-disk snapshot already has it (see _profile_snapshot). Same
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

    def _lookup_live(self, code: str) -> Dict[str, Any]:
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
                code, "OKX không trả được dữ liệu sổ lệnh cho mã này lúc này"
            )

        if not positions and not history:
            # Mirrors LiveBotDataSource.get_ledger's own fail-closed guard: a
            # uniqueCode that is OKX-listed at all must have traded SOMETHING
            # to be listed, so an all-empty response here is far more likely
            # a wrong/garbage code than a genuinely untraded bot.
            return _lookup_not_found_result(
                code,
                "OKX trả về sổ lệnh trống hoàn toàn cho mã này "
                "(0 vị thế mở, 0 lệnh đã đóng)",
            )

        now_ms = self._wall_clock_ms()
        open_symbols = [_base_symbol(p.get("instId")) for p in positions]
        closed_records = [
            (_base_symbol(t.get("instId")), _int(t.get("closeTime"))) for t in history
        ]
        assets = _build_asset_states(open_symbols, closed_records, now_ms)
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
        if profile_row is not None:
            return _lookup_limited_result(code, profile_row)
        stats_row = self._lookup_fetch_stats(code)
        if stats_row is not None:
            return _lookup_limited_result(code, None)
        return _lookup_not_found_result(
            code,
            f"Không tìm thấy mã {code} ở bảng xếp hạng lead traders đã lưu hay "
            "public-stats của OKX -- nhiều khả năng đây là uniqueCode sai",
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

    def analyze(self, raw_code: Any) -> Dict[str, Any]:
        code = validate_unique_code(raw_code)
        cached = self._analyze_cache.get(code)
        if cached is not None:
            return cached
        result = self._analyze_live(code)
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

    def _analyze_live(self, code: str) -> Dict[str, Any]:
        try:
            return self._analyze_full(code)
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

    def _analyze_full(self, code: str) -> Dict[str, Any]:
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
            self._scratch_dir, self.evaluation_mode, bot_source=self._bot_source
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
        result = pipeline.run(_SCRATCH_ASSET, f"bot_{code}", venue_type=_SCRATCH_VENUE)
        return _full_result(code, result)

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
                "Module chấm điểm rút gọn (Agent/backend/analysis/limited.py) "
                "chưa sẵn sàng ở phiên bản này của dịch vụ, nên chưa thể trả "
                "kết quả LIMITED chi tiết hơn cho bot này.",
            )
        try:
            payload = assess_from_error(exc)
        except Exception as inner:  # noqa: BLE001 - a sibling module must
            # never be able to crash this endpoint; see the soft-import
            # block's docstring.
            return self._ledger_unavailable_fallback(
                exc,
                f"Module chấm điểm rút gọn báo lỗi khi xử lý mã {code!r}: {inner}",
            )
        if not isinstance(payload, dict) or payload.get("status") not in (
            "FULL",
            "LIMITED",
            "NOT_FOUND",
        ):
            return self._ledger_unavailable_fallback(
                exc,
                "Module chấm điểm rút gọn trả về dữ liệu không đúng định dạng "
                "hợp đồng /api/analyze.",
            )
        # Agent/backend/analysis/limited.py is off-limits here and owned by a
        # parallel task -- it predates this task's `assets` field and has no
        # reason to know about it. A LIMITED/NOT_FOUND bot has no visible
        # ledger by definition (that is what LedgerUnavailableError means),
        # so "no known assets" is the only honest value regardless; this
        # just guarantees the key exists rather than silently omitting it.
        payload.setdefault("assets", [])
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
