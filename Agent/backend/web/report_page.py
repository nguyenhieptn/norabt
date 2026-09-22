"""Self-contained HTML for `GET /bot/<code>` -- the "final destination" page
a human (or another agent) lands on to actually read one bot's risk
assessment, as opposed to the raw JSON `/api/analyze` returns.

Everything needed to render the page is already sitting in the dict
`WebDataService.analyze()` returns (see `Agent/backend/web/data.py`'s module
docstring for its top-level keys, including the optional `narrative` field
from Agent/backend/llm/narrative.py): this module only turns that dict into
HTML/CSS/inline-SVG, it computes nothing new and calls no scoring code of its
own. `app.py` (owned by a parallel task at the time this module was written)
is expected to call `render_bot_report_html(result)` from its `GET
/bot/<code>` handler in place of the bare `<pre>{markdown}</pre>` it renders
today.

Hard constraints this module exists to satisfy (see the task this was
written for):

  * No JavaScript, no external stylesheet/font/CDN, no network fetch of any
    kind. This page is served to strangers' agents on the OKX AI Marketplace
    and to whoever else opens a `/bot/<code>` link; an external dependency
    would be both a point of failure and a tracking vector. Charts are drawn
    as inline `<svg>` built by hand below.
  * One self-contained HTML document. Works fully offline once downloaded.
  * Every value that originates from `result` (a bot's own OKX-supplied
    nick_name most of all -- attacker-controlled, can contain `<script>`,
    quotes, `&`, anything) is HTML-escaped before it is ever concatenated
    into a template string. See `_esc`. There is no path in this module that
    writes untrusted text into the page without going through it.
  * Every numeric value that ends up inside an SVG attribute (a coordinate,
    a width, a radius, ...) is passed through `_coord`, which always returns
    a finite, fixed-point decimal string -- never "nan", "inf", "-inf" or
    "None" -- because assessment data is full of `Optional[float]` fields
    that are frequently `None` (an unmeasured dimension, a simulation that
    never ran, ...), and a bad attribute string is a malformed SVG, not just
    an ugly one.
  * Renders sensibly on a ~400px phone and on a desktop; wide tables scroll
    inside their own `overflow-x:auto` wrapper rather than the whole page.
  * Respects `prefers-color-scheme` (light and dark palettes both defined).

Layout (see the task's own numbered spec, mirrored 1:1 in the section
functions below): header -> conclusion/recommendation -> per-dimension
scores -> Monte Carlo -> statistical inference -> trade metrics -> traded
assets. Sections 3 through 7 each carry at least one collapsible
`<details>` "Phương pháp luận & diễn giải" block -- see `_theory` -- because a
dashboard of numbers with no explanation of what they mean or where they
come from is exactly the failure mode the project owner's own brief called
out ("thiếu vế thứ ba là hỏng"). The Vietnamese in those blocks and in this
module's own prose is written in the same register as
`Agent/backend/report/qc/reporting/reasons.py`: plain, evidence-first, no hedging
filler, no marketing.

LIMITED and NOT_FOUND are first-class inputs, not error cases: a LIMITED
bot's `evidence` dict has a different shape from a FULL bot's (a flat
`components` list -- see `Agent/backend/bot/analysis/limited.py` -- instead of
the FULL pipeline's `dimensions` dict + `score_breakdown`), so the
dimensions section below branches on which shape is actually present rather
than assuming FULL's. NOT_FOUND renders a short standalone page and skips
every other section outright.
"""

from __future__ import annotations

import html
import json
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from numbers import Real
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from Agent.backend.infra.config import config
from Agent.backend.web import limited_view
from Agent.backend.web import score_basis
from Agent.backend.web.loss_analysis import compute_loss_profile
from Agent.backend.market.coverage import MARKET_COVERAGE_TARGET_PCT
from Agent.backend.report.qc.reporting.reasons import LIQ_VI, TREND_VI, VOL_VI

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Escaping / number formatting -- every leaf helper below is defensive by
# construction: give it `None`, a string, `float("nan")`, a bool, whatever a
# half-populated assessment dict might contain, and it returns something safe
# to embed rather than raising.
# --------------------------------------------------------------------------- #


def _esc(value: Any) -> str:
    """HTML-escape anything for embedding as text or inside an attribute.

    `html.escape(..., quote=True)` (the default) escapes `& < > " '`, which
    covers both the "breaks out into a new tag" case and the "breaks out of
    a quoted attribute" case. `None` becomes an empty string rather than the
    literal text "None" -- a missing bot name should render as nothing, not
    as the word "None".
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _coord(value: Any, default: float = 0.0) -> str:
    """Render `value` as an SVG-attribute-safe fixed-point decimal string.

    Never returns "nan", "inf", "-inf", "None" or anything else that would
    make the surrounding SVG attribute malformed -- see this module's own
    docstring on why that is a dedicated, tested guarantee rather than an
    incidental one. Any non-finite or non-numeric input silently falls back
    to `default` (itself always a plain finite float from call sites below).
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = default
    if not math.isfinite(v):
        v = default
    return f"{v:.2f}"


def _num(value: Any, digits: int = 1, default: str = "—") -> str:
    if not _is_finite_number(value):
        return default
    return f"{float(value):,.{digits}f}"


def _pct(value: Any, digits: int = 1, default: str = "—", signed: bool = False) -> str:
    if not _is_finite_number(value):
        return default
    fmt = "{:+.%df}%%" % digits if signed else "{:.%df}%%" % digits
    return fmt.format(float(value))


def _format_prob_pct(value: Any, default: str = "—") -> str:
    if not _is_finite_number(value):
        return default
    fval = float(value)
    if 0.0 < fval < 0.05:
        return "<0.1%"
    if 99.95 < fval < 100.0:
        return ">99.9%"
    return f"{fval:.1f}%"


def _money(value: Any, default: str = "—") -> str:
    if not _is_finite_number(value):
        return default
    return f"{float(value):,.0f} USDT"


def _int_text(value: Any, default: str = "—") -> str:
    if not _is_finite_number(value):
        return default
    return f"{int(round(float(value))):,}"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# --------------------------------------------------------------------------- #
# Labels shared with the QC pipeline's own Vietnamese vocabulary. Duplicated
# here (rather than imported from Agent/backend/report/qc/**) deliberately: that
# tree is off-limits to touch for this task and owned by other work in
# flight, and a presentation-only module has no business depending on it for
# a handful of label strings anyway -- see Agent/backend/report/qc/scoring/fusion.py
# (DIMENSION_LABEL_VI) and Agent/backend/report/qc/reporting/reasons.py (TIER_VI) if
# these ever need to be reconciled by hand.
# --------------------------------------------------------------------------- #

DIMENSION_ORDER: Tuple[str, ...] = (
    "tail_risk",
    "drawdown_risk",
    "behavioral_risk",
    "leverage_exposure",
    "strategy_drift",
    "liquidity_execution",
    "performance_quality",
    "return_r_quality",
    "portfolio_risk",
    "market_alignment",
)

DIMENSION_LABEL_VI: Dict[str, str] = {
    "market_alignment": "Market alignment",
    "performance_quality": "Performance quality",
    "return_r_quality": "Return / R quality",
    "drawdown_risk": "Drawdown risk",
    "tail_risk": "Tail risk",
    "leverage_exposure": "Leverage / exposure",
    "behavioral_risk": "Trading behaviour",
    "strategy_drift": "Strategy durability across phases",
    "liquidity_execution": "Liquidity / execution",
    "portfolio_risk": "Portfolio risk",
}

TIER_LABEL_VI: Dict[str, str] = {
    "EMERGENCY": "EMERGENCY",
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "ELEVATED": "ELEVATED",
    "WATCH": "WATCH",
    # "Khoẻ" (RiskTier.HEALTHY), not "AN TOÀN": that exact string is reserved
    # for the (removed) old 4-bucket bot-level verdict label, and this is a
    # per-dimension risk tier -- a different, more granular axis. See
    # Agent/backend/report/qc/scoring/verdict.py's module docstring.
    "HEALTHY": "HEALTHY",
    "UNKNOWN": "UNMEASURED",
}

# Green -> red as the tier gets worse; UNKNOWN is neutral grey, never green
# (an unmeasured dimension is not the same claim as a measured safe one).
TIER_COLOR: Dict[str, str] = {
    "HEALTHY": "#16a34a",
    "WATCH": "#ca8a04",
    "ELEVATED": "#ea580c",
    "HIGH": "#dc2626",
    "CRITICAL": "#991b1b",
    "EMERGENCY": "#7f1d1d",
    "UNKNOWN": "#9ca3af",
}

# --------------------------------------------------------------------------- #
# Việc 1/Việc 2 -- "Cách bot này chơi": vocabulary for translating the enum
# values `Agent/backend/bot/mcp/analytics/strategy/profile.py` /
# `Agent/backend/bot/mcp/analytics/behavior/detector.py` produce (surfaced in
# `evidence["strategy"]`/`evidence["behavioral"]`, see data.py's
# `_strategy_evidence`/`_behavioral_evidence`) into plain Vietnamese. Kept
# local to this module rather than imported from those trees, same
# reasoning as DIMENSION_LABEL_VI/TIER_LABEL_VI above (off-limits to touch,
# and this module already owns its own presentation vocabulary).
# --------------------------------------------------------------------------- #

MARKET_PHASE_LABEL_VI: Dict[str, str] = {
    "UPTREND_CALM": "uptrend, calm",
    "UPTREND_VOLATILE": "uptrend, highly volatile",
    "DOWNTREND_CALM": "downtrend, calm",
    "DOWNTREND_VOLATILE": "downtrend, highly volatile",
    "RANGE_CALM": "sideways, calm",
    "RANGE_VOLATILE": "sideways, highly volatile",
    "UNKNOWN": "phase not identified",
}

DIRECTIONAL_BIAS_LABEL_VI: Dict[str, str] = {
    "LONG_ONLY": "long only, no short trades",
    "SHORT_ONLY": "short only, no long trades",
    "LONG_TILTED": "leans long",
    "SHORT_TILTED": "leans short",
    "TWO_WAY": "trades both directions, fairly balanced",
    "UNKNOWN": "not enough evidence to determine",
}

ENTRY_STYLE_LABEL_VI: Dict[str, str] = {
    "TREND_FOLLOWING": "trend-following (buys as price rises, sells as price falls)",
    "MEAN_REVERSION": "mean-reversion (buys as price falls, sells as price rises)",
    "MIXED": "a mix of both styles, no clear lean",
    "UNKNOWN": "not enough evidence to determine",
}

# Different vocabulary from the three maps above -- see data.py's own
# `_OBSERVED_PROFILE_VI` comment for why this one is NOT translated at the
# source (it doubles as a scoring-input matching key).
OBSERVED_PROFILE_LABEL_VI: Dict[str, str] = {
    "Scalping": "short-term scalping",
    "Swing": "swing holding",
    "DayTrading": "intraday trading",
    "Grid/Martingale-like": "grid / martingale-style (repeated stacked entries)",
    "UNKNOWN": "not yet determined",
}

BEHAVIORAL_TIER_LABEL_VI: Dict[str, str] = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
    "UNKNOWN": "not measured",
}

# Three-tier confidence a reader needs PER ROW of the phase cross-tab --
# coordinator's own explicit threshold, and explicitly finer than profile.py's
# own single `MIN_TRADES_PER_PHASE=5` cutoff (which only gates whether a row
# feeds best_phase/worst_phase/regime_dependence -- a presentational concern
# report_page.py has no business re-deriving, see that module's own
# docstring). A 1-trade "100% win rate" row must never read as equally solid
# evidence as a 15-trade one (coordinator's own explicit example), hence the
# split at the very bottom rather than a single small/not-small badge.
PHASE_CONFIDENCE_ENOUGH_TRADES = 10  # N >= 10 -> đủ mẫu, được rút ra quy luật
PHASE_CONFIDENCE_THIN_TRADES = 3  # 3 <= N < 10 -> mẫu mỏng, chỉ tham khảo
# N < PHASE_CONFIDENCE_THIN_TRADES -> chưa đủ ý nghĩa, không đại diện.
PHASE_CONFIDENCE_ENOUGH_VI = "enough sample"
PHASE_CONFIDENCE_THIN_VI = "thin sample"
PHASE_CONFIDENCE_INSUFFICIENT_VI = "not yet meaningful"
# Below this coverage, most of the ledger never got assigned a market phase
# at all -- the cross-tab is a strong hint, not a firm conclusion (task's
# own explicit "ranh giới" requirement).
PHASE_COVERAGE_WARN_PCT = 60.0


def _phase_confidence_vi(trades: Any) -> str:
    """`N >= 10` -> `"đủ mẫu"`, `3 <= N < 10` -> `"mẫu mỏng"`, everything else
    (`N < 3`, missing, or non-numeric) -> `"chưa đủ ý nghĩa"` -- coordinator's
    own explicit three-tier threshold. Degrades to the STRICTEST tier on bad
    input (never the most lenient one): a row this function cannot even
    count is exactly the kind of row that must not be trusted by default.
    """
    if (
        not isinstance(trades, (int, float))
        or isinstance(trades, bool)
        or not math.isfinite(trades)
    ):
        return PHASE_CONFIDENCE_INSUFFICIENT_VI
    if trades >= PHASE_CONFIDENCE_ENOUGH_TRADES:
        return PHASE_CONFIDENCE_ENOUGH_VI
    if trades >= PHASE_CONFIDENCE_THIN_TRADES:
        return PHASE_CONFIDENCE_THIN_VI
    return PHASE_CONFIDENCE_INSUFFICIENT_VI


def _phase_label_vi(phase: Any) -> str:
    return MARKET_PHASE_LABEL_VI.get(
        str(phase or "UNKNOWN").upper(), "phase not identified"
    )


# Keys match the English asset-state constants `data.py` already emits
# (`ASSET_STATE_TRADING`/`ASSET_STATE_HOLDING`/`ASSET_STATE_LEFT` --
# "TRADING"/"HOLDING ONLY"/"EXITED"), not this module's own label
# vocabulary: `_render_assets` below reads `a.get("state")` and looks it up
# here directly, with no translation step of its own.
ASSET_STATE_COLOR: Dict[str, str] = {
    "TRADING": "#16a34a",
    "HOLDING ONLY": "#dc2626",
    "EXITED": "#6b7280",
}

# --------------------------------------------------------------------------- #
# Shared design tokens (task's Việc 3) -- Agent/web/tokens.css is now the ONE
# place a verdict-state color (or a page-chrome/type-scale/spacing/radius
# value) is written down; this module previously hardcoded its own copy of
# the `VERDICT_COLOR` values as Python string literals, with no
# guarantee the React SPA (Agent/frontend/) would ever be told about a
# change to them. See tokens.css's own header comment for the full design
# and for why admin_page.py needs no separate wiring (it already imports
# `VERDICT_COLOR` FROM this module rather than redeclaring it).
#
# Mounted read-only into the container as part of Agent/web/ (see
# docker-compose.yml's `../web:/app/Agent/web:ro`), exactly like
# Agent/web/dashboard.html used to be read by app.py's `_dashboard_response`
# -- so this follows the same "never let a missing/unreadable file crash the
# route" discipline that pattern already established, via
# `_FALLBACK_VERDICT_COLOR` below.
# --------------------------------------------------------------------------- #

_DESIGN_TOKENS_PATH = Path(config.BASE_DIR) / "frontend" / "tokens.css"

# Same 6 values this module falls back to whenever tokens.css cannot be
# read/parsed at all (missing checkout, bad permissions, a syntax error a
# human introduced by hand-editing the CSS), so a broken/absent token file
# degrades this module's OWN color choices back to a known-good set, rather
# than breaking every rendered page's verdict badge. Kept byte-identical to
# tokens.css's own `:root` values (see that file's "Verdict classification"
# block) so the two never silently drift.
_FALLBACK_VERDICT_COLOR: Dict[str, str] = {
    "DRAWDOWN: HIGH · QUALITY: WEAK": "#dc2626",
    "DRAWDOWN: HIGH · QUALITY: GOOD": "#d97706",
    "DRAWDOWN: LOW · QUALITY: GOOD": "#16a34a",
    "DRAWDOWN: LOW · QUALITY: WEAK": "#0284c7",
    "HIDDEN RISK": "#7c3aed",
    "INSUFFICIENT EVIDENCE": "#6b7280",
}

# CSS custom-property name -> the Vietnamese verdict label it colors, per
# tokens.css's own "Verdict classification" block. A dict, not a reverse
# lookup built from `_FALLBACK_VERDICT_COLOR`'s keys, because the CSS
# variable NAME is deliberately English/semantic ("high-dd-weak-q"/
# "high-dd-good-q"/"low-dd-good-q"/"low-dd-weak-q"/"hidden-risk"/"unknown")
# while the Python-side key stays the Vietnamese label every call site
# (`_verdict_color`, admin_page.py's own `VERDICT_COLOR.get(verdict, ...)`)
# already looks up by.
_VERDICT_TOKEN_TO_LABEL: Dict[str, str] = {
    "--verdict-high-dd-weak-q": "DRAWDOWN: HIGH · QUALITY: WEAK",
    "--verdict-high-dd-good-q": "DRAWDOWN: HIGH · QUALITY: GOOD",
    "--verdict-low-dd-good-q": "DRAWDOWN: LOW · QUALITY: GOOD",
    "--verdict-low-dd-weak-q": "DRAWDOWN: LOW · QUALITY: WEAK",
    "--verdict-hidden-risk": "HIDDEN RISK",
    "--verdict-unknown": "INSUFFICIENT EVIDENCE",
}

# Matches one `--custom-property: value;` declaration, capturing the name
# (group 1, without the leading `--`) and the value (group 2, whitespace-
# trimmed by the `.strip()` call at each use site rather than in the pattern
# itself, since a value can legitimately contain internal spaces, e.g. the
# `repeating-linear-gradient(...)` track-muted token). Deliberately simple
# (no full CSS parser, no new dependency) -- tokens.css is a file this
# project itself authors and controls the shape of, not arbitrary/hostile
# CSS, so this only has to survive THIS file's own small, hand-written
# grammar, not the general CSS spec.
_CSS_CUSTOM_PROPERTY_RE = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")

# Matches the FIRST top-level `:root { ... }` block only (non-greedy up to
# the first `}`) -- deliberately excludes the `@media (prefers-color-scheme:
# dark)`/`:root[data-theme="dark"]` blocks that follow it in tokens.css, so
# a dark-mode override of a variable (e.g. `--bg`) can never shadow that
# variable's base/light value when this module reads a Python-side color out
# of the file (verdict colors are never redefined for dark mode in
# tokens.css -- see that file's own comment -- but this guard makes that
# true by construction rather than by convention alone).
_ROOT_BLOCK_RE = re.compile(r":root\s*\{([^}]*)\}")


def _parse_root_css_custom_properties(css_text: str) -> Dict[str, str]:
    """`--name: value;` pairs from the first `:root { ... }` block of
    `css_text` -- see `_ROOT_BLOCK_RE`/`_CSS_CUSTOM_PROPERTY_RE` above for
    exactly what is and is not matched. Returns `{}` (never raises) for
    anything that does not contain a recognisable `:root { ... }` block.
    """
    root_match = _ROOT_BLOCK_RE.search(css_text)
    if root_match is None:
        return {}
    return {
        name: value.strip()
        for name, value in _CSS_CUSTOM_PROPERTY_RE.findall(root_match.group(1))
    }


def _design_tokens_css_text() -> str:
    """Raw text of `tokens.css`, for embedding verbatim into this module's
    rendered `<style>` tag (see `render_bot_report_html`) -- the "Python đọc
    rồi nhúng vào <style>" half of the task's own suggested wiring. `""` on
    any read failure: a missing/unreadable token file must degrade this
    page's styling, never crash the route (same contract as
    `app.py`'s `_dashboard_response`) -- the page still renders, just
    without the CSS custom properties its own `_CSS` below relies on for
    theming (a logged warning either way, so this is not silent).
    """
    try:
        return _DESIGN_TOKENS_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "Could not read design token %s -- falling back to the default colors "
            "hardcoded in source: %s",
            _DESIGN_TOKENS_PATH,
            exc,
        )
        return ""


def _load_verdict_color() -> Dict[str, str]:
    """Build `VERDICT_COLOR` (below) FROM `tokens.css` when possible,
    falling back to `_FALLBACK_VERDICT_COLOR`'s hardcoded values -- see that
    dict's own docstring for exactly when the fallback applies. Called once
    at import time: `VERDICT_COLOR` is a plain module-level dict (like it
    was before tokens.css existed) so every existing call site
    (`_verdict_color`, admin_page.py's own `VERDICT_COLOR.get(...)`) keeps
    working unchanged -- this only changes WHERE the values originally come
    from, never the shape callers see.
    """
    colors = dict(_FALLBACK_VERDICT_COLOR)
    tokens = _parse_root_css_custom_properties(_design_tokens_css_text())
    for var_name, label in _VERDICT_TOKEN_TO_LABEL.items():
        value = tokens.get(var_name) or tokens.get(var_name.lstrip("-"))
        if value:
            colors[label] = value
    return colors


# The public dict every call site in this module (and admin_page.py, via its
# own `from report_page import VERDICT_COLOR`) actually reads. Populated once
# at import time -- see `_load_verdict_color`'s own docstring for why a
# plain dict rather than a lazy property/function call was kept here: it
# preserves the exact shape every existing caller already depends on.
VERDICT_COLOR: Dict[str, str] = _load_verdict_color()

HORIZON_LABEL_VI: Dict[str, str] = {
    "SHORT": "SHORT",
    "MEDIUM": "MEDIUM",
    "LONG": "LONG",
}


def _tier_color(tier: Any) -> str:
    return TIER_COLOR.get(str(tier or "UNKNOWN").upper(), TIER_COLOR["UNKNOWN"])


def _verdict_color(verdict: Any) -> str:
    return VERDICT_COLOR.get(str(verdict or ""), "#6b7280")


# --------------------------------------------------------------------------- #
# Small HTML fragment builders
# --------------------------------------------------------------------------- #


def _theory(
    read_html: str, basis_html: str, *, label: str = "Methodology & interpretation"
) -> str:
    """Collapsible methodology & quantitative interpretation block in compact terminal format."""
    return (
        '<details class="theory">'
        f"<summary>{_esc(label)}</summary>"
        '<div class="theory-body theory-quant-grid">'
        '<div class="theory-item"><span class="theory-tag">METRIC FOCUS</span>'
        f'<div class="theory-text">{read_html}</div></div>'
        '<div class="theory-item"><span class="theory-tag theory-tag-formula">METHODOLOGY</span>'
        f'<div class="theory-text">{basis_html}</div></div>'
        "</div></details>"
    )


def _section(
    title: str,
    body: str,
    *,
    anchor: Optional[str] = None,
    tone: str = "",
    pair: bool = False,
    eyebrow: str = "",
    note: str = "",
) -> str:
    """`tone` chọn mức nổi bật của cả khối `<section>` -- phần thiết kế lại
    (Việc "nhìn xấu quá") giải quyết đúng than phiền "mọi mục trông như
    nhau": `"primary"` cho khối kết luận/điểm số (nổi bật nhất, viền nhấn +
    nền ánh accent), `"quiet"` cho khối kỹ thuật/kiểm toán thuần số liệu
    (lùi xuống, tiêu đề nhỏ và trầm hơn), `""` (mặc định, giữ NGUYÊN
    `class="card"` như trước -- hai test `test_report_page.py` khoá đúng
    chuỗi `class="card" id="thi-truong"`/`id="cach-choi"` bằng regex nên hai
    mục đó KHÔNG được đổi tone HAY `pair`) là mức trung tính hiện có từ
    trước.

    `eyebrow`/`note` (cùng mặc định rỗng nên mọi lời gọi cũ không đổi
    hình dạng) là hai chỗ chữ nhỏ trong `.block-h`: eyebrow đứng TRÊN tiêu
    đề (nhãn mono viết hoa, nói mục này thuộc nhóm nào), note nằm sát mép
    phải cùng hàng với tiêu đề (chú thích ngắn, ví dụ nguồn số liệu) --
    đúng cấu trúc `.block-h`/`.block-b` của bảng điều khiển Nora.

    `pair=True` thêm class `card-pair`, cho `.tab-panel` (xem `_CSS`'s
    `@media (min-width: 1100px)`) phép ghép mục này với mục liền kề vào
    chung một hàng lưới 2 cột trên màn rộng thay vì luôn chiếm trọn một
    hàng riêng -- chỉ bật ở những mục đã kiểm tra là đủ ngắn/gọn để đứng
    cạnh nhau (ví dụ hai mục kỹ thuật liền kề trong tab Lệnh & Vị Thế),
    KHÔNG bật tràn lan vì một mục dài đứng lẻ loi cạnh khoảng trống trông
    còn xấu hơn cả xếp dọc.
    """
    if not body:
        return ""
    anchor_attr = f' id="{_esc(anchor)}"' if anchor else ""
    tone_cls = f" card-{tone}" if tone else ""
    pair_cls = " card-pair" if pair else ""
    eyebrow_html = f'<span class="eyebrow">{_esc(eyebrow)}</span>' if eyebrow else ""
    note_html = f'<span class="note">{_esc(note)}</span>' if note else ""
    return (
        f'<section class="card{tone_cls}{pair_cls}"{anchor_attr}>'
        f'<header class="block-h">{eyebrow_html}<h2>{_esc(title)}</h2>{note_html}</header>'
        f'<div class="block-b">{body}</div>'
        "</section>"
    )


METRIC_FORMULA_INFO: Dict[str, Dict[str, str]] = {
    # Headline scores
    "risk_score": {
        "title": "Overall risk score (0-100)",
        "formula": "Risk Score = Min(100, Max(Veto_Floors, Weighted_Average(10 Risk Dimensions)))",
        "desc": "Scale of 0-100 (lower is safer). Combines 10 independent risk dimensions (drawdown, leverage, fat tails, holding losers, ...), with a Veto Floor & Emergency Override mechanism that forces the score to 100 when a liquidation risk or extreme risk is detected.",
    },
    "quality_score": {
        "title": "Strategy quality score (0-100)",
        "formula": "Quality Score = Base(50) + Bonus(Sharpe, Sortino, Calmar, WinRate, Expectancy) - Risk Penalty",
        "desc": "Scale of 0-100 (higher is better). A comprehensive assessment of return per unit of risk, the ability to preserve capital when the market turns unfavourable, and the stability of the closed-trade sequence.",
    },
    "confidence": {
        "title": "Data confidence (0-100%)",
        "formula": "Confidence = f(Number of trades N, Observation period T, Market-phase distribution)",
        "desc": "Measures whether the sample size is statistically adequate: fewer than 30 trades is considered insufficient data; a bot that has gone through all market phases (up/down/sideways) with more than 100 trades reaches high confidence.",
    },
    # 10 Risk Dimensions
    "tail_risk": {
        "title": "Tail risk",
        "formula": "Kurtosis, Skewness, 95% CVaR, Max Loss Outlier relative to standard deviation",
        "desc": "Measures the risk of black-swan events or extreme losing trades outside the normal distribution that could wipe out accumulated profit.",
    },
    "drawdown_risk": {
        "title": "Drawdown risk",
        "formula": "Max Drawdown %, Recovery Days, length of consecutive drawdown streaks",
        "desc": "Measures the depth and duration of the account's fall from its peak, the psychological pressure it creates, and the risk of the bot's followers blowing up their account.",
    },
    "behavioral_risk": {
        "title": "Trading behaviour risk",
        "formula": "Detects martingale, averaging down, raising leverage after a loss, order-entry loops",
        "desc": "Assesses high-risk or undisciplined trading habits found in the trade ledger that could lead to a sudden account blow-up.",
    },
    "leverage_exposure": {
        "title": "Leverage & exposure",
        "formula": "Actual leverage ratio / capital, margin utilisation, concurrent-position exposure ratio",
        "desc": "Measures how much financial leverage is used and the risk of forced liquidation by the exchange during sharp market moves.",
    },
    "strategy_drift": {
        "title": "Strategy durability across phases",
        "formula": "Consistency of entry style, performance deviation across uptrend / downtrend / sideways phases",
        "desc": "Checks whether the bot keeps to its own rules or drifts and loses effectiveness when the market changes phase.",
    },
    "liquidity_execution": {
        "title": "Liquidity & execution",
        "formula": "Estimated slippage, order size relative to order-book depth of the traded pair",
        "desc": "Measures slippage risk when copying the bot's trades, especially on thinly traded pairs.",
    },
    "performance_quality": {
        "title": "Performance quality",
        "formula": "Profit Factor, Sharpe, Sortino, Calmar, average win/loss ratio",
        "desc": "Assesses actual profit generated relative to the risk taken, over the history of closed trades.",
    },
    "return_r_quality": {
        "title": "Return / R quality",
        "formula": "Distribution of per-trade R-multiples, expectancy per unit of risk accepted (R)",
        "desc": "Measures positive asymmetry: how much money is made per unit of capital put at risk.",
    },
    "portfolio_risk": {
        "title": "Portfolio risk",
        "formula": "Cross-asset correlation, capital concentration in a single position",
        "desc": "Measures the risk of concentrating capital in one coin or holding several positions whose moves are correlated.",
    },
    "market_alignment": {
        "title": "Market alignment",
        "formula": "Beta versus BTC/ETH, alignment with or against the broader market trend",
        "desc": "Measures whether the bot makes money through genuine skill (alpha) or simply by riding a broad market rally (beta).",
    },
    "drawdown": {
        "title": "Drawdown risk",
        "formula": "Max Drawdown %, Recovery Days, length of consecutive drawdown streaks",
        "desc": "Measures the depth and duration of the account's fall from its peak, the psychological pressure it creates, and the risk of the bot's followers blowing up their account.",
    },
    "stability": {
        "title": "Performance stability",
        "formula": "Variance of weekly return ratios, equity curve smoothness, consistency index",
        "desc": "Assesses whether return comes from steady, repeatable execution or volatile spikes.",
    },
    "win_cadence": {
        "title": "Win & loss cadence",
        "formula": "Autocorrelation of trade outcomes, streak length distribution, clustering of losses",
        "desc": "Measures whether losses occur in clusters that could exhaust follower capital.",
    },
    "monte_carlo": {
        "title": "Monte Carlo simulation",
        "formula": "10,000 bootstrap simulations of return distribution, CVaR and probability of ruin",
        "desc": "Stress-tests the historical return distribution across thousands of simulated market paths.",
    },
    "trade_count": {
        "title": "Total closed trades",
        "formula": "Trade count = total number of completed position closes",
        "desc": "Counted directly from the bot's public closed-trade log on OKX. Every time the bot closes a position (win or loss) it counts as one trade.",
    },
    "win_rate": {
        "title": "Win rate",
        "formula": "Win Rate (%) = (trades with PnL > 0 / total trades) × 100%",
        "desc": "The percentage of closed trades with a positive result. Note: a high win rate does not guarantee safety if the bot holds losers instead of cutting them.",
    },
    "profit_factor": {
        "title": "Profit factor",
        "formula": "Profit Factor = total profit from winning trades / |total loss from losing trades|",
        "desc": "The ratio of total profit to total absolute loss. PF > 1.0: the bot has a net profit; PF < 1.0: total losses exceed total profit (losing money); PF > 1.5: a strongly profitable system.",
    },
    "payoff_ratio": {
        "title": "Payoff ratio",
        "formula": "Payoff Ratio = average profit per winning trade / |average loss per losing trade|",
        "desc": "The ratio between the average win and the average loss. A payoff ratio above 1.0 means each win tends to be larger than each loss.",
    },
    "expectancy": {
        "title": "Expectancy per trade",
        "formula": "Expectancy = (win rate × average win) - (loss rate × |average loss|)",
        "desc": "The average expected profit for each new trade opened (USDT). Reflects the strategy's mathematical edge: positive means an edge, negative means it loses money over time.",
    },
    "total_pnl": {
        "title": "Total PnL (cumulative)",
        "formula": "Total PnL = Σ (PnL of every closed trade)",
        "desc": "The total realised profit or loss (USDT) accumulated across the bot's entire closed-trade history.",
    },
    "max_drawdown_pct": {
        "title": "Max drawdown",
        "formula": "Max DD (%) = Max [ (highest capital peak - next lowest trough) / capital peak ] × 100%",
        "desc": "The largest fall in capital from its highest peak to the lowest trough in the bot's history. Measures the worst stretch a copier of this bot has ever had to endure.",
    },
    "current_drawdown_pct": {
        "title": "Current drawdown",
        "formula": "Current DD (%) = [ (most recent capital peak - current capital) / most recent capital peak ] × 100%",
        "desc": "How far the account currently sits below the highest capital peak the bot has ever reached.",
    },
    "sharpe_ratio": {
        "title": "Sharpe ratio",
        "formula": "Sharpe = (average return - risk-free rate) / standard deviation of returns (σ)",
        "desc": "Measures return earned per unit of total volatility. Sharpe > 1 is decent, > 2 is excellent. Penalises upside and downside volatility equally.",
    },
    "sortino_ratio": {
        "title": "Sortino ratio",
        "formula": "Sortino = (average return - risk-free rate) / downside deviation",
        "desc": "Similar to Sharpe but only counts the volatility of LOSING trades (downside risk), without penalising large wins. A more honest reflection of the ability to preserve capital.",
    },
    "calmar_ratio": {
        "title": "Calmar ratio (annualised return / max drawdown)",
        "formula": "Calmar = annualised return / max drawdown",
        "desc": "The ratio between the annualised rate of capital growth and the deepest drawdown ever suffered. A higher Calmar ratio means faster recovery after a drawdown.",
    },
    "max_win_streak": {
        "title": "Longest winning streak",
        "formula": "Max Win Streak = the most consecutive trades with PnL > 0",
        "desc": "The record number of consecutive winning trades with no losing trade in between.",
    },
    "max_loss_streak": {
        "title": "Longest losing streak",
        "formula": "Max Loss Streak = the most consecutive trades with PnL ≤ 0",
        "desc": "The record number of consecutive losing trades in the bot's history. Critical for managing capital and avoiding an account blow-up during a sustained drawdown.",
    },
    "average_hold_time_minutes": {
        "title": "Average hold time",
        "formula": "Average Hold Time = total time positions were open (minutes) / total trades",
        "desc": "The average time from when the bot opens a position to when it closes it. Helps identify whether the bot is scalping (<30 min), day trading (a few hours), or swing trading (several days).",
    },
    "trade_frequency_per_day": {
        "title": "Trade frequency (trades per day)",
        "formula": "Frequency = total closed trades / total active days",
        "desc": "The average number of trades per day. Reflects how active the bot is and how much it spends on trading costs (commission/slippage).",
    },
    # Open positions audit
    "open_positions": {
        "title": "Open positions",
        "formula": "The number of positions currently OPEN and not yet closed on OKX",
        "desc": "The number of positions the bot currently has floating in the market, not yet taken profit or stopped out.",
    },
    "open_loss": {
        "title": "Unrealised loss",
        "formula": "Unrealised loss = Σ (market price - entry price) × size, for positions currently underwater",
        "desc": "The total mark-to-market loss across all open positions that have not yet been closed.",
    },
    "open_loss_to_capital_pct": {
        "title": "Unrealised loss / capital ratio",
        "formula": "Ratio (%) = (|unrealised loss| / the bot's reference capital) × 100%",
        "desc": "The percentage of capital being eroded by open positions held at a loss. A high ratio warns that the bot is close to being liquidated.",
    },
    "marked_pf": {
        "title": "Marked-to-market profit factor (Marked PF)",
        "formula": "Marked PF = (realised profit + unrealised profit) / (|realised loss| + |unrealised loss|)",
        "desc": "The profit factor if every open position were closed right now at current prices. If Marked PF < 1 while the closed-book PF > 1, the bot is holding losers to hide the true loss.",
    },
    "pnl_skew": {
        "title": "PnL skewness",
        "formula": "Skewness = E[(X - μ)³] / σ³ over the per-trade PnL series",
        "desc": "Measures the asymmetry of returns. A deeply negative skew (< -0.5) shows the bot tends to take small profits early but occasionally suffers one enormous loss -- typical of martingale or averaging-down behaviour.",
    },
    "pnl_kurtosis": {
        "title": "PnL kurtosis",
        "formula": "Kurtosis = E[(X - μ)⁴] / σ⁴ over the per-trade PnL series",
        "desc": "Measures how fat the tails of the distribution are. Kurtosis > 3 indicates the bot carries fat-tail risk, with extreme swings happening more often than a normal distribution would predict.",
    },
    # Statistical inference
    "sharpe_per_trade": {
        "title": "Sharpe per trade",
        "formula": "Sharpe_trade = average PnL per trade / standard deviation of PnL per trade",
        "desc": "The Sharpe ratio computed over individual trades instead of over a daily or monthly time series.",
    },
    "probabilistic_sharpe": {
        "title": "Probabilistic Sharpe Ratio (PSR)",
        "formula": "PSR(SR*) = Z [ (SR - SR*) × √(N - 1) / √(1 - Skew×SR + (Kurt-1)/4 × SR²) ]",
        "desc": "The probability that the true Sharpe ratio exceeds zero once sample length, skew and fat tails are corrected for (Bailey & López de Prado, 2012). PSR above 95% is needed before claiming a genuine edge.",
    },
    "deflated_sharpe": {
        "title": "Deflated Sharpe Ratio (DSR)",
        "formula": "DSR = PSR(SR_benchmark), where SR_benchmark is the maximum expected Sharpe from trying many bots",
        "desc": "Corrects the probabilistic Sharpe ratio for the fact that this bot was picked out of a larger group of candidates. DSR removes the luck introduced by selecting the best-looking bot in hindsight (selection bias).",
    },
    "min_track_record_trades": {
        "title": "Minimum trades required (MinTRL)",
        "formula": "MinTRL = 1 + [1 - Skew×SR + (Kurt-1)/4 × SR²] × (Z_0.95 / SR)²",
        "desc": "The minimum number of trades the bot needs for its Sharpe ratio to reach 95% statistical confidence. If the current trade count is below MinTRL, the Sharpe result is not yet reliable.",
    },
    "sample_size": {
        "title": "Inference sample size",
        "formula": "Sample size = the number of trades fed into the statistical test",
        "desc": "The total number of trade observations used to run the statistical inference model.",
    },
    "selection_trials": {
        "title": "Number of candidates compared (Selection Trials)",
        "formula": "The number of bots in the pool this bot was selected from",
        "desc": "The number of strategies/bots evaluated at the same time. Used to compute how much the DSR result should be discounted.",
    },
}


def _calc_label_html(label: str, info_key: Optional[str] = None) -> str:
    """Render a parameter label with native title tooltip and clickable formula button."""
    info = METRIC_FORMULA_INFO.get(info_key) if info_key else None
    if not info:
        return _esc(label)

    title = _esc(info.get("title", label))
    formula = _esc(info.get("formula", ""))
    desc = _esc(info.get("desc", ""))
    escaped_key = _esc(info_key or "")
    tooltip = f"{title}\n📐 Formula: {formula}\n💡 Criteria: {desc}"

    return (
        f'<span class="metric-label-row">'
        f'<span class="param-label" title="{_esc(tooltip)}" data-metric-key="{escaped_key}" '
        f'data-title="{title}" data-formula="{formula}" data-desc="{desc}">'
        f'{_esc(label)}'
        f'</span>'
        f'<button type="button" class="formula-star-btn" onclick="openFormulaModal(\'{escaped_key}\')" '
        f'data-metric-key="{escaped_key}" data-title="{title}" data-formula="{formula}" data-desc="{desc}" '
        f'aria-label="View formula {title}">*</button>'
        f'</span>'
    )


def _stat_tile(
    label: str,
    value: str,
    *,
    color: Optional[str] = None,
    size: str = "",
    info_key: Optional[str] = None,
    basis_anchor: Optional[str] = None,
) -> str:
    """`size="hero"` là biến thể to/đậm hơn dùng riêng cho 3 ô điểm số đầu
    trang (rủi ro/chất lượng/độ tin cậy) -- đúng yêu cầu "kết luận + điểm số
    phải nổi bật nhất". Mặc định `size=""` giữ nguyên `class="stat-tile"`
    như trước, không ảnh hưởng mọi lời gọi khác trong module này.

    `basis_anchor`, khi có, thêm một dấu `*` bấm được ngay sau nhãn, dẫn tới
    `#{basis_anchor}` -- id của khối "Chú thích giải thích điểm số" trong
    mục "Điểm từng chiều rủi ro" (xem `_render_score_basis`). Chủ dự án yêu
    cầu thẳng: "nên có sao ở đó để giải thích những tiêu chí và công thức để
    ra được score đấy". Không dùng JS: trình duyệt hiện đại tự mở một
    `<details>` đang đóng khi mục tiêu điều hướng theo fragment nằm bên
    trong nó, nên một thẻ `<a href="#...">` thường là đủ. Mặc định `None`
    (không đổi hình dạng của mọi lời gọi cũ).
    """
    style = f' style="color:{color}"' if color else ""
    tile_style = f' style="--tile-accent:{color}"' if color else ""
    size_cls = f" stat-tile-{size}" if size else ""
    label_markup = _calc_label_html(label, info_key) if info_key else _esc(label)
    if basis_anchor and not info_key:
        label_markup += (
            f' <a class="score-basis-star" href="#{_esc(basis_anchor)}" '
            f'aria-label="See how {_esc(label)} is calculated" title="See how this score is calculated">*</a>'
        )
    return (
        f'<div class="stat-tile{size_cls}"{tile_style}>'
        f'<div class="stat-value"{style}>{_esc(value)}</div>'
        f'<div class="stat-label">{label_markup}</div>'
        "</div>"
    )


def _table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    table_class: str = "",
    table_id: str = "",
    page_size: Optional[int] = None,
) -> str:
    """Every cell is passed through the caller already escaped/formatted --
    this only lays out the markup, and wraps the whole thing in a horizontal
    scroll container so a wide table never widens the page itself (task's
    own explicit mobile requirement).
    """
    if not rows:
        return ""
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body_rows = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    cls_attr = f' class="{_esc(table_class)}"' if table_class else ""
    id_attr = f' id="{_esc(table_id)}"' if table_id else ""
    page_attr = f' data-page-size="{page_size}"' if page_size else ""
    return (
        f'<div class="table-scroll"><table{id_attr}{cls_attr}{page_attr}>'
        f"<thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody>"
        "</table></div>"
    )


def _badge(text: str, color: str) -> str:
    return f'<span class="badge" style="--badge-color:{color}">{_esc(text)}</span>'


def _findings_list(findings: Any, limit: int = 4) -> str:
    if not isinstance(findings, list) or not findings:
        return ""
    items = [f for f in findings if isinstance(f, str) and f.strip()][:limit]
    if not items:
        return ""
    return (
        "<ul class='findings'>"
        + "".join(f"<li>{_esc(f)}</li>" for f in items)
        + "</ul>"
    )


# --------------------------------------------------------------------------- #
# SVG primitives -- hand-rolled, no library (see module docstring). Every
# function here funnels coordinates through `_coord` before writing them
# into an attribute string.
# --------------------------------------------------------------------------- #


def _svg(
    width: float,
    height: float,
    body: str,
    *,
    extra_class: str = "",
    aria_label: str = "",
) -> str:
    w = _coord(width, 320.0)
    h = _coord(height, 120.0)
    cls = f' class="{_esc(extra_class)}"' if extra_class else ""
    # `aria_label` is optional and additive (every existing call site keeps
    # working with none) -- a short Vietnamese description of what the chart
    # shows, for a screen reader, since `role="img"` alone gives it no
    # accessible name of its own.
    aria_attr = f' aria-label="{_esc(aria_label)}"' if aria_label else ""
    # KHÔNG ghi `height` cố định: với `width="100%"` + `height="{h}"` thì
    # `preserveAspectRatio` mặc định (xMidYMid meet) ghim nội dung ở đúng cỡ
    # gốc rồi căn giữa -- trên thẻ rộng (trang đã full màn hình) thành ra hai
    # mảng trắng lớn hai bên. Bỏ `height` + CSS `height:auto` cho nội dung
    # giãn ĐỀU theo bề ngang thật; mỗi loại biểu đồ tự chặn bằng `max-width`
    # trong `_CSS` để chữ không phóng to quá cỡ đọc.
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%"{cls}{aria_attr} '
        f'role="img" xmlns="http://www.w3.org/2000/svg">{body}</svg>'
    )


def _rect(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str,
    rx: float = 4.0,
    extra: str = "",
) -> str:
    return (
        f'<rect x="{_coord(x)}" y="{_coord(y)}" width="{_coord(max(w, 0.0))}" '
        f'height="{_coord(max(h, 0.0))}" rx="{_coord(rx)}" fill="{_esc(fill)}" {extra}/>'
    )


def _line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str,
    width: float = 1.0,
    dash: str = "",
    extra: str = "",
) -> str:
    """`extra` mirrors `_text`'s own parameter: raw SVG attributes appended
    verbatim. Callers in the Monte Carlo chart already passed it, which raised
    a TypeError on every render of that chart until this accepted it. Content
    is trusted markup written in this module, never user data -- same contract
    as `_text`.
    """
    dash_attr = f' stroke-dasharray="{_esc(dash)}"' if dash else ""
    extra_attr = f" {extra.strip()}" if extra else ""
    return (
        f'<line x1="{_coord(x1)}" y1="{_coord(y1)}" x2="{_coord(x2)}" y2="{_coord(y2)}" '
        f'stroke="{_esc(stroke)}" stroke-width="{_coord(width)}"{dash_attr}{extra_attr}/>'
    )


def _text(
    x: float,
    y: float,
    text: str,
    *,
    anchor: str = "start",
    cls: str = "",
    fill: str = "",
    extra: str = "",
) -> str:
    fill_attr = f' fill="{_esc(fill)}"' if fill else ""
    cls_attr = f' class="{_esc(cls)}"' if cls else ""
    extra_attr = f" {extra.strip()}" if extra else ""
    return (
        f'<text x="{_coord(x)}" y="{_coord(y)}" text-anchor="{_esc(anchor)}"'
        f"{cls_attr}{fill_attr}{extra_attr}>{_esc(text)}</text>"
    )


# --------------------------------------------------------------------------- #
# Chart: horizontal bars, 0..100 scale -- used for per-dimension scores.
# --------------------------------------------------------------------------- #


class _BarRow:
    __slots__ = (
        "label",
        "value",
        "color",
        "value_text",
        "measured",
        "tag",
        "info_key",
        "note",
    )

    def __init__(
        self,
        label: str,
        value: Optional[float],
        color: str,
        value_text: str,
        *,
        measured: bool = True,
        tag: Optional[str] = None,
        info_key: Optional[str] = None,
        note: Optional[str] = None,
    ) -> None:
        self.label = label
        self.value = value
        self.color = color
        self.value_text = value_text
        self.measured = measured
        self.tag = tag
        self.info_key = info_key
        self.note = note


def _horizontal_bars(
    rows: Sequence[_BarRow],
    *,
    max_value: float = 100.0,
    width: float = 750.0,
    value_w: float = 135.0,
) -> str:
    if not rows:
        return ""
    row_h = 38.0  # khoảng thở thoáng đãng giữa các thanh
    top_pad = 8.0
    label_w = 236.0
    star_x = 242.0
    track_x = 252.0
    track_w = max(width - track_x - value_w - 10.0, 40.0)
    height = top_pad * 2 + row_h * len(rows)
    parts: List[str] = []
    for i, row in enumerate(rows):
        y = top_pad + i * row_h
        mid = y + row_h * 0.60
        info = METRIC_FORMULA_INFO.get(row.info_key) if row.info_key else None
        row_parts: List[str] = []
        note_suffix = f" -- {row.note}" if row.note else ""
        if info:
            tooltip_str = f"{info.get('title', row.label)}: {info.get('desc', '')} (Formula: {info.get('formula', '')}){note_suffix}"
            row_parts.append(f"<title>{_esc(tooltip_str)}</title>")
            escaped_key = _esc(row.info_key or "")
            t_title = _esc(info.get("title", row.label))
            t_formula = _esc(info.get("formula", ""))
            t_desc = _esc(info.get("desc", ""))
            text_extra = (
                f'style="cursor:pointer" data-metric-key="{escaped_key}" '
                f'data-title="{t_title}" data-formula="{t_formula}" data-desc="{t_desc}" '
                f'title="{_esc(tooltip_str)}" onclick="openFormulaModal(\'{escaped_key}\')"'
            )
            star_extra = (
                f'style="cursor:pointer;font-weight:700;" data-metric-key="{escaped_key}" '
                f'data-title="{t_title}" data-formula="{t_formula}" data-desc="{t_desc}" '
                f'title="{_esc(tooltip_str)}" onclick="openFormulaModal(\'{escaped_key}\')"'
            )
        elif row.note:
            text_extra = f'title="{_esc(row.note)}"'
            star_extra = ""
        else:
            text_extra = ""
            star_extra = ""

        label_text = row.label if len(row.label) <= 36 else row.label[:35] + "…"
        row_parts.append(_text(0, mid, label_text, cls="bar-label", extra=text_extra))
        if info:
            row_parts.append(
                _text(
                    star_x,
                    mid,
                    "*",
                    anchor="middle",
                    cls="bar-star",
                    fill="var(--accent, #38bdf8)",
                    extra=star_extra,
                )
            )
        row_parts.append(
            _rect(track_x, y + 6, track_w, row_h - 16, fill="var(--track)", rx=6)
        )
        if row.measured and row.value is not None:
            frac = _clamp(float(row.value) / max_value if max_value else 0.0, 0.0, 1.0)
            row_parts.append(
                _rect(track_x, y + 6, track_w * frac, row_h - 16, fill=row.color, rx=6)
            )
        else:
            # Unmeasured: a flat hatched-looking muted bar rather than a
            # numeric value -- a neutral placeholder score must never look
            # like a real measurement (task's own LIMITED requirement).
            row_parts.append(
                _rect(track_x, y + 6, track_w, row_h - 16, fill="var(--track)", rx=6)
            )
            row_parts.append(
                _rect(
                    track_x,
                    y + 6,
                    track_w,
                    row_h - 16,
                    fill="none",
                    rx=6,
                    extra='stroke="var(--axis)" stroke-width="1" stroke-dasharray="5 4"',
                )
            )
        value_x = track_x + track_w + 10
        val_cls = "bar-value"
        val_fill = ""
        val_txt = str(row.value_text or "").strip()
        if val_txt.startswith("+"):
            val_cls += " val-pos"
            val_fill = "#10b981"
        elif val_txt.startswith("-") or "-" in val_txt:
            val_cls += " val-neg"
            val_fill = "#ef4444"
        row_parts.append(_text(value_x, mid, row.value_text, cls=val_cls, fill=val_fill))
        if row.tag:
            row_parts.append(_text(track_x + 4, y + row_h - 3, row.tag, cls="bar-tag"))
        parts.append(f'<g class="bar-row-g">{"".join(row_parts)}</g>')
    return _svg(width, height, "".join(parts), extra_class="bar-chart")


def _diverging_bars(
    rows: Sequence[Tuple[str, Optional[float]]],
    *,
    width: float = 640.0,
    unit: str = "%",
) -> str:
    """Percentiles that can be negative or positive, drawn as bars growing
    left (loss) or right (profit) from a shared zero/breakeven line. Used
    for the Monte Carlo terminal-outcome percentile spread. Clamped at -100.0%
    stop-out boundary so that simulated paths do not show unrealistic -3000% ruin.
    """
    values = [max(-100.0, float(v)) for _, v in rows if _is_finite_number(v)]
    if not values:
        return ""
    span = max(max(values, default=1.0), abs(min(values, default=-1.0)), 1.0)
    row_h = 32.0
    top_pad = 6.0
    label_w = 70.0
    value_w = 110.0
    half_track = max((width - label_w - value_w - 20.0) / 2.0, 40.0)
    zero_x = label_w + 10.0 + half_track
    height = top_pad * 2 + row_h * len(rows) + 4
    parts: List[str] = [
        _line(zero_x, 2, zero_x, height - 2, stroke="var(--axis)", width=1.5)
    ]
    for i, (label, value) in enumerate(rows):
        y = top_pad + i * row_h
        mid = y + row_h * 0.62
        parts.append(_text(0, mid, label, cls="bar-label"))
        if not _is_finite_number(value):
            parts.append(_text(zero_x + half_track + 8, mid, "—", cls="bar-value"))
            continue
        v = float(value)
        v_clamped = max(-100.0, v)
        frac = _clamp(abs(v_clamped) / span, 0.0, 1.0) * half_track
        color = "#16a34a" if v >= 0 else "#dc2626"
        if v >= 0:
            parts.append(_rect(zero_x, y + 5, frac, row_h - 14, fill=color, rx=4))
        else:
            parts.append(
                _rect(zero_x - frac, y + 5, frac, row_h - 14, fill=color, rx=4)
            )
        if v <= -100.0:
            value_text = f"-100.0{unit} (Ruin)"
        else:
            value_text = f"{v:+.1f}{unit}"
        parts.append(_text(zero_x + half_track + 8, mid, value_text, cls="bar-value"))
    return _svg(width, height, "".join(parts), extra_class="bar-chart")


def _vertical_bars(
    rows: Sequence[Tuple[str, Optional[float]]],
    *,
    width: float = 560.0,
    height: float = 200.0,
    max_value: Optional[float] = None,
    unit: str = "%",
    value_fmt: Optional[Callable[[float], str]] = None,
    colors: Optional[Sequence[str]] = None,
    higher_is_better: bool = False,
) -> str:
    """Simple upward bars for non-negative distributions (drawdown depth by
    percentile, probability-of-profit per horizon, a plain count per bucket
    ...).

    `value_fmt`, when given, replaces the default "{value:.1f}{unit}" label
    text -- e.g. an integer bot count reads far better as "5" than "5.0".

    Colour is either taken verbatim from `colors` (one entry per row, for a
    caller whose bars each carry their OWN fixed meaning -- e.g. a risk-score
    bucket is always the same colour regardless of how many bots happen to
    land in it this run), or else inferred from where the bar's OWN value
    sits relative to `scale_max`, exactly as before this parameter existed.
    `higher_is_better` flips that inferred direction (green-high/red-low
    instead of green-low/red-high) for a metric like "probability of
    profit", where a TALL bar is the good outcome -- the original
    green-low/red-high mapping was written for the opposite case (drawdown
    depth, where a tall bar is bad) and must not be reused unchanged for a
    metric with the opposite polarity.
    """
    values = [v for _, v in rows if _is_finite_number(v)]
    if not values:
        return ""
    scale_max = max_value if max_value is not None else max(max(values), 1.0)
    scale_max = max(scale_max, 1e-9)
    n = len(rows)
    left_pad = 34.0
    bottom_pad = 34.0
    top_pad = 14.0
    plot_w = max(width - left_pad - 10.0, 40.0)
    plot_h = max(height - top_pad - bottom_pad, 40.0)
    gap = plot_w / n
    bar_w = gap * 0.55
    parts: List[str] = [
        _line(left_pad, top_pad, left_pad, top_pad + plot_h, stroke="var(--axis)"),
        _line(
            left_pad,
            top_pad + plot_h,
            left_pad + plot_w,
            top_pad + plot_h,
            stroke="var(--axis)",
        ),
    ]
    for i, (label, value) in enumerate(rows):
        cx = left_pad + gap * i + gap / 2.0
        if _is_finite_number(value):
            v = _clamp(float(value), 0.0, scale_max)
            bar_h = plot_h * (v / scale_max)
            if colors is not None and i < len(colors):
                color = colors[i]
            elif higher_is_better:
                color = (
                    "#dc2626"
                    if v < scale_max * 0.34
                    else ("#ea580c" if v < scale_max * 0.7 else "#16a34a")
                )
            else:
                color = (
                    "#16a34a"
                    if v < scale_max * 0.34
                    else ("#ea580c" if v < scale_max * 0.7 else "#dc2626")
                )
            parts.append(
                _rect(
                    cx - bar_w / 2,
                    top_pad + plot_h - bar_h,
                    bar_w,
                    bar_h,
                    fill=color,
                    rx=3,
                )
            )
            value_text = (
                value_fmt(float(value)) if value_fmt else f"{float(value):.1f}{unit}"
            )
            parts.append(
                _text(
                    cx,
                    top_pad + plot_h - bar_h - 6,
                    value_text,
                    anchor="middle",
                    cls="bar-value-sm",
                )
            )
        else:
            parts.append(
                _text(
                    cx, top_pad + plot_h - 6, "—", anchor="middle", cls="bar-value-sm"
                )
            )
        parts.append(
            _text(cx, top_pad + plot_h + 16, label, anchor="middle", cls="bar-label-sm")
        )
    return _svg(width, height, "".join(parts), extra_class="bar-chart")


# --------------------------------------------------------------------------- #
# Chart: pie -- hand-computed wedges via trigonometry (no library). Used both
# by this module's own win/loss composition charts and by admin_page.py's
# verdict-distribution overview (imported from here rather than duplicated,
# since a pie is exactly the kind of primitive both pages need identically).
# --------------------------------------------------------------------------- #


def _pie_chart(
    slices: Sequence[Tuple[str, Optional[float], str]],
    *,
    width: float = 460.0,
    height: float = 260.0,
    radius: float = 82.0,
) -> str:
    """`slices` is `(label, value, color)` triples. Never raises and never
    emits a malformed wedge, whatever the values look like:

      * A non-finite/negative/missing value is treated as `0.0` -- a slice
        that cannot be measured contributes nothing to the pie rather than
        corrupting the total or the angle math.
      * `sum(values) <= 0` (every slice empty, or `slices` itself empty) has
        no meaningful proportions to draw at all -- rendered as a plain
        outlined circle with a "no data" label instead of a divide-by-zero.
      * A slice occupying the ENTIRE pie (100%) is drawn as a plain
        `<circle>`, not the usual `M/L/A/Z` wedge path: that path formula
        computes its start and end point from the SAME angle when a slice
        spans a full 360 degrees, which collapses the arc to a zero-length
        loop back to itself -- a real but visually empty (and confusing)
        shape, not the solid disc the caller actually means.
      * A slice with a genuine `0` value contributes no wedge geometry at
        all (nothing to draw), but keeps its direct label -- so a category
        that legitimately has zero members (e.g. no bot fell in the
        "DRAWDOWN: LOW · QUALITY: WEAK" state this run) still shows up as
        "0 · 0.0%" rather than
        silently vanishing from the picture, which would look like a bug
        rather than a fact about the data.

    Every slice is labelled directly on the chart, next to its own wedge --
    no separate colour-matching legend, per this project's own design rule
    that a legend the reader has to cross-reference is a lazy substitute for
    a direct label.
    """
    cx, cy = width / 2.0, height / 2.0
    cleaned: List[Tuple[str, float, str]] = []
    for label, value, color in slices:
        v = float(value) if _is_finite_number(value) else 0.0
        cleaned.append((str(label), max(v, 0.0), color))
    total = sum(v for _, v, _ in cleaned)

    if total <= 0:
        body = (
            f'<circle cx="{_coord(cx)}" cy="{_coord(cy)}" r="{_coord(radius)}" '
            'fill="transparent" stroke="var(--track)" stroke-width="2"/>'
            + _text(cx, cy, "No data", anchor="middle", cls="pie-empty")
        )
        return _svg(width, height, body, extra_class="pie-chart")

    def point(angle_deg: float, r: float) -> Tuple[float, float]:
        rad = math.radians(angle_deg - 90.0)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    parts: List[str] = []
    cumulative = 0.0
    for label, value, color in cleaned:
        frac = value / total
        start_angle = cumulative
        end_angle = cumulative + frac * 360.0
        mid_angle = (start_angle + end_angle) / 2.0

        if frac >= 0.999999:
            parts.append(
                f'<circle cx="{_coord(cx)}" cy="{_coord(cy)}" r="{_coord(radius)}" '
                f'fill="{_esc(color)}"/>'
            )
        elif value > 0:
            x1, y1 = point(start_angle, radius)
            x2, y2 = point(end_angle, radius)
            large_arc = 1 if (end_angle - start_angle) > 180.0 else 0
            parts.append(
                f'<path d="M {_coord(cx)},{_coord(cy)} L {_coord(x1)},{_coord(y1)} '
                f"A {_coord(radius)},{_coord(radius)} 0 {large_arc} 1 "
                f'{_coord(x2)},{_coord(y2)} Z" fill="{_esc(color)}"/>'
            )

        lx, ly = point(mid_angle, radius + 34.0)
        anchor = "start" if lx >= cx else "end"
        label_text = label if len(label) <= 22 else label[:21] + "…"
        parts.append(_text(lx, ly - 3, label_text, anchor=anchor, cls="pie-label"))
        parts.append(
            _text(
                lx,
                ly + 11,
                f"{_num(value, 0)} · {frac * 100.0:.1f}%",
                anchor=anchor,
                cls="pie-value",
            )
        )
        cumulative = end_angle

    return _svg(
        width,
        height,
        "".join(parts),
        extra_class="pie-chart",
        aria_label="Pie chart",
    )


# --------------------------------------------------------------------------- #
# Chart: cumulative line -- the "tăng trưởng" chart, plotting a running total
# (vốn tích luỹ) against sequence order (thứ tự lệnh), point by point.
# --------------------------------------------------------------------------- #


def _line_chart(
    ys: Sequence[Any],
    *,
    width: float = 750.0,
    height: float = 460.0,
    y_unit: str = "",
    x_label_prefix: str = "Trade",
    aria_label: str = "Cumulative capital curve by closed trade",
) -> str:
    """Plot `ys` (already the values to draw, e.g. a running cumulative sum
    the caller computed) against a plain 0..n-1 sequence index.

    Degenerate inputs never raise and never produce a malformed chart:

      * No finite points at all -> `""` (caller hides the whole subsection;
        see `_render_growth_curve`'s own "đừng bịa" rule -- there is nothing
        honest to draw).
      * Exactly one point -> a single marker, no line segment (there is no
        second point to draw a segment TO).
      * Every point identical (a flat curve, most commonly an all-zero PnL
        sequence collapsing to a flat cumulative line at 0) -> the normal
        "scale value into the plot height by dividing by (max-min)" step
        would divide by zero; this pads the range symmetrically around the
        shared value first so that division is always by a positive number.
      * All points negative (a bot that has only ever lost money) -> the
        y-range is still anchored to include 0 (see `lo`/`hi` below) so the
        breakeven line stays meaningful context, and the curve simply never
        crosses back above it.
    """
    pts = [float(v) for v in ys if _is_finite_number(v)]
    n = len(pts)
    if n == 0:
        return ""

    left_pad = 95.0
    right_pad = 145.0
    top_pad = 28.0
    bottom_pad = 36.0
    plot_w = max(width - left_pad - right_pad, 40.0)
    plot_h = max(height - top_pad - bottom_pad, 40.0)

    lo = min(min(pts), 0.0)
    hi = max(max(pts), 0.0)
    if hi - lo < 1e-9:
        pad = max(abs(hi), 1.0)
        lo -= pad
        hi += pad

    def xy(i: int, v: float) -> Tuple[float, float]:
        x = left_pad if n == 1 else left_pad + plot_w * (i / (n - 1))
        y = top_pad + plot_h * (1.0 - (v - lo) / (hi - lo))
        return x, y

    zero_y = top_pad + plot_h * (1.0 - (0.0 - lo) / (hi - lo))

    # Gradient hai màu: Trên zero baseline (lãi > 0) màu xanh lá (#10b981),
    # Dưới zero baseline (lỗ < 0) màu đỏ (#ef4444)
    gradient_id = f"pnl-grad-{abs(hash(tuple(pts[:min(len(pts), 8)])))}"
    grad_defs = ""
    if hi > 0.0 and lo < 0.0:
        zero_pct = _clamp(((zero_y - top_pad) / plot_h) * 100.0, 0.0, 100.0)
        grad_defs = (
            f'<defs>'
            f'<linearGradient id="{gradient_id}" x1="0" y1="{_coord(top_pad)}" x2="0" y2="{_coord(top_pad + plot_h)}" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0%" stop-color="#10b981"/>'
            f'<stop offset="{zero_pct:.2f}%" stop-color="#10b981"/>'
            f'<stop offset="{zero_pct:.2f}%" stop-color="#ef4444"/>'
            f'<stop offset="100%" stop-color="#ef4444"/>'
            f'</linearGradient>'
            f'</defs>'
        )
        stroke = f"url(#{gradient_id})"
    elif hi <= 0.0:
        stroke = "#ef4444"
    else:
        stroke = "#10b981"

    parts: List[str] = []
    if grad_defs:
        parts.append(grad_defs)

    # Đường trục zero baseline
    parts.append(
        _line(
            left_pad,
            zero_y,
            left_pad + plot_w,
            zero_y,
            stroke="var(--line-2, #64748b)",
            dash="4,4",
        )
    )
    if abs(zero_y - (top_pad + 4)) > 14 and abs(zero_y - (top_pad + plot_h + 2)) > 14:
        parts.append(
            _text(
                left_pad - 8,
                zero_y + 3,
                f"0{y_unit}",
                anchor="end",
                cls="line-axis-label",
            )
        )

    last_is_profit = pts[-1] >= 0.0
    stroke_last = "#10b981" if last_is_profit else "#ef4444"
    x_last, y_last = xy(n - 1, pts[-1])

    if n == 1:
        parts.append(
            f'<circle cx="{_coord(x_last)}" cy="{_coord(y_last)}" r="5" fill="{stroke_last}"/>'
        )
    else:
        coords = " ".join(
            f"{_coord(x)},{_coord(y)}" for x, y in (xy(i, v) for i, v in enumerate(pts))
        )
        parts.append(
            f'<polyline points="{coords}" fill="transparent" stroke="{stroke}" '
            'stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        x0, y0 = xy(0, pts[0])
        first_color = "#10b981" if pts[0] >= 0.0 else "#ef4444"
        parts.append(
            f'<circle cx="{_coord(x0)}" cy="{_coord(y0)}" r="4" fill="{first_color}"/>'
        )
        parts.append(
            f'<circle cx="{_coord(x_last)}" cy="{_coord(y_last)}" r="5" fill="{stroke_last}"/>'
        )
        peak_i = max(range(n), key=lambda i: pts[i])
        trough_i = min(range(n), key=lambda i: pts[i])
        for i, tag, color in (
            (peak_i, "Peak", "#10b981"),
            (trough_i, "Trough", "#ef4444"),
        ):
            if i == 0 or (i == n - 1 and tag == "Peak"):
                continue
            x, y = xy(i, pts[i])
            parts.append(
                f'<circle cx="{_coord(x)}" cy="{_coord(y)}" r="4" fill="{color}"/>'
            )
            marker_anchor = "middle"
            if x < left_pad + 45.0:
                marker_anchor = "start"
            elif x > left_pad + plot_w - 45.0:
                marker_anchor = "end"

            # Avoid clipping below SVG or above top padding
            if tag == "Trough":
                marker_y = y - 8 if y >= top_pad + plot_h - 14 else y + 16
            else:
                marker_y = y + 16 if y <= top_pad + 14 else y - 8

            parts.append(
                _text(
                    x,
                    marker_y,
                    f"{tag} {pts[i]:,.0f}{y_unit}",
                    anchor=marker_anchor,
                    cls=f"line-marker line-marker-{tag.lower()}",
                    fill=color,
                )
            )

    # Nhãn điểm cuối: đặt tại lề phải ngoài plot, không bao giờ đè lên nhãn Đáy/Đỉnh
    y_end = _clamp(y_last + 4, top_pad + 12, height - bottom_pad - 4)
    end_cls = "line-end-label end-pos" if pts[-1] >= 0.0 else "line-end-label end-neg"
    parts.append(
        _text(
            left_pad + plot_w + 10,
            y_end,
            f"{pts[-1]:,.0f}{y_unit}",
            anchor="start",
            cls=end_cls,
            fill=stroke_last,
        )
    )

    # Nhãn trục Y: đặt bên ngoài bên trái plot với anchor="end", không bao giờ đè vào đường line
    parts.append(
        _text(
            left_pad - 8,
            top_pad + 4,
            f"{hi:,.0f}{y_unit}",
            anchor="end",
            cls="line-axis-label",
        )
    )
    parts.append(
        _text(
            left_pad - 8,
            top_pad + plot_h + 2,
            f"{lo:,.0f}{y_unit}",
            anchor="end",
            cls="line-axis-label",
        )
    )

    # Nhãn trục X: <prefix> #1 và <prefix> #n -- mặc định "Lệnh" (chuỗi lệnh
    # đã chốt), caller truyền `x_label_prefix` khác (vd. "Tuần", "Điểm") khi
    # trục thời gian không phải là các lệnh (xem các mục LIMITED bên dưới,
    # vẽ trên đường vốn tuần / chuỗi pnlRatio công khai thay vì sổ lệnh).
    parts.append(
        _text(
            left_pad,
            height - 6,
            f"{x_label_prefix} #1",
            anchor="start",
            cls="line-axis-label",
        )
    )
    parts.append(
        _text(
            left_pad + plot_w,
            height - 6,
            f"{x_label_prefix} #{n}",
            anchor="end",
            cls="line-axis-label",
        )
    )

    return _svg(
        width,
        height,
        "".join(parts),
        extra_class="line-chart",
        aria_label=aria_label,
    )


# --------------------------------------------------------------------------- #
# Section 1 -- header
# --------------------------------------------------------------------------- #


def _has_score_basis(evidence: Any) -> bool:
    """Liệu mục "Điểm từng chiều rủi ro" (anchor `diem-chieu`) sẽ thực sự
    render nội dung nào đó cho `result` này hay không -- dùng để quyết định
    có gắn dấu `*` bấm được trên các ô điểm số hero hay không (một dấu sao
    dẫn tới một fragment rỗng/không tồn tại còn tệ hơn không có dấu sao).
    Cùng đúng điều kiện `_render_dimensions_section` đã dùng để quyết định
    render hay trả `""`.
    """
    if not isinstance(evidence, dict):
        return False
    dimensions = evidence.get("dimensions")
    if isinstance(dimensions, dict) and dimensions:
        return True
    components = evidence.get("components")
    return isinstance(components, list) and bool(components)


def _render_hero_scores(result: Dict[str, Any]) -> str:
    risk = result.get("risk")
    quality = result.get("quality")
    confidence = result.get("confidence")
    verdict_basis = result.get("verdict_basis")

    has_basis = _has_score_basis(result.get("evidence"))
    tiles = [
        _stat_tile(
            "Risk score (lower = better)",
            _num(risk, 0),
            color=_risk_color(risk),
            size="hero",
            info_key="risk_score",
            basis_anchor="giai-thich-risk" if has_basis and risk is not None else None,
        ),
        _stat_tile(
            "Quality score",
            _num(quality, 0),
            color=_higher_is_better_color(quality),
            size="hero",
            info_key="quality_score",
            basis_anchor=(
                "giai-thich-quality" if has_basis and quality is not None else None
            ),
        ),
        _stat_tile(
            "Confidence",
            _pct(confidence, 0),
            color=_higher_is_better_color(confidence),
            size="hero",
            info_key="confidence",
            basis_anchor=(
                "giai-thich-confidence"
                if has_basis and confidence is not None
                else None
            ),
        ),
    ]

    veto_notice = ""
    score_breakdown = ((result.get("evidence") or {}).get("score_breakdown")) or {}
    decided_by = score_breakdown.get("decided_by")
    veto_reasons = score_breakdown.get("veto_reasons") or []
    if decided_by and decided_by != "WEIGHTED_AVERAGE":
        avg = score_breakdown.get("weighted_average")
        reason_text = "; ".join(_esc(r) for r in veto_reasons) if veto_reasons else ""
        kind = (
            "emergency rule (EMERGENCY_OVERRIDE)"
            if decided_by == "EMERGENCY_OVERRIDE"
            else "exchange veto (VETO_FLOOR)"
        )
        veto_notice = (
            '<div class="notice notice-danger">'
            f"<strong>Risk score {_num(risk, 0)} is NOT the average of the 10 dimensions</strong> "
            f"-- decided instead by the {kind}"
            + (
                f", the actual weighted average is only {_num(avg, 1)}"
                if avg is not None
                else ""
            )
            + "."
            + (f" Reason for the veto: {reason_text}." if reason_text else "")
            + "</div>"
        )

    limited_notice = ""
    if result.get("status") == "LIMITED":
        reason = (
            result.get("limited_reason") or "OKX does not publicly expose enough data for this bot"
        )
        unavailable = result.get("unavailable") or []
        unavailable_vi = ", ".join(_esc(u) for u in unavailable)
        limited_notice = (
            '<div class="notice notice-warning">'
            f"<strong>LIMITED ASSESSMENT</strong> -- {_esc(reason)}."
            + (
                f" Could not be computed: {unavailable_vi}. The confidence ceiling has"
                " been lowered because no per-trade-level evidence is available at all."
                if unavailable_vi
                else ""
            )
            + "</div>"
        )

    verdict_basis_html = (
        '<div class="verdict-basis collapsible-basis" id="verdict-basis-box">'
        '<div class="basis-header" onclick="var b=document.getElementById(\'verdict-basis-box\');if(b){b.classList.toggle(\'expanded\');var p=b.querySelector(\'.basis-toggle-pill\');if(p){p.textContent=b.classList.contains(\'expanded\')?\'Collapse ▲\':\'Show methodology ▼\';}}">'
        '<div class="basis-title-group">'
        '<span class="basis-icon-badge">📐</span>'
        "<div>"
        '<div class="basis-main-title">QUANTITATIVE METHODOLOGY BASIS</div>'
        '<div class="basis-subtitle">Independent mathematical model &middot; 4 pillars of algorithmic risk validation</div>'
        "</div>"
        "</div>"
        '<div class="basis-toggle-action">'
        '<span class="basis-academic-tag">NoraBT Quantitative Assessment Standard</span>'
        '<span class="basis-toggle-pill">Show methodology ▼</span>'
        "</div>"
        "</div>"
        '<div class="basis-collapsible-body">'
        '<div class="basis-pillars-grid">'
        '<div class="basis-pillar-card">'
        '<div class="pillar-top">'
        '<span class="pillar-badge pillar-blue">10,000 SCENARIOS</span>'
        '<span class="pillar-tag">Non-parametric</span>'
        "</div>"
        '<div class="pillar-name">Stationary Bootstrap</div>'
        '<div class="pillar-desc">Simulates 10,000 scenarios (Politis &amp; Romano, 1994) on the bot\'s own closed trade ledger -- preserves the sequence\'s autocorrelation structure instead of assuming a normal distribution.</div>'
        "</div>"
        '<div class="basis-pillar-card">'
        '<div class="pillar-top">'
        '<span class="pillar-badge pillar-amber">VaR 95% &amp; CVaR</span>'
        '<span class="pillar-tag">Tail risk</span>'
        "</div>"
        '<div class="pillar-name">Expected Shortfall</div>'
        '<div class="pillar-desc">Tail risk measured with 95% VaR and CVaR (expected shortfall) to catch stress scenarios that lead to extreme liquidation.</div>'
        "</div>"
        '<div class="basis-pillar-card">'
        '<div class="pillar-top">'
        '<span class="pillar-badge pillar-purple">PSR &amp; DSR</span>'
        '<span class="pillar-tag">Bias correction</span>'
        "</div>"
        '<div class="pillar-name">Deflated Sharpe Ratio</div>'
        '<div class="pillar-desc">Sharpe quality measured with the Probabilistic Sharpe Ratio and Deflated Sharpe Ratio (Bailey and L&oacute;pez de Prado, 2012 and 2014) -- corrected for false-edge inflation, alongside the Minimum Track Record Length.</div>'
        "</div>"
        '<div class="basis-pillar-card">'
        '<div class="pillar-top">'
        '<span class="pillar-badge pillar-green">SPEARMAN &rho; = 0.64</span>'
        '<span class="pillar-tag">Out-of-sample validation</span>'
        "</div>"
        '<div class="pillar-name">36-Bot Empirical Study</div>'
        '<div class="pillar-desc">The Spearman rank correlation between the risk score and subsequent drawdown is 0.64 (95% confidence interval [0.39-0.80]). The score does NOT forecast profit or loss.</div>'
        "</div>"
        "</div>"
        '<div class="basis-verbatim-card">'
        '<div class="verbatim-header">'
        '<span class="verbatim-dot"></span>'
        '<span class="verbatim-label">Full academic basis text:</span>'
        "</div>"
        f'<div class="basis-text">{_esc(verdict_basis)}</div>'
        "</div>"
        "</div>"
        "</div>"
        if verdict_basis
        else ""
    )
    notices_html = (
        f'<div class="header-notices">{veto_notice}{limited_notice}{verdict_basis_html}</div>'
        if (verdict_basis_html or limited_notice or veto_notice)
        else ""
    )
    return f'<div class="report-hero-scores">{"".join(tiles)}</div>{notices_html}'


def _render_header(result: Dict[str, Any]) -> Tuple[str, str]:
    name = result.get("name") or result.get("code") or "Bot"
    code = result.get("code") or ""
    verdict = result.get("verdict")
    verdict_color = _verdict_color(verdict)

    symbol = (result.get("evidence") or {}).get("traded_symbol") or (
        result.get("market_analysis") or {}
    ).get("symbol")
    venue = (result.get("market_analysis") or {}).get("venue_type") or "CEX"
    market_tag = (
        f' · <span class="venue-symbol-badge">⚡ {_esc(symbol)} ({_esc(venue)})</span>'
        if symbol
        else ""
    )

    crumb_html = (
        f'<div class="crumb">REPORT / {_esc(code)}</div>'
        if code
        else '<div class="crumb">REPORT</div>'
    )
    subnav_html = (
        '<div class="report-subnav-bar">'
        '<a href="/#/admin?tab=bots" class="btn-subnav-back">'
        '<span class="back-arrow">←</span>'
        "<span>Back to bot list</span>"
        "</a>"
        '<div class="subnav-crumb">'
        '<span class="crumb-dim">Monitoring system</span>'
        '<span class="crumb-sep">/</span>'
        '<a href="/#/admin?tab=bots" class="crumb-link">Bot list</a>'
        '<span class="crumb-sep">/</span>'
        f'<span class="crumb-active">{_esc(name)}</span>'
        "</div>"
        "</div>"
    )
    main_header = (
        f"{subnav_html}"
        '<header class="report-header report-hero-card">'
        '<div class="report-hero-top">'
        '<div class="report-hero-identity">'
        f"{crumb_html}"
        f'<h1 class="head-title">{_esc(name)}</h1>'
        '<div class="report-hero-meta">'
        f'<span class="bot-code-pill">Code: <code>{_esc(code)}</code></span>'
        f"{market_tag}"
        f'<span class="verdict-badge" style="--badge-color:{verdict_color}">{_esc(verdict or "INSUFFICIENT EVIDENCE")}</span>'
        "</div>"
        "</div>"
        "</div>"
        "</header>"
    )
    side_blocks = (
        '<div class="side-identity-block">'
        f'<span class="verdict-badge" style="--badge-color:{verdict_color}">{_esc(verdict or "INSUFFICIENT EVIDENCE")}</span>'
        "</div>"
    )
    return main_header, side_blocks


def _risk_color(risk: Any) -> str:
    if not _is_finite_number(risk):
        return "#6b7280"
    v = float(risk)
    if v >= 85:
        return "#7f1d1d"
    if v >= 70:
        return "#dc2626"
    if v >= 50:
        return "#ea580c"
    if v >= 30:
        return "#ca8a04"
    return "#16a34a"


def _higher_is_better_color(value: Any) -> str:
    """Màu cho một chỉ số mà CÀNG CAO CÀNG TỐT (điểm chất lượng, độ tin cậy
    đánh giá) -- ảnh chụp trang thật cho thấy 2/3 ô số liệu quan trọng nhất
    trang (chỉ có ô "Điểm rủi ro" tô màu qua `_risk_color`) trông đen trơn,
    không phân cấp, dù cùng là những con số quan trọng nhất trang. Cùng bảng
    màu 4 mốc với `_risk_color` (khác polarity: thấp = xấu/đỏ ở đây thay vì
    cao = xấu/đỏ như risk) để một người đọc quen mắt với ý nghĩa xanh/đỏ trên
    trang này không phải học thêm một bảng màu khác.
    """
    if not _is_finite_number(value):
        return "#6b7280"
    v = float(value)
    if v >= 75:
        return "#16a34a"
    if v >= 50:
        return "#ca8a04"
    if v >= 25:
        return "#ea580c"
    return "#dc2626"


# --------------------------------------------------------------------------- #
# Section 2 -- conclusion / recommendation
# --------------------------------------------------------------------------- #


_CONCLUSION_WHY_PREFIX = "WHY THIS HAPPENED:"
_CONCLUSION_PROOF_PREFIX = "EVIDENCE:"
_CONCLUSION_VERDICT_PREFIX = "CONCLUSION:"


def _format_verdict_headline(headline: str) -> str:
    """Highlight risk verdict values (e.g. HIGH, WEAK, LOW, GOOD) with soft warning badges on hover."""
    if not headline:
        return ""
    pattern = r'\b(HIGH|WEAK|LOW|GOOD|ELEVATED|ACCEPTABLE|VETO|DANGER|MODERATE|ROBUST|SAFE|WARNING)\b'
    parts = []
    last_end = 0
    for m in re.finditer(pattern, headline, flags=re.IGNORECASE):
        parts.append(_esc(headline[last_end:m.start()]))
        word = m.group(0)
        u = word.upper()
        if u in ("HIGH", "DANGER", "VETO"):
            badge_cls = "badge-high"
        elif u in ("WEAK", "ELEVATED", "WARNING", "CAUTION"):
            badge_cls = "badge-weak"
        elif u in ("LOW", "GOOD", "ROBUST", "SAFE"):
            badge_cls = "badge-low"
        else:
            badge_cls = "badge-acceptable"
        parts.append(f'<span class="verdict-val-badge {badge_cls}">{_esc(word)}</span>')
        last_end = m.end()
    parts.append(_esc(headline[last_end:]))
    return "".join(parts)


def _detect_quant_tag(text: str) -> str:
    u = text.upper()
    if "PROFIT FACTOR" in u:
        return "[PROFIT FACTOR]"
    elif "UNREALISED LOSS" in u or "UNREALIZED LOSS" in u or "OPEN LOSS" in u:
        return "[UNREALISED LOSS]"
    elif "VETO FLOOR" in u:
        return "[RISK VETO FLOOR]"
    elif "RISK SCORE" in u:
        return "[RISK DRIVERS]"
    elif "MONTE CARLO" in u:
        return "[MONTE CARLO]"
    elif "TAIL RISK" in u or "TAIL LOSS" in u or "SIMULATED TAIL" in u:
        return "[TAIL RISK]"
    elif "PAYOFF" in u or "WIN RATE" in u or "WINNING TRADES" in u:
        return "[PAYOFF ASYMMETRY]"
    elif "NEVER TESTED" in u or "DOWNTREND" in u:
        return "[REGIME BIAS]"
    elif "DRAWDOWN" in u or "SHARPE" in u:
        return "[DRAWDOWN / SHARPE]"
    elif "STRESS SCENARIO" in u or "STRESS TEST" in u:
        return "[STRESS TEST]"
    elif "DEFLATED SHARPE" in u:
        return "[DEFLATED SHARPE]"
    return "[AUDIT LOG]"


def _split_quant_consequence(text: str) -> Tuple[str, Optional[str]]:
    # 1. " — " em dash or hyphen separator
    if " — " in text:
        main, cons = text.split(" — ", 1)
        return main.strip(), cons.strip()
    # 2. " → one losing trade..." or " → winning trades..."
    if " → one losing trade" in text:
        main, cons = text.split(" → ", 1)
        return main.strip(), cons.strip()
    if " → winning trades are" in text:
        main, cons = text.split(" → ", 1)
        return main.strip(), cons.strip()
    # 3. Veto floor with ": destructive trading behaviour"
    if "): " in text and "veto floor" in text.lower():
        main, cons = text.split("): ", 1)
        return (main + ")").strip(), cons.strip()
    return text.strip(), None


def _highlight_quant_numbers(raw_text: str) -> str:
    """Highlight numbers, USDT values, negative percentages in quant terminal text."""
    pattern = r'([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*%|\s*USDT)?)'
    tokens = []
    last_idx = 0
    for m in re.finditer(pattern, raw_text):
        val = m.group(0)
        start, end = m.start(), m.end()
        if not re.search(r'\d', val):
            continue
        prefix = raw_text[last_idx:start]
        tokens.append(_esc(prefix))

        val_clean = val.strip()
        is_neg = val_clean.startswith("-") or ("loss" in prefix.lower() and "%" in val_clean)
        is_warn = val_clean in ("97%", "100%", "88") or ("ruin" in prefix.lower())

        if is_neg:
            tokens.append(f'<span class="quant-num quant-num-neg">{_esc(val)}</span>')
        elif is_warn:
            tokens.append(f'<span class="quant-num quant-num-warn">{_esc(val)}</span>')
        else:
            tokens.append(f'<span class="quant-num">{_esc(val)}</span>')
        last_idx = end
    tokens.append(_esc(raw_text[last_idx:]))
    return "".join(tokens)


def _render_quant_terminal_evidence(proof_items: List[str]) -> str:
    """Render quantitative evidence as an Audit Log / Quant Terminal Text View."""
    if not proof_items:
        return ""
    rows = []
    for item in proof_items:
        tag = _detect_quant_tag(item)
        main_text, cons_text = _split_quant_consequence(item)
        main_html = _highlight_quant_numbers(main_text)

        cons_html = ""
        if cons_text:
            if cons_text and cons_text[0].islower() and not cons_text.startswith("http"):
                cons_disp = cons_text[0].upper() + cons_text[1:]
            else:
                cons_disp = cons_text
            cons_body = _highlight_quant_numbers(cons_disp)
            cons_html = (
                f'<div class="quant-audit-consequence">'
                f'<span class="quant-consequence-arrow">↳</span> '
                f'<span class="quant-consequence-text">{cons_body}</span>'
                f'</div>'
            )

        rows.append(
            f'<div class="quant-audit-row">'
            f'<div class="quant-audit-tag">{_esc(tag)}</div>'
            f'<div class="quant-audit-body">'
            f'<div class="quant-audit-main">{main_html}</div>'
            f'{cons_html}'
            f'</div>'
            f'</div>'
        )

    return (
        '<div class="quant-audit-terminal">'
        '<div class="quant-terminal-divider"></div>'
        f'<div class="quant-audit-rows">{"".join(rows)}</div>'
        '<div class="quant-terminal-divider"></div>'
        '</div>'
    )


def _render_quick_risk_strip(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    perf = evidence.get("performance")
    if not isinstance(perf, dict):
        perf = {}
    metrics = evidence.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    loss_prof = compute_loss_profile(evidence)
    if not isinstance(loss_prof, dict):
        loss_prof = {}

    # 1. Reference Capital
    capital = loss_prof.get("capital")
    if not _is_finite_number(capital):
        capital = evidence.get("capital") or perf.get("capital")
    if _is_finite_number(capital) and float(capital) > 0:
        cap_val = float(capital)
        cap_text = f"{cap_val:,.0f} USDT" if cap_val >= 1000 else f"{cap_val:.2f} USDT"
    else:
        cap_text = "—"

    # 2. Unrealised Float PnL
    open_loss = perf.get("open_loss")
    open_loss_pct = perf.get("open_loss_to_capital_pct")
    if _is_finite_number(open_loss_pct):
        float_pct = float(open_loss_pct) * 100.0 if abs(float(open_loss_pct)) <= 1.0 else float(open_loss_pct)
        float_cls = "qrs-danger" if float_pct < 0 else "qrs-safe"
        float_text = f"{float_pct:+.1f}%"
        if _is_finite_number(open_loss):
            float_text += f" ({_money(open_loss)})"
    elif _is_finite_number(open_loss):
        val_ol = float(open_loss)
        float_cls = "qrs-danger" if val_ol < 0 else "qrs-safe"
        float_text = _money(open_loss)
    else:
        open_pos = perf.get("open_positions")
        if open_pos == 0:
            float_cls = "qrs-safe"
            float_text = "0.0% (Clean)"
        else:
            float_cls = "qrs-neutral"
            float_text = "—"

    # 3. Max Drawdown
    deepest_ep = loss_prof.get("deepest_episode")
    deepest_ep = deepest_ep if isinstance(deepest_ep, dict) else {}
    depth_pct = deepest_ep.get("depth_pct")
    depth_abs = deepest_ep.get("depth_abs")
    if _is_finite_number(depth_pct):
        dd_val = float(depth_pct)
        dd_cls = "qrs-danger" if dd_val >= 20.0 else ("qrs-warn" if dd_val >= 10.0 else "qrs-safe")
        dd_text = f"-{dd_val:.1f}%"
    elif _is_finite_number(depth_abs):
        dd_cls = "qrs-danger" if float(depth_abs) > 0 else "qrs-safe"
        dd_text = f"-{_money(depth_abs)}"
    else:
        m_dd = metrics.get("max_drawdown") or perf.get("max_drawdown")
        if _is_finite_number(m_dd):
            val = float(m_dd) * 100.0 if float(m_dd) <= 1.0 else float(m_dd)
            dd_cls = "qrs-danger" if val >= 20.0 else "qrs-warn"
            dd_text = f"-{val:.1f}%"
        else:
            dd_cls = "qrs-neutral"
            dd_text = "—"

    # 4. Win Rate
    win_rate = metrics.get("win_rate") or perf.get("win_rate")
    if _is_finite_number(win_rate):
        wr_val = float(win_rate) * 100.0 if float(win_rate) <= 1.0 else float(win_rate)
        wr_cls = "qrs-safe" if wr_val >= 50.0 else "qrs-warn"
        wr_text = f"{wr_val:.1f}%"
    else:
        wr_cls = "qrs-neutral"
        wr_text = "—"

    # 5. Observed trades
    sample_count = result.get("trade_count") or perf.get("trade_count") or perf.get("closed_trades_count")
    if not _is_finite_number(sample_count):
        trades = loss_prof.get("trades") or []
        sample_count = len(trades) if trades else None
    if _is_finite_number(sample_count) and float(sample_count) > 0:
        sample_text = f"{int(float(sample_count)):,} trades"
        sample_cls = "qrs-safe" if int(float(sample_count)) >= 50 else "qrs-warn"
    else:
        sample_text = "—"
        sample_cls = "qrs-neutral"

    return (
        f'<div class="quick-risk-strip">'
        f'<div class="qrs-item">'
        f'<span class="qrs-label">Reference Capital</span>'
        f'<span class="qrs-value">{_esc(cap_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {float_cls}">'
        f'<span class="qrs-label">Unrealised Loss (Float)</span>'
        f'<span class="qrs-value">{_esc(float_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {dd_cls}">'
        f'<span class="qrs-label">Max Drawdown</span>'
        f'<span class="qrs-value">{_esc(dd_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {wr_cls}">'
        f'<span class="qrs-label">Win Rate</span>'
        f'<span class="qrs-value">{_esc(wr_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {sample_cls}">'
        f'<span class="qrs-label">Observed Trades</span>'
        f'<span class="qrs-value">{_esc(sample_text)}</span>'
        f'</div>'
        f'</div>'
    )


def _render_conclusion(result: Dict[str, Any]) -> str:
    """Trình bày mục "Kết luận và khuyến nghị" theo cấu trúc chuẩn đồng nhất
    với hệ thống:
      - Khối phán quyết nổi bật, sắc nét, tương ứng mức độ rủi ro (tone-danger / warning / success)
      - Dòng tóm tắt định danh và các chỉ số đo lường cốt lõi
      - Danh sách nguyên nhân và bằng chứng định lượng chuẩn mực
      - Cảnh báo rủi ro tiềm ẩn (notice-danger)
      - Khối lưu ý phạm vi kiểm định & thiếu dữ liệu gọn gàng.
    """
    text_lines = result.get("text")
    if not isinstance(text_lines, list) or not text_lines:
        return ""

    verdict_info = None
    why_items: List[str] = []
    proof_items: List[str] = []
    warning_items: List[str] = []
    limitation_items: List[str] = []
    overview_parts: List[str] = []
    other_lines: List[str] = []

    for raw_line in text_lines:
        if not isinstance(raw_line, str) or not raw_line.strip():
            continue
        line = raw_line.strip()
        line = re.sub(r"^([^\(\)]+?)\s*\(\1\)", r"\1", line)
        upper = line.upper()

        if line.startswith(("• ", "- ", "* ")):
            proof_items.append(line[2:].strip())
            continue

        if upper.startswith(_CONCLUSION_VERDICT_PREFIX) or upper.startswith("KẾT LUẬN:"):
            rest = line[line.index(":") + 1 :].strip()
            if " — " in rest:
                headline, detail = rest.split(" — ", 1)
            else:
                headline, detail = rest, ""
            verdict_info = (headline.strip(), detail.strip())
        elif upper.startswith(_CONCLUSION_WHY_PREFIX) or upper.startswith("NGUYÊN NHÂN:"):
            prefix_len = (
                len(_CONCLUSION_WHY_PREFIX)
                if upper.startswith(_CONCLUSION_WHY_PREFIX)
                else len("NGUYÊN NHÂN:")
            )
            rest = line[prefix_len:].strip()
            subs = [s.strip() for s in rest.split(";") if s.strip()]
            why_items.extend(subs if subs else [rest])
        elif upper.startswith(_CONCLUSION_PROOF_PREFIX) or upper.startswith("CHỨNG MINH"):
            continue
        elif upper.startswith("CẢNH BÁO ẨN:") or upper.startswith("CẢNH BÁO RỦI RO:"):
            rest = line[line.index(":") + 1 :].strip()
            subs = [s.strip() for s in rest.split(";") if s.strip()]
            warning_items.extend(subs if subs else [rest])
        elif upper.startswith("GIỚI HẠN DỮ LIỆU:") or upper.startswith("GIỚI HẠN:"):
            rest = line[line.index(":") + 1 :].strip()
            subs = [s.strip() for s in rest.split(";") if s.strip()]
            limitation_items.extend(subs if subs else [rest])
        elif (" — " in line and ("giao dịch " in line or "lệnh đã chốt" in line)) or (
            "Điểm rủi ro " in line and "/100" in line
        ) or ("độ tin cậy" in line.lower()):
            overview_parts.append(line)
        else:
            other_lines.append(line)

    blocks: List[str] = []

    # 1. Prominent Verdict Box with Action Directive
    verdict_detail = ""
    if verdict_info:
        headline, detail = verdict_info
        verdict_detail = detail.strip()
        is_veto = "VETO" in headline.upper()
        upper = headline.upper()
        is_danger = "DRAWDOWN: HIGH" in upper or "HIDDEN RISK" in upper
        verdict_cls = (
            "danger"
            if (is_veto or is_danger)
            else ("warning" if "CẢNH BÁO" in headline.upper() else "success")
        )

        formatted_headline = _format_verdict_headline(headline)

        if verdict_cls == "danger":
            action_directive = (
                '<div class="verdict-action-callout action-danger">'
                '<div class="action-callout-badge">ACTION DIRECTIVE: DO NOT ALLOCATE CAPITAL</div>'
                '<p class="action-callout-desc">Potential investors: do not copy this bot. Existing followers: consider stopping copy-trading and closing open positions immediately to prevent severe liquidation.</p>'
                '</div>'
            )
        elif verdict_cls == "warning":
            action_directive = (
                '<div class="verdict-action-callout action-warning">'
                '<div class="action-callout-badge">ACTION DIRECTIVE: ELEVATED CAUTION / STRICT SIZE CAP</div>'
                '<p class="action-callout-desc">Bot shows elevated tail risk or thin sample validity. Maintain strict stop-loss discipline and restrict allocation to minimal exploratory sizing.</p>'
                '</div>'
            )
        else:
            action_directive = (
                '<div class="verdict-action-callout action-success">'
                '<div class="action-callout-badge">ACTION DIRECTIVE: STANDARD ALLOCATION</div>'
                '<p class="action-callout-desc">Risk parameters within normal operational boundaries. Maintain standard portfolio risk limits and monitor drawdown progression.</p>'
                '</div>'
            )

        # Crisp, clean verdict box: chip headline + action directive (detail moved to QUANTITATIVE EVIDENCE)
        blocks.append(
            f'<div class="conclusion-verdict-box tone-{verdict_cls}">'
            f'<div class="verdict-header-line">'
            f'<span class="verdict-chip">{formatted_headline}</span>'
            f'</div>'
            f'{action_directive}'
            f'</div>'
        )

    # 2. Hero Scores & System Theory Description (Quantitative Methodology Basis)
    scores_and_basis_html = _render_hero_scores(result)
    if scores_and_basis_html:
        blocks.append(f'<div class="conclusion-scores-wrapper">{scores_and_basis_html}</div>')

    # 2b. Quick Risk Metrics Strip (Reference capital, float PnL, max DD, win rate, sample size)
    quick_strip_html = _render_quick_risk_strip(result)
    if quick_strip_html:
        blocks.append(quick_strip_html)

    # Sample count — moved into QUANTITATIVE EVIDENCE below
    evidence = result.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    performance = evidence.get("performance")
    performance = performance if isinstance(performance, dict) else {}
    sample_count = result.get("trade_count") or performance.get("trade_count")

    # 3. Why / Causes
    if why_items:
        items_html = "".join(f"<li>{_esc(w)}</li>" for w in why_items)
        blocks.append(
            '<div class="conclusion-section-block">'
            '<div class="conclusion-sub-title">WHY</div>'
            f'<ul class="findings">{items_html}</ul>'
            '</div>'
        )

    # 4. Proof / Quantitative Evidence (Terminal View)
    # Includes: scorecard chips, narrative paragraph (from verdict detail / other_lines), revisit banner, audit log
    has_quant_content = bool(proof_items or overview_parts or other_lines or verdict_detail)
    if has_quant_content:
        quant_evidence_html = _render_quant_terminal_evidence(proof_items) if proof_items else ""

        # ── Top scorecard: key scores + simulated drawdown + ruin + confidence ──
        _q = result.get("quality")
        _r = result.get("risk")
        _cf = result.get("confidence")
        _mc = result.get("mc") if isinstance(result.get("mc"), dict) else {}
        _hz_scenarios = _mc.get("horizon_scenarios")
        _med_dd = None
        if isinstance(_hz_scenarios, list):
            for _s in _hz_scenarios:
                if isinstance(_s, dict) and _s.get("label") == "MEDIUM":
                    _med_dd = _s.get("median_max_drawdown")
                    break
        _dd_val = _med_dd if _is_finite_number(_med_dd) else _mc.get("median_max_drawdown")
        _ruin_val = _mc.get("probability_of_ruin") if _is_finite_number(_mc.get("probability_of_ruin")) else _mc.get("p_ruin")

        # Fallback extract from verdict_detail if not provided in result dict
        if not _is_finite_number(_q) and verdict_detail:
            m = re.search(r'(?:quality|chất lượng|điểm chất lượng)\s*:?\s*(\d+(?:\.\d+)?)\s*/\s*100', verdict_detail, re.IGNORECASE)
            if m:
                _q = float(m.group(1))
        if not _is_finite_number(_r) and verdict_detail:
            m = re.search(r'(?:risk|rủi ro|điểm rủi ro)\s*:?\s*(\d+(?:\.\d+)?)\s*/\s*100', verdict_detail, re.IGNORECASE)
            if m:
                _r = float(m.group(1))
        if not _is_finite_number(_cf) and verdict_detail:
            m = re.search(r'(?:confidence|độ tin cậy)\s*(?:in this assessment itself is only)?\s*:?\s*(\d+(?:\.\d+)?)%', verdict_detail, re.IGNORECASE)
            if m:
                _cf = float(m.group(1))
        if not _is_finite_number(_dd_val) and verdict_detail:
            m = re.search(r'(?:simulated\s+p95\s+drawdown|drawdown|sụt giảm)\s*:?\s*(\d+(?:\.\d+)?)%', verdict_detail, re.IGNORECASE)
            if m:
                _dd_val = float(m.group(1))
        if not _is_finite_number(_ruin_val) and verdict_detail:
            m = re.search(r'(\d+(?:\.\d+)?)%\s+of\s+simulations\s+wipe\s+out\s+capital', verdict_detail, re.IGNORECASE)
            if not m:
                m = re.search(r'probability\s+of\s+ruin\s*:?\s*(\d+(?:\.\d+)?)%', verdict_detail, re.IGNORECASE)
            if m:
                _ruin_val = float(m.group(1))

        def _qe_chip(label: str, value: str, cls: str) -> str:
            return (
                f'<div class="qe-chip {cls}">'
                f'<span class="qe-chip-label">{_esc(label)}</span>'
                f'<span class="qe-chip-value">{_esc(value)}</span>'
                f'</div>'
            )

        chips = []
        if _is_finite_number(_q):
            qv = float(_q)
            q_cls = "qe-chip-good" if qv >= 60 else ("qe-chip-warn" if qv >= 35 else "qe-chip-bad")
            chips.append(_qe_chip("Quality", f"{int(round(qv))}/100", q_cls))
        if _is_finite_number(_r):
            rv = float(_r)
            r_cls = "qe-chip-bad" if rv >= 70 else ("qe-chip-warn" if rv >= 40 else "qe-chip-good")
            chips.append(_qe_chip("Risk", f"{int(round(rv))}/100", r_cls))
        if _is_finite_number(_dd_val):
            dv = float(_dd_val)
            dd_cls = "qe-chip-bad" if dv >= 20 else ("qe-chip-warn" if dv >= 10 else "qe-chip-good")
            chips.append(_qe_chip("Sim. Max DD (med)", f"-{dv:.1f}%", dd_cls))
        if _is_finite_number(_ruin_val):
            ruin_num = float(_ruin_val)
            ruin_pct = ruin_num * 100.0 if (0.0 < ruin_num <= 1.0) else ruin_num
            if ruin_pct > 0:
                ruin_cls = "qe-chip-bad" if ruin_pct >= 10 else "qe-chip-warn"
                chips.append(_qe_chip("Ruin Prob.", f"{ruin_pct:.0f}%", ruin_cls))
            else:
                chips.append(_qe_chip("Ruin Prob.", "0% (Safe Floor)", "qe-chip-good"))
        if _is_finite_number(_cf):
            cfv = float(_cf) * 100.0 if float(_cf) <= 1.0 else float(_cf)
            cf_cls = "qe-chip-good" if cfv >= 70 else ("qe-chip-warn" if cfv >= 45 else "qe-chip-bad")
            chips.append(_qe_chip("Confidence", f"{int(round(cfv))}%", cf_cls))
        # Sample size chip
        if _is_finite_number(sample_count) and float(sample_count) > 0:
            n = int(float(sample_count))
            s_cls = "qe-chip-good" if n >= 50 else "qe-chip-warn"
            chips.append(
                f'<div class="qe-chip {s_cls}">'
                f'<span class="qe-chip-label">Sample</span>'
                f'<span class="qe-chip-value">{n:,} trades</span>'
                f'<span style="display:none">SAMPLE: {n:,} TRADES</span>'
                f'</div>'
            )

        scorecard_html = (
            f'<div class="qe-scorecard">{"".join(chips)}</div>'
            if chips else ""
        )

        # ── Parse verdict_detail for narrative & revisit condition ──────────
        revisit_text = ""
        cleaned_narrative = verdict_detail

        # Extract revisit condition
        m_revisit = re.search(r'(?:Condition to revisit|Revisit when|Điều kiện xem lại):\s*(.+?)(?=\.\s+[A-Z]|$)', cleaned_narrative, re.IGNORECASE)
        if m_revisit:
            revisit_text = m_revisit.group(0).strip()
            cleaned_narrative = cleaned_narrative.replace(revisit_text, "").strip()

        # Clean out leading quality/risk text and confidence note from the narrative prose
        cleaned_narrative = re.sub(r'^(?:quality|chất lượng|điểm chất lượng)\s*:?\s*\d+(?:\.\d+)?/100[,\.]\s*(?:risk|rủi ro|điểm rủi ro)\s*:?\s*\d+(?:\.\d+)?/100\.?\s*', '', cleaned_narrative, flags=re.IGNORECASE)
        cleaned_narrative = re.sub(r'Confidence\s+in\s+this\s+assessment\s+itself\s+is\s+only\s+\d+(?:\.\d+)?%\.?', '', cleaned_narrative, flags=re.IGNORECASE)
        cleaned_narrative = re.sub(r'Độ tin cậy\s+của\s+đánh giá\s+chỉ\s+khoảng\s+\d+(?:\.\d+)?%\.?', '', cleaned_narrative, flags=re.IGNORECASE)
        cleaned_narrative = re.sub(r'\s{2,}', ' ', cleaned_narrative).strip(' .')
        if cleaned_narrative:
            cleaned_narrative = cleaned_narrative + "."

        narrative_lines: List[str] = []
        if cleaned_narrative:
            narrative_lines.append(cleaned_narrative)
        for ol in overview_parts:
            ls = ol.strip()
            if ls and ls not in narrative_lines:
                narrative_lines.append(ls)
        for ol in other_lines:
            ls = ol.strip()
            if ls and ls not in narrative_lines:
                narrative_lines.append(ls)

        narrative_html = ""
        if narrative_lines:
            combined = " ".join(narrative_lines)
            narrative_html = f'<div class="qe-narrative">{_esc(combined)}</div>'

        revisit_html = ""
        if revisit_text:
            parts = revisit_text.split(":", 1)
            tag = parts[0].strip().upper()
            body = parts[1].strip() if len(parts) > 1 else ""
            revisit_html = (
                f'<div class="qe-revisit-banner">'
                f'<span class="qe-revisit-tag">{_esc(tag)}</span>'
                f'<span class="qe-revisit-text">{_esc(body)}</span>'
                f'</div>'
            )

        blocks.append(
            '<div class="conclusion-section-block conclusion-quant-evidence-block">'
            '<div class="conclusion-sub-title">QUANTITATIVE EVIDENCE</div>'
            f'{scorecard_html}'
            f'{narrative_html}'
            f'{revisit_html}'
            f'{quant_evidence_html}'
            '</div>'
        )


    # 5. Hidden Warnings
    if warning_items:
        items_html = "".join(f"<li>{_esc(w)}</li>" for w in warning_items)
        blocks.append(
            '<div class="notice notice-danger">'
            '<strong>Hidden risk warning:</strong>'
            f'<ul class="findings">{items_html}</ul>'
            '</div>'
        )

    # 7. Limitations & Missing Data Notes
    limitation_html = ""

    if limitation_items:
        badge_text = f"{len(limitation_items)} notes"
        items_html = "".join(f"<li>{_esc(it)}</li>" for it in limitation_items)
        limitation_html = (
            '<div class="conclusion-limitation-accordion">'
            '<input type="checkbox" id="toggle-limitations" class="limitation-toggle-checkbox">'
            '<label for="toggle-limitations" class="limitation-accordion-summary">'
            f'<strong class="limitation-title">Notes on missing data &amp; testing scope</strong> '
            f'<span class="badge badge-info">{badge_text}</span>'
            '<span class="limitation-toggle-hint">View details ▾</span>'
            '</label>'
            '<div class="limitation-accordion-body">'
            f'<ul class="findings">{items_html}</ul>'
            '</div>'
            '</div>'
        )

    conclusion_theory = _theory(
        "<strong>Section overview.</strong> Synthesises the bot's overall risk tier, operational directive, "
        "and empirical quantitative proof into an actionable recommendation for copy-trading.<br><br>"
        "<strong>Verdict Box &amp; Action Directive:</strong> "
        "Clear risk classification (VETO / DRAWDOWN: HIGH / HIDDEN RISK / WATCH / SAFE) paired with an explicit capital allocation directive. "
        "Veto verdicts strictly instruct followers not to allocate capital or to close positions.<br><br>"
        "<strong>Hero Scores &amp; Quick Strip:</strong> "
        "<em>Risk score (0-100)</em> &mdash; lower is safer; combines 10 independent risk dimensions with Veto Floors. "
        "<em>Quality score (0-100)</em> &mdash; higher is better; evaluates risk-adjusted return and strategy edge. "
        "<em>Confidence (%)</em> &mdash; measures sample adequacy (&ge;30 trades required for minimum statistical validity). "
        "<em>Quick Strip</em> &mdash; snapshots reference capital, unrealised float loss, max drawdown, win rate, and observed trade count.<br><br>"
        "<strong>Quantitative Evidence &amp; Scorecard:</strong> "
        "Summarises simulated stress drawdown (P95), ruin probability, confidence, and sample size in high-visibility chips. "
        "Accompanied by key cause analysis (Why), revisit conditions, and terminal audit logs.<br><br>"
        "<strong>Hidden Warnings &amp; Testing Scope:</strong> "
        "Highlights latent risks (e.g. untested in downtrends, thin track records, heavy regime dependence) that leaderboard returns conceal.",
        "Deterministic multi-factor decision engine fusing OKX public order book records, open position exposure, "
        "and 10,000-scenario stationary bootstrap simulations. Employs asymmetric risk-first evaluation: liquidation risk or extreme "
        "tail loss triggers an immediate Veto Floor override that forces the final score and verdict to emergency status regardless of past profit.",
    )

    body = '<div class="conclusion-body-wrap">' + "".join(blocks) + limitation_html + conclusion_theory + "</div>"
    return _section("Conclusion and recommendation", body, tone="primary", anchor="ket-luan")


# --------------------------------------------------------------------------- #
# Việc 2/3 -- "thị trường được chấm chỉ là một phần hoạt động của bot".
# `bot.identity.symbol_exposure_share`/`observed_symbols`
# (Agent/backend/bot/mcp/service.py::_resolve_identity_market) đã được tính sẵn
# từ lâu nhưng chưa từng hiển thị ở đâu: một bot tập trung 95% vào đúng thị
# trường được chấm và một bot chỉ giao dịch thị trường đó 30% thời gian giá
# trị trông giống hệt nhau trên mọi biểu đồ khác của trang này. Đặt NGAY SAU
# phần kết luận (không phải trong <details>) theo đúng yêu cầu: đây là bối
# cảnh quyết định các chiều phụ thuộc thị trường (market_alignment,
# liquidity_execution, leverage_exposure) có đại diện cho toàn bộ hoạt động
# bot hay chỉ một phần của nó.
# --------------------------------------------------------------------------- #


def _render_market_coverage(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    primary_share_pct = evidence.get("primary_share_pct")
    if not _is_finite_number(primary_share_pct):
        return ""

    traded_symbol = evidence.get("traded_symbol") or result.get("code") or "?"
    observed_symbols = evidence.get("observed_symbols")
    observed_symbols = observed_symbols if isinstance(observed_symbols, list) else []
    share_map = evidence.get("symbol_exposure_share")
    share_map = share_map if isinstance(share_map, dict) else {}

    _raw_resolved = evidence.get("resolved_markets")
    resolved_markets = (
        [m for m in _raw_resolved if isinstance(m, dict) and m.get("symbol")]
        if isinstance(_raw_resolved, list)
        else []
    )
    _raw_unresolved = evidence.get("unresolved_markets")
    unresolved_markets = (
        [m for m in _raw_unresolved if isinstance(m, dict) and m.get("symbol")]
        if isinstance(_raw_unresolved, list)
        else []
    )
    coverage_achieved_pct = evidence.get("coverage_achieved_pct")
    has_full_coverage_data = bool(resolved_markets) and _is_finite_number(
        coverage_achieved_pct
    )
    headline_pct = (
        float(coverage_achieved_pct) if has_full_coverage_data else float(primary_share_pct)
    )

    if has_full_coverage_data:
        resolved_list = resolved_markets
        unresolved_list = unresolved_markets
    else:
        resolved_list = [{"symbol": traded_symbol, "share_pct": float(primary_share_pct)}]
        others = [s for s in observed_symbols if s != traded_symbol]
        unresolved_list = [
            {"symbol": s, "share_pct": float(share_map[s] * 100.0)}
            for s in others
            if _is_finite_number(share_map.get(s))
        ]

    resolved_sum = sum(float(m.get("share_pct", 0) or 0) for m in resolved_list)
    unresolved_sum = sum(float(m.get("share_pct", 0) or 0) for m in unresolved_list)
    accounted_sum = resolved_sum + unresolved_sum
    rem_pct = round(100.0 - accounted_sum, 1) if (accounted_sum < 99.5 and accounted_sum > 0) else 0.0
    unresolved_total = unresolved_sum + rem_pct

    target_pct = float(MARKET_COVERAGE_TARGET_PCT)
    # Legacy primary-only coverage used a 60% representativeness threshold;
    # resolved-market coverage uses the explicit 80% target. Keep the two
    # semantics separate so old assessment files do not suddenly acquire a
    # stricter warning merely because the renderer learned the new branch.
    is_under_target = (
        headline_pct < target_pct
        if has_full_coverage_data
        else float(primary_share_pct) < 60.0
    )

    if is_under_target:
        status_badge = '<span class="cov-status-badge cov-status-under">UNDER TARGET ⚠</span>'
    else:
        status_badge = '<span class="cov-status-badge cov-status-met">TARGET MET ✔</span>'

    # Curated crypto brand colors
    asset_brand_colors = {
        "BTC": "#f7931a",
        "ETH": "#627eea",
        "SOL": "#9945ff",
        "BNB": "#f3ba2f",
        "DOGE": "#ba9f33",
        "SUI": "#2a82e4",
        "DOT": "#e6007a",
        "UNI": "#ff007a",
        "AVAX": "#e84142",
        "LINK": "#375bd2",
        "XRP": "#23292f",
        "ADA": "#0033ad",
        "NEAR": "#1e293b",
        "APT": "#10b981",
        "MATIC": "#8247e5",
        "POL": "#8247e5",
        "ARB": "#28a0f0",
        "OP": "#ff0420",
        "TRX": "#ef0027",
        "LTC": "#345d9d",
        "SHIB": "#ea580c",
        "PEPE": "#15803d",
    }
    fallback_palette = [
        "#6366f1", "#0ea5e9", "#10b981", "#8b5cf6", "#f59e0b",
        "#ec4899", "#14b8a6", "#f97316", "#3b82f6", "#84cc16"
    ]

    segments_html = []
    color_idx = 0
    for m in resolved_list:
        sym = str(m.get("symbol", "")).strip()
        share = float(m.get("share_pct", 0) or 0)
        if share <= 0:
            continue
        base_sym = sym.split("-")[0].upper()
        color = asset_brand_colors.get(base_sym, fallback_palette[color_idx % len(fallback_palette)])
        color_idx += 1

        if share >= 6.5:
            label_inside = f'<span class="cov-seg-sym">{_esc(sym)}</span> <span class="cov-seg-pct">{_pct(share, 0)}</span>'
        elif share >= 4.0:
            label_inside = f'<span class="cov-seg-sym">{_esc(sym)}</span>'
        else:
            label_inside = ""

        tooltip = f"{sym}: {_pct(share, 1)} of trading value (Covered) · Order book, liquidity & volatility integrated into risk score"
        segments_html.append(
            f'<div class="cov-bar-seg cov-seg-resolved" style="width:{share:.2f}%;flex-basis:{share:.2f}%;background:{color};" '
            f'title="{_esc(tooltip)}">'
            f'<div class="cov-seg-inner">{label_inside}</div>'
            f'</div>'
        )

    for m in unresolved_list:
        sym = str(m.get("symbol", "")).strip()
        share = float(m.get("share_pct", 0) or 0)
        if share <= 0:
            continue
        reason = m.get("reason") or "Market data could not be measured / CEX order book not synchronized"
        reason_text = str(reason).replace("NO_MARKET_DATA_FOR_TRADED_SYMBOL", "market data could not be measured")
        reason_text = reason_text.replace("TIMEOUT", "market data request timed out")

        if share >= 6.5:
            label_inside = f'<span class="cov-seg-sym">{_esc(sym)}</span> <span class="cov-seg-pct">{_pct(share, 0)}</span>'
        elif share >= 4.0:
            label_inside = f'<span class="cov-seg-sym">{_esc(sym)}</span>'
        else:
            label_inside = ""

        tooltip = f"{sym}: {_pct(share, 1)} of trading value (Unresolved) · {reason_text}. Not inferred from other markets."
        segments_html.append(
            f'<div class="cov-bar-seg cov-seg-unresolved" style="width:{share:.2f}%;flex-basis:{share:.2f}%;" '
            f'title="{_esc(tooltip)}">'
            f'<div class="cov-seg-inner">{label_inside}</div>'
            f'</div>'
        )

    if rem_pct > 0.5:
        if rem_pct >= 6.5:
            label_inside = f'<span class="cov-seg-sym">Others</span> <span class="cov-seg-pct">{_pct(rem_pct, 0)}</span>'
        elif rem_pct >= 4.0:
            label_inside = '<span class="cov-seg-sym">Others</span>'
        else:
            label_inside = f'<span class="cov-seg-pct">{_pct(rem_pct, 0)}</span>'
        tooltip = f"Other unallocated activity: {_pct(rem_pct, 1)} of trading value (Unmeasured)"
        segments_html.append(
            f'<div class="cov-bar-seg cov-seg-unallocated" style="width:{rem_pct:.2f}%;flex-basis:{rem_pct:.2f}%;" '
            f'title="{_esc(tooltip)}">'
            f'<div class="cov-seg-inner">{label_inside}</div>'
            f'</div>'
        )

    target_line_html = (
        f'<div class="cov-target-line" style="left:{target_pct:.1f}%;" '
        f'title="Target benchmark: {target_pct:.0f}% coverage">'
        f'<span class="cov-target-pin">Target: {target_pct:.0f}%</span>'
        '</div>'
    )

    sublabels_html = (
        '<div class="cov-sublabel-row">'
        '<div class="cov-sublabel-col cov-sublabel-resolved">'
        f'<span class="cov-icon-resolved">✓</span> <span><strong>Resolved {len(resolved_list)} markets: covering {_pct(headline_pct, 0)} of trading value</strong></span>'
        '</div>'
        '<div class="cov-sublabel-col cov-sublabel-unresolved">'
        f'<span class="cov-icon-unresolved">✗</span> <span><strong>Unresolved:</strong> {_pct(unresolved_total, 0)} unmeasured (Not inferred from another market)</span>'
        '</div>'
        '</div>'
    )

    warning_html = ""
    if is_under_target:
        warning_html = (
            '<div class="cov-warning-box notice-warning">'
            '<div class="cov-warning-head">'
            '<span class="cov-warning-icon">⚠</span>'
            '<span class="cov-warning-title">COVERAGE WARNING</span>'
            '</div>'
            '<div class="cov-warning-body">'
            f"Only <strong>{_pct(headline_pct, 0)}</strong> of the bot's trading value has been covered so far (target {target_pct:.0f}%). "
            'The <code class="cov-dim-pill" title="View dimension in Analyst Result" onclick="if(window.location.hash!=\'#panel-report\')window.location.hash=\'#panel-report\';">market_alignment</code>, '
            '<code class="cov-dim-pill" title="View dimension in Analyst Result" onclick="if(window.location.hash!=\'#panel-report\')window.location.hash=\'#panel-report\';">liquidity_execution</code> and '
            '<code class="cov-dim-pill" title="View dimension in Analyst Result" onclick="if(window.location.hash!=\'#panel-report\')window.location.hash=\'#panel-report\';">leverage_exposure</code> '
            "dimensions are <strong>ONLY</strong> scored on the primary market; the rest of the bot's activity has NOT been reviewed."
            '</div>'
            '</div>'
        )

    secondary_html = ""
    if not has_full_coverage_data:
        secondary = evidence.get("secondary_market")
        if isinstance(secondary, dict) and secondary.get("symbol"):
            trend = TREND_VI.get(secondary.get("trend"), "unclear")
            vol = VOL_VI.get(secondary.get("volatility"), "unclear")
            liq = LIQ_VI.get(secondary.get("liquidity_tier"), "unclear")
            secondary_share = secondary.get("share_pct")
            secondary_share_text = (
                _pct(secondary_share, 0) if _is_finite_number(secondary_share) else "—"
            )
            secondary_html = (
                '<div class="card-hint" style="margin-top:0.65rem;">'
                f"Second-largest market by trading share: <strong>{_esc(secondary.get('symbol'))}</strong> "
                f"({secondary_share_text}) -- {trend}, {vol}, {liq}."
                '</div>'
            )

    theory = (
        '<div class="theory theory-always-visible"><div class="theory-body">'
        '<div class="theory-title" style="font-weight:700;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.04em;color:var(--muted);margin-bottom:0.35rem;">Methodology &amp; interpretation</div>'
        '<p><strong>Interpretation:</strong> Market data coverage reflects how much of the bot\'s total trading volume has been'
        ' directly observed and validated against historical order book, candle series, and liquidity depth.'
        ' When a bot trades many symbols and coverage is below the 80% benchmark, dimensions dependent on'
        ' market microstructure (market_alignment, liquidity_execution, leverage_exposure) are only scored'
        ' on the observed slice, and cannot be blindly extrapolated to the unmeasured markets.</p>'
        '<p><strong>Method:</strong> Calculated from closed trades notional value distribution across symbols.'
        ' Targets 80% coverage to minimize unobserved multi-asset tail risks.</p>'
        '</div></div>'
    )

    card_body = (
        '<div class="cov-card-wrap">'
        '<div class="cov-benchmark-row">'
        '  <span class="cov-benchmark-title">DATA COVERAGE BENCHMARK</span>'
        '  <div class="cov-benchmark-metrics">'
        f'    <span class="cov-metric-item"><span class="cov-metric-label">TARGET:</span> <span class="cov-metric-val">{target_pct:.1f}%</span></span>'
        '    <span class="cov-metric-sep">│</span>'
        f'    <span class="cov-metric-item"><span class="cov-metric-label">CURRENT:</span> <span class="cov-metric-val">{headline_pct:.1f}%</span></span>'
        f'    {status_badge}'
        '  </div>'
        '</div>'
        f'{sublabels_html}'
        '<div class="cov-bar-wrapper">'
        f'  <div class="cov-stacked-bar">{"".join(segments_html)}</div>'
        f'  {target_line_html}'
        '</div>'
        f'{warning_html}'
        f'{secondary_html}'
        '</div>'
    )

    return _section("Market being scored", card_body + theory, anchor="thi-truong")


# --------------------------------------------------------------------------- #
# Section ① -- "Cách bot này chơi": Việc 1/2's own explicit fix. The QC
# engine already reconstructs how a bot trades from its closed ledger
# (`Agent/backend/bot/mcp/analytics/strategy/profile.py` /
# `.../behavior/detector.py`) and uses it to SCORE two dimensions
# (strategy_drift, behavioral_risk) -- but that observation never reached the
# report itself, leaving a reader to reassemble "what does this bot actually
# do" by hand out of ten unrelated dimension bars. This section is placed
# right after the conclusion (project owner's own explicit placement), in
# plain Vietnamese prose (never a bare enum), so everything below it reads
# as evidence FOR this section rather than ten independent facts.
# --------------------------------------------------------------------------- #


def _phase_row_sort_key(row: Dict[str, Any]) -> float:
    share = row.get("profit_share_pct")
    return share if isinstance(share, (int, float)) and math.isfinite(share) else -1e18


def _render_phase_breakdown_table(strategy: Dict[str, Any]) -> str:
    """The pha × cách-đánh cross-tab (coordinator's own explicit addendum):
    one row per market phase the bot was ever measured in, sorted by profit
    contribution descending (the phase that made the money leads), each row
    tagged with its own three-tier confidence (`_phase_confidence_vi`) so a
    1-2 trade phase can never read as equally solid evidence as a 15-trade
    one. Returns "" (never a broken empty table) when there is no phase
    breakdown to show at all.
    """
    rows = strategy.get("phase_breakdown")
    if not isinstance(rows, list) or not rows:
        return ""
    ordered = sorted(
        (r for r in rows if isinstance(r, dict)), key=_phase_row_sort_key, reverse=True
    )
    if not ordered:
        return ""
    table_rows = []
    for row in ordered:
        trades = row.get("trades")
        confidence = _phase_confidence_vi(trades)
        phase_cell = _esc(_phase_label_vi(row.get("phase")))
        if confidence == PHASE_CONFIDENCE_INSUFFICIENT_VI:
            phase_cell += " " + _badge(
                f"{PHASE_CONFIDENCE_INSUFFICIENT_VI} (not representative)", "#dc2626"
            )
        elif confidence == PHASE_CONFIDENCE_THIN_VI:
            phase_cell += " " + _badge(
                f"{PHASE_CONFIDENCE_THIN_VI} (reference only)", "#9ca3af"
            )
        pnl = row.get("total_pnl")
        pnl_text = _money(pnl)
        if _is_finite_number(pnl):
            f_pnl = float(pnl)
            if f_pnl > 0:
                pnl_cell = f'<span class="pnl-val pnl-pos" style="color:#16a34a;font-weight:700;font-family:var(--mono);">+{_esc(pnl_text)}</span>'
            elif f_pnl < 0:
                pnl_cell = f'<span class="pnl-val pnl-neg" style="color:#dc2626;font-weight:700;font-family:var(--mono);">{_esc(pnl_text)}</span>'
            else:
                pnl_cell = f'<span class="pnl-val pnl-zero" style="font-weight:600;font-family:var(--mono);">{_esc(pnl_text)}</span>'
        else:
            pnl_cell = f'<span class="pnl-val">{_esc(pnl_text)}</span>'

        table_rows.append(
            [
                phase_cell,
                _esc(_num(trades, 0)),
                _esc(_pct(row.get("win_rate"), 0)),
                pnl_cell,
                _esc(_pct(row.get("long_share_pct"), 0)) + " long",
                _esc(_num(row.get("average_leverage"), 1)) + "x",
                _esc(_num(row.get("median_hold_minutes"), 0)) + " min",
                _esc(_pct(row.get("profit_share_pct"), 0)),
            ]
        )
    coverage = strategy.get("phase_coverage_pct")
    coverage_html = (
        f'<p class="phase-coverage">Share of trades that could be assigned to a '
        f"specific market phase: <strong>{_esc(_pct(coverage, 1))}</strong>.</p>"
    )
    coverage_warning = ""
    if isinstance(coverage, (int, float)) and coverage < PHASE_COVERAGE_WARN_PCT:
        coverage_warning = (
            '<div class="notice notice-warning">Most trades (over '
            f"{_esc(_pct(100.0 - coverage, 0))}) could not be assigned to a specific "
            "market phase -- reason: some of the symbols this bot trades have no "
            "reference candle series to determine the phase from (not a timing "
            "mismatch or a phase-transition edge case) -- the table below is a "
            "HINT, NOT a firm conclusion about the bot's behaviour.</div>"
        )
    untested = strategy.get("untested_phases")
    untested_html = ""
    if isinstance(untested, list) and untested:
        names = ", ".join(_esc(_phase_label_vi(p)) for p in untested)
        untested_html = (
            f'<p class="phase-untested">Never traded through market phase: '
            f"<strong>{names}</strong> -- nobody yet knows how the bot handles this phase.</p>"
        )
    table_html = _table(
        [
            "Market phase",
            "Trades",
            "Win rate",
            "PnL",
            "Bias in this phase",
            "Avg leverage",
            "Hold time (median)",
            "Share of profit",
        ],
        table_rows,
    )
    return coverage_html + coverage_warning + table_html + untested_html


def _render_strategy_section(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return ""
    strategy = evidence.get("strategy")
    behavioral = evidence.get("behavioral")
    if not isinstance(strategy, dict) or not isinstance(behavioral, dict):
        return ""

    paragraphs: List[str] = []

    profile_label = OBSERVED_PROFILE_LABEL_VI.get(
        strategy.get("observed_profile"), "not yet determined"
    )
    bias_label = DIRECTIONAL_BIAS_LABEL_VI.get(
        strategy.get("directional_bias"), "not enough evidence to determine"
    )
    entry_style = strategy.get("entry_style")
    style_label = (
        "not enough evidence to determine"
        if entry_style == "UNKNOWN" or entry_style is None
        else ENTRY_STYLE_LABEL_VI.get(entry_style, "not enough evidence to determine")
    )
    paragraphs.append(
        "<p><strong>Observed profile</strong> from closed trades: "
        f"{_esc(profile_label)}. <strong>Bias:</strong> {_esc(bias_label)}. "
        f"<strong>Entry style:</strong> {_esc(style_label)}.</p>"
    )

    phase_bits: List[str] = []
    best_phase = strategy.get("best_phase")
    worst_phase = strategy.get("worst_phase")
    if best_phase:
        phase_bits.append(f"performs best in the {_esc(_phase_label_vi(best_phase))} phase")
    if worst_phase:
        phase_bits.append(f"performs worst in the {_esc(_phase_label_vi(worst_phase))} phase")
    if not strategy.get("tested_in_downtrend"):
        phase_bits.append("no evidence it has ever traded through a downtrend")
    if phase_bits:
        paragraphs.append(
            "<p><strong>By market phase:</strong> "
            + "; ".join(phase_bits)
            + ".</p>"
        )

    flags = []
    if behavioral.get("martingale_escalation_detected"):
        flags.append("martingale-style stacking (raising size after a losing trade)")
    if behavioral.get("averaging_down_detected"):
        flags.append("averaging down by adding to a losing position in the same direction")
    if behavioral.get("leverage_escalation_detected"):
        flags.append("raising leverage after a losing trade")
    if behavioral.get("reentry_loop_detected"):
        flags.append("repeatedly re-entering in a loop")
    tier_label = BEHAVIORAL_TIER_LABEL_VI.get(
        behavioral.get("behavioral_risk_tier"), "not measured"
    )
    if flags:
        behavior_html = (
            "<p><strong>Behavioural signals:</strong> shows signs of "
            + "; ".join(flags)
            + f". Raw behavioural signal from the trade ledger: <strong>{_esc(tier_label)}</strong> "
            "-- this is the level of the OBSERVED SIGNAL, not the scored value "
            "of the \u201cTrading behaviour\u201d dimension in the scores section.</p>"
        )
    else:
        behavior_html = (
            "<p><strong>Behavioural signals:</strong> no sign of averaging down, "
            "martingale-style stacking, or raising leverage after a loss found in "
            f"the closed trade data. Raw behavioural signal from the trade ledger: <strong>{_esc(tier_label)}</strong> "
            "-- this is the level of the OBSERVED SIGNAL, not the scored value "
            "of the \u201cTrading behaviour\u201d dimension in the scores section.</p>"
        )
    paragraphs.append(behavior_html)

    table_block = _render_phase_breakdown_table(strategy)

    theory = _theory(
        "Reconstructed trading style, directional bias, behavioral risk patterns, and performance across market regimes. "
        "Identifies high-risk trading behaviors such as martingale escalation (raising size after losses), "
        "averaging down into losing positions, leverage escalation, and rapid re-entry loops. "
        "Market phase performance evaluates profit distribution across regimes. Sample validity: "
        f"<strong>{PHASE_CONFIDENCE_ENOUGH_VI}</strong> (≥10 trades) = statistically valid; "
        f"<strong>{PHASE_CONFIDENCE_THIN_VI}</strong> (3–9 trades) = reference only; "
        f"<strong>{PHASE_CONFIDENCE_INSUFFICIENT_VI}</strong> (&lt;3 trades) = unrepresentative.",
        "Inferred from transaction timing, position sizing changes, and entry intervals mapped onto 1H OHLCV trend and volatility phases.",
    )
    body = "".join(paragraphs) + table_block + theory
    return _section("How this bot trades", body, anchor="cach-choi")


# --------------------------------------------------------------------------- #
# Section 2b -- narrative ("nhận định chuyên môn"): an OPTIONAL, LLM-authored
# paragraph built from the numbers already shown above (see
# Agent/backend/llm/narrative.py's own module docstring for the
# full design -- feature flag, three validation gates, fail-closed fallback).
# Placed right after the conclusion per the task this was written for.
#
# Renders NOTHING when `result["narrative"]` is `None`/blank (feature off,
# or -- for a LIMITED/NOT_FOUND result -- simply not applicable), so this
# never adds an empty card to the page and never changes the page's
# `<svg>`/`<details>` counts on its own: it is one more plain `<section>`
# only when there is a narrative string to show, no chart, no collapsible
# block.
# --------------------------------------------------------------------------- #


def _is_narrative_pending(text: str) -> bool:
    t = text.lower()
    return (
        "15-45" in t
        or "being drafted by the language model" in t
        or "written assessment for this bot" in t
        or "is being drafted" in t
        or "language model in the background" in t
        or "revisit the report_url" in t
        or "detail_url" in t
    )


def _synthesize_3rd_person_narrative(result: Dict[str, Any]) -> str:
    """Xây dựng nhận định chuyên môn từ góc nhìn thứ ba độc lập (3rd-person perspective)
    dựa trên toàn bộ kết quả phân tích định lượng đã đo lường của bot."""
    code = result.get("code") or "—"
    name = result.get("name") or result.get("nick_name") or code
    symbol = result.get("traded_symbol") or "the primary market"
    risk = result.get("risk")
    verdict = result.get("verdict") or "UNDETERMINED"
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    score_bd = evidence.get("score_breakdown") or {}
    veto_reasons = score_bd.get("veto_reasons") or []

    trade_count = result.get("trade_count")
    win_rate = result.get("win_rate")
    pf = result.get("profit_factor")
    mdd = result.get("max_drawdown")

    p1 = (
        f"From an independent quantitative review, bot <strong>{_esc(str(name))}</strong> "
        f"(code <code>{_esc(str(code))}</code>), trading the <strong>{_esc(str(symbol))}</strong> pair, "
        f"is rated: <strong>{_esc(str(verdict))}</strong>."
    )
    if risk is not None:
        p1 += f" Its overall risk score is <strong>{_num(risk, 0)}/100</strong>"
        if veto_reasons:
            reasons_str = "; ".join(_esc(str(r)) for r in veto_reasons)
            p1 += f", triggered by the safety veto mechanism: <em>{reasons_str}</em>."
        else:
            p1 += ", based on the weighted average of the measured risk dimensions."

    p2_parts = []
    if mdd is not None:
        p2_parts.append(f"the max drawdown recorded is {_pct(mdd, 1)}")
    if win_rate is not None and trade_count is not None:
        p2_parts.append(f"the win rate reached {_pct(win_rate, 1)} across {trade_count} closed trades")
    if pf is not None:
        p2_parts.append(f"the profit factor reached {_num(pf, 2)}")

    p2 = ""
    if p2_parts:
        p2 = "On the performance and capital-safety profile, the system recorded " + ", ".join(p2_parts) + "."

    behavioral = evidence.get("behavioral") or {}
    b_flags = []
    if behavioral.get("martingale_escalation_detected"):
        b_flags.append("adding size after a losing trade (martingale)")
    if behavioral.get("averaging_down_detected"):
        b_flags.append("averaging down by adding more positions in the same direction")
    if behavioral.get("leverage_escalation_detected"):
        b_flags.append("raising leverage while the account is underwater")

    if b_flags:
        p2 += f" Notably, the algorithm detected unusual behaviour: {', '.join(b_flags)}, creating a risk of a sudden drawdown."

    if "VETO" in str(verdict).upper() or (risk is not None and risk >= 70):
        p3 = (
            "Independent recommendation: This bot's risk level exceeds an acceptable "
            "safety threshold. Investors should not allocate capital to this strategy, "
            "in order to limit the risk of liquidation or a severe account drawdown."
        )
    elif "WARNING" in str(verdict).upper() or (risk is not None and risk >= 50):
        p3 = (
            "Independent recommendation: This bot shows profit potential but carries "
            "meaningful market risk. Anyone copying its trades should allocate only a "
            "small share of capital and set a strict account stop-loss."
        )
    else:
        p3 = (
            "Independent recommendation: This bot has maintained relatively stable "
            "capital-management discipline over the data reviewed. Investors should "
            "keep monitoring actual slippage and liquidity depth closely when copying "
            "its trades."
        )

    paragraphs = [p1]
    if p2:
        paragraphs.append(p2)
    paragraphs.append(p3)

    cards = []
    labels = ["Quantitative Review & Risk Score", "Performance & Behavioral Profile", "Capital Allocation Recommendation"]
    for idx, p in enumerate(paragraphs, start=1):
        lbl = labels[idx - 1] if idx <= len(labels) else f"Point {idx}"
        cards.append(
            f'<div class="expert-point-card" style="display:flex;flex-direction:column;gap:5px;background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);border-radius:7px;padding:10px 12px;box-sizing:border-box;margin-bottom:7px;">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span class="expert-point-num" style="font-family:var(--mono);font-size:10px;font-weight:700;color:#38bdf8;background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.2);border-radius:4px;padding:2px 6px;line-height:1.2;">{idx:02d}</span>'
            f'<span style="font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#38bdf8;">{lbl}</span>'
            f'</div>'
            f'<div class="expert-point-content" style="font-size:12.5px;line-height:1.55;color:var(--ink-2,#cbd5e1);">{p}</div>'
            f'</div>'
        )
    return f'<div class="expert-points-feed" style="display:flex;flex-direction:column;gap:6px;margin-top:0.75rem;">{"".join(cards)}</div>'


def _format_expert_metric_highlights(text: str) -> str:
    escaped = _esc(text)
    return re.sub(
        r'(\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%|\b\d+(?:\.\d+)?x|\b\d+\.\d+\b)',
        r'<strong class="expert-metric" style="font-family:var(--mono);font-weight:700;color:var(--ink,#fff);background:rgba(255,255,255,0.06);padding:0 4px;border-radius:3px;font-variant-numeric:tabular-nums;">\1</strong>',
        escaped,
    )


def _render_deterministic_thesis(result: Dict[str, Any]) -> str:
    """Core Strategy Thesis and root causes, measured rather than written.

    This section's thesis box used to be built only from the optional LLM
    narrative, which is off by default -- so on an ordinary page the section
    rendered nothing at all and the engine's own summary never reached a
    reader. The deterministic `executive_essence` and `failure_modes` modules
    fill exactly that role, and they belong HERE (design section III, tier 3:
    "Hop nhat Nhan dinh chuyen gia & Ly do cot loi") rather than in a card of
    their own beside the Conclusion.
    """
    insights = _insights(result)
    essence = insights.get("executive_essence") or {}
    modes = insights.get("failure_modes") or []
    if not essence and not modes:
        return ""

    parts: List[str] = []
    thesis = essence.get("what_it_appears_to_do")
    if thesis:
        extras = [
            essence.get("dominant_behavior"),
            essence.get("strongest_positive_evidence"),
        ]
        detail = " &middot; ".join(_esc(str(x)) for x in extras if x)
        parts.append(
            '<div class="expert-summary-box">'
            '<div class="expert-summary-label">Core Strategy Thesis</div>'
            f'<div class="expert-summary-text">{_esc(str(thesis))}</div>'
            + (f'<div class="expert-summary-sub">{detail}</div>' if detail else "")
            + "</div>"
        )

    if modes:
        rows = "".join(
            "<li><strong>"
            + _esc(str(m.get("mechanism") or ""))
            + "</strong><span class=\"root-cause-support\">"
            + _esc(str(m.get("observed_support") or ""))
            + "</span></li>"
            for m in modes
        )
        parts.append(
            '<div class="root-cause-block">'
            f'<div class="root-cause-title">Root causes on the evidence ({len(modes)})</div>'
            f'<ul class="root-cause-list">{rows}</ul>'
            "</div>"
        )

    unknown = essence.get("most_important_unknown")
    if unknown:
        parts.append(
            f'<p class="notice notice-neutral">Most important unknown: {_esc(str(unknown))}</p>'
        )
    return "".join(parts)


def _render_narrative(result: Dict[str, Any]) -> str:
    text = result.get("narrative")
    if not isinstance(text, str) or not text.strip():
        # No LLM narrative: the deterministic thesis carries this section.
        body = _render_deterministic_thesis(result)
        if not body:
            return ""
        return _section("Expert assessment", body, anchor="nhan-dinh")

    is_pending = _is_narrative_pending(text)
    bullets: List[str] = []

    if is_pending:
        # Khi đang chờ LLM nền, tuyệt đối không hiện câu note chờ vô nghĩa.
        # Ưu tiên bản luận đề TẤT ĐỊNH (`executive_essence` + `failure_modes`)
        # vì nó là tóm tắt của chính engine, có số liệu kiểm chứng kèm theo;
        # chỉ khi module đó không dựng được mới rơi về bản văn tổng hợp từ số.
        prose_html = _render_deterministic_thesis(result) or _synthesize_3rd_person_narrative(result)
    else:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        prose_lines: List[str] = []
        for l in lines:
            if l.startswith(("- ", "• ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ")):
                cleaned = re.sub(r"^([-\*•]|\d+\.)\s*", "", l)
                bullets.append(cleaned)
            else:
                prose_lines.append(l)

        if not bullets and prose_lines:
            full_prose = " ".join(prose_lines)
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", full_prose)
                if len(s.strip()) > 15
            ]
            if len(sentences) >= 2:
                summary_text = sentences[0]
                bullets = sentences[1:]
                prose_html = (
                    '<div class="expert-summary-box">'
                    '<div class="expert-summary-label">Core Strategy Thesis</div>'
                    f'<div class="expert-summary-text">{_esc(summary_text)}</div>'
                    '</div>'
                )
            else:
                prose_html = (
                    '<div class="expert-summary-box">'
                    '<div class="expert-summary-label">Core Strategy Thesis</div>'
                    f'<div class="expert-summary-text">{_esc(full_prose)}</div>'
                    '</div>'
                )
        else:
            summary_p = "".join(f"<div style='margin-bottom:4px;'>{_esc(p)}</div>" for p in prose_lines)
            prose_html = (
                '<div class="expert-summary-box">'
                '<div class="expert-summary-label">Core Strategy Thesis</div>'
                f'<div class="expert-summary-text">{summary_p}</div>'
                '</div>'
                if summary_p else ""
            )

    keypoints_html = ""
    if bullets:
        card_items = []
        for idx, b in enumerate(bullets, start=1):
            highlighted = _format_expert_metric_highlights(b)
            card_items.append(
                f'<div class="expert-point-card" style="display:flex;align-items:flex-start;gap:10px;background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);border-radius:7px;padding:9px 12px;box-sizing:border-box;transition:all 0.15s ease;">'
                f'<span class="expert-point-num" style="font-family:var(--mono);font-size:10px;font-weight:700;color:#38bdf8;background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.2);border-radius:4px;padding:2px 6px;line-height:1.2;flex-shrink:0;margin-top:2px;">{idx:02d}</span>'
                f'<div class="expert-point-content" style="font-size:12.5px;line-height:1.5;color:var(--ink-2,#cbd5e1);flex:1;">{highlighted}</div>'
                f'</div>'
            )

        keypoints_html = (
            '<div class="expert-points-wrap" style="margin-top:0.5rem;display:flex;flex-direction:column;">'
            '<div class="expert-points-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.65rem;">'
            '<span class="expert-points-title" style="font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:var(--muted,#94a3b8);">Key findings & quantitative evidence</span>'
            f'<span class="expert-points-count" style="font-family:var(--mono);font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;background:rgba(255,255,255,0.06);color:var(--muted,#94a3b8);">{len(bullets)} items</span>'
            '</div>'
            f'<div class="expert-points-feed" style="display:flex;flex-direction:column;gap:7px;max-height:285px;overflow-y:auto;padding-right:4px;box-sizing:border-box;">{"".join(card_items)}</div>'
            '</div>'
        )

    narrative_theory = _theory(
        "<strong>Section overview.</strong> Provides an independent analytical synthesis combining qualitative strategy archetypes "
        "with key empirical findings extracted from trade ledger data.<br><br>"
        "<strong>Core Strategy Thesis:</strong> "
        "Executive summary identifying the bot's core trading mechanics (e.g. trend-following, mean reversion, scalp, grid), "
        "market regime alignment, and structural behavioural characteristics.<br><br>"
        "<strong>Key findings &amp; quantitative evidence:</strong> "
        "Numbered audit points highlighting specific empirical risks: trade frequency cadence, tail risk exposure, "
        "loss-holding behaviour, leverage scaling, and dependencies on specific market phases.",
        "Synthesised deterministically from quantitative engine metrics (trade distribution, duration percentiles, "
        "holding time skew, regime compatibility, and open float drag). Every finding is cross-referenced directly with "
        "the underlying OKX order book and Monte Carlo simulation outputs.",
    )

    body = (
        '<div class="narrative-body-wrap">'
        '<div class="narrative-meta-bar" style="display:flex;align-items:center;gap:10px;margin-bottom:0.75rem;flex-wrap:wrap;">'
        '<span class="badge badge-info">INDEPENDENT VIEW</span>'
        '<span class="meta-desc" style="font-size:12px;color:var(--muted,#94a3b8);">An independent third-person view synthesised by a language model from the quantitative analysis results</span>'
        '</div>'
        f'{prose_html}'
        f'{keypoints_html}'
        f'{narrative_theory}'
        '</div>'
    )
    return _section("Expert assessment", body, tone="primary", anchor="nhan-dinh")


# --------------------------------------------------------------------------- #
# Section 3 -- per-dimension scores
# --------------------------------------------------------------------------- #


def _render_dimensions_section(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return ""

    dimensions = evidence.get("dimensions")
    if isinstance(dimensions, dict) and dimensions:
        body = _render_full_dimension_bars(
            dimensions, evidence.get("score_breakdown") or {}
        )
    else:
        components = evidence.get("components")
        if isinstance(components, list) and components:
            body = _render_component_bars(components)
        else:
            return ""

    theory = _theory(
        "<strong>Section overview.</strong> Decomposes overall strategy risk into 10 orthogonal risk dimensions, "
        "evaluating structural vulnerability across distinct operational axes.<br><br>"
        "<strong>10 Risk Dimensions (0-100 scale, lower is safer, ≥70 indicates severe danger):</strong><br>"
        "• <em>Market alignment</em>: Consistency of edge across trending, sideways, and volatile regimes.<br>"
        "• <em>Trading behaviour</em>: Detection of high-risk toxic mechanics (martingale sizing, refusing to cut losses, wide grid spacing).<br>"
        "• <em>Leverage exposure</em>: Effective margin utilization, leverage spikes, and borrowing risk.<br>"
        "• <em>Drawdown control</em>: Historical peak-to-trough drawdown depth, recovery velocity, and underwater duration.<br>"
        "• <em>Tail risk</em>: Extreme loss distribution, negative skewness, and catastrophic tail probabilities.<br>"
        "• <em>Capital integrity</em>: Unrealised floating loss drag relative to capital (detects masked losses in open positions).<br>"
        "• <em>Profit stability</em>: Consistency of monthly returns and Sharpe/Sortino ratios across rolling windows.<br>"
        "• <em>Asset concentration</em>: Single-token concentration vs multi-asset diversification risk.<br>"
        "• <em>Liquidity &amp; execution</em>: Slippage risk, order size relative to market depth, and execution friction.<br>"
        "• <em>Sample validity</em>: Statistical significance based on track record length and trade sample size.<br><br>"
        "<strong>Score Basis &amp; Weighting:</strong> "
        "Each verified dimension carries an assigned weight. Unmeasured dimensions default to neutral 50 without penalizing the overall score.",
        "Multi-dimensional fusion algorithm: Baseline score = ∑(w_i × Score_i) / ∑(w_i). "
        "Critical risk dimensions enforce non-compensatory <em>Veto Floors</em>: if any critical dimension (e.g. liquidation risk, "
        "extreme leverage, or unhedged float drag) breaches safety boundaries, the overall risk score is automatically overridden "
        "and clamped to the veto level (up to 100) regardless of strong performance in other dimensions.",
    )
    return _section(
        "Score by risk dimension",
        body + _render_score_basis(result) + theory,
        tone="primary",
        anchor="diem-chieu",
    )


# --------------------------------------------------------------------------- #
# "CHÚ THÍCH GIẢI THÍCH ĐIỂM SỐ" -- khối mà dấu `*` bấm được trên 3 ô điểm
# số hero (`_render_header`) dẫn tới. Nhúng VÀO TRONG mục "Điểm từng chiều
# rủi ro" sẵn có (không phải một `<section>` mới) để giữ đúng bất biến "cùng
# tập id mục" giữa trang LIMITED và trang đầy đủ -- cùng lý do
# `_render_limited_measured_evidence` đã nêu. Dữ liệu đọc qua
# `Agent/backend/web/score_basis.py` (module đó CHỈ tính/gom, không dựng
# HTML); mọi escape/format ở đây.
# --------------------------------------------------------------------------- #


def _percentile_findings_html(components: List[Dict[str, Any]]) -> str:
    """Trích đúng câu "Phân vị mô phỏng: ..." (đã có sẵn tham số/giá trị của
    bot/cỡ quần thể/trung vị quần thể trong chính câu văn, do
    `Agent/backend/bot/analysis/limited.py` viết ra khi chấm bằng phân vị) từ
    `findings` của từng thành phần, thay vì tính lại. `""` khi không thành
    phần nào chấm bằng phân vị (quần thể chưa đủ 10 bot, xem
    `Agent/backend/bot/analysis/population_reference.py`).
    """
    rows = []
    for c in components:
        label = c.get("label") or c.get("name") or "—"
        for finding in c.get("findings") or []:
            if "Percentile" in finding or "percentile" in finding:
                rows.append(f"<li><strong>{_esc(label)}:</strong> {_esc(finding)}</li>")
    if not rows:
        return ""
    return (
        "<p>The dimensions below are scored using the <strong>percentile rank "
        "within the population of scored bots</strong> (not a fixed threshold -- see "
        "<code>Agent/backend/bot/analysis/population_reference.py</code>):</p>"
        "<ul class='findings'>" + "".join(rows) + "</ul>"
    )


def _render_full_score_basis(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence") or {}
    dims = score_basis.full_risk_dimensions(evidence)
    if not dims:
        return ""
    fusion = score_basis.full_fusion_summary(evidence)

    table_rows = []
    for d in dims:
        label = DIMENSION_LABEL_VI.get(d["name"], str(d["name"]))
        status = str(d.get("status") or "AVAILABLE").upper()
        score_val = d.get("score")
        weight_val = d.get("weight")
        conf_val = d.get("confidence")

        score_str = f"{_num(score_val, 0)}/100" if score_val is not None else "—"
        weight_str = f"{weight_val:.1f}x" if weight_val is not None else "1.0x"
        conf_str = f"{conf_val * 100:.0f}%" if conf_val is not None else "—"

        if status == "AVAILABLE":
            badge_html = '<span class="q-badge q-badge-ok">ACTIVE</span>'
            row_cls = ""
        else:
            badge_html = f'<span class="q-badge q-badge-neutral">{_esc(status)}</span>'
            row_cls = "row-unmeasured"

        table_rows.append(
            f'<tr class="{row_cls}">'
            f'<td class="dim-col-name"><strong>{_esc(label)}</strong></td>'
            f'<td class="dim-col-num">{score_str}</td>'
            f'<td class="dim-col-num">{weight_str}</td>'
            f'<td class="dim-col-num">{conf_str}</td>'
            f'<td class="dim-col-status">{badge_html}</td>'
            f'</tr>'
        )

    weighted_avg = fusion.get("weighted_average")
    weighted_str = f"{weighted_avg:.1f}/100" if weighted_avg is not None else "—"
    # `total_weight` is absent from saved assessment records (see
    # `score_basis.full_fusion_summary`'s `has_rich_breakdown`). Formatting it
    # unconditionally crashed every disk-read report, so the weight clause is
    # stated only when the record actually carries the number.
    tot_weight = fusion.get("total_weight")
    has_rich = bool(fusion.get("has_rich_breakdown")) and tot_weight is not None
    final_score = fusion.get("final_score", result.get("risk"))
    final_str = f"{final_score:.0f}/100" if final_score is not None else "—"

    if fusion.get("decided_by") and fusion.get("decided_by") != "WEIGHTED_AVERAGE":
        rule_name = "VETO FLOOR" if fusion["decided_by"] == "VETO_FLOOR" else "EMERGENCY OVERRIDE"
        reasons = "; ".join(_esc(r) for r in fusion.get("veto_reasons", []))
        veto_box = (
            f'<div class="score-basis-alert score-basis-veto">'
            f'<span class="sb-badge-veto">{rule_name}</span> '
            f'Risk elevated to <strong>{final_str}</strong> (Weighted avg: {weighted_str}). '
            f'Trigger: {reasons}'
            f'</div>'
        )
    else:
        if has_rich:
            basis_clause = (
                f"Weighted average across {len(dims)} dimensions, "
                f"total weight: {tot_weight:.1f}"
            )
        else:
            basis_clause = (
                f"Weighted average across {len(dims)} dimensions; "
                "per-dimension weights are not present in this bot's saved record"
            )
        veto_box = (
            f'<div class="score-basis-alert score-basis-normal">'
            f'<span class="sb-badge-normal">WEIGHTED FUSION</span> '
            f'Risk score: <strong>{final_str}</strong> ({basis_clause}).'
            f'</div>'
        )

    risk_html = (
        '<div id="giai-thich-risk" class="score-basis-section">'
        f'<div class="sb-section-header"><strong>Risk Score Composition</strong> ({_num(result.get("risk"), 0)}/100)</div>'
        '<table class="score-basis-table">'
        '<thead><tr>'
        '<th>Dimension</th><th>Score</th><th>Weight</th><th>Confidence</th><th>Status</th>'
        '</tr></thead>'
        f'<tbody>{"".join(table_rows)}</tbody>'
        '</table>'
        f'{veto_box}'
        '</div>'
    )

    quality_html = (
        '<div id="giai-thich-quality" class="score-basis-section">'
        f'<div class="sb-math-col"><span class="sb-label">QUALITY SCORE ({_num(result.get("quality"), 0)}/100)</span>'
        '<span class="sb-desc">Execution consistency & trade expectancy: Profit Factor (40%) + Win Rate (30%) + Calmar Drawdown Ratio (30%).</span></div>'
        '</div>'
    )

    confidence_html = (
        '<div id="giai-thich-confidence" class="score-basis-section">'
        f'<div class="sb-math-col"><span class="sb-label">CONFIDENCE ({_pct(result.get("confidence"), 0)})</span>'
        '<span class="sb-desc">Data Trust (freshness & candle completeness) × Dimension Measurability Ratio.</span></div>'
        '</div>'
    )

    return f'<div class="score-basis-wrap">{risk_html}<div class="score-basis-math-grid">{quality_html}{confidence_html}</div></div>'


def _render_limited_score_basis(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence") or {}
    components = score_basis.limited_risk_components(evidence)
    if not components:
        return ""
    fusion = score_basis.limited_fusion_summary(components)

    table_rows = []
    for c in components:
        label = c.get("label") or c.get("name") or "—"
        status = str(c.get("status") or "AVAILABLE").upper()
        score_val = c.get("score")
        weight_val = c.get("weight")

        score_str = f"{_num(score_val, 0)}/100" if score_val is not None else "—"
        weight_str = f"{weight_val:.1f}x" if weight_val is not None else "1.0x"

        if status == "AVAILABLE":
            badge_html = '<span class="q-badge q-badge-ok">ACTIVE</span>'
            row_cls = ""
        else:
            tag = "CONCEALED" if status == "UNKNOWN_CONCEALED" else "MISSING"
            badge_html = f'<span class="q-badge q-badge-neutral">{tag}</span>'
            row_cls = "row-unmeasured"

        table_rows.append(
            f'<tr class="{row_cls}">'
            f'<td class="dim-col-name"><strong>{_esc(label)}</strong></td>'
            f'<td class="dim-col-num">{score_str}</td>'
            f'<td class="dim-col-num">{weight_str}</td>'
            f'<td class="dim-col-status">{badge_html}</td>'
            f'</tr>'
        )

    weighted_avg = fusion.get("weighted_average")
    weighted_str = f"{weighted_avg:.1f}/100" if weighted_avg is not None else "—"
    final_score = fusion.get("final_score", result.get("risk"))
    final_str = f"{final_score:.0f}/100" if final_score is not None else "—"

    summary_box = (
        f'<div class="score-basis-alert score-basis-normal">'
        f'<span class="sb-badge-normal">LIMITED RECORD</span> '
        f'Risk score: <strong>{final_str}</strong> (Weighted base: {weighted_str}).'
        f'</div>'
    )

    risk_html = (
        '<div id="giai-thich-risk" class="score-basis-section">'
        f'<div class="sb-section-header"><strong>Component Breakdown</strong> ({_num(result.get("risk"), 0)}/100)</div>'
        '<table class="score-basis-table">'
        '<thead><tr>'
        '<th>Component</th><th>Score</th><th>Weight</th><th>Status</th>'
        '</tr></thead>'
        f'<tbody>{"".join(table_rows)}</tbody>'
        '</table>'
        f'{summary_box}'
        '</div>'
    )

    quality_html = (
        '<div id="giai-thich-quality" class="score-basis-section">'
        f'<div class="sb-math-col"><span class="sb-label">QUALITY SCORE ({_num(result.get("quality"), 0)}/100)</span>'
        '<span class="sb-desc">Base 50 pts + Lead days factor + Cumulative PnL sign.</span></div>'
        '</div>'
    )

    confidence_html = (
        '<div id="giai-thich-confidence" class="score-basis-section">'
        f'<div class="sb-math-col"><span class="sb-label">CONFIDENCE ({_pct(result.get("confidence"), 0)})</span>'
        '<span class="sb-desc">Derived from observable history length and data source trust.</span></div>'
        '</div>'
    )

    return f'<div class="score-basis-wrap">{risk_html}<div class="score-basis-math-grid">{quality_html}{confidence_html}</div></div>'


def _render_score_basis(result: Dict[str, Any]) -> str:
    """Toàn bộ khối "CHÚ THÍCH GIẢI THÍCH ĐIỂM SỐ" -- yêu cầu gốc của chủ dự
    án: "nên có sao ở đó để giải thích những tiêu chí và công thức để ra
    được score đấy". Bọc trong MỘT `<details>` (giống mọi khối `_theory`
    khác trong module này) chứ không mở sẵn, để không làm trang dài thêm
    với người không cần đọc -- nhưng trình duyệt tự mở nó khi một dấu `*` ở
    đầu trang dẫn tới một id nằm bên trong (không cần JS, xem `_stat_tile`).

    Nhánh nào (FULL/LIMITED) được chọn theo ĐÚNG hình dạng `evidence` mà
    `_render_dimensions_section` đã dùng để chọn `_render_full_dimension_bars`
    hay `_render_component_bars` -- không có nhánh thứ ba, không đoán.
    """
    evidence = result.get("evidence") or {}
    if isinstance(evidence.get("dimensions"), dict) and evidence.get("dimensions"):
        body = _render_full_score_basis(result)
    elif isinstance(evidence.get("components"), list) and evidence.get("components"):
        body = _render_limited_score_basis(result)
    else:
        return ""
    if not body:
        return ""
    return (
        '<details class="theory score-basis">'
        "<summary>Score explanation notes (*)</summary>"
        f'<div class="theory-body">{body}</div>'
        "</details>"
    )


def _render_full_dimension_bars(
    dimensions: Dict[str, Any], score_breakdown: Dict[str, Any]
) -> str:
    rows: List[_BarRow] = []
    keys = list(DIMENSION_ORDER) + [k for k in dimensions if k not in DIMENSION_ORDER]
    seen = set()
    for key in keys:
        if key in seen or key not in dimensions:
            continue
        seen.add(key)
        dim = dimensions.get(key) or {}
        raw_label = DIMENSION_LABEL_VI.get(key, dim.get("dimension_name") or key)
        status = str(dim.get("status") or "AVAILABLE").upper()
        score = dim.get("score")
        tier = dim.get("tier")

        if status == "AVAILABLE" and _is_finite_number(score):
            val_num = float(score)
            color = _tier_color(tier)
            tier_str = TIER_LABEL_VI.get(str(tier).upper(), tier or "—")
            rows.append(
                _BarRow(
                    raw_label,
                    val_num,
                    color,
                    f"{val_num:.0f} · {tier_str}",
                    info_key=key,
                )
            )
        else:
            findings = dim.get("key_findings")
            note = None
            if isinstance(findings, list):
                for finding in findings:
                    if isinstance(finding, str) and finding.strip():
                        note = finding.strip()
                        break
            rows.append(
                _BarRow(
                    raw_label,
                    None,
                    TIER_COLOR["UNKNOWN"],
                    "not measured",
                    measured=False,
                    info_key=key,
                    note=note,
                )
            )

    measured = [r for r in rows if r.measured and r.value is not None]
    unmeasured = [r for r in rows if not r.measured or r.value is None]
    measured.sort(key=lambda r: float(r.value or 0.0), reverse=True)
    return _horizontal_bars(measured + unmeasured)


def _render_component_bars(components: List[Any]) -> str:
    rows: List[_BarRow] = []
    for comp in components:
        if not isinstance(comp, dict):
            continue
        raw_label = comp.get("label") or comp.get("name") or "—"
        key = comp.get("name") or comp.get("key") or ""
        info_key = key if key in METRIC_FORMULA_INFO else "risk_score"
        status = str(comp.get("status") or "AVAILABLE").upper()
        score = comp.get("score")
        if status == "AVAILABLE" and _is_finite_number(score):
            color = _risk_color(score)
            rows.append(_BarRow(raw_label, float(score), color, f"{float(score):.0f}", info_key=info_key))
        else:
            tag = "concealed" if status == "UNKNOWN_CONCEALED" else "missing data"
            rows.append(
                _BarRow(raw_label, None, TIER_COLOR["UNKNOWN"], tag, measured=False, info_key=info_key)
            )
    return _horizontal_bars(rows)


# --------------------------------------------------------------------------- #
# Section 3.5 -- growth: cumulative equity curve + win/loss composition.
#
# The project owner's own explicit ask ("biểu đồ tăng trưởng") -- everything
# else in this module already existed before that request; this is the
# single most direct answer to it (a cumulative-PnL line is literally what
# "growth" looks like on a chart), so it gets its own section rather than
# being buried as a footnote inside Monte Carlo (forward-looking simulation)
# or trade metrics (a table of aggregates, not a picture of the trajectory).
# --------------------------------------------------------------------------- #

# `evidence.closed_trade_series` is the ONE real key `WebDataService.analyze()`
# populates for a FULL result (see Agent/backend/web/data.py's
# `_full_result`/`_closed_trade_series_from_bot_result`): a list of
# `{"close_time": <int ms>, "realized_pnl": <float>}` rows, CLOSED trades
# only, already sorted ascending by close_time. An earlier version of
# `_extract_trade_pnls` below speculatively probed five different
# plausible-sounding key paths (`evidence.closed_trades`,
# `evidence.trade_ledger`, `evidence.trade_ledger_summary`, `mc.trade_pnls`,
# a bare top-level `trade_pnls`) because at the time NONE of them were ever
# actually populated -- that guesswork was dead code dressed up as
# future-proofing. Now that data.py exposes a real, contractual key, reading
# it directly is both simpler and correct; there is nothing left to guess.


def _extract_trade_pnls(result: Dict[str, Any]) -> Optional[List[float]]:
    """Per-trade realized-PnL sequence for the cumulative equity curve,
    read from `evidence.closed_trade_series` (see the module-level comment
    above for what that key contractually contains).

    Defensively re-sorts by `close_time` when every row carries one, rather
    than trusting the input's ordering blindly -- data.py's own contract
    already guarantees ascending order, but this keeps a hand-built
    dict (e.g. in a test) or any future caller that forgets to sort correct
    too, at negligible cost.

    Returns `None` (never `[]`) whenever the key is missing, not a
    non-empty list, or carries no usable numeric `realized_pnl` at all --
    true for LIMITED/NOT_FOUND results (whose `evidence` shape never has
    this key at all) and for a FULL result whose bot has zero closed trades
    -- so callers can use a single falsy check to mean "hide this chart"
    (see `_render_growth_curve`'s own "đừng bịa" rule: there is nothing
    honest to draw).
    """
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return None
    series = evidence.get("closed_trade_series")
    if not isinstance(series, list) or not series:
        return None

    rows = [row for row in series if isinstance(row, dict)]
    if rows and all(_is_finite_number(row.get("close_time")) for row in rows):
        rows = sorted(rows, key=lambda row: row["close_time"])

    pnls = [
        float(row["realized_pnl"])
        for row in rows
        if _is_finite_number(row.get("realized_pnl"))
    ]
    return pnls or None


def _render_growth_curve(result: Dict[str, Any]) -> str:
    pnls = _extract_trade_pnls(result)
    if not pnls:
        return ""
    cumulative: List[float] = []
    running = 0.0
    for v in pnls:
        running += v
        cumulative.append(running)
    chart = _line_chart(cumulative, y_unit=" USDT")
    if not chart:
        return ""
    return (
        '<div class="growth-curve-panel">'
        '<h3>Cumulative capital curve by closed trade</h3>'
        f'<div class="growth-chart-wrapper">{chart}</div>'
        '</div>'
    )


def _render_win_loss_composition(result: Dict[str, Any]) -> str:
    """Two pies, side by side: how many trades win vs. lose, and how much
    MONEY was won vs. lost gross. Project owner's own explicit ask -- these
    two numbers diverging (high win rate, large gross loss) is exactly the
    "lệch payoff" signature the task calls out, and it is only visible when
    both pies are read together.
    """
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return ""
    perf = evidence.get("performance")
    if not isinstance(perf, dict):
        return ""

    trade_count = perf.get("trade_count")
    win_rate = perf.get("win_rate")
    if not (_is_finite_number(trade_count) and _is_finite_number(win_rate)):
        return ""
    total = int(round(float(trade_count)))
    if total <= 0:
        return ""

    win_count = max(0, min(int(round(total * float(win_rate) / 100.0)), total))
    loss_rate = perf.get("loss_rate")
    if _is_finite_number(loss_rate):
        loss_count = max(
            0, min(int(round(total * float(loss_rate) / 100.0)), total - win_count)
        )
    else:
        loss_count = max(total - win_count, 0)
    breakeven_count = max(total - win_count - loss_count, 0)

    count_slices: List[Tuple[str, Optional[float], str]] = [
        ("Winning trades", float(win_count), "#16a34a"),
        ("Losing trades", float(loss_count), "#dc2626"),
    ]
    if breakeven_count:
        count_slices.append(("Break-even", float(breakeven_count), "#9ca3af"))
    count_pie = _pie_chart(count_slices)

    average_win = perf.get("average_win")
    average_loss = perf.get("average_loss")
    profit_pie = ""
    if (
        _is_finite_number(average_win)
        and _is_finite_number(average_loss)
        and win_count > 0
        and loss_count > 0
    ):
        gross_profit = max(float(average_win), 0.0) * win_count
        gross_loss = abs(float(average_loss)) * loss_count
        if gross_profit > 0 or gross_loss > 0:
            profit_pie = _pie_chart(
                [
                    ("Gross profit", gross_profit, "#16a34a"),
                    ("Gross loss", gross_loss, "#dc2626"),
                ]
            )

    if not count_pie and not profit_pie:
        return ""

    cells = ""
    if count_pie:
        cells += f'<div class="pie-card-stacked"><h4>Trade count breakdown</h4>{count_pie}</div>'
    if profit_pie:
        cells += f'<div class="pie-card-stacked"><h4>Gross profit/loss breakdown (USDT)</h4>{profit_pie}</div>'
    stacked = f'<div class="pie-stack-vertical">{cells}</div>'

    return f'<div class="win-loss-composition-panel"><h3>Win/loss composition</h3>{stacked}</div>'


def _render_growth_section(result: Dict[str, Any]) -> str:
    curve_html = _render_growth_curve(result)
    composition_html = _render_win_loss_composition(result)
    if not curve_html and not composition_html:
        return ""
    if curve_html and composition_html:
        dashboard_body = (
            '<div class="growth-dashboard-grid">'
            f'<div class="growth-dashboard-left">{curve_html}</div>'
            f'<div class="growth-dashboard-right">{composition_html}</div>'
            '</div>'
        )
    else:
        dashboard_body = curve_html or composition_html

    growth_theory = _theory(
        "<strong>Section overview.</strong> Evaluates capital trajectory and payoff distribution to verify whether profitability "
        "stems from a consistent, repeatable edge or masks an asymmetric high-risk profile.<br><br>"
        "<strong>Cumulative capital curve:</strong> "
        "Chronological trajectory of realized USDT equity across all completed closed trades. "
        "Highlights historical peak equity runs, drawdown valleys, and recovery duration. Excludes open positions to isolate closed-book execution.<br><br>"
        "<strong>Win/loss composition &amp; Payoff asymmetry:</strong> "
        "Displays trade count distribution (left) alongside gross dollar profit/loss distribution (right). "
        "Reading both charts together reveals <em>payoff skew</em>: a high win rate (e.g. 90%+) paired with gross loss dominating "
        "the profit pie is the definitive signature of an asymmetric strategy (such as martingale or grid holding losers) where occasional "
        "severe losses wipe out dozens of accumulated small wins.",
        "Equity curve: Equity(t) = Initial + ∑ PnL(i) directly calculated from verified OKX closed trades. "
        "Gross profit = N_wins × Average_Win; Gross loss = N_losses × |Average_Loss|. "
        "Profit Factor = Gross Profit / Gross Loss. All metrics reflect actual ledger timestamps.",
    )
    return _section("Growth & outcome composition", dashboard_body + growth_theory, anchor="tang-truong")


# --------------------------------------------------------------------------- #
# Section 4 -- Monte Carlo
# --------------------------------------------------------------------------- #


def _render_monte_carlo(result: Dict[str, Any]) -> str:
    mc = result.get("mc")
    if not isinstance(mc, dict) or not mc:
        return ""

    parts: List[str] = []

    if mc.get("deferred_loss_bias"):
        parts.append(
            '<div class="notice notice-warning">This simulation is biased optimistic:'
            " the bot is holding an unrealised loss, and the distribution below is"
            " computed only on closed trades, so it does NOT see that loss -- the real"
            " probability is worse than the number shown.</div>"
        )

    # Mẫu mỏng (10 <= n < 20, xem MonteCarloSimulationEngine.THIN_SAMPLE_SIZE)
    # -- điển hình cho một bot LIMITED chỉ có ~12 điểm PnL tuần, nhưng cũng
    # có thể xảy ra ở một bot FULL ít lệnh. Câu cảnh báo được ĐỌC từ chính
    # `mc["warnings"]` (engine đã tự viết đúng một câu cho việc này, xem
    # THIN_SAMPLE_WARNING_VI), không viết lại ở đây -- chỉ khi payload nào
    # đó (vd. một fixture test cũ) thiếu hẳn `warnings` mới dùng câu dự
    # phòng bên dưới, đọc kiểu phòng thủ đúng như engine mô tả.
    if mc.get("sample_is_thin"):
        thin_warnings = mc.get("warnings")
        thin_text = (
            "; ".join(_esc(w) for w in thin_warnings if isinstance(w, str))
            if isinstance(thin_warnings, list)
            else ""
        )
        if not thin_text:
            thin_text = (
                f"Thin sample ({_int_text(mc.get('sample_size'))} observations): the "
                "simulation still runs, but should only be read as a reference range, "
                "not a firm estimate -- a bootstrap percentile can only resolve to "
                "about 1/n, so at this sample size the figures at both tails (the 5th "
                "percentile, probability of ruin, the 95th percentile of drawdown) "
                "carry a large standard error."
            )
        parts.append(f'<div class="notice notice-warning">{thin_text}</div>')

    # 1. Row 1: Unified Multi-Horizon Simulation & Tail Risk Distribution Chart
    unified_chart = _render_unified_monte_carlo_chart(mc)
    if unified_chart:
        parts.append(f'<div class="mc-full-row">{unified_chart}</div>')
    else:
        # Fallback if horizon_scenarios is empty
        fan_rows = [
            ("P05", max(-100.0, float(mc.get("profit_pct_p05"))) if _is_finite_number(mc.get("profit_pct_p05")) else None),
            ("P25", max(-100.0, float(mc.get("profit_pct_p25"))) if _is_finite_number(mc.get("profit_pct_p25")) else None),
            ("P50", mc.get("profit_pct_p50")),
            ("P75", mc.get("profit_pct_p75")),
            ("P95", mc.get("profit_pct_p95")),
        ]
        chart = _diverging_bars(fan_rows)
        if chart:
            parts.append(f'<div class="mc-full-row">{_subsection("End-of-horizon outcome percentiles", chart)}</div>')

    # 2. Row 2: Multi-Horizon Scenario Matrix
    horizon_comp_html = _render_horizon_comparison(mc)
    if horizon_comp_html:
        parts.append(f'<div class="mc-full-row">{horizon_comp_html}</div>')

    # 3. Row 3: Outcome Percentile Spectrum (Full 9-tier confidence distribution)
    spectrum_html = _render_percentile_spectrum(mc)
    if spectrum_html:
        parts.append(f'<div class="mc-full-row">{spectrum_html}</div>')

    # 4. Row 4: Key Probabilities, Simulated Risk & Efficiency, Losing Streak Table
    key_prob_html = _render_key_probabilities(mc)
    if key_prob_html:
        parts.append(f'<div class="mc-full-row">{key_prob_html}</div>')

    body = "".join(p for p in parts if p)
    if not body:
        return ""
    # One methodology drawer for the whole section -- covers all sub-sections.
    body += _theory(
        "<strong>Section overview.</strong> This section runs a stationary-bootstrap "
        "Monte Carlo simulation across three trade horizons and reports the full "
        "outcome distribution, tail risk, ruin probability, and streak risk in one "
        "unified view. Every number here is a <em>simulated</em> statistic, not a "
        "realised figure.<br><br>"
        "<strong>Horizon Distribution Chart:</strong> "
        "Box-and-whisker columns for SHORT / MEDIUM / LONG horizons. Each column shows the P05&ndash;P50 "
        "downside band (red) and the P50&ndash;P95 upside band (green) with the P50 median marker (amber). "
        "Whiskers extend to the full P05&ndash;P95 range. The Breakeven (0%) line and Drawdown indicator "
        "are overlaid. <em>PoP</em> badge at the top = Probability of Profit. "
        "<em>DD</em> = Median maximum drawdown for that horizon.<br><br>"
        "<strong>Multi-horizon comparison table:</strong> "
        "<em>Sample</em> = number of trades simulated. "
        "<em>Profit Chance</em> = PoP (%). "
        "<em>Median (P50)</em> = expected return at the middle scenario. "
        "<em>Range (P05&rarr;P95)</em> = 90% confidence interval. "
        "<em>Max DD</em> = median worst drawdown. "
        "<em>Loss &middot; Ruin</em> = P(loss at horizon end) &middot; P(full ruin at &minus;100%).<br><br>"
        "<strong>Detailed percentile spectrum:</strong> "
        "Full 9-tier distribution from Worst to Best. "
        "<em>P05</em> = Stress VaR (5th percentile, worst realistic scenario). "
        "<em>P25/P75</em> = Interquartile range (Q1/Q3). "
        "<em>Skew badge</em> = upside-to-downside span ratio; Positive Skew (&ge;1.4&times;) means "
        "upside tail is disproportionately wider than downside tail.<br><br>"
        "<strong>Key probabilities &amp; simulated risk:</strong> "
        "<em>VaR (95%)</em> = Value at Risk &mdash; the 5th-pct return threshold (max expected loss at 95% confidence). "
        "<em>CVaR (95%)</em> = Conditional VaR / Expected Shortfall &mdash; average loss across the worst 5% tail paths. "
        "<em>MAR</em> = annualised return &divide; max drawdown (median across paths); &ge;2.0 = excellent, &ge;0.5 = acceptable. "
        "<em>PF</em> = Profit Factor &mdash; gross wins &divide; gross losses (median); &ge;1.25 = healthy edge. "
        "<em>Losing streak excess</em> = max(0, observed streak probability &minus; Binomial baseline); "
        "positive excess signals loss clustering beyond random chance.",
        "Stationary bootstrap (Politis &amp; Romano 1994): "
        f"{_int_text(mc.get('iterations') or 10000)} resampled paths with random block lengths, "
        "re-run at SHORT = 0.2&times;, MEDIUM = 1.0&times;, LONG = 3.0&times; the observed trade count. "
        "Terminal return percentiles are computed from the empirical distribution of end-of-path equity; "
        "any path reaching &minus;100% is absorbed at the liquidation boundary and reported as &minus;100%. "
        "Drawdown = max peak-to-trough decline over the path; the reported value is the median across all paths. "
        "Streak baseline = Markov-binomial model at observed loss rate; excess = observed minus analytical, "
        "clamped at zero so only clustering above chance is counted. "
        "VaR / CVaR are read directly from the simulated terminal return distribution (5th percentile / "
        "expected value below 5th percentile). MAR and PF are computed per path then the median is reported.",
    )
    return _section("Monte Carlo simulation", body, anchor="monte-carlo")


def _subsection(title: str, chart: str, theory: str = "") -> str:
    if not chart:
        return ""
    return f"<h3>{_esc(title)}</h3>{chart}{theory}"


def _render_percentile_spectrum(mc: Dict[str, Any]) -> str:
    """Detailed percentile spectrum of terminal return distribution across 10,000 bootstrap paths.
    Provides the full quantitative panorama: Worst, P05, P10, P25, P50, P75, P90, P95, Best.
    """
    p05 = mc.get("profit_pct_p05")
    p50 = mc.get("profit_pct_p50")
    p95 = mc.get("profit_pct_p95")
    if not any(_is_finite_number(v) for v in (p05, p50, p95)):
        return ""

    p10 = mc.get("profit_pct_p10")
    p25 = mc.get("profit_pct_p25")
    p75 = mc.get("profit_pct_p75")
    p90 = mc.get("profit_pct_p90")
    worst = mc.get("profit_pct_worst")
    best = mc.get("profit_pct_best")

    tiers = [
        ("Worst", worst, "Tail risk floor"),
        ("P05", p05, "5th pct (Stress VaR)"),
        ("P10", p10, "10th percentile"),
        ("P25", p25, "1st Quartile (Q1)"),
        ("P50", p50, "Median Expected"),
        ("P75", p75, "3rd Quartile (Q3)"),
        ("P90", p90, "90th percentile"),
        ("P95", p95, "95th pct (Upside cap)"),
        ("Best", best, "Maximum upside"),
    ]

    grid_cards = []
    for label, val, sublabel in tiers:
        if not _is_finite_number(val):
            continue
        v_num = float(val)
        v_str = f"{v_num:+.1f}%" if v_num != 0 else "0.0%"
        if v_num <= -100.0:
            v_str = "-100% (Ruin)"
        card_color = "var(--down, #ef4444)" if v_num < 0 else ("var(--up, #10b981)" if v_num > 0 else "var(--ink, #ffffff)")
        grid_cards.append(
            f'<div class="mc-spec-card">'
            f'  <div class="mc-spec-top">'
            f'    <span class="mc-spec-lbl">{label}</span>'
            f'    <span class="mc-spec-sub">{sublabel}</span>'
            f'  </div>'
            f'  <div class="mc-spec-val" style="color:{card_color};">{v_str}</div>'
            f'</div>'
        )

    if not grid_cards:
        return ""

    # Skew / Asymmetry calculation if P05, P50, P95 available
    skew_badge = ""
    if _is_finite_number(p05) and _is_finite_number(p50) and _is_finite_number(p95):
        p05_f = float(p05)
        p50_f = float(p50)
        p95_f = float(p95)
        upside_span = max(0.0, p95_f - p50_f)
        downside_span = max(0.01, p50_f - max(-100.0, p05_f))
        ratio = upside_span / downside_span if downside_span > 0 else 1.0
        if ratio >= 1.4:
            skew_badge = f'<span class="mc-skew-badge positive" title="Upside tail is {ratio:.1f}x wider than downside tail (positive return skew)">Positive Skew ({ratio:.1f}:1) ✔</span>'
        elif ratio <= 0.7:
            inv_ratio = 1.0 / ratio if ratio > 0 else 99.0
            skew_badge = f'<span class="mc-skew-badge negative" title="Downside tail is {inv_ratio:.1f}x wider than upside tail (martingale / tail risk)">Negative Skew ({inv_ratio:.1f}:1) ⚠</span>'
        else:
            skew_badge = f'<span class="mc-skew-badge balanced" title="Outcome distribution is symmetric around median">Symmetric ({ratio:.1f}:1)</span>'

    header_html = (
        '<div class="mc-spec-header">'
        '  <div>'
        '    <h4 class="mc-spec-title">Detailed percentile spectrum</h4>'
        '    <div class="mc-spec-subtitle">Quantitative outcome distribution across confidence percentiles (base horizon)</div>'
        '  </div>'
        f'  <div>{skew_badge}</div>'
        '</div>'
    )

    body_content = (
        f'<div class="mc-spec-panel">'
        f'{header_html}'
        f'<div class="mc-spec-grid">{"".join(grid_cards)}</div>'
        f'</div>'
    )
    return _subsection("Outcome percentile spectrum", body_content, "")


def _render_horizon_comparison(mc: Dict[str, Any]) -> str:
    scenarios = mc.get("horizon_scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return ""
    by_label = {s.get("label"): s for s in scenarios if isinstance(s, dict)}
    rows_html = []
    short_s = by_label.get("SHORT")
    long_s = by_label.get("LONG")

    for key in ("SHORT", "MEDIUM", "LONG"):
        s = by_label.get(key)
        if not s:
            continue
        trades = s.get("horizon_trades")
        pop = s.get("probability_of_profit")
        p_loss = s.get("p_loss_after_horizon")
        p_ruin = s.get("p_ruin")
        p50 = s.get("profit_pct_p50")
        p05 = s.get("profit_pct_p05")
        p95 = s.get("profit_pct_p95")
        dd = s.get("median_max_drawdown")

        pop_num = float(pop) if _is_finite_number(pop) else 0.0
        pop_pct_str = _format_prob_pct(pop)
        loss_pct_str = _format_prob_pct(p_loss)
        ruin_pct_str = _format_prob_pct(p_ruin)

        bar_w = max(0.0, min(100.0, pop_num))
        if pop_num >= 50.0:
            color = "#10b981"
        elif pop_num >= 20.0:
            color = "#f59e0b"
        else:
            color = "#ef4444"

        ruin_color = "#ef4444" if (_is_finite_number(p_ruin) and float(p_ruin) > 0.05) else "var(--muted, #64748b)"
        loss_color = "#ef4444" if (_is_finite_number(p_loss) and float(p_loss) >= 60.0) else "var(--ink-2, #94a3b8)"

        trades_str = f"{_int_text(trades)} trds"
        row_tooltip = f"Monte Carlo bootstrap across 10,000 scenarios over {_int_text(trades)} trades"

        # P50 Median return
        if _is_finite_number(p50):
            p50_f = float(p50)
            p50_str = f"{p50_f:+.1f}%" if p50_f != 0 else "0.0%"
            p50_color = "var(--up, #10b981)" if p50_f > 0 else ("var(--down, #ef4444)" if p50_f < 0 else "var(--ink, #ffffff)")
        else:
            p50_str = "—"
            p50_color = "var(--muted, #64748b)"

        # P05 -> P95 Range
        if _is_finite_number(p05) and _is_finite_number(p95):
            p05_f = float(p05)
            p95_f = float(p95)
            p05_disp = "-100% (Ruin)" if p05_f <= -100.0 else f"{p05_f:+.1f}%"
            p95_disp = f"{p95_f:+.1f}%"
            range_str = f"{p05_disp} &rarr; {p95_disp}"
        else:
            range_str = "—"

        # Max Drawdown
        if _is_finite_number(dd):
            dd_str = f"-{float(dd):.1f}%"
        else:
            dd_str = "—"

        rows_html.append(
            f'<tr class="hz-matrix-row" data-hz="{key.lower()}" title="{_esc(row_tooltip)}">'
            f'<td class="col-hz"><span class="hz-pill hz-pill-{key.lower()}">{key}</span></td>'
            f'<td class="col-sample"><span class="hz-sample">{trades_str}</span></td>'
            f'<td class="col-pop">'
            f'  <div class="hz-progress-wrap">'
            f'    <div class="hz-progress-track"><div class="hz-progress-bar" style="width:{bar_w:.1f}%;background:{color};"></div></div>'
            f'    <span class="hz-progress-val" style="color:{color};">{pop_pct_str}</span>'
            f'  </div>'
            f'</td>'
            f'<td class="col-med" style="color:{p50_color};font-weight:700;">{p50_str}</td>'
            f'<td class="col-range"><span class="hz-range-val">{range_str}</span></td>'
            f'<td class="col-dd" style="color:var(--down, #ef4444);font-family:var(--mono);font-weight:600;">{dd_str}</td>'
            f'<td class="col-loss-ruin">'
            f'  <span class="hz-loss-val" style="color:{loss_color};">{loss_pct_str}</span>'
            f'  <span class="hz-divider">&middot;</span>'
            f'  <span class="hz-ruin-val" style="color:{ruin_color};">{ruin_pct_str}</span>'
            f'</td>'
            f'</tr>'
        )

    if not rows_html:
        return ""

    table_html = (
        '<div class="hz-matrix-wrap">'
        '<table class="hz-matrix-table">'
        '<thead><tr>'
        '<th class="col-hz" title="Simulation horizon (Short / Medium / Long)">Horizon</th>'
        '<th class="col-sample" title="Sample size in trades for this horizon">Sample</th>'
        '<th class="col-pop" title="Probability of ending with profit (Profit &gt; 0)">Profit Chance</th>'
        '<th class="col-med" title="Median simulated return across 10,000 paths">Median (P50)</th>'
        '<th class="col-range" title="90% confidence outcome interval from 5th to 95th percentile">Range (P05 &rarr; P95)</th>'
        '<th class="col-dd" title="Median maximum drawdown suffered">Max DD</th>'
        '<th class="col-loss-ruin" title="Probability of loss at horizon end &middot; Probability of ruin">Loss &middot; Ruin</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
        '</div>'
    )

    insight_html = ""
    stability_label = mc.get("horizon_stability_label")
    if short_s and long_s:
        s_pop = float(short_s.get("probability_of_profit") or 0.0)
        l_pop = float(long_s.get("probability_of_profit") or 0.0)

        if stability_label in ("HOLDS ONLY AT SHORT HORIZON", "CHỈ ỔN Ở NGẮN HẠN") or (s_pop >= 50.0 and l_pop < 50.0):
            callout_icon = "⚠"
            callout_class = "hz-insight-warn"
            callout_title = "HOLDS ONLY AT SHORT HORIZON"
            callout_msg = f"Profit edge ({_pct(s_pop, 1)}) decays sharply over longer horizons ({_pct(l_pop, 1)}); strategy relies on short sample."
        elif stability_label in ("NEEDS MORE TIME", "CẦN THỜI GIAN") or (s_pop < 50.0 and l_pop >= 50.0):
            callout_icon = "⏳"
            callout_class = "hz-insight-info"
            callout_title = "NEEDS MORE TIME TO CONVERGE"
            callout_msg = f"Requires sufficient trade sample to realise statistical edge ({_pct(s_pop, 1)} &rarr; {_pct(l_pop, 1)})."
        elif stability_label in ("STABLE ACROSS HORIZONS", "ỔN ĐỊNH MỌI HORIZON") or (s_pop >= 50.0 and l_pop >= 50.0):
            if s_pop >= 50.0 and l_pop >= 50.0:
                callout_icon = "✔"
                callout_class = "hz-insight-positive"
                callout_title = "STABLE ACROSS HORIZONS"
                callout_msg = f"Profit chance remains solid ({_pct(s_pop, 1)} &rarr; {_pct(l_pop, 1)}), confirming persistent statistical edge."
            else:
                callout_icon = "⚡"
                callout_class = "hz-insight-decay"
                callout_title = "PERSISTENT NEGATIVE EDGE"
                callout_msg = f"Profit probability remains depressed across all simulated horizons ({_pct(s_pop, 1)} &rarr; {_pct(l_pop, 1)})."
        else:
            callout_icon = "ℹ"
            callout_class = "hz-insight-info"
            callout_title = "MULTI-HORIZON OUTCOME"
            callout_msg = f"Profit chance varies {_pct(s_pop, 1)} &rarr; {_pct(l_pop, 1)} across horizons."

        insight_html = (
            f'<div class="hz-insight-callout {callout_class}">'
            f'<span class="hz-insight-icon">{callout_icon}</span>'
            f'<div class="hz-insight-body"><strong>{callout_title}:</strong> {callout_msg}</div>'
            f'</div>'
        )
    elif stability_label:
        insight_html = (
            f'<div class="hz-insight-callout hz-insight-info">'
            f'<span class="hz-insight-icon">ℹ</span>'
            f'<div class="hz-insight-body"><strong>INSIGHT:</strong> {_esc(stability_label)}</div>'
            f'</div>'
        )

    exceeds_html = ""
    if mc.get("horizon_exceeds_observed"):
        days = mc.get("horizon_calendar_days")
        span = mc.get("observed_span_days")
        detail = (
            f" (simulated \u2248 {_num(days, 0)} days, only"
            f" {_num(span, 0)} days of data actually observed)"
            if _is_finite_number(days) and _is_finite_number(span)
            else ""
        )
        exceeds_html = (
            '<div class="notice notice-warning" style="margin-top:0.5rem;font-size:11.5px;padding:6px 10px;">The simulated horizon is longer than'
            f" the actual observed data{detail}: this is an EXTRAPOLATION beyond the"
            " observed data, not a validated result.</div>"
        )
    return _subsection(
        "Multi-horizon comparison",
        f'{table_html}{insight_html}{exceeds_html}',
        "",
    )


def _render_unified_monte_carlo_chart(mc: Dict[str, Any]) -> str:
    """Biểu đồ hợp nhất toàn diện Monte Carlo: kết hợp cả 3 yếu tố cốt tử:
      1. Phân vị kết cục (P05..P95) chặn sàn thanh lý -100.0%
      2. Mức độ sụt giảm tối đa (Median & Worst Drawdown)
      3. Diễn tiến xác suất có lãi & cháy vốn theo đa kỳ hạn (Short/Medium/Long)
    trên một khung nhìn trực quan chuẩn mực tài chính, hoàn toàn không đè chữ/nhãn.
    """
    scenarios = mc.get("horizon_scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return ""
    by_label = {s.get("label"): s for s in scenarios if isinstance(s, dict)}
    valid_scenarios = []
    for key in ("SHORT", "MEDIUM", "LONG"):
        s = by_label.get(key)
        if s and isinstance(s, dict):
            valid_scenarios.append((key, s))
    if not valid_scenarios:
        return ""

    width = 800.0
    height = 420.0
    pad_l = 80.0
    pad_r = 105.0
    pad_t = 48.0
    pad_b = 68.0
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    # --- Y domain -------------------------------------------------------- #
    lows: List[float] = []
    highs: List[float] = []
    ruin_risk = False
    for _, s in valid_scenarios:
        raw_05 = s.get("profit_pct_p05")
        p05_v = float(raw_05) if _is_finite_number(raw_05) else -100.0
        if p05_v <= -100.0:
            ruin_risk = True
        lows.append(max(-100.0, p05_v))
        dd_v = s.get("median_max_drawdown")
        if _is_finite_number(dd_v):
            lows.append(max(-100.0, -float(dd_v)))
        v = s.get("profit_pct_p95")
        if _is_finite_number(v):
            highs.append(float(v))
        pr = s.get("p_ruin")
        if _is_finite_number(pr) and float(pr) > 0.05:
            ruin_risk = True

    data_low = min(lows) if lows else -100.0
    data_high = max(highs) if highs else 10.0
    # Breakeven is always on the axis: it is the line every reader compares to.
    data_low = min(data_low, 0.0)
    data_high = max(data_high, 0.0)

    if ruin_risk:
        y_floor_val = -100.0
    else:
        headroom = max(6.0, (data_high - data_low) * 0.12)
        y_floor_val = math.floor((data_low - headroom) / 10.0) * 10.0
    y_ceil_val = math.ceil((data_high + max(6.0, (data_high - data_low) * 0.12)) / 10.0) * 10.0
    if y_ceil_val <= y_floor_val:
        y_ceil_val = y_floor_val + 10.0
    y_span = max(y_ceil_val - y_floor_val, 1.0)

    def to_y(val: float) -> float:
        c_val = max(y_floor_val, min(y_ceil_val, val))
        ratio = (c_val - y_floor_val) / y_span
        return (pad_t + plot_h) - ratio * plot_h

    y_ruin = to_y(-100.0)
    y_zero = to_y(0.0)

    svg_parts: List[str] = []

    # 1. Background grid with dynamic step
    raw_step = y_span / 5.0
    magnitude = 10.0 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 10.0
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        step = candidate * magnitude
        if step >= raw_step:
            break
    tick = math.ceil(y_floor_val / step) * step
    while tick <= y_ceil_val + 1e-9:
        y_t = to_y(tick)
        if abs(tick) > 1e-9 and pad_t + 6 <= y_t <= pad_t + plot_h - 6:
            svg_parts.append(_line(pad_l, y_t, pad_l + plot_w, y_t, stroke="var(--mc-grid-line, #334155)", width=1.0, dash="4,4", extra='opacity="0.6"'))
            svg_parts.append(_text(pad_l - 8, y_t + 4, f"{tick:+.0f}%", anchor="end", fill="var(--mc-grid-text, #94a3b8)", extra='font-size="10" font-family="var(--mono)"'))
        tick += step

    # Ruin floor
    if ruin_risk:
        svg_parts.append(_line(pad_l, y_ruin, pad_l + plot_w, y_ruin, stroke="var(--down, #dc2626)", width=2.0, dash="6,4"))
        svg_parts.append(_text(pad_l - 8, y_ruin + 4, "-100%", anchor="end", fill="var(--down, #ef4444)", extra='font-size="10" font-weight="bold"'))
        svg_parts.append(_rect(pad_l + 4, y_ruin - 16, 175, 15, fill="var(--mc-pill-bg, #0b111e)", rx=3.0, extra='stroke="var(--down, #dc2626)" stroke-width="0.75"'))
        svg_parts.append(_text(pad_l + 8, y_ruin - 5, "RUIN / LIQUIDATION FLOOR", fill="var(--down, #ef4444)", extra='font-size="9.5" font-weight="bold"'))

    # Breakeven line (0%) with anti-bleed pill
    svg_parts.append(_line(pad_l, y_zero, pad_l + plot_w, y_zero, stroke="var(--mc-be-line, rgba(255, 255, 255, 0.35))", width=1.5, extra='opacity="0.5"'))
    svg_parts.append(_text(pad_l - 8, y_zero + 4, "0%", anchor="end", fill="var(--mc-be-text, #94a3b8)", extra='font-weight="bold" font-size="10"'))
    svg_parts.append(_rect(pad_l + 4, y_zero - 15, 68, 15, fill="var(--mc-pill-bg, #0b111e)", rx=3.0, extra='stroke="var(--mc-pill-border, #334155)" stroke-width="0.75"'))
    svg_parts.append(_text(pad_l + 8, y_zero - 4, "Breakeven", anchor="start", fill="var(--mc-be-text, #94a3b8)", extra='font-size="9.5" font-weight="600"'))

    n_cols = len(valid_scenarios)
    col_x_list = []
    for i in range(n_cols):
        cx = pad_l + plot_w * (2 * i + 1) / (2 * n_cols)
        col_x_list.append(cx)

    # 2. Shaded Fan Ribbons connecting columns
    if n_cols >= 2:
        p95_points = []
        p50_points = []
        p05_points = []
        for i, (_, s) in enumerate(valid_scenarios):
            cx = col_x_list[i]
            p95_val = float(s.get("profit_pct_p95") or 0.0)
            p50_val = float(s.get("profit_pct_p50") or 0.0)
            raw_05 = s.get("profit_pct_p05")
            p05_val = float(raw_05) if _is_finite_number(raw_05) else -100.0
            p95_points.append((cx, to_y(p95_val)))
            p50_points.append((cx, to_y(p50_val)))
            p05_points.append((cx, to_y(max(-100.0, p05_val))))

        poly_upper_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in p95_points)
        poly_upper_pts += " " + " ".join(f"{x:.1f},{y:.1f}" for x, y in reversed(p50_points))
        svg_parts.append(f'<polygon points="{poly_upper_pts}" fill="var(--up, #10b981)" fill-opacity="0.14" />')

        poly_lower_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in p50_points)
        poly_lower_pts += " " + " ".join(f"{x:.1f},{y:.1f}" for x, y in reversed(p05_points))
        svg_parts.append(f'<polygon points="{poly_lower_pts}" fill="var(--down, #ef4444)" fill-opacity="0.14" />')

        med_path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(p50_points))
        svg_parts.append(f'<path d="{med_path}" fill="none" stroke="var(--amber, #f59e0b)" stroke-width="2" stroke-dasharray="4,3" />')

    # 3. Render Columns with Zero-Collision Positioning Engine
    for i, (key, s) in enumerate(valid_scenarios):
        cx = col_x_list[i]
        trades = s.get("horizon_trades")
        pop = s.get("probability_of_profit")
        p_ruin = s.get("p_ruin")
        p95_val = float(s.get("profit_pct_p95") or 0.0)
        p50_val = float(s.get("profit_pct_p50") or 0.0)
        raw_p05 = s.get("profit_pct_p05")
        p05_val = float(raw_p05) if _is_finite_number(raw_p05) else -100.0
        dd_val = float(s.get("median_max_drawdown") or 0.0)

        is_liquidated = p05_val <= -100.0
        clamped_p05 = max(-100.0, p05_val)

        y_p95 = to_y(p95_val)
        y_p50 = to_y(p50_val)
        y_p05 = to_y(clamped_p05)

        # Whisker line
        svg_parts.append(_line(cx, y_p05, cx, y_p95, stroke="var(--mc-whisker, #64748b)", width=2.0))

        # Upper box (P50 to P95)
        box_w = 48.0
        box_x = cx - box_w / 2.0
        h_upper = max(2.0, y_p50 - y_p95)
        svg_parts.append(_rect(box_x, y_p95, box_w, h_upper, fill="var(--up, #10b981)", rx=3.0, extra='opacity="0.85"'))

        # Lower box (P05 to P50)
        h_lower = max(2.0, y_p05 - y_p50)
        svg_parts.append(_rect(box_x, y_p50, box_w, h_lower, fill="var(--down, #ef4444)", rx=3.0, extra='opacity="0.85"'))

        # --- Median Marker & Label with Collision Protection ---
        if min(h_upper, h_lower) < 18.0:
            svg_parts.append(_line(cx - box_w / 2.0 - 2, y_p50, cx + box_w / 2.0 + 2, y_p50, stroke="var(--amber, #f59e0b)", width=2.5))
            tag_w = 68.0
            tag_h = 18.0
            tag_x = cx - box_w / 2.0 - 8.0
            svg_parts.append(_line(cx - box_w / 2.0, y_p50, tag_x, y_p50, stroke="var(--amber, #f59e0b)", width=1.2, dash="2,2"))
            svg_parts.append(_rect(tag_x - tag_w, y_p50 - tag_h / 2.0, tag_w, tag_h, fill="var(--mc-pill-bg, #0b111e)", rx=3.0, extra='stroke="var(--amber, #f59e0b)" stroke-width="1.0"'))
            svg_parts.append(_text(tag_x - tag_w / 2.0, y_p50 + 4.0, f"P50 {p50_val:+.1f}%", anchor="middle", fill="var(--amber, #f59e0b)", extra='font-size="9" font-weight="700" font-family="var(--mono)"'))
        else:
            svg_parts.append(_line(cx - box_w / 2.0 - 3, y_p50, cx + box_w / 2.0 + 3, y_p50, stroke="var(--amber, #f59e0b)", width=2.5))
            lbl_w = 54.0
            lbl_h = 16.0
            svg_parts.append(_rect(cx - lbl_w / 2.0, y_p50 - lbl_h / 2.0, lbl_w, lbl_h, fill="var(--mc-pill-bg, #0b111e)", rx=3.0, extra='stroke="var(--amber, #f59e0b)" stroke-width="0.85"'))
            svg_parts.append(_text(cx, y_p50 + 4.0, f"{p50_val:+.1f}%", anchor="middle", fill="var(--mc-med-text, #ffffff)", extra='font-size="9.5" font-weight="700" font-family="var(--mono)"'))

        # --- P95 Label with Backdrop Pill ---
        p95_lbl_y = y_p95 - 8.0
        if p95_lbl_y < pad_t + 10.0:
            p95_lbl_y = pad_t + 10.0
        pill_w = 78.0
        pill_h = 16.0
        svg_parts.append(_rect(cx - pill_w / 2.0, p95_lbl_y - 12.0, pill_w, pill_h, fill="var(--mc-pill-bg, #0b111e)", rx=3.0, extra='stroke="var(--up, #10b981)" stroke-width="0.85"'))
        svg_parts.append(_text(cx, p95_lbl_y, f"P95: {p95_val:+.1f}%", anchor="middle", fill="var(--up, #10b981)", extra='font-size="9.5" font-weight="600" font-family="var(--mono)"'))

        # --- P05 Label with Vertical Clearance Enforcement ---
        p05_lbl_y = max(y_p05 + 14.0, y_p50 + 20.0)
        if p05_lbl_y > pad_t + plot_h - 4.0:
            p05_lbl_y = pad_t + plot_h - 4.0
        p05_pill_w = 96.0 if is_liquidated else 78.0
        p05_pill_h = 16.0
        p05_text = "P05: RUIN (-100%)" if is_liquidated else f"P05: {p05_val:+.1f}%"
        svg_parts.append(_rect(cx - p05_pill_w / 2.0, p05_lbl_y - 12.0, p05_pill_w, p05_pill_h, fill="var(--mc-pill-bg, #0b111e)", rx=3.0, extra='stroke="var(--down, #ef4444)" stroke-width="0.85"'))
        svg_parts.append(_text(cx, p05_lbl_y, p05_text, anchor="middle", fill="var(--down, #ef4444)", extra='font-size="9.5" font-weight="600" font-family="var(--mono)"'))

        # --- Drawdown Indicator with Stepped Leader Anti-Collision ---
        y_dd = to_y(-dd_val)
        dd_txt_x = cx + box_w / 2.0 + 16.0
        if abs(y_dd - p05_lbl_y) < 18.0:
            dd_disp_y = p05_lbl_y + 18.0 if p05_lbl_y + 18.0 <= pad_t + plot_h - 4.0 else p05_lbl_y - 18.0
            svg_parts.append(f'<path d="M {cx + box_w / 2.0 + 3.0:.1f} {y_dd:.1f} L {cx + box_w / 2.0 + 9.0:.1f} {y_dd:.1f} L {dd_txt_x - 3.0:.1f} {dd_disp_y - 3.0:.1f} H {dd_txt_x + 4.0:.1f}" fill="none" stroke="var(--down, #ef4444)" stroke-width="1.2" stroke-dasharray="2,2"/>')
        else:
            dd_disp_y = y_dd
            svg_parts.append(_line(cx + box_w / 2.0 + 3.0, y_dd, dd_txt_x - 3.0, y_dd, stroke="var(--down, #ef4444)", width=1.2))
        svg_parts.append(f'<circle cx="{_coord(cx + box_w / 2.0 + 3.0)}" cy="{_coord(y_dd)}" r="2.5" fill="var(--down, #ef4444)"/>')

        dd_pill_w = 70.0
        dd_pill_h = 15.0
        svg_parts.append(_rect(dd_txt_x - 2.0, dd_disp_y - 11.0, dd_pill_w, dd_pill_h, fill="var(--mc-pill-bg, #0b111e)", rx=3.0, extra='stroke="var(--down, #ef4444)" stroke-width="0.6"'))
        svg_parts.append(_text(dd_txt_x + 2.0, dd_disp_y, f"DD: -{dd_val:.1f}%", anchor="start", fill="var(--down, #ef4444)", extra='font-size="9" font-family="var(--mono)" font-weight="600"'))

        # Probability of profit badge at top
        pop_num = float(pop) if _is_finite_number(pop) else 0.0
        pop_str = _format_prob_pct(pop)
        pop_bg = "var(--up, #10b981)" if pop_num >= 50.0 else ("var(--amber, #f59e0b)" if pop_num >= 20.0 else "var(--down, #ef4444)")
        badge_w = 88.0
        badge_x = cx - badge_w / 2.0
        badge_y = 14.0
        svg_parts.append(_rect(badge_x, badge_y, badge_w, 20.0, fill=pop_bg, rx=4.0))
        svg_parts.append(_text(cx, badge_y + 14.0, f"PoP: {pop_str}", anchor="middle", fill="#ffffff", extra='font-size="10" font-weight="bold"'))

        # X-axis label
        label_y = pad_t + plot_h + 18.0
        svg_parts.append(_text(cx, label_y, key, anchor="middle", fill="var(--ink, #0f172a)", extra='font-size="11" font-weight="bold"'))
        svg_parts.append(_text(cx, label_y + 14.0, f"{_int_text(trades)} trds", anchor="middle", fill="var(--ink-3, #94a3b8)", extra='font-size="10"'))

        # Ruin indicator
        if _is_finite_number(p_ruin) and float(p_ruin) > 0.05:
            ruin_str = f"Ruin: {_format_prob_pct(p_ruin)} ⚠"
            svg_parts.append(_text(cx, label_y + 28.0, ruin_str, anchor="middle", fill="var(--down, #ef4444)", extra='font-size="9.5" font-weight="bold"'))
        else:
            svg_parts.append(_text(cx, label_y + 28.0, "Safe Floor ✔", anchor="middle", fill="var(--up, #10b981)", extra='font-size="9.5"'))

    svg_content = "".join(svg_parts)
    chart_svg = _svg(width, height, svg_content, extra_class="mc-unified-svg")

    subtitle = (
        f"{_int_text(mc.get('iterations') or 10000)} bootstrap paths &middot; "
        + (
            "liquidation floor at -100%"
            if ruin_risk
            else "no simulated path reaches liquidation"
        )
    )
    ruin_legend = (
        '<span class="mc-legend-item"><span class="mc-legend-dot" '
        'style="background:var(--down,#dc2626);"></span>-100% ruin floor</span>'
        if ruin_risk
        else ""
    )
    header_html = (
        '<div class="mc-unified-header">'
        '  <div class="mc-unified-title-wrap">'
        '    <h3 class="mc-unified-title">Outcome distribution by horizon</h3>'
        f'    <div class="mc-unified-subtitle">{subtitle}</div>'
        '  </div>'
        '  <div class="mc-unified-legend">'
        '    <span class="mc-legend-item"><span class="mc-legend-dot" style="background:var(--up,#10b981);"></span>P50&ndash;P95 upside</span>'
        '    <span class="mc-legend-item"><span class="mc-legend-dot" style="background:var(--amber,#f59e0b);"></span>P50 median</span>'
        '    <span class="mc-legend-item"><span class="mc-legend-dot" style="background:var(--down,#ef4444);"></span>P05&ndash;P50 downside</span>'
        f'    {ruin_legend}'
        '  </div>'
        '</div>'
    )

    # --- Parameter glossary (* notes) rendered as an aligned two-column grid
    # matching the style of the existing score-basis notes in the rest of the report.
    param_notes_html = (
        '<div class="mc-param-notes">'
        '<div class="mc-param-notes-grid">'
        '<div class="mc-param-note-item"><span class="mc-param-star">PoP</span>'
        '<span class="mc-param-desc">Probability of Profit &mdash; share of simulated paths ending with positive return (terminal equity &gt; starting equity).</span></div>'
        '<div class="mc-param-note-item"><span class="mc-param-star">P05 / P50 / P95</span>'
        '<span class="mc-param-desc">5th / 50th (median) / 95th percentile of terminal return across all bootstrap paths. P05 = stress scenario; P95 = upside scenario.</span></div>'
        '<div class="mc-param-note-item"><span class="mc-param-star">DD</span>'
        '<span class="mc-param-desc">Median maximum drawdown &mdash; the typical deepest peak-to-trough capital decline observed across simulated paths.</span></div>'
        '<div class="mc-param-note-item"><span class="mc-param-star">Safe Floor ✔ / Ruin</span>'
        '<span class="mc-param-desc">Safe Floor: no simulated path reached &minus;100% (liquidation boundary). Ruin %: fraction of paths that hit full liquidation.</span></div>'
        '<div class="mc-param-note-item"><span class="mc-param-star">SHORT / MEDIUM / LONG</span>'
        '<span class="mc-param-desc">Simulated horizons at 0.2&times;, 1.0&times;, and 3.0&times; the observed trade count. Horizon stability tests whether edge persists at scale.</span></div>'
        '</div>'
        '</div>'
    )

    return f'<div class="mc-unified-panel">{header_html}{chart_svg}{param_notes_html}</div>'


def _render_horizon_probability_chart(mc: Dict[str, Any]) -> str:
    """Counterpart preserving API and test compatibility for the horizon probability chart."""
    return _render_unified_monte_carlo_chart(mc)


def _render_key_probabilities(mc: Dict[str, Any]) -> str:
    p_ruin = mc.get("p_ruin")
    p_loss = mc.get("p_loss_after_horizon")
    horizon_trades = mc.get("horizon_trades")
    horizon_desc = f" ({_int_text(horizon_trades)} trds)" if _is_finite_number(horizon_trades) else ""

    kpi_cards = []
    # 1. Probability of ruin
    if _is_finite_number(p_ruin):
        val_ruin = float(p_ruin)
        if val_ruin <= 0.05:
            badge = '<span class="kp-badge kp-badge-safe" title="Zero ruin probability detected across 10,000 paths"><span class="kp-badge-dot"></span>Safe Floor ℹ</span>'
            ruin_color = "var(--ink, #fff)"
        elif val_ruin <= 5.0:
            badge = '<span class="kp-badge kp-badge-warn" title="Low risk of total capital loss"><span class="kp-badge-dot"></span>Low Ruin Risk</span>'
            ruin_color = "#f59e0b"
        else:
            badge = '<span class="kp-badge kp-badge-danger" title="Severe capital wipeout risk"><span class="kp-badge-dot"></span>Elevated Ruin ⚠</span>'
            ruin_color = "#ef4444"

        ruin_display = _format_prob_pct(val_ruin)
        if val_ruin <= 0.05:
            safe_title = "Zero ruin probability detected across 10,000 paths (0 / 10,000 paths touched 0 USDT)" if val_ruin <= 0.0001 else "Near-zero ruin probability (<0.05% across 10,000 paths)"
            badge = f'<span class="kp-badge kp-badge-safe" title="{safe_title}"><span class="kp-badge-dot"></span>Safe Floor ℹ</span>'
            ruin_color = "var(--ink, #fff)"
        elif val_ruin <= 5.0:
            badge = '<span class="kp-badge kp-badge-warn" title="Low risk of total capital loss"><span class="kp-badge-dot"></span>Low Ruin Risk</span>'
            ruin_color = "#f59e0b"
        else:
            badge = '<span class="kp-badge kp-badge-danger" title="Severe capital wipeout risk"><span class="kp-badge-dot"></span>Elevated Ruin ⚠</span>'
            ruin_color = "#ef4444"

        kpi_cards.append(
            f'<div class="kp-kpi-card" title="Simulated probability that cumulative equity drops to or below 0 USDT across 10,000 bootstrap paths">'
            f'<div class="kp-kpi-header"><span class="kp-kpi-label">Probability of Ruin</span></div>'
            f'<div class="kp-kpi-sublabel">P(100% loss){horizon_desc}</div>'
            f'<div class="kp-kpi-value" style="color:{ruin_color};">{ruin_display}</div>'
            f'<div class="kp-kpi-footer">{badge}</div>'
            f'</div>'
        )

    # 2. Probability of loss at horizon end
    if _is_finite_number(p_loss):
        val_loss = float(p_loss)
        loss_display = _format_prob_pct(val_loss)
        if val_loss >= 70.0:
            badge = '<span class="kp-badge kp-badge-danger" title="Loss probability is near absolute"><span class="kp-badge-dot"></span>Extreme Decay ⚠</span>'
            loss_color = "#ef4444"
        elif val_loss <= 20.0:
            fav_title = "Zero terminal loss detected across 10,000 simulations (terminal capital remained >= initial equity)" if val_loss <= 0.0001 else "High probability of ending profitable"
            badge = f'<span class="kp-badge kp-badge-safe" title="{fav_title}"><span class="kp-badge-dot"></span>Favourable Odds ✔</span>'
            loss_color = "#10b981"
        else:
            badge = '<span class="kp-badge kp-badge-warn" title="Moderate loss probability"><span class="kp-badge-dot"></span>Moderate Risk</span>'
            loss_color = "#f59e0b"

        kpi_cards.append(
            f'<div class="kp-kpi-card" title="Simulated probability that terminal capital is below initial equity across 10,000 bootstrap iterations">'
            f'<div class="kp-kpi-header"><span class="kp-kpi-label">Prob. of Loss at End</span></div>'
            f'<div class="kp-kpi-sublabel">Simulation horizon{horizon_desc}</div>'
            f'<div class="kp-kpi-value" style="color:{loss_color};">{loss_display}</div>'
            f'<div class="kp-kpi-footer">{badge}</div>'
            f'</div>'
        )

    streak_rows = []
    for n, obs_key, base_key, excess_key in (
        (5, "p_5_loss_streak", "p_5_loss_streak_baseline", "p_5_loss_streak_excess"),
        (10, "p_10_loss_streak", "p_10_loss_streak_baseline", "p_10_loss_streak_excess"),
    ):
        obs = mc.get(obs_key)
        if not _is_finite_number(obs):
            continue
        base = mc.get(base_key)
        excess = mc.get(excess_key)

        obs_val = float(obs)
        base_val = float(base) if _is_finite_number(base) else None
        excess_val = float(excess) if _is_finite_number(excess) else None

        excess_str = f"+{excess_val:.1f}%" if (excess_val is not None and excess_val > 0.05) else (_pct(excess_val, 1) if excess_val is not None else "—")
        excess_color = "#f59e0b" if (excess_val is not None and excess_val > 0.05) else "var(--muted, #94a3b8)"

        excess_tooltip = (
            f"Observed probability of \u2265{n} consecutive losses is {excess_str} higher than random baseline, indicating loss clustering (e.g. averaging down or martingale)"
            if (excess_val is not None and excess_val > 0.05)
            else f"Losing streak \u2265{n} trades is consistent with random chance"
        )

        streak_rows.append(
            f'<tr class="kp-streak-row" title="Simulated probability of \u2265{n} consecutive losing trades">'
            f'<td class="col-streak"><span class="kp-streak-pill">&ge;{n} trades</span></td>'
            f'<td class="col-obs">{_pct(obs_val, 1)}</td>'
            f'<td class="col-base">{_pct(base_val, 1) if base_val is not None else "—"}</td>'
            f'<td class="col-excess" style="color:{excess_color};font-weight:700;" title="{_esc(excess_tooltip)}">{excess_str}</td>'
            f'</tr>'
        )

    body_parts = []
    if kpi_cards:
        body_parts.append(f'<div class="kp-kpi-row">{"".join(kpi_cards)}</div>')

    # 3. Core Risk & Performance Metrics (unblocked schema fields: VaR 95%, CVaR 95%, MAR median, PF median)
    var_95 = mc.get("var_95_pct")
    cvar_95 = mc.get("cvar_95_pct")
    mar_median = mc.get("mar_ratio_median")
    pf_median = mc.get("profit_factor_median")

    has_any_risk_stat = any(
        _is_finite_number(v) for v in (var_95, cvar_95, mar_median, pf_median)
    )
    if has_any_risk_stat:
        risk_cards = []
        if _is_finite_number(var_95):
            v = float(var_95)
            v_str = f"{v:+.1f}%" if v != 0 else "0.0%"
            c = "var(--down, #ef4444)" if v < 0 else "var(--up, #10b981)"
            risk_cards.append(
                f'<div class="kp-stat-item" title="Value at Risk (95% confidence): maximum expected loss threshold at 95% certainty">'
                f'<div class="kp-stat-label">VaR (95%)</div>'
                f'<div class="kp-stat-val" style="color:{c};">{_esc(v_str)}</div>'
                f'<div class="kp-stat-sub">5th pct threshold</div>'
                f'</div>'
            )
        else:
            risk_cards.append(
                '<div class="kp-stat-item" title="Value at Risk not measured">'
                '<div class="kp-stat-label">VaR (95%)</div>'
                '<div class="kp-stat-val" style="color:var(--ink-3, #94a3b8);">&mdash;</div>'
                '<div class="kp-stat-sub">not measured</div>'
                '</div>'
            )

        if _is_finite_number(cvar_95):
            cv = float(cvar_95)
            cv_disp = -abs(cv) if cv > 0 else cv
            cv_str = f"{cv_disp:.1f}%"
            risk_cards.append(
                f'<div class="kp-stat-item" title="Conditional VaR (Expected Shortfall): expected average loss in the worst 5% tail outcomes">'
                f'<div class="kp-stat-label">CVaR (95%)</div>'
                f'<div class="kp-stat-val" style="color:var(--down, #ef4444);">{_esc(cv_str)}</div>'
                f'<div class="kp-stat-sub">Tail shortfall</div>'
                f'</div>'
            )
        else:
            risk_cards.append(
                '<div class="kp-stat-item" title="Conditional VaR not measured">'
                '<div class="kp-stat-label">CVaR (95%)</div>'
                '<div class="kp-stat-val" style="color:var(--ink-3, #94a3b8);">&mdash;</div>'
                '<div class="kp-stat-sub">not measured</div>'
                '</div>'
            )

        if _is_finite_number(mar_median):
            m = float(mar_median)
            m_str = f"{m:.2f}"
            c = "var(--up, #10b981)" if m >= 2.0 else ("var(--amber, #f59e0b)" if m >= 0.5 else "var(--down, #ef4444)")
            risk_cards.append(
                f'<div class="kp-stat-item" title="MAR Ratio (Median): ratio of annualized return to maximum drawdown across simulations">'
                f'<div class="kp-stat-label">MAR (med)</div>'
                f'<div class="kp-stat-val" style="color:{c};">{_esc(m_str)}</div>'
                f'<div class="kp-stat-sub">Return / Max DD</div>'
                f'</div>'
            )
        else:
            risk_cards.append(
                '<div class="kp-stat-item" title="MAR ratio not measured">'
                '<div class="kp-stat-label">MAR (med)</div>'
                '<div class="kp-stat-val" style="color:var(--ink-3, #94a3b8);">&mdash;</div>'
                '<div class="kp-stat-sub">not measured</div>'
                '</div>'
            )

        if _is_finite_number(pf_median):
            pf = float(pf_median)
            pf_str = f"{pf:.2f}"
            c = "var(--up, #10b981)" if pf >= 1.25 else ("var(--amber, #f59e0b)" if pf >= 1.0 else "var(--down, #ef4444)")
            risk_cards.append(
                f'<div class="kp-stat-item" title="Profit Factor (Median): median ratio of gross profits to gross losses across bootstrap paths">'
                f'<div class="kp-stat-label">PF (med)</div>'
                f'<div class="kp-stat-val" style="color:{c};">{_esc(pf_str)}</div>'
                f'<div class="kp-stat-sub">Gross win / loss</div>'
                f'</div>'
            )
        else:
            risk_cards.append(
                '<div class="kp-stat-item" title="Profit factor not measured">'
                '<div class="kp-stat-label">PF (med)</div>'
                '<div class="kp-stat-val" style="color:var(--ink-3, #94a3b8);">&mdash;</div>'
                '<div class="kp-stat-sub">not measured</div>'
                '</div>'
            )

        body_parts.append(
            '<div class="kp-subhead-row">'
            '<span class="kp-subhead-title">SIMULATED RISK &amp; EFFICIENCY</span>'
            '</div>'
            f'<div class="kp-stat-strip">{"".join(risk_cards)}</div>'
        )

    if streak_rows:
        streak_meta = f'<span class="kp-subhead-meta">Horizon: {_int_text(horizon_trades)} trades</span>' if _is_finite_number(horizon_trades) else ''
        body_parts.append(
            '<div class="kp-subhead-row">'
            '<span class="kp-subhead-title">LOSING STREAK RISK</span>'
            f'{streak_meta}'
            '</div>'
            '<div class="kp-table-wrap">'
            '<table class="kp-table">'
            '<thead><tr>'
            '<th class="col-streak" title="Consecutive losing trades streak">Streak</th>'
            '<th class="col-obs" title="Observed probability from 10,000 bootstrap simulations">Observed</th>'
            '<th class="col-base" title="Baseline expected from random chance (Binomial distribution)">Baseline <span class="th-sub">(random)</span></th>'
            '<th class="col-excess" title="Excess over random baseline (Observed - Baseline)">Excess</th>'
            '</tr></thead>'
            f'<tbody>{"".join(streak_rows)}</tbody>'
            '</table>'
            '</div>'
        )

    body = "".join(body_parts)
    if not body:
        return ""
    # No drawer here either: the Monte Carlo section carries one for all of
    # its sub-blocks, and the streak baseline is explained there.
    return _subsection("Key probabilities", body, "")


# --------------------------------------------------------------------------- #
# Section 5 -- statistical inference
# --------------------------------------------------------------------------- #


def _render_statistical_inference(result: Dict[str, Any]) -> str:
    mc = result.get("mc")
    if not isinstance(mc, dict) or not mc:
        return ""

    has_any = any(
        _is_finite_number(mc.get(k))
        for k in (
            "probabilistic_sharpe",
            "deflated_sharpe",
            "min_track_record_trades",
            "sharpe_per_trade",
        )
    )
    if not has_any and not mc.get("inference_notes"):
        return ""

    reliable = mc.get("inference_reliable")
    unreliable_notice = ""
    if reliable is False:
        notes = mc.get("inference_notes") or []
        notes_html = "; ".join(_esc(n) for n in notes if isinstance(n, str))
        unreliable_notice = (
            '<div class="notice notice-danger">'
            "<strong>Statistical inference is NOT reliable</strong> for this bot"
            + (f": {notes_html}." if notes_html else ".")
            + " Read the figures below as a reference, not a firm conclusion."
            "</div>"
        )

    spt = mc.get("sharpe_per_trade")
    if _is_finite_number(spt):
        f_spt = float(spt)
        spt_str = _num(spt, 2)
        if f_spt > 0:
            spt_val = f'<span style="color:#16a34a;font-weight:700;font-family:var(--mono);">+{spt_str}</span>'
        elif f_spt < 0:
            spt_val = f'<span style="color:#dc2626;font-weight:700;font-family:var(--mono);">{spt_str}</span>'
        else:
            spt_val = f'<span style="font-family:var(--mono);">{spt_str}</span>'
    else:
        spt_val = f'<span style="font-family:var(--mono);">{_num(spt, 2)}</span>'

    psr_val = _ratio_to_pct(mc.get("probabilistic_sharpe"))
    if _is_finite_number(psr_val):
        f_psr = float(psr_val)
        psr_str = _pct(f_psr, 1)
        if f_psr >= 95.0:
            psr_cell = f'<span style="color:#16a34a;font-weight:700;font-family:var(--mono);">{psr_str}</span>'
        elif f_psr < 50.0:
            psr_cell = f'<span style="color:#dc2626;font-weight:700;font-family:var(--mono);">{psr_str}</span>'
        else:
            psr_cell = f'<span style="font-family:var(--mono);">{psr_str}</span>'
    else:
        psr_cell = f'<span style="font-family:var(--mono);">{_pct(psr_val, 1)}</span>'

    dsr_val = _ratio_to_pct(mc.get("deflated_sharpe"))
    if _is_finite_number(dsr_val):
        f_dsr = float(dsr_val)
        dsr_str = _pct(f_dsr, 1)
        if f_dsr >= 95.0:
            dsr_cell = f'<span style="color:#16a34a;font-weight:700;font-family:var(--mono);">{dsr_str}</span>'
        elif f_dsr < 50.0:
            dsr_cell = f'<span style="color:#dc2626;font-weight:700;font-family:var(--mono);">{dsr_str}</span>'
        else:
            dsr_cell = f'<span style="font-family:var(--mono);">{dsr_str}</span>'
    else:
        dsr_cell = f'<span style="font-family:var(--mono);">{_pct(dsr_val, 1)}</span>'

    rows = [
        [
            _calc_label_html("Sharpe per trade", "sharpe_per_trade"),
            spt_val,
        ],
        [
            _calc_label_html(
                "Probabilistic Sharpe Ratio (PSR)", "probabilistic_sharpe"
            ),
            psr_cell,
        ],
        [
            _calc_label_html("Deflated Sharpe Ratio (DSR)", "deflated_sharpe"),
            dsr_cell,
        ],
        [
            _calc_label_html(
                "Minimum trades required (MinTRL)", "min_track_record_trades"
            ),
            _int_text(mc.get("min_track_record_trades")),
        ],
        [
            _calc_label_html("Sample size used for inference", "sample_size"),
            _int_text(mc.get("sample_size")),
        ],
        [
            _calc_label_html(
                "Candidates compared to select this bot", "selection_trials"
            ),
            _int_text(mc.get("selection_trials")),
        ],
    ]
    table = _table(["Metric", "Value"], rows)

    theory = _theory(
        "Statistical inference testing whether observed strategy profitability represents genuine skill or random luck / data mining: "
        "Probabilistic Sharpe Ratio (PSR) accounts for non-normal return skewness and fat tails (PSR ≥ 95% indicates genuine statistical edge); "
        "Deflated Sharpe Ratio (DSR) discounts selection bias across multiple strategy trials to avoid false discoveries; "
        "MinTRL defines the minimum track record length (trades required) needed for 95% statistical confidence given the strategy's Sharpe, skewness, and kurtosis.",
        "Methodology by Bailey &amp; López de Prado (2014): PSR(SR* = 0) adjusted for sample skewness and kurtosis; DSR adjusting for the variance of trials among candidate strategies.",
    )
    return _section(
        "Statistical inference",
        unreliable_notice + table + theory,
        tone="quiet",
        pair=True,
        anchor="suy-luan",
    )


def _ratio_to_pct(value: Any) -> Optional[float]:
    if not _is_finite_number(value):
        return None
    return float(value) * 100.0


# --------------------------------------------------------------------------- #
# Section 6 -- trade metrics
# --------------------------------------------------------------------------- #


_PERFORMANCE_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("trade_count", "Closed trades", "int"),
    ("win_rate", "Win rate", "pct"),
    ("profit_factor", "Profit factor", "num2"),
    ("payoff_ratio", "Payoff ratio", "num2"),
    ("expectancy", "Expectancy per trade", "money"),
    ("total_pnl", "Total PnL", "money"),
    ("max_drawdown_pct", "Max drawdown", "pct"),
    ("current_drawdown_pct", "Current drawdown", "pct"),
    ("sharpe_ratio", "Sharpe ratio", "num2"),
    ("sortino_ratio", "Sortino ratio", "num2"),
    ("calmar_ratio", "Calmar ratio", "num2"),
    ("max_win_streak", "Longest winning streak", "int"),
    ("max_loss_streak", "Longest losing streak", "int"),
    ("average_hold_time_minutes", "Average hold time (minutes)", "num1"),
    ("trade_frequency_per_day", "Trades / day", "num2"),
)

_FORMATTERS = {
    "int": _int_text,
    "pct": lambda v: _pct(v, 1),
    "num2": lambda v: _num(v, 2),
    "num1": lambda v: _num(v, 1),
    "money": _money,
}


def _render_trade_metrics(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return ""
    perf = evidence.get("performance")
    if not isinstance(perf, dict) or not perf:
        return ""
    rows = []
    for key, label, kind in _PERFORMANCE_ROWS:
        if key not in perf:
            continue
        val = perf.get(key)
        formatted_val = _FORMATTERS[kind](val)
        if key in ("total_pnl", "expectancy", "sharpe_ratio", "sortino_ratio", "calmar_ratio") and _is_finite_number(val):
            f_val = float(val)
            if f_val > 0:
                prefix = "+" if not str(formatted_val).startswith("+") else ""
                val_cell = f'<span style="color:#16a34a;font-weight:700;font-family:var(--mono);">{prefix}{_esc(formatted_val)}</span>'
            elif f_val < 0:
                val_cell = f'<span style="color:#dc2626;font-weight:700;font-family:var(--mono);">{_esc(formatted_val)}</span>'
            else:
                val_cell = f'<span style="font-weight:600;font-family:var(--mono);">{_esc(formatted_val)}</span>'
        elif key in ("max_drawdown_pct", "current_drawdown_pct") and _is_finite_number(val) and float(val) > 0:
            val_cell = f'<span style="color:#dc2626;font-weight:600;font-family:var(--mono);">{_esc(formatted_val)}</span>'
        else:
            val_cell = f'<span style="font-family:var(--mono);">{_esc(formatted_val)}</span>'
        rows.append([_calc_label_html(label, key), val_cell])
    if not rows:
        return ""
    table = _table(["Metric", "Value"], rows)
    theory = _theory(
        "Core trading performance and risk-adjusted return metrics across the closed trade history. "
        "Profit Factor (&lt;1.0 indicates cumulative net loss), Payoff Ratio (average win / average loss), "
        "and Expectancy (expected value per trade) measure statistical profitability. "
        "Sharpe, Sortino (penalizing downside volatility only), and Calmar (annualized return / max drawdown) "
        "evaluate return efficiency per unit of risk, alongside drawdown depths, streaks, and trading cadence.",
        "Extracted directly from closed order fill records: Profit Factor = Gross Profit / Gross Loss; "
        "Payoff Ratio = Avg Win / Avg Loss; Expectancy = Total PnL / Total Trades. "
        "Drawdown measures peak-to-trough decline in cumulative equity.",
    )
    return _section("Trade metrics", table + theory, pair=True, anchor="so-lieu")


# --------------------------------------------------------------------------- #
# Section 7 -- traded assets
# --------------------------------------------------------------------------- #


def _render_assets(result: Dict[str, Any]) -> str:
    assets = result.get("assets")
    if not isinstance(assets, list) or not assets:
        return ""
    rows = []
    for a in assets:
        if not isinstance(a, dict):
            continue
        state = a.get("state") or "—"
        color = ASSET_STATE_COLOR.get(state, "#6b7280")
        rows.append(
            [
                f"<strong>{_esc(a.get('asset'))}</strong>",
                _badge(state, color),
                _int_text(a.get("open_positions")),
                _int_text(a.get("closed_seen")),
                _num(a.get("last_close_days"), 1) + " days ago"
                if _is_finite_number(a.get("last_close_days"))
                else "never closed",
            ]
        )
    if not rows:
        return ""
    table = _table(
        ["Asset", "Status", "Open positions", "Closed trades", "Last closed"],
        rows,
    )
    theory = _theory(
        "Activity audit across all traded symbols: "
        "<strong>TRADING</strong>: has a recently closed trade, indicating active ongoing execution; "
        "<strong>HOLDING ONLY</strong>: holds an open position without recent closed trades (signals holding losing trades open instead of cutting losses); "
        "<strong>EXITED</strong>: historically traded asset with zero open exposure and no recent trades, no longer reflecting current bot operations.",
        "Inferred from active open positions cross-referenced with chronological closed-trade history in the exchange ledger.",
    )
    return _section(
        "Traded assets", table + theory, pair=True, anchor="tai-san"
    )


# --------------------------------------------------------------------------- #
# Bước 1 + 2 Tab Components: Market Analytics & Trade Analytics
# --------------------------------------------------------------------------- #

_TREND_LABEL_VI = {
    "BULLISH": "RISING ↗",
    "BEARISH": "FALLING ↘",
    "SIDEWAYS": "SIDEWAYS ↔",
}

_VOLATILITY_LABEL_VI = {
    "LOW": "LOW VOLATILITY",
    "NORMAL": "NORMAL VOLATILITY",
    "HIGH": "HIGH VOLATILITY ⚠️",
}

_LIQUIDITY_LABEL_VI = {
    "DEEP": "DEEP",
    "ADEQUATE": "ADEQUATE",
    "THIN": "THIN / SLIPPAGE-PRONE ⚠️",
}


def _render_dominant_market_card(result: Dict[str, Any]) -> str:
    market = (
        result.get("market_analysis")
        or ((result.get("evidence") or {}).get("market_analysis"))
        or {}
    )
    evidence = result.get("evidence") or {}
    symbol = market.get("symbol") or evidence.get("traded_symbol") or "Premium Market"
    venue = market.get("venue_type") or "CEX"
    posture = market.get("posture") or (
        "STABLE" if market.get("available") else "UNDETERMINED"
    )
    posture_evidence = market.get("posture_evidence") or []
    trend = market.get("trend")
    volatility = market.get("volatility")
    liquidity = market.get("liquidity")
    data_quality = market.get("data_quality")
    comparison = market.get("comparison") or []

    trend_text = _TREND_LABEL_VI.get(trend, "UNDETERMINED")
    trend_color = (
        "#16a34a" if trend == "BULLISH" else ("#dc2626" if trend == "BEARISH" else None)
    )
    vol_text = _VOLATILITY_LABEL_VI.get(volatility, "NORMAL")
    liq_text = _LIQUIDITY_LABEL_VI.get(liquidity, "ADEQUATE")
    quality_text = _pct(
        float(data_quality) * 100 if _is_finite_number(data_quality) else 100.0, 0
    )

    # NOTE: "ỔN" matches the Vietnamese `POSTURE_STABLE` value
    # ("ỔN ĐỊNH") that `Agent/backend/report/qc/reporting/market_posture.py`
    # (out of scope for this translation pass) still produces; "STABLE"
    # covers this module's own English fallback default above.
    posture_color = "#16a34a" if "ỔN" in posture or posture == "STABLE" else "#d97706"

    trend_style = f' style="color:{trend_color};"' if trend_color else ""

    evidence_bullets = (
        "".join(f"<li>{_esc(e)}</li>" for e in posture_evidence)
        if posture_evidence
        else "<li>Candle and order-book data meet the Step 1 standard</li>"
    )
    comparison_html = ""
    if comparison:
        comp_bullets = "".join(f"<li>{_esc(c)}</li>" for c in comparison)
        comparison_html = (
            '<div class="market-comparison-box">'
            "<h4>Performance comparison on the same market:</h4>"
            f'<ul class="findings">{comp_bullets}</ul>'
            "</div>"
        )

    hint = (
        '<div class="card-hint">'
        "<strong>Step 1 + 2 basis:</strong> Assesses the bot's actual operating environment. "
        "Includes order-book liquidity, volatility range, and the balance of two-way order flow. "
        "Data is loaded from the order book and historical candle series."
        "</div>"
    )

    # Asset evaluation parameters view thẳng, không dùng card hover riêng lẻ
    body = (
        f'<div class="market-hero-card">'
        f'<div class="market-specs-panel">'
        f'  <div class="market-spec-hero">'
        f'    <div class="market-spec-hero-title">Market pair: <strong>{_esc(symbol)} / USDT ({_esc(venue)})</strong></div>'
        f'    <span class="badge" style="background:{posture_color}">STATUS: {_esc(posture)}</span>'
        f'  </div>'
        f'  <div class="market-spec-grid">'
        f'    <div class="market-spec-item">'
        f'      <span class="market-spec-label">Market trend</span>'
        f'      <span class="market-spec-val"{trend_style}><strong>{_esc(trend_text)}</strong></span>'
        f'    </div>'
        f'    <div class="market-spec-item">'
        f'      <span class="market-spec-label">Volatility level</span>'
        f'      <span class="market-spec-val"><strong>{_esc(vol_text)}</strong></span>'
        f'    </div>'
        f'    <div class="market-spec-item">'
        f'      <span class="market-spec-label">Order-book liquidity</span>'
        f'      <span class="market-spec-val"><strong>{_esc(liq_text)}</strong></span>'
        f'    </div>'
        f'    <div class="market-spec-item">'
        f'      <span class="market-spec-label">Data quality</span>'
        f'      <span class="market-spec-val"><strong>{_esc(quality_text)}</strong></span>'
        f'    </div>'
        f'  </div>'
        f'</div>'
        f'<div class="market-boxes">'
        f'<div class="market-evidence-box">'
        f"<h4>Status evidence from Step 1 + 2:</h4>"
        f'<ul class="findings">{evidence_bullets}</ul>'
        f"</div>"
        f"{comparison_html}"
        "</div>"
        f"{hint}"
        f"</div>"
    )
    theory = _theory(
        "Primary trading market posture, regime classification (trend, volatility, liquidity), and order-book data quality. "
        "Validates whether the bot's primary trading pair offers deep order book liquidity and fair spreads to avoid adverse execution slippage.",
        "Real-time and historical order book depth plus candle telemetry from OKX/Binance. "
        "Assesses two-way order flow balance, spread stability, and cross-bot peer performance comparison on the same asset.",
    )
    return _section(
        "Bot's primary trading market", body + theory, anchor="thi-truong-chinh"
    )


def _render_open_positions_audit(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence") or {}
    perf = evidence.get("performance") or {}

    open_pos = perf.get("open_positions")
    open_loss = perf.get("open_loss")
    open_loss_pct = perf.get("open_loss_to_capital_pct")
    booked_pf = perf.get("profit_factor")
    marked_pf = perf.get("marked_profit_factor")
    skew = perf.get("pnl_skew")
    kurt = perf.get("pnl_kurtosis")

    if all(v is None for v in (open_pos, open_loss, marked_pf, skew, kurt)):
        return ""

    items = []
    if open_pos is not None:
        items.append(("Open positions", _int_text(open_pos), None, "open_positions"))
    if open_loss is not None:
        loss_color = (
            "#dc2626"
            if (_is_finite_number(open_loss) and float(open_loss) < 0)
            else None
        )
        items.append(
            ("Unrealised loss", _money(open_loss), loss_color, "open_loss")
        )
    if open_loss_pct is not None:
        pct_val = (
            float(open_loss_pct) * 100.0
            if float(open_loss_pct) <= 1.0
            else float(open_loss_pct)
        )
        items.append(
            (
                "Unrealised loss / capital ratio",
                _pct(pct_val, 1),
                None,
                "open_loss_to_capital_pct",
            )
        )
    if booked_pf is not None and marked_pf is not None:
        pf_color = (
            "#dc2626"
            if (
                _is_finite_number(marked_pf)
                and float(marked_pf) < 1.0
                and float(booked_pf) >= 1.0
            )
            else None
        )
        items.append(
            (
                "Marked PF (mark-to-market)",
                _num(marked_pf, 2),
                pf_color,
                "marked_pf",
            )
        )
    if skew is not None:
        skew_color = (
            "#dc2626" if (_is_finite_number(skew) and float(skew) < -0.5) else None
        )
        items.append(
            ("PnL skewness", _num(skew, 2), skew_color, "pnl_skew")
        )
    if kurt is not None:
        items.append(("PnL kurtosis", _num(kurt, 2), None, "pnl_kurtosis"))

    row_list = []
    for label, val, color, key in items:
        val_str = str(val).strip()
        if val_str.startswith("-") or "-" in val_str:
            final_color = "#ef4444"
        else:
            final_color = "#10b981"
        val_style = f' style="color:{final_color};"'
        row_list.append(
            f'<div class="param-horizontal-row">'
            f'<span class="param-horizontal-name">{_calc_label_html(label, key)}</span>'
            f'<span class="param-horizontal-val"{val_style}>{_esc(val)}</span>'
            f'</div>'
        )
    rows_html = "".join(row_list)

    deferred_notice = ""
    if _is_finite_number(booked_pf) and _is_finite_number(marked_pf):
        b_pf = float(booked_pf)
        m_pf = float(marked_pf)
        if b_pf >= 1.0 and m_pf < 1.0:
            deferred_notice = (
                '<div class="notice notice-danger">'
                f"<strong>WARNING -- HIDDEN LOSS-HOLDING:</strong> The profit factor on the closed book is {_num(b_pf, 2)}, "
                f"but once open positions are marked to market (Marked PF) it drops to {_num(m_pf, 2)}. "
                "The bot shows signs of holding losing trades open instead of cutting them, to keep an artificial win rate."
                "</div>"
            )

    hint = (
        '<div class="card-hint">'
        "<strong>Open-position audit:</strong> Detects the risk of holding losing trades open to preserve the win rate. "
        "The Marked PF figure reflects the result if every open position were closed right now. "
        "Skewness and kurtosis measure the shape of the return distribution and outlier risk."
        "</div>"
    )

    theory = _theory(
        "Audit of open positions, unrealized losses, and return distribution geometry. "
        "Marked PF (mark-to-market) evaluates bot profitability if all open positions were closed immediately, "
        "detecting hidden loss-holding patterns used to maintain an artificial win rate. "
        "Skewness (&lt; -0.5) detects asymmetric downside risk (rare heavy losses vs small frequent wins); "
        "kurtosis (&gt; 3.0) detects heavy fat-tail / black swan vulnerability.",
        "Active positions marked against real-time order-book mid-prices; skewness and kurtosis computed "
        "as third and fourth standardized central moments of the trade return distribution.",
    )

    body = f'<div class="param-horizontal-list">{rows_html}</div>{deferred_notice}{hint}{theory}'
    # LƯU Ý: chỉ viết MỘT dấu `&` thô ở đây -- `_section()` tự đưa `title` qua
    # `_esc()` một lần rồi mới in ra. Trước đây chỗ này viết sẵn "&amp;" nên
    # bị escape hai lần (& -> &amp; -> &amp;amp;), hiển thị sai thành literal
    # "&amp;" trên trang. Xem cách "Tăng trưởng & cơ cấu kết quả" đã làm đúng
    # ngay từ đầu để đối chiếu.
    return _section(
        "Open-position audit & return distribution",
        body,
        tone="quiet",
        pair=True,
        anchor="vi-the-mo",
    )


def _render_closed_trades_table(result: Dict[str, Any], limit: int = 200) -> str:
    evidence = result.get("evidence") or {}
    series = evidence.get("closed_trade_series")
    if not isinstance(series, list) or not series:
        return ""

    symbol = (
        evidence.get("traded_symbol")
        or (result.get("market_analysis") or {}).get("symbol")
        or "BTC-USDT"
    )

    rows = []
    running_pnl = 0.0
    total_trades = len(series)
    enriched = []
    for item in series:
        if not isinstance(item, dict):
            continue
        pnl = item.get("realized_pnl")
        pnl_val = float(pnl) if _is_finite_number(pnl) else 0.0
        running_pnl += pnl_val
        enriched.append(
            {
                "close_time": item.get("close_time"),
                "realized_pnl": pnl_val,
                "running_pnl": running_pnl,
            }
        )

    recent = list(reversed(enriched))[:limit]
    for idx, t in enumerate(recent, 1):
        ct = t.get("close_time")
        time_str = _format_vn_timestamp(ct) if _is_finite_number(ct) else "—"
        pnl_val = t["realized_pnl"]
        run_val = t["running_pnl"]
        is_win = pnl_val > 0
        if is_win:
            badge = '<span class="badge-win" style="display:inline-block;background:rgba(22,163,74,0.15);color:#16a34a;border:1px solid rgba(22,163,74,0.35);font-family:var(--mono);font-weight:700;font-size:0.75rem;padding:0.15rem 0.5rem;border-radius:4px;">WIN</span>'
            pnl_html = f'<span class="text-profit" style="color:#16a34a;font-weight:700;font-family:var(--mono);">+{pnl_val:,.2f} USDT</span>'
        elif pnl_val < 0:
            badge = '<span class="badge-loss" style="display:inline-block;background:rgba(220,38,38,0.15);color:#dc2626;border:1px solid rgba(220,38,38,0.35);font-family:var(--mono);font-weight:700;font-size:0.75rem;padding:0.15rem 0.5rem;border-radius:4px;">LOSS</span>'
            pnl_html = f'<span class="text-loss" style="color:#dc2626;font-weight:700;font-family:var(--mono);">{pnl_val:,.2f} USDT</span>'
        else:
            badge = '<span class="badge" style="display:inline-block;background:rgba(156,163,175,0.15);color:#9ca3af;border:1px solid rgba(156,163,175,0.35);font-family:var(--mono);font-weight:700;font-size:0.75rem;padding:0.15rem 0.5rem;border-radius:4px;">BREAK-EVEN</span>'
            pnl_html = f'<span style="font-weight:600;font-family:var(--mono);">{pnl_val:,.2f} USDT</span>'

        if run_val > 0:
            run_html = f'<strong class="text-profit" style="color:#16a34a;font-weight:700;font-family:var(--mono);">+{run_val:,.2f} USDT</strong>'
        elif run_val < 0:
            run_html = f'<strong class="text-loss" style="color:#dc2626;font-weight:700;font-family:var(--mono);">{run_val:,.2f} USDT</strong>'
        else:
            run_html = f'<strong style="font-weight:600;font-family:var(--mono);">{run_val:,.2f} USDT</strong>'

        rows.append(
            [
                str(idx),
                f'<span class="mono-symbol">{_esc(symbol)}</span>',
                time_str,
                pnl_html,
                run_html,
                badge,
            ]
        )

    table = _table(
        ["#", "Pair", "Close time", "Profit / Loss (USDT)", "Cumulative PnL", "Result"],
        rows,
        table_class="okx-trades-table paginated-table",
        table_id="table-closed-trades",
        page_size=10,
    )
    subtitle = (
        f"<p style='color:var(--muted);font-size:0.85rem;margin-top:-0.2rem'>"
        f"OKX closed trade ledger · Showing {len(recent)} trades out of {total_trades} recorded trades "
        f"(10 trades per page with pagination controls below)."
        f"</p>"
    )

    hint = (
        '<div class="card-hint">'
        "<strong>Closed trade log:</strong> Check how regular the cash flow is "
        "and the time gaps between take-profit or stop-loss cycles."
        "</div>"
    )

    theory = _theory(
        "Detailed ledger of executed transactions showing realized PnL, running cumulative equity curve, "
        "and outcome classification (WIN, LOSS, BREAK-EVEN). Used to verify trade cadence, cash flow regularity, "
        "and the time intervals between take-profit or stop-loss executions.",
        "Directly extracted from exchange execution records in reverse chronological order. "
        "Cumulative PnL tracks running sum of realized profits and losses over the entire track record.",
    )
    return _section(
        "Most recent closed trades",
        subtitle + table + hint + theory,
        anchor="danh-sach-lenh",
    )


# --------------------------------------------------------------------------- #
# LIMITED tab content -- one bot, same 14 section ids as a FULL result.
#
# Yêu cầu gốc của người dùng: "bot private phải tận dụng những gì có thể
# public để phân tích đánh giá ... đảm bảo report đều giống nhau". Trước khi
# có khối này, một bot LIMITED (`Agent/backend/bot/analysis/limited.py`, sổ lệnh
# bị OKX chặn ở lỗi 60004) chỉ tự nhiên khớp được BA trong số 14 mục FULL
# có (ket-luan, diem-chieu, thi-truong-chinh -- ba hàm `_render_conclusion`/
# `_render_dimensions_section`/`_render_dominant_market_card` phía trên đều
# không có điều kiện tiên quyết nào chỉ FULL mới thoả), vì mọi hàm còn lại
# chỉ đọc được đúng hình dạng `evidence` của FULL (`closed_trade_series`,
# `performance`, `dimensions`, `primary_share_pct`, ...) mà một bot LIMITED
# không có và không cần bịa ra.
#
# Ba hàm dưới đây (`_render_tab_report_limited`/`_market_limited`/
# `_trades_limited`) là ĐÚNG MỘT điểm nối cho mỗi tab -- `_render_tab_report`/
# `_render_tab_market`/`_render_tab_trades` bên dưới rẽ nhánh ngay dòng đầu
# tiên khi `status == "LIMITED"`, không đổi gì trong nhánh FULL sẵn có. Mọi
# phép tính (định dạng số, gom nhiều luồng `evidence` lại) nằm ở
# `Agent/backend/web/limited_view.py`; các hàm `_render_limited_*` ở đây chỉ
# format/escape/`_section()` hoá, đúng phong cách `loss_analysis.py` đã có.
#
# Mỗi mục KHÔNG đo được vẫn phải HIỆN, kèm lý do thật -- không ẩn mục, không
# in "0"/"—" trơ trọi như thể đã đo. `_LIMITED_GAP_NOTICE` là khối giải
# thích dùng chung cho mọi trường hợp đó.
# --------------------------------------------------------------------------- #


def _limited_gap_notice(reason_html: str) -> str:
    return f'<div class="notice notice-warning">{reason_html}</div>'


def _render_limited_narrative(result: Dict[str, Any]) -> str:
    """ "nhan-dinh" cho LIMITED: một đoạn văn xuôi DUY NHẤT kết hợp nhiều
    luồng public cùng lúc (hồ sơ xếp hạng + thống kê ngày + đường vốn tuần +
    trạng thái Monte Carlo) -- xem `limited_view.narrative_paragraph`'s
    docstring cho lý do đoạn này KHÔNG lặp lại nguyên văn `result["text"]`
    (đã hiện đủ, theo từng dòng, ở mục "Kết luận và khuyến nghị").
    """
    text = limited_view.narrative_paragraph(result)
    if not text:
        return _section(
            "Expert assessment",
            _limited_gap_notice(
                "Could not synthesise an assessment: besides having its trade "
                "ledger hidden by OKX, this bot has no readable ranking profile "
                "(public-lead-traders) or daily stats (public-stats) either."
            ),
            anchor="nhan-dinh",
        )
    body = (
        '<div class="narrative-body-wrap">'
        '<div class="narrative-meta-bar">'
        '<span class="badge badge-info">SYNTHESISED FROM PUBLIC SOURCES</span>'
        '<span class="meta-desc">An objective summary synthesised from the bot\'s verified public data</span>'
        "</div>"
        f'<div class="narrative-prose-content"><p class="narrative-paragraph">{_esc(text)}</p></div>'
        "</div>"
    )
    return _section("Expert assessment", body, anchor="nhan-dinh")


def _render_limited_growth(result: Dict[str, Any]) -> str:
    """ "tang-truong" cho LIMITED: hai chuỗi công khai còn vẽ được --
    đường vốn suy từ PnL tuần (`weekly_series`) và chuỗi `pnlRatio` của hồ
    sơ xếp hạng (`pnl_ratio_series`) -- KHÔNG phải đường vốn tích luỹ theo
    từng lệnh (bot này không công khai lệnh nào), nên dùng `_line_chart`
    với `x_label_prefix`/`aria_label` riêng để không lẫn với chart của một
    bot FULL. Không có chuỗi nào đọc được thì hiện khối giải thích, không
    vẽ biểu đồ rỗng.
    """
    evidence = result.get("evidence") or {}
    parts: List[str] = []

    equity_pts = limited_view.weekly_equity_points(evidence)
    if equity_pts:
        coverage = limited_view.weekly_series_coverage(evidence) or {}
        chart = _line_chart(
            equity_pts,
            y_unit=" USDT",
            x_label_prefix="Week",
            aria_label="Capital curve inferred from public weekly PnL",
        )
        caption = (
            f"<p class='card-hint'>Inferred from {coverage.get('usable', len(equity_pts))}/"
            f"{coverage.get('total', len(equity_pts))} weeks with a PnL/ratio precise "
            "enough to convert into capital -- NOT a per-trade equity curve.</p>"
        )
        parts.append("<h3>Capital curve inferred from weekly PnL</h3>" + chart + caption)

    ratio_pts = limited_view.pnl_ratio_points(evidence)
    if ratio_pts:
        chart = _line_chart(
            ratio_pts,
            y_unit="%",
            x_label_prefix="Point",
            aria_label="Published pnlRatio over time",
        )
        parts.append("<h3>Published return ratio over time (pnlRatio)</h3>" + chart)

    if not parts:
        return _section(
            "Growth & outcome composition",
            _limited_gap_notice(
                "No weekly PnL or pnlRatio series is available to plot -- this bot "
                "does not publicly expose its trade ledger, so there is no "
                "per-trade cumulative equity curve like a FULL bot has."
            ),
            anchor="tang-truong",
        )

    theory = _theory(
        "Comparative tracking: cumulative equity reconstructed from weekly PnL versus official OKX pnlRatio time series.",
        "Equity reconstructed via EquityCurveBuilder: Equity(w) = PnL(w) / pnlRatio(w) per weekly reporting cycle."
    )
    return _section(
        "Growth & outcome composition", "".join(parts) + theory, anchor="tang-truong"
    )


def _render_limited_monte_carlo(result: Dict[str, Any]) -> str:
    """ "monte-carlo" cho LIMITED: dùng LẠI đúng `_render_monte_carlo` (đọc
    `result["mc"]`, không quan tâm status) khi engine đã chạy được thật --
    một bot LIMITED có đủ >= MIN_SAMPLE_SIZE điểm PnL tuần (thường mỏng,
    xem cảnh báo `sample_is_thin` đã thêm ở `_render_monte_carlo`) vẫn có mô
    phỏng thật, không phải bịa. Chỉ khi `mc` thật sự vắng (engine từ chối vì
    quá ít điểm) mới hiện khối giải thích, lấy ĐÚNG lý do engine đã dùng để
    chấm điểm (`components` -- không suy đoán lại).
    """
    rendered = _render_monte_carlo(result)
    if rendered:
        return rendered
    evidence = result.get("evidence") or {}
    reason = limited_view.monte_carlo_gap_reason(evidence) or (
        "Not enough weekly PnL points to run a Monte Carlo simulation."
    )
    return _section(
        "Monte Carlo simulation",
        _limited_gap_notice(_esc(reason)),
        anchor="monte-carlo",
    )


def _render_limited_market_scope(result: Dict[str, Any]) -> str:
    """ "thi-truong" cho LIMITED: bot 60004 không có `primary_share_pct`
    (cần sổ lệnh để tính tỉ trọng theo mã) nên không thể trả lời "thị
    trường được chấm chiếm bao nhiêu % hoạt động". Nêu rõ lý do và, nếu đọc
    được, số lượng hợp đồng bot đang chạy (`traderInsts`) như một tín hiệu
    thay thế thô -- KHÔNG suy ra tỉ trọng từ đó.
    """
    evidence = result.get("evidence") or {}
    instruments = limited_view.traded_instruments(evidence)
    reason = (
        "Could not compute what share of the bot's activity the scored market "
        "accounts for: a per-symbol share requires the per-position trade "
        "ledger, and OKX does not publicly expose this bot's trade ledger "
        "(error 60004)."
    )
    if instruments:
        # Chỉ nêu một mẫu nhỏ làm ví dụ -- một bot lưới/scalping có thể chạy
        # tới vài trăm hợp đồng (đo được: 269 ở bot mẫu của việc này), liệt
        # kê hết vào giữa một câu văn xuôi sẽ biến cả đoạn thành một khối
        # ký tự không đọc được. Danh sách ĐẦY ĐỦ nằm ở mục "Tài sản đang
        # giao dịch" (bảng, có phân trang bằng số lượng hiển thị).
        _SAMPLE_N = 8
        sample = ", ".join(instruments[:_SAMPLE_N])
        remaining = len(instruments) - _SAMPLE_N
        sample_text = sample + (f", and {remaining} other symbols" if remaining > 0 else "")
        reason += (
            f" The public profile shows the bot running {len(instruments)} "
            f"instruments (for example: {_esc(sample_text)} -- the full list is in "
            "the &quot;Traded assets&quot; section) -- this is a list only, with NO "
            "trading-value share between these instruments."
        )
    return _section(
        "Market being scored", _limited_gap_notice(reason), anchor="thi-truong"
    )


def _render_limited_playstyle(result: Dict[str, Any]) -> str:
    """ "cach-choi" cho LIMITED: tái dựng cách bot chơi (`strategy_drift`,
    `behavioral_risk` ở FULL) cần chuỗi lệnh với thời điểm mở/đóng, đòn bẩy,
    hướng lệnh -- không có gì trong số đó công khai cho một bot 60004.
    """
    reason = (
        "Could not reconstruct how this bot enters trades (direction, leverage, "
        "hold time, allocation by market phase): all of that requires reading "
        "individual trades directly from the trade ledger, and OKX does not "
        "publicly expose this bot's trade ledger (error 60004). What is public "
        "(ranking profile, daily stats) cannot say HOW THE BOT ENTERS TRADES, "
        "only the AGGREGATE RESULT."
    )
    return _section(
        "How this bot trades", _limited_gap_notice(reason), anchor="cach-choi"
    )


_LIMITED_PUBLIC_STATS_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("win_ratio_pct", "Share of winning days (public-stats)", "pct"),
    ("profit_days", "Winning days", "int"),
    ("loss_days", "Losing days", "int"),
    ("invest_amt", "Invested capital (investAmt)", "money"),
    ("avg_sub_pos_notional", "Avg sub-position notional", "money"),
    ("cur_copy_trader_pnl", "Current copier PnL", "money"),
    ("aum", "AUM (ranking profile)", "money"),
    ("pnl", "Total PnL (ranking profile)", "money"),
    ("pnl_ratio_pct", "Published return ratio", "pct"),
    ("lead_days", "Days as lead trader", "int"),
    ("copy_trader_num", "Current copiers", "int"),
    ("max_copy_trader_num", "Max copiers", "int"),
    ("acc_copy_trader_num", "Total copiers ever", "int"),
    ("rank", "Ranking position", "int"),
)


def _render_limited_public_stats(result: Dict[str, Any]) -> str:
    """ "so-lieu" cho LIMITED: bảng số liệu CÔNG KHAI (public-lead-traders +
    public-stats) -- KHÔNG phải bảng "Số liệu giao dịch" của FULL (đo trên
    sổ lệnh: profit factor, Sharpe, ...), dù dùng chung tiêu đề để mục lục
    hai bên khớp nhau. Chỉ những trường thật sự đọc được mới lên bảng.
    """
    evidence = result.get("evidence") or {}
    snapshot = limited_view.public_stats_snapshot(evidence)
    if not snapshot:
        return _section(
            "Trade metrics",
            _limited_gap_notice(
                "No public-lead-traders or public-stats data is readable for "
                "this bot -- there is no public data to show."
            ),
            anchor="so-lieu",
        )
    rows = []
    for key, label, kind in _LIMITED_PUBLIC_STATS_ROWS:
        value = snapshot.get(key)
        if value is None:
            continue
        text = {
            "pct": lambda v: _pct(v, 1),
            "int": _int_text,
            "money": _money,
        }[kind](value)
        rows.append([label, text])
    copy_state = snapshot.get("copy_state")
    if copy_state:
        rows.append(["Copy-trade status", _esc(copy_state)])
    table = _table(["Metric (public source)", "Value"], rows)
    notice = _limited_gap_notice(
        "This is AGGREGATE data by day/ranking profile that OKX still makes "
        "public, NOT a per-trade profit factor/Sharpe/expectancy (those metrics "
        "require the trade ledger, which this bot does not make public)."
    )
    return _section("Trade metrics", table + notice, anchor="so-lieu")


def _render_limited_drawdown(result: Dict[str, Any]) -> str:
    """ "sut-giam-von" cho LIMITED: đúng con số `_drawdown_component` trong
    `limited.py` đã CHẤM (không tính lại), tách khỏi chuỗi `findings` thành
    trường có cấu trúc (`evidence.drawdown_summary`). Mẫu số ở đây là ĐƯỜNG
    VỐN TUẦN (suy từ pnl/pnlRatio công khai), khác hẳn mẫu số "vốn tại đúng
    thời điểm lệnh đóng" mà `_render_drawdown_vs_capital` dùng cho một bot
    FULL (xem `Agent/backend/web/loss_analysis.py`'s docstring, cùng
    nguyên tắc: hai mẫu số khác nhau không phải mâu thuẫn).
    """
    evidence = result.get("evidence") or {}
    summary = limited_view.drawdown_summary(evidence)
    if not summary:
        return _section(
            "Drawdown vs. capital",
            _limited_gap_notice(
                "Could not infer drawdown from the weekly capital curve: no week "
                "has a PnL/ratio precise enough to convert into capital (see the "
                '"Score by risk dimension" section -- this bot\'s drawdown '
                "dimension is in a missing-data state, not a low-risk one)."
            ),
            anchor="sut-giam-von",
        )
    tiles = [
        _stat_tile(
            "Max drawdown (weekly capital curve)",
            _pct(summary["max_dd_pct"], 1),
            color=_risk_color(summary["max_dd_pct"]),
        ),
        _stat_tile(
            "Usable weeks",
            f"{_int_text(summary.get('usable_weeks'))}/{_int_text(summary.get('total_weeks'))}",
        ),
    ]
    body = f'<div class="stat-row">{"".join(tiles)}</div>'
    if summary.get("wiped_out"):
        body += _limited_gap_notice(
            "The weekly capital curve fell to zero during the observed period: "
            "the account was wiped out at least once by this measure."
        )
    theory = _theory(
        "Inferred weekly maximum drawdown (running peak minus trough). Finer trade-level ticks are unavailable for limited bots.",
        "EquityCurveBuilder weekly capital series: MaxDD = max(1 - Equity(w) / Peak(w))."
    )
    return _section("Drawdown vs. capital", body + theory, anchor="sut-giam-von")


def _render_limited_open_positions(result: Dict[str, Any]) -> str:
    """ "vi-the-mo" cho LIMITED: kiểm toán vị thế mở (PF tất toán sổ, độ
    lệch/độ nhọn PnL, ...) cần biết TỪNG vị thế đang mở lỗ/lãi bao nhiêu --
    không đọc được từ bất kỳ endpoint public nào còn sống ở một bot 60004.
    """
    reason = (
        "Could not audit open positions (unrealised loss, marked-to-market PF "
        "versus closed-book PF, PnL distribution skew/kurtosis): these metrics "
        "require knowing each of the bot's open positions individually, and "
        "OKX does not make that public for this bot. This does not mean the "
        "bot is not holding losers -- only that it cannot be observed."
    )
    return _section(
        "Open-position audit & return distribution",
        _limited_gap_notice(reason),
        tone="quiet",
        pair=True,
        anchor="vi-the-mo",
    )


def _render_limited_inference(result: Dict[str, Any]) -> str:
    """ "suy-luan" cho LIMITED: PSR/DSR (Bailey &amp; López de Prado) cần
    chuỗi lợi nhuận TỪNG LỆNH để tính skew/kurtosis/Sharpe mỗi lệnh -- một
    chuỗi PnL tuần chỉ có 12 điểm không đứng vào vai trò đó, kể cả khi
    Monte Carlo ở mục trên vẫn chạy được (chạy trên PnL tuần, không phải
    trên PnL từng lệnh).
    """
    reason = (
        "Could not infer the Probabilistic/Deflated Sharpe Ratio (PSR/DSR): "
        "both metrics require a PER-TRADE return series to estimate skew, "
        "kurtosis, and Sharpe per trade, while this bot's public data only has "
        "PnL AGGREGATED by week -- weekly aggregation cannot substitute for "
        "per-trade data, even though it is enough to run the rougher Monte "
        "Carlo simulation in the section above."
    )
    return _section(
        "Statistical inference",
        _limited_gap_notice(reason),
        tone="quiet",
        pair=True,
        anchor="suy-luan",
    )


def _render_limited_assets(result: Dict[str, Any]) -> str:
    """ "tai-san" cho LIMITED: danh sách hợp đồng bot đang chạy
    (`profile.traderInsts`) khi đọc được -- KHÔNG có tỉ trọng vốn/PnL theo
    từng tài sản (cần sổ lệnh để tính) như bảng "Tài sản đang giao dịch"
    của một bot FULL.
    """
    evidence = result.get("evidence") or {}
    instruments = limited_view.traded_instruments(evidence)
    if not instruments:
        return _section(
            "Traded assets",
            _limited_gap_notice(
                "Could not read the list of assets this bot trades from the "
                "remaining public data for this bot."
            ),
            anchor="tai-san",
        )
    # Chặn số dòng hiển thị -- một bot lưới/scalping có thể chạy tới vài
    # trăm hợp đồng (đo được: 269 ở bot mẫu của việc này); một bảng dài như
    # vậy với cột "Tỉ trọng" mà MỌI dòng đều "—" (không có tỉ trọng nào tính
    # được, xem docstring) không thêm thông tin gì so với một danh sách tên
    # thuần -- nên bỏ hẳn cột đó, chỉ liệt kê tên, và cắt ở
    # `_ASSET_LIST_LIMIT` dòng kèm chú thích tổng số, cùng kiểu với
    # `_render_closed_trades_table`'s "hiển thị N trong tổng số M" phía trên.
    _ASSET_LIST_LIMIT = 40
    shown = instruments[:_ASSET_LIST_LIMIT]
    rows = [[_esc(name)] for name in shown]
    table = _table(["Running instruments (traderInsts)"], rows)
    subtitle = ""
    if len(instruments) > _ASSET_LIST_LIMIT:
        subtitle = (
            "<p class='card-hint'>Showing "
            f"{_ASSET_LIST_LIMIT}/{len(instruments)} instruments.</p>"
        )
    notice = _limited_gap_notice(
        "This is only a LIST of instruments from the public ranking profile, "
        "with no capital/PnL share per asset -- that share requires the trade "
        "ledger, which this bot does not make public."
    )
    return _section(
        "Traded assets", table + subtitle + notice, anchor="tai-san"
    )


def _render_limited_trades_table(result: Dict[str, Any]) -> str:
    """ "danh-sach-lenh" cho LIMITED: không có gì để liệt kê -- đây CHÍNH LÀ
    dữ liệu OKX trả lỗi 60004, không phải một khoảng trống tình cờ.
    """
    reason = (
        "OKX does not publicly expose this bot's trade ledger (the trade-ledger "
        'endpoint returns error 60004 -- "Trader doesn\'t exist"): there are no '
        "trades to list here, even though the bot is still active and still "
        "publishes its ranking profile/daily stats in other sections of this page."
    )
    return _section(
        "Most recent closed trades",
        _limited_gap_notice(reason),
        anchor="danh-sach-lenh",
    )


def _render_limited_measured_evidence(result: Dict[str, Any]) -> str:
    """Bằng chứng thô của từng chiều ĐÃ ĐO ĐƯỢC, dạng KHỐI RỜI để nhúng vào
    trong chính mục "Điểm từng chiều rủi ro".

    Biểu đồ cho con số; phần này cho CĂN CỨ của con số đó. Với một bot giấu
    sổ lệnh thì đây chính là chỗ thể hiện việc kết hợp nhiều luồng public:
    mỗi chiều ghi rõ nó dựng trên bao nhiêu quan sát, từ endpoint nào.

    CỐ Ý KHÔNG dựng một `<section>` riêng: trang LIMITED phải có ĐÚNG cùng
    tập id mục với trang đầy đủ (yêu cầu "report đều giống nhau", đã khoá
    bằng `test_limited_result_has_the_same_section_ids_as_a_full_result`).
    Bản đầu của hàm này thêm mục `bang-chung-chieu` và lập tức phá vỡ đúng
    bất biến đó.
    """
    rows = limited_view.measured_component_evidence(result)
    if not rows:
        return ""
    blocks = []
    for row in rows:
        score = row.get("score")
        head = _esc(str(row.get("label") or "—"))
        score_html = (
            f'<span class="badge" style="--badge-color:{_risk_color(score)}">'
            f"{_num(score, 0)}</span>"
            if score is not None
            else ""
        )
        blocks.append(
            f'<div class="limited-evidence-row"><h3>{head} {score_html}</h3>'
            f"{_findings_list(row.get('findings'), limit=4)}</div>"
        )
    return (
        '<h3 class="limited-evidence-head">Evidence for each measured dimension</h3>'
        + "".join(blocks)
    )


def _render_limited_dimensions(result: Dict[str, Any]) -> str:
    """Mục "Điểm từng chiều rủi ro" của trang LIMITED: y hệt bản đầy đủ,
    kèm thêm bằng chứng thô của từng chiều đo được ngay bên dưới biểu đồ.

    Nhúng VÀO TRONG mục sẵn có chứ không tách mục mới -- xem
    `_render_limited_measured_evidence` cho lý do (bất biến "cùng tập id
    mục" giữa trang LIMITED và trang đầy đủ).
    """
    section = _render_dimensions_section(result)
    evidence = _render_limited_measured_evidence(result)
    if not section or not evidence:
        return section
    closing = "</section>"
    if not section.endswith(closing):
        return section
    return section[: -len(closing)] + evidence + closing


def _render_tab_report_limited(result: Dict[str, Any]) -> str:
    sections = [
        _render_conclusion(result),
        _render_limited_growth(result),
        _render_limited_narrative(result),
        _render_limited_dimensions(result),
        _render_limited_monte_carlo(result),
        _render_methodology_footer(result),
    ]
    return "".join(s for s in sections if s)


def _render_tab_market_limited(result: Dict[str, Any]) -> str:
    sections = [
        _render_dominant_market_card(result),
        _render_market_compatibility(result),
        _render_limited_market_scope(result),
        _render_limited_playstyle(result),
    ]
    return "".join(s for s in sections if s)


def _render_tab_trades_limited(result: Dict[str, Any]) -> str:
    sections = [
        _render_limited_public_stats(result),
        _render_validation_section(result),
        _render_scenario_lab(result),
        _render_limited_drawdown(result),
        _render_limited_open_positions(result),
        _render_limited_inference(result),
        _render_limited_assets(result),
        _render_limited_trades_table(result),
    ]
    return "".join(s for s in sections if s)



# --------------------------------------------------------------------------- #
# Deterministic insight sections.
#
# These render the objects `data.py` attaches under `evidence["insights"]` --
# the SAME objects the dossier and /api/v2/dossier publish. Nothing here
# computes a number: if a field is absent the section hides itself, which is
# how every other optional section in this module already behaves.
# --------------------------------------------------------------------------- #


def _insights(result: Dict[str, Any]) -> Dict[str, Any]:
    evidence = result.get("evidence") or {}
    insights = evidence.get("insights")
    return insights if isinstance(insights, dict) else {}


_NO_INSIGHT_REASON = (
    "This needs the bot's own closed-trade ledger. This page was built from a "
    "record that does not carry it, so the section is shown empty rather than "
    "dropped."
)


# Methodology text per insight section, shared by the populated and the empty
# render. An empty section keeps its methodology note on purpose: a reader who
# lands on a page that cannot compute one still learns what it would have shown
# and how, which is also what keeps the block counts identical across the live
# and saved-record paths.
_INSIGHT_THEORY: Dict[str, Tuple[str, str]] = {
    "holdout": (
        "Walk-forward holdout validation evaluates whether trading performance persists over time or suffers from curve-fitting and strategy decay. "
        "Compares earlier in-sample performance against subsequent out-of-sample windows. "
        "A Profit Factor Ratio (Later PF / Earlier PF) near or above 1.0 confirms consistency, while a ratio &lt;0.70 signals severe edge decay.",
        "Time-partitioned fold validation splitting the historical closed transaction ledger chronologically. "
        "Computes trade count, profit factors, fold-by-fold stability grade, and overall consistency across out-of-sample windows. See Agent/backend/report/qc/reporting/validation.py.",
    ),
    "market-compatibility": (
        "Market compatibility evaluates bot performance across historical market phases (Bull, Bear, Sideways, High/Low Volatility) "
        "and execution cost sensitivity (spread widening, order book depth degradation). "
        "A regime or scenario with insufficient observed trades is displayed as unmeasured rather than estimated.",
        "Trades are classified by the market regime active at entry time (`TradeLedgerItem.market_phase`). "
        "Reliability follows statistical thresholds: ≥10 trades valid, 3–9 reference only, &lt;3 unrepresentative. "
        "Cost sensitivity scenarios model slippage impact under stressed liquidity depth.",
    ),
    "scenario-lab": (
        "Scenario stress-testing simulates bot performance under diverse conditioned market regimes "
        "(e.g. persistent downtrends, extreme volatility spikes, liquidity droughts). "
        "Median (P50) reflects the expected outcome, the 5th–95th percentile span defines tail risk bounds, "
        "and Chance of Loss measures the probability of net capital impairment.",
        "Stationary bootstrap resampling (Politis &amp; Romano 1994) applied in blocks across the bot's own historical trades. "
        "Conditions lacking sufficient empirical observations are left unsimulated to prevent unsubstantiated extrapolation. See Agent/backend/report/qc/reporting/scenarios.py.",
    ),
}


def _insight_theory(anchor: str) -> str:
    read_html, basis_html = _INSIGHT_THEORY[anchor]
    return _theory(read_html, basis_html)


# Insight sections that cannot be computed render NOTHING.
#
# They used to render an empty card carrying the reason, on the theory that a
# visible "not measured" beats a silent omission. In practice a page rebuilt
# from a saved record cannot compute ANY of them, so the reader got four cards
# in a row repeating one sentence -- noise that pushed the real content down
# and taught nothing the fourth time it was read. The limitation is now stated
# once, in the data-limitations drawer at the foot of the result tab, which is
# where a reader looks for exactly that.
def _insight_placeholder(title: str, anchor: str) -> str:
    return ""


def _render_validation_section(result: Dict[str, Any]) -> str:
    """Did what the early trades showed keep being true later?"""
    if not _insights(result):
        return _insight_placeholder("Did earlier results hold up later", "holdout")
    validation = _insights(result).get("validation") or {}
    if not validation:
        return _insight_placeholder(
            "Did earlier results hold up later", "holdout"
        )
    if validation.get("status") != "EVALUATED":
        reasons = [str(r) for r in (validation.get("limitations") or [])]
        if not reasons:
            return _insight_placeholder(
                "Did earlier results hold up later", "holdout"
            )
        return _section(
            "Did earlier results hold up later",
            f'<p class="notice notice-neutral">{_esc("; ".join(reasons))}</p>',
            anchor="holdout",
        )

    rows = []
    for fold in validation.get("folds") or []:
        in_s = fold.get("in_sample") or {}
        out_s = fold.get("out_of_sample") or {}
        ratio = fold.get("profit_factor_ratio")
        in_pf = in_s.get("profit_factor")
        out_pf = out_s.get("profit_factor")
        rows.append(
            "<tr>"
            f'<td class="dim-col-name">Window {_int_text(fold.get("fold_index"))}</td>'
            f'<td class="dim-col-num">{_int_text(in_s.get("trades"))}</td>'
            f'<td class="dim-col-num">{_num(in_pf, 2) if in_pf is not None else "&mdash;"}</td>'
            f'<td class="dim-col-num">{_int_text(out_s.get("trades"))}</td>'
            f'<td class="dim-col-num">{_num(out_pf, 2) if out_pf is not None else "&mdash;"}</td>'
            f'<td class="dim-col-num">{_num(ratio, 2) if ratio is not None else "&mdash;"}</td>'
            f'<td class="dim-col-status">{_esc(str(fold.get("reliability") or "UNKNOWN"))}</td>'
            "</tr>"
        )
    headline = (
        '<div class="score-basis-alert score-basis-normal">'
        f'<span class="sb-badge-normal">{_esc(str(validation.get("stability_grade") or "UNKNOWN"))}</span> '
        f'{_int_text(validation.get("oos_profitable_folds"))} of '
        f'{_int_text(validation.get("folds_evaluated"))} later windows were in profit.'
        "</div>"
    )
    table = (
        '<table class="data-table"><thead><tr>'
        "<th>Window</th><th>Earlier trades</th><th>Earlier PF</th>"
        "<th>Later trades</th><th>Later PF</th><th>Later/Earlier</th><th>Grade</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )
    caveats = [str(c) for c in (validation.get("limitations") or [])]
    caveat_html = (
        f'<p class="notice notice-neutral">{_esc("; ".join(caveats))}</p>'
        if caveats
        else ""
    )
    return _section(
        "Did earlier results hold up later",
        headline
        + table
        + caveat_html
        + _insight_theory("holdout"),
        anchor="holdout",
    )


def _render_scenario_lab(result: Dict[str, Any]) -> str:
    """Named what-ifs, each with an interval rather than a single number."""
    if not _insights(result):
        return _insight_placeholder("Scenario laboratory", "scenario-lab")
    lab = _insights(result).get("scenario_laboratory") or {}
    # Execution-cost scenarios are a property of the market the bot trades in
    # and are shown on the market tab under "Cost sensitivity". Rendering them
    # here as well put the same two rows on two tabs.
    scenarios = [
        s for s in (lab.get("scenarios") or []) if s.get("family") != "EXECUTION"
    ]
    if not scenarios:
        return _insight_placeholder("Scenario laboratory", "scenario-lab")
    rows = []
    for scenario in scenarios:
        band = scenario.get("total_pnl") or {}
        simulated = scenario.get("status") == "SIMULATED" and band.get("p50") is not None
        label = str(scenario.get("name") or "")
        if scenario.get("family") == "REGIME":
            label = f"Behaviour in the {_phase_label_vi(label)} phase"
        span = (
            f'{_num(band.get("p05"), 0)} &hellip; {_num(band.get("p95"), 0)}'
            if simulated
            else "&mdash;"
        )
        loss = scenario.get("probability_of_loss_pct")
        rows.append(
            "<tr>"
            f'<td class="dim-col-name"><strong>{_esc(label)}</strong></td>'
            f'<td class="dim-col-num">{_int_text(scenario.get("sample_size"))}</td>'
            f'<td class="dim-col-num">{_num(band.get("p50"), 0) if simulated else "&mdash;"}</td>'
            f'<td class="dim-col-num">{span}</td>'
            f'<td class="dim-col-num">{_pct(loss, 0) if loss is not None else "&mdash;"}</td>'
            f'<td class="dim-col-status">{_esc(str(scenario.get("status") or ""))}</td>'
            "</tr>"
        )
    untested = [_phase_label_vi(u) for u in (lab.get("untested_conditions") or [])]
    untested_html = (
        '<p class="notice notice-neutral">Never observed, so not simulated: '
        f'{_esc(", ".join(untested))}</p>'
        if untested
        else ""
    )
    return _section(
        "Scenario laboratory",
        '<table class="data-table"><thead><tr>'
        "<th>Scenario</th><th>Trades</th><th>Median</th><th>5th&ndash;95th</th>"
        "<th>Chance of loss</th><th>Status</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        + untested_html
        + _insight_theory("scenario-lab"),
        anchor="scenario-lab",
    )


def _render_market_compatibility(result: Dict[str, Any]) -> str:
    """Where this bot has actually traded, regime by regime.

    Market-conditioned, so it belongs in the market tab rather than the
    user-facing overview. A regime with no observed trade is shown as a row
    with no numbers, not omitted -- leaving it out would show the reader only
    the conditions that happened to go well.
    """
    if not _insights(result):
        return _insight_placeholder("Market compatibility", "market-compatibility")
    compat = _insights(result).get("market_compatibility") or {}
    cells = compat.get("cells") or []
    if not cells:
        return _insight_placeholder("Market compatibility", "market-compatibility")

    rows = []
    for cell in cells:
        observed = cell.get("observed_trades") or 0
        pnl = cell.get("total_pnl")
        wr = cell.get("win_rate")
        tested = cell.get("status") == "OBSERVED" and observed > 0
        rows.append(
            "<tr>"
            f'<td class="dim-col-name"><strong>{_esc(_phase_label_vi(cell.get("regime")))}</strong></td>'
            f'<td class="dim-col-num">{_int_text(observed)}</td>'
            f'<td class="dim-col-num">{_num(wr, 1) + "%" if tested and wr is not None else "&mdash;"}</td>'
            f'<td class="dim-col-num">{_num(pnl, 0) if tested and pnl is not None else "&mdash;"}</td>'
            f'<td class="dim-col-status">{_esc(str(cell.get("reliability") or "UNKNOWN"))}</td>'
            "</tr>"
        )

    # Execution scenarios are a property of the market the bot trades in (spread,
    # depth), so they sit here rather than with the bot-conditioned scenarios.
    lab = _insights(result).get("scenario_laboratory") or {}
    exec_rows = []
    for scenario in lab.get("scenarios") or []:
        if scenario.get("family") != "EXECUTION":
            continue
        band = scenario.get("total_pnl") or {}
        simulated = scenario.get("status") == "SIMULATED" and band.get("p50") is not None
        exec_rows.append(
            "<tr>"
            f'<td class="dim-col-name"><strong>{_esc(str(scenario.get("name") or ""))}</strong></td>'
            f'<td class="dim-col-num">{_int_text(scenario.get("sample_size"))}</td>'
            f'<td class="dim-col-num">{_num(band.get("p50"), 0) if simulated else "&mdash;"}</td>'
            f'<td class="dim-col-num">'
            f'{_num(band.get("p05"), 0) + " &hellip; " + _num(band.get("p95"), 0) if simulated else "&mdash;"}'
            "</td>"
            f'<td class="dim-col-status">{_esc(str(scenario.get("status") or ""))}</td>'
            "</tr>"
        )
    exec_html = (
        '<h3>Cost sensitivity</h3>'
        '<table class="data-table"><thead><tr>'
        "<th>Scenario</th><th>Trades</th><th>Median</th><th>5th&ndash;95th</th><th>Status</th>"
        f'</tr></thead><tbody>{"".join(exec_rows)}</tbody></table>'
        if exec_rows
        else ""
    )

    limitations = [str(x) for x in (compat.get("limitations") or [])]
    limit_html = (
        f'<p class="notice notice-neutral">{_esc("; ".join(limitations))}</p>'
        if limitations
        else ""
    )
    return _section(
        "Market compatibility",
        '<table class="data-table"><thead><tr>'
        "<th>Market phase</th><th>Trades</th><th>Win rate</th><th>Net PnL</th><th>Reliability</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        + limit_html
        + exec_html
        + _insight_theory("market-compatibility"),
        anchor="market-compatibility",
    )


def _render_methodology_footer(result: Dict[str, Any]) -> str:
    """Data limitations and open questions, folded away at the foot of the tab.

    Deliberately NOT a `<section class="card">`: the result tab is the
    user-facing overview and must not grow another card. This is a closed
    accordion after the last card, so an ordinary reader is not stopped by it
    and an auditor can still open it.
    """
    insights = _insights(result)
    if not insights:
        # One statement, naming exactly which analyses are missing and why,
        # instead of an empty card per analysis.
        missing = (
            "Behavioural DNA, holdout validation, the scenario laboratory and "
            "market compatibility"
        )
        return (
            '<details class="theory methodology-footer" id="phuong-phap">'
            "<summary>Data limitations</summary>"
            f'<div class="theory-body"><p class="notice notice-neutral">'
            f"{_esc(missing)} need this bot's own closed-trade ledger. This page "
            "was built from a saved record that does not carry it, so those "
            "analyses were not run. They are available on a live analysis."
            "</p></div></details>"
        )
    questions = insights.get("user_questions") or []
    passport = insights.get("uncertainty") or {}
    reasons = passport.get("abstention_reasons") or []
    if not questions and not reasons:
        return ""

    blocks: List[str] = []
    if reasons:
        blocks.append(
            '<div class="mf-group"><div class="mf-title">What the evidence does not settle</div>'
            "<ul class=\"mf-list\">"
            + "".join(f"<li>{_esc(str(r))}</li>" for r in reasons)
            + "</ul></div>"
        )
    if questions:
        items = []
        for q in questions:
            text = str(q.get("question") or "")
            # The core keeps the machine phase key (it is an identifier for the
            # API and MCP); this module owns the human label vocabulary, so the
            # enum is translated here rather than leaked onto the page.
            if q.get("answered_by") == "UNTESTED_REGIME_SCENARIO":
                regime = str(q.get("question_id") or "").rsplit(".", 1)[-1]
                text = text.replace(regime, _phase_label_vi(regime))
            items.append(
                f"<li><strong>{_esc(text)}</strong>"
                f'<span class="mf-why">{_esc(str(q.get("why_it_is_open") or ""))}</span></li>'
            )
        blocks.append(
            '<div class="mf-group"><div class="mf-title">Open questions</div>'
            f'<ul class="mf-list">{"".join(items)}</ul></div>'
        )
    reliability = passport.get("overall_reliability") or "UNKNOWN"
    return (
        '<details class="theory methodology-footer" id="phuong-phap">'
        f"<summary>Data limitations &amp; open questions &middot; evidence reliability: {_esc(str(reliability))}</summary>"
        f'<div class="theory-body">{"".join(blocks)}</div>'
        "</details>"
    )


def _render_tab_report(result: Dict[str, Any]) -> str:
    if result.get("status") == "LIMITED":
        return _render_tab_report_limited(result)
    sections = [
        _render_conclusion(result),
        _render_growth_section(result),
        _render_narrative(result),
        _render_dimensions_section(result),
        _render_monte_carlo(result),
        _render_methodology_footer(result),
    ]
    return "".join(s for s in sections if s)


def _render_tab_market(result: Dict[str, Any]) -> str:
    if result.get("status") == "LIMITED":
        return _render_tab_market_limited(result)
    sections = [
        _render_dominant_market_card(result),
        _render_market_compatibility(result),
        _render_market_coverage(result),
        _render_strategy_section(result),
    ]
    return "".join(s for s in sections if s)


def _render_drawdown_vs_capital(result: Dict[str, Any]) -> str:
    """Mục "Sụt giảm so với vốn" -- tính lại từ chính sổ lệnh đã chốt.

    Trả lời ba câu mà một con số "sụt vốn tối đa" đơn lẻ KHÔNG trả lời được:
    một lệnh tệ nhất mất bao nhiêu so với vốn, đợt sụt sâu nhất diễn ra
    trong mấy lệnh và đã hồi chưa, và chuỗi thua liên tiếp tốn kém nhất mất
    bao nhiêu TIỀN (`max_loss_streak` cũ chỉ đếm số lệnh).

    Toàn bộ phép tính nằm ở `Agent/backend/web/loss_analysis.py`; ở đây chỉ
    trình bày. Mục tự ẩn khi không đọc được lệnh đã chốt nào.
    """
    profile = compute_loss_profile(result.get("evidence"))
    if not profile:
        return ""

    capital = profile.get("capital")
    has_capital = _is_finite_number(capital)

    def _loss_pct(value: Any) -> str:
        return _pct(value, 1) if _is_finite_number(value) else "—"

    worst = profile.get("worst_trade")
    episode = profile.get("deepest_episode")
    streak = profile.get("worst_losing_streak")
    gross = profile.get("gross_loss") or {}

    worst_val = (
        _loss_pct((worst or {}).get("pct_of_capital"))
        if has_capital
        else _money((worst or {}).get("pnl"))
    ) if worst else "No losing trades yet"

    episode_val = (
        _loss_pct((episode or {}).get("depth_pct"))
        if has_capital
        else _money(-(episode or {}).get("depth_abs", 0.0))
    ) if episode else "No drawdown yet"

    streak_val = (
        _loss_pct((streak or {}).get("pct_of_capital"))
        if has_capital
        else _money((streak or {}).get("total_loss"))
    ) if streak else "None"

    gross_val = (
        _loss_pct(gross.get("pct_of_capital"))
        if has_capital
        else _money(gross.get("total"))
    )

    items = [
        ("Worst single loss", worst_val, "#dc2626" if worst else None),
        ("Deepest drawdown episode", episode_val, "#dc2626" if episode else None),
        ("Most costly losing streak", streak_val, "#dc2626" if streak else None),
        ("Total gross loss", gross_val, "#dc2626" if gross.get("total") else None),
    ]

    param_row_list = []
    for k, v, c in items:
        val_style = f' style="color:{c};"' if c else ""
        param_row_list.append(
            f'<div class="param-horizontal-row">'
            f'<span class="param-horizontal-name">{_esc(k)}</span>'
            f'<span class="param-horizontal-val"{val_style}>{_esc(v)}</span>'
            f'</div>'
        )
    param_rows_html = "".join(param_row_list)
    body = f'<div class="param-horizontal-list">{param_rows_html}</div>'

    if not has_capital:
        body += (
            '<div class="notice notice-warning">Could not infer reference capital from'
            " this bot's public capital curve, so every loss figure below is shown as"
            " an absolute amount -- NOT converted to a percentage of capital (no"
            " denominator means no percentage; this is missing data, not low risk).</div>"
        )

    worst_list = profile.get("worst_trades") or []
    if worst_list:
        rows = []
        for item in worst_list:
            pct = item.get("pct_of_capital")
            measured = _is_finite_number(pct)
            rows.append(
                _BarRow(
                    _format_vn_timestamp(item["close_time"])
                    if _is_finite_number(item.get("close_time"))
                    else "—",
                    float(pct) if measured else None,
                    _verdict_color("HIDDEN RISK") if False else "#dc2626",
                    f"{_money(item.get('pnl'))}"
                    + (f" · {_pct(pct, 1)} of capital" if measured else ""),
                    measured=measured,
                )
            )
        largest = max(
            (float(r.value) for r in rows if r.value is not None), default=0.0
        )
        body += "<h3>Five worst losing trades</h3>" + _horizontal_bars(
            rows, max_value=max(largest, 1.0), width=860.0, value_w=210.0
        )

    if episode:
        recovered = episode.get("recovered")
        depth_val = -float(episode.get("depth_abs", 0.0))
        depth_str = _money(depth_val) + (
            f" · {_pct(episode.get('depth_pct'), 1)} of reference capital"
            if _is_finite_number(episode.get("depth_pct"))
            else ""
        )
        dur_hours = episode.get("duration_hours")
        dur_str = f"{_num(dur_hours, 1)} hours" if _is_finite_number(dur_hours) else "—"
        recovered_badge = (
            '<span style="display:inline-block;background:rgba(22,163,74,0.15);color:#16a34a;border:1px solid rgba(22,163,74,0.35);font-family:var(--mono);font-weight:700;font-size:0.75rem;padding:0.15rem 0.5rem;border-radius:4px;">RECOVERED</span>'
            if recovered
            else '<span style="display:inline-block;background:rgba(220,38,38,0.15);color:#dc2626;border:1px solid rgba(220,38,38,0.35);font-family:var(--mono);font-weight:700;font-size:0.75rem;padding:0.15rem 0.5rem;border-radius:4px;">NOT RECOVERED</span>'
        )
        trough_str = _money(episode.get("trough_cum"))
        trough_color = "#ef4444" if str(trough_str).startswith("-") else "#10b981"
        episode_rows = [
            ["Capital peak before the fall", f'<span style="color:#10b981;font-weight:600;font-family:var(--mono);">+{_esc(_money(episode.get("peak_cum")))}</span>'],
            ["Trough of the drawdown", f'<span style="color:{trough_color};font-weight:600;font-family:var(--mono);">{_esc(trough_str)}</span>'],
            [
                "Depth",
                f'<span style="color:#ef4444;font-weight:700;font-family:var(--mono);">{_esc(depth_str)}</span>',
            ],
            ["Trades from peak to trough", f'<span style="font-family:var(--mono);">{_esc(_int_text(episode.get("trade_count")))}</span>'],
            [
                "Duration",
                f'<span style="font-family:var(--mono);">{_esc(dur_str)}</span>',
            ],
            [
                "Recovered to the previous peak?",
                recovered_badge,
            ],
        ]
        body += "<h3>Deepest drawdown episode</h3>" + _table(
            ["Metric", "Value"], episode_rows
        )

    if streak:
        body += (
            '<p class="card-hint">Most costly consecutive losing streak: '
            f"<strong>{_int_text(streak.get('count'))} trades</strong> losing "
            f"<strong>{_money(streak.get('total_loss'))}</strong>"
            + (
                f" ({_pct(streak.get('pct_of_capital'), 1)} of reference capital)"
                if _is_finite_number(streak.get("pct_of_capital"))
                else ""
            )
            + ". Selected by TOTAL MONEY LOST rather than trade count: a short"
            " streak that loses a lot is more dangerous than a long streak that"
            " loses little.</p>"
        )

    theory = _theory(
        "Capital drawdown and downside severity analysis answering three critical risk questions: "
        "the single worst loss relative to capital, the deepest peak-to-trough drawdown episode "
        "(depth %, duration in hours, and whether equity recovered to its previous high), "
        "and the most costly consecutive losing streak ranked by total money lost rather than trade count.",
        "Reconstructed from chronological closed trade sequence against reference capital (Agent/backend/web/loss_analysis.py). "
        "Drawdown depth = (Running Peak − Current Trough) / Reference Capital. "
        "Losing streaks are ranked by cumulative dollar loss to highlight true capital destruction risk.",
    )
    return _section("Drawdown vs. capital", body + theory, anchor="sut-giam-von")


def _render_tab_trades(result: Dict[str, Any]) -> str:
    if result.get("status") == "LIMITED":
        return _render_tab_trades_limited(result)
    sections = [
        _render_trade_metrics(result),
        _render_validation_section(result),
        _render_scenario_lab(result),
        _render_drawdown_vs_capital(result),
        _render_open_positions_audit(result),
        _render_statistical_inference(result),
        _render_assets(result),
        _render_closed_trades_table(result),
    ]
    return "".join(s for s in sections if s)


# Text shown in place of a panel a role does not receive. It is deliberately a
# visible statement rather than an absent element: the design contract requires
def _render_locked_panel(panel_type: str = "market") -> str:
    if panel_type == "market":
        title = "Premium Market Intelligence"
        desc = (
            "Phân tích chuyên sâu vi cấu trúc sổ lệnh OKX, áp lực dòng tiền cá mập Taker "
            "và đo lường thanh khoản đa sàn thời gian thực."
        )
        features = [
            ("📊 L2 Orderbook Microstructure", "Đo lường độ lệch cung cầu thực tế, spread và kiểm toán độ sâu thanh khoản."),
            ("🐋 Whale Taker Volume Flow", "Phân tích dòng tiền mua/bán chủ động của cá mập và biến động khối lượng thực."),
            ("💧 Liquidity & Slippage Matrix", "Mô phỏng độ trượt giá theo các kích thước vốn lớn và rủi ro cạn kiệt thanh khoản."),
        ]
        plan_badge = "PRO / INSTITUTIONAL"
    else:
        title = "Orders & Detailed Position Audit"
        desc = (
            "Kiểm toán toàn bộ 200+ lệnh đã khớp, mô phỏng stress test vị thế mở "
            "và phân rã xác suất cháy tài khoản đa chiều."
        )
        features = [
            ("📑 Complete Trade Execution Ledger", "Nhật ký khớp lệnh chi tiết, thời gian nắm giữ, phí giao dịch và PnL lũy kế."),
            ("⚠️ Mark-to-Market Position Stress", "Kiểm toán vị thế mở thực tế theo giá thị trường và cảnh báo găm lỗ ảo."),
            ("📐 Return Distribution Geometry", "Đo lường độ lệch âm, độ nhọn phân phối đuôi dày và rủi ro thiên nga đen."),
        ]
        plan_badge = "PRO / ENTERPRISE"

    feature_items = "".join(
        f'<div class="locked-feature-item">'
        f'<div class="locked-feature-title">{_esc(f_title)}</div>'
        f'<div class="locked-feature-desc">{_esc(f_desc)}</div>'
        f'</div>'
        for f_title, f_desc in features
    )

    return (
        f'<section class="card card-locked" id="detail-withheld">'
        f'<div class="locked-card-container">'
        f'<div class="locked-badge-row">'
        f'<span class="locked-status-badge">🔒 LOCKED FEATURE</span>'
        f'<span class="locked-plan-badge">{plan_badge}</span>'
        f'</div>'
        f'<h2 class="locked-title">{_esc(title)}</h2>'
        f'<p class="locked-subtitle">{_esc(desc)}</p>'
        f'<div class="locked-features-grid">{feature_items}</div>'
        f'<div class="locked-action-box">'
        f'<p class="withheld-note locked-note" data-withheld="DETAIL_WITHHELD_BY_ROLE">'
        f'Tài khoản hiện tại ở gói Basic chỉ bao gồm thẻ Kết quả phân tích (Analyst Result). '
        f'Các tab dữ liệu chuyên sâu có ổ khoá sẽ tự động mở khóa khi nâng cấp gói dịch vụ.'
        f'</p>'
        f'<button type="button" class="btn-upgrade-plan" onclick="alert(\'Tính năng nâng cấp gói tài khoản đang kết nối cổng thanh toán Web3. Vui lòng liên hệ quản trị viên để mở khóa trước.\')">'
        f'⚡ Nâng cấp gói để mở khóa'
        f'</button>'
        f'</div>'
        f'</div>'
        f'</section>'
    )


WITHHELD_BY_ROLE_HTML = _render_locked_panel("market")


def _render_tabs_wrapper(
    tab1_content: str,
    tab2_content: str,
    tab3_content: str,
    *,
    hidden_panels: Sequence[str] = (),
) -> str:
    """Assemble the three tabs.

    `hidden_panels` names panel ids the current role does not receive. The
    panel element and its semantic id ALWAYS remain -- they are a compatibility
    contract that the SPA, tests and deep links all rely on -- so a hidden panel
    keeps its shell and carries an explicit withheld notice instead of its body.
    Removing the element outright is what the client used to do, and it made
    "you may not see this" indistinguishable from "this does not exist".
    """
    hidden = set(hidden_panels)
    if "panel-market" in hidden:
        tab2_content = _render_locked_panel("market")
    if "panel-trades" in hidden:
        tab3_content = _render_locked_panel("trades")
    tab_label_attr = ""
    if hidden:
        tab_label_attr = f' data-hidden-panels="{" ".join(sorted(hidden))}"'

    market_icon = "🔒" if "panel-market" in hidden else "🌐"
    market_class = "tab-label label-market" + (" tab-label-locked" if "panel-market" in hidden else "")
    trades_icon = "🔒" if "panel-trades" in hidden else "📑"
    trades_class = "tab-label label-trades" + (" tab-label-locked" if "panel-trades" in hidden else "")

    return (
        f'<div class="tabs-control-wrapper"{tab_label_attr}>'
        '<input type="radio" name="main_tabs" id="tab-nav-report" class="tab-nav-radio" checked style="display:none!important;position:absolute!important;opacity:0!important;pointer-events:none!important;">'
        '<input type="radio" name="main_tabs" id="tab-nav-market" class="tab-nav-radio" style="display:none!important;position:absolute!important;opacity:0!important;pointer-events:none!important;">'
        '<input type="radio" name="main_tabs" id="tab-nav-trades" class="tab-nav-radio" style="display:none!important;position:absolute!important;opacity:0!important;pointer-events:none!important;">'
        '<div class="tabs-header-container">'
        '<div class="tabs-nav-bar" role="tablist">'
        '<label class="tab-label label-report" for="tab-nav-report" id="label-tab-report" tabindex="0">'
        '<span class="tab-icon">📊</span> <span class="tab-title">Analyst Result</span>'
        "</label>"
        f'<label class="{market_class}" for="tab-nav-market" id="label-tab-market" tabindex="0">'
        f'<span class="tab-icon">{market_icon}</span> <span class="tab-title">Premium Market</span>'
        "</label>"
        f'<label class="{trades_class}" for="tab-nav-trades" id="label-tab-trades" tabindex="0">'
        f'<span class="tab-icon">{trades_icon}</span> <span class="tab-title">Other &amp; Position</span>'
        "</label>"
        "</div>"
        "</div>"
        '<div class="tab-panels">'
        f'<div class="tab-panel panel-report" id="panel-report" role="tabpanel">{tab1_content}</div>'
        f'<div class="tab-panel panel-market" id="panel-market" role="tabpanel">{tab2_content}</div>'
        f'<div class="tab-panel panel-trades" id="panel-trades" role="tabpanel">{tab3_content}</div>'
        "</div>"
        "</div>"
    )


# --------------------------------------------------------------------------- #
# Left rail (mục lục + danh tính + điểm số) -- xem `_render_header`'s comment
# for why the identity/score blocks live here rather than at the top of the
# scrolling column.
# --------------------------------------------------------------------------- #


_SECTION_HEADING_RE = re.compile(
    r'<section class="card[^"]*" id="([^"]+)">.*?<h2>(.*?)</h2>', re.S
)


def _nav_items(tab_html: str) -> List[Tuple[str, str]]:
    """Mục lục tự sinh từ chính HTML vừa render -- không có một danh sách
    tiêu đề thứ hai phải nhớ cập nhật mỗi khi thêm/bớt/đổi tên một mục, và
    một mục bị ẩn (body rỗng -> `_section` trả chuỗi rỗng) tự động biến mất
    khỏi mục lục thay vì để lại một anchor chết.
    """
    return [
        (anchor, html.unescape(title))
        for anchor, title in _SECTION_HEADING_RE.findall(tab_html)
    ]


def _render_nav(tab1_content: str, tab2_content: str, tab3_content: str) -> str:
    groups = (
        ("report", "Analyst Result", tab1_content),
        ("market", "Premium Market", tab2_content),
        ("trades", "Other & Position", tab3_content),
    )
    out: List[str] = []
    for tab_key, label, content in groups:
        items = _nav_items(content)
        if not items:
            continue
        links = "".join(
            f'<a href="#{_esc(anchor)}" data-tab="{tab_key}">{_esc(title)}</a>'
            for anchor, title in items
        )
        out.append(
            f'<div class="nav-group" data-group="{tab_key}">'
            f'<div class="nav-group-label">{_esc(label)}</div>'
            f"{links}</div>"
        )
    if not out:
        return ""
    return f'<nav class="nav" aria-label="Report table of contents">{"".join(out)}</nav>'


def _render_sidebar(side_blocks: str, nav_html: str) -> str:
    return (
        '<aside class="side">'
        '<div class="brand"><b>OKX bot risk</b>'
        "<span>AI-powered risk monitoring</span></div>"
        f'<div class="side-identity">{side_blocks}</div>'
        f"{nav_html}"
        '<div class="side-foot">'
        '<button type="button" class="theme-toggle-btn" id="theme-toggle-btn-sidebar"'
        ' aria-label="Switch Light/Dark mode" title="Switch Light/Dark theme">'
        '<span class="theme-icon theme-icon-light">☀️ Light</span>'
        '<span class="theme-icon theme-icon-dark">🌙 Dark</span>'
        "</button>"
        "</div>"
        "</aside>"
    )


# --------------------------------------------------------------------------- #
# NOT_FOUND page
# --------------------------------------------------------------------------- #


def _render_not_found_body(result: Dict[str, Any]) -> str:
    code = result.get("code") or ""
    text_lines = result.get("text") or []
    message = (
        text_lines[0]
        if text_lines and isinstance(text_lines[0], str)
        else (f"No bot found with code {code!r} on OKX.")
    )
    return (
        '<div class="card not-found">'
        "<h1>Bot not found</h1>"
        f"<p>Lookup code: <code>{_esc(code)}</code></p>"
        f"<p>{_esc(message)}</p>"
        "</div>"
    )


# --------------------------------------------------------------------------- #
# CSS -- theme-aware, mobile-first. No external stylesheet, per module
# constraints (see docstring). The `:root`/dark-mode CUSTOM-PROPERTY
# DEFINITIONS this class-rule CSS relies on (--bg, --text, --border, the
# verdict-tier colors, ...) no longer live in this string -- they are read
# from Agent/web/tokens.css and embedded ahead of this constant by
# `render_bot_report_html` below (see `_design_tokens_css_text`/Việc 3).
# This string keeps only the CLASS/ELEMENT rules that reference those
# variables via `var(...)`.
# --------------------------------------------------------------------------- #

_CSS = """
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: var(--font-size-md);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* --- Khung trang: bảng điều khiển 2 cột -----------------------------------
   Mobile-first: một cột, cột trái (`aside.side`) trở thành khối tóm tắt nằm
   trên cùng. Từ 1100px trở lên mới tách thành lưới [rail cố định | nội dung]
   và rail dính lại khi cuộn -- danh tính bot + 3 điểm số + mục lục là thứ
   luôn đúng bất kể đang đọc tới đâu, nên không được trôi mất theo trang. */
.page { width: 100%; margin: 0; }
.main { min-width: 0; max-width: 1560px; margin: 0 auto; padding: 20px 20px 3rem; overflow-x: hidden; }

.side {
  display: none !important;
}

/* --- Institutional Color Tokens Fallback --- */
/* --- Institutional Color Tokens Fallback --- */
/* MẶC ĐỊNH LÀ SÁNG, TỐI CHỈ KHI ĐƯỢC YÊU CẦU.
   Bản trước đặt bảng màu TỐI vào `:root` VÔ ĐIỀU KIỆN như "fallback", trong
   khi `Agent/web/tokens.css` (nạp trước file này) lấy SÁNG làm nền. Hai bảng
   màu đá nhau, và bên tối thắng vì nạp sau.
   Hệ quả đo được trên trang thật: script đặt `data-theme` nằm CUỐI <body> và
   chỉ chạy khi localStorage đã có lựa chọn sẵn -- nên khách vào LẦN ĐẦU không
   bao giờ có thuộc tính đó, trang kẹt ở nền sáng của tokens.css trộn với
   `--panel/--panel-2/--ink` tối của khối này: tiêu đề mục và chữ trong <code>
   thành tối trên nền tối, gần như không đọc được.
   Sửa theo đúng quy ước sẵn có của `tokens.css`: SÁNG là nền không điều kiện,
   TỐI áp dụng khi hệ điều hành ưa tối (và người dùng chưa chọn sáng) hoặc khi
   chọn tối tường minh. Không biến nào bị mất -- hai khối vốn khai báo đúng
   cùng 23 biến. */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --s1: #3b82f6; --s2: #f97316; --s3: #10b981;
    --s4: #f59e0b; --s5: #ec4899; --s6: #14b8a6;
    --ground: #0B0F19;
    --panel: #111726;
    --panel-2: #161F32;
    --panel-3: #1A243B;
    --ink: #FFFFFF;
    --ink-2: #CBD5E1;
    --ink-3: #94A3B8;
    --line: #1E293B;
    --line-2: #2B3954;
    --amber: #F59E0B;
    --amber-bg: rgba(245, 158, 11, 0.12);
    --up: #10B981;
    --down: #F43F5E;
    --info: #38BDF8;
    --track: #161F32;
    --header-bg: rgba(11, 15, 25, 0.85);
    --header-border: #1E293B;
    --text: var(--ink);
    --muted: var(--ink-2);
    --axis: #64748b;
}
}
:root[data-theme="dark"] {
  --s1: #3b82f6; --s2: #f97316; --s3: #10b981;
  --s4: #f59e0b; --s5: #ec4899; --s6: #14b8a6;
  --ground: #0B0F19;
  --panel: #111726;
  --panel-2: #161F32;
  --panel-3: #1A243B;
  --ink: #FFFFFF;
  --ink-2: #CBD5E1;
  --ink-3: #94A3B8;
  --line: #1E293B;
  --line-2: #2B3954;
  --amber: #F59E0B;
  --amber-bg: rgba(245, 158, 11, 0.12);
  --up: #10B981;
  --down: #F43F5E;
  --info: #38BDF8;
  --track: #161F32;
  --header-bg: rgba(11, 15, 25, 0.85);
  --header-border: #1E293B;
  --text: var(--ink);
  --muted: var(--ink-2);
  --axis: #64748b;
  --mc-pill-bg: #0b111e;
  --mc-pill-border: #2b3954;
  --mc-grid-line: #1e293b;
  --mc-grid-text: #94a3b8;
  --mc-be-line: rgba(255, 255, 255, 0.35);
  --mc-be-text: #94a3b8;
  --mc-whisker: #64748b;
  --mc-med-text: #ffffff;
}
:root {
  --s1: #2563eb; --s2: #ea580c; --s3: #10b981;
  --s4: #d97706; --s5: #db2777; --s6: #059669;
  --ground: #F8FAFC;
  --panel: #FFFFFF;
  --panel-2: #F1F5F9;
  --panel-3: #E2E8F0;
  --ink: #0F172A;
  --ink-2: #475569;
  --ink-3: #64748B;
  --line: #E2E8F0;
  --line-2: #CBD5E1;
  --amber: #D97706;
  --amber-bg: #FEF3C7;
  --up: #059669;
  --down: #DC2626;
  --info: #0284C7;
  --track: #F1F5F9;
  --header-bg: rgba(255, 255, 255, 0.88);
  --header-border: #E2E8F0;
  --text: var(--ink);
  --muted: var(--ink-2);
  --axis: #94a3b8;
  --mc-pill-bg: #ffffff;
  --mc-pill-border: #cbd5e1;
  --mc-grid-line: #e2e8f0;
  --mc-grid-text: #64748b;
  --mc-be-line: rgba(15, 23, 42, 0.35);
  --mc-be-text: #475569;
  --mc-whisker: #94a3b8;
  --mc-med-text: #0f172a;
}
:root[data-theme="light"] {
  --mc-pill-bg: #ffffff;
  --mc-pill-border: #cbd5e1;
  --mc-grid-line: #e2e8f0;
  --mc-grid-text: #64748b;
  --mc-be-line: rgba(15, 23, 42, 0.35);
  --mc-be-text: #475569;
  --mc-whisker: #94a3b8;
  --mc-med-text: #0f172a;
}

/* --- Top Header (Shared Institutional OKX AI Design System) --- */
.top-header {
  height: 56px;
  width: 100%;
  background: rgba(9, 13, 22, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  transition: background 0.2s ease, border-color 0.2s ease;
}
:root[data-theme="light"] .top-header {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 18px;
}
.header-divider {
  width: 1px;
  height: 22px;
  background: rgba(255, 255, 255, 0.1);
}
:root[data-theme="light"] .header-divider {
  background: rgba(15, 23, 42, 0.1);
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  cursor: pointer;
  user-select: none;
  text-decoration: none;
}
.brand-logo-box {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(145deg, #1E293B 0%, #0F172A 100%);
  border: 1px solid rgba(255, 255, 255, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #F8FAFC;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.18);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
:root[data-theme="light"] .brand-logo-box {
  background: #0F172A;
  border: 1px solid #0F172A;
  color: #FFFFFF;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.2);
}
.brand:hover .brand-logo-box {
  transform: scale(1.05);
  border-color: rgba(56, 189, 248, 0.6);
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.3);
}
.brand-logo-grid {
  display: grid;
  grid-template-columns: 8px 8px;
  grid-template-rows: 8px 8px;
  gap: 2.5px;
  width: 18.5px;
  height: 18.5px;
  align-items: center;
  justify-content: center;
}
.grid-sq {
  width: 8px;
  height: 8px;
  border-radius: 1.5px;
  box-sizing: border-box;
}
.grid-sq.sq-1 { background: currentColor; opacity: 0.95; }
.grid-sq.sq-2 { border: 1.8px solid currentColor; background: transparent; }
.grid-sq.sq-3 { border: 1.8px solid currentColor; background: transparent; }
.grid-sq.sq-4 { background: #38BDF8; }

.brand-title-wrap {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.brand-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.brand-name {
  font-family: var(--display, var(--sans));
  font-size: 15.5px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: var(--ink);
}
.brand-badge-fintech {
  font-family: var(--mono);
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.1em;
  padding: 1.5px 5px;
  border-radius: 4px;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38BDF8;
}
:root[data-theme="light"] .brand-badge-fintech {
  background: rgba(2, 132, 199, 0.08);
  border-color: rgba(2, 132, 199, 0.25);
  color: #0284C7;
}
.brand-sub {
  font-family: var(--mono);
  font-size: 8.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-3);
  font-weight: 600;
  margin-top: 2px;
}

.header-nav-tabs {
  display: flex;
  align-items: center;
  gap: 3px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.07);
  padding: 3px;
  border-radius: 9px;
}
:root[data-theme="light"] .header-nav-tabs {
  background: rgba(15, 23, 42, 0.04);
  border-color: rgba(15, 23, 42, 0.08);
}
.header-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 13px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 12.5px;
  color: var(--ink-2);
  text-decoration: none;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  height: 30px;
}
.header-tab:hover {
  color: var(--ink);
  background: rgba(255, 255, 255, 0.04);
}
:root[data-theme="light"] .header-tab:hover {
  background: rgba(15, 23, 42, 0.04);
}
.header-tab.on {
  background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
  color: #FFFFFF;
  border-color: rgba(255, 255, 255, 0.16);
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
:root[data-theme="light"] .header-tab.on {
  background: #FFFFFF;
  color: #0F172A;
  border-color: rgba(15, 23, 42, 0.12);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
.tab-glyph {
  width: 12px;
  height: 12px;
  display: inline-block;
  opacity: 0.7;
  vertical-align: middle;
}
.glyph-overview {
  border: 1.5px solid currentColor;
  border-radius: 2px;
  position: relative;
}
.glyph-overview::after {
  content: '';
  position: absolute;
  top: 1px;
  left: 1px;
  right: 1px;
  bottom: 1px;
  background: currentColor;
  opacity: 0.4;
}
.glyph-bots {
  box-shadow: 0 -3.5px 0 0.8px currentColor, 0 0 0 0.8px currentColor, 0 3.5px 0 0.8px currentColor;
  height: 1.5px;
  margin-top: 4px;
}
.glyph-analyze {
  border: 1.5px solid currentColor;
  border-radius: 50%;
  position: relative;
}
.glyph-analyze::after {
  content: '';
  position: absolute;
  width: 3.5px;
  height: 1.5px;
  background: currentColor;
  bottom: -2px;
  right: -2px;
  transform: rotate(45deg);
}

.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-header-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: #38BDF8;
  box-shadow: 0 1px 8px rgba(56, 189, 248, 0.12);
}
:root[data-theme="light"] .btn-header-cta {
  background: #0F172A;
  border-color: #0F172A;
  color: #FFFFFF;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.15);
}
.btn-header-cta:hover {
  transform: translateY(-1px);
  border-color: rgba(56, 189, 248, 0.6);
  box-shadow: 0 2px 12px rgba(56, 189, 248, 0.25);
}
.btn-cta-plus {
  font-size: 14px;
  line-height: 1;
  font-weight: 700;
}
.user-badge-capsule {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
:root[data-theme="light"] .user-badge-capsule {
  background: rgba(15, 23, 42, 0.035);
  border-color: rgba(15, 23, 42, 0.08);
}
.user-badge-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 8px #10B981;
  animation: pulseGlow 2s infinite ease-in-out;
}
@keyframes pulseGlow {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}
.user-badge-label {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--ink-2);
}
.theme-btn {
  height: 30px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.035);
  color: var(--ink-2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  font-size: 11.5px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}
:root[data-theme="light"] .theme-btn {
  background: rgba(15, 23, 42, 0.035);
  border-color: rgba(15, 23, 42, 0.08);
}
.theme-btn:hover {
  border-color: rgba(56, 189, 248, 0.4);
  color: var(--ink);
  transform: translateY(-1px);
}

/* Subnav Bar below Header */
.report-subnav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 14px 0;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-wrap: wrap;
  gap: 12px;
}
:root[data-theme="light"] .report-subnav-bar {
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.btn-subnav-back {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: var(--ink-2);
  font-size: 12.5px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s ease;
}
:root[data-theme="light"] .btn-subnav-back {
  background: rgba(15, 23, 42, 0.035);
  border-color: rgba(15, 23, 42, 0.08);
}
.btn-subnav-back:hover {
  background: rgba(56, 189, 248, 0.08);
  border-color: rgba(56, 189, 248, 0.4);
  color: #38BDF8;
  transform: translateX(-2px);
}
.btn-subnav-back .back-arrow {
  font-size: 14px;
  color: #38BDF8;
  transition: transform 0.2s ease;
}
.btn-subnav-back:hover .back-arrow {
  transform: translateX(-2px);
}
.subnav-crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-3);
  font-family: var(--mono);
}
.subnav-crumb .crumb-sep {
  color: rgba(255, 255, 255, 0.15);
}
:root[data-theme="light"] .subnav-crumb .crumb-sep {
  color: rgba(15, 23, 42, 0.2);
}
.subnav-crumb .crumb-link {
  color: var(--ink-2);
  text-decoration: none;
  transition: color 0.15s ease;
}
.subnav-crumb .crumb-link:hover {
  color: #38BDF8;
  text-decoration: underline;
}
.subnav-crumb .crumb-active {
  color: var(--ink);
  font-weight: 600;
}

/* Report Hero Card - Đồng bộ 100% với ngôn ngữ thiết kế NoraBT & OKX AI */
.report-hero-card {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius-lg, 16px) !important;
  padding: 30px 34px !important;
  margin: 16px 0 28px 0 !important;
  box-shadow: var(--card-shadow, 0 4px 20px -2px rgba(0, 0, 0, 0.3)) !important;
}
.report-hero-top {
  border-bottom: 1px solid var(--line) !important;
  padding-bottom: 22px !important;
  margin-bottom: 26px !important;
}
.report-hero-identity {
  width: 100% !important;
}
.report-hero-identity .crumb {
  font-size: 11.5px !important;
  font-weight: 600 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  color: var(--ink-3) !important;
  font-family: var(--mono) !important;
  margin-bottom: 8px !important;
}
.head-title {
  font-size: 32px !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
  color: var(--ink) !important;
  margin: 0 0 12px 0 !important;
  line-height: 1.2 !important;
  font-family: var(--display, var(--sans)) !important;
}
.report-hero-meta {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  flex-wrap: wrap !important;
}
.bot-code-pill {
  font-size: 12px !important;
  color: var(--ink-2) !important;
  font-family: var(--mono) !important;
  background: var(--panel-2) !important;
  padding: 4px 12px !important;
  border-radius: var(--radius-xs, 4px) !important;
  border: 1px solid var(--line) !important;
}
.venue-symbol-badge {
  font-size: 12px !important;
  font-weight: 600 !important;
  font-family: var(--mono) !important;
  background: rgba(59, 130, 246, 0.12) !important;
  color: var(--s1, #3b82f6) !important;
  padding: 4px 12px !important;
  border-radius: var(--radius-xs, 4px) !important;
  border: 1px solid rgba(59, 130, 246, 0.25) !important;
}
.verdict-badge {
  font-family: var(--mono) !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  padding: 5px 14px !important;
  border-radius: var(--radius-xs, 4px) !important;
  color: #ffffff !important;
  background: var(--badge-color, #6b7280) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25) !important;
}
.report-hero-scores {
  display: grid !important;
  grid-template-columns: repeat(3, 1fr) !important;
  gap: 20px !important;
  margin-bottom: 26px !important;
  background: transparent !important;
  border: none !important;
}
@media (max-width: 800px) {
  .report-hero-scores {
    grid-template-columns: 1fr !important;
  }
}
.report-hero-scores .stat-tile-hero {
  background: var(--panel-2) !important;
  border: 1px solid var(--line) !important;
  border-top: 3px solid var(--tile-accent, var(--line)) !important;
  border-radius: var(--radius-md, 12px) !important;
  padding: 22px 26px !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  box-shadow: var(--card-shadow, 0 4px 16px -2px rgba(0, 0, 0, 0.25)) !important;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.report-hero-scores .stat-tile-hero:hover {
  border-color: var(--tile-accent, var(--line)) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px -2px rgba(0, 0, 0, 0.4), 0 0 15px rgba(59, 130, 246, 0.15) !important;
}
.report-hero-scores .stat-tile-hero .stat-value {
  font-size: 42px !important;
  font-weight: 800 !important;
  line-height: 1.15 !important;
  font-family: var(--mono) !important;
  font-variant-numeric: tabular-nums !important;
  letter-spacing: -0.02em !important;
  color: var(--tile-accent, var(--ink)) !important;
}
.report-hero-scores .stat-tile-hero .stat-label {
  font-family: var(--mono) !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  color: var(--ink-2) !important;
  margin-top: 8px !important;
}

/* Header notices container */
.header-notices {
  display: flex !important;
  flex-direction: column !important;
  gap: 22px !important;
  margin-top: 26px !important;
}

/* Veto notice */
.notice-danger {
  background: rgba(244, 63, 94, 0.08) !important;
  border: 1px solid rgba(244, 63, 94, 0.28) !important;
  border-left: 4px solid var(--down, #F43F5E) !important;
  border-radius: var(--radius-md, 12px) !important;
  padding: 18px 24px !important;
  color: var(--ink) !important;
  font-size: 14px !important;
  line-height: 1.65 !important;
  margin: 0 !important;
  box-shadow: var(--card-shadow, 0 4px 16px -2px rgba(0, 0, 0, 0.2)) !important;
}
.notice-danger strong {
  color: var(--down, #F43F5E) !important;
  font-weight: 700 !important;
}
:root[data-theme="light"] .notice-danger {
  background: #FFF1F2 !important;
  border: 1px solid #FDA4AF !important;
  border-left: 5px solid #E11D48 !important;
  color: #4C0519 !important;
  font-size: 14.5px !important;
  line-height: 1.65 !important;
  font-weight: 500 !important;
}
:root[data-theme="light"] .notice-danger strong {
  color: #881337 !important;
  font-weight: 800 !important;
}
:root[data-theme="light"] .notice-warning {
  background: #FFFBEB !important;
  border: 1px solid #FDE68A !important;
  border-left: 4px solid #D97706 !important;
  color: #78350F !important;
}
:root[data-theme="light"] .notice-warning strong {
  color: #B45309 !important;
}

/* Methodology Framework (Cơ sở phương pháp luận định lượng) */
.verdict-basis {
  background: var(--panel-2) !important;
  border: 1px solid var(--line) !important;
  border-left: 3px solid var(--s1, #3b82f6) !important;
  border-radius: var(--radius-md, 12px) !important;
  padding: 12px 18px !important;
  margin: 0 !important;
  display: block !important;
  box-shadow: var(--card-shadow, 0 4px 20px -2px rgba(0, 0, 0, 0.25)) !important;
  -webkit-line-clamp: unset !important;
  overflow: visible !important;
  max-width: none !important;
  transition: all 0.25s ease !important;
}
.verdict-basis:hover {
  border-color: rgba(59, 130, 246, 0.4) !important;
}
.verdict-basis .basis-header {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  flex-wrap: wrap !important;
  gap: 12px !important;
  cursor: pointer !important;
  user-select: none !important;
}
.collapsible-basis .basis-collapsible-body {
  display: none !important;
}
.collapsible-basis.expanded .basis-collapsible-body {
  display: block !important;
  margin-top: 18px !important;
}
.collapsible-basis.expanded .basis-header {
  margin-bottom: 16px !important;
  padding-bottom: 14px !important;
  border-bottom: 1px solid var(--line) !important;
}
.basis-toggle-action {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
}
.basis-toggle-pill {
  font-family: var(--mono) !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 0.04em !important;
  background: rgba(59, 130, 246, 0.1) !important;
  color: var(--s1, #3b82f6) !important;
  border: 1px solid rgba(59, 130, 246, 0.25) !important;
  padding: 4px 10px !important;
  border-radius: 6px !important;
  transition: all 0.2s ease !important;
  white-space: nowrap !important;
}
.verdict-basis:hover .basis-toggle-pill {
  background: var(--s1, #3b82f6) !important;
  color: #ffffff !important;
}
.collapsible-basis.expanded .basis-toggle-pill {
  background: var(--panel) !important;
  color: var(--ink-2) !important;
  border-color: var(--line) !important;
}
.verdict-basis .basis-title-group {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
}
.verdict-basis .basis-icon-badge {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 36px !important;
  height: 36px !important;
  background: rgba(59, 130, 246, 0.12) !important;
  color: var(--s1, #3b82f6) !important;
  border: 1px solid rgba(59, 130, 246, 0.25) !important;
  border-radius: var(--radius-sm, 8px) !important;
  font-size: 18px !important;
  flex-shrink: 0 !important;
}
.verdict-basis .basis-main-title {
  font-family: var(--mono) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  color: var(--ink) !important;
  line-height: 1.3 !important;
}
.verdict-basis .basis-subtitle {
  font-size: 12px !important;
  color: var(--ink-3) !important;
  margin-top: 3px !important;
}
.verdict-basis .basis-academic-tag {
  font-family: var(--mono) !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  background: var(--panel) !important;
  color: var(--s1, #3b82f6) !important;
  border: 1px solid var(--line) !important;
  padding: 4px 10px !important;
  border-radius: var(--radius-xs, 4px) !important;
}
.verdict-basis .basis-pillars-grid {
  display: grid !important;
  grid-template-columns: repeat(4, 1fr) !important;
  gap: 16px !important;
  margin-bottom: 20px !important;
}
@media (max-width: 1024px) {
  .verdict-basis .basis-pillars-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
@media (max-width: 640px) {
  .verdict-basis .basis-pillars-grid {
    grid-template-columns: 1fr !important;
  }
}
.basis-pillar-card {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius-md, 12px) !important;
  padding: 16px 16px !important;
  display: flex !important;
  flex-direction: column !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
.basis-pillar-card:hover {
  border-color: rgba(59, 130, 246, 0.4) !important;
  background: rgba(59, 130, 246, 0.04) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3), 0 0 12px rgba(59, 130, 246, 0.12) !important;
}
.basis-pillar-card .pillar-top {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 6px !important;
  margin-bottom: 10px !important;
}
.basis-pillar-card .pillar-badge {
  font-family: var(--mono) !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  padding: 2px 7px !important;
  border-radius: var(--radius-xs, 4px) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}
.pillar-blue {
  background: rgba(57, 135, 229, 0.15) !important;
  color: var(--s1, #3987e5) !important;
}
.pillar-amber {
  background: rgba(245, 158, 11, 0.15) !important;
  color: #f59e0b !important;
}
.pillar-purple {
  background: rgba(139, 92, 246, 0.15) !important;
  color: #a78bfa !important;
}
.pillar-green {
  background: rgba(16, 185, 129, 0.15) !important;
  color: #10b981 !important;
}
.basis-pillar-card .pillar-tag {
  font-size: 10.5px !important;
  color: var(--ink-3) !important;
}
.basis-pillar-card .pillar-name {
  font-size: 13.5px !important;
  font-weight: 700 !important;
  color: var(--ink) !important;
  margin-bottom: 8px !important;
}
.basis-pillar-card .pillar-desc {
  font-size: 12px !important;
  line-height: 1.6 !important;
  color: var(--ink-2) !important;
  flex-grow: 1 !important;
}
.basis-verbatim-card {
  background: var(--panel) !important;
  border: 1px dashed var(--line) !important;
  border-radius: 3px !important;
  padding: 14px 18px !important;
}
.basis-verbatim-card .verbatim-header {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  margin-bottom: 8px !important;
}
.basis-verbatim-card .verbatim-dot {
  width: 6px !important;
  height: 6px !important;
  background: var(--s1, #3987e5) !important;
  border-radius: 50% !important;
}
.basis-verbatim-card .verbatim-label {
  font-family: var(--mono) !important;
  font-size: 10.5px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: var(--ink-3) !important;
}
.verdict-basis .basis-text {
  font-size: 12.5px !important;
  line-height: 1.7 !important;
  color: var(--ink-2) !important;
}

/* AI Quant Narrative Card */
.narrative-card {
  background: var(--panel-2) !important;
  border: 1px solid var(--line) !important;
}
/* ==========================================================================
   Conclusion & Narrative Unified Styles (System Consistent)
   ========================================================================== */
.conclusion-body-wrap,
.narrative-body-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Verdict Banner */
.conclusion-verdict-box {
  border-radius: var(--radius-md, 12px);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-left: 4px solid var(--amber, #f59e0b);
  background: var(--panel-2, #161f32);
  border-top: 1px solid var(--line);
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
:root[data-theme="light"] .conclusion-verdict-box {
  background: #ffffff !important;
  border-top-color: #e2e8f0 !important;
  border-right-color: #e2e8f0 !important;
  border-bottom-color: #e2e8f0 !important;
}
.conclusion-verdict-box.tone-danger {
  border-left-color: #e11d48 !important;
}
.conclusion-verdict-box.tone-warning {
  border-left-color: #f59e0b !important;
}
.conclusion-verdict-box.tone-success {
  border-left-color: #10b981 !important;
}

.verdict-header-line {
  display: flex;
  align-items: center;
  gap: 10px;
}
.verdict-chip {
  font-family: var(--mono);
  font-size: 13.5px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.tone-danger .verdict-chip {
  color: #f43f5e;
}
:root[data-theme="light"] .tone-danger .verdict-chip {
  color: #e11d48;
}
.tone-warning .verdict-chip {
  color: #f59e0b;
}
:root[data-theme="light"] .tone-warning .verdict-chip {
  color: #d97706;
}
.tone-success .verdict-chip {
  color: #10b981;
}

.verdict-detail {
  margin: 0;
  font-size: 14.5px;
  line-height: 1.65;
  color: var(--ink);
}

/* Overview block inside conclusion */
.conclusion-overview-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(148, 163, 184, 0.05);
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--line);
}
:root[data-theme="light"] .conclusion-overview-block {
  background: #f8fafc !important;
  border-color: #e2e8f0 !important;
}
.conclusion-identity-row {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--ink);
}
.conclusion-metric-row {
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.conclusion-summary-text {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
}

/* Sub-sections & Takeaways */
.conclusion-section-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.conclusion-sub-title,
.narrative-sub-title {
  font-size: 13px !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  color: var(--ink, #f1f5f9) !important;
}
:root[data-theme="light"] .conclusion-sub-title,
:root[data-theme="light"] .narrative-sub-title {
  color: #0f172a !important;
}

/* Verdict Headline Value Badges (hover pill with soft warning colors) */
.verdict-val-badge {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 4px;
  font-weight: 800;
  letter-spacing: 0.04em;
  transition: all 0.18s ease;
  cursor: default;
}
.verdict-val-badge.badge-high,
.verdict-val-badge.badge-danger {
  color: #f43f5e;
}
.verdict-val-badge.badge-high:hover,
.verdict-val-badge.badge-danger:hover {
  background: rgba(244, 63, 94, 0.15);
  box-shadow: 0 0 0 1px rgba(244, 63, 94, 0.35);
}
.verdict-val-badge.badge-weak,
.verdict-val-badge.badge-elevated,
.verdict-val-badge.badge-warning {
  color: #f59e0b;
}
.verdict-val-badge.badge-weak:hover,
.verdict-val-badge.badge-elevated:hover,
.verdict-val-badge.badge-warning:hover {
  background: rgba(245, 158, 11, 0.15);
  box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.35);
}
.verdict-val-badge.badge-low,
.verdict-val-badge.badge-good,
.verdict-val-badge.badge-safe {
  color: #10b981;
}
.verdict-val-badge.badge-low:hover,
.verdict-val-badge.badge-good:hover,
.verdict-val-badge.badge-safe:hover {
  background: rgba(16, 185, 129, 0.15);
  box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.35);
}
.verdict-val-badge.badge-acceptable {
  color: #38bdf8;
}
.verdict-val-badge.badge-acceptable:hover {
  background: rgba(56, 189, 248, 0.15);
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.35);
}
:root[data-theme="light"] .verdict-val-badge.badge-high,
:root[data-theme="light"] .verdict-val-badge.badge-danger {
  color: #e11d48;
}
:root[data-theme="light"] .verdict-val-badge.badge-high:hover,
:root[data-theme="light"] .verdict-val-badge.badge-danger:hover {
  background: rgba(225, 29, 72, 0.12);
  box-shadow: 0 0 0 1px rgba(225, 29, 72, 0.3);
}
:root[data-theme="light"] .verdict-val-badge.badge-weak,
:root[data-theme="light"] .verdict-val-badge.badge-elevated,
:root[data-theme="light"] .verdict-val-badge.badge-warning {
  color: #d97706;
}
:root[data-theme="light"] .verdict-val-badge.badge-weak:hover,
:root[data-theme="light"] .verdict-val-badge.badge-elevated:hover,
:root[data-theme="light"] .verdict-val-badge.badge-warning:hover {
  background: rgba(217, 119, 6, 0.12);
  box-shadow: 0 0 0 1px rgba(217, 119, 6, 0.3);
}
:root[data-theme="light"] .verdict-val-badge.badge-low,
:root[data-theme="light"] .verdict-val-badge.badge-good,
:root[data-theme="light"] .verdict-val-badge.badge-safe {
  color: #15803d;
}
:root[data-theme="light"] .verdict-val-badge.badge-low:hover,
:root[data-theme="light"] .verdict-val-badge.badge-good:hover,
:root[data-theme="light"] .verdict-val-badge.badge-safe:hover {
  background: rgba(21, 128, 61, 0.12);
  box-shadow: 0 0 0 1px rgba(21, 128, 61, 0.3);
}

/* QUANTITATIVE EVIDENCE — top scorecard chips */
.qe-scorecard {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}
.qe-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 9px 16px 8px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  min-width: 106px;
}
:root[data-theme="light"] .qe-chip {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.qe-chip-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted, #94a3b8);
}
:root[data-theme="light"] .qe-chip-label {
  color: var(--ink-2, #64748b);
}
.qe-chip-value {
  font-size: 18px;
  font-weight: 700;
  font-family: var(--mono, 'SFMono-Regular', monospace);
  letter-spacing: -0.01em;
}
/* color variants */
.qe-chip-good .qe-chip-value  { color: var(--up, #10b981); }
.qe-chip-good                  { border-color: rgba(16,185,129,0.25); }
:root[data-theme="light"] .qe-chip-good { border-color: rgba(16,185,129,0.35); background: #f0fdf4; }
.qe-chip-warn .qe-chip-value  { color: var(--amber, #f59e0b); }
.qe-chip-warn                  { border-color: rgba(245,158,11,0.25); }
:root[data-theme="light"] .qe-chip-warn { border-color: rgba(245,158,11,0.35); background: #fffbeb; }
.qe-chip-bad  .qe-chip-value  { color: var(--down, #ef4444); }
.qe-chip-bad                   { border-color: rgba(239,68,68,0.25); }
:root[data-theme="light"] .qe-chip-bad  { border-color: rgba(239,68,68,0.35); background: #fff1f2; }

/* Narrative summary paragraph inside QUANTITATIVE EVIDENCE */
.qe-narrative {
  font-size: 13px;
  line-height: 1.65;
  color: var(--ink-1, #e2e8f0);
  margin: 10px 0 12px;
  padding: 10px 14px;
  border-left: 3px solid rgba(59, 130, 246, 0.5);
  border-radius: 0 6px 6px 0;
  background: rgba(59, 130, 246, 0.04);
}
:root[data-theme="light"] .qe-narrative {
  color: var(--ink-1, #1e293b);
  border-left-color: #3b82f6;
  background: #f0f7ff;
}

/* Revisit condition banner inside QUANTITATIVE EVIDENCE */
.qe-revisit-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0 14px;
  padding: 8px 14px;
  background: rgba(234, 179, 8, 0.08);
  border: 1px solid rgba(234, 179, 8, 0.25);
  border-radius: 6px;
  font-size: 12.5px;
  line-height: 1.5;
}
.qe-revisit-tag {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(234, 179, 8, 0.2);
  color: #fbbf24;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.qe-revisit-text {
  color: var(--ink-1, #e2e8f0);
  font-weight: 500;
}
:root[data-theme="light"] .qe-revisit-banner {
  background: #fefce8;
  border-color: #fde047;
}
:root[data-theme="light"] .qe-revisit-tag {
  background: #fef08a;
  color: #854d0e;
}
:root[data-theme="light"] .qe-revisit-text {
  color: #713f12;
}

/* QUANT TERMINAL / AUDIT LOG TEXT VIEW */
.quant-audit-terminal {
  font-family: var(--mono, "JetBrains Mono", monospace);
  font-size: 13px;
  line-height: 1.6;
  margin: 8px 0 14px 0;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 10px 0;
}
:root[data-theme="light"] .quant-audit-terminal {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.quant-terminal-divider {
  height: 1px;
  background: linear-gradient(90deg, rgba(255,255,255,0.14), rgba(255,255,255,0.03));
  margin: 4px 14px;
}
:root[data-theme="light"] .quant-terminal-divider {
  background: #e2e8f0;
}
.quant-audit-rows {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.quant-audit-row {
  display: grid;
  grid-template-columns: 190px 1fr;
  align-items: start;
  column-gap: 20px;
  padding: 8px 16px;
  border-left: 3px solid transparent;
  transition: all 0.15s ease;
  cursor: default;
}
.quant-audit-row:hover {
  background: rgba(255, 255, 255, 0.04);
  border-left-color: #f59e0b;
}
:root[data-theme="light"] .quant-audit-row:hover {
  background: rgba(241, 245, 249, 0.85);
  border-left-color: #d97706;
}
.quant-audit-tag {
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.03em;
  white-space: nowrap;
  user-select: none;
  transition: color 0.15s ease;
}
.quant-audit-row:hover .quant-audit-tag {
  color: #f1f5f9;
}
:root[data-theme="light"] .quant-audit-tag {
  color: #64748b;
}
:root[data-theme="light"] .quant-audit-row:hover .quant-audit-tag {
  color: #0f172a;
}
.quant-audit-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.quant-audit-main {
  color: #cbd5e1;
  word-break: break-word;
}
:root[data-theme="light"] .quant-audit-main {
  color: #334155;
}
.quant-audit-consequence {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding-left: 2px;
}
.quant-consequence-arrow {
  color: #f59e0b;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}
.quant-consequence-text {
  font-weight: 500;
  color: #fde68a;
}
:root[data-theme="light"] .quant-consequence-arrow {
  color: #d97706;
}
:root[data-theme="light"] .quant-consequence-text {
  color: #b45309;
}
.quant-num {
  font-weight: 700;
  color: #f8fafc;
}
:root[data-theme="light"] .quant-num {
  color: #0f172a;
}
.quant-num.quant-num-neg {
  color: #f87171 !important;
}
:root[data-theme="light"] .quant-num.quant-num-neg {
  color: #dc2626 !important;
}
.quant-num.quant-num-warn {
  color: #fbbf24 !important;
}
:root[data-theme="light"] .quant-num.quant-num-warn {
  color: #d97706 !important;
}
@media (max-width: 768px) {
  .quant-audit-row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
.conclusion-extra-line {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink);
}

/* Limitations Accordion */
.conclusion-limitation-accordion {
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--line);
  background: var(--panel-2);
  overflow: hidden;
}
:root[data-theme="light"] .conclusion-limitation-accordion {
  background: #f8fafc !important;
  border-color: #e2e8f0 !important;
}
.limitation-accordion-summary {
  cursor: pointer;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
  font-size: 13.5px;
}
.limitation-accordion-summary strong {
  color: var(--ink);
}
.limitation-toggle-hint {
  font-size: 12px;
  color: var(--ink-3);
}
.limitation-toggle-checkbox {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.limitation-accordion-body {
  display: none;
  padding: 4px 16px 16px 16px;
  border-top: 1px solid var(--line);
}
.limitation-toggle-checkbox:checked ~ .limitation-accordion-body {
  display: block;
}

/* Narrative Unified Box */
.narrative-meta-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}
.narrative-meta-bar .meta-desc {
  font-size: 12.5px;
  color: var(--ink-2);
}
.narrative-prose-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.narrative-paragraph {
  margin: 0;
  font-size: 14.5px;
  line-height: 1.8;
  color: var(--ink);
  font-family: var(--sans);
}
:root[data-theme="light"] .narrative-paragraph {
  color: #0f172a !important;
}
:root[data-theme="light"] .verdict-detail {
  color: #0f172a !important;
}
:root[data-theme="light"] .conclusion-identity-row {
  color: #0f172a !important;
}
:root[data-theme="light"] .conclusion-metric-row {
  color: #0f172a !important;
}

/* Hover on SVG bar label with pointer */
.bar-chart text.bar-label[style*="cursor:pointer"]:hover {
  fill: var(--s1, #3b82f6) !important;
  font-weight: 700;
}

/* Dimensions table & stars */
#diem-chieu .table-scroll {
  overflow: visible !important;
  max-height: none !important;
}
.dim-score-badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.dim-score-badge.unmeasured {
  background: rgba(156, 163, 175, 0.15) !important;
  color: #9CA3AF !important;
  border: 1px solid rgba(156, 163, 175, 0.3) !important;
}
.dim-meta-tag {
  font-size: 12px;
  color: var(--muted, #64748B);
  font-weight: 500;
}

/* Narrative Structured Styles */
.narrative-overview-box {
  margin-top: 14px;
}
.narrative-subheading {
  font-size: 12.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--amber, #F59E0B);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.narrative-keypoints-box {
  margin-top: 16px;
}
.narrative-keypoint-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.narrative-keypoint-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.55;
}
.narrative-pending-notice {
  font-style: italic;
  font-size: 14px;
}

/* ==========================================================================
   Theme: DARK MODE (Default when dark or data-theme="dark")
   ========================================================================== */
:root[data-theme="dark"] .conclusion-overview-card,
:root:not([data-theme="light"]) .conclusion-overview-card {
  background: var(--panel, #111726);
  border: 1px solid var(--line, #1E293B);
}
:root[data-theme="dark"] .conclusion-overview-card .conclusion-eyebrow,
:root:not([data-theme="light"]) .conclusion-overview-card .conclusion-eyebrow {
  color: var(--ink-3, #94A3B8);
}
:root[data-theme="dark"] .overview-bot-title,
:root:not([data-theme="light"]) .overview-bot-title {
  color: #F8FAFC !important;
}
:root[data-theme="dark"] .overview-meta-chip,
:root:not([data-theme="light"]) .overview-meta-chip {
  color: #CBD5E1 !important;
}
:root[data-theme="dark"] .overview-scores-row,
:root:not([data-theme="light"]) .overview-scores-row {
  color: #F1F5F9 !important;
}
:root[data-theme="dark"] .overview-line,
:root:not([data-theme="light"]) .overview-line {
  color: var(--ink, #FFFFFF);
}

:root[data-theme="dark"] .conclusion-verdict-block,
:root:not([data-theme="light"]) .conclusion-verdict-block {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-left: 4px solid var(--amber, #F59E0B);
}
:root[data-theme="dark"] .conclusion-verdict-block .conclusion-eyebrow,
:root:not([data-theme="light"]) .conclusion-verdict-block .conclusion-eyebrow {
  color: #FBBF24;
}
:root[data-theme="dark"] .verdict-headline,
:root:not([data-theme="light"]) .verdict-headline {
  color: #FDE68A;
}
:root[data-theme="dark"] .verdict-desc,
:root[data-theme="dark"] .conclusion-verdict-block .conclusion-line,
:root:not([data-theme="light"]) .verdict-desc,
:root:not([data-theme="light"]) .conclusion-verdict-block .conclusion-line {
  color: var(--ink, #F8FAFC);
}

:root[data-theme="dark"] .conclusion-why,
:root:not([data-theme="light"]) .conclusion-why {
  background: rgba(244, 63, 94, 0.08);
  border: 1px solid rgba(244, 63, 94, 0.25);
  border-left: 4px solid var(--down, #F43F5E);
}
:root[data-theme="dark"] .conclusion-why .conclusion-eyebrow,
:root:not([data-theme="light"]) .conclusion-why .conclusion-eyebrow {
  color: #FB7185;
}
:root[data-theme="dark"] .conclusion-why .bullet-item,
:root:not([data-theme="light"]) .conclusion-why .bullet-item {
  background: var(--panel, #111726);
  border: 1px solid rgba(244, 63, 94, 0.2);
}
:root[data-theme="dark"] .conclusion-why .bullet-icon,
:root:not([data-theme="light"]) .conclusion-why .bullet-icon {
  color: var(--down, #F43F5E);
}
:root[data-theme="dark"] .conclusion-why .bullet-text,
:root[data-theme="dark"] .conclusion-why .conclusion-line,
:root:not([data-theme="light"]) .conclusion-why .bullet-text,
:root:not([data-theme="light"]) .conclusion-why .conclusion-line {
  color: var(--ink, #F8FAFC);
}

:root[data-theme="dark"] .conclusion-proof,
:root:not([data-theme="light"]) .conclusion-proof {
  background: var(--panel, #111726);
  border: 1px solid var(--line, #1E293B);
  border-left: 4px solid var(--info, #38BDF8);
}
:root[data-theme="dark"] .conclusion-proof .conclusion-eyebrow,
:root:not([data-theme="light"]) .conclusion-proof .conclusion-eyebrow {
  color: var(--info, #38BDF8);
}
:root[data-theme="dark"] .conclusion-proof-list li.proof-card,
:root:not([data-theme="light"]) .conclusion-proof-list li.proof-card {
  background: var(--panel, #111726);
  border: 1px solid var(--line, #1E293B);
  border-left: 3px solid var(--info, #38BDF8);
  color: var(--ink, #F8FAFC);
}
:root[data-theme="dark"] .proof-dot,
:root:not([data-theme="light"]) .proof-dot {
  color: var(--info, #38BDF8);
}

:root[data-theme="dark"] .conclusion-warning-block,
:root:not([data-theme="light"]) .conclusion-warning-block {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-left: 4px solid var(--amber, #F59E0B);
}
:root[data-theme="dark"] .warning-eyebrow,
:root:not([data-theme="light"]) .warning-eyebrow {
  color: #FBBF24;
}
:root[data-theme="dark"] .badge-warning,
:root:not([data-theme="light"]) .badge-warning {
  background: rgba(245, 158, 11, 0.2);
  color: #FBBF24;
  border: 1px solid rgba(245, 158, 11, 0.35);
}
:root[data-theme="dark"] .warning-bullet-item,
:root:not([data-theme="light"]) .warning-bullet-item {
  background: var(--panel, #111726);
  border: 1px solid rgba(245, 158, 11, 0.2);
}
:root[data-theme="dark"] .warning-bullet-text,
:root:not([data-theme="light"]) .warning-bullet-text {
  color: var(--ink, #F8FAFC);
}

:root[data-theme="dark"] .conclusion-limitation-accordion,
:root:not([data-theme="light"]) .conclusion-limitation-accordion {
  background: rgba(56, 189, 248, 0.06);
  border: 1px solid rgba(56, 189, 248, 0.2);
}
:root[data-theme="dark"] .limitation-title,
:root:not([data-theme="light"]) .limitation-title {
  color: #38BDF8;
}
:root[data-theme="dark"] .limitation-toggle-hint,
:root:not([data-theme="light"]) .limitation-toggle-hint {
  color: #94A3B8;
}
:root[data-theme="dark"] .conclusion-limitation-accordion .badge-info,
:root:not([data-theme="light"]) .conclusion-limitation-accordion .badge-info {
  background: rgba(56, 189, 248, 0.15);
  color: #38BDF8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}
:root[data-theme="dark"] .limitation-bullet-item,
:root:not([data-theme="light"]) .limitation-bullet-item {
  background: var(--panel, #111726);
  border: 1px solid rgba(56, 189, 248, 0.18);
}
:root[data-theme="dark"] .limitation-bullet-dot,
:root:not([data-theme="light"]) .limitation-bullet-dot {
  color: #38BDF8;
}
:root[data-theme="dark"] .limitation-bullet-text,
:root:not([data-theme="light"]) .limitation-bullet-text {
  color: var(--ink, #F8FAFC);
}

:root[data-theme="dark"] .conclusion-summary-box,
:root:not([data-theme="light"]) .conclusion-summary-box {
  background: var(--panel-2, #161F32);
  border: 1px solid var(--line, #1E293B);
}
:root[data-theme="dark"] .conclusion-summary-box .conclusion-line,
:root:not([data-theme="light"]) .conclusion-summary-box .conclusion-line {
  color: var(--ink, #F8FAFC);
}

:root[data-theme="dark"] .narrative-keypoint-item,
:root:not([data-theme="light"]) .narrative-keypoint-item {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: #E2E8F0 !important;
}
:root[data-theme="dark"] .narrative-pending-notice,
:root:not([data-theme="light"]) .narrative-pending-notice {
  color: #94A3B8 !important;
}

/* ==========================================================================
   Theme: LIGHT MODE (:root[data-theme="light"])
   CRITICAL CONTRAST: Every text element MUST be dark (#0F172A / #1E293B)
   ========================================================================== */
:root[data-theme="light"] .conclusion-overview-card {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
}
:root[data-theme="light"] .conclusion-overview-card .conclusion-eyebrow {
  color: #475569 !important;
}
:root[data-theme="light"] .overview-bot-title {
  color: #0F172A !important;
}
:root[data-theme="light"] .overview-meta-chip {
  color: #334155 !important;
}
:root[data-theme="light"] .overview-scores-row {
  color: #0F172A !important;
}
:root[data-theme="light"] .overview-line {
  color: #0F172A !important;
}

:root[data-theme="light"] .conclusion-verdict-block {
  background: #FFFBEB !important;
  border: 1px solid #FDE68A !important;
  border-left: 4px solid #D97706 !important;
}
:root[data-theme="light"] .conclusion-verdict-block .conclusion-eyebrow {
  color: #B45309 !important;
}
:root[data-theme="light"] .verdict-headline {
  color: #78350F !important;
}
:root[data-theme="light"] .verdict-desc,
:root[data-theme="light"] .conclusion-verdict-block .conclusion-line {
  color: #1E293B !important;
}

:root[data-theme="light"] .conclusion-why {
  background: #FFF1F2 !important;
  border: 1px solid #FECDD3 !important;
  border-left: 4px solid #E11D48 !important;
}
:root[data-theme="light"] .conclusion-why .conclusion-eyebrow {
  color: #BE123C !important;
}
:root[data-theme="light"] .conclusion-why .bullet-item {
  background: #FFFFFF !important;
  border: 1px solid #FFE4E6 !important;
}
:root[data-theme="light"] .conclusion-why .bullet-icon {
  color: #E11D48 !important;
}
:root[data-theme="light"] .conclusion-why .bullet-text,
:root[data-theme="light"] .conclusion-why .conclusion-line {
  color: #1E293B !important;
}

:root[data-theme="light"] .conclusion-proof {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
  border-left: 4px solid #2563EB !important;
}
:root[data-theme="light"] .conclusion-proof .conclusion-eyebrow {
  color: #1D4ED8 !important;
}
:root[data-theme="light"] .conclusion-proof-list li.proof-card {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-left: 3px solid #2563EB !important;
  color: #1E293B !important;
}
:root[data-theme="light"] .proof-dot {
  color: #2563EB !important;
}

:root[data-theme="light"] .conclusion-warning-block {
  background: #FFFBEB !important;
  border: 1px solid #FDE68A !important;
  border-left: 4px solid #D97706 !important;
}
:root[data-theme="light"] .warning-eyebrow {
  color: #B45309 !important;
}
:root[data-theme="light"] .badge-warning {
  background: #FEF3C7 !important;
  color: #B45309 !important;
  border: 1px solid #FDE68A !important;
}
:root[data-theme="light"] .warning-bullet-item {
  background: #FFFFFF !important;
  border: 1px solid #FEF3C7 !important;
}
:root[data-theme="light"] .warning-bullet-text {
  color: #1E293B !important;
}

:root[data-theme="light"] .conclusion-limitation-accordion {
  background: #F0F9FF !important;
  border: 1px solid #BAE6FD !important;
}
:root[data-theme="light"] .limitation-title {
  color: #0369A1 !important;
}
:root[data-theme="light"] .limitation-toggle-hint {
  color: #0284C7 !important;
}
:root[data-theme="light"] .conclusion-limitation-accordion .badge-info {
  background: #E0F2FE !important;
  color: #0369A1 !important;
  border: 1px solid #BAE6FD !important;
}
:root[data-theme="light"] .limitation-bullet-item {
  background: #FFFFFF !important;
  border: 1px solid #E0F2FE !important;
}
:root[data-theme="light"] .limitation-bullet-dot {
  color: #0284C7 !important;
}
:root[data-theme="light"] .limitation-bullet-text {
  color: #1E293B !important;
}

:root[data-theme="light"] .conclusion-summary-box {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
}
:root[data-theme="light"] .conclusion-summary-box .conclusion-line {
  color: #1E293B !important;
}

:root[data-theme="light"] .narrative-keypoint-item {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
  color: #1E293B !important;
}
:root[data-theme="light"] .narrative-pending-notice {
  color: #475569 !important;
}

/* Formula Tooltips & Asterisk */
#so-lieu .table-scroll,
#suy-luan .table-scroll {
  overflow: visible !important;
  max-height: none !important;
}
table tr:hover {
  position: relative;
  z-index: 20;
}
/* Formula Modal & Dialog */
.formula-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  z-index: 99999;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.formula-modal-backdrop.is-open {
  display: flex;
}
.formula-modal-card {
  background: var(--panel, #111726);
  border: 1px solid var(--line, #1E293B);
  border-radius: var(--radius, 12px);
  width: 100%;
  max-width: 520px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: modalFadeIn 0.18s ease-out;
}
@keyframes modalFadeIn {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
:root[data-theme="light"] .formula-modal-card {
  background: #ffffff !important;
  border-color: #cbd5e1 !important;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.15) !important;
}
.formula-modal-header {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--line, #1E293B);
}
:root[data-theme="light"] .formula-modal-header {
  border-bottom-color: #e2e8f0 !important;
}
.formula-modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink, #F8FAFC);
}
:root[data-theme="light"] .formula-modal-header h3 {
  color: #0F172A !important;
}
.formula-modal-close {
  background: transparent;
  border: none;
  font-size: 24px;
  line-height: 1;
  color: var(--ink-2, #94A3B8);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.formula-modal-close:hover {
  color: var(--ink, #FFFFFF);
  background: rgba(255, 255, 255, 0.08);
}
:root[data-theme="light"] .formula-modal-close:hover {
  color: #0F172A !important;
  background: #f1f5f9 !important;
}
.formula-modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.formula-field label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-2, #94A3B8);
  display: block;
  margin-bottom: 6px;
}
:root[data-theme="light"] .formula-field label {
  color: #475569 !important;
}
.formula-field pre {
  margin: 0;
  padding: 12px 14px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--line, #1E293B);
  color: var(--s1, #38BDF8);
  font-family: var(--mono);
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}
:root[data-theme="light"] .formula-field pre {
  background: #f8fafc !important;
  border-color: #cbd5e1 !important;
  color: #0284c7 !important;
}
.formula-field p {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink, #F8FAFC);
}
:root[data-theme="light"] .formula-field p {
  color: #1e293b !important;
}

/* Formula Star Button - clean naked asterisk without circular wrapper or circular hover layout */
.formula-star-btn {
  display: inline-block !important;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  outline: none !important;
  color: var(--accent, #38BDF8) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  cursor: pointer !important;
  line-height: 1 !important;
  padding: 0 1px !important;
  margin: 0 0 0 3px !important;
  width: auto !important;
  height: auto !important;
  min-width: 0 !important;
  min-height: 0 !important;
  vertical-align: baseline !important;
  transition: color 0.15s ease !important;
  transform: none !important;
}
.formula-star-btn:hover,
.formula-star-btn:focus-visible {
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  outline: none !important;
  transform: none !important;
  color: #7dd3fc !important;
  text-decoration: underline !important;
}
:root[data-theme="light"] .formula-star-btn {
  background: transparent !important;
  border: none !important;
  color: #0284c7 !important;
}
:root[data-theme="light"] .formula-star-btn:hover,
:root[data-theme="light"] .formula-star-btn:focus-visible {
  background: transparent !important;
  border: none !important;
  transform: none !important;
  color: #0369a1 !important;
}

.param-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.formula-star {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--amber, #f59e0b);
  font-weight: 800;
  font-size: 15px;
  cursor: pointer;
  position: relative;
  padding: 0 4px;
  line-height: 1;
  transition: transform 0.15s ease, color 0.15s ease;
  vertical-align: middle;
}
.formula-star:hover,
.formula-star:focus-within {
  color: #fbbf24;
  transform: scale(1.3);
  z-index: 99999;
}
.formula-tooltip {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 330px;
  max-width: 85vw;
  background: var(--card-bg, #1e2430);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.22));
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.6);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text, #e5e7eb);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  z-index: 999999;
  transition: opacity 0.15s ease, visibility 0.15s ease;
  text-align: left;
  white-space: normal;
  font-weight: 400;
}
[data-theme="light"] .formula-tooltip {
  background: #ffffff;
  border: 1px solid #d1d5db;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
  color: #1f2937;
}
.param-label:hover .formula-tooltip,
.formula-star:hover .formula-tooltip,
.formula-star:focus-within .formula-tooltip {
  opacity: 1 !important;
  visibility: visible !important;
  pointer-events: auto;
}
.formula-tooltip::before {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 10px;
  border-width: 6px;
  border-style: solid;
  border-color: transparent transparent var(--card-bg, #1e2430) transparent;
}
[data-theme="light"] .formula-tooltip::before {
  border-color: transparent transparent #ffffff transparent;
}
.ft-title {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--amber, #f59e0b);
  margin-bottom: 6px;
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.1));
  padding-bottom: 4px;
}
.ft-formula {
  display: block;
  font-size: 11.5px;
  font-family: var(--mono);
  background: rgba(245, 158, 11, 0.08);
  border: 1px dashed rgba(245, 158, 11, 0.35);
  padding: 6px 8px;
  border-radius: 4px;
  margin-bottom: 6px;
  word-break: break-word;
}
.ft-formula code {
  font-size: 11.5px;
  color: var(--amber, #f59e0b);
  font-weight: 600;
}
.ft-desc {
  display: block;
  font-size: 11.5px;
  color: var(--muted, #9ca3af);
  line-height: 1.45;
}
[data-theme="light"] .ft-desc {
  color: #4b5563;
}
.brand { min-width: 0; }
.brand b { font-size: 19px; font-weight: 600; letter-spacing: -0.02em; }
.brand span {
  display: block;
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: var(--eyebrow-tracking);
  text-transform: uppercase;
  color: var(--muted);
  margin-top: 3px;
}
.side-identity { min-width: 0; }
/* Dưới 1100px rail KHÔNG dính (nó nằm ngay trên header cột phải), nên tên bot
   + mã ở đây lặp lại đúng cái `<h1>`/vụn đường dẫn cách đó vài dòng. Ẩn bản
   trong rail, giữ nhãn phán quyết + 3 ô điểm (những thứ header mỏng không
   có). Từ 1100px rail dính lại khi cuộn nên bản này mới có việc để làm. */
.side-identity .bot-name, .side-identity .bot-code { display: none; }
.side-foot { margin-top: auto; padding-top: 12px; border-top: 1px solid var(--border); }

/* Mục lục: một cột danh sách phẳng, viền trái mảnh làm chỉ dấu hover --
   giống `.nav` của bảng điều khiển Nora, không nút bo tròn, không bóng. */
.nav { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.nav-group { display: flex; flex-direction: column; gap: 1px; margin-bottom: 0.6rem; min-width: 0; max-width: 100%; }
.nav-group-label {
  font-family: var(--mono);
  font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-tracking);
  text-transform: uppercase;
  color: var(--muted);
  padding: 4px 0 5px;
}
.nav a {
  display: block;
  min-width: 0;
  max-width: 100%;
  padding: 6px 10px;
  color: var(--muted);
  font-size: 13.5px;
  text-decoration: none;
  border-left: 2px solid transparent;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav a:hover {
  background: var(--panel-2);
  color: var(--text);
  border-left-color: var(--primary-accent);
}

/* --- Đầu cột nội dung: một header MỎNG ------------------------------------
   Danh tính + điểm số đã nằm ở rail trái, nên chỗ này chỉ còn vụn đường dẫn
   mono, tên bot và các cảnh báo. */
.report-header {
  padding: 1.25rem 0 1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.75rem;
}
.crumb {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: var(--eyebrow-tracking);
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 8px;
  overflow-wrap: anywhere;
}
.head-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 0;
  overflow-wrap: anywhere;
  text-wrap: balance;
}
.header-notices { display: flex; flex-direction: column; gap: 22px; margin-top: 26px; }
.bot-name {
  font-size: var(--font-size-lg);
  font-weight: 600;
  letter-spacing: -0.02em;
  overflow-wrap: anywhere;
  color: var(--text);
}
.bot-code {
  color: var(--muted);
  font-size: var(--font-size-xs);
  margin-top: 0.3rem;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.bot-code code {
  background: var(--track);
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-xs);
  font-family: var(--mono);
  font-size: 0.88em;
  border: 1px solid var(--border);
  overflow-wrap: anywhere;
}
.verdict-badge {
  display: inline-flex;
  align-items: center;
  margin-top: 0.6rem;
  padding: 0.3rem 0.7rem;
  border-radius: var(--radius-xs);
  font-family: var(--mono);
  font-weight: 600;
  font-size: var(--font-size-xs);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #fff;
  background: var(--badge-color, #6b7280);
}
/* Hiển thị trọn vẹn văn bản phương pháp luận, không cắt chữ */
.verdict-basis {
  display: block !important;
  -webkit-line-clamp: unset !important;
  overflow: visible !important;
  max-width: none !important;
  font-style: normal !important;
}

/* --- Ô số liệu: lưới hairline kiểu bảng điều khiển ------------------------
   Không bo góc, không bóng đổ, không khe hở: các ô dính liền nhau, ngăn cách
   bằng đúng 1px nền `--border` lộ ra qua `gap` -- đọc như một dải số liệu
   liền mạch chứ không phải một đống thẻ trắng rời rạc. */
.stat-row, .cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(158px, 1fr));
  gap: 1px;
  /* Nền là MÀU THẺ, không phải màu viền: khi số ô không chia hết cho số cột,
     ô trống cuối hàng trước đây lộ ra một mảng xám đặc (ảnh chụp tab "Lệnh &
     vị thế": 6 ô trên lưới 4 cột). Đường kẻ 1px giờ do chính mỗi ô vẽ bằng
     `box-shadow` trải ra ngoài, nên chỗ KHÔNG có ô thì cũng không có kẻ. */
  background: var(--card-bg);
  border: 1px solid var(--border);
  margin-top: 1rem;
}
.stat-tile {
  background: var(--card-bg);
  box-shadow: 0 0 0 1px var(--border);
  padding: 13px 15px;
  min-width: 0;
}
.stat-value {
  font-family: var(--mono);
  font-size: 22px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1.15;
  overflow-wrap: anywhere;
}
.stat-label {
  font-family: var(--mono);
  color: var(--muted);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-top: 0.4rem;
}
/* Dấu `*` bấm được trên mỗi ô điểm số hero, dẫn tới khối giải thích công
   thức bên dưới mục dimension-bar (xem `_stat_tile`'s `basis_anchor`).
   Không hoa/không gạch chân như link thường (đây là một chú thích, không
   phải điều hướng chính của trang), nhưng đủ tương phản để thấy là bấm
   được. */
.score-basis-star {
  color: var(--accent, #3b82f6);
  text-decoration: none;
  font-weight: 700;
  margin-left: 0.15rem;
  cursor: pointer;
}
.score-basis-star:hover, .score-basis-star:focus-visible {
  text-decoration: underline;
}
details.theory.score-basis h3 {
  font-size: var(--font-size-sm);
  margin: 0.9rem 0 0.3rem;
}
details.theory.score-basis h3:first-child { margin-top: 0; }

/* Biến thể "hero" -- 3 ô điểm số ở rail trái, thứ duy nhất yêu cầu thiết kế
   nói phải nổi bật NHẤT. Dải màu mảnh bên trái thay cho viền trên: ở rail
   dọc, ba ô xếp chồng nên dải dọc mới phân biệt được chúng bằng mắt. */
.stat-tile-hero {
  padding: 13px 15px;
  border-left: 3px solid var(--tile-accent, var(--border));
}
.stat-tile-hero .stat-value { font-size: 34px; font-weight: 600; line-height: 1.05; }
.stat-tile-hero .stat-label { font-size: 10.5px; margin-top: 0.35rem; }
.side-identity .cards { grid-template-columns: 1fr; margin-top: 0.85rem; }

/* --- Khối nội dung: `.block-h` + `.block-b` -------------------------------
   Bỏ hẳn bo góc lớn + bóng đổ (thứ làm cả trang trông như một chồng thẻ nổi
   giống hệt nhau): mỗi mục giờ là một khối viền 1px, có thanh tiêu đề nền
   `--panel-2` ngăn cách rõ với phần thân. */
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  box-shadow: none;
  margin-top: 1.15rem;
  min-width: 0;
}
.block-h {
  padding: 11px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--panel-2);
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.block-h .eyebrow {
  flex: 1 0 100%;
  font-family: var(--mono);
  font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-tracking);
  text-transform: uppercase;
  color: var(--muted);
}
.block-h .note {
  margin-left: auto;
  font-size: var(--font-size-xs);
  color: var(--muted);
}
.block-b { padding: 14px 16px 16px; min-width: 0; }
.card h2 {
  margin: 0;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
  min-width: 0;
  overflow-wrap: anywhere;
}
.card h3 { margin: 1.1rem 0 0.4rem; font-size: var(--font-size-sm); font-weight: 600; color: var(--text); }
.block-b > *:first-child { margin-top: 0; }

/* --- Phân cấp thị giác giữa các mục ---------------------------------------
   CHÚ Ý: comment trong `_CSS` này bị nhúng vào MỌI trang render ra -- một
   vài test dò "tiêu đề mục X không được xuất hiện ở đâu cả trong HTML" bằng
   cách tìm nguyên văn tiêu đề đó trên TOÀN BỘ output, nên comment ở đây
   tuyệt đối không được gõ lại nguyên văn một tiêu đề mục nào, chỉ nhắc bằng
   id neo (id="..." -- xem `_section`'s `anchor=`).

   `.card-primary` (id="ket-luan", id="diem-chieu") nổi bật bằng một vạch màu
   verdict ở mép trái + thanh tiêu đề ánh accent, KHÔNG bằng bóng đổ.
   `.card-quiet` (id="suy-luan", id="vi-the-mo") lùi xuống: tiêu đề nhỏ, mờ. */
.card-primary {
  border-color: var(--card-border-emphasis);
  border-left: 3px solid var(--primary-accent);
}
.card-primary > .block-h { background: var(--card-bg-emphasis); }
.card-primary > .block-h h2 { font-size: 17px; }
.card-quiet > .block-h h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.notice {
  border-left: 4px solid;
  border-radius: 6px;
  padding: 0.6rem 0.85rem;
  margin-top: 0.75rem;
  font-size: var(--font-size-sm);
}
.notice-warning { background: var(--notice-warning-bg); border-color: var(--notice-warning-border); }
.notice-danger { background: var(--notice-danger-bg); border-color: var(--notice-danger-border); }
.header-notices .notice { margin-top: 0; }
.narrative-disclaimer { color: var(--muted); font-size: var(--font-size-xs); margin: 0 0 0.6rem; font-style: italic; }
.narrative-body { margin: 0; white-space: pre-wrap; line-height: 1.55; }
.table-scroll { overflow-x: auto; margin-top: 0.5rem; max-height: 560px; }
#so-lieu .table-scroll, #suy-luan .table-scroll { overflow: visible !important; max-height: none !important; }
table {
  border-collapse: collapse;
  width: 100%;
  min-width: 320px;
  font-size: 13.5px;
  font-variant-numeric: tabular-nums;
}
th, td {
  text-align: left;
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
/* Hàng tiêu đề dính khi cuộn bảng dài (`.table-scroll` có max-height) -- đọc
   tới hàng thứ 40 vẫn biết cột nào là cột nào. */
thead th {
  color: var(--muted);
  font-family: var(--mono);
  font-weight: 400;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: var(--panel-2);
  position: sticky;
  top: 0;
  z-index: 1;
}
tbody tr:last-child td { border-bottom: none; }
td:first-child, th:first-child { white-space: normal; }
/* Căn phải mọi cột trừ cột đầu (luôn là nhãn/tên) -- dễ quét mắt theo cột
   số dọc thay vì chữ lởm chởm hai bên, đúng quy ước bảng số liệu tài
   chính (Bloomberg/Stripe). */
td:not(:first-child), th:not(:first-child) { text-align: right; }
tbody tr:hover { background: var(--table-hover); }
.badge {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-family: var(--mono);
  font-size: 10.5px;
  font-weight: 600;
  color: #fff;
  background: var(--badge-color, #6b7280);
  white-space: nowrap;
}
details.theory {
  margin-top: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.35);
  padding: 0.4rem 0.75rem;
  transition: all 0.2s ease;
}
:root[data-theme="light"] details.theory {
  background: #f8fafc;
  border-color: #e2e8f0;
}
details.theory summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 11.5px;
  letter-spacing: 0.03em;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}
details.theory[open] summary {
  color: #38bdf8;
  margin-bottom: 0.4rem;
}
.theory-body { font-size: var(--font-size-sm); margin-top: 0.25rem; color: var(--text); }
.theory-body p { margin: 0.3rem 0; }
.theory-body code { background: var(--track); padding: 0.05rem 0.3rem; border-radius: 4px; }
.theory-quant-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0 2px;
}
.theory-item {
  display: grid;
  grid-template-columns: 140px 1fr;
  align-items: baseline;
  gap: 12px;
  font-size: 12px;
  line-height: 1.5;
}
@media (max-width: 640px) {
  .theory-item {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
.theory-tag {
  font-family: var(--mono, monospace);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.25);
  padding: 1px 6px;
  border-radius: 4px;
  width: fit-content;
}
.theory-tag.theory-tag-formula {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.1);
  border-color: rgba(167, 139, 250, 0.25);
}
.theory-text {
  color: #cbd5e1;
}
:root[data-theme="light"] .theory-text {
  color: #334155;
}

/* Score explanation notes - Quant Matrix View */
.score-basis-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 6px;
}
.score-basis-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sb-section-header {
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.score-basis-table,
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: var(--mono, monospace);
  background: rgba(15, 23, 42, 0.4);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
:root[data-theme="light"] .score-basis-table {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.score-basis-table th,
.data-table th {
  text-align: left;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.04);
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
:root[data-theme="light"] .score-basis-table th,
:root[data-theme="light"] .data-table th {
  background: #f1f5f9;
  color: #64748b;
  border-bottom-color: #e2e8f0;
}
.score-basis-table td,
.data-table td {
  padding: 6px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: #cbd5e1;
}
:root[data-theme="light"] .score-basis-table td,
:root[data-theme="light"] .data-table td {
  border-bottom-color: #f1f5f9;
  color: #334155;
}
.score-basis-table tr:last-child td,
.data-table tr:last-child td {
  border-bottom: none;
}
.score-basis-table .row-unmeasured td,
.data-table .row-unmeasured td {
  opacity: 0.6;
}
.dim-col-name strong {
  font-family: var(--font, sans-serif);
  color: #f1f5f9;
  font-weight: 600;
}
:root[data-theme="light"] .dim-col-name strong {
  color: #0f172a;
}
.dim-col-num {
  font-weight: 700;
}
.q-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.04em;
}
.q-badge-ok {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.q-badge-neutral {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.25);
}
.score-basis-alert {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.score-basis-veto {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}
:root[data-theme="light"] .score-basis-veto {
  background: rgba(239, 68, 68, 0.06);
  border-color: #fca5a5;
  color: #b91c1c;
}
.score-basis-normal {
  background: rgba(56, 189, 248, 0.06);
  border: 1px solid rgba(56, 189, 248, 0.25);
  color: #bae6fd;
}
:root[data-theme="light"] .score-basis-normal {
  background: #f0f9ff;
  border-color: #bae6fd;
  color: #0369a1;
}
.sb-badge-veto {
  font-family: var(--mono, monospace);
  font-size: 10.5px;
  font-weight: 800;
  background: #ef4444;
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
}
.sb-badge-normal {
  font-family: var(--mono, monospace);
  font-size: 10.5px;
  font-weight: 700;
  background: #0284c7;
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
}
.score-basis-math-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 4px;
}
@media (max-width: 640px) {
  .score-basis-math-grid {
    grid-template-columns: 1fr;
  }
}
.sb-math-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}
:root[data-theme="light"] .sb-math-col {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.sb-label {
  font-family: var(--mono, monospace);
  font-size: 10.5px;
  font-weight: 700;
  color: #94a3b8;
}
:root[data-theme="light"] .sb-label {
  color: #64748b;
}
.sb-desc {
  font-size: 11.5px;
  color: #cbd5e1;
}
:root[data-theme="light"] .sb-desc {
  color: #475569;
}
.findings { margin: 0.5rem 0 0; padding-left: 1.2rem; font-size: var(--font-size-sm); color: var(--ink-2, #cbd5e1); line-height: 1.6; }
.findings li { margin: 0.25rem 0; }
.findings li strong { color: var(--ink, #ffffff); font-weight: 600; }
/* Expert Assessment - Modern Fintech Insight Cards */
.expert-summary-box {
  background: rgba(56, 189, 248, 0.04);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-left: 3px solid var(--info, #38bdf8);
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 0.5rem;
  margin-bottom: 0.85rem;
  box-sizing: border-box;
}
.expert-summary-label {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--info, #38bdf8);
  margin-bottom: 4px;
}
.expert-summary-text {
  font-size: 13.5px;
  line-height: 1.55;
  color: var(--ink, #ffffff);
  font-weight: 500;
}
.methodology-footer {
  margin-top: 1rem;
}
.mf-group + .mf-group {
  margin-top: 0.85rem;
}
.mf-title {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-3, #94a3b8);
  margin-bottom: 6px;
}
.mf-list {
  margin: 0;
  padding-left: 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.mf-list li {
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--ink-2, #cbd5e1);
}
.mf-why {
  display: block;
  margin-top: 2px;
  font-size: 11.5px;
  color: var(--ink-3, #94a3b8);
}
.expert-summary-sub {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ink-2, #cbd5e1);
}
.root-cause-block {
  margin-top: 0.85rem;
}
.root-cause-title {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-3, #94a3b8);
  margin-bottom: 6px;
}
.root-cause-list {
  margin: 0;
  padding-left: 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.root-cause-list li {
  font-size: 13px;
  line-height: 1.5;
  color: var(--ink, #0f172a);
}
/* The measurement that put the mechanism on the list, on its own line so a
   reader can check the claim rather than take the sentence on trust. */
.root-cause-support {
  display: block;
  margin-top: 2px;
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--ink-3, #94a3b8);
}
.expert-points-wrap {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
}
.expert-points-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
}
.expert-points-title {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted, #94a3b8);
}
.expert-points-count {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--muted, #94a3b8);
}
.expert-points-feed {
  display: flex;
  flex-direction: column;
  gap: 7px;
  max-height: 285px;
  overflow-y: auto;
  padding-right: 4px;
  box-sizing: border-box;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}
.expert-points-feed::-webkit-scrollbar {
  width: 5px;
}
.expert-points-feed::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px;
}
.expert-point-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 7px;
  padding: 9px 12px;
  box-sizing: border-box;
  transition: all 0.15s ease;
}
.expert-point-card:hover {
  background: rgba(255, 255, 255, 0.045);
  border-color: rgba(56, 189, 248, 0.3);
  transform: translateX(2px);
}
.expert-point-num {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 4px;
  padding: 2px 6px;
  line-height: 1.2;
  flex-shrink: 0;
  margin-top: 2px;
}
.expert-point-content {
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--ink-2, #cbd5e1);
  flex: 1;
}
.expert-metric {
  font-family: var(--mono);
  font-weight: 700;
  color: var(--ink, #ffffff);
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
}
:root[data-theme="light"] .expert-summary-box {
  background: #f0f9ff;
  border-color: #bae6fd;
  border-left-color: #0284c7;
}
:root[data-theme="light"] .expert-summary-label {
  color: #0284c7;
}
:root[data-theme="light"] .expert-summary-text {
  color: #0f172a;
}
:root[data-theme="light"] .expert-point-card {
  background: #f8fafc;
  border-color: #e2e8f0;
}
:root[data-theme="light"] .expert-point-card:hover {
  background: #ffffff;
  border-color: #0284c7;
}
:root[data-theme="light"] .expert-point-num {
  color: #0284c7;
  background: #e0f2fe;
  border-color: #bae6fd;
}
:root[data-theme="light"] .expert-point-content {
  color: #334155;
}
:root[data-theme="light"] .expert-metric {
  color: #0f172a;
  background: #f1f5f9;
}
svg { height: auto; }
svg.bar-chart { display: block; margin-top: 0.6rem; max-width: 860px; }
svg text { fill: var(--text); font-size: 12px; font-variant-numeric: tabular-nums; }
svg .bar-label, svg .bar-label-sm { fill: var(--ink-2, #cbd5e1); font-size: 12.5px; font-weight: 500; }
svg .bar-value, svg .bar-value-sm { font-weight: 700; font-size: 12px; fill: var(--ink, #ffffff); }
svg .bar-value.val-pos { fill: #10b981 !important; }
svg .bar-value.val-neg { fill: #ef4444 !important; }

/* Market Data Coverage */
.cov-card-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.cov-benchmark-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 4px;
}
.cov-benchmark-title {
  font-family: var(--mono, monospace);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted, #94a3b8);
}
.cov-benchmark-metrics {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono, monospace);
  font-size: 11px;
}
.cov-metric-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.cov-metric-label {
  color: var(--muted, #94a3b8);
}
.cov-metric-val {
  color: var(--ink, #ffffff);
  font-weight: 700;
}
.cov-metric-sep {
  color: var(--border, rgba(255, 255, 255, 0.15));
}
.cov-status-badge {
  font-family: var(--mono, monospace);
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.cov-status-under {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.35);
}
.cov-status-met {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.35);
}
.cov-bar-wrapper {
  position: relative;
  width: 100%;
  margin: 16px 0 8px;
}
.cov-target-line {
  position: absolute;
  top: -8px;
  bottom: -8px;
  width: 2px;
  border-left: 2px dashed #f59e0b;
  z-index: 10;
  pointer-events: none;
}
.cov-target-pin {
  position: absolute;
  top: -16px;
  left: 0;
  transform: translateX(-50%);
  font-family: var(--mono, monospace);
  font-size: 9.5px;
  font-weight: 700;
  color: #f59e0b;
  background: var(--card-bg, #0b1120);
  padding: 1px 4px;
  border-radius: 3px;
  border: 1px solid rgba(245, 158, 11, 0.3);
  white-space: nowrap;
}
.cov-stacked-bar {
  display: flex;
  width: 100%;
  height: 38px;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  box-sizing: border-box;
}
.cov-bar-seg {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.18s ease;
  box-sizing: border-box;
  border-right: 1px solid rgba(0, 0, 0, 0.25);
  cursor: pointer;
}
.cov-bar-seg:hover {
  filter: brightness(1.18);
  transform: translateY(-1px);
  z-index: 5;
}
.cov-bar-seg:last-child {
  border-right: none;
}
.cov-seg-inner {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 4px;
  font-family: var(--mono, monospace);
  font-size: 11px;
  font-weight: 600;
  pointer-events: none;
}
.cov-seg-resolved .cov-seg-inner {
  color: #ffffff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.65);
}
.cov-seg-unresolved {
  background: repeating-linear-gradient(45deg, rgba(148, 163, 184, 0.1), rgba(148, 163, 184, 0.1) 6px, rgba(148, 163, 184, 0.22) 6px, rgba(148, 163, 184, 0.22) 12px) !important;
  border-right: 1px dashed rgba(148, 163, 184, 0.3);
}
.cov-seg-unresolved .cov-seg-inner {
  color: var(--muted, #cbd5e1);
}
.cov-seg-unallocated {
  background: repeating-linear-gradient(-45deg, rgba(148, 163, 184, 0.06), rgba(148, 163, 184, 0.06) 5px, rgba(148, 163, 184, 0.14) 5px, rgba(148, 163, 184, 0.14) 10px) !important;
}
.cov-seg-unallocated .cov-seg-inner {
  color: var(--muted, #94a3b8);
  font-size: 10.5px;
}
.cov-sublabel-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11.5px;
  margin-top: 4px;
  padding: 0 2px;
}
.cov-sublabel-col {
  display: flex;
  align-items: center;
  gap: 6px;
}
.cov-sublabel-resolved {
  color: #10b981;
}
.cov-sublabel-unresolved {
  color: var(--muted, #94a3b8);
}
.cov-icon-resolved {
  color: #10b981;
  font-weight: 700;
}
.cov-icon-unresolved {
  color: #f59e0b;
  font-weight: 700;
}
.cov-warning-box {
  border-left: 3px solid #f59e0b;
  background: rgba(245, 158, 11, 0.08);
  border-radius: 6px;
  padding: 11px 15px;
  margin-top: 8px;
}
.cov-warning-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--mono, monospace);
  font-size: 11px;
  font-weight: 700;
  color: #f59e0b;
  margin-bottom: 4px;
  letter-spacing: 0.04em;
}
.cov-warning-body {
  font-size: 12px;
  line-height: 1.55;
  color: var(--ink, #e2e8f0);
}
.cov-dim-pill {
  display: inline-block;
  font-family: var(--mono, monospace);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: #fbbf24;
  margin: 0 2px;
  transition: all 0.15s ease;
  cursor: pointer;
}
.cov-dim-pill:hover {
  background: rgba(245, 158, 11, 0.25);
  border-color: #f59e0b;
  color: #ffffff;
  text-decoration: none;
}

/* Light mode overrides for market coverage */
:root[data-theme="light"] .cov-benchmark-title {
  color: #64748b !important;
}
:root[data-theme="light"] .cov-metric-val {
  color: #0f172a !important;
}
:root[data-theme="light"] .cov-metric-sep {
  color: #cbd5e1 !important;
}
:root[data-theme="light"] .cov-target-pin {
  background: #ffffff !important;
  color: #d97706 !important;
  border-color: rgba(217, 119, 6, 0.3) !important;
}
:root[data-theme="light"] .cov-stacked-bar {
  background: #f1f5f9 !important;
  border-color: #e2e8f0 !important;
}
:root[data-theme="light"] .cov-seg-unresolved {
  background: repeating-linear-gradient(45deg, rgba(100, 116, 139, 0.08), rgba(100, 116, 139, 0.08) 6px, rgba(100, 116, 139, 0.16) 6px, rgba(100, 116, 139, 0.16) 12px) !important;
  border-right-color: #cbd5e1 !important;
}
:root[data-theme="light"] .cov-seg-unresolved .cov-seg-inner {
  color: #475569 !important;
}
:root[data-theme="light"] .cov-warning-box {
  background: #fffbeb !important;
  border-color: #d97706 !important;
}
:root[data-theme="light"] .cov-warning-head {
  color: #b45309 !important;
}
:root[data-theme="light"] .cov-warning-body {
  color: #1e293b !important;
}
:root[data-theme="light"] .cov-dim-pill {
  background: #fef3c7 !important;
  border-color: #fde68a !important;
  color: #92400e !important;
}
:root[data-theme="light"] .cov-dim-pill:hover {
  background: #fde68a !important;
  color: #78350f !important;
}

/* Multi-horizon comparison matrix */
.hz-matrix-wrap {
  width: 100%;
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  background: var(--card-bg, #0e1526);
  overflow-x: auto;
  overflow-y: visible;
  max-height: none;
  margin-top: 0.25rem;
  margin-bottom: 0.65rem;
  box-sizing: border-box;
}
.hz-matrix-table {
  width: 100%;
  min-width: 320px;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: auto;
  margin: 0;
}
.hz-matrix-table th {
  background: rgba(255, 255, 255, 0.035);
  color: var(--muted, #94a3b8);
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
}
.hz-matrix-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: var(--ink, #e2e8f0);
  font-size: 12px;
  vertical-align: middle;
}
.hz-matrix-row {
  transition: background 0.15s ease;
}
.hz-matrix-row:hover {
  background: rgba(255, 255, 255, 0.035);
}
.hz-matrix-table tr:last-child td {
  border-bottom: none;
}
.hz-matrix-table .col-hz {
  width: 22%;
  text-align: left;
}
.hz-matrix-table .col-sample {
  width: 18%;
  text-align: left;
}
.hz-matrix-table .col-pop {
  width: 34%;
  text-align: left;
}
.hz-matrix-table .col-loss-ruin {
  width: 26%;
  text-align: right;
  white-space: nowrap;
}
.hz-pill {
  display: inline-block;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 2px 7px;
  border-radius: 4px;
}
.hz-pill-short {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}
.hz-pill-medium {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}
.hz-pill-long {
  background: rgba(14, 165, 233, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(14, 165, 233, 0.3);
}
.hz-sample {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted, #94a3b8);
  font-variant-numeric: tabular-nums;
}
.hz-progress-wrap {
  display: flex;
  align-items: center;
  gap: 7px;
}
.hz-progress-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
  min-width: 36px;
}
.hz-progress-bar {
  height: 100%;
  border-radius: 999px;
  transition: width 0.3s ease;
}
.hz-progress-val {
  font-family: var(--mono);
  font-size: 11.5px;
  font-weight: 700;
  min-width: 38px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.hz-loss-val, .hz-ruin-val {
  font-family: var(--mono);
  font-size: 11.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.hz-divider {
  color: var(--muted, #64748b);
  margin: 0 3px;
  opacity: 0.6;
}
.hz-insight-callout {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 11.5px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.4;
  margin-top: 0.5rem;
  margin-bottom: 0.75rem;
  box-sizing: border-box;
}
.hz-insight-icon {
  font-size: 13px;
  flex: 0 0 auto;
  line-height: 1.3;
}
.hz-insight-body {
  flex: 1;
}
.hz-insight-decay {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: #fca5a5;
}
.hz-insight-decay strong {
  color: #ef4444;
}
.hz-insight-warn {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  color: #fde68a;
}
.hz-insight-warn strong {
  color: #f59e0b;
}
.hz-insight-positive {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.25);
  color: #a7f3d0;
}
.hz-insight-positive strong {
  color: #10b981;
}
.hz-insight-info {
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: #bfdbfe;
}
.hz-insight-info strong {
  color: #60a5fa;
}

/* Key Probabilities KPI Badges & Table */
.kp-kpi-footer {
  margin-top: 6px;
  display: flex;
  align-items: center;
}
.kp-kpi-sublabel {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted, #94a3b8);
  margin-top: 1px;
  margin-bottom: 4px;
}
.kp-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--mono);
  font-size: 9.5px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.kp-badge-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  display: inline-block;
}
.kp-badge-safe {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}
.kp-badge-safe .kp-badge-dot {
  background: #10b981;
}
.kp-badge-warn {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #fbbf24;
}
.kp-badge-warn .kp-badge-dot {
  background: #f59e0b;
}
.kp-badge-danger {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}
.kp-badge-danger .kp-badge-dot {
  background: #ef4444;
}
.kp-subhead-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.65rem;
  margin-bottom: 0.35rem;
}
.kp-subhead-title {
  font-family: var(--mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted, #94a3b8);
}
.kp-subhead-meta {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted, #94a3b8);
}
.kp-table-wrap {
  width: 100%;
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  background: var(--card-bg, #0e1526);
  overflow-x: auto;
  overflow-y: visible;
  max-height: none;
  margin-bottom: 0.5rem;
  box-sizing: border-box;
}
.kp-table {
  width: 100%;
  min-width: 320px;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: auto;
  margin: 0;
}
.kp-table th {
  background: rgba(255, 255, 255, 0.035);
  color: var(--muted, #94a3b8);
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
}
.kp-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: var(--ink, #e2e8f0);
  font-size: 12px;
  vertical-align: middle;
}
.kp-table tr:last-child td {
  border-bottom: none;
}
.kp-table .col-streak {
  width: 28%;
  text-align: left;
  white-space: nowrap;
}
.kp-table .col-obs {
  width: 24%;
  text-align: right;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}
.kp-table .col-base {
  width: 24%;
  text-align: right;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}
.kp-table .col-excess {
  width: 24%;
  text-align: right;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}
.kp-streak-pill {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--ink, #e2e8f0);
}
.kp-streak-row {
  transition: background 0.15s ease;
}
.kp-streak-row:hover {
  background: rgba(255, 255, 255, 0.035);
}
.th-sub {
  font-size: 8.5px;
  font-weight: 400;
  text-transform: none;
  opacity: 0.75;
}

/* Light Mode Overrides for Monte Carlo pair */
:root[data-theme="light"] .hz-matrix-wrap {
  background: #ffffff !important;
  border-color: #e2e8f0 !important;
}
:root[data-theme="light"] .hz-matrix-table th {
  background: #f8fafc !important;
  border-color: #e2e8f0 !important;
  color: #64748b !important;
}
:root[data-theme="light"] .hz-matrix-table td {
  border-color: #f1f5f9 !important;
  color: #0f172a !important;
}
:root[data-theme="light"] .hz-matrix-row:hover,
:root[data-theme="light"] .kp-streak-row:hover {
  background: #f8fafc !important;
}
:root[data-theme="light"] .hz-progress-track {
  background: rgba(0, 0, 0, 0.07) !important;
}
:root[data-theme="light"] .hz-insight-decay {
  background: #fef2f2 !important;
  border-color: #fecaca !important;
  color: #991b1b !important;
}
:root[data-theme="light"] .hz-insight-decay strong {
  color: #b91c1c !important;
}
:root[data-theme="light"] .hz-insight-warn {
  background: #fffbeb !important;
  border-color: #fde68a !important;
  color: #92400e !important;
}
:root[data-theme="light"] .hz-insight-warn strong {
  color: #b45309 !important;
}
:root[data-theme="light"] .hz-insight-positive {
  background: #f0fdf4 !important;
  border-color: #bbf7d0 !important;
  color: #166534 !important;
}
:root[data-theme="light"] .hz-insight-positive strong {
  color: #15803d !important;
}
:root[data-theme="light"] .hz-insight-info {
  background: #eff6ff !important;
  border-color: #bfdbfe !important;
  color: #1e40af !important;
}
:root[data-theme="light"] .hz-insight-info strong {
  color: #1d4ed8 !important;
}
:root[data-theme="light"] .kp-streak-pill {
  color: #0f172a !important;
}
:root[data-theme="light"] .kp-subhead-title {
  color: #64748b !important;
}

/* Monte Carlo paired 2-column layout */
.mc-pair-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
  align-items: stretch;
  margin-top: 1rem;
  width: 100%;
  box-sizing: border-box;
}
@media (max-width: 1080px) {
  .mc-pair-row {
    grid-template-columns: 1fr !important;
  }
}
.mc-pair-cell {
  background: var(--surface-2, rgba(255, 255, 255, 0.035));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.09));
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: auto;
  min-height: auto;
  box-sizing: border-box;
}
.mc-pair-cell h3 {
  margin: 0 0 0.75rem 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink, #ffffff);
}
.mc-pair-cell details.theory,
.mc-full-row details.theory {
  margin-top: auto;
}
.mc-full-row {
  background: var(--surface-2, rgba(255, 255, 255, 0.035));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.09));
  border-radius: 10px;
  padding: 1.25rem;
  margin-top: 1.25rem;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  min-width: 0;
}
.mc-full-row h3 {
  margin: 0 0 0.75rem 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink, #ffffff);
}
:root[data-theme="light"] .mc-pair-cell,
:root[data-theme="light"] .mc-full-row {
  background: var(--panel, #ffffff);
  border: 1px solid var(--line, #e2e8f0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
:root[data-theme="light"] .mc-pair-cell h3,
:root[data-theme="light"] .mc-full-row h3 {
  color: var(--ink, #0f172a);
}
.mc-pair-cell .table-scroll {
  margin-top: 0.25rem;
  margin-bottom: 0.5rem;
  max-height: 180px;
  overflow-y: auto;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
}
.mc-pair-cell .table-scroll::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.mc-pair-cell .table-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.mc-pair-cell .table-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px;
}
.mc-pair-cell .table-scroll thead th {
  position: sticky;
  top: 0;
  background: var(--surface-2, #141b2d);
  z-index: 2;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.08);
}
:root[data-theme="light"] .mc-pair-cell .table-scroll {
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
  border-color: rgba(0, 0, 0, 0.06);
}
:root[data-theme="light"] .mc-pair-cell .table-scroll thead th {
  background: #f8fafc;
  box-shadow: 0 1px 0 #e2e8f0;
}
/* Key Probabilities Layout - Seamless & Aligned */
.kp-kpi-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
  margin-top: 0.25rem;
  margin-bottom: 0.75rem;
  width: 100%;
}
.kp-kpi-card {
  background: var(--card-bg, #0e1526);
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  padding: 11px 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.kp-kpi-value {
  font-family: var(--mono);
  font-size: 21px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--ink, #ffffff);
  font-variant-numeric: tabular-nums;
}
.kp-kpi-label {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--muted, #94a3b8);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 4px;
}
.kp-table-wrap {
  width: 100%;
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  background: var(--card-bg, #0e1526);
  overflow-y: auto;
  overflow-x: hidden;
  max-height: 180px;
  margin-bottom: 0.5rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}
.kp-table-wrap::-webkit-scrollbar {
  width: 5px;
}
.kp-table-wrap::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px;
}
.kp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: fixed;
  margin: 0;
}
.kp-table th {
  background: rgba(255, 255, 255, 0.035);
  color: var(--muted, #94a3b8);
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  position: sticky;
  top: 0;
  z-index: 1;
}
.kp-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: var(--ink, #e2e8f0);
  font-size: 12px;
}
.kp-table tr:last-child td {
  border-bottom: none;
}
.kp-table .col-streak {
  text-align: left;
  width: 44%;
}
.kp-table .col-obs,
.kp-table .col-base,
.kp-table .col-excess {
  text-align: right;
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  width: 18.6%;
}
:root[data-theme="light"] .kp-kpi-card {
  background: #ffffff;
  border-color: #e2e8f0;
}
:root[data-theme="light"] .kp-table-wrap {
  background: #ffffff;
  border-color: #e2e8f0;
}
:root[data-theme="light"] .kp-table th {
  background: #f8fafc;
  border-color: #e2e8f0;
}
:root[data-theme="light"] .kp-table td {
  border-color: #f1f5f9;
}
.kp-stat-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 0.35rem;
  margin-bottom: 0.75rem;
  width: 100%;
}
@media (max-width: 640px) {
  .kp-stat-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.kp-stat-item {
  background: var(--card-bg, #0e1526);
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
}
:root[data-theme="light"] .kp-stat-item {
  background: #ffffff;
  border-color: #e2e8f0;
}
.kp-stat-label {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--muted, #94a3b8);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
:root[data-theme="light"] .kp-stat-label {
  color: #64748b;
}
.kp-stat-val {
  font-family: var(--mono);
  font-size: 15px;
  font-weight: 700;
  margin-top: 3px;
  margin-bottom: 3px;
  font-variant-numeric: tabular-nums;
  color: var(--ink, #ffffff);
}
:root[data-theme="light"] .kp-stat-val {
  color: #0f172a;
}
.kp-stat-sub {
  font-size: 10px;
  color: var(--ink-3, #94a3b8);
  line-height: 1.25;
}
:root[data-theme="light"] .kp-stat-sub {
  color: #64748b;
}
@media (max-width: 900px) {
  .mc-pair-row {
    grid-template-columns: 1fr;
  }
}
.not-found { text-align: center; padding: 2.5rem 1.2rem; }
.not-found h1 { font-size: var(--font-size-lg); }
svg.line-chart { display: block; margin-top: 0.6rem; max-width: 1000px; }
svg .line-marker { font-weight: 700; font-size: 11px; }
svg .line-marker.line-marker-trough { fill: #f87171 !important; font-weight: 700 !important; font-size: 11px !important; }
svg .line-marker.line-marker-peak { fill: #34d399 !important; font-weight: 700 !important; font-size: 11px !important; }
:root[data-theme="light"] svg .line-marker.line-marker-trough { fill: #dc2626 !important; }
:root[data-theme="light"] svg .line-marker.line-marker-peak { fill: #15803d !important; }
svg .line-end-label { font-weight: 700; font-size: 13px; fill: var(--ink, #ffffff); }
svg.pie-chart { display: block; margin-top: 0.4rem; max-width: 460px; margin-inline: auto; }
svg .pie-label { font-weight: 600; font-size: 11.5px; fill: var(--ink, #ffffff); }
svg .pie-value { fill: var(--ink-2, #cbd5e1); font-size: 11px; }
svg .pie-empty { fill: var(--ink-3, #94a3b8); font-size: 12px; }
.growth-dashboard-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 1.5rem;
  align-items: stretch;
}
@media (max-width: 960px) {
  .growth-dashboard-grid {
    grid-template-columns: 1fr;
  }
}
.growth-dashboard-left {
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.growth-curve-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.growth-chart-wrapper {
  flex: 1 0 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.growth-dashboard-right {
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 1rem;
}
.win-loss-composition-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.pie-stack-vertical {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 0.5rem;
  flex: 1 0 auto;
}
.growth-curve-panel > .theory,
.win-loss-composition-panel > .theory {
  margin-top: auto !important;
  padding-top: 14px;
}
.pie-card-stacked {
  background: var(--surface-2, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: 10px;
  padding: 1rem;
}
.pie-card-stacked h4 { margin: 0 0 0.4rem; font-size: var(--font-size-md); color: var(--muted); }
.pie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
  margin-top: 0.5rem;
}
.pie-cell { min-width: 0; }
.pie-cell h4 { margin: 0 0 0.3rem; font-size: var(--font-size-md); color: var(--muted); }
.admin-banner {
  display: none !important;
}
.admin-badge {
  background: #111827;
  color: #fff;
  font-weight: 700;
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}
.admin-banner a { color: var(--muted); }
/* Banner thông báo trạng thái phân tích lưu trữ (đặt ở đầu trang, ngay dưới header/admin-banner) */
.snapshot-banner {
  margin-top: 1rem;
  margin-bottom: 1rem;
  padding: 9px 16px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-left: 3px solid var(--primary-accent);
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.84rem;
  color: var(--ink-2);
}
.snapshot-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 5px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--primary-accent);
  white-space: nowrap;
}
.snapshot-text {
  flex: 1 1 320px;
  min-width: 240px;
}
.snapshot-text strong {
  color: var(--ink);
}
.snapshot-actions {
  display: inline-flex;
  align-items: center;
}
.snapshot-banner a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  background: var(--primary-accent);
  color: #ffffff !important;
  font-weight: 600;
  font-size: 0.82rem;
  border-radius: 6px;
  text-decoration: none;
  transition: all 0.2s ease;
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}
.snapshot-banner a:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
  text-decoration: none;
}
.snapshot-stale {
  color: #d97706;
  font-weight: 600;
  display: inline-block;
}
footer.report-footer {
  color: var(--muted);
  font-size: var(--font-size-xs);
  text-align: center;
  margin-top: 1.5rem;
}
.venue-symbol-badge {
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.15rem 0.55rem;
  border-radius: 6px;
  background: var(--track);
  color: var(--primary-accent);
  border: 1px solid var(--border);
  vertical-align: middle;
}
.tabs-control-wrapper {
  margin-top: 1.25rem;
}
.tab-nav-radio {
  display: none !important;
}
/* Thanh tab dính đầu cột nội dung -- cuộn sâu 3000px vẫn đổi được tab.
   Accent dùng kiệm: tab đang mở chỉ gạch chân 2px, không nền, không bóng. */
.tabs-header-container {
  position: sticky;
  top: 56px;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  padding: 10px 0;
  background: var(--bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}
:root[data-theme="light"] .tabs-header-container {
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.tabs-nav-bar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.07);
  padding: 4px;
  border-radius: 10px;
}
:root[data-theme="light"] .tabs-nav-bar {
  background: rgba(15, 23, 42, 0.04);
  border-color: rgba(15, 23, 42, 0.08);
}
.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-2);
  cursor: pointer;
  user-select: none;
  border-radius: 7px;
  border: 1px solid transparent;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.tab-label:hover {
  color: var(--ink);
  background: rgba(255, 255, 255, 0.04);
}
:root[data-theme="light"] .tab-label:hover {
  background: rgba(15, 23, 42, 0.04);
}
.theme-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.7rem;
  background: var(--card-bg);
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  font-size: 11px;
  font-family: var(--mono);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
}
.theme-toggle-btn:hover {
  border-color: var(--primary-accent);
  color: var(--primary-accent);
}
[data-theme="dark"] .theme-icon-dark,
:root:not([data-theme="light"]) .theme-icon-dark {
  display: none;
}
[data-theme="dark"] .theme-icon-light,
:root:not([data-theme="light"]) .theme-icon-light {
  display: inline;
}
:root[data-theme="light"] .theme-icon-light {
  display: none;
}
:root[data-theme="light"] .theme-icon-dark {
  display: inline;
}
#tab-nav-report:checked ~ .tabs-header-container .label-report,
#tab-nav-market:checked ~ .tabs-header-container .label-market,
#tab-nav-trades:checked ~ .tabs-header-container .label-trades {
  background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
  color: #FFFFFF;
  border-color: rgba(255, 255, 255, 0.16);
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
:root[data-theme="light"] #tab-nav-report:checked ~ .tabs-header-container .label-report,
:root[data-theme="light"] #tab-nav-market:checked ~ .tabs-header-container .label-market,
:root[data-theme="light"] #tab-nav-trades:checked ~ .tabs-header-container .label-trades {
  background: #FFFFFF;
  color: #0F172A;
  border-color: rgba(15, 23, 42, 0.12);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
/* Không animation khi đổi tab: thừa, và làm ảnh chụp/kiểm thử thị giác bắt
   được trạng thái mờ dở dang. */
.tab-panel {
  display: none !important;
}
.tab-panel.active-tab-panel {
  display: flex !important;
  flex-direction: column !important;
  gap: 1.5rem !important;
  width: 100% !important;
}
#tab-nav-report:checked ~ .tab-panels > .panel-report {
  display: flex !important;
  flex-direction: column !important;
  gap: 1.5rem !important;
  width: 100% !important;
}
#tab-nav-market:checked ~ .tab-panels > .panel-market {
  display: flex !important;
  flex-direction: column !important;
  gap: 1.5rem !important;
  width: 100% !important;
}
#tab-nav-trades:checked ~ .tab-panels > .panel-trades {
  display: flex !important;
  flex-direction: column !important;
  gap: 1.5rem !important;
  width: 100% !important;
}
.market-hero-card {
  margin-top: 0.5rem;
}
.market-specs-panel {
  background: var(--card-bg, #111827);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 8px);
  overflow: hidden;
  margin-bottom: 1rem;
}
.market-spec-hero {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: var(--track, rgba(255, 255, 255, 0.02));
}
.market-spec-hero-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text, #f9fafb);
  display: flex;
  align-items: center;
  gap: 8px;
}
.market-spec-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: var(--border, rgba(255, 255, 255, 0.08));
}
.market-spec-item {
  background: var(--card-bg, #111827);
  padding: 11px 16px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: none !important;
  transform: none !important;
  cursor: default !important;
}
.market-spec-item:hover {
  transform: none !important;
  box-shadow: none !important;
  border-color: transparent !important;
}
.market-spec-label {
  font-family: var(--mono, monospace);
  font-size: 10.5px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted, #9ca3af);
}
.market-spec-val {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text, #f9fafb);
  line-height: 1.25;
}
.market-hero-card .stat-tile,
.market-hero-card .stat-tile:hover {
  transform: none !important;
  transition: none !important;
  box-shadow: none !important;
  cursor: default !important;
}
#cach-choi {
  grid-column: 1 / -1 !important;
  width: 100% !important;
}
#cach-choi .table-scroll {
  width: 100% !important;
  overflow-x: auto !important;
  margin-top: 1rem;
}
#cach-choi table {
  width: 100% !important;
  min-width: 780px;
  border-collapse: collapse;
}
#cach-choi th, #cach-choi td {
  padding: 11px 14px !important;
  font-size: 13px !important;
  vertical-align: middle !important;
}
#cach-choi th {
  background: var(--track, rgba(255, 255, 255, 0.04)) !important;
  font-family: var(--mono, monospace) !important;
  font-size: 11px !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  color: var(--muted, #9ca3af) !important;
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.1)) !important;
}
#cach-choi td {
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.06)) !important;
}

/* Horizontal parameter list (Drawdown vs. capital & Open-position audit) */
.param-horizontal-list {
  background: var(--card-bg, #111827);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 8px);
  overflow: hidden;
  margin: 0.75rem 0 1.25rem;
}
.param-horizontal-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.06));
}
.param-horizontal-row:last-child {
  border-bottom: none;
}
.param-horizontal-name {
  font-family: var(--mono, monospace);
  font-size: 11.5px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted, #9ca3af);
  display: flex !important;
  align-items: center !important;
  flex: 0 0 340px !important;
  max-width: 340px !important;
}
.param-horizontal-name .metric-label-row {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  width: 100% !important;
  gap: 8px !important;
}
.param-horizontal-name .metric-label-row .param-label {
  flex: 1 1 auto !important;
  text-align: left !important;
}
.param-horizontal-name .metric-label-row .formula-star-btn {
  flex: 0 0 16px !important;
  width: 16px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  margin-left: auto !important;
  margin-right: 4px !important;
  text-align: center !important;
  color: var(--accent, #38BDF8) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
}
.param-horizontal-val {
  font-family: var(--mono, monospace);
  font-size: 14px;
  font-weight: 700;
  color: var(--text, #f9fafb);
  text-align: right;
  margin-left: auto;
}

/* Metric label row for inline alignment of formula stars */
.metric-label-row {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  width: 100% !important;
  gap: 4px !important;
}
.metric-label-row .param-label,
.metric-label-row .metric-name {
  flex: 1 1 auto;
  text-align: left;
}
.metric-label-row .formula-star-btn {
  flex: 0 0 auto;
  margin-left: auto !important;
  margin-right: 4px !important;
}

#so-lieu table td:first-child .metric-label-row,
#suy-luan table td:first-child .metric-label-row {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  width: 100% !important;
}
#so-lieu table td:first-child .metric-label-row .param-label,
#suy-luan table td:first-child .metric-label-row .param-label {
  flex: 1 1 auto !important;
  text-align: left !important;
}
#so-lieu table td:first-child .metric-label-row .formula-star-btn,
#suy-luan table td:first-child .metric-label-row .formula-star-btn {
  flex: 0 0 16px !important;
  width: 16px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  margin-left: auto !important;
  margin-right: 4px !important;
  text-align: center !important;
  color: var(--accent, #38BDF8) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
}

/* Drawdown vs. capital & Most recent closed trades full width */
#sut-giam-von,
#danh-sach-lenh {
  grid-column: 1 / -1 !important;
  width: 100% !important;
}
#sut-giam-von .table-scroll,
#danh-sach-lenh .table-scroll {
  width: 100% !important;
  overflow-x: auto !important;
}

/* Metric tables in Trade metrics and Statistical inference */
#so-lieu table,
#suy-luan table {
  width: 100% !important;
  table-layout: fixed !important;
}
#so-lieu table th:first-child,
#so-lieu table td:first-child,
#suy-luan table th:first-child,
#suy-luan table td:first-child {
  width: 68% !important;
}
#so-lieu table th:last-child,
#so-lieu table td:last-child,
#suy-luan table th:last-child,
#suy-luan table td:last-child {
  width: 32% !important;
  text-align: right !important;
}

/* Locked Feature Card for User Role */
.card-locked {
  background: linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(15, 23, 42, 0.92)) !important;
  border: 1px solid rgba(56, 189, 248, 0.25) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
  border-radius: var(--radius-md, 8px) !important;
  padding: 36px 32px !important;
  margin: 20px 0 !important;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.card-locked::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #38BDF8, #818CF8, transparent);
}
.locked-card-container {
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.locked-badge-row {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.locked-status-badge {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 4px 12px;
  border-radius: 9999px;
  background: rgba(245, 158, 11, 0.15);
  color: #F59E0B;
  border: 1px solid rgba(245, 158, 11, 0.35);
}
.locked-plan-badge {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 4px 12px;
  border-radius: 9999px;
  background: rgba(56, 189, 248, 0.15);
  color: #38BDF8;
  border: 1px solid rgba(56, 189, 248, 0.35);
}
.locked-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text, #F9FAFB);
  margin: 0 0 10px 0;
  letter-spacing: -0.01em;
}
.locked-subtitle {
  font-size: 14px;
  color: var(--muted, #9CA3AF);
  margin: 0 0 24px 0;
  line-height: 1.6;
}
.locked-features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  width: 100%;
  margin-bottom: 28px;
  text-align: left;
}
.locked-feature-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s ease;
}
.locked-feature-item:hover {
  border-color: rgba(56, 189, 248, 0.3);
}
.locked-feature-title {
  font-size: 13px;
  font-weight: 700;
  color: #E2E8F0;
  margin-bottom: 6px;
}
.locked-feature-desc {
  font-size: 12px;
  color: #94A3B8;
  line-height: 1.5;
}
.locked-action-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  width: 100%;
}
.locked-note {
  font-size: 13px;
  color: var(--muted, #9CA3AF);
  max-width: 560px;
  line-height: 1.6;
  margin: 0 !important;
}
.btn-upgrade-plan {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #0284C7, #2563EB);
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  padding: 11px 26px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
}
.btn-upgrade-plan:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
}
.tab-label-locked {
  opacity: 0.9;
}
.tab-label-locked .tab-icon {
  filter: drop-shadow(0 0 3px rgba(245, 158, 11, 0.8));
}

/* Traded assets 5-row view limit with vertical scroll */
#tai-san .table-scroll {
  max-height: 275px !important;
  overflow-y: auto !important;
}
#tai-san thead th {
  position: sticky !important;
  top: 0 !important;
  z-index: 2 !important;
  background: var(--track, #1e293b) !important;
}
.market-hero-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}
/* "Bằng chứng trạng thái" và "So sánh hiệu suất" trả lời hai câu khác nhau
   nhưng cùng cấp -- xếp NGANG HÀNG bằng CSS Grid trên tablet+ thay vì luôn
   xếp chồng dọc như trước (mục "so sánh" vốn có thể vắng mặt, `auto-fit`
   tự co về 1 cột khi chỉ có 1 khối, không cần CSS riêng cho trường hợp
   đó). */
.market-boxes {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  margin-top: 1rem;
}
.market-evidence-box, .market-comparison-box {
  padding: 0.75rem 1rem;
  background: var(--track);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  min-width: 0;
}
.market-evidence-box h4, .market-comparison-box h4 {
  margin: 0 0 0.4rem;
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--text);
}
.badge-win {
  display: inline-block;
  background: rgba(16, 185, 129, 0.14);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
  font-family: var(--mono);
  font-weight: 700;
  font-size: 0.75rem;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
}
.badge-loss {
  display: inline-block;
  background: rgba(239, 68, 68, 0.14);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  font-family: var(--mono);
  font-weight: 700;
  font-size: 0.75rem;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
}
.text-profit {
  color: #10b981;
  font-family: var(--mono);
  font-weight: 600;
}
.text-loss {
  color: #ef4444;
  font-family: var(--mono);
  font-weight: 600;
}
.mono-symbol {
  font-family: var(--mono);
  font-size: 11.5px;
  font-weight: 700;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.25);
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.03em;
}
.okx-trades-table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
  font-size: 12.5px;
  font-family: var(--font, system-ui, sans-serif);
}
.okx-trades-table thead th {
  background: var(--surface-2, rgba(255, 255, 255, 0.03));
  color: var(--muted, #94a3b8);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  position: sticky;
  top: 0;
  z-index: 2;
}
.okx-trades-table tbody td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.05));
  font-variant-numeric: tabular-nums;
}
.okx-trades-table tbody tr {
  transition: background 0.15s ease;
}
.okx-trades-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.04);
}
.table-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
  padding: 10px 14px;
  background: var(--surface-2, rgba(255, 255, 255, 0.02));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.06));
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--muted, #94a3b8);
}
.pagination-info {
  font-variant-numeric: tabular-nums;
}
.pagination-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pagination-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 30px;
  padding: 0 10px;
  background: var(--surface, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
  border-radius: 6px;
  color: var(--text, #e2e8f0);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.pagination-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.35);
  color: #60a5fa;
}
.pagination-btn.active {
  background: #2563eb;
  border-color: #3b82f6;
  color: #ffffff;
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
}
.pagination-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
#rich-formula-tooltip {
  position: fixed !important;
  z-index: 99999 !important;
  pointer-events: none !important;
  max-width: 400px !important;
  background: rgba(15, 23, 42, 0.96) !important;
  backdrop-filter: blur(20px) saturate(180%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
  border: 1px solid rgba(56, 189, 248, 0.22) !important;
  border-radius: 12px !important;
  padding: 13px 16px !important;
  box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.06), 0 4px 12px rgba(0, 0, 0, 0.5) !important;
  color: #f1f5f9 !important;
  font-size: 12.5px !important;
  line-height: 1.55 !important;
  opacity: 0 !important;
  transform: translateY(6px) scale(0.98) !important;
  transition: opacity 0.16s cubic-bezier(0.16, 1, 0.3, 1), transform 0.16s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
#rich-formula-tooltip.is-visible {
  opacity: 1 !important;
  transform: translateY(0) scale(1) !important;
}
#rich-formula-tooltip .rich-tip-header {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  margin-bottom: 9px !important;
  padding-bottom: 8px !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}
#rich-formula-tooltip .rich-tip-icon {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 22px !important;
  height: 22px !important;
  font-size: 12px !important;
  border-radius: 6px !important;
  background: rgba(56, 189, 248, 0.12) !important;
  border: 1px solid rgba(56, 189, 248, 0.28) !important;
  flex-shrink: 0 !important;
}
#rich-formula-tooltip .rich-tip-title {
  font-weight: 700 !important;
  font-size: 13.5px !important;
  letter-spacing: -0.01em !important;
  color: #38bdf8 !important;
}
#rich-formula-tooltip .rich-tip-formula-box {
  background: rgba(8, 14, 26, 0.85) !important;
  border: 1px solid rgba(56, 189, 248, 0.2) !important;
  border-left: 3px solid #38bdf8 !important;
  border-radius: 7px !important;
  padding: 8px 11px !important;
  font-family: var(--mono, 'JetBrains Mono', monospace) !important;
  font-size: 11.5px !important;
  line-height: 1.55 !important;
  color: #a7f3d0 !important;
  margin-bottom: 10px !important;
  word-break: break-word !important;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.3) !important;
}
#rich-formula-tooltip .rich-tip-formula-box strong,
#rich-formula-tooltip .rich-tip-formula-label {
  color: #38bdf8 !important;
  font-weight: 700 !important;
  margin-right: 5px !important;
}
#rich-formula-tooltip .rich-tip-formula-code {
  color: #34d399 !important;
  font-weight: 600 !important;
}
#rich-formula-tooltip .rich-tip-desc {
  color: #cbd5e1 !important;
  font-size: 12px !important;
  line-height: 1.55 !important;
}
#rich-formula-tooltip .rich-tip-footer {
  margin-top: 8px !important;
  font-size: 10.5px !important;
  color: #94a3b8 !important;
  display: flex !important;
  align-items: center !important;
  gap: 4px !important;
}

/* Harmonious Light Mode Overrides */
#rich-formula-tooltip.theme-light,
#rich-formula-tooltip[data-theme="light"],
:root[data-theme="light"] #rich-formula-tooltip {
  background: rgba(255, 255, 255, 0.98) !important;
  border: 1px solid #cbd5e1 !important;
  box-shadow: 0 18px 40px -8px rgba(15, 23, 42, 0.16), 0 4px 12px -2px rgba(15, 23, 42, 0.06), 0 0 0 1px rgba(226, 232, 240, 0.9) !important;
  color: #0f172a !important;
}
#rich-formula-tooltip.theme-light .rich-tip-header,
#rich-formula-tooltip[data-theme="light"] .rich-tip-header,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-header {
  border-bottom: 1px solid #e2e8f0 !important;
}
#rich-formula-tooltip.theme-light .rich-tip-icon,
#rich-formula-tooltip[data-theme="light"] .rich-tip-icon,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-icon {
  background: rgba(2, 132, 199, 0.08) !important;
  border: 1px solid rgba(2, 132, 199, 0.25) !important;
  color: #0284c7 !important;
}
#rich-formula-tooltip.theme-light .rich-tip-title,
#rich-formula-tooltip[data-theme="light"] .rich-tip-title,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-title {
  color: #0284c7 !important;
}
#rich-formula-tooltip.theme-light .rich-tip-formula-box,
#rich-formula-tooltip[data-theme="light"] .rich-tip-formula-box,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-formula-box {
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-left: 3px solid #0284c7 !important;
  color: #065f46 !important;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.03) !important;
}
#rich-formula-tooltip.theme-light .rich-tip-formula-box strong,
#rich-formula-tooltip.theme-light .rich-tip-formula-label,
#rich-formula-tooltip[data-theme="light"] .rich-tip-formula-box strong,
#rich-formula-tooltip[data-theme="light"] .rich-tip-formula-label,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-formula-box strong,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-formula-label {
  color: #0284c7 !important;
}
#rich-formula-tooltip.theme-light .rich-tip-formula-code,
#rich-formula-tooltip[data-theme="light"] .rich-tip-formula-code,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-formula-code {
  color: #047857 !important;
  font-weight: 600 !important;
}
#rich-formula-tooltip.theme-light .rich-tip-desc,
#rich-formula-tooltip[data-theme="light"] .rich-tip-desc,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-desc {
  color: #334155 !important;
}
#rich-formula-tooltip.theme-light .rich-tip-footer,
#rich-formula-tooltip[data-theme="light"] .rich-tip-footer,
:root[data-theme="light"] #rich-formula-tooltip .rich-tip-footer {
  color: #64748b !important;
}
.card-hint {
  margin-top: 0.85rem;
  padding: 0.75rem 1rem;
  background: var(--track);
  border-left: 3px solid var(--primary-accent);
  border-radius: 6px;
  font-size: var(--font-size-sm);
  color: var(--muted);
  line-height: 1.55;
}

/* --- Điểm ngắt bố cục -----------------------------------------------------
   Chữ đã co giãn liên tục bằng clamp() (xem tokens.css) nên các mốc dưới đây
   chỉ đổi BỐ CỤC thật sự: số cột, rail trái nằm trên hay nằm bên. */

/* Điện thoại nhỏ: bớt đệm để không lãng phí bề ngang ít ỏi cho khoảng trắng. */
/* Điện thoại: mục lục 13 dòng đứng trước nội dung là 13 dòng phải cuộn qua
   trước khi đọc được chữ đầu tiên -- trên một cột hẹp nó tốn nhiều hơn nó
   giúp, nên ẩn hẳn (từ 640px trở lên nó xếp 3 cột ngang, rẻ chỗ, nên giữ). */
@media (max-width: 639px) {
  .nav { display: none; }
}

@media (max-width: 480px) {
  .block-b { padding: 12px 12px 14px; }
  .block-h { padding: 10px 12px; }
  .stat-tile, .horizon-card { padding: 11px 12px; }
  .stat-tile-hero .stat-value { font-size: 28px; }
}

/* Tablet: rail trái vẫn nằm trên cùng nhưng xếp ngang (danh tính | điểm số |
   mục lục) thay vì chồng dọc lãng phí chiều cao; hai khối trong tab thị
   trường nằm cạnh nhau. */
@media (min-width: 640px) {
  .side { padding: 20px 16px; }
  .side-identity {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.7fr);
    gap: 1.5rem;
    align-items: center;
  }
  .side-foot { margin-top: 0; }
  .side-identity .cards { margin-top: 0; grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .side-identity .stat-tile-hero { border-left: none; border-top: 3px solid var(--tile-accent, var(--border)); }
  .nav { flex-direction: row; flex-wrap: wrap; gap: 1.5rem; }
  .nav-group { flex: 1 1 200px; margin-bottom: 0; }
  .market-boxes {
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  }
}

/* Màn hình rộng: bố cục toàn màn hình gọn đẹp */
@media (min-width: 1100px) {
  .page {
    display: block;
    width: 100%;
    min-height: 100vh;
  }
  .side {
    display: none !important;
  }
  .main { max-width: 1560px; margin: 0 auto; padding: 24px 30px 60px; }
  .stat-row, .horizon-row { gap: 1px; }

  /* Phản hồi thị giác thật: "toàn trang là các thẻ xếp dọc liên tục, không
     nhịp điệu, cuộn rất dài". Mỗi tab vẫn giữ NGUYÊN số mục và thứ tự mục
     (comment này tránh gõ lại nguyên văn một tiêu đề mục nào -- xem lý do ở
     comment phía trên `.card-primary`), chỉ đổi CÁCH XẾP trên màn rộng:
     mặc định MỌI mục vẫn chiếm TRỌN bề ngang, chỉ những mục đã được xác
     nhận đủ ngắn mới ghép đôi qua `.card-pair` (`_section(..., pair=True)`). */
  .tab-panel.active-tab-panel,
  #tab-nav-report:checked ~ .tab-panels > .panel-report,
  #tab-nav-market:checked ~ .tab-panels > .panel-market,
  #tab-nav-trades:checked ~ .tab-panels > .panel-trades {
    display: flex !important;
    flex-direction: column !important;
    gap: 1.25rem !important;
    align-items: stretch !important;
    width: 100% !important;
  }
  .tab-panel > .card { margin-top: 0; width: 100% !important; max-width: 100% !important; grid-column: 1 / -1 !important; }
  .tab-panel > .card.card-pair,
  .tab-panel > #nhan-dinh, .tab-panel > #diem-chieu,
  .tab-panel > #thi-truong-chinh, .tab-panel > #thi-truong,
  .tab-panel > #so-lieu, .tab-panel > #vi-the-mo,
  .tab-panel > #suy-luan, .tab-panel > #tai-san,
  .tab-panel > #tang-truong { width: 100% !important; max-width: 100% !important; grid-column: 1 / -1 !important; }
}

/* Màn rất rộng: ô số và mục ghép có thêm chỗ, tăng khoảng thở như nora. */
/* Quick Risk Metrics Strip (Tầng 1) */
.quick-risk-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  margin: 14px 0 16px 0;
  padding: 12px 14px;
  background: var(--surface-2, rgba(255,255,255,0.02));
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 8px;
}
.qrs-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px;
  background: var(--surface, rgba(255,255,255,0.03));
  border-radius: 6px;
  border-left: 3px solid var(--border, #475569);
}
.qrs-item.qrs-danger {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.07);
}
.qrs-item.qrs-warn {
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.07);
}
.qrs-item.qrs-safe {
  border-left-color: #10b981;
  background: rgba(16, 185, 129, 0.07);
}
.qrs-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted, #94a3b8);
}
.qrs-value {
  font-family: var(--mono, monospace);
  font-size: 14px;
  font-weight: 700;
  color: var(--ink, #ffffff);
}
.qrs-danger .qrs-value { color: #ef4444; }
.qrs-warn .qrs-value { color: #f59e0b; }
.qrs-safe .qrs-value { color: #10b981; }

/* Verdict Action Directive Callout */
.verdict-action-callout {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.verdict-action-callout.action-danger {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
}
.verdict-action-callout.action-warning {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.35);
}
.verdict-action-callout.action-success {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
}
.action-callout-badge {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.action-danger .action-callout-badge { color: #f87171; }
.action-warning .action-callout-badge { color: #fbbf24; }
.action-success .action-callout-badge { color: #34d399; }
.action-callout-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--ink, #e2e8f0);
}

/* Unified Monte Carlo Multi-Horizon Panel (Tầng 4) */
.mc-unified-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
  background: var(--surface, rgba(255,255,255,0.02));
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 8px;
  padding: 16px 18px;
}
:root[data-theme="light"] .mc-unified-panel {
  background: var(--panel, #ffffff);
  border: 1px solid var(--line, #e2e8f0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.mc-unified-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.06));
  padding-bottom: 10px;
}
:root[data-theme="light"] .mc-unified-header {
  border-bottom-color: var(--line, #e2e8f0);
}
.mc-unified-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink, #ffffff);
}
:root[data-theme="light"] .mc-unified-title {
  color: var(--ink, #0f172a);
}
.mc-unified-subtitle {
  font-size: 11px;
  color: var(--muted, #94a3b8);
  margin-top: 3px;
}
:root[data-theme="light"] .mc-unified-subtitle {
  color: var(--ink-3, #64748b);
}
.mc-unified-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.mc-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--muted, #94a3b8);
}
:root[data-theme="light"] .mc-legend-item {
  color: var(--ink-2, #475569);
}
.mc-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.mc-unified-svg {
  width: 100%;
  max-width: 820px;
  height: auto;
  display: block;
  margin: 0 auto;
}

/* Parameter glossary (* notes) below the Outcome distribution chart */
.mc-param-notes {
  margin: 10px 0 4px;
  padding: 10px 14px;
  border-top: 1px solid var(--border, rgba(255,255,255,0.08));
}
:root[data-theme="light"] .mc-param-notes {
  border-top: 1px solid var(--line, #e2e8f0);
}
.mc-param-notes-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 16px;
  align-items: baseline;
}
.mc-param-note-item {
  display: contents; /* lets children sit in the parent grid */
}
.mc-param-star {
  font-size: 10.5px;
  font-family: var(--mono, 'SFMono-Regular', monospace);
  font-weight: 700;
  white-space: nowrap;
  color: var(--accent, #818cf8);
  padding-right: 4px;
}
:root[data-theme="light"] .mc-param-star {
  color: var(--accent-dark, #4f46e5);
}
.mc-param-desc {
  font-size: 10.5px;
  color: var(--muted, #94a3b8);
  line-height: 1.55;
}
:root[data-theme="light"] .mc-param-desc {
  color: var(--ink-2, #475569);
}

/* Percentile Spectrum (Tầng Monte Carlo) */
.mc-spec-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
  background: var(--surface, rgba(255,255,255,0.02));
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 8px;
  padding: 16px 18px;
}
:root[data-theme="light"] .mc-spec-panel {
  background: var(--panel, #ffffff);
  border: 1px solid var(--line, #e2e8f0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.mc-spec-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.06));
  padding-bottom: 10px;
}
:root[data-theme="light"] .mc-spec-header {
  border-bottom-color: var(--line, #e2e8f0);
}
.mc-spec-title {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink, #ffffff);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
:root[data-theme="light"] .mc-spec-title {
  color: var(--ink, #0f172a);
}
.mc-spec-subtitle {
  font-size: 11px;
  color: var(--muted, #94a3b8);
  margin-top: 3px;
}
:root[data-theme="light"] .mc-spec-subtitle {
  color: var(--ink-3, #64748b);
}
.mc-skew-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--mono, monospace);
}
.mc-skew-badge.positive {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.35);
}
:root[data-theme="light"] .mc-skew-badge.positive {
  background: #ecfdf5;
  color: #059669;
  border-color: #a7f3d0;
}
.mc-skew-badge.negative {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.35);
}
:root[data-theme="light"] .mc-skew-badge.negative {
  background: #fef2f2;
  color: #dc2626;
  border-color: #fecaca;
}
.mc-skew-badge.balanced {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.35);
}
:root[data-theme="light"] .mc-skew-badge.balanced {
  background: #fffbeb;
  color: #d97706;
  border-color: #fde68a;
}
.mc-spec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  margin-top: 4px;
}
.mc-spec-card {
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.06));
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
:root[data-theme="light"] .mc-spec-card {
  background: var(--panel-2, #f8fafc);
  border: 1px solid var(--line, #e2e8f0);
}
.mc-spec-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
}
.mc-spec-lbl {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-2, #cbd5e1);
  font-family: var(--mono, monospace);
}
:root[data-theme="light"] .mc-spec-lbl {
  color: var(--ink-2, #475569);
}
.mc-spec-sub {
  font-size: 9.5px;
  color: var(--muted, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
:root[data-theme="light"] .mc-spec-sub {
  color: var(--ink-3, #64748b);
}
.mc-spec-val {
  font-size: 15px;
  font-weight: 700;
  font-family: var(--mono, monospace);
  letter-spacing: -0.02em;
}
/* Multi-horizon matrix expanded columns */
.hz-matrix-table .col-med {
  text-align: right;
  font-family: var(--mono, monospace);
  font-size: 12px;
  white-space: nowrap;
}
.hz-matrix-table .col-range {
  text-align: center;
  font-family: var(--mono, monospace);
  font-size: 11px;
  white-space: nowrap;
  color: var(--ink-2, #cbd5e1);
}
:root[data-theme="light"] .hz-matrix-table .col-range {
  color: var(--ink-2, #475569);
}
.hz-matrix-table .col-dd {
  text-align: right;
  font-family: var(--mono, monospace);
  font-size: 12px;
  white-space: nowrap;
}
.hz-range-val {
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}
:root[data-theme="light"] .hz-range-val {
  background: var(--panel-2, #f1f5f9);
  border-color: var(--line, #e2e8f0);
  color: var(--ink, #0f172a);
}
"""


# --------------------------------------------------------------------------- #
# Snapshot timestamp banner -- see Agent/backend/web/snapshot.py's module
# docstring for the caching feature this displays. Vietnam runs UTC+7 with no
# DST, so a fixed offset is all this ever needs (no zoneinfo/tz database
# dependency, matching this module's own "no new dependency" constraint).
# --------------------------------------------------------------------------- #

_VN_TZ = timezone(timedelta(hours=7))


def _format_vn_timestamp(snapshot_at_ms: int) -> str:
    dt = datetime.fromtimestamp(snapshot_at_ms / 1000, tz=_VN_TZ)
    return dt.strftime("%H:%M:%S %d/%m/%Y")


def _render_snapshot_banner(
    snapshot_at_ms: Optional[int],
    refresh_url: Optional[str],
    *,
    is_stale: bool = False,
) -> str:
    """One line at the very top of the page telling a reader EXACTLY when
    this analysis was captured -- not a decorative detail (see the task this
    was written for): `GET /bot/<code>`/`GET /<userref>_<code>` can now be
    served from a Redis snapshot up to 24h old
    (Agent/backend/web/snapshot.py) OR from this bot's own already-scored
    `assessment.json` on disk (no built-in expiry -- see `app.py`'s
    `_bot_report_response`/`data.py`'s `find_scored_report`), so a reader
    must never be left guessing whether they are looking at a fresh view or
    an old one. The "Phân tích lại" link (when `refresh_url` is given)
    always points back at THIS SAME page with `?refresh=1` appended, forcing
    a fresh analysis -- see app.py's `_bot_report_response` for why that
    link still costs the same rate-limit quota an ordinary analysis would.

    `is_stale` (default `False`, same backward-compatible pattern as every
    other parameter here) adds one extra clause to the same line rather than
    a whole separate notice -- a days-old on-disk assessment is still the
    real, current verdict for that bot (nothing here claims otherwise), it
    is simply worth telling a reader exactly how old the picture is so they
    can decide for themselves whether to click "Phân tích lại".

    Omitted entirely when the caller passes no timestamp at all (`None`,
    the default) -- every pre-existing direct call to
    `render_bot_report_html` in this module's own test suite keeps getting
    byte-for-byte the same page as before this parameter existed, same
    backward-compatible default pattern as `is_admin` above.
    """
    if snapshot_at_ms is None:
        return ""
    when = _esc(_format_vn_timestamp(snapshot_at_ms))
    refresh_link = (
        f'<a href="{_esc(refresh_url)}">Re-analyze</a>' if refresh_url else ""
    )
    stale_clause = (
        ' · <span class="snapshot-stale">snapshot is stale (over 24 hours old)</span>'
        if is_stale
        else ""
    )
    return (
        '<div class="snapshot-banner">'
        '<span class="snapshot-badge">SNAPSHOT</span>'
        '<span class="snapshot-text">'
        f"Snapshot taken at: <strong>{when}</strong> (Vietnam time, GMT+7){stale_clause}"
        "</span>"
        f'<span class="snapshot-actions">{refresh_link}</span>'
        "</div>"
    )


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def render_bot_report_html(
    result: Dict[str, Any],
    *,
    is_admin: bool = False,
    admin_back_url: str = "/#/admin",
    snapshot_at_ms: Optional[int] = None,
    refresh_url: Optional[str] = None,
    is_stale: bool = False,
    hidden_panels: Sequence[str] = (),
) -> str:
    """Render the full standalone HTML page for one `/api/analyze`-shaped
    result dict (see `WebDataService.analyze`'s contract). Never raises on a
    malformed/partial `result` -- every field access below goes through
    `.get()` with a safe default, matching the task's own "no KeyError, hide
    the section instead" requirement.

    `is_admin` (default `False`, so every pre-existing caller is unaffected)
    adds ONE extra strip at the very top of the page -- an "ADMIN" badge and
    a link back to `admin_back_url` -- and changes NOTHING else: the task's
    own explicit rule is that a viewer's role may change NAVIGATION only,
    never a single word of the analysis itself. Callers that never pass
    `is_admin` keep getting byte-for-byte the same page as before this
    parameter existed.

    `snapshot_at_ms`/`refresh_url`/`is_stale` (default `None`/`None`/`False`,
    same backward-compatible pattern) add a second strip -- see
    `_render_snapshot_banner` -- showing when this particular render was
    captured, whether it is now considered stale (>24h old), and, when
    `refresh_url` is given, a "Phân tích lại" link. Also navigation-only:
    none of the three touches the analysis sections below.
    """
    if not isinstance(result, dict):
        result = {}
    status = result.get("status")
    name = result.get("name") or result.get("code") or "Bot"

    sidebar_html = ""
    if status == "NOT_FOUND":
        body = _render_not_found_body(result)
        title = f"Nora - Risk Management · Not found · {name}"
    else:
        header_html, side_blocks = _render_header(result)
        tab1_content = _render_tab_report(result)
        tab2_content = _render_tab_market(result)
        tab3_content = _render_tab_trades(result)
        tabs_html = _render_tabs_wrapper(
            tab1_content, tab2_content, tab3_content, hidden_panels=hidden_panels
        )
        body = f"{header_html}{tabs_html}"
        if not (tab1_content or tab2_content or tab3_content):
            # Nuốt lặng lẽ: một `result` HỢP LỆ mà cả ba tab ra rỗng thì
            # người đọc nhận về trang "không tìm thấy" y hệt trường hợp mã
            # bot sai, và không còn dấu vết nào để lần. Đã cắn thật: ngày
            # 19/09 ba test render đỏ đúng kiểu này trong MỘT lượt chạy suite
            # rồi không tái hiện được ở hai lượt sau -- không có dòng log nào
            # để biết tab nào rỗng hay vì sao. Ghi lại đủ để lần sau chẩn
            # đoán được ngay, không đổi thứ người dùng nhìn thấy.
            logger.warning(
                "Bot report degraded to the not-found body although the result "
                "was usable: code=%r status=%r has_evidence=%s tabs=(%d,%d,%d)",
                result.get("code"),
                status,
                isinstance(result.get("evidence"), dict)
                and bool(result.get("evidence")),
                len(tab1_content or ""),
                len(tab2_content or ""),
                len(tab3_content or ""),
            )
            body = _render_not_found_body(result)
        else:
            nav_html = _render_nav(
                tab1_content,
                "" if "panel-market" in set(hidden_panels) else tab2_content,
                "" if "panel-trades" in set(hidden_panels) else tab3_content,
            )
            sidebar_html = _render_sidebar(side_blocks, nav_html)
        title = f"Nora - Risk Management · {name}"

    footer = (
        '<footer class="report-footer">Automated assessment based on public'
        " OKX copy-trading data. THIS IS NOT investment advice. Readers are"
        " solely responsible for their own decisions.</footer>"
    )

    role_capsule = (
        '<div class="user-badge-capsule">'
        '<span class="user-badge-pulse"></span>'
        '<span class="user-badge-label">USER</span>'
        '</div>'
    )

    top_header = (
        '<header class="top-header">'
        '<div class="header-left">'
        '<a href="/#/admin?tab=overview" class="brand">'
        '<div class="brand-logo-box">'
        '<div class="brand-logo-grid">'
        '<span class="grid-sq sq-1"></span>'
        '<span class="grid-sq sq-2"></span>'
        '<span class="grid-sq sq-3"></span>'
        '<span class="grid-sq sq-4"></span>'
        '</div>'
        '</div>'
        '<div class="brand-title-wrap">'
        '<div class="brand-name-row">'
        '<span class="brand-name">NORABT</span>'
        '<span class="brand-badge-fintech">AI ENGINE</span>'
        '</div>'
        '<span class="brand-sub">OKX QUANT RISK PROTOCOL</span>'
        '</div>'
        '</a>'
        '<div class="header-divider"></div>'
        '<nav class="header-nav-tabs">'
        '<a href="/#/admin?tab=overview" class="header-tab">'
        '<span class="tab-glyph glyph-overview"></span>'
        '<span>Overview</span>'
        '</a>'
        '<a href="/#/admin?tab=bots" class="header-tab on">'
        '<span class="tab-glyph glyph-bots"></span>'
        '<span>Bot list</span>'
        '</a>'
        '<a href="/#/admin?tab=analyze" class="header-tab">'
        '<span class="tab-glyph glyph-analyze"></span>'
        '<span>Assess bot</span>'
        '</a>'
        '</nav>'
        '</div>'
        '<div class="top-bar-actions">'
        '<a href="/#/admin?tab=analyze" class="btn-header-cta" title="Assess a new bot">'
        '<span class="btn-cta-plus">+</span>'
        '<span class="btn-header-cta-text">Assess bot</span>'
        '</a>'
        f'{role_capsule}'
        '<button type="button" class="theme-btn theme-toggle-btn" id="theme-toggle-btn" aria-label="Switch Light/Dark mode" title="Switch Light/Dark theme">'
        '<span class="theme-icon theme-icon-light">☀️ Light</span>'
        '<span class="theme-icon theme-icon-dark">🌙 Dark</span>'
        '</button>'
        '</div>'
        '</header>'
    )

    admin_banner = (
        (
            '<div class="admin-banner">'
            f'<a href="{_esc(admin_back_url)}" class="back-link">← Back to bot list</a>'
            '<span class="admin-badge">ADMIN</span>'
            "</div>"
        )
        if is_admin
        else ""
    )
    snapshot_banner = _render_snapshot_banner(
        snapshot_at_ms, refresh_url, is_stale=is_stale
    )

    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">\n'
        f"<title>{_esc(title)}</title>\n"
        f"<style>{_design_tokens_css_text()}\n{_CSS}</style>\n"
        "</head>\n<body>\n"
        f"{top_header}"
        f'<div class="page">{sidebar_html}'
        f'<div class="main">{admin_banner}{snapshot_banner}{body}{footer}</div>'
        "</div>\n"
        f"{_RUNTIME_SCRIPT}\n"
        "</body>\n</html>\n"
    )


_FORMULA_MODAL_HTML = ""


_RUNTIME_SCRIPT = (
    '<script id="report-runtime">\n'
    f'window.METRIC_INFO = {json.dumps(METRIC_FORMULA_INFO, ensure_ascii=False)};\n'
    """window.openFormulaModal = function(key) {};
window.closeFormulaModal = function() {};
(function() {
  try {
    // Chuyển tiếp mượt mà vào SPA để giữ header cố định, không load lại trang
    if (window.location.pathname.startsWith('/bot/') || /^\\/[a-zA-Z0-9]+_[a-zA-Z0-9]+$/.test(window.location.pathname)) {
      var seg = window.location.pathname.replace(/^\\/bot\\//, '').replace(/^\\/[^_]+_/, '');
      if (seg && !window.location.hash) {
        window.location.replace('/#/admin?tab=bot&code=' + seg);
        return;
      }
    }
    var root = document.documentElement;
    var themeKey = 'norabt_theme';
    var saved = localStorage.getItem(themeKey);
    if (saved === 'dark' || saved === 'light') {
      root.setAttribute('data-theme', saved);
    }
    var btn = document.getElementById('theme-toggle-btn');
    if (btn) {
      btn.addEventListener('click', function() {
        var current = root.getAttribute('data-theme');
        var isDark = current === 'dark' || (!current && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
        var next = isDark ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem(themeKey, next); } catch (e) {}
      });
    }
    var hash = (window.location.hash || '').toLowerCase();
    if (hash === '#market' || hash === '#thitruong' || hash === '#thi-truong') {
      var r = document.getElementById('tab-nav-market');
      if (r) r.checked = true;
    } else if (hash === '#trades' || hash === '#lenh' || hash === '#tradelist' || hash === '#vi-the') {
      var r = document.getElementById('tab-nav-trades');
      if (r) r.checked = true;
    } else if (hash === '#report' || hash === '#baocao' || hash === '#bao-cao') {
      var r = document.getElementById('tab-nav-report');
      if (r) r.checked = true;
    }
    // Mục lục cột trái trỏ tới các mục nằm trong CẢ BA tab; một anchor thuộc
    // tab đang đóng thì cuộn tới cũng vô nghĩa (panel đang display:none), nên
    // mỗi link tự bật đúng tab của nó trước rồi mới cuộn.
    var navLinks = document.querySelectorAll('.nav a[data-tab]');
    Array.prototype.forEach.call(navLinks, function(a) {
      a.addEventListener('click', function(ev) {
        var tab = a.getAttribute('data-tab');
        var radio = document.getElementById('tab-nav-' + tab);
        if (radio && !radio.checked) { radio.checked = true; }
        var id = (a.getAttribute('href') || '').slice(1);
        var target = id ? document.getElementById(id) : null;
        if (target) {
          ev.preventDefault();
          target.scrollIntoView({ block: 'start' });
        }
      });
    });
    var radios = ['tab-nav-report', 'tab-nav-market', 'tab-nav-trades'];
    radios.forEach(function(id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener('change', function() {
          if (el.checked && window.history && window.history.replaceState) {
            var h = id === 'tab-nav-market' ? '#market' : (id === 'tab-nav-trades' ? '#trades' : '#report');
            window.history.replaceState(null, '', h);
          }
        });
      }
    });
    document.querySelectorAll('.formula-star').forEach(function(star) {
      star.addEventListener('click', function(ev) {
        ev.stopPropagation();
        var tip = star.querySelector('.formula-tooltip');
        if (tip) {
          var isVisible = tip.style.visibility === 'visible' && tip.style.opacity === '1';
          tip.style.visibility = isVisible ? 'hidden' : 'visible';
          tip.style.opacity = isVisible ? '0' : '1';
        }
      });
    });

    // OKX-Style Table Pagination
    function initTablePagination() {
      var tables = document.querySelectorAll('.paginated-table');
      tables.forEach(function(table) {
        if (table.dataset.paginationInitialized) return;
        table.dataset.paginationInitialized = 'true';
        var tbody = table.querySelector('tbody');
        if (!tbody) return;
        var allRows = Array.from(tbody.querySelectorAll('tr'));
        var totalRows = allRows.length;
        var pageSize = parseInt(table.dataset.pageSize || '10', 10);
        if (totalRows <= pageSize) return;

        var totalPages = Math.ceil(totalRows / pageSize);
        var currentPage = 1;

        var pagEl = document.createElement('div');
        pagEl.className = 'table-pagination';

        function renderPage(page) {
          currentPage = page;
          var start = (page - 1) * pageSize;
          var end = Math.min(start + pageSize, totalRows);

          allRows.forEach(function(row, idx) {
            row.style.display = (idx >= start && idx < end) ? '' : 'none';
          });

          pagEl.innerHTML = '';

          var infoEl = document.createElement('div');
          infoEl.className = 'pagination-info';
          infoEl.textContent = 'Showing ' + (start + 1) + ' – ' + end + ' of ' + totalRows + ' trades';

          var controlsEl = document.createElement('div');
          controlsEl.className = 'pagination-controls';

          function createBtn(text, pageNum, disabled, isActive) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'pagination-btn' + (isActive ? ' active' : '');
            btn.textContent = text;
            btn.disabled = !!disabled;
            if (!disabled && !isActive) {
              btn.onclick = function() { renderPage(pageNum); };
            }
            return btn;
          }

          controlsEl.appendChild(createBtn('«', 1, currentPage === 1));
          controlsEl.appendChild(createBtn('‹', currentPage - 1, currentPage === 1));

          var startP = Math.max(1, currentPage - 2);
          var endP = Math.min(totalPages, startP + 4);
          if (endP - startP < 4) {
            startP = Math.max(1, endP - 4);
          }

          for (var p = startP; p <= endP; p++) {
            controlsEl.appendChild(createBtn(String(p), p, false, p === currentPage));
          }

          controlsEl.appendChild(createBtn('›', currentPage + 1, currentPage === totalPages));
          controlsEl.appendChild(createBtn('»', totalPages, currentPage === totalPages));

          pagEl.appendChild(infoEl);
          pagEl.appendChild(controlsEl);
        }

        var parent = table.closest('.table-scroll') || table;
        parent.parentNode.insertBefore(pagEl, parent.nextSibling);
        renderPage(1);
      });
    }
    initTablePagination();

    // Rich Formula Hover Tooltips
    function initRichTooltips() {
      var tip = document.getElementById('rich-formula-tooltip');
      if (!tip) {
        tip = document.createElement('div');
        tip.id = 'rich-formula-tooltip';
        document.body.appendChild(tip);
      }

      function getTooltipData(target) {
        var el = target.closest('[data-formula], [data-metric-key], .param-label, .bar-label, .formula-star-btn');
        if (!el) return null;
        var formula = el.getAttribute('data-formula');
        var key = el.getAttribute('data-metric-key');
        var title = el.getAttribute('data-title');
        var desc = el.getAttribute('data-desc');

        if (!formula && key && window.METRIC_INFO && window.METRIC_INFO[key]) {
          var info = window.METRIC_INFO[key];
          formula = info.formula;
          title = title || info.title || key;
          desc = desc || info.desc;
        }
        if (!formula && !desc) return null;
        return { title: title || 'Calculation Methodology', formula: formula, desc: desc };
      }

      function positionTip(e) {
        var pad = 14;
        var tipW = tip.offsetWidth || 340;
        var tipH = tip.offsetHeight || 120;
        var x = e.clientX + pad;
        var y = e.clientY + pad;

        if (x + tipW > window.innerWidth - 10) {
          x = e.clientX - tipW - pad;
        }
        if (y + tipH > window.innerHeight - 10) {
          y = e.clientY - tipH - pad;
        }
        tip.style.left = Math.max(10, x) + 'px';
        tip.style.top = Math.max(10, y) + 'px';
      }

      document.addEventListener('mouseover', function(e) {
        var data = getTooltipData(e.target);
        if (!data) return;

        var isLight = document.documentElement.getAttribute('data-theme') === 'light';
        tip.className = (isLight ? 'theme-light is-visible' : 'theme-dark is-visible');
        tip.setAttribute('data-theme', isLight ? 'light' : 'dark');

        tip.innerHTML =
          '<div class="rich-tip-header"><span class="rich-tip-icon">📐</span><span class="rich-tip-title">' + (data.title || 'Formula') + '</span></div>' +
          (data.formula ? '<div class="rich-tip-formula-box"><strong class="rich-tip-formula-label">Formula:</strong> <span class="rich-tip-formula-code">' + data.formula + '</span></div>' : '') +
          (data.desc ? '<div class="rich-tip-desc">' + data.desc + '</div>' : '');

        positionTip(e);
      });

      document.addEventListener('mousemove', function(e) {
        if (tip) {
          if (!tip.classList.contains('is-visible')) {
            var data = getTooltipData(e.target);
            if (data) {
              var isLight = document.documentElement.getAttribute('data-theme') === 'light';
              tip.className = (isLight ? 'theme-light is-visible' : 'theme-dark is-visible');
              tip.setAttribute('data-theme', isLight ? 'light' : 'dark');

              tip.innerHTML =
                '<div class="rich-tip-header"><span class="rich-tip-icon">📐</span><span class="rich-tip-title">' + (data.title || 'Formula') + '</span></div>' +
                (data.formula ? '<div class="rich-tip-formula-box"><strong class="rich-tip-formula-label">Formula:</strong> <span class="rich-tip-formula-code">' + data.formula + '</span></div>' : '') +
                (data.desc ? '<div class="rich-tip-desc">' + data.desc + '</div>' : '');
              positionTip(e);
            }
          } else {
            positionTip(e);
          }
        }
      });

      document.addEventListener('mouseout', function(e) {
        if (e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('[data-formula], [data-metric-key], .param-label, .bar-label, .formula-star-btn')) {
          return;
        }
        if (tip) {
          tip.classList.remove('is-visible');
        }
      });
    }
    initRichTooltips();
  } catch (err) {}
})();
</script>"""
)
