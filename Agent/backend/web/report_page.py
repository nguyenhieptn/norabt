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

import hashlib
import html
import contextvars
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
from Agent.backend.web.portfolio_section import member_palette
from Agent.backend.market.coverage import MARKET_COVERAGE_TARGET_PCT
from Agent.backend.report.qc.reporting.reasons import LIQ_VI, TREND_VI, VOL_VI
from Agent.backend.report.qc.reporting.verdict_zone import (
    ZONE_DANGER,
    ZONE_NORMAL,
    ZONE_WARNING,
    classify_verdict_zone,
)

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
    "return_r_quality": "Return quality",
    "drawdown_risk": "Drawdown risk",
    "tail_risk": "Tail risk",
    "leverage_exposure": "Leverage / exposure",
    "behavioral_risk": "Behavioral risk",
    "strategy_drift": "Regime robustness",
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
    # One 3-colour risk scale everywhere: green = safe, yellow = risk,
    # red = danger (project owner, 2026-09-25).
    "HEALTHY": "#16a34a",
    "WATCH": "#eab308",
    "ELEVATED": "#eab308",
    "HIGH": "#dc2626",
    "CRITICAL": "#dc2626",
    "EMERGENCY": "#dc2626",
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
    "DRAWDOWN: HIGH · QUALITY: GOOD": "#ca8a04",
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


_STYLESHEET_CACHE: Dict[str, Tuple[str, str]] = {}


def report_stylesheet() -> Tuple[str, str]:
    """(URL, text) of the report's stylesheet -- tokens.css + `_CSS`, the
    exact text the inline `<style>` would carry. The URL embeds a hash of
    that text, so it can be cached forever and changes whenever the CSS
    does."""
    text = f"{_design_tokens_css_text()}\n{_CSS}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    if digest not in _STYLESHEET_CACHE:
        _STYLESHEET_CACHE.clear()
        _STYLESHEET_CACHE[digest] = (f"/assets/report-{digest}.css", text)
    return _STYLESHEET_CACHE[digest]


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
    # Section header bar (title + eyebrow/note) is deliberately not rendered
    # -- project owner's explicit call (2026-09): every section was ALSO
    # subdividing into its own titled sub-sections, so the page read as
    # "everything has a label on a label," and removing the label text alone
    # would have left an empty `.block-h` bar (its own background colour +
    # border) floating above the content for no reason. `title` stays a
    # REQUIRED parameter -- every call site still names its section for
    # readability in this source file and for `aria-label` below, screen
    # readers still get the section's name even though sighted users no
    # longer see a printed heading.
    return (
        f'<section class="card{tone_cls}{pair_cls}"{anchor_attr} aria-label="{_esc(title)}">'
        f'<div class="block-b">{body}</div>'
        "</section>"
    )


METRIC_FORMULA_INFO: Dict[str, Dict[str, str]] = {
    # Monte Carlo section (`_render_monte_carlo`), written against
    # bot/mcp/analytics/simulation/monte_carlo.py.
    "mc_p_ruin": {"title": "Probability of ruin", "formula": "P(ruin) = paths whose equity reaches 0 / all paths x 100", "desc": "Share of simulated paths that wipe out the capital."},
    "mc_mdd_p50": {"title": "Max drawdown · typical case (P50)", "formula": "Median over all simulated paths of Max((Peak - Equity) / Peak) x 100", "desc": "Half of the simulated paths fall less deep than this."},
    "mc_mdd_hist": {"title": "Max drawdown · actual path", "formula": "Max((Peak - Equity) / Peak) x 100 on the bot's real trade order, starting from the same capital as the simulation", "desc": "The drawdown the bot actually went through, measured exactly like the simulated paths so the two can be compared."},
    "mc_mdd_p95": {"title": "Max drawdown · bad case (P95)", "formula": "95th percentile of the simulated max drawdowns", "desc": "Only 5% of simulated paths fall deeper."},
    "mc_mdd_p99": {"title": "Max drawdown · very bad case (P99)", "formula": "99th percentile of the simulated max drawdowns", "desc": "Only 1% of simulated paths fall deeper."},
    "mc_mdd_exceed": {"title": "P(max drawdown worse than actual)", "formula": "Simulated paths whose max drawdown exceeds the actual path's / all paths x 100 (same trades, capital, horizon and seed as the simulation)", "desc": "How often the future could be worse than the worst stretch the bot has already been through."},
    "mc_p_mdd25": {"title": "P(max drawdown > 25%)", "formula": "Paths whose max((Peak - Equity) / Peak) exceeds 25% / all paths x 100", "desc": "How often a copier would sit through a fall deeper than a quarter of the capital."},
    "mc_p_loss": {"title": "P(loss at horizon)", "formula": "Paths ending below the starting capital after the horizon / all paths x 100", "desc": "Chance of being down after the simulated number of trades."},
    "mc_p_profit": {"title": "P(profit at horizon)", "formula": "P(profit) = 100% - P(loss at horizon)", "desc": "Chance of being up after the simulated number of trades."},
    "mc_var95": {"title": "Value at Risk 95%", "formula": "VaR 95% = 5th percentile of the final return % over all paths", "desc": "In 95% of paths the final return is at least this."},
    "mc_cvar95": {"title": "Conditional VaR 95%", "formula": "CVaR 95% = mean final return % of the worst 5% of paths", "desc": "The average of the bad cases beyond VaR."},
    "mc_mar": {"title": "MAR ratio (median)", "formula": "Per path: final return % / max drawdown %; median over paths", "desc": "Return earned per unit of drawdown suffered. Not annualised."},
    "mc_pf": {"title": "Profit factor (median)", "formula": "Per path: gross profit / |gross loss| of its resampled trades; median over paths", "desc": "Above 1 the typical path makes money."},
    "mc_skew": {"title": "Upside/downside ratio", "formula": "(P95 - P50) / (P50 - P05) of the final return %", "desc": "Above 1 the upside tail is wider than the downside tail."},
    # Evidence rows (`_render_quant_terminal_evidence`), one per tag -- short,
    # and written against what each row actually shows.
    "ev_profit_factor": {
        "title": "Profit factor",
        "formula": "PF = gross profit of winning closed trades / |gross loss of losing closed trades|; Marked = (gross profit + open gains) / (gross loss + open losses)",
        "desc": "Above 1 the book makes money. A big drop from Closed to Marked means losses are being held open.",
    },
    "ev_unrealised_loss": {
        "title": "Unrealized loss",
        "formula": "Unrealised = |PnL of still-open losing positions|; % = Unrealised / reference capital x 100",
        "desc": "Loss already there but not booked yet.",
    },
    "ev_stress_test": {
        "title": "Stress test",
        "formula": "Replay of the bot's closed trades with volatility x2, spread x3, liquidity x1/2",
        "desc": "Liquidated = equity reaches zero under that replay.",
    },
    "ev_risk_veto": {
        "title": "Risk veto floor",
        "formula": "Risk = Max(veto floor, weighted average of the 10 risk dimensions)",
        "desc": "One severe enough fault lifts risk to its floor, whatever the average says.",
    },
    "ev_risk_drivers": {
        "title": "Risk drivers",
        "formula": "Risk = weighted average of the 10 risk dimensions; heaviest = the dimensions adding the most to it",
        "desc": "No veto fired, so the average is the score.",
    },
    "ev_monte_carlo": {
        "title": "Monte Carlo",
        "formula": "N paths x H trades resampled from the bot's own trades (stationary bootstrap); Median / P05 / Worst = 50th percentile / 5th percentile / minimum of final return % of capital",
        "desc": "H defaults to the bot's own trade count.",
    },
    "ev_tail_risk": {
        "title": "Tail risk",
        "formula": "Worst-5% = mean final return of the worst 5% of paths (CVaR 95); P(loss) = paths ending below start / all paths x 100",
        "desc": "How bad the bad cases get, and how often a path ends in a loss.",
    },
    "ev_payoff": {
        "title": "Payoff asymmetry",
        "formula": "Win = winning trades / closed trades x 100; Payoff = average win / |average loss|",
        "desc": "Payoff above 1 means a typical win is larger than a typical loss.",
    },
    "ev_drawdown_sharpe": {
        "title": "Drawdown / Sharpe",
        "formula": "Max DD = deepest peak-to-trough fall of equity %; Sharpe = mean return / standard deviation of returns",
        "desc": "Depth of the worst fall, and return per unit of volatility.",
    },
    "ev_deflated_sharpe": {
        "title": "Deflated Sharpe",
        "formula": "Probability the Sharpe ratio is above zero after discounting how many candidates it was picked from",
        "desc": "Close to 50% means the edge may be luck.",
    },
    "ev_regime_bias": {
        "title": "Regime bias",
        "formula": "Downtrend trades = closed trades taken while the market phase was Downtrend",
        "desc": "0 means the strategy has never been tested in a falling market.",
    },
    "ev_profile": {
        "title": "Bot profile",
        "formula": "Trades = closed trades; Ref. capital = the capital every % is measured against; trades/day = closed trades / days observed",
        "desc": "Who the bot is and how much it trades.",
    },
    "ev_quality_drag": {
        "title": "Quality drag",
        "formula": "The quality components (0-100 each) scoring lowest, which pull the quality score down",
        "desc": "Where the strategy quality is lost.",
    },
    "ev_data_limits": {
        "title": "Data limits",
        "formula": "Mode = how much of the ledger is public (FULL / PARTIAL / LIMITED); Ledger covers = days with public trades / days active",
        "desc": "Less public data, less certain figures.",
    },
    "ev_not_computed": {
        "title": "Not computed",
        "formula": "Metrics that need per-trade data OKX does not publish for this bot",
        "desc": "Left blank rather than guessed.",
    },
    "ev_hidden_sections": {
        "title": "Hidden sections",
        "formula": "Report sections skipped because their data is not public for this bot",
        "desc": "Skipped rather than shown empty.",
    },
    "ev_strategy": {
        "title": "Strategy",
        "formula": "Direction and style read from the bot's trades; Best phase = market phase with the largest share of gross profit",
        "desc": "A high share from one phase means the edge depends on that market.",
    },
    "ev_audit_log": {
        "title": "Audit note",
        "formula": "Unstructured note from the analysis; no single formula",
        "desc": "Shown as written.",
    },
    # QUANTITATIVE EVIDENCE scorecard (_render_conclusion). Written against
    # bot/mcp/analytics/simulation/monte_carlo.py's `_simulate_horizon`.
    "qe_sim_max_dd": {
        "title": "Simulated max drawdown (P95, bad case)",
        "formula": "95th percentile over 10,000 simulated paths of Max((Peak - Equity) / Peak) x 100; paths = stationary bootstrap of the bot's own trades from the current capital, horizon = its own trade count",
        "desc": "Only 5% of simulated paths fall deeper than this. The typical (P50) and very bad (P99) cases are in the Monte Carlo section.",
    },
    "qe_ruin": {
        "title": "Probability of ruin",
        "formula": "P(ruin) = paths whose equity reaches 0 / all simulated paths x 100",
        "desc": "Share of simulated paths that wipe out the capital. 0% means no path did in this simulation, not that it cannot happen.",
    },
    # Quick risk strip under the headline scores (_render_quick_risk_strip).
    # Written against what that function and loss_analysis.py actually
    # compute, not the generic definitions further down -- e.g. the drawdown
    # there is the deepest episode over ONE reference capital, not
    # performance.max_drawdown_pct.
    "qrs_reference_capital": {
        "title": "Reference capital",
        "formula": "Reference capital = bot's reference capital (current state), else capital at risk from its weekly equity curve",
        "desc": "The single capital base every % on this strip is measured against. Never replaced by self-reported AUM.",
    },
    "qrs_unrealised_loss": {
        "title": "Unrealized loss",
        "formula": "Float % = PnL of still-open positions / Reference capital x 100",
        "desc": "Loss sitting in open positions that has not been booked yet. Shows 0.0% when the bot holds no open position.",
    },
    "qrs_max_drawdown": {
        "title": "Max drawdown",
        "formula": "Max DD (%) = Max [ (peak equity - following trough equity) / peak equity ] × 100%, equity = reference capital + cumulative realised PnL",
        "desc": "Standard peak-to-trough max drawdown of the bot's closed trades, capped at 100% (a wipe-out). The same figure as in Trade metrics and the Monte Carlo 'actual'.",
    },
    "qrs_win_rate": {
        "title": "Win rate",
        "formula": "Win rate = Winning closed trades / All closed trades x 100",
        "desc": "Share of closed trades that ended in profit. Says nothing about how large wins are compared with losses.",
    },
    "qrs_observed_trades": {
        "title": "Closed trades",
        "formula": "Count of closed trades in the bot's public ledger",
        "desc": "Sample size behind every statistic in this report. Below 50 is marked amber: too few trades for stable estimates.",
    },
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
        "title": "Behavioral risk",
        "formula": "Detects martingale, averaging down, raising leverage after a loss, order-entry loops",
        "desc": "Assesses high-risk or undisciplined trading habits found in the trade ledger that could lead to a sudden account blow-up.",
    },
    "leverage_exposure": {
        "title": "Leverage & exposure",
        "formula": "Actual leverage ratio / capital, margin utilisation, concurrent-position exposure ratio",
        "desc": "Measures how much financial leverage is used and the risk of forced liquidation by the exchange during sharp market moves.",
    },
    "strategy_drift": {
        "title": "Regime robustness",
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
        "title": "Return quality",
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
        "formula": "Max DD (%) = Max [ (peak equity - following trough equity) / peak equity ] × 100%, equity = reference capital + cumulative realised PnL",
        "desc": "The largest peak-to-trough fall of the bot's equity over its closed trades, capped at 100% (a wipe-out). Same path and formula as the Monte Carlo simulation, so the two compare directly.",
    },
    "current_drawdown_pct": {
        "title": "Current drawdown",
        "formula": "Current DD (%) = [ (highest equity so far - latest equity) / highest equity so far ] × 100%, equity = reference capital + cumulative realised PnL",
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
    "calmar_ratio_weekly": {
        "title": "Calmar ratio (annualised return / max drawdown)",
        "formula": "Calmar = [ (Π (1 + weekly return))^(365.25 / days) − 1 ] / max(max DD on trades, max DD of weekly equity, max DD of the weekly return index Π(1 + r))",
        "desc": "OKX publishes no total ROI for this bot, so the return is compounded from OKX's own weekly returns, annualised, then divided by the largest of the measured max drawdowns (the conservative choice). Used only when the rounding of the published weekly ratios moves the return by at most 25%, and over at least 30 days.",
    },
    "calmar_ratio_equity": {
        "title": "Calmar ratio (estimated capital)",
        "formula": "Calmar = [ ((E + total PnL) / E)^(365.25 / days) − 1 ] / max drawdown",
        "desc": "No OKX ROI and no weekly history long enough: the return is the realised PnL over the estimated capital E (same capital as the drawdown rows), annualised over the ledger span (at least 30 days). Approximate.",
    },
    "calmar_ratio_nodd": {
        "title": "Calmar ratio",
        "formula": "Calmar = annualised return / max drawdown",
        "desc": "Positive return with no drawdown at all: the ratio has no finite value, so none is shown.",
    },
    "calmar_ratio_wiped": {
        "title": "Calmar ratio",
        "formula": "Calmar = annualised return / max drawdown",
        "desc": "The weekly equity reached zero (a 100% loss) inside the published weeks, so there is no return to annualise; the account was wiped out.",
    },
    "dd_weekly_max": {
        "title": "Max drawdown (weekly equity)",
        "formula": "Max DD = max over weeks [ (equity peak − equity) / equity peak ], equity = weekly PnL / weekly PnL ratio",
        "desc": "This bot has no closed trade in the ledger, so the drawdown is read from the account equity OKX's weekly PnL implies (weeks whose ratio is precise enough).",
    },
    "dd_weekly_cur": {
        "title": "Current drawdown (weekly equity)",
        "formula": "Current DD = (highest weekly equity − latest weekly equity) / highest weekly equity",
        "desc": "How far the latest weekly equity sits below its highest point.",
    },
    "dd_pooled_max": {
        "title": "Max drawdown (pooled equity estimate)",
        "formula": "Max DD ≈ max drawdown on trades (USDT) / E,  E = Σ|weekly PnL| / Σ|weekly ratio|",
        "desc": "No single week's ratio is precise enough to give the account equity, so all weeks are pooled; the rounding of the published ratios bounds the error of E (shown only when that bound is 15% or less).",
    },
    "dd_pooled_cur": {
        "title": "Current drawdown (pooled equity estimate)",
        "formula": "Current DD ≈ (peak cumulative PnL − current cumulative PnL) / E",
        "desc": "Same pooled equity estimate E as the max drawdown row.",
    },
    "dd_margin_max": {
        "title": "Max drawdown (upper bound)",
        "formula": "C₀ = max over time (margin in use − realised PnL so far);  equity = C₀ + cumulative PnL;  Max DD = max (peak − equity) / peak",
        "desc": "No usable equity figure at all, so capital is the smallest amount that could have funded every position in the ledger. Real capital can only be larger, so the real drawdown is at most this value.",
    },
    "dd_margin_cur": {
        "title": "Current drawdown (upper bound)",
        "formula": "Current DD ≤ (peak equity − latest equity) / peak equity, equity = C₀ + cumulative PnL",
        "desc": "Same minimum-funding capital C₀ as the max drawdown row.",
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
        "title": "Unrealized loss",
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
    "stress_test": {
        "title": "Stress scenario",
        "formula": "Replays the closed trade sequence with volatility ×2, spread ×3, liquidity ×0.5",
        "desc": "A synthetic worst-case market applied on top of the bot's own trade history, to see whether it survives conditions harsher than anything actually observed yet.",
    },
}


# Per-render formula overrides. A PORTFOLIO page is rendered by this same
# renderer, but each number on it is computed from N members together, so
# its explanations differ from the single-bot ones below (see
# `web/portfolio_formulas.py`). The page's data carries them as
# `result["formula_overrides"]`; `render_bot_report_html` sets this for the
# duration of one render. A single-bot result carries none, and every lookup
# then returns exactly `METRIC_FORMULA_INFO` as before.
_FORMULA_OVERRIDES: "contextvars.ContextVar[Optional[Dict[str, Dict[str, str]]]]" = (
    contextvars.ContextVar("report_formula_overrides", default=None)
)


def _formula_info(key: Optional[str]) -> Optional[Dict[str, str]]:
    if not key:
        return None
    overrides = _FORMULA_OVERRIDES.get()
    if overrides and key in overrides:
        return overrides[key]
    return METRIC_FORMULA_INFO.get(key)


def _formula_override_script() -> str:
    """Hands this render's overrides to the formula modal (the runtime script
    loads `METRIC_FORMULA_INFO`; this runs after it, in the page and in the
    SPA, which re-runs a report's scripts in document order)."""
    overrides = _FORMULA_OVERRIDES.get()
    if not overrides:
        return ""
    payload = json.dumps(overrides, ensure_ascii=False).replace("</", "<\\/")
    return (
        '<script id="report-formula-overrides">'
        f"window.METRIC_INFO=Object.assign(window.METRIC_INFO||{{}},{payload});"
        "</script>\n"
    )


def _calc_label_html(label: str, info_key: Optional[str] = None) -> str:
    """Render a parameter label with native title tooltip and clickable formula button."""
    info = _formula_info(info_key)
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


def _gauge_svg(pct: Any, color: Optional[str]) -> str:
    """Half-circle gauge for a 0-100 hero score: a full grey track plus an
    arc filled clockwise from the left end in proportion to `pct`. A missing
    or non-finite value draws the track only -- never a guessed fill."""
    track = '<path class="gauge-track" d="M10,60 A50,50 0 0 1 110,60"/>'
    arc = ""
    if _is_finite_number(pct):
        v = max(0.0, min(100.0, float(pct)))
        if v > 0:
            theta = math.radians(180.0 - 1.8 * v)
            x = 60.0 + 50.0 * math.cos(theta)
            y = 60.0 - 50.0 * math.sin(theta)
            stroke = f' style="stroke:{_esc(color)}"' if color else ""
            arc = f'<path class="gauge-arc" d="M10,60 A50,50 0 0 1 {x:.2f},{y:.2f}"{stroke}/>'
    return f'<svg class="stat-gauge" viewBox="0 0 120 66" aria-hidden="true">{track}{arc}</svg>'


def _note_chip(short: str, full_html: str, tone: str = "warning") -> str:
    """A caveat as one short line; the full explanation behind its ⓘ.
    Long warning paragraphs used to sit in the middle of the report."""
    full = html.unescape(re.sub(r"<[^>]+>", " ", full_html))
    full = re.sub(r"\s+", " ", full).strip()
    return (
        f'<div class="note-chip notice-{tone}-chip">'
        f'<span class="nc-dot"></span><span class="nc-text">{_esc(short)}</span>'
        f'<i class="info-ic" tabindex="0">i<span class="info-tip">{_esc(full)}</span></i></div>'
    )


def _stat_tile(
    label: str,
    value: str,
    *,
    color: Optional[str] = None,
    size: str = "",
    info_key: Optional[str] = None,
    basis_anchor: Optional[str] = None,
    with_gauge: bool = False,
    gauge_pct: Any = None,
    unit: str = "",
    hint: str = "",
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
    if hint:
        label_markup += f'<span class="stat-hint">{_esc(hint)}</span>'
    if basis_anchor and not info_key:
        label_markup += (
            f' <a class="score-basis-star" href="#{_esc(basis_anchor)}" '
            f'aria-label="See how {_esc(label)} is calculated" title="See how this score is calculated">*</a>'
        )
    if with_gauge:
        unit_html = f'<span class="stat-unit">{_esc(unit)}</span>' if unit else ""
        return (
            f'<div class="stat-tile{size_cls}"{tile_style}>'
            f"{_gauge_svg(gauge_pct, color)}"
            '<div class="stat-body">'
            f'<div class="stat-label">{label_markup}</div>'
            f'<div class="stat-value"{style}>{_esc(value)}{unit_html}</div>'
            "</div>"
            "</div>"
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


def _table_caption(text: str) -> str:
    """A visible name above a data table -- project owner's own request
    (2026-09-22): every value-list table in the Market/Position tabs should
    name what it lists, unlike the Analyst Result tab's section-level
    labels (WHY/QUANTITATIVE EVIDENCE/...), which stay exactly as they were.
    Deliberately its own small caption, not `_subsection()`: a table caption
    names ONE table inline with the surrounding prose, it does not open a
    whole new `.subsection` block around content that already has its own
    paragraphs before/after the table.
    """
    return f'<div class="table-caption">{_esc(text)}</div>'


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


def _nice_tick_step(y_range: float, target_ticks: int = 6) -> float:
    """A gridline step that scales with the data instead of a fixed table.

    A bot whose Monte Carlo P50 compounds into the thousands of percent
    (a real, observed fixture: checkpoints spanning +1680% to +4736%) blew
    past every hand-picked step tier this chart used to have (capped at a
    flat 5% for the median line, 20% for the fan chart) -- the tick loop
    kept stepping by that tiny fixed amount across a huge range and drew
    on the order of a thousand overlapping gridlines/labels, turning the
    chart into an unreadable smear instead of a professional chart.

    Standard "nice number" tick sizing instead: pick the step from
    {1, 2, 2.5, 5} x 10^n closest to `y_range / target_ticks`, so the
    number of gridlines stays roughly constant (~target_ticks) no matter
    how small or how enormous the value range is.
    """
    if y_range <= 0 or not math.isfinite(y_range):
        return 1.0
    raw_step = y_range / max(1, target_ticks)
    magnitude = 10.0 ** math.floor(math.log10(raw_step))
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        step = candidate * magnitude
        if step >= raw_step:
            return step
    return 10.0 * magnitude


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
                    else ("#eab308" if v < scale_max * 0.7 else "#16a34a")
                )
            else:
                color = (
                    "#16a34a"
                    if v < scale_max * 0.34
                    else ("#eab308" if v < scale_max * 0.7 else "#dc2626")
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
    _label_w = 300.0  # reserved for SVG layout, not yet wired to track_x
    star_x = 306.0
    track_x = 316.0
    track_w = max(width - track_x - value_w - 10.0, 40.0)
    height = top_pad * 2 + row_h * len(rows)
    parts: List[str] = []
    for i, row in enumerate(rows):
        y = top_pad + i * row_h
        mid = y + row_h * 0.60
        info = _formula_info(row.info_key)
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
    center_title: str = "",
    center_subtitle: str = "",
) -> str:
    """`slices` is `(label, value, color)` triples.
    Renders an institutional modern Donut Chart with center KPI text.
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
    inner_radius = radius * 0.67

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
                f'{_coord(x2)},{_coord(y2)} Z" fill="{_esc(color)}" '
                f'stroke="var(--panel, #111726)" stroke-width="2"/>'
            )

        lx, ly = point(mid_angle, radius + 22.0)
        anchor = "start" if lx >= cx else "end"
        label_text = label if len(label) <= 22 else label[:21] + "…"
        parts.append(_text(lx, ly - 3, label_text, anchor=anchor, cls="pie-label"))
        parts.append(
            _text(
                lx,
                ly + 10,
                f"{_num(value, 0)} · {frac * 100.0:.1f}%",
                anchor=anchor,
                cls="pie-value",
            )
        )
        cumulative = end_angle

    # Inner cutout disc creating the Donut ring (wider inner hole for clean breathing room)
    parts.append(
        f'<circle cx="{_coord(cx)}" cy="{_coord(cy)}" r="{_coord(inner_radius)}" '
        f'fill="var(--panel, var(--card-bg, #111726))"/>'
    )
    if center_title:
        parts.append(
            _text(
                cx,
                cy - 4,
                center_title,
                anchor="middle",
                cls="pie-center-title",
                fill="var(--text, #ffffff)",
                extra='style="font-family:var(--mono);font-size:13.5px;font-weight:700;"',
            )
        )
    if center_subtitle:
        parts.append(
            _text(
                cx,
                cy + 11,
                center_subtitle,
                anchor="middle",
                cls="pie-center-sub",
                fill="var(--muted, #94a3b8)",
                extra='style="font-family:var(--sans);font-size:7.5px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;"',
            )
        )

    return _svg(
        width,
        height,
        "".join(parts),
        extra_class="pie-chart donut-chart",
        aria_label="Outcome distribution chart",
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

    left_pad = 85.0
    right_pad = 115.0
    top_pad = 24.0
    bottom_pad = 32.0
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
    """The 3 headline score tiles (risk/quality/confidence), global to every
    tab -- see `_render_header`, which now embeds this output right below the
    bot identity/verdict badge, outside `.tab-panels`, so it stays visible no
    matter which of the 3 tabs is open (it used to live only inside the
    Analyst Result tab's Conclusion section, via `_render_conclusion`).

    The veto/emergency-override explanation ("Risk score X is NOT the
    average...") and the "QUANTITATIVE METHODOLOGY BASIS" collapsible used to
    render here too; both were dropped at the project owner's request --
    the hero area is meant to be score + general parameters only, not the
    full reasoning (`_render_conclusion`'s WHY/EVIDENCE blocks already carry
    that argument in the Analyst Result tab).
    """
    risk = result.get("risk")
    quality = result.get("quality")
    confidence = result.get("confidence")

    tiles = [
        _stat_tile(
            "Risk score",
            _num(risk, 0),
            hint="lower = better",
            color=_risk_color(risk),
            size="hero",
            info_key="risk_score",
            with_gauge=True,
            gauge_pct=risk,
            unit="/100" if _is_finite_number(risk) else "",
        ),
        _stat_tile(
            "Quality score",
            _num(quality, 0),
            hint="higher = better",
            color=_higher_is_better_color(quality),
            size="hero",
            info_key="quality_score",
            with_gauge=True,
            gauge_pct=quality,
            unit="/100" if _is_finite_number(quality) else "",
        ),
        _stat_tile(
            "Confidence",
            _pct(confidence, 0),
            color=_higher_is_better_color(confidence),
            size="hero",
            info_key="confidence",
            with_gauge=True,
            gauge_pct=confidence,
        ),
    ]

    limited_notice = ""
    if result.get("status") == "LIMITED":
        reason = (
            result.get("limited_reason") or "OKX does not publicly expose enough data for this bot"
        )
        unavailable = result.get("unavailable") or []
        unavailable_vi = ", ".join(_esc(u) for u in unavailable)
        _limited_full = (
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
        limited_notice = _note_chip("Limited assessment: public data only", _limited_full)

    notices_html = (
        f'<div class="header-notices">{limited_notice}</div>' if limited_notice else ""
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
        f' · <span class="venue-symbol-badge">{_esc(symbol)} ({_esc(venue)})</span>'
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
    # Score tiles (risk/quality/confidence) + the quick risk metrics strip
    # (reference capital, unrealised loss, max drawdown, win rate, observed
    # trades) render here now, right after the identity/verdict badge and
    # BEFORE the tabs -- global to every tab, not just Analyst Result (see
    # `_render_hero_scores`/`_render_quick_risk_strip`, moved out of
    # `_render_conclusion`). A separate sibling <div> on purpose, never
    # nested inside <header class="report-header report-hero-card">: the SPA
    # (BotDetailView.jsx) strips that exact header out of the fetched
    # document and rebuilds its own from `.head-title`/`.verdict-badge`
    # before it removes anything, so a sibling survives that DOM surgery
    # and still shows on every tab there too, while a descendant would not.
    key_metrics_html = _render_short_answer(result) + _render_hero_scores(result) + _render_quick_risk_strip(result)
    key_metrics_block = (
        f'<div class="report-key-metrics">{key_metrics_html}</div>'
        if key_metrics_html
        else ""
    )
    # Right-aligned on the same row as the bot name. Lives inside the
    # server header, which the SPA strips -- BotDetailView.jsx copies
    # `.report-verdict-chip` out first and re-renders it on its own header
    # row, same as it already does for `.head-title`/`.verdict-badge`.
    verdict_chip = _verdict_chip_html(result)
    hero_top_cls = "report-hero-top has-verdict-chip" if verdict_chip else "report-hero-top"
    main_header = (
        f"{subnav_html}"
        '<header class="report-header report-hero-card">'
        f'<div class="{hero_top_cls}">'
        '<div class="report-hero-identity">'
        f"{crumb_html}"
        f'<h1 class="head-title">{_esc(name)}</h1>'
        '<div class="report-hero-meta">'
        f'<span class="bot-code-pill">Code: <code>{_esc(code)}</code></span>'
        f"{market_tag}"
        f'<span class="verdict-badge" style="--badge-color:{verdict_color}">{_esc(verdict or "INSUFFICIENT EVIDENCE")}</span>'
        "</div>"
        "</div>"
        f"{verdict_chip}"
        "</div>"
        "</header>"
        f"{key_metrics_block}"
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
    # Same bands as the risk dimensions: <30 safe, 30-69 risk, >=70 danger.
    v = float(risk)
    if v >= 70:
        return "#dc2626"
    if v >= 30:
        return "#eab308"
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
    if v >= 70:
        return "#16a34a"
    if v >= 40:
        return "#eab308"
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


def _verdict_chip_html(result: Dict[str, Any]) -> str:
    """The compact "DRAWDOWN: X · QUALITY: Y" chip, now shown in the page
    header on the same row as the bot name (right-aligned) instead of at the
    top of the Analyst Result tab's Conclusion.

    Same headline and same tone as the chip `_render_conclusion` used to
    render: parsed from the `CONCLUSION:` line of `result["text"]` (falling
    back to `result["verdict"]`), zoned by `classify_verdict_zone` with the
    same portfolio HIGH_CORRELATION_CLUSTER floor.
    """
    headline, tone = _verdict_headline_and_tone(result)
    if not headline:
        return ""
    # The verdict's own basis (method + what the score does and does not
    # claim) used to sit in an always-open block under the hero scores; it
    # now rides on the chip as its hover text.
    basis = result.get("verdict_basis")
    title = f' title="{_esc(basis)}"' if isinstance(basis, str) and basis.strip() else ""
    return (
        f'<div class="report-verdict-chip tone-{tone}"{title}>'
        f'<span class="verdict-chip">{_format_verdict_headline(headline)}</span>'
        "</div>"
    )


def _verdict_headline_and_tone(result: Dict[str, Any]) -> Tuple[str, str]:
    """(headline, zone tone) shared by the header chip and the WHY icons."""
    headline = ""
    text_lines = result.get("text")
    for raw_line in text_lines if isinstance(text_lines, list) else []:
        if not isinstance(raw_line, str):
            continue
        line = re.sub(r"^([^\(\)]+?)\s*\(\1\)", r"\1", raw_line.strip())
        upper = line.upper()
        if upper.startswith(_CONCLUSION_VERDICT_PREFIX) or upper.startswith("KẾT LUẬN:"):
            headline = line[line.index(":") + 1 :].split(" — ", 1)[0].strip()
            break
    if not headline:
        headline = str(result.get("verdict") or "").strip()
    if not headline:
        return "", ZONE_NORMAL
    portfolio_verdict = (result.get("portfolio") or {}).get("verdict")
    min_zone = ZONE_WARNING if portfolio_verdict == "HIGH_CORRELATION_CLUSTER" else ZONE_NORMAL
    return headline, classify_verdict_zone(headline, min_zone=min_zone)


def _detect_quant_tag(text: str) -> str:
    u = text.upper()
    if "PROFIT FACTOR" in u:
        return "[PROFIT FACTOR]"
    elif "UNREALISED LOSS" in u or "UNREALIZED LOSS" in u or "OPEN LOSS" in u:
        return "[UNREALIZED LOSS]"
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


# Which `METRIC_FORMULA_INFO` entry the "*" star on each `_detect_quant_tag`
# result opens -- project owner's own request (2026-09-23): "thêm * mô tả
# cho từng tham số trong đó" (add a "*" description for each parameter in
# there), same mechanism `_calc_label_html` already uses on every FULL-mode
# metric table. "[AUDIT LOG]" -- the fallback tag for a row that matched none
# of `_detect_quant_tag`'s keywords (e.g. the bot's own identity line) --
# deliberately has no entry: there is no single formula behind an
# unstructured audit note, so it gets no star rather than a misleading one.
_QUANT_TAG_INFO_KEY: Dict[str, str] = {
    "[PROFIT FACTOR]": "ev_profit_factor",
    "[UNREALIZED LOSS]": "ev_unrealised_loss",
    "[RISK VETO FLOOR]": "ev_risk_veto",
    "[RISK DRIVERS]": "ev_risk_drivers",
    "[MONTE CARLO]": "ev_monte_carlo",
    "[TAIL RISK]": "ev_tail_risk",
    "[PAYOFF ASYMMETRY]": "ev_payoff",
    "[REGIME BIAS]": "ev_regime_bias",
    "[DRAWDOWN / SHARPE]": "ev_drawdown_sharpe",
    "[STRESS TEST]": "ev_stress_test",
    "[DEFLATED SHARPE]": "ev_deflated_sharpe",
    "[PROFILE]": "ev_profile",
    "[QUALITY DRAG]": "ev_quality_drag",
    "[DATA LIMITS]": "ev_data_limits",
    "[NOT COMPUTED]": "ev_not_computed",
    "[HIDDEN SECTIONS]": "ev_hidden_sections",
    "[STRATEGY]": "ev_strategy",
    "[AUDIT LOG]": "ev_audit_log",
}


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
    # Comma-grouped form first (`1,234,567`), else a plain unbounded digit
    # run -- the old `\d{1,3}(?:,\d{3})*` matched a bare 4+ digit number
    # (no commas, e.g. OKX's error code 60004) as "600" then a separate
    # "04", splitting one number into two highlighted spans.
    # Not glued to a word: "p05" is a label and "3EB985..." a bot code, not
    # numbers to highlight ("2x" still is -- the letter after it is alone).
    pattern = r'(?<![A-Za-z0-9.])([+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:\s*%|\s*USDT)?|[+-]?\d+(?:\.\d+)?(?:\s*%|\s*USDT)?)(?![A-Za-z]\w|\d)'
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


def _split_top_level_commas(text: str) -> List[str]:
    """Split on ", " outside parentheses -- "(volatility 2x, spread 3x)"
    stays one piece, and "10,000" (no space) is never split. Prose (several
    sentences, or a " -- " aside) is left whole: its commas are grammar, not
    separators between values."""
    if re.search(r"\.\s+[A-Z]", text) or " -- " in text:
        return [text.strip()] if text.strip() else []
    parts: List[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0 and text[i + 1 : i + 2] == " ":
            parts.append(text[start:i].strip())
            start = i + 2
    parts.append(text[start:].strip())
    return [p for p in parts if p]


def _consequence_tone(tag: str, text: str) -> Optional[str]:
    """Tone of a proof point's closing clause (see reasons.py `_proof_points`)
    when it reads as a verdict, else None -- then it is plain detail and
    stays with the values instead of becoming an end pill."""
    low = text.lower()
    if tag == "[RISK VETO FLOOR]":
        return "bad"
    if any(k in low for k in ("whole problem", "erases", "liquidat")):
        return "bad"
    if any(k in low for k in ("would cost", "downtrend phase", "never tested")):
        return "warn"
    if any(k in low for k in ("not hiding a loss", "well ahead")):
        return "good"
    return None


# --------------------------------------------------------------------------- #
# Peer comparison -- where this bot's headline numbers sit among the other
# bots this system has already scored (`/api/bots` rows, passed in by the
# route as `peer_rows`). Only fully scored bots count (a quality score and at
# least one closed trade): the store also holds placeholder rows for bots
# that could not be scored, and those would drag every median down. The
# group is small and self-selected (only bots someone asked to analyse), so
# the header always names N and the tooltip says it is not all of OKX.
# --------------------------------------------------------------------------- #

_PEER_BINS = 10


def _peer_population(result: Dict[str, Any], mine: Dict[str, Optional[float]]) -> List[Dict[str, float]]:
    rows = result.get("_peer_rows")
    if not isinstance(rows, list):
        return []
    code = result.get("code")
    pop: List[Dict[str, float]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("code") == code:
            continue
        tc = row.get("trade_count")
        if not _is_finite_number(row.get("quality")) or not _is_finite_number(tc) or tc <= 0:
            continue
        pop.append({k: row.get(k) for k in ("risk", "quality", "confidence", "trade_count")})
    # This bot enters with the numbers on this page, not its stored row.
    pop.append(dict(mine))
    return pop


def _peer_hist_svg(values: List[float], mine: float, lo: float, hi: float, tone: str) -> str:
    span = (hi - lo) or 1.0
    counts = [0] * _PEER_BINS

    def _bin(v: float) -> int:
        return min(_PEER_BINS - 1, max(0, int((v - lo) / span * _PEER_BINS)))

    for v in values:
        counts[_bin(v)] += 1
    top = max(counts) or 1
    my_bin = _bin(mine)
    w, bw, base, h_max = 200.0, 20.0, 60.0, 44.0
    bars = []
    for i, c in enumerate(counts):
        bh = max(2.0, c / top * h_max) if c else 2.0
        cls = f"peer-bar peer-bar-me tone-{tone}" if i == my_bin else "peer-bar"
        bars.append(
            f'<rect class="{cls}" x="{i * bw + 2:.1f}" y="{base - bh:.1f}" '
            f'width="{bw - 4:.1f}" height="{bh:.1f}" rx="1.5"/>'
        )
    my_h = max(2.0, counts[my_bin] / top * h_max)
    mx = my_bin * bw + bw / 2
    marker = (
        f'<path class="peer-marker tone-{tone}" '
        f'd="M{mx - 4:.1f},{base - my_h - 8:.1f} L{mx + 4:.1f},{base - my_h - 8:.1f} '
        f'L{mx:.1f},{base - my_h - 3:.1f} Z"/>'
    )
    ordered = sorted(values)
    median = ordered[len(ordered) // 2] if len(ordered) % 2 else (
        (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
    )
    medx = max(0.0, min(w, (median - lo) / span * w))
    med_line = (
        f'<line class="peer-median" x1="{medx:.1f}" y1="6" x2="{medx:.1f}" y2="{base:.1f}"/>'
    )
    return (
        f'<svg class="peer-hist" viewBox="0 0 {w:.0f} 62" preserveAspectRatio="none" '
        f'aria-hidden="true">{"".join(bars)}{med_line}{marker}</svg>'
    )


def _render_peer_comparison(result: Dict[str, Any], sample_count: Any) -> str:
    conf = result.get("confidence")
    if _is_finite_number(conf) and float(conf) <= 1.0:
        conf = float(conf) * 100.0
    mine: Dict[str, Optional[float]] = {
        "risk": float(result["risk"]) if _is_finite_number(result.get("risk")) else None,
        "quality": float(result["quality"]) if _is_finite_number(result.get("quality")) else None,
        "confidence": float(conf) if _is_finite_number(conf) else None,
        "trade_count": float(sample_count) if _is_finite_number(sample_count) else None,
    }
    pop = _peer_population(result, mine)
    if len(pop) < 5:
        return ""

    def _conf_val(v: Any) -> Optional[float]:
        if not _is_finite_number(v):
            return None
        return float(v) * 100.0 if float(v) <= 1.0 else float(v)

    specs = [
        # key, label, lower_is_better, value fmt, axis labels
        ("risk", "Risk score", True, lambda v: f"{v:.0f}", None),
        ("quality", "Quality score", False, lambda v: f"{v:.0f}", None),
        ("confidence", "Confidence", False, lambda v: f"{v:.0f}%", None),
        ("trade_count", "Closed trades", False, lambda v: f"{v:,.0f}", None),
    ]
    cards = []
    for key, label, lower_better, fmt, _ in specs:
        me = mine.get(key)
        if me is None or (key == "trade_count" and not me):
            continue
        vals = [
            (_conf_val(r.get(key)) if key == "confidence" else float(r[key]))
            for r in pop
            if _is_finite_number(r.get(key))
        ]
        vals = [v for v in vals if v is not None]
        if len(vals) < 5:
            continue
        n = len(vals)
        rank = 1 + sum(1 for v in vals if (v < me if lower_better else v > me))
        frac = rank / n
        tone = "good" if frac <= 1 / 3 else ("warn" if frac <= 2 / 3 else "bad")
        ordered = sorted(vals)
        median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        if key in ("risk", "quality"):
            lo, hi = 0.0, 100.0
            lo_lbl, hi_lbl = ("better", "worse") if key == "risk" else ("0", "100")
        elif key == "confidence":
            lo = max(0.0, math.floor(min(vals) / 10.0) * 10.0)
            hi = 100.0
            lo_lbl, hi_lbl = f"{lo:.0f}%", "100%"
        else:
            lo = 0.0
            hi = max(10.0, math.ceil(max(vals) / 10.0) * 10.0)
            lo_lbl, hi_lbl = "0", f"{hi:,.0f}"
        cards.append(
            '<div class="peer-card">'
            '<div class="peer-card-head">'
            f'<span class="peer-card-label">{_esc(label)}</span>'
            f'<span class="peer-rank tone-{tone}" title="Rank {rank} of {n}">#{rank}</span>'
            "</div>"
            '<div class="peer-card-value">'
            f'<span class="peer-value">{_esc(fmt(me))}</span>'
            f'<span class="peer-median-text">median {_esc(fmt(median))}</span>'
            "</div>"
            f"{_peer_hist_svg(vals, me, lo, hi, tone)}"
            f'<div class="peer-axis"><span>{_esc(lo_lbl)}</span><span>{_esc(hi_lbl)}</span></div>'
            "</div>"
        )
    if not cards:
        return ""
    n_all = len(pop)
    tip = (
        f"Compared only with the {n_all} bots already scored in this system, not every bot "
        "on OKX. #1 is the best in the group; with a group this small one rank step is a "
        "big percentile jump. Dashed line = group median."
    )
    return (
        '<div class="conclusion-section-block conclusion-peer-block">'
        '<div class="peer-head">'
        '<div class="conclusion-sub-title">Peer comparison</div>'
        f'<span class="peer-head-note">Rank among {n_all} analyzed bots'
        f'<i class="info-ic" tabindex="0">i<span class="info-tip">{_esc(tip)}</span></i></span>'
        "</div>"
        f'<div class="peer-grid">{"".join(cards)}</div>'
        "</div>"
    )


# --------------------------------------------------------------------------- #
# Compact WHY / evidence -- project owner (2026-09-24): "nhiều chữ quá ... ngắn
# gọn chủ yếu tham số giống như preview". The sentences `reasons.py` writes
# are parsed back into short labels + the figures they carry; nothing is
# invented, and the full wording stays one hover away (the "i" next to each
# section label). A line that matches no known shape falls back to the old
# rendering, so a new phrasing in reasons.py degrades to "wordy", not "gone".
# --------------------------------------------------------------------------- #

_WhyFact = Tuple[str, Optional[str], str]  # (label, chip or None, tone good|warn|bad)


def _no_trades(result: Dict[str, Any]) -> bool:
    """True when the bot publishes no closed trade at all (hidden or none):
    the page then leaves out everything that would only say so -- project
    owner, 2026-09-24: a bot that hides its data is simply not talked about."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    n = perf.get("trade_count", result.get("trade_count"))
    return _is_finite_number(n) and int(float(n)) == 0 and not evidence.get("closed_trade_series")


def _why_facts(story: str, result: Dict[str, Any]) -> List[_WhyFact]:
    s = " ".join(story.split())
    low = s.lower()
    facts: List[_WhyFact] = []
    risk = result.get("risk")
    risk_txt = f"Risk {float(risk):.0f}/100" if _is_finite_number(risk) else None
    # The leaderboard figures reasons.py puts in brackets: "(win rate 80%,
    # profit factor 2.10, max drawdown 9.8%)" -> "Win 80% · PF 2.10".
    surface_chip: Optional[str] = None
    sm = re.search(r"\(((?:win rate|profit factor|max drawdown)[^)]*)\)", s)
    if sm:
        bits = []
        for part in sm.group(1).split(", "):
            pm = re.match(r"(win rate|profit factor|max drawdown) (.+)$", part)
            if pm:
                bits.append({"win rate": "Win", "profit factor": "PF", "max drawdown": "DD"}[pm.group(1)] + " " + pm.group(2))
        surface_chip = " · ".join(bits[:2]) or None
    if _no_trades(result):
        surface_chip = None

    m = re.search(r"is blocked by a veto rule, not by the weighted average score: (.+?)\. A veto exists", s)
    if m:
        facts.append(("Blocked by a veto rule", risk_txt, "bad"))
        for reason in m.group(1).split("; "):
            reason = reason.strip()
            if reason:
                facts.append((reason[0].upper() + reason[1:], None, "bad"))
        w = re.search(r"weighted average across the 10 dimensions is still (\d+(?:\.\d+)?)", s)
        if w:
            facts.append(("Average alone would not decide it", f"Weighted avg {w.group(1)}", "warn"))
        return facts

    if "only on closed trades" in low and "sits unrealised" in low:
        m = re.search(r": (.+?) of loss sits unrealised(?: \((\d+)% of capital\))?", s)
        if m:
            chip = f"Unrealised {m.group(1)}" + (f" · {m.group(2)}% of capital" if m.group(2) else "")
            facts.append(("Loss hidden in open positions", chip, "bad"))
        m = re.search(r"profit factor into (\d+(?:\.\d+)?)", s)
        if m:
            facts.append(("Wins taken early, losses held", f"MTM PF {m.group(1)}", "bad"))
        return facts

    m = re.search(r"is holding (.+?) of unrealised loss, equal to (\d+)% of reference capital", s)
    if m:
        facts.append(("Unrealised loss not yet booked", f"{m.group(1)} · {m.group(2)}% of capital", "bad"))
        facts.append(("Headline metrics do not show it", surface_chip, "warn"))
        return facts

    m = re.search(r"has run (\d+) trades without ever booking a single loss", s)
    if m:
        facts.append(("Never booked a single loss", f"{m.group(1)} trades · 0 losses", "bad"))
        facts.append(("Headline figures only half true", surface_chip, "warn"))
        return facts

    m = re.search(r"(\d+)% of gross profit comes from a single market phase, ([^.]+)\.", s)
    if m:
        facts.append(("Profit from one market phase", f"{m.group(1)}% · {m.group(2).strip()}", "warn"))
        n = re.search(r"net losing in (\d+/6) phases", s)
        if n:
            facts.append(("Net losing in other phases", f"{n.group(1)} phases", "bad"))
        return facts

    if "without a single trade during a downtrend phase" in low:
        facts.append(("Good track record so far", surface_chip, "good"))
        facts.append(("Untested in downtrend", "Downtrend trades 0", "warn"))
        return facts

    m = re.search(r"across (\d+) closed trades, the expectancy per trade is (-?[\d,]+(?:\.\d+)?) USDT", s)
    if m:
        facts.append(("Losing money per trade", f"Expectancy {m.group(2)} USDT", "bad"))
        c = re.search(r"cumulative loss of (\S+?)\.?(?:\s|$)", s)
        if c:
            facts.append(("Cumulative loss", c.group(1).rstrip("."), "bad"))
        wr = re.search(r"win rate of (\d+)% sounds fine, but each winning trade is only (\d+(?:\.\d+)?) times", s)
        if wr:
            facts.append(("High win rate hides it", f"Win {wr.group(1)}% · payoff {wr.group(2)}", "warn"))
        facts.append(("Enough trades to conclude", f"{m.group(1)} trades", "warn"))
        return facts

    m = re.search(r"best of (\d+) candidates.*?genuine edge is only (\d+(?:\.\d+)?)%", s)
    if m:
        facts.append(("Picked as the best of many", f"{m.group(1)} candidates", "warn"))
        facts.append(("Edge close to a coin flip", f"Genuine edge {m.group(2)}%", "bad"))
        return facts

    m = re.search(r"profit factor (\d+(?:\.\d+)?) on closed trades, and (\d+(?:\.\d+)?) if every open position", s)
    if m:
        facts.append(("Honest book, no hidden loss", f"PF {m.group(1)} → {m.group(2)}", "good"))
        d = re.search(r"real drawdown recorded so far is (\d+(?:\.\d+)?)%", s)
        if d:
            facts.append(("Real drawdown so far", f"Max DD {d.group(1)}%", "good"))
        return facts

    if "no single anomaly severe enough" in low:
        facts.append(("No single decisive fault", surface_chip or "No veto", "good"))
        facts.append(("Score is the average across dimensions", risk_txt, "warn"))
        return facts

    return facts


# (prefix, value, suffix) -- the value is the bold figure.
_EvChunk = Tuple[str, str, str]
_EvPill = Tuple[str, str]  # (text, tone good|warn|bad|flat)


def _compact_proof(item: str) -> Optional[Tuple[str, List[_EvChunk], Optional[_EvPill]]]:
    t = " ".join(item.split())

    m = re.match(r"Profit factor (\d+(?:\.\d+)?) \(closed book\) → (\d+(?:\.\d+)?) \(open book closed too\)(?: — (.+))?$", t)
    if m:
        v = (m.group(3) or "").lower()
        pill: Optional[_EvPill] = None
        if "whole problem" in v:
            pill = ("Hidden loss", "bad")
        elif "would cost" in v:
            c = re.search(r"(\d+)% of the edge", v)
            pill = (f"-{c.group(1)}% edge" if c else "Edge cut", "warn")
        elif "not hiding" in v:
            pill = ("No hidden loss", "good")
        return "[PROFIT FACTOR]", [("Closed ", m.group(1), ""), ("→ MTM ", m.group(2), "")], pill
    m = re.match(r"Profit factor (\d+(?:\.\d+)?)$", t)
    if m:
        return "[PROFIT FACTOR]", [("PF ", m.group(1), "")], None

    m = re.match(r"Unrealised loss (.+?) = (\d+)% of capital, across (\d+) open positions$", t)
    if m:
        pct = int(m.group(2))
        pill = ("High", "bad") if pct >= 20 else (("Elevated", "warn") if pct >= 5 else ("Low", "good"))
        return "[UNREALIZED LOSS]", [("", m.group(1), ""), ("", f"{pct}%", " of capital"), ("", m.group(3), " open")], pill

    m = re.match(r"Stress scenario \(volatility (\S+?)x, spread (\S+?)x, liquidity (\S+?)\): (\w+)$", t)
    if m:
        state = m.group(4).lower()
        pill = ("Liquidated", "bad") if state == "liquidated" else ("Vulnerable", "warn")
        return "[STRESS TEST]", [("Vol ×", m.group(1), ""), ("Spread ×", m.group(2), ""), ("Liquidity ×", m.group(3), "")], pill

    m = re.match(r"Risk score (\d+) comes from the veto floor \(weighted average across 10 dimensions is only (\d+(?:\.\d+)?)\)", t)
    if m:
        return "[RISK VETO FLOOR]", [("Risk ", m.group(1), " = veto floor"), ("Weighted avg ", m.group(2), "")], ("Veto", "bad")

    m = re.match(r"Risk score (\d+) is the weighted average across 10 dimensions; heaviest: (.+)$", t)
    if m:
        return "[RISK DRIVERS]", [("Risk ", m.group(1), " = weighted avg"), ("Heaviest: ", m.group(2), "")], ("No veto", "flat")

    m = re.match(r"Monte Carlo ([\d,]+) scenarios × (\d+) trades: median ([+-]?\d+(?:\.\d+)?)% of capital(?:, p05 ([+-]?\d+(?:\.\d+)?)%)?(?:, worst ([+-]?\d+(?:\.\d+)?)%)?$", t)
    if m:
        chunks: List[_EvChunk] = [("", m.group(1), ""), ("× ", m.group(2), " trades"), ("Median ", m.group(3) + "%", "")]
        if m.group(4):
            chunks.append(("P05 ", m.group(4) + "%", ""))
        if m.group(5):
            chunks.append(("Worst ", m.group(5) + "%", ""))
        return "[MONTE CARLO]", chunks, None

    m = re.match(r"Simulated tail risk: (.+)$", t)
    if m:
        chunks = []
        for part in m.group(1).split(", "):
            p = re.match(r"worst 5% tail (loss|still profit) (\d+(?:\.\d+)?)%$", part)
            if p:
                chunks.append(("CVaR 95% ", ("-" if p.group(1) == "loss" else "+") + p.group(2) + "%", ""))
                continue
            p = re.match(r"probability of (loss|ruin) (\d+(?:\.\d+)?)%$", part)
            if p:
                chunks.append((f"P({p.group(1)}) ", p.group(2) + "%", ""))
                continue
            return None
        return "[TAIL RISK]", chunks, None

    if t.startswith("Never tested on the way down"):
        return "[REGIME BIAS]", [("Downtrend trades ", "0", "")], ("Untested", "warn")

    m = re.match(r"(\d+) trades, win rate (\d+)%, payoff (\d+(?:\.\d+)?)(?: → (.+))?$", t)
    if m:
        v = (m.group(4) or "").lower()
        pill = None
        e = re.search(r"erases (\d+(?:\.\d+)?) winning", v)
        if e:
            pill = (f"1 loss = {e.group(1)} wins", "bad")
        elif "well ahead" in v:
            pill = ("Wins ≫ losses", "good")
        return "[PAYOFF ASYMMETRY]", [("", m.group(1), " trades"), ("Win ", m.group(2) + "%", ""), ("Payoff ratio ", m.group(3), "")], pill

    m = re.match(r"Actual drawdown (\d+(?:\.\d+)?)%, Sharpe (-?\d+(?:\.\d+)?)(?:, longest losing streak (\d+) trades)?$", t)
    if m:
        chunks = [("Max DD ", m.group(1) + "%", ""), ("Sharpe ", m.group(2), "")]
        if m.group(3):
            chunks.append(("Loss streak ", m.group(3), ""))
        return "[DRAWDOWN / SHARPE]", chunks, None

    m = re.match(r"Probability of a genuine edge (\d+(?:\.\d+)?)% after discounting selection from (\d+) candidates( \(low reliability, tail too thick\))?$", t)
    if m:
        return "[DEFLATED SHARPE]", [("Genuine edge ", m.group(1) + "%", ""), ("", m.group(2), " candidates")], (("Low reliability", "warn") if m.group(3) else None)

    m = re.match(r"Quality (\d+)/100 dragged down by: (.+)$", t)
    if m:
        chunks = [("Quality ", m.group(1), "/100")]
        for part in m.group(2).split(", "):
            p = re.match(r"(.+?) (\d+(?:\.\d+)?)$", part)
            chunks.append((p.group(1) + " ", p.group(2), "") if p else ("", part, ""))
        return "[QUALITY DRAG]", chunks, None

    m = re.match(r"Strategy: (.+?); strongest in phase (.+?) \((\d+)% of gross profit\)(?:, net losing in (\d+/6) phases)?$", t)
    if m:
        style = m.group(1)
        chunks = [("", "", style[0].upper() + style[1:]), ("Best phase ", m.group(2), f" · {m.group(3)}% of profit")]
        pill = (f"Losing {m.group(4)} phases", "bad") if m.group(4) else None
        return "[STRATEGY]", chunks, pill

    m = re.match(r"Could not be computed \(requires individual trade data OKX does not publish\): (.+)$", t)
    if m:
        return "[NOT COMPUTED]", [("", "", p) for p in m.group(1).split(", ")], ("Trades not public", "flat")

    m = re.match(r"Sections with nothing to show for this bot are left out of this report rather than shown empty: (.+?) are never public", t)
    if m:
        names = re.split(r", and |, ", m.group(1))
        return "[HIDDEN SECTIONS]", [("", "", "Sections left out of this report:")] + [("", "", n) for n in names], ("Not public", "flat")

    m = re.match(r"Data limitations: (.+)$", t)
    if m:
        chunks = []
        for part in m.group(1).split("; "):
            p = re.match(r"measurement mode (\w+)$", part)
            q = re.match(r"the public ledger only covers (\d+/\d+) days of activity$", part)
            if p:
                chunks.append(("Mode ", p.group(1), ""))
            elif q:
                chunks.append(("Ledger covers ", q.group(1), " days"))
            else:
                chunks.append(("", part, ""))
        return "[DATA LIMITS]", chunks, None

    # The bot identity line: "<code> — BTC/CEX, 269 closed trades, reference
    # capital 381,720 USDT, 3.4 trades/day."
    m = re.match(r".+? — (.+?)\.?$", t)
    if m and re.search(r"/(?:CEX|DEX)\b|reference capital|closed trades", m.group(1)):
        chunks = []
        for part in m.group(1).split(", "):
            p = re.match(r"(\d[\d,]*) closed trades$", part)
            q = re.match(r"reference capital (.+)$", part)
            r = re.match(r"(\d+(?:\.\d+)?) trades/day$", part)
            if p:
                chunks.append(("", p.group(1), " trades"))
            elif q:
                chunks.append(("Ref. capital ", q.group(1), ""))
            elif r:
                chunks.append(("", r.group(1), " trades/day"))
            else:
                chunks.append(("", part, ""))
        return "[PROFILE]", chunks, None
    return None


_WHY_MIN_REASONS = 4


def _fact_key(label: str, chip: Optional[str]) -> str:
    """Which topic a WHY line covers, so a supplement never repeats it."""
    t = f"{label} {chip or ''}".lower()
    for key, words in (
        ("stress", ("stress", "liquidat")),
        ("unrealised", ("unrealised", "unrealized", "open position", "not yet booked")),
        ("pf", ("pf ", "profit factor", "book", "wins taken early")),
        ("downtrend", ("downtrend",)),
        ("regime", ("phase",)),
        ("ploss", ("p(loss)", "ending at a loss")),
        ("ruin", ("ruin", "wiping out")),
        ("tail", ("tail", "worst 5%", "worst-5%")),
        ("dsr", ("genuine edge", "best of many", "coin flip")),
        ("payoff", ("expectancy", "win ", "payoff", "per trade")),
        ("dd", ("drawdown", "max dd")),
        ("risk", ("veto", "weighted avg", "average", "risk ")),
        ("sample", ("trades",)),
    ):
        if any(w in t for w in words):
            return key
    return t


def _why_supplements(proof_items: List[str], result: Dict[str, Any]) -> List[Tuple[str, str, Optional[str], str]]:
    """Further reasons read off the evidence bullets and the scores, as
    (topic key, label, chip, tone) -- used to bring WHY up to
    `_WHY_MIN_REASONS` when the cause story itself names fewer. Same rule as
    `_why_facts`: every figure comes from the data, none is invented."""
    out: List[Tuple[str, str, Optional[str], str]] = []
    for item in proof_items:
        t = " ".join(item.split())
        m = re.match(r"Stress scenario \(volatility (\S+?)x, spread (\S+?)x, [^)]*\): (\w+)$", t)
        if m:
            chip = f"Vol ×{m.group(1)} · Spread ×{m.group(2)}"
            if m.group(3).lower() == "liquidated":
                out.append(("stress", "Fails the stress test", chip, "bad"))
            else:
                out.append(("stress", "Vulnerable under stress", chip, "warn"))
            continue
        m = re.match(r"Profit factor (\d+(?:\.\d+)?) \(closed book\) → (\d+(?:\.\d+)?) \(open book closed too\)(?: — (.+))?$", t)
        if m:
            v = (m.group(3) or "").lower()
            chip = f"PF {m.group(1)} → {m.group(2)}"
            if "whole problem" in v:
                out.append(("pf", "Open losses flip the profit", chip, "bad"))
            elif "would cost" in v:
                out.append(("pf", "Open book cuts the edge", chip, "warn"))
            else:
                out.append(("pf", "Honest book, no hidden loss", chip, "good"))
            continue
        m = re.match(r"Profit factor (\d+(?:\.\d+)?)$", t)
        if m:
            pf = float(m.group(1))
            label, tone = (
                ("Strong profit on closed trades", "good") if pf >= 1.5
                else (("Thin profit margin", "warn") if pf >= 1.0 else ("Losing on closed trades", "bad"))
            )
            out.append(("pf", label, f"PF {m.group(1)}", tone))
            continue
        m = re.match(r"Unrealised loss (.+?) = (\d+)% of capital", t)
        if m:
            pct = int(m.group(2))
            label, tone = (
                ("Large unrealised loss", "bad") if pct >= 20
                else (("Some unrealised loss", "warn") if pct >= 5 else ("Little unrealised loss", "good"))
            )
            out.append(("unrealised", label, f"{pct}% of capital", tone))
            continue
        m = re.match(r"Risk score (\d+) is the weighted average across 10 dimensions; heaviest: (.+)$", t)
        if m:
            out.append(("risk", "Main risk drivers", m.group(2), "warn"))
            continue
        m = re.match(r"Monte Carlo .*?, p05 ([+-]?\d+(?:\.\d+)?)%", t)
        if m:
            p05 = float(m.group(1))
            if p05 < 0:
                out.append(("mc", "Bad-case path loses money", f"P05 {m.group(1)}%", "bad" if p05 <= -20 else "warn"))
            else:
                out.append(("mc", "Even a bad-case path profits", f"P05 {m.group(1)}%", "good"))
            continue
        m = re.match(r"Simulated tail risk: (.+)$", t)
        if m:
            w5 = re.search(r"worst 5% tail loss (\d+(?:\.\d+)?)%", t)
            if w5:
                wv = float(w5.group(1))
                tone = "bad" if wv >= 30 else ("warn" if wv >= 15 else "good")
                label = "Mild losses in the worst 5%" if tone == "good" else "Heavy losses in the worst 5%"
                out.append(("tail", label, f"CVaR 95% -{w5.group(1)}%", tone))
            pm = re.search(r"probability of loss (\d+(?:\.\d+)?)%", t)
            if pm:
                pl = float(pm.group(1))
                tone = "bad" if pl >= 30 else ("warn" if pl >= 15 else "good")
                out.append(("ploss", "Chance of ending at a loss", f"P(loss) {pm.group(1)}%", tone))
            r = re.search(r"probability of ruin (\d+(?:\.\d+)?)%", t)
            if r:
                out.append(("ruin", "Risk of wiping out capital", f"P(ruin) {r.group(1)}%", "bad"))
            continue
        if t.startswith("Never tested on the way down"):
            out.append(("downtrend", "Untested in downtrend", "Downtrend trades 0", "warn"))
            continue
        m = re.match(r"(\d+) trades, win rate (\d+)%, payoff (\d+(?:\.\d+)?)(?: → (.+))?$", t)
        if m:
            v = (m.group(4) or "").lower()
            e = re.search(r"erases (\d+(?:\.\d+)?) winning", v)
            if e:
                out.append(("payoff", "Losses outweigh wins", f"1 loss = {e.group(1)} wins", "bad"))
            elif "well ahead" in v:
                out.append(("payoff", "Wins bigger than losses", f"Payoff {m.group(3)}", "good"))
            else:
                out.append(("payoff", "Wins and losses about even", f"Win {m.group(2)}% · payoff {m.group(3)}", "warn"))
            continue
        m = re.match(r"Actual drawdown (\d+(?:\.\d+)?)%, Sharpe (-?\d+(?:\.\d+)?)", t)
        if m:
            dd = float(m.group(1))
            label, tone = (
                ("Deep drawdown", "bad") if dd >= 30
                else (("Noticeable drawdown", "warn") if dd >= 15 else ("Shallow drawdown", "good"))
            )
            out.append(("dd", label, f"Max DD {m.group(1)}% · Sharpe {m.group(2)}", tone))
            continue
        m = re.match(r"Probability of a genuine edge (\d+(?:\.\d+)?)%", t)
        if m:
            p = float(m.group(1))
            out.append(("dsr", "Edge may be luck" if p < 60 else "Edge likely genuine", f"Genuine edge {m.group(1)}%", "bad" if p < 60 else "good"))
            continue
        m = re.match(r"Quality (\d+)/100 dragged down by: (.+)$", t)
        if m:
            out.append(("quality", "Quality dragged down", m.group(2).split(", ")[0], "warn"))
            continue
        m = re.search(r"net losing in (\d+/6) phases", t)
        if m and t.startswith("Strategy:"):
            out.append(("regime", "Losing in some market phases", f"{m.group(1)} phases", "bad"))
            continue
        if t.startswith("Data limitations:"):
            # What is not public is not talked about (project owner, 2026-09-24).
            continue

    # From the scores themselves.
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    n = result.get("trade_count") or perf.get("trade_count")
    if _is_finite_number(n) and 0 < float(n) < 30:
        out.append(("sample", "Too few trades to be sure", f"{int(float(n))} trades", "bad"))
    q = result.get("quality")
    if _is_finite_number(q):
        qv = float(q)
        out.append((
            "quality",
            "Strong strategy quality" if qv >= 70 else ("Middling strategy quality" if qv >= 50 else "Weak strategy quality"),
            f"Quality {qv:.0f}/100",
            "good" if qv >= 70 else ("warn" if qv >= 50 else "bad"),
        ))
    cf = result.get("confidence")
    if _is_finite_number(cf):
        cv = float(cf) * 100.0 if float(cf) <= 1.0 else float(cf)
        out.append((
            "confidence",
            "Assessment well supported" if cv >= 70 else "Assessment only partly supported",
            f"Confidence {cv:.0f}%",
            "good" if cv >= 70 else "warn",
        ))
    rank = {"bad": 0, "warn": 1, "good": 2}
    return sorted(out, key=lambda f: rank.get(f[3], 1))


def _is_prose(text: str) -> bool:
    return bool(re.search(r"[.!?]\s+[A-Z]", text)) or " -- " in text or len(text) > 110


def _ev_chunk_html(chunk: _EvChunk) -> str:
    pre, val, suf = chunk
    if not val:
        return f'<span class="ev-chunk">{_esc(pre + suf)}</span>'
    neg = " quant-num-neg" if val.startswith("-") else ""
    # "10,000 × 269 trades" reads as one figure, not two spaced chunks.
    join = " ev-join" if pre.startswith("× ") else ""
    return (
        f'<span class="ev-chunk{join}">{_esc(pre)}<b class="quant-num{neg}">{_esc(val)}</b>{_esc(suf)}</span>'
    )


_NOT_PUBLIC_TAGS = frozenset({"[DATA LIMITS]", "[NOT COMPUTED]", "[HIDDEN SECTIONS]"})


def _render_quant_terminal_evidence(proof_items: List[str]) -> Tuple[str, List[str]]:
    """Evidence rows laid out like the redesign preview: [TAG] | figures |
    verdict pill. Returns (rows html, prose lines) -- prose that has no
    figures to lay out goes to the section's hover note instead of a row."""
    if not proof_items:
        return "", []
    rows = []
    notes: List[str] = []
    for item in proof_items:
        compact = _compact_proof(item)
        if compact is not None and compact[0] in _NOT_PUBLIC_TAGS:
            # Rows that only say what is not public are left out (project
            # owner, 2026-09-24).
            continue
        if compact is not None:
            tag, chunks, pill = compact
            vals_html = "".join(_ev_chunk_html(c) for c in chunks)
            end_html = (
                f'<span class="ev-pill ev-pill-{pill[1]}">{_esc(pill[0])}</span>' if pill else ""
            )
        else:
            tag = _detect_quant_tag(item)
            main_text, cons_text = _split_quant_consequence(item)
            tag_name = tag.strip("[]").lower()
            if main_text.lower().startswith(tag_name + " "):
                main_text = main_text[len(tag_name) + 1 :].strip()
            parts = _split_top_level_commas(main_text)
            end_html = ""
            if cons_text:
                if cons_text[0].islower() and not cons_text.startswith("http"):
                    cons_text = cons_text[0].upper() + cons_text[1:]
                tone = _consequence_tone(tag, cons_text)
                if tone:
                    end_html = f'<span class="ev-pill ev-pill-{tone}">{_esc(cons_text)}</span>'
                else:
                    parts += _split_top_level_commas(cons_text)
            vals_html = "".join(
                f'<span class="ev-chunk">{_highlight_quant_numbers(c)}</span>' for c in parts
            )
        tag_html = _calc_label_html(tag, _QUANT_TAG_INFO_KEY.get(tag))
        rows.append(
            f'<div class="quant-audit-row">'
            f'<div class="quant-audit-tag">{tag_html}</div>'
            f'<div class="quant-audit-main">{vals_html}</div>'
            f'<div class="quant-audit-end">{end_html}</div>'
            f'</div>'
        )
    if not rows:
        return "", notes
    return (
        '<div class="quant-audit-terminal">'
        f'<div class="quant-audit-rows">{"".join(rows)}</div>'
        '</div>',
        notes,
    )


def _render_headline_items(items: Sequence[Dict[str, Any]]) -> str:
    """The strip, from precomputed items -- `{label, key, value, tone}`.

    A portfolio page passes its own five numbers here (the book as one
    account: `data._portfolio_page_overrides`); deriving them from the merged
    order book below would run single-bot formulas over a pooled trade list.
    """
    cells = []
    for item in items:
        if not isinstance(item, dict):
            continue
        tone = str(item.get("tone") or "qrs-neutral")
        cells.append(
            f'<div class="qrs-item {_esc(tone)}">'
            f'<span class="qrs-label">{_calc_label_html(str(item.get("label") or ""), item.get("key"))}</span>'
            f'<span class="qrs-value">{_esc(item.get("value") if item.get("value") is not None else "—")}</span>'
            "</div>"
        )
    return f'<div class="quick-risk-strip">{"".join(cells)}</div>' if cells else ""


def _render_quick_risk_strip(result: Dict[str, Any]) -> str:
    headline = result.get("headline")
    if isinstance(headline, list) and headline:
        return _render_headline_items(headline)
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
    # A portfolio's reference capital is the sum of its members' (the merged
    # book's `PORTFOLIO_SUM`): name it for what it is.
    cap_source = str(((evidence.get("current_state") or {}) if isinstance(evidence.get("current_state"), dict) else {}).get("reference_capital_source") or "")
    cap_label = "Combined capital" if cap_source.startswith("PORTFOLIO") or isinstance(result.get("portfolio"), dict) else "Reference capital"

    # 2. Unrealised Float PnL
    open_loss = perf.get("open_loss")
    open_loss_pct = perf.get("open_loss_to_capital_pct")
    # `open_loss_to_capital_pct` is ALREADY a percentage (the fusion rule
    # compares it with 15.0) and `open_loss` a positive loss size. The old
    # "<= 1 means a fraction" guess multiplied every sub-1% loss by 100
    # (0.19% of capital read "+18.8%"), and the "+" sign in green presented
    # a loss as a gain.
    if _is_finite_number(open_loss_pct):
        float_pct = abs(float(open_loss_pct))
        float_cls = "qrs-danger" if float_pct >= 15 else ("qrs-warn" if float_pct >= 5 else "qrs-safe")
        digits = 2 if 0 < float_pct < 1 else 1
        float_text = f"{-float_pct:.{digits}f}%" if float_pct else "0.0%"
        if _is_finite_number(open_loss) and float(open_loss):
            float_text += f" ({-abs(float(open_loss)):,.0f} USDT)"
    elif _is_finite_number(open_loss):
        val_ol = abs(float(open_loss))
        float_cls = "qrs-warn" if val_ol else "qrs-safe"
        float_text = f"{-val_ol:,.0f} USDT" if val_ol else "0 USDT"
    else:
        open_pos = perf.get("open_positions")
        if open_pos == 0:
            float_cls = "qrs-safe"
            float_text = "0.0%"
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
        # A fall deeper than the whole equity is a wipe-out: drawdown is a
        # share of equity and stops at 100%.
        dd_text = "-100% · wiped out" if dd_val >= 99.95 else f"-{dd_val:.1f}%"
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
        f'<span class="qrs-label">{_calc_label_html(cap_label, "qrs_reference_capital")}</span>'
        f'<span class="qrs-value">{_esc(cap_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {float_cls}">'
        f'<span class="qrs-label">{_calc_label_html("Unrealized loss", "qrs_unrealised_loss")}</span>'
        f'<span class="qrs-value">{_esc(float_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {dd_cls}">'
        f'<span class="qrs-label">{_calc_label_html("Max drawdown", "qrs_max_drawdown")}</span>'
        f'<span class="qrs-value">{_esc(dd_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {wr_cls}">'
        f'<span class="qrs-label">{_calc_label_html("Win rate", "qrs_win_rate")}</span>'
        f'<span class="qrs-value">{_esc(wr_text)}</span>'
        f'</div>'
        f'<div class="qrs-item {sample_cls}">'
        f'<span class="qrs-label">{_calc_label_html("Closed trades", "qrs_observed_trades")}</span>'
        f'<span class="qrs-value">{_esc(sample_text)}</span>'
        f'</div>'
        f'</div>'
    )


# The risk tier the old verdict box carried, now the compact pill on the
# WHY row (same three tiers, an assessment -- never advice; detail in the tooltip).
_ACTION_BY_TONE: Dict[str, Tuple[str, str]] = {
    ZONE_DANGER: (
        "High",
        "Loss, drawdown or ruin readings sit in the danger band; the measured record "
        "shows a real risk of severe loss.",
    ),
    ZONE_WARNING: (
        "Elevated",
        "Tail risk is elevated or the sample is too thin to be fully reliable.",
    ),
    ZONE_NORMAL: (
        "Normal",
        "Risk readings are within normal bounds for the measured period.",
    ),
}


def _parse_conclusion_lines(text_lines: Sequence[Any]) -> Dict[str, Any]:
    """The engine's conclusion text split into its parts (verdict, causes,
    evidence bullets, warnings, limitations, overview, other) -- shared by the
    Conclusion section and the short answer at the top of the page."""
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
            # Split on sentence ends, not ";" -- the cause story is prose, and
            # a ";" inside a sentence ("tail risk; stress scenario ends in
            # liquidation. A veto exists...") used to cut it mid-thought.
            subs = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+(?=[^\sa-zà-ỹ])", rest)
                if s.strip()
            ]
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

    return {
        "verdict_info": verdict_info, "why_items": why_items, "proof_items": proof_items,
        "warning_items": warning_items, "limitation_items": limitation_items,
        "overview_parts": overview_parts, "other_lines": other_lines,
    }


def _conclusion_facts(result: Dict[str, Any], why_items: Sequence[str], proof_items: Sequence[str],
                      why_tone: str) -> List["_WhyFact"]:
    """The WHY reasons (label, figure chip, tone), worst first -- the list the
    Conclusion shows and the short answer takes its reason from."""
    story = " ".join(why_items)
    facts = _why_facts(story, result) if story else []
    if not facts:
        # Unknown phrasing: the sentences themselves, one marker each.
        fallback_tone = {"success": "good", "warning": "warn"}.get(why_tone, "bad")
        facts = [(w, None, fallback_tone) for w in why_items]
    # Every reason carries its figure, as in the preview: a reason without
    # one borrows the chip of the evidence bullet on the same topic (the
    # veto's "extreme simulated tail risk" -> "Worst-5% -36.7%"), and is
    # dropped when there is none -- the top-up below refills the list.
    supplements = _why_supplements(proof_items, result)
    chip_by_key: Dict[str, str] = {}
    for key, _label, chip, _tone in supplements:
        if chip and key not in chip_by_key:
            chip_by_key[key] = chip
    is_veto_story = bool(facts) and facts[0][0] == "Blocked by a veto rule"
    filled: List[_WhyFact] = []
    for label, chip, tone in facts:
        if not chip and not _is_prose(label):
            chip = chip_by_key.get(_fact_key(label, None)) or ("Veto trigger" if is_veto_story else None)
            if not chip:
                continue
        filled.append((label, chip, tone))
    facts = filled
    # At least `_WHY_MIN_REASONS` main reasons (project owner, 2026-09-24):
    # top up from the evidence bullets / scores, skipping any topic already
    # named, worst first.
    if len(facts) < _WHY_MIN_REASONS:
        seen = {_fact_key(label, chip) for label, chip, _ in facts}
        for key, label, chip, tone in supplements:
            if len(facts) >= _WHY_MIN_REASONS:
                break
            if key in seen:
                continue
            seen.add(key)
            facts.append((label, chip, tone))
    return facts


def _render_conclusion(result: Dict[str, Any], compact: bool = False) -> str:
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

    _parsed = _parse_conclusion_lines(text_lines)
    verdict_info = _parsed["verdict_info"]
    why_items: List[str] = _parsed["why_items"]
    proof_items: List[str] = _parsed["proof_items"]
    warning_items: List[str] = _parsed["warning_items"]
    limitation_items: List[str] = _parsed["limitation_items"]
    overview_parts: List[str] = _parsed["overview_parts"]
    other_lines: List[str] = _parsed["other_lines"]

    blocks: List[str] = []

    # The verdict chip ("DRAWDOWN: X · QUALITY: Y") that used to open this
    # section now sits in the page header on the bot-name row -- see
    # `_verdict_chip_html`/`_render_header` -- together with the zone logic
    # (portfolio HIGH_CORRELATION_CLUSTER floor included). The
    # EMERGENCY/CAUTION/STANDARD callout box that used to sit under it was
    # dropped at the project owner's request. Only the detail text after
    # " — " is still used here, by the QUANTITATIVE EVIDENCE block below.
    verdict_detail = verdict_info[1].strip() if verdict_info else ""

    # Hero scores (risk/quality/confidence) and the quick risk metrics strip
    # used to render here, inside the Analyst Result tab's Conclusion. They
    # now render once, globally, right below the bot identity in the page
    # header -- see `_render_header` -- so they stay visible on the Market
    # and Positions tabs too instead of disappearing when the reader leaves
    # this tab.

    # Sample count — moved into QUANTITATIVE EVIDENCE below
    evidence = result.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    performance = evidence.get("performance")
    performance = performance if isinstance(performance, dict) else {}
    sample_count = result.get("trade_count") or performance.get("trade_count")

    # 3. Why / Causes -- laid out like the redesign preview: the action pill
    # on the label row, each cause with a marker and (when the sentence
    # carries one) its key figure as a chip, then the peer comparison.
    _, why_tone = _verdict_headline_and_tone(result)
    action_label, action_desc = _ACTION_BY_TONE.get(why_tone, _ACTION_BY_TONE[ZONE_NORMAL])
    action_html = (
        f'<span class="action-pill tone-{why_tone}">Risk: {_esc(action_label)}'
        f'<i class="info-ic" tabindex="0">i<span class="info-tip">{_esc(action_desc)}</span></i></span>'
    )
    icons = {
        "good": '<svg class="why-icon tone-good" viewBox="0 0 16 16" aria-hidden="true">'
        '<path d="M3 8.5l3 3 7-7"/></svg>',
        "warn": '<svg class="why-icon tone-warn" viewBox="0 0 16 16" aria-hidden="true">'
        '<circle cx="8" cy="8" r="6.5"/><path d="M8 4.5v4.5M8 11.5h.01"/></svg>',
        "bad": '<svg class="why-icon tone-bad" viewBox="0 0 16 16" aria-hidden="true">'
        '<circle cx="8" cy="8" r="6.5"/><path d="M8 4.5v4.5M8 11.5h.01"/></svg>',
    }
    facts = _conclusion_facts(result, why_items, proof_items, why_tone)
    if compact:
        # Overview: the two causes that matter most, worst first.
        facts = sorted(facts, key=lambda f: {"bad": 0, "warn": 1}.get(f[2], 2))[:2]
    why_rows = []
    for label, chip, tone in facts:
        chip_html = (
            f'<span class="why-chip why-chip-{tone}">{_esc(chip)}</span>' if chip else ""
        )
        why_rows.append(
            f'<div class="why-item">{icons.get(tone, icons["warn"])}'
            f'<span class="why-text">{_esc(label)}{chip_html}</span></div>'
        )
    grid_cls = "why-grid" if len(why_rows) > 1 else "why-grid why-grid-single"
    why_body = f'<div class="{grid_cls}">{"".join(why_rows)}</div>' if why_rows else ""
    blocks.append(
        # Card title + action pill on one row (preview), then "Why" as the
        # first sub-label.
        '<div class="conclusion-section-block conclusion-why-block">'
        '<div class="why-head">'
        '<span class="mc-title conclusion-title" title="Conclusion">Why</span>'
        f'{action_html}'
        '</div>'

        + f'{why_body}'
        '</div>'
    )

    peer_html = "" if compact else _render_peer_comparison(result, sample_count)
    if peer_html:
        blocks.append(peer_html)

    # 4. Proof / Quantitative Evidence (Terminal View)
    # Includes: scorecard chips, narrative paragraph (from verdict detail / other_lines), revisit banner, audit log
    has_quant_content = bool(proof_items or overview_parts or other_lines or verdict_detail)
    if has_quant_content:

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
        # The bad case (P95), not the typical one: a risk figure is read at
        # the tail (project owner, 2026-09-25).
        _dd_val = _mc.get("p95_max_drawdown") if _is_finite_number(_mc.get("p95_max_drawdown")) else (
            _med_dd if _is_finite_number(_med_dd) else _mc.get("median_max_drawdown"))
        _ruin_val = _mc.get("probability_of_ruin") if _is_finite_number(_mc.get("probability_of_ruin")) else _mc.get("p_ruin")
        _dd_label, _dd_key = ("Sim. max DD · P95" if _is_finite_number(_mc.get("p95_max_drawdown")) else "Median sim. max DD"), "qe_sim_max_dd"
        _ruin_label, _ruin_key = "Probability of ruin", "qe_ruin"
        # A portfolio page's simulated drawdown and ruin come from the JOINT
        # simulation (all members, co-movement kept), not the single-bot one
        # over the merged order book.
        _hs = result.get("headline_sim") if isinstance(result.get("headline_sim"), dict) else None
        if _hs:
            # `max_drawdown` is whichever scenario the data chose to headline
            # (the joint P95 today); older saved documents carry the median.
            _dd_val = _hs.get("max_drawdown", _hs.get("median_max_drawdown"))
            # Joint p_ruin is a PERCENT; the chip below reads (0, 1] as a
            # fraction -- 0.5% would print as 50% if passed through as is.
            _pr = _hs.get("p_ruin")
            _ruin_val = float(_pr) / 100.0 if _is_finite_number(_pr) else None
            _dd_label = str(_hs.get("dd_label") or _dd_label)
            _dd_key = str(_hs.get("dd_key") or _dd_key)
            _ruin_label = str(_hs.get("ruin_label") or _ruin_label)
            _ruin_key = str(_hs.get("ruin_key") or _ruin_key)

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

        def _qe_chip(label: str, value: str, cls: str, info_key: Optional[str] = None) -> str:
            return (
                f'<div class="qe-chip {cls}">'
                f'<span class="qe-chip-label">{_calc_label_html(label, info_key)}</span>'
                f'<span class="qe-chip-value">{_esc(value)}</span>'
                f'</div>'
            )

        chips = []
        if _is_finite_number(_q):
            qv = float(_q)
            q_cls = "qe-chip-good" if qv >= 60 else ("qe-chip-warn" if qv >= 35 else "qe-chip-bad")
            chips.append(_qe_chip("Quality", f"{int(round(qv))}/100", q_cls, "quality_score"))
        if _is_finite_number(_r):
            rv = float(_r)
            r_cls = "qe-chip-bad" if rv >= 70 else ("qe-chip-warn" if rv >= 40 else "qe-chip-good")
            chips.append(_qe_chip("Risk", f"{int(round(rv))}/100", r_cls, "risk_score"))
        if _is_finite_number(_dd_val):
            dv = float(_dd_val)
            dd_cls = "qe-chip-bad" if dv >= 20 else ("qe-chip-warn" if dv >= 10 else "qe-chip-good")
            chips.append(_qe_chip(_dd_label, f"{dv:.1f}%", dd_cls, _dd_key))
        if _is_finite_number(_ruin_val):
            ruin_num = float(_ruin_val)
            ruin_pct = ruin_num * 100.0 if (0.0 < ruin_num <= 1.0) else ruin_num
            if ruin_pct > 0:
                ruin_cls = "qe-chip-bad" if ruin_pct >= 10 else "qe-chip-warn"
                chips.append(_qe_chip(_ruin_label, f"{ruin_pct:.0f}%", ruin_cls, _ruin_key))
            else:
                chips.append(_qe_chip(_ruin_label, "0%", "qe-chip-good", _ruin_key))
        if _is_finite_number(_cf):
            cfv = float(_cf) * 100.0 if float(_cf) <= 1.0 else float(_cf)
            cf_cls = "qe-chip-good" if cfv >= 70 else ("qe-chip-warn" if cfv >= 45 else "qe-chip-bad")
            chips.append(_qe_chip("Confidence", f"{int(round(cfv))}%", cf_cls, "confidence"))
        # Sample size chip
        if _is_finite_number(sample_count) and float(sample_count) > 0:
            n = int(float(sample_count))
            s_cls = "qe-chip-good" if n >= 50 else "qe-chip-warn"
            chips.append(
                f'<div class="qe-chip {s_cls}">'
                f'<span class="qe-chip-label">{_calc_label_html("Sample", "trade_count")}</span>'
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
        # Folded into the SAME tagged audit-log rows as `proof_items`
        # (auto-tagged via `_detect_quant_tag`) instead of a separate
        # flowing paragraph in its own box -- project owner's own report on
        # a real bot page, 2026-09-22: "ném nội dung đó vào bên nội dung
        # từng gạch đầu dòng đẹp mắt ở trên" (throw that content into the
        # same nicely-bulleted rows above). One combined call so every row
        # -- proof bullets and this closing text alike -- sits inside a
        # single `.quant-audit-terminal` box, not two stacked ones.
        # The verdict's closing prose (`cleaned_narrative`) is left out: WHY,
        # the action pill and the rows above already say it, in figures --
        # project owner (2026-09-24): "ngắn gọn chủ yếu tham số".
        quant_evidence_html, _ = _render_quant_terminal_evidence(
            proof_items + [ln for ln in narrative_lines if ln != cleaned_narrative]
        )
        qe_label = "Quantitative evidence"
        # Calculation rows behind a "Show calculation details" toggle, as in
        # the redesign preview; the toggle lists the row names.
        qe_rows_html = ""
        if quant_evidence_html and not compact:
            row_tags = []
            for t in re.findall(r'class="param-label"[^>]*>\[([^\]]+)\]|<div class="quant-audit-tag">\[([^\]]+)\]', quant_evidence_html):
                name = (t[0] or t[1]).title()
                if name not in row_tags:
                    row_tags.append(name)
            qe_rows_html = _collapse_toggle(
                "Show calculation details", "Hide calculation details", " · ".join(row_tags), quant_evidence_html
            )

        revisit_html = ""
        if revisit_text and not compact:
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
            f'<div class="conclusion-sub-title">{qe_label}</div>'
            f'{scorecard_html}'
            f'{qe_rows_html}'
            f'{narrative_html}'
            f'{revisit_html}'
            '</div>'
        )


    # 5. Hidden Warnings
    if warning_items:
        items_html = "".join(f"<li>{_esc(w)}</li>" for w in warning_items)
        blocks.append(_note_chip(
            f"Hidden risk warning{'s' if len(warning_items) > 1 else ''} · {len(warning_items)}",
            "; ".join(warning_items), "danger"))

    # 7. Limitations & Missing Data Notes
    limitation_html = ""

    if limitation_items and not compact:
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

    # No printed title and no "Methodology & interpretation" note -- both
    # dropped at the project owner's request (2026-09-24).
    body = '<div class="conclusion-body-wrap">' + "".join(blocks) + limitation_html + "</div>"
    return _section("Conclusion", body, tone="primary", anchor=None if compact else "ket-luan")


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
        "XRP": "#7c8597",
        "ADA": "#0033ad",
        "NEAR": "#7c8597",
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

    # Multi-asset: the part of trading value that is neither resolved nor
    # unresolved is still named symbol by symbol when the exposure map has
    # them (each one "not measured"), instead of one anonymous "Others".
    listed = {str(m.get("symbol", "")).strip() for m in list(resolved_list) + list(unresolved_list)}
    not_measured = [
        (sym, float(v) * 100.0) for sym, v in sorted(share_map.items(), key=lambda kv: -(float(kv[1]) if _is_finite_number(kv[1]) else 0.0))
        if _is_finite_number(v) and float(v) > 0 and str(sym) not in listed
    ] if has_full_coverage_data else []
    if not_measured:
        for sym, share in not_measured:
            label_inside = f'<span class="cov-seg-sym">{_esc(sym)}</span>' if share >= 4.0 else ""
            segments_html.append(
                f'<div class="cov-bar-seg cov-seg-unallocated" style="width:{share:.2f}%;flex-basis:{share:.2f}%;" '
                f'title="{_esc(sym)}: {_pct(share, 1)} of trading value (Not measured) · below the share the analysis looks up. Not inferred from other markets.">'
                f'<div class="cov-seg-inner">{label_inside}</div></div>'
            )
        rem_pct = 0.0
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

    # Legend: every symbol with its share and status (multi-asset).
    legend_items = []
    for idx_m, m in enumerate(resolved_list):
        sym = str(m.get("symbol", "")).strip()
        base_sym = sym.split("-")[0].upper()
        color = asset_brand_colors.get(base_sym, fallback_palette[idx_m % len(fallback_palette)])
        legend_items.append(f'<span class="cv-leg"><i style="background:{color}"></i><b>{_esc(sym)}</b><em>{_pct(float(m.get("share_pct", 0) or 0), 0)}</em></span>')
    for m in unresolved_list:
        sym = str(m.get("symbol", "")).strip()
        legend_items.append(f'<span class="cv-leg"><i class="cv-hatch"></i><b>{_esc(sym)}</b><em>{_pct(float(m.get("share_pct", 0) or 0), 0)}</em>'
                            '<span class="st-chip st-chip-warn pv-state">Unresolved</span></span>')
    for sym, share in not_measured:
        legend_items.append(f'<span class="cv-leg"><i class="cv-hatch"></i><b>{_esc(sym)}</b><em>{("&lt;1%" if share < 0.5 else _pct(share, 0))}</em></span>')
    if not_measured:
        legend_items.append('<span class="cv-leg"><span class="st-chip st-chip-flat pv-state">Hatched = not measured</span></span>')
    legend_html = f'<div class="cv-legend">{"".join(legend_items)}</div>' if legend_items else ""

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

    # Laid out like the redesign preview: title + target status, three tiles
    # (current coverage, target, resolved/unresolved count), the stacked bar
    # with its target pin, then the resolved/unresolved line. The old
    # always-open methodology block is gone (project owner, 2026-09-24).
    met = not is_under_target
    n_unres = len([m for m in unresolved_list if float(m.get("share_pct", 0) or 0) > 0])
    tiles = (
        '<div class="cv-tiles">'
        '<div class="cv-tile cv-tile-main"><div class="st-label">Data coverage benchmark</div>'
        f'<div class="cv-big {"pv-v-good" if met else "pv-v-warn"}">{_pct(headline_pct, 0)}<span>current</span></div></div>'
        f'<div class="cv-tile"><div class="cv-tile-l">Target</div><div class="cv-mid">{target_pct:.0f}%</div></div>'
        '<div class="cv-tile"><div class="cv-tile-l">Resolved / unresolved</div>'
        f'<div class="cv-mid"><span class="pv-v-good">{len(resolved_list)}</span> <span class="cv-unit">markets</span> / '
        f'<span class="{"pv-v-warn" if n_unres else ""}">{n_unres}</span></div></div>'
        "</div>"
    )
    head = (
        '<div class="gc-head"><span class="mc-title" title="Market being scored">Data coverage</span>'
        f'<span class="st-chip {"st-chip-good" if met else "st-chip-warn"}">{"✓ Target met" if met else "⚠ Under target"}</span></div>'
    )
    card_body = (
        '<div class="cov-card-wrap cv-wrap">'
        f"{head}{tiles}{sublabels_html}"
        '<div class="cov-bar-wrapper">'
        f'  <div class="cov-stacked-bar">{"".join(segments_html)}</div>'
        f'  {target_line_html}'
        '</div>'
        f'{legend_html}'
        f'{warning_html}'
        f'{secondary_html}'
        '</div>'
    )
    return _section("Market being scored", card_body, anchor="thi-truong")


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


def _cap_span(text: str, cls: str = "") -> str:
    """Enum label kept lower-case in the markup (tests and search match the
    vocabulary as written) and capitalised on screen by CSS `::first-letter`."""
    extra = f" {cls}" if cls else ""
    return f'<span class="cap{extra}">{_esc(text)}</span>'


def _split_label(label: str) -> Tuple[str, str]:
    """"trend-following (buys as price rises, ...)" -> ("trend-following",
    "buys as price rises, ..."): the short name goes on the tile, the
    explanation into its hover title."""
    m = re.match(r"^(.*?) \((.+)\)$", label)
    return (m.group(1), m.group(2)) if m else (label, "")


def _render_phase_breakdown_table(strategy: Dict[str, Any]) -> str:
    """The pha × cách-đánh cross-tab (coordinator's own explicit addendum):
    one row per market phase the bot was ever measured in, sorted by profit
    contribution descending (the phase that made the money leads), each row
    tagged with its own three-tier confidence (`_phase_confidence_vi`) so a
    1-2 trade phase can never read as equally solid evidence as a 15-trade
    one. Returns "" (never a broken empty table) when there is no phase
    breakdown to show at all.

    Laid out like the redesign preview: best/worst phase as pills on the
    caption row, a dot on those two rows, a bar under win rate and share of
    profit, PnL in USDT without the unit repeated on every row.
    """
    rows = strategy.get("phase_breakdown")
    if not isinstance(rows, list) or not rows:
        return ""
    ordered = sorted(
        (r for r in rows if isinstance(r, dict)), key=_phase_row_sort_key, reverse=True
    )
    if not ordered:
        return ""
    best_phase = strategy.get("best_phase")
    worst_phase = strategy.get("worst_phase")

    def _bar(pct: Any, cls: str) -> str:
        if not _is_finite_number(pct):
            return ""
        w = max(0.0, min(100.0, float(pct)))
        return f'<span class="st-bar"><span class="st-bar-fill {cls}" style="width:{w:.0f}%"></span></span>'

    table_rows = []
    for row in ordered:
        trades = row.get("trades")
        confidence = _phase_confidence_vi(trades)
        phase = row.get("phase")
        dot = ""
        if phase and phase == best_phase:
            dot = '<span class="st-dot st-dot-best" title="Best phase"></span>'
        elif phase and phase == worst_phase:
            dot = '<span class="st-dot st-dot-worst" title="Worst phase"></span>'
        else:
            dot = '<span class="st-dot"></span>'
        phase_cell = dot + _cap_span(_phase_label_vi(phase), "st-phase-name")
        if confidence == PHASE_CONFIDENCE_INSUFFICIENT_VI:
            phase_cell += (
                f' <span class="st-conf st-conf-bad" title="Fewer than {PHASE_CONFIDENCE_THIN_TRADES} trades: not representative">'
                f"{_esc(PHASE_CONFIDENCE_INSUFFICIENT_VI)}</span>"
            )
        elif confidence == PHASE_CONFIDENCE_THIN_VI:
            phase_cell += (
                f' <span class="st-conf" title="{PHASE_CONFIDENCE_THIN_TRADES}-{PHASE_CONFIDENCE_ENOUGH_TRADES - 1} trades: reference only">'
                f"{_esc(PHASE_CONFIDENCE_THIN_VI)}</span>"
            )
        pnl = row.get("total_pnl")
        if _is_finite_number(pnl):
            f_pnl = float(pnl)
            tone = "pos" if f_pnl > 0 else ("neg" if f_pnl < 0 else "zero")
            pnl_cell = f'<span class="st-num st-pnl-{tone}">{f_pnl:+,.0f}</span>'
        else:
            pnl_cell = '<span class="st-num">—</span>'
        win = row.get("win_rate")
        share = row.get("profit_share_pct")
        table_rows.append(
            [
                phase_cell,
                f'<span class="st-num">{_esc(_num(trades, 0))}</span>',
                f'<span class="st-barcell">{_bar(win, "st-bar-win")}<span class="st-num">{_esc(_pct(win, 0))}</span></span>',
                pnl_cell,
                f'<span class="st-num">{_esc(_pct(row.get("long_share_pct"), 0))} long</span>',
                f'<span class="st-num">{_esc(_num(row.get("average_leverage"), 1))}x</span>',
                f'<span class="st-num">{_esc(_num(row.get("median_hold_minutes"), 0))} min</span>',
                f'<span class="st-barcell">{_bar(share, "st-bar-share")}<span class="st-num">{_esc(_pct(share, 0))}</span></span>',
            ]
        )
    pills = ""
    if best_phase:
        pills += f'<span class="st-pill st-pill-good">Best: {_cap_span(_phase_label_vi(best_phase))}</span>'
    if worst_phase:
        pills += f'<span class="st-pill st-pill-bad">Worst: {_cap_span(_phase_label_vi(worst_phase))}</span>'
    head = (
        '<div class="st-head">'
        '<span class="st-label" title="Each closed trade is tagged with the market phase at entry (trend x volatility). '
        'Sorted by share of gross profit.">Performance by market phase</span>'
        f'<span class="st-pills">{pills}</span>'
        "</div>"
    )
    table_html = _table(
        ["Market phase", "Trades", "Win rate", "PnL (USDT)", "Long share", "Avg leverage", "Median hold", "Share of profit"],
        table_rows,
    )
    return f'<div class="st-phase">{head}{table_html}</div>'


def _render_strategy_section(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return ""
    strategy = evidence.get("strategy")
    behavioral = evidence.get("behavioral")
    if not isinstance(strategy, dict) or not isinstance(behavioral, dict) or _no_trades(result):
        return ""

    # -- 4 tiles: profile, bias, entry style, phase coverage -----------------
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
    profile_main, profile_note = _split_label(profile_label)
    style_main, style_note = _split_label(style_label)
    style_title = " · ".join(
        t for t in (style_note, str(strategy.get("entry_style_evidence") or "")) if t
    )

    # Long share across the trades that were assigned a phase -- the only
    # place a per-trade long/short split is available on this page.
    long_n = long_sum = 0.0
    breakdown = strategy.get("phase_breakdown")
    for r in breakdown if isinstance(breakdown, list) else []:
        if isinstance(r, dict) and _is_finite_number(r.get("trades")) and _is_finite_number(r.get("long_share_pct")):
            long_n += float(r["trades"])
            long_sum += float(r["trades"]) * float(r["long_share_pct"])
    bias_sub = ""
    if long_n > 0:
        bias_sub = (
            f' <span class="st-tile-sub" title="Long share of the {long_n:,.0f} closed trades '
            f'assigned to a market phase">{long_sum / long_n:.0f}%</span>'
        )

    coverage = strategy.get("phase_coverage_pct")

    def _tile(label: str, value_html: str, title: str = "") -> str:
        t = f' title="{_esc(title)}"' if title else ""
        return (
            f'<div class="st-tile"{t}><div class="st-tile-l">{_esc(label)}</div>'
            f'<div class="st-tile-v">{value_html}</div></div>'
        )

    tiles = (
        '<div class="st-tiles">'
        + _tile("Profile", _cap_span(profile_main), "Observed profile from closed trades"
                + (f" -- {profile_note}" if profile_note else ""))
        + _tile("Directional bias", _cap_span(bias_label) + bias_sub)
        + _tile("Entry style", _cap_span(style_main), style_title)
        + _tile(
            "Phase coverage",
            f'<span class="st-num">{_esc(_pct(coverage, 1))}</span>',
            "Share of trades that could be assigned to a specific market phase",
        )
        + "</div>"
    )

    coverage_warning = ""
    if isinstance(coverage, (int, float)) and coverage < PHASE_COVERAGE_WARN_PCT:
        coverage_warning = (
_note_chip(f"Phase unknown for {_pct(100.0 - coverage, 0)} of trades · hint only",             '<div class="notice notice-warning">Most trades (over '
            f"{_esc(_pct(100.0 - coverage, 0))}) could not be assigned to a specific "
            "market phase -- reason: some of the symbols this bot trades have no "
            "reference candle series to determine the phase from (not a timing "
            "mismatch or a phase-transition edge case) -- the table below is a "
            "HINT, NOT a firm conclusion about the bot's behaviour.</div>")
        )

    # -- Behavioural signals: one chip per pattern + the raw ledger tier -----
    flag_defs = (
        ("martingale_escalation_detected", "Martingale", "martingale-style stacking (raising size after a losing trade)"),
        ("averaging_down_detected", "Averaging down", "averaging down by adding to a losing position in the same direction"),
        ("leverage_escalation_detected", "Leverage escalation", "raising leverage after a losing trade"),
        ("reentry_loop_detected", "Re-entry loop", "repeatedly re-entering in a loop"),
    )
    chips = []
    for key, name, desc in flag_defs:
        hit = bool(behavioral.get(key))
        chips.append(
            f'<span class="st-chip {"st-chip-bad" if hit else "st-chip-good"}" '
            f'title="{_esc(desc)}: {"detected" if hit else "not detected"}">'
            f'{"!" if hit else "✓"} {_esc(name)}</span>'
        )
    tier = behavioral.get("behavioral_risk_tier")
    tier_label = BEHAVIORAL_TIER_LABEL_VI.get(tier, "not measured")
    tier_tone = {"LOW": "good", "MEDIUM": "warn", "HIGH": "bad", "CRITICAL": "bad"}.get(tier, "flat")
    chips.append(
        f'<span class="st-chip st-chip-{tier_tone}" title="Raw behavioural signal from the trade '
        'ledger -- the level of the OBSERVED SIGNAL, not the scored value of the '
        '&ldquo;Behavioral risk&rdquo; dimension in the scores section.">'
        f'Behavioral risk: {_esc(tier_label)}</span>'
    )
    any_hit = any(behavioral.get(k) for k, _, _ in flag_defs)
    signals_title = (
        "Detected in the closed trade data -- hover each chip for what it means."
        if any_hit
        else "no sign of averaging down, martingale-style stacking, or raising leverage "
        "after a loss found in the closed trade data."
    )
    signals = (
        f'<div class="st-row"><span class="st-label" title="{_esc(signals_title)}">Behavioural signals</span>'
        f'<span class="st-chips">{"".join(chips)}</span></div>'
    )

    table_block = _render_phase_breakdown_table(strategy)

    untested = strategy.get("untested_phases")
    untested_html = ""
    if isinstance(untested, list) and untested:
        untested_html = (
            '<div class="st-row"><span class="st-label" title="Never traded through market phase '
            '-- nobody yet knows how the bot handles this phase.">Untested phases</span>'
            '<span class="st-chips">'
            + "".join(
                f'<span class="st-chip st-chip-warn">{_cap_span(_phase_label_vi(p))}</span>'
                for p in untested
            )
            + "</span></div>"
        )

    body = (
        '<div class="st-wrap">'
        + tiles + coverage_warning + signals + table_block + untested_html
        + "</div>"
    )
    # No "Methodology & interpretation" note here -- dropped at the project
    # owner's request (2026-09-24); the chips/labels carry their meaning in
    # their hover titles.
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


def _format_expert_metric_highlights(text: str) -> str:
    escaped = _esc(text)
    return re.sub(
        r'(\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%|\b\d+(?:\.\d+)?x|\b\d+\.\d+\b)',
        r'<strong class="expert-metric" style="font-family:var(--mono);font-weight:700;color:var(--ink,#fff);background:rgba(255,255,255,0.06);padding:0 4px;border-radius:3px;font-variant-numeric:tabular-nums;">\1</strong>',
        escaped,
    )


# --------------------------------------------------------------------------- #
# Ask Nora AI -- widget hỏi-đáp, gọi `POST /api/chat`
# (`Agent/backend/llm/chat.py`).
#
# CỐ Ý không kiểm `chat.chat_enabled()` hay vai (USER/ADMIN) ở ĐÂY: đúng
# triết lý "hiện khối, dặn giới hạn công khai" (`view_policy.WITHHELD_MARKER`)
# đã dùng cho các panel bị khoá khác -- widget luôn hiện, câu trả lời tự nói
# "phần này thuộc Premium" khi cần (xem `chat._PREMIUM_SIMULATION_NOTICE`),
# và khi tính năng tắt hẳn ở backend thì JS bên dưới hiện đúng câu 503 server
# trả về. Không có đường nào ở widget này gọi lại `/api/analyze` hay bất kỳ
# tuyến ghi nào -- CHỈ `POST /api/chat`, đúng ranh giới "Mode C, không phải
# Mode B" của `chat.py`'s module docstring.
# --------------------------------------------------------------------------- #


def _render_chat_widget(result: Dict[str, Any]) -> str:
    """Nút nổi "Ask Nora AI" ở góc phải dưới màn hình -- click mở/đóng một
    khung hội thoại, đúng khuôn widget chat hỗ trợ (Intercom/Crisp-style),
    theo yêu cầu tường minh của chủ dự án (22/09). Đứng NGOÀI cả ba tab
    (`panel-report`/`panel-market`/`panel-trades`), hiện xuyên suốt bất kể
    tab nào đang mở -- xem call site trong `render_bot_report_html`.

    HAI LÝ DO cố tình KHÔNG dùng `_section()` (khối `<section class="card"
    id="...">` mà mọi mục khác trong ba tab đều dùng), vẫn nguyên vẹn dù đổi
    sang dạng nổi:
      1. `test_render_invariants.py::test_result_tab_stays_an_overview` khoá
         CỨNG tab Analyst Result ở đúng 5 section -- một quyết định sản phẩm
         có chủ đích ("người dùng thường chỉ xem tab này, phải giữ nó là bản
         tóm lược"), đã từng bị phá bởi các mục thử-rồi-bỏ trước đây. Thêm
         một `_section()` thứ sáu vào đó là lặp lại đúng lỗi đã sửa.
      2. `test_report_page.py`'s `_tab_ids("panel-trades", ...)` cắt chuỗi
         tới HẾT phần còn lại của trang (panel-trades là tab cuối, không có
         `class="tab-panel` nào theo sau để làm mốc dừng) -- nên bất kỳ
         `<section class="card">` nào đặt sau `tabs_html`, DÙ ở ngoài mọi
         div tab, vẫn bị đếm lẫn vào tab đó. Dùng thẻ khác `<section
         class="card">` (ở đây là `<aside>` + `<button>` FAB riêng) khiến
         regex của cả hai test không bao giờ khớp, bất kể đặt ở đâu.

    Đóng theo mặc định (`hidden` + `aria-hidden="true"` trên panel,
    `aria-expanded="false"` trên nút nổi) -- một khung chat bung sẵn ngay
    khi mở trang là đúng thứ yêu cầu này muốn tránh. JS bật/tắt ở
    `nora-chat-runtime` bên dưới; không JS thì panel vẫn tồn tại trong DOM
    (không phải progressive-enhancement-cấm) nhưng nút nổi không phản hồi
    click -- chấp nhận được vì toàn bộ tính năng vốn đã cần JS để gọi
    `/api/chat`.
    """
    code = result.get("code") or ""
    if not code:
        return ""
    return (
        '<button type="button" class="nora-chat-fab" id="nora-chat-fab" '
        'aria-haspopup="dialog" aria-expanded="false" '
        'aria-controls="nora-chat-widget" aria-label="Ask Nora AI">'
        '<span class="nora-chat-fab-icon" aria-hidden="true"><span class="ic-mask ic-chat"></span></span>'
        "</button>"
        '<aside class="nora-chat-widget" id="nora-chat-widget" '
        f'data-bot-code="{_esc(code)}" role="dialog" aria-modal="false" '
        'aria-label="Ask Nora AI" aria-hidden="true" hidden>'
        '<div class="nora-chat-head">'
        '<div class="nora-chat-avatar-head"></div>'
        '<div class="nora-chat-title-group">'
        '<div class="nora-chat-title-row">'
        '<h2>Nora AI</h2>'
        # Không ghi tên model cụ thể ở đây có chủ đích: badge này đã từng
        # ghi "GPT-4o QUANT" trong khi backend thật (`NORABT_NARRATIVE_BACKEND`)
        # là Gemini qua `agy`, không phải GPT-4o -- sai sự thật hiển thị công
        # khai cho người dùng. Đổi model backend (đã xảy ra ít nhất 2 lần
        # trong lịch sử dự án, xem `narrative.py`'s "Đổi LLM sang agy/Gemini")
        # không nên bắt phải sửa lại UI, nên nhãn chỉ nói ĐÚNG cái người dùng
        # cần biết -- đây là trợ lý định lượng, không phải mô hình cụ thể nào.
        '<span class="badge badge-info">QUANT AI</span>'
        '</div>'
        '<div class="nora-chat-status-sub">'
        '<span class="nora-chat-online-dot"></span>'
        '<span>Online &middot; Risk Assistant</span>'
        '</div>'
        '</div>'
        '<button type="button" class="nora-chat-close" id="nora-chat-close" '
        'aria-label="Close chat">&times;</button>'
        '</div>'
        '<div class="nora-chat-log" id="nora-chat-log"></div>'
        '<div class="nora-chat-status" id="nora-chat-status"></div>'
        '<div class="nora-chat-chips" id="nora-chat-chips"></div>'
        '<form class="nora-chat-form" id="nora-chat-form">'
        '<input type="text" id="nora-chat-input" class="nora-chat-input" '
        'maxlength="500" autocomplete="off" '
        'placeholder="Ask me anything&hellip;" />'
        '<button type="submit" id="nora-chat-send" class="nora-chat-send" aria-label="Ask">&uarr;</button>'
        '</form>'
        '<p class="nora-chat-disclaimer">'
        'Inferences are generated directly from this bot&rsquo;s audit data. Not financial advice.'
        '</p>'
        '</aside>'
    )


def _peer_rank(result: Dict[str, Any], key: str, value: Optional[float]) -> Optional[Tuple[int, int]]:
    """(rank, group size) of `value` among the scored bots, higher = better;
    None without a peer group (see `_render_peer_comparison`)."""
    if value is None:
        return None
    pop = _peer_population(result, {key: value})
    vals = [float(r[key]) for r in pop if _is_finite_number(r.get(key))]
    if len(vals) < 5:
        return None
    return 1 + sum(1 for v in vals if v > value), len(vals)


_TREND_FAMILY = {"UPTREND": "Uptrend", "DOWNTREND": "Downtrend", "RANGE": "Sideways"}


def _expert_cards(result: Dict[str, Any]) -> List[str]:
    """The three cards of the preview's Expert assessment, each read straight
    off the engine's own fields:
      [REGIME DEPENDENCE] -- strategy.regime_dependence_pct (share of gross
          profit from the single best phase) + the next phase / the rest,
          from phase_breakdown.profit_share_pct.
      [SAMPLE SIZE] / [TRACK RECORD] -- public ledger days, closed trades,
          confidence, and the extra trades the verdict says it still needs.
      [UNTESTED REGIME] -- the market phases the bot has never traded.
    A card whose inputs are missing is left out rather than filled in."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    strategy = evidence.get("strategy") if isinstance(evidence.get("strategy"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    cards: List[str] = []

    def card(tag: str, badge: Tuple[str, str], value: str, unit: str, meta: Sequence[Tuple[str, str]], title: str = "") -> str:
        t = f' title="{_esc(title)}"' if title else ""
        meta_html = "".join(
            f'<span><em>{_esc(k)}</em> <b>{_esc(v)}</b></span>' for k, v in meta
        )
        return (
            f'<div class="ex-card"{t}>'
            f'<div class="ex-card-head"><span class="ex-tag">{_esc(tag)}</span>'
            f'<span class="st-chip st-chip-{badge[1]} ex-badge">{_esc(badge[0])}</span></div>'
            f'<div class="ex-card-value"><span class="ex-num">{_esc(value)}</span>'
            f'<span class="ex-unit">{_esc(unit)}</span></div>'
            f'<div class="ex-meta">{meta_html}</div>'
            "</div>"
        )

    # 1. Regime dependence
    dep = strategy.get("regime_dependence_pct")
    rows = [r for r in (strategy.get("phase_breakdown") or []) if isinstance(r, dict)]
    shares = sorted(
        (float(r["profit_share_pct"]) for r in rows if _is_finite_number(r.get("profit_share_pct"))),
        reverse=True,
    )
    if _is_finite_number(dep):
        d = float(dep)
        badge = ("High", "bad") if d >= 70 else (("Moderate", "warn") if d >= 50 else ("Diversified", "good"))
        meta = []
        if len(shares) >= 2:
            meta.append(("2nd phase", f"{shares[1]:.0f}%"))
            meta.append(("Others", f"{max(sum(shares[2:]), 0.0):.0f}%"))
        cards.append(card(
            "[REGIME DEPENDENCE]", badge, f"{d:.0f}%", "profit from 1 phase", meta,
            "Share of gross profit that comes from the single best market phase.",
        ))

    # 2. Track record
    days = perf.get("ledger_coverage_days")
    lead = perf.get("declared_lead_days")
    trades = perf.get("trade_count") or result.get("trade_count")
    conf = result.get("confidence")
    cf = (float(conf) * 100.0 if float(conf) <= 1.0 else float(conf)) if _is_finite_number(conf) else None
    needs = None
    for line in result.get("text") or []:
        m = re.search(r"roughly (\d[\d,]*) more trades are needed", str(line))
        if m:
            needs = m.group(1)
            break
    thin = (
        needs is not None
        or (cf is not None and cf < 70)
        or (_is_finite_number(trades) and float(trades) < 30)
        or perf.get("measurement_mode") in ("PARTIAL", "LIMITED")
    )
    if _is_finite_number(days) or _is_finite_number(trades):
        if _is_finite_number(days):
            value = f"{float(days):.0f}" + (f" / {float(lead):.0f}" if _is_finite_number(lead) else "")
            unit = "days of public ledger"
        else:
            value, unit = f"{int(float(trades)):,}", "closed trades"
        meta = []
        if _is_finite_number(days) and _is_finite_number(trades):
            meta.append(("Trades", f"{int(float(trades)):,}"))
        if cf is not None:
            meta.append(("Confidence", f"{cf:.0f}%"))
        if needs:
            meta.append(("Needs", f"+{needs} trades"))
        else:
            rk = _peer_rank(result, "trade_count", float(trades) if _is_finite_number(trades) else None)
            if rk:
                meta.append(("Rank by trades", f"#{rk[0]}"))
        cards.append(card(
            "[SAMPLE SIZE]" if thin else "[TRACK RECORD]",
            ("Limits confidence", "warn") if thin else ("Solid", "good"),
            value, unit, meta,
            "Days of public trade ledger behind this assessment"
            + (f" (mode {perf.get('measurement_mode')})" if perf.get("measurement_mode") else "") + ".",
        ))

    # 3. Key unknown
    untested = [p for p in (strategy.get("untested_phases") or []) if isinstance(p, str)]
    traded = [r.get("phase") for r in rows if _is_finite_number(r.get("trades")) and float(r["trades"]) > 0]
    if untested or rows:
        family_counts: Dict[str, int] = {}
        for p in untested:
            fam = p.split("_", 1)[0]
            family_counts[fam] = family_counts.get(fam, 0) + 1
        whole = [f for f, c in family_counts.items() if c >= 2]
        if whole:
            fam = whole[0]
            fam_trades = sum(
                float(r.get("trades") or 0) for r in rows if str(r.get("phase", "")).startswith(fam + "_")
            )
            cards.append(card(
                "[UNTESTED REGIME]", ("Open", "flat"), _TREND_FAMILY.get(fam, fam.title()), "untested",
                [("Phases", "0/2"), ("Trades", f"{fam_trades:.0f}")],
                "Never traded through market phase -- nobody yet knows how the bot handles it.",
            ))
        elif untested:
            first = _phase_label_vi(untested[0])
            cards.append(card(
                "[UNTESTED REGIME]", ("Open", "flat"), f"{len(untested)} of 6", "phases untested",
                [("Traded", f"{len(set(traded))}/6"), ("e.g.", first[0].upper() + first[1:])],
                "Never traded through market phase: "
                + ", ".join(_phase_label_vi(p) for p in untested) + ".",
            ))
        else:
            cards.append(card(
                "[PHASE COVERAGE]", ("Covered", "good"), f"{len(set(traded))}/6", "phases traded",
                [("Untested", "0")],
            ))
    return cards


def _expert_thesis(result: Dict[str, Any]) -> str:
    """One sentence built from the strategy fields when neither the engine's
    `executive_essence` nor an LLM narrative supplies one."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    strategy = evidence.get("strategy") if isinstance(evidence.get("strategy"), dict) else {}
    if not strategy:
        return ""
    profile = _split_label(OBSERVED_PROFILE_LABEL_VI.get(strategy.get("observed_profile"), ""))[0]
    bias = DIRECTIONAL_BIAS_LABEL_VI.get(strategy.get("directional_bias"), "")
    n = lev = 0.0
    for r in strategy.get("phase_breakdown") or []:
        if isinstance(r, dict) and _is_finite_number(r.get("trades")) and _is_finite_number(r.get("average_leverage")):
            n += float(r["trades"])
            lev += float(r["trades"]) * float(r["average_leverage"])
    bits = []
    if profile and profile != "not yet determined":
        bits.append(profile[0].upper() + profile[1:] + " bot")
    if bias and "not enough" not in bias:
        bits.append(bias.split(",")[0])
    if n > 0:
        bits.append(f"{lev / n:.0f}x average leverage")
    best = strategy.get("best_phase")
    tail = f" — earns most in the {_phase_label_vi(best)} phase" if best else ""
    return (", ".join(bits) + tail + ".") if bits else ""


def _render_narrative(result: Dict[str, Any]) -> str:
    """Expert assessment, laid out like the redesign preview: a Core thesis
    bar, three evidence cards (`_expert_cards`), then the engine's root causes
    and -- when the LLM narrative is on -- its key findings, compact. No
    methodology note (project owner, 2026-09-24)."""
    text = result.get("narrative")
    has_llm = isinstance(text, str) and bool(text.strip()) and not _is_narrative_pending(text)
    insights = _insights(result)
    essence = insights.get("executive_essence") or {}
    modes = insights.get("failure_modes") or []

    bullets: List[str] = []
    thesis = ""
    source = "Built from the scoring engine's own fields."
    if has_llm:
        lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
        prose: List[str] = []
        for ln in lines:
            if re.match(r"^([-*•]|\d+\.)\s+", ln):
                bullets.append(re.sub(r"^([-*•]|\d+\.)\s*", "", ln))
            else:
                prose.append(ln)
        full = " ".join(prose)
        sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", full) if x.strip()]
        if sentences:
            thesis = sentences[0]
            if not bullets:
                bullets = [x for x in sentences[1:] if len(x) > 15]
        source = "Written by a language model from the quantitative analysis results (an independent view, not a measurement)."
    if not thesis and essence.get("what_it_appears_to_do"):
        thesis = str(essence["what_it_appears_to_do"])
    if not thesis:
        thesis = _expert_thesis(result)

    cards = _expert_cards(result)
    if not thesis and not cards and not modes and not bullets:
        return ""

    parts: List[str] = []
    if thesis:
        sub = ""
        if not has_llm and essence:
            extras = [essence.get("dominant_behavior"), essence.get("strongest_positive_evidence")]
            sub = " · ".join(str(x) for x in extras if x)
        parts.append(
            f'<div class="ex-thesis" title="Core Strategy Thesis -- {_esc(source)}">'
            '<span class="ex-thesis-k">Core thesis</span>'
            f'<span class="ex-thesis-v"><b>{_esc(thesis)}</b>'
            + (f'<span class="ex-thesis-sub">{_esc(sub)}</span>' if sub else "")
            + "</span></div>"
        )
    if cards:
        parts.append(f'<div class="ex-cards">{"".join(cards)}</div>')
    if modes:
        rows = "".join(
            '<div class="quant-audit-row">'
            f'<div class="quant-audit-tag">{_esc(str(m.get("mechanism") or ""))}</div>'
            f'<div class="quant-audit-main"><span class="root-cause-support">{_esc(str(m.get("observed_support") or ""))}</span></div>'
            '<div class="quant-audit-end"></div></div>'
            for m in modes
        )
        parts.append(
            f'<div class="ex-list"><span class="st-label">Root causes on the evidence ({len(modes)})</span>'
            f'<div class="quant-audit-rows ex-rows">{rows}</div></div>'
        )
    unknown = essence.get("most_important_unknown")
    if unknown:
        parts.append(f'<div class="ex-note"><span class="qe-revisit-tag">Most important unknown</span> {_esc(str(unknown))}</div>')
    if bullets:
        items = "".join(
            f'<div class="ex-finding"><span class="ex-finding-n">{i:02d}</span>'
            f'<span>{_format_expert_metric_highlights(b)}</span></div>'
            for i, b in enumerate(bullets, start=1)
        )
        parts.append(
            f'<div class="ex-list"><span class="st-label" title="{_esc(source)}">Key findings</span>'
            f'<div class="ex-findings">{items}</div></div>'
        )
    body = '<div class="ex-wrap">' + "".join(parts) + "</div>"
    return _section("Expert assessment", body, anchor="nhan-dinh")


# --------------------------------------------------------------------------- #
# Section 3 -- per-dimension scores
# --------------------------------------------------------------------------- #


# Tier bands of a single dimension -- report/qc/evaluator/common.py `tier_for`.
_DIM_TIERS: Tuple[Tuple[str, str, str], ...] = (
    ("HEALTHY", "Low", "<30"),
    ("WATCH", "Moderate", "30–49"),
    ("ELEVATED", "Elevated", "50–69"),
    ("HIGH", "High", "70–84"),
    ("CRITICAL", "Critical", "≥85"),
)


def _dim_tier_for(score: float) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 50:
        return "ELEVATED"
    if score >= 30:
        return "WATCH"
    return "HEALTHY"


def _dimension_rows(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    """(label, info key, score, tier, note, tag) per dimension, measured ones
    sorted riskiest first, unmeasured ones last. FULL results read
    `evidence.dimensions` (tier as the engine set it); LIMITED ones read
    `evidence.components` (tier from the same bands, `_dim_tier_for`)."""
    out: List[Dict[str, Any]] = []
    dimensions = evidence.get("dimensions")
    if isinstance(dimensions, dict) and dimensions:
        keys = list(DIMENSION_ORDER) + [k for k in dimensions if k not in DIMENSION_ORDER]
        for key in dict.fromkeys(keys):
            if key not in dimensions:
                continue
            dim = dimensions.get(key) or {}
            label = DIMENSION_LABEL_VI.get(key, dim.get("dimension_name") or key)
            status = str(dim.get("status") or "AVAILABLE").upper()
            score = dim.get("score")
            findings = [f.strip() for f in (dim.get("key_findings") or []) if isinstance(f, str) and f.strip()]
            if status == "AVAILABLE" and _is_finite_number(score):
                tier = str(dim.get("tier") or _dim_tier_for(float(score))).upper()
                # Findings are engine notes (may carry raw enums) -- the "*"
                # formula carries the explanation for a measured dimension.
                out.append({"label": label, "key": key, "score": float(score), "tier": tier,
                            "note": "", "tag": ""})
            else:
                out.append({"label": label, "key": key, "score": None, "tier": None,
                            "note": findings[0] if findings else "", "tag": "Not measured"})
    else:
        for comp in evidence.get("components") or []:
            if not isinstance(comp, dict):
                continue
            label = comp.get("label") or comp.get("name") or "—"
            key = comp.get("name") or comp.get("key") or ""
            info_key = key if _formula_info(key) is not None else "risk_score"
            status = str(comp.get("status") or "AVAILABLE").upper()
            score = comp.get("score")
            findings = [f.strip() for f in (comp.get("findings") or []) if isinstance(f, str) and f.strip()]
            if status == "AVAILABLE" and _is_finite_number(score):
                out.append({"label": label, "key": info_key, "score": float(score),
                            "tier": _dim_tier_for(float(score)), "note": "; ".join(findings[:2]), "tag": ""})
            else:
                tag = "concealed" if status == "UNKNOWN_CONCEALED" else "missing data"
                out.append({"label": label, "key": info_key, "score": None, "tier": None,
                            "note": "; ".join(findings[:2]), "tag": tag})
    measured = sorted((r for r in out if r["score"] is not None), key=lambda r: r["score"], reverse=True)
    return measured + [r for r in out if r["score"] is None]


def _render_dimensions_section(result: Dict[str, Any]) -> str:
    """Risk score by dimension, laid out like the redesign preview: one row
    per dimension (name + "*" formula, bar, score, tier pill), riskiest first,
    and a "Dimensions by tier" donut card counting the measured dimensions
    per tier band. No score-note / methodology drawers (project owner,
    2026-09-24): each row's findings are in its hover title instead."""
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return ""
    # Unmeasured dimensions are left out rather than listed as "not
    # measured" (project owner, 2026-09-24).
    rows = [r for r in _dimension_rows(evidence) if r["score"] is not None]
    if not rows:
        return ""

    row_html = []
    for r in rows:
        title = f' title="{_esc(r["note"])}"' if r["note"] else ""
        if r["score"] is not None:
            tier = r["tier"] if r["tier"] in {t for t, _, _ in _DIM_TIERS} else (
                "CRITICAL" if r["tier"] == "EMERGENCY" else "HEALTHY"
            )
            tier_name = dict((t, n) for t, n, _ in _DIM_TIERS)[tier]
            if r["tier"] == "EMERGENCY":
                tier_name = "Emergency"
            w = max(1.5, min(100.0, r["score"]))
            bar = f'<span class="dm-fill dm-t-{tier.lower()}" style="width:{w:.0f}%"></span>'
            val = (
                f'<b class="dm-num">{r["score"]:.0f}</b>'
                f'<span class="dm-pill dm-p-{tier.lower()}">{_esc(tier_name)}</span>'
            )
        else:
            bar = ""
            val = f'<b class="dm-num dm-num-na">—</b><span class="dm-pill dm-p-na">{_esc(r["tag"])}</span>'
        row_html.append(
            f'<div class="dm-row"{title}>'
            f'<span class="dm-name">{_calc_label_html(r["label"], r["key"])}</span>'
            f'<span class="dm-track">{bar}</span>'
            f'<span class="dm-val">{val}</span>'
            "</div>"
        )

    measured = [r for r in rows if r["score"] is not None]
    counts = {t: 0 for t, _, _ in _DIM_TIERS}
    for r in measured:
        t = r["tier"] if r["tier"] in counts else ("CRITICAL" if r["tier"] == "EMERGENCY" else "HEALTHY")
        counts[t] += 1
    card = ""
    if measured:
        legend = "".join(
            f'<div class="gc-leg-row{" dm-leg-zero" if counts[t] == 0 else ""}">'
            f'<span class="gc-dot dm-dot-{t.lower()}"></span>'
            f'<span class="gc-leg-name">{_esc(n)} <span class="dm-band">{_esc(band)}</span></span>'
            f'<b class="gc-leg-val">{counts[t]}</b></div>'
            for t, n, band in _DIM_TIERS
        )
        donut = _donut_svg(
            [(float(counts[t]), f"dm-{t.lower()}") for t, _, _ in _DIM_TIERS],
            f"{counts['HEALTHY']}/{len(measured)}",
            "LOW RISK",
        )
        card = (
            '<div class="gc-card dm-card">'
            '<div class="gc-head"><span class="st-label">Dimensions by tier</span></div>'
            f'<div class="dm-donut">{donut}</div>'
            f'<div class="gc-legend dm-legend">{legend}</div>'
            "</div>"
        )
    body = (
        '<div class="dm-grid">'
        '<div class="dm-left">'
        '<span class="st-label" title="0–100, higher = worse. Sorted from riskiest.">Risk score by dimension</span>'
        f'<div class="dm-rows bar-chart">{"".join(row_html)}</div>'
        "</div>"
        f"{card}"
        "</div>"
    )
    return _section("Score by risk dimension", body, tone="primary", anchor="diem-chieu")


# --------------------------------------------------------------------------- #
# "CHÚ THÍCH GIẢI THÍCH ĐIỂM SỐ" -- khối mà dấu `*` bấm được trên 3 ô điểm
# số hero (`_render_header`) dẫn tới. Nhúng VÀO TRONG mục "Điểm từng chiều
# rủi ro" sẵn có (không phải một `<section>` mới) để giữ đúng bất biến "cùng
# tập id mục" giữa trang LIMITED và trang đầy đủ -- cùng lý do
# `_render_limited_measured_evidence` đã nêu. Dữ liệu đọc qua
# `Agent/backend/web/score_basis.py` (module đó CHỈ tính/gom, không dựng
# HTML); mọi escape/format ở đây.
# --------------------------------------------------------------------------- #


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


def _fmt_axis_money(v: float) -> str:
    """Short axis tick: +60k, -1.2M, 0."""
    if abs(v) < 1e-9:
        return "0"
    sign = "+" if v > 0 else "-"
    a = abs(v)
    if a >= 1e6:
        return f"{sign}{a / 1e6:.1f}M".replace(".0M", "M")
    if a >= 1e3:
        return f"{sign}{a / 1e3:.0f}k"
    return f"{sign}{a:.0f}"


def _nice_step(span: float, target_ticks: int = 4) -> float:
    raw = max(span, 1e-9) / target_ticks
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _growth_curve_svg(cumulative: List[float], capital: Optional[float], members: Sequence[Tuple[str, List[float]]] = ()) -> str:
    """Cumulative realised PnL, drawn like the redesign preview: light grid
    with short tick labels, soft area fill, the DEEPEST drawdown episode
    shaded (running peak -> lowest point below it, same definition as
    loss_analysis.py's `_deepest_episode`) with its Peak/Trough marked and
    its depth as % of reference capital, and the final value at the end."""
    pts = [0.0] + [float(v) for v in cumulative if _is_finite_number(v)]
    n = len(pts)
    if n < 2:
        return ""
    W, H = 560.0, 240.0
    L, R, T, B = 50.0, 12.0, 26.0, 30.0
    pw, ph = W - L - R, H - T - B
    every = pts + [float(v) for _, line in members for v in line]
    lo, hi = min(min(every), 0.0), max(max(every), 0.0)
    if hi - lo < 1e-9:
        hi, lo = hi + 1.0, lo - 1.0
    step = _nice_step(hi - lo)
    lo_t = math.floor(lo / step) * step
    hi_t = math.ceil(hi / step) * step
    lo, hi = lo_t, hi_t

    def X(i: int) -> float:
        return L + pw * (i / (n - 1))

    def Y(v: float) -> float:
        return T + ph * (1.0 - (v - lo) / (hi - lo))

    parts: List[str] = []
    k = lo
    guard = 0
    while k <= hi + step * 1e-6 and guard < 20:
        y = Y(k)
        cls = "gc-zero" if abs(k) < step * 1e-6 else "gc-grid"
        parts.append(f'<line class="{cls}" x1="{_coord(L)}" y1="{_coord(y)}" x2="{_coord(L + pw)}" y2="{_coord(y)}"/>')
        parts.append(f'<text class="gc-tick" x="{_coord(L - 8)}" y="{_coord(y + 3.5)}" text-anchor="end">{_esc(_fmt_axis_money(k))}</text>')
        k += step
        guard += 1

    # Deepest drawdown episode on the running peak.
    peak_v, peak_i = pts[0], 0
    best = None
    for i, v in enumerate(pts):
        if v >= peak_v:
            peak_v, peak_i = v, i
            continue
        depth = peak_v - v
        if best is None or depth > best[0]:
            best = (depth, peak_i, i)
    if best is not None:
        depth, pi, ti = best
        x1, x2 = X(pi), X(ti)
        parts.append(
            f'<rect class="gc-dd-band" x="{_coord(x1)}" y="{_coord(T - 8)}" '
            f'width="{_coord(max(x2 - x1, 2.0))}" height="{_coord(ph + 8)}" rx="4"/>'
        )
        dd_txt = (
            f"-{depth / capital * 100.0:.1f}%" if _is_finite_number(capital) and capital and capital > 0
            else f"-{depth:,.0f}"
        )
        parts.append(
            f'<text class="gc-dd-label" x="{_coord((x1 + x2) / 2)}" y="{_coord(T + 4)}" '
            f'text-anchor="middle">{_esc(dd_txt)}</text>'
        )

    final_pos = pts[-1] >= 0.0
    tone = "up" if final_pos else "down"
    gid = f"gc-fill-{abs(hash(tuple(round(v, 2) for v in pts[:12]))) % 10**8}"
    line_pts = " ".join(f"{_coord(X(i))},{_coord(Y(v))}" for i, v in enumerate(pts))
    zero_y = Y(0.0)
    parts.insert(
        0,
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" class="gc-fill-stop gc-fill-{tone}" stop-opacity="0.18"/>'
        f'<stop offset="100%" class="gc-fill-stop gc-fill-{tone}" stop-opacity="0"/>'
        "</linearGradient></defs>",
    )
    parts.append(
        f'<path fill="url(#{gid})" stroke="none" d="M{_coord(X(0))},{_coord(zero_y)} '
        + " ".join(f"L{_coord(X(i))},{_coord(Y(v))}" for i, v in enumerate(pts))
        + f' L{_coord(X(n - 1))},{_coord(zero_y)} Z"/>'
    )
    # A portfolio: each member's running PnL under the combined line.
    for colour, line in members:
        if len(line) == n - 1:
            mp = " ".join(f"{_coord(X(i))},{_coord(Y(v))}" for i, v in enumerate([0.0] + list(line)))
            parts.append(f'<polyline class="gc-member" stroke="{_esc(colour)}" points="{mp}"/>')
    parts.append(f'<polyline class="gc-line gc-line-{tone}" fill="none" points="{line_pts}"/>')

    if best is not None:
        depth, pi, ti = best
        if pi > 0:
            px, py = X(pi), Y(pts[pi])
            anchor, lx = ("end", px - 7) if px > L + 110 else ("start", px + 7)
            parts.append(f'<circle class="gc-mk gc-mk-peak" cx="{_coord(px)}" cy="{_coord(py)}" r="4"/>')
            parts.append(
                f'<text class="gc-mk-label gc-mk-label-peak" x="{_coord(lx)}" y="{_coord(max(py - 8, T + 16))}" '
                f'text-anchor="{anchor}">Peak {pts[pi]:+,.0f}</text>'
            )
        tx, ty = X(ti), Y(pts[ti])
        anchor, lx = ("start", tx + 8) if tx < L + pw - 120 else ("end", tx - 8)
        parts.append(f'<circle class="gc-mk gc-mk-trough" cx="{_coord(tx)}" cy="{_coord(ty)}" r="4"/>')
        parts.append(
            f'<text class="gc-mk-label gc-mk-label-trough" x="{_coord(lx)}" y="{_coord(min(ty + 4, T + ph))}" '
            f'text-anchor="{anchor}">Trough {pts[ti]:+,.0f}</text>'
        )

    ex, ey = X(n - 1), Y(pts[-1])
    parts.append(f'<circle class="gc-end gc-end-{tone}" cx="{_coord(ex)}" cy="{_coord(ey)}" r="4.5"/>')
    end_y = ey - 10 if ey - 10 > T - 6 else ey + 18
    parts.append(
        f'<text class="gc-end-label" x="{_coord(ex - 6)}" y="{_coord(end_y)}" text-anchor="end">{pts[-1]:+,.0f}</text>'
    )
    parts.append(f'<text class="gc-tick" x="{_coord(L)}" y="{_coord(H - 6)}">Trade #1</text>')
    parts.append(
        f'<text class="gc-tick" x="{_coord(L + pw)}" y="{_coord(H - 6)}" text-anchor="end">Trade #{n - 1}</text>'
    )
    return (
        f'<svg class="line-chart gc-svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
        f'aria-label="Cumulative capital curve by closed trade">{"".join(parts)}</svg>'
    )


def _pf_member_series(result: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[List[float]]]:
    """For a portfolio whose merged series tags each trade with its member
    (`owner`): the members that have trades, and for each one its running
    realised PnL at every merged trade (same close-time order as the equity
    curve, so index k is merged trade #k+1). ([], []) otherwise."""
    owners = _owner_index(result)
    series = (result.get("evidence") or {}).get("closed_trade_series") or []
    rows = [r for r in series if isinstance(r, dict) and _is_finite_number(r.get("realized_pnl"))]
    if not owners or not rows or not any(r.get("owner") in owners for r in rows):
        return [], []
    if all(_is_finite_number(r.get("close_time")) for r in rows):
        rows = sorted(rows, key=lambda r: r["close_time"])
    order = [m for m in _pf_members(result) if not m.get("ledger_hidden")]
    running = {str(m.get("unique_code") or "")[:8]: 0.0 for m in order}
    lines: Dict[str, List[float]] = {k: [] for k in running}
    for r in rows:
        key = r.get("owner")
        if key in running:
            running[key] += float(r["realized_pnl"])
        for k in running:
            lines[k].append(running[k])
    used = [m for m in order if any(abs(v) > 1e-9 for v in lines[str(m.get("unique_code") or "")[:8]])]
    return used, [lines[str(m.get("unique_code") or "")[:8]] for m in used]


def _pf_line_legend(members: Sequence[Dict[str, Any]], combined: str, tone_var: str, values: Sequence[str]) -> str:
    return (
        '<div class="gc-mlegend">'
        f'<span><i style="background:var({tone_var});height:3px"></i>{_esc(combined)}</span>'
        + "".join(
            f'<span><i style="background:{_esc(m.get("colour"))}"></i>{_esc(m.get("short") or m.get("label"))}{(" " + v) if v else ""}</span>'
            for m, v in zip(members, values)
        )
        + "</div>"
    )


def _render_growth_curve(result: Dict[str, Any]) -> str:
    pnls = _extract_trade_pnls(result)
    if not pnls:
        return ""
    cumulative: List[float] = []
    running = 0.0
    for v in pnls:
        running += v
        cumulative.append(running)
    profile = compute_loss_profile(result.get("evidence"))
    capital = profile.get("capital") if isinstance(profile, dict) else None
    members, lines = _pf_member_series(result)
    chart = _growth_curve_svg(cumulative, capital, [(str(m.get("colour")), line) for m, line in zip(members, lines)])
    if not chart:
        return ""
    legend = ""
    if members:
        hidden = [m for m in _pf_members(result) if m.get("ledger_hidden")]
        legend = _pf_line_legend(members, "Combined", "--up" if cumulative[-1] >= 0 else "--down", [""] * len(members))
        if hidden:
            legend = legend[:-len("</div>")] + (
                f'<span class="gc-mlegend-off"><i style="background:var(--muted)"></i>{len(hidden)} concealed · not drawn</span></div>'
            )
    title = "Equity curve · combined &amp; by bot" if members else "Equity curve"
    return (
        '<div class="growth-curve-panel" aria-label="Cumulative capital curve by closed trade">'
        f'<div class="gc-head"><span class="st-label">{title}</span>'
        '<span class="gc-note">USDT · by closed trade</span></div>'
        f"{chart}{legend}"
        "</div>"
    )


def _donut_svg(slices: Sequence[Tuple[float, str]], center: str, sub: str) -> str:
    """Ring donut from stroke-dash segments; `slices` are (value, tone)."""
    r, sw = 44.0, 15.0
    c = 2 * math.pi * r
    total = sum(max(v, 0.0) for v, _ in slices)
    parts = [f'<circle class="dn-track" cx="60" cy="60" r="{r:.0f}" fill="none" stroke-width="{sw:.0f}"/>']
    offset = 0.0
    if total > 0:
        for v, tone in slices:
            v = max(v, 0.0)
            if v <= 0:
                continue
            seg = c * v / total
            parts.append(
                f'<circle class="dn-seg dn-{tone}" cx="60" cy="60" r="{r:.0f}" fill="none" '
                f'stroke-width="{sw:.0f}" stroke-dasharray="{_coord(seg)} {_coord(c - seg)}" '
                f'stroke-dashoffset="{_coord(-offset)}" transform="rotate(-90 60 60)"/>'
            )
            offset += seg
    parts.append(f'<text class="dn-center" x="60" y="62" text-anchor="middle">{_esc(center)}</text>')
    parts.append(f'<text class="dn-sub" x="60" y="77" text-anchor="middle">{_esc(sub)}</text>')
    return f'<svg class="pie-chart" viewBox="0 0 120 120" role="img" aria-label="{_esc(sub)}">{"".join(parts)}</svg>'


def _donut_card(title: str, note: str, svg: str, legend: Sequence[Tuple[str, str, str]], aria: str) -> str:
    rows = "".join(
        f'<div class="gc-leg-row"><span class="gc-dot dn-{tone}"></span>'
        f'<span class="gc-leg-name">{_esc(name)}</span><b class="gc-leg-val">{_esc(val)}</b></div>'
        for name, val, tone in legend
    )
    note_html = f'<span class="gc-note gc-note-mono">{_esc(note)}</span>' if note else ""
    return (
        f'<div class="gc-card" aria-label="{_esc(aria)}">'
        f'<div class="gc-head"><span class="st-label">{_esc(title)}</span>{note_html}</div>'
        f'<div class="gc-card-body">{svg}<div class="gc-legend">{rows}</div></div>'
        "</div>"
    )


def _render_win_loss_composition(result: Dict[str, Any]) -> str:
    """Two donut cards, stacked: trade count (win / loss / break-even) and
    gross profit vs gross loss. Gross amounts are printed only when they come
    from the bot's own averages or its PnL; when they had to be sized from a
    ratio alone the card shows shares, never an invented USDT amount."""
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
    win_pct = (win_count / total) * 100.0 if total > 0 else 0.0

    average_win = perf.get("average_win")
    average_loss = perf.get("average_loss")
    gross_profit = gross_loss = profit_factor = 0.0
    gross_is_real = False
    if (
        _is_finite_number(average_win)
        and _is_finite_number(average_loss)
        and win_count > 0
        and loss_count > 0
    ):
        gross_profit = max(float(average_win), 0.0) * win_count
        gross_loss = abs(float(average_loss)) * loss_count
        gross_is_real = True
    elif win_count > 0 and loss_count > 0:
        pf_val = perf.get("profit_factor")
        total_pnl = perf.get("total_pnl")
        payoff_r = perf.get("payoff_ratio")
        if _is_finite_number(pf_val) and float(pf_val) > 0:
            profit_factor = float(pf_val)
            pnl = float(total_pnl) if _is_finite_number(total_pnl) else 0.0
            if profit_factor > 1.0 and pnl > 0:
                gross_loss = pnl / (profit_factor - 1.0)
                gross_profit = gross_loss * profit_factor
                gross_is_real = True
            elif 0 < profit_factor < 1.0 and pnl < 0:
                gross_loss = abs(pnl) / (1.0 - profit_factor)
                gross_profit = gross_loss * profit_factor
                gross_is_real = True
            else:
                gross_profit, gross_loss = profit_factor, 1.0
        elif _is_finite_number(payoff_r) and float(payoff_r) > 0:
            profit_factor = float(payoff_r) * (win_count / float(loss_count))
            gross_profit, gross_loss = profit_factor, 1.0

    count_slices = [(float(win_count), "good"), (float(loss_count), "bad")]
    legend = [("Winning", f"{win_count:,}", "good"), ("Losing", f"{loss_count:,}", "bad")]
    if breakeven_count:
        count_slices.append((float(breakeven_count), "flat"))
        legend.append(("Break-even", f"{breakeven_count:,}", "flat"))
    cards = _donut_card(
        "Trade outcome",
        f"{total:,} trades",
        _donut_svg(count_slices, f"{win_pct:.1f}%", "WIN RATE"),
        legend,
        "Trade count breakdown",
    )
    if gross_profit > 0 or gross_loss > 0:
        if profit_factor <= 0 and gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        g_total = gross_profit + gross_loss
        if gross_is_real:
            g_legend = [
                ("Gross profit", f"{gross_profit:,.0f}", "good"),
                ("Gross loss", f"{gross_loss:,.0f}", "bad"),
            ]
        else:
            g_legend = [
                ("Gross profit", f"{gross_profit / g_total * 100:.0f}%", "good"),
                ("Gross loss", f"{gross_loss / g_total * 100:.0f}%", "bad"),
            ]
        cards += _donut_card(
            "Gross profit / loss",
            "USDT" if gross_is_real else "share",
            _donut_svg([(gross_profit, "good"), (gross_loss, "bad")], f"{profit_factor:.2f}x", "PF"),
            g_legend,
            "Gross profit/loss breakdown (USDT)",
        )
    return f'<div class="win-loss-composition-panel" aria-label="Win/loss composition">{cards}</div>'


def _render_growth_section(result: Dict[str, Any], anchor: Optional[str] = "tang-truong") -> str:
    curve_html = _render_growth_curve(result)
    composition_html = _render_win_loss_composition(result)
    if not curve_html and not composition_html:
        return ""
    if curve_html and composition_html:
        dashboard_body = (
            '<div class="gc-grid">'
            f'<div class="gc-left">{curve_html}</div>'
            f'<div class="gc-right">{composition_html}</div>'
            '</div>'
        )
    else:
        dashboard_body = curve_html or composition_html

    # No "Methodology & interpretation" note -- dropped at the project
    # owner's request (2026-09-24).
    return _section("Growth & outcome composition", dashboard_body, anchor=anchor)


# --------------------------------------------------------------------------- #
# Section 4 -- Monte Carlo
# --------------------------------------------------------------------------- #


def _mc_f(v: Any) -> Optional[float]:
    return float(v) if _is_finite_number(v) else None


def _mc_pct_points(mc: Dict[str, Any]) -> List[Dict[str, float]]:
    """Checkpoints of the simulated equity paths as % return on the capital
    the simulation started from (`capital_at_risk`, else `initial_equity`),
    with trade 0 = 0%. Checkpoints already in % are kept as they are; with
    no usable base for absolute ones, nothing is drawn (never a guessed base)."""
    cps = mc.get("horizon_checkpoints")
    if not isinstance(cps, list) or not cps:
        return []
    base = _mc_f(mc.get("capital_at_risk")) or _mc_f(mc.get("initial_equity"))
    out: List[Dict[str, float]] = [{"tc": 0.0, "p05": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0}]
    for cp in cps:
        if not isinstance(cp, dict):
            continue
        vals = {k: _mc_f(cp.get(k)) for k in ("p05", "p25", "p50", "p75", "p95")}
        tc = _mc_f(cp.get("trade_count"))
        if tc is None or any(v is None for v in vals.values()):
            continue
        if abs(vals["p50"]) > 1000.0:  # absolute equity, not %
            if not base:
                return []
            vals = {k: (v / base - 1.0) * 100.0 for k, v in vals.items()}
        out.append({"tc": tc, **vals})
    return out if len(out) >= 3 else []


def _mc_sample_paths(result: Dict[str, Any], mc: Dict[str, Any], count: int = 46) -> List[List[Tuple[float, float]]]:
    """A few of the simulation's own kind of path, redrawn for the picture:
    the same stationary bootstrap the engine runs
    (bot/mcp/analytics/simulation/monte_carlo.py `_simulate_horizon` --
    blocks of expected length round(n^(1/3)), wrap-around, equity absorbed at
    zero) over this bot's own closed-trade PnL, on the same capital and
    horizon, with a fixed seed so the page is stable between reloads. They
    illustrate spread only; every number on the page comes from the engine's
    10,000-path run, not from these."""
    pnls = _extract_trade_pnls(result) or []
    capital = _mc_f(mc.get("capital_at_risk")) or _mc_f(mc.get("initial_equity"))
    horizon = int(_mc_f(mc.get("horizon_trades")) or 0)
    if len(pnls) < 10 or not capital or capital <= 0 or horizon < 2:
        return []
    import random as _random

    rng = _random.Random(sum(ord(c) for c in str(result.get("code") or "mc")) * 7919 + len(pnls))
    n = len(pnls)
    block = max(2, min(int(round(n ** (1 / 3))), n // 2))
    step = max(1, horizon // 60)
    paths = []
    for _ in range(count):
        eq, pos, pts = capital, 0, [(0.0, 0.0)]
        ruined = False
        for t in range(1, horizon + 1):
            if t == 1 or rng.random() < 1.0 / block:
                pos = rng.randrange(n)
            else:
                pos = (pos + 1) % n
            if not ruined:
                eq += pnls[pos]
                if eq <= 0:
                    eq, ruined = 0.0, True
            if t % step == 0 or t == horizon:
                pts.append((float(t), (eq / capital - 1.0) * 100.0))
        paths.append(pts)
    return paths


_MC_W, _MC_H, _MC_L, _MC_R, _MC_T, _MC_B = 760.0, 290.0, 46.0, 100.0, 14.0, 30.0


def _mc_axes(lo: float, hi: float, step: float, tmax: float, Y: Callable[[float], float], X: Callable[[float], float], unit: str = "%", x_unit: str = "trade") -> str:
    parts = []
    k = lo
    while k <= hi + step * 1e-6:
        y = Y(k)
        cls = "mc-zero" if abs(k) < step * 1e-6 else "mc-grid"
        label = "0%" if abs(k) < step * 1e-6 else f"{k:+.0f}{unit}"
        parts.append(f'<line class="{cls}" x1="{_coord(_MC_L)}" y1="{_coord(y)}" x2="{_coord(_MC_W - _MC_R)}" y2="{_coord(y)}"/>')
        parts.append(f'<text class="mc-tick" x="{_coord(_MC_L - 8)}" y="{_coord(y + 3.5)}" text-anchor="end">{label}</text>')
        k += step
    xstep = next((s for s in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000) if tmax / s <= 5.5), 5000)
    t = 0.0
    while t <= tmax + 1e-6:
        # "Trade " sits in its own tspan so a phone can drop the word and
        # keep the "0" (the full label crowds "#100" at that size).
        if x_unit == "day":
            label = f'<tspan class="mc-x0">Day </tspan>{t:.0f}' if t else '<tspan class="mc-x0">Day </tspan>0'
        else:
            label = '<tspan class="mc-x0">Trade </tspan>0' if t == 0 else f"#{t:.0f}"
        parts.append(
            f'<text class="mc-tick mc-tick-x" x="{_coord(X(t))}" y="{_coord(_MC_H - 10)}" text-anchor="middle">'
            f'{label}</text>'
        )
        t += xstep
    return "".join(parts)


def _mc_tag(x: float, y: float, text: str, tone: str) -> str:
    w = len(text) * 6.6 + 12
    return (
        f'<rect class="mc-tag mc-tag-{tone}" x="{_coord(x + 6)}" y="{_coord(y - 9)}" width="{_coord(w)}" height="18" rx="5"/>'
        f'<text class="mc-tag-text" x="{_coord(x + 6 + w / 2)}" y="{_coord(y + 3.5)}" text-anchor="middle">{_esc(text)}</text>'
    )


def _mc_band_svg(points: List[Dict[str, float]], paths: List[List[Tuple[float, float]]], uid: str, x_unit: str = "trade") -> str:
    W, H, L, R, T, B = _MC_W, _MC_H, _MC_L, _MC_R, _MC_T, _MC_B
    pw, ph = W - L - R, H - T - B
    vals = [p[k] for p in points for k in ("p05", "p95")]
    if paths:
        ends = sorted(pts[-1][1] for pts in paths)
        vals += [ends[max(0, len(ends) // 20)], ends[min(len(ends) - 1, len(ends) - 1 - len(ends) // 20)]]
    lo, hi = min(min(vals), 0.0), max(max(vals), 0.0)
    step = _nice_step(hi - lo, 5)
    lo, hi = math.floor(lo / step) * step, math.ceil(hi / step) * step
    tmax = points[-1]["tc"] or 1.0

    def X(tc: float) -> float:
        return L + pw * (tc / tmax)

    def Y(v: float) -> float:
        return T + ph * (1.0 - (v - lo) / ((hi - lo) or 1.0))

    def line(key: str) -> str:
        return " ".join(f"{'M' if i == 0 else 'L'}{_coord(X(p['tc']))},{_coord(Y(p[key]))}" for i, p in enumerate(points))

    def area(k_lo: str, k_hi: str) -> str:
        up = [f"{_coord(X(p['tc']))},{_coord(Y(p[k_hi]))}" for p in points]
        dn = [f"{_coord(X(p['tc']))},{_coord(Y(p[k_lo]))}" for p in reversed(points)]
        return "M" + " L".join(up + dn) + " Z"

    gid, cid = f"mcfan-{uid}", f"mcclip-{uid}"
    parts = [
        f'<defs><linearGradient id="{gid}" x1="0" x2="1" y1="0" y2="0">'
        '<stop offset="0" class="mc-fan-stop" stop-opacity="0.05"/><stop offset="1" class="mc-fan-stop" stop-opacity="0.16"/>'
        f'</linearGradient><clipPath id="{cid}"><rect x="{_coord(L)}" y="{_coord(T)}" width="{_coord(pw)}" height="{_coord(ph)}"/></clipPath></defs>',
        _mc_axes(lo, hi, step, tmax, Y, X, x_unit=x_unit),
        f'<path fill="url(#{gid})" d="{area("p05", "p95")}"/>',
        f'<path class="mc-band-inner" d="{area("p25", "p75")}"/>',
    ]
    path_els = []
    for pts in paths:
        d = " ".join(f"{'M' if i == 0 else 'L'}{_coord(X(t))},{_coord(Y(v))}" for i, (t, v) in enumerate(pts))
        path_els.append(f'<path class="mc-path {"mc-path-loss" if pts[-1][1] < 0 else "mc-path-win"}" d="{d}"/>')
    parts.append(f'<g clip-path="url(#{cid})">{"".join(path_els)}</g>')
    parts.append(f'<path class="mc-edge mc-edge-up" d="{line("p95")}"/>')
    parts.append(f'<path class="mc-edge mc-edge-down" d="{line("p05")}"/>')
    parts.append(f'<path class="mc-median" d="{line("p50")}"/>')
    end = points[-1]
    ys: List[float] = []
    for name, key, tone in (("P95", "p95", "up"), ("P50", "p50", "mid"), ("P05", "p05", "down")):
        y = Y(end[key])
        for q in ys:
            if abs(y - q) < 20:
                y = q + 20
        ys.append(y)
        parts.append(_mc_tag(X(tmax), y, f"{name} {end[key]:+.1f}%", tone))
    parts.append(
        f'<line class="mc-cross" x1="0" y1="{_coord(T)}" x2="0" y2="{_coord(T + ph)}" visibility="hidden"/>'
        '<circle class="mc-dot" cx="0" cy="0" r="4" visibility="hidden"/>'
        f'<rect class="mc-hit" x="{_coord(L)}" y="{_coord(T)}" width="{_coord(pw)}" height="{_coord(ph)}" fill="transparent"/>'
    )
    cps = json.dumps([[round(p["tc"], 2)] + [round(p[k], 2) for k in ("p05", "p25", "p50", "p75", "p95")] for p in points])
    geo = json.dumps([L, pw, T, ph, lo, hi, tmax])
    return (
        f'<svg class="mc-svg mc-chart-fan" viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
        f'aria-label="Simulated return band by {x_unit}" data-unit="{x_unit}" data-cps="{_esc(cps)}" data-geo="{_esc(geo)}">{"".join(parts)}</svg>'
    )


def _mc_median_svg(points: List[Dict[str, float]], uid: str, x_unit: str = "trade", members: Sequence[Tuple[str, List[List[float]], bool]] = ()) -> str:
    W, H, L, R, T, B = _MC_W, _MC_H, _MC_L, _MC_R, _MC_T, _MC_B
    pw, ph = W - L - R, H - T - B
    vals = [p["p50"] for p in points] + [float(v) for _, path, _ in members for _, v in path]
    lo, hi = min(min(vals), 0.0), max(max(vals), 0.0)
    step = _nice_step(hi - lo, 4)
    lo, hi = math.floor(lo / step) * step - (step if min(vals) >= 0 else 0), math.ceil(hi / step) * step
    tmax = points[-1]["tc"] or 1.0

    def X(tc: float) -> float:
        return L + pw * (tc / tmax)

    def Y(v: float) -> float:
        return T + ph * (1.0 - (v - lo) / ((hi - lo) or 1.0))

    gid = f"mcmed-{uid}"
    d = " ".join(f"{'M' if i == 0 else 'L'}{_coord(X(p['tc']))},{_coord(Y(p['p50']))}" for i, p in enumerate(points))
    parts = [
        f'<defs><linearGradient id="{gid}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" class="mc-fan-stop" stop-opacity="0.22"/>'
        '<stop offset="1" class="mc-fan-stop" stop-opacity="0"/></linearGradient></defs>',
        _mc_axes(lo, hi, step, tmax, Y, X, x_unit=x_unit),
        f'<path fill="url(#{gid})" d="{d} L{_coord(X(tmax))},{_coord(Y(0))} L{_coord(X(0))},{_coord(Y(0))} Z"/>',
    ]
    # A portfolio: each member's own median path (its own capital), under the combined one.
    for colour, path, dashed in members:
        md = " ".join(f"{'M' if k == 0 else 'L'}{_coord(X(float(t)))},{_coord(Y(float(v)))}" for k, (t, v) in enumerate(path))
        parts.append(f'<path class="mc-member" d="{md}" stroke="{_esc(colour)}"{" stroke-dasharray=\"4 3\"" if dashed else ""}/>')
    parts.append(f'<path class="mc-median mc-median-thick" d="{d}"/>')
    marks = points[1:]
    stride = max(1, len(marks) // 4)
    chosen = marks[stride - 1::stride]
    if marks[-1] not in chosen:
        chosen.append(marks[-1])
    for p in chosen[-4:]:
        x, y = X(p["tc"]), Y(p["p50"])
        parts.append(f'<circle class="mc-median-pt" cx="{_coord(x)}" cy="{_coord(y)}" r="4.5"/>')
        parts.append(f'<text class="mc-median-lbl" x="{_coord(x)}" y="{_coord(y - 12)}" text-anchor="middle">{p["p50"]:+.1f}%</text>')
    parts.append(f'<text class="mc-tick mc-tick-note" x="{_coord(X(tmax) + 10)}" y="{_coord(Y(0) + 3.5)}">Breakeven</text>')
    return f'<svg class="mc-svg mc-chart-median" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Median simulated path">{"".join(parts)}</svg>'


def _mc_hist_svg(mc: Dict[str, Any]) -> str:
    """Terminal-return histogram -- only from the engine's own
    `terminal_outcome_histogram`; nothing is drawn without it."""
    hist = mc.get("terminal_outcome_histogram")
    if not isinstance(hist, dict):
        return ""
    edges = [float(e) for e in (hist.get("bin_edges_pct") or []) if _is_finite_number(e)]
    counts = [float(c) for c in (hist.get("counts") or []) if _is_finite_number(c)]
    n = min(len(counts), len(edges) - 1)
    if n < 2:
        return ""
    W, H, L, R, T, B = _MC_W, _MC_H, _MC_L, _MC_R, _MC_T, _MC_B
    R = 24.0
    top_pad = T + 24.0
    pw, ph = W - L - R, H - top_pad - B
    total = sum(counts[:n]) or 1.0
    shares = [c / total * 100.0 for c in counts[:n]]
    ymax = max(shares) or 1.0
    ystep = _nice_step(ymax, 3)
    ymax = math.ceil(ymax / ystep) * ystep
    lo, hi = min(edges[0], 0.0), max(edges[n], 0.0)

    def X(v: float) -> float:
        return L + pw * (v - lo) / ((hi - lo) or 1.0)

    def Y(p: float) -> float:
        return top_pad + ph * (1.0 - p / ymax)

    parts = []
    g = 0.0
    while g <= ymax + 1e-9:
        parts.append(f'<line class="mc-grid" x1="{_coord(L)}" y1="{_coord(Y(g))}" x2="{_coord(L + pw)}" y2="{_coord(Y(g))}"/>')
        parts.append(f'<text class="mc-tick" x="{_coord(L - 8)}" y="{_coord(Y(g) + 3.5)}" text-anchor="end">{g:.0f}%</text>')
        g += ystep
    p05, cvar = _mc_f(mc.get("profit_pct_p05")), _mc_f(mc.get("cvar_95_pct"))
    if p05 is not None and p05 > lo:
        xr = X(p05)
        parts.append(f'<rect class="mc-cvar-zone" x="{_coord(L)}" y="{_coord(top_pad)}" width="{_coord(xr - L)}" height="{_coord(ph)}"/>')
        if cvar is not None and xr - L > 40:
            parts.append(f'<text class="mc-cvar-lbl" x="{_coord((L + xr) / 2)}" y="{_coord(top_pad + 16)}" text-anchor="middle">CVaR</text>')
            parts.append(f'<text class="mc-cvar-lbl" x="{_coord((L + xr) / 2)}" y="{_coord(top_pad + 28)}" text-anchor="middle">{-cvar:+.1f}%</text>')
    for i in range(n):
        e0, e1, sh = edges[i], edges[i + 1], shares[i]
        x0, x1 = X(e0), X(e1)
        loss = (e0 + e1) / 2 < 0
        op = 1.0 if loss else 0.35 + min(0.6, sh / ymax)
        parts.append(
            f'<rect class="mc-bin {"mc-bin-loss" if loss else "mc-bin-win"}" x="{_coord(x0 + 1.5)}" y="{_coord(Y(sh))}" '
            f'width="{_coord(max(x1 - x0 - 3, 1))}" height="{_coord(Y(0) - Y(sh))}" rx="3" fill-opacity="{op:.2f}" '
            f'data-tip="{_esc(f"{e0:+.1f}% … {e1:+.1f}%|Paths|{sh:.1f}%")}"/>'
        )
    placed: List[Tuple[float, float]] = []
    for name, key, tone in (("P05", "profit_pct_p05", "down"), ("Median", "profit_pct_p50", "mid"), ("P95", "profit_pct_p95", "up")):
        v = _mc_f(mc.get(key))
        if v is None:
            continue
        x = X(max(min(v, hi), lo))
        text = f"{name} {v:+.1f}%"
        w = len(text) * 6.3 + 12
        y = T - 2
        for (px, py) in placed:
            if abs(px - x) < (w + 60) / 2 and py == y:
                y += 20
        placed.append((x, y))
        parts.append(f'<line class="mc-pline mc-pline-{tone}" x1="{_coord(x)}" y1="{_coord(y + 18)}" x2="{_coord(x)}" y2="{_coord(top_pad + ph)}"/>')
        parts.append(
            f'<rect class="mc-tag mc-tag-{tone}" x="{_coord(x - w / 2)}" y="{_coord(y)}" width="{_coord(w)}" height="18" rx="5"/>'
            f'<text class="mc-tag-text" x="{_coord(x)}" y="{_coord(y + 12.5)}" text-anchor="middle">{_esc(text)}</text>'
        )
    xstep = _nice_step(hi - lo, 6)
    v = math.ceil(lo / xstep) * xstep
    while v <= hi + 1e-9:
        parts.append(f'<text class="mc-tick mc-tick-x" x="{_coord(X(v))}" y="{_coord(H - 10)}" text-anchor="middle">{"0%" if abs(v) < 1e-9 else f"{v:+.0f}%"}</text>')
        v += xstep
    return f'<svg class="mc-svg mc-chart-histogram" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Distribution of simulated final returns">{"".join(parts)}</svg>'


def _collapse_toggle(show: str, hide: str, tags: str, inner: str) -> str:
    """Preview-style "Show … / Hide …" dashed toggle over a collapsed block
    (inline onclick, so it also works after the SPA injects this HTML)."""
    esc_show, esc_hide = _esc(show), _esc(hide)
    return (
        '<button type="button" class="mc-toggle" aria-expanded="false" '
        "onclick=\"var o=this.getAttribute('aria-expanded')!=='true';this.setAttribute('aria-expanded',o);"
        "this.nextElementSibling.classList.toggle('open',o);"
        f"this.querySelector('.mc-toggle-l').textContent=o?'{esc_hide}':'{esc_show}';\">"
        f'<span class="mc-toggle-l">{esc_show}</span>'
        f'<span class="mc-toggle-tags">{_esc(tags)}</span>'
        '<span class="mc-toggle-ic" aria-hidden="true"></span>'
        "</button>"
        f'<div class="mc-more"><div class="mc-more-in">{inner}</div></div>'
    )


def _mc_one_in(p: Optional[float], paths: Optional[float] = None) -> str:
    if p is None:
        return ""
    if p <= 0:
        return f"0 of {paths:,.0f} paths" if paths else "no simulated path"
    if p >= 50:
        return f"≈ {p / 10:.0f} in 10"
    return f"≈ 1 in {max(1, round(100.0 / p)):,}"


_MDD_SCEN_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _mdd_scenarios(result: Dict[str, Any]) -> Dict[str, Any]:
    """Max-drawdown scenarios from the bot's own Monte Carlo, good -> bad ->
    very bad: P50 / P95 / P99 of the simulated max drawdowns, the drawdown
    of the bot's ACTUAL trade order on the same starting capital and the
    same formula (so the two are comparable), and the share of simulated
    paths worse than that actual path. The exceedance is re-run with the
    engine's own `_simulate_horizon` on the same trades, capital, horizon,
    iterations and seed, so its P50/P95 reproduce the saved figures."""
    mc = result.get("mc") if isinstance(result.get("mc"), dict) else {}
    out: Dict[str, Any] = {k: mc.get(v) for k, v in (("p50", "median_max_drawdown"), ("p95", "p95_max_drawdown"), ("p99", "p99_max_drawdown"))
                           if _is_finite_number(mc.get(v))}
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    cap = mc.get("capital_at_risk") if _is_finite_number(mc.get("capital_at_risk")) else perf.get("capital_at_risk")
    pnls = [float(x["realized_pnl"]) for x in (evidence.get("closed_trade_series") or [])
            if isinstance(x, dict) and _is_finite_number(x.get("realized_pnl"))]
    if not (pnls and _is_finite_number(cap) and float(cap) > 0):
        return out
    eq, peak, hist = float(cap), float(cap), 0.0
    for v in pnls:
        eq += v
        peak = max(peak, eq)
        if peak > 0:
            hist = max(hist, min(1.0, max(0.0, (peak - eq) / peak)))
    out["hist"] = hist * 100.0
    iters = int(mc.get("iterations") or 0)
    horizon = int(mc.get("horizon_trades") or len(pnls))
    if iters <= 0 or len(pnls) < 5:
        return out
    key = (result.get("code"), len(pnls), round(sum(pnls), 6), float(cap), horizon, iters)
    hit = _MDD_SCEN_CACHE.get(key)
    if hit is None:
        try:
            import numpy as np
            from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import MonteCarloSimulationEngine

            st = MonteCarloSimulationEngine._simulate_horizon(
                pnls=np.asarray(pnls, dtype=np.float64), initial_equity=float(cap), horizon=horizon,
                iterations=iters, seed=42, block_bootstrap=True, current_drawdown_pct=out["hist"],
                trade_frequency_per_day=None,
            )
            hit = {"p_exceed": st.get("p_capital_loss_gt_current_dd")}
        except Exception:  # noqa: BLE001 - optional figure
            logger.warning("max drawdown exceedance could not be computed", exc_info=True)
            hit = {}
        if len(_MDD_SCEN_CACHE) > 512:
            _MDD_SCEN_CACHE.clear()
        _MDD_SCEN_CACHE[key] = hit
    out.update(hit)
    return out


def _pf_joint(result: Dict[str, Any]) -> Dict[str, Any]:
    """A portfolio's JOINT simulation (every member drawn on the same day),
    or {} for a single bot / a run whose joint simulation is not valid."""
    portfolio = result.get("portfolio")
    joint = portfolio.get("joint_simulation") if isinstance(portfolio, dict) else None
    return joint if isinstance(joint, dict) and joint.get("is_valid") else {}


def _render_joint_monte_carlo(result: Dict[str, Any], compact: bool = False) -> str:
    """Monte Carlo for a portfolio: the joint run (`JointMonteCarloEngine`),
    one draw = one day taken for EVERY member, so bots that lose together
    keep losing together; members with a hidden order book are in through
    their public daily PnL. Horizon in days. Every figure and chart is a
    field of `portfolio.joint_simulation` -- nothing recomputed here."""
    joint = _pf_joint(result)
    f = _mc_f
    iterations = f(joint.get("iterations"))
    horizon_days = f(joint.get("horizon_calendar_days"))
    sample = f(joint.get("sample_buckets"))
    members = _pf_members(result)
    hidden = [m for m in members if m.get("ledger_hidden")]
    uid = re.sub(r"[^A-Za-z0-9]", "", str(result.get("code") or "pf"))[:16] + ("ov" if compact else "jt")
    parts: List[str] = []

    chips = []
    if iterations:
        chips.append(f"{iterations:,.0f} paths")
    if sample:
        chips.append(f"Daily buckets · {sample:,.0f} days")
    if horizon_days:
        chips.append(f"Horizon {horizon_days:,.0f} days")
    per_member = joint.get("per_member_var_95_pct") or {}
    if members:
        chips.append(f"{len(per_member) or len(members)} of {len(members)} bots")
    parts.append(
        '<div class="mc-head"><span class="mc-title" title="One draw = one day taken for every bot at once '
        '(stationary bootstrap over daily buckets): bots that lose together keep losing together.">'
        'Monte Carlo simulation · joint</span>'
        f'<span class="mc-chips">{"".join(f"<span class=mc-chip>{_esc(c)}</span>" for c in chips)}</span></div>'
    )
    if hidden and not compact:
        names = ", ".join(str(m.get("short") or m.get("label")) for m in hidden)
        parts.append(_note_chip(
            f"{len(hidden)} concealed bot{'s' if len(hidden) > 1 else ''} included via public daily PnL",
            f"{_esc(names)} hide{'s' if len(hidden) == 1 else ''} the order book on OKX, so the public daily PnL stands in "
            "for the trades. Without it the combined book would read safer than it is.", "info"))
    if joint.get("sample_is_thin") and not compact:
        parts.append(_note_chip("Thin sample: read as a range", "; ".join(
            _esc(w) for w in (joint.get("warnings") or []) if isinstance(w, str)) or "Few shared days to resample from."))

    ruin, pprof = f(joint.get("p_ruin")), f(joint.get("probability_of_profit"))
    ploss = None if pprof is None else max(0.0, 100.0 - pprof)
    var95, cvar95 = f(joint.get("var_95_pct")), f(joint.get("cvar_95_pct"))
    var99, cvar99 = f(joint.get("var_99_pct")), f(joint.get("cvar_99_pct"))
    mdd, p95dd = f(joint.get("median_max_drawdown")), f(joint.get("p95_max_drawdown"))

    def ret_tone(loss: Optional[float]) -> str:
        return "bad" if loss is not None and loss > 0 else "good"

    def dd_tone(v: Optional[float]) -> str:
        return "good" if v is not None and v < 10 else ("warn" if v is not None and v < 20 else "bad")

    def stat_strip(items: Sequence[Tuple[str, str, Optional[str], str]]) -> str:
        cells = [(l, k, v, t) for l, k, v, t in items if v is not None]
        if not cells:
            return ""
        return '<div class="mc-strip">' + "".join(
            f'<div class="mc-stat"><div class="mc-stat-l">{_calc_label_html(l, k)}</div>'
            f'<div class="mc-stat-v mc-t-{t}">{_esc(v)}</div></div>'
            for l, k, v, t in cells
        ) + "</div>"

    pct = lambda v, signed=True: None if v is None else (f"{v:+.1f}%" if signed else f"{v:.1f}%")  # noqa: E731
    if compact:
        parts.append(stat_strip([
            ("VaR 95%", "pf_joint_var", pct(None if var95 is None else -var95), ret_tone(var95)),
            ("CVaR 95%", "mc_cvar95", pct(None if cvar95 is None else -cvar95), ret_tone(cvar95)),
            ("P(profit)", "mc_p_profit", pct(pprof, False), "good" if (pprof or 0) > 85 else ("warn" if (pprof or 0) > 65 else "bad")),
            ("Median max DD", "pf_sim_max_dd_median", pct(mdd, False), dd_tone(mdd)),
            ("P95 max DD", "pf_sim_max_dd", pct(p95dd, False), dd_tone(p95dd)),
            ("Probability of ruin", "pf_ruin", pct(ruin, False), "good" if (ruin or 0) <= 1 else ("warn" if (ruin or 0) <= 5 else "bad")),
        ]))
    else:
        def pcard(label: str, key: str, v: float, tone: str) -> str:
            return (
                f'<div class="mc-pcard"><div class="mc-pcard-l">{_calc_label_html(label, key)}</div>'
                f'<div class="mc-pcard-v mc-t-{tone}">{v:.1f}%</div>'
                f'<span class="mc-pbar"><span class="mc-pbar-fill mc-bg-{tone}" style="width:{max(0.0, min(100.0, v)):.1f}%"></span></span>'
                f'<div class="mc-pcard-s">{_esc(_mc_one_in(v, iterations))}</div></div>'
            )
        cards = []
        if ruin is not None:
            cards.append(pcard("Probability of ruin", "pf_ruin", ruin, "good" if ruin <= 1 else ("warn" if ruin <= 5 else "bad")))
        if ploss is not None:
            cards.append(pcard("P(loss)", "mc_p_loss", ploss, "good" if ploss < 15 else ("warn" if ploss < 35 else "bad")))
        if pprof is not None:
            cards.append(pcard("P(profit)", "mc_p_profit", pprof, "good" if pprof > 85 else ("warn" if pprof > 65 else "bad")))
        if cards:
            parts.append(f'<div class="mc-pcards mc-pcards-3">{"".join(cards)}</div>')
        parts.append(stat_strip([
            ("VaR 95%", "pf_joint_var", pct(None if var95 is None else -var95), ret_tone(var95)),
            ("CVaR 95%", "mc_cvar95", pct(None if cvar95 is None else -cvar95), ret_tone(cvar95)),
            ("VaR 99%", "mc_var99", pct(None if var99 is None else -var99), ret_tone(var99)),
            ("CVaR 99%", "mc_cvar99", pct(None if cvar99 is None else -cvar99), ret_tone(cvar99)),
            ("Median max DD", "pf_sim_max_dd_median", pct(mdd, False), dd_tone(mdd)),
            ("P95 max DD", "pf_sim_max_dd", pct(p95dd, False), dd_tone(p95dd)),
        ]))

    # Charts, from the joint run's own checkpoints / histogram / sample paths.
    points = [
        {"tc": float(c["day"]), **{k: float(c[k]) for k in ("p05", "p25", "p50", "p75", "p95")}}
        for c in (joint.get("path_checkpoints") or [])
        if isinstance(c, dict) and all(_is_finite_number(c.get(k)) for k in ("day", "p05", "p25", "p50", "p75", "p95"))
    ]
    if len(points) < 3:
        points = []
    by_label = {m.get("label"): m for m in members}
    member_lines = []
    for label, path in (joint.get("member_median_paths") or {}).items():
        m = by_label.get(label) or {}
        clean = [[float(t), float(v)] for t, v in path if _is_finite_number(t) and _is_finite_number(v)] if isinstance(path, list) else []
        if len(clean) >= 2:
            member_lines.append((str(m.get("colour") or "#64748b"), clean, bool(m.get("ledger_hidden")), str(m.get("short") or label)))
    median_legend = ""
    if points and member_lines:
        member_lines = [ml for ml in member_lines]
    if points:
        end = points[-1]["p50"]
        median_legend = (
            '<span class="mc-legend mc-legend-median">'
            f'<span><i class="mc-lg-med"></i>Combined {end:+.1f}%</span>'
            + "".join(
                f'<span><i style="background:{_esc(c)}"></i>{_esc(n)} {path[-1][1]:+.1f}%{" (daily PnL)" if dashed else ""}</span>'
                for c, path, dashed, n in member_lines
            )
            + "</span>"
        )
    median_svg = _mc_median_svg(points, uid, x_unit="day", members=[(c, pth, d) for c, pth, d, _ in member_lines]) if points else ""
    tone = "good" if points and points[-1]["p50"] >= 0 else "bad"
    parts[0] = parts[0]  # (head)
    if compact:
        if median_svg:
            parts.append(f'<div class="mc-ov-median mc-ov-{tone}">{median_legend}{median_svg}</div>')
        elif not points:
            parts.append('<div class="mc-ov-note">Paths are drawn from the next analysis of this portfolio.</div>')
        return _section("Monte Carlo simulation", f'<div class="mc-wrap mc-joint mc-tone-{tone}">' + "".join(parts) + "</div>")

    views = []
    paths = [
        [(float(t), float(v)) for t, v in pth]
        for pth in (joint.get("sample_paths") or [])
        if isinstance(pth, list) and len(pth) >= 2
    ]
    if points:
        views.append(("band", "Confidence bands", _mc_band_svg(points, paths, uid, x_unit="day")))
    hist = _mc_hist_svg({
        "terminal_outcome_histogram": joint.get("terminal_histogram"),
        "profit_pct_p05": joint.get("profit_pct_p05"), "profit_pct_p50": joint.get("profit_pct_p50"),
        "profit_pct_p95": joint.get("profit_pct_p95"), "cvar_95_pct": joint.get("cvar_95_pct"),
    })
    if hist:
        views.append(("dist", "Return distribution", hist))
    if median_svg:
        views.append(("median", "Median path", median_svg))
    chart_html = ""
    if views:
        btns = "".join(
            f'<button type="button" class="mc-vbtn" data-view="{k}" '
            f"onclick=\"this.closest('.mc-chart').setAttribute('data-view','{k}')\">{_esc(lbl)}</button>"
            for k, lbl, _ in views
        )
        legends = (
            '<span class="mc-legend mc-legend-band"><span><i class="mc-lg-med"></i>Median · combined</span>'
            '<span><i class="mc-lg-in"></i>P25–P75</span><span><i class="mc-lg-out"></i>P05–P95</span>'
            + ('<span><i class="mc-lg-loss"></i>Losing path</span>' if paths else "") + "</span>"
            '<span class="mc-legend mc-legend-dist"><span><i class="mc-lg-win"></i>Profit</span><span><i class="mc-lg-lossbar"></i>Loss</span></span>'
            + median_legend
        )
        panes = "".join(f'<div class="mc-view mc-view-{k}">{svg}</div>' for k, _, svg in views)
        chart_html = (
            f'<div class="mc-chart" data-view="{views[0][0]}">'
            f'<div class="mc-chart-bar"><span class="mc-vtabs">{btns}</span>{legends}</div>'
            f'<div class="mc-chart-body">{panes}<div class="mc-tipbox"></div></div></div>'
        )
    p05, p50, p95 = f(joint.get("profit_pct_p05")), f(joint.get("profit_pct_p50")), f(joint.get("profit_pct_p95"))
    ladder_rows = [r for r in (("P95 · good case", p95, "p95"), ("Median", p50, "med"), ("P05 · bad case", p05, "p05")) if r[1] is not None]
    ladder_html = ""
    if ladder_rows:
        items = "".join(
            f'<div class="mc-lad-row mc-lad-{cls}"><i></i><span>{_esc(name)}</span>'
            f'<b class="{"mc-t-good" if v >= 0 else "mc-t-bad"}">{v:+.1f}%</b></div>'
            for name, v, cls in ladder_rows
        )
        head = f'<div class="st-label mc-lad-h">After {horizon_days:,.0f} days</div>' if horizon_days else ""
        ladder_html = f'<div class="mc-ladder-card">{head}<div class="mc-ladder">{items}</div></div>'
    if chart_html or ladder_html:
        parts.append(f'<div class="mc-mid">{chart_html}{ladder_html}</div>')
    elif not points:
        parts.append('<div class="mc-ov-note">Paths and the return distribution are drawn from the next analysis of this portfolio.</div>')

    # What combining the bots did to the tail, and each bot alone.
    undiv, indep = f(joint.get("sum_individual_var_95_pct")), f(joint.get("independent_var_95_pct"))
    ratio = f(joint.get("diversification_ratio"))

    def jv_rows(rows: Sequence[Tuple[str, str, float, str]]) -> str:
        top = max((abs(v) for _, _, v, _ in rows), default=0.0) or 1.0
        return "".join(
            f'<div class="jv"><span class="jv-l">{dot}{_esc(name)}</span>'
            f'<span class="jv-plot"><span class="jv-fill jv-{tone}" style="width:{max(0.0, v) / top * 100:.1f}%"></span></span>'
            f'<b class="jv-v mc-t-{tone}">{v:.1f}%</b></div>'
            for name, dot, v, tone in rows
        )

    blocks = []
    if var95 is not None and undiv is not None:
        # Only the portfolio's own bar is an assessment: better than the
        # co-movement-free benchmark is good, between it and undiversified
        # is a warning. The two benchmarks are reference bars.
        own_tone = "good" if indep is not None and var95 <= indep else ("warn" if var95 < undiv else "bad")
        rows = [("Undiversified", "", undiv, "ink"), ("This portfolio", "", var95, own_tone)]
        if indep is not None:
            rows.append(("Independent", "", indep, "ink"))
        tail = (
            f'<span class="st-chip st-chip-good">−{ratio * 100:.0f}% tail</span>'
            if ratio is not None and ratio > 0 else ""
        )
        cost = f(joint.get("correlation_cost_pct"))
        foot = []
        if cost is not None:
            foot.append(f"<span><em>Correlation cost</em>{cost:+.1f} pts</span>")
        if ratio is not None:
            foot.append(f"<span><em>Tail removed</em>{ratio * 100:.0f}%</span>")
        blocks.append(
            '<div class="jv-card"><div class="gc-head"><span class="st-label" title="Undiversified = each bot&#39;s own VaR, '
            'capital-weighted and summed (the bots as one bet). Independent = the same bots with their co-movement removed '
            '(the best case). This portfolio = the joint run.">VaR 95% · diversification</span>' + tail + "</div>"
            + jv_rows(rows) + (f'<div class="jv-foot">{"".join(foot)}</div>' if foot else "") + "</div>"
        )
    if per_member:
        rows = []
        for label, v in per_member.items():
            if not _is_finite_number(v):
                continue
            m = by_label.get(label) or {}
            dot = f'<i class="jv-dot" style="background:{_esc(m.get("colour") or "#64748b")}"></i>'
            rows.append((str(m.get("short") or label), dot, float(v), "bad" if float(v) >= 15 else ("warn" if float(v) > 0 else "good")))
        if rows:
            blocks.append(
                '<div class="jv-card"><div class="gc-head"><span class="st-label" title="Each bot&#39;s own simulated '
                'VaR on its own capital, same engine and horizon.">VaR 95% · each bot alone</span></div>'
                + jv_rows(rows) + "</div>"
            )
    if blocks:
        parts.append(f'<div class="jv-grid">{"".join(blocks)}</div>')
    return _section("Monte Carlo simulation", f'<div class="mc-wrap mc-joint mc-tone-{tone}">' + "".join(parts) + "</div>", anchor="monte-carlo")


def _render_monte_carlo(result: Dict[str, Any], compact: bool = False) -> str:
    """Monte Carlo, laid out like the redesign preview: 4 probability cards,
    a metric strip, the chart (band with sample paths / distribution / median,
    switched in place, hover read-out), the return ladder at the horizon, and
    losing streaks + the three horizons behind a toggle. Every figure is a
    field of `result["mc"]` (see bot/mcp/analytics/simulation/monte_carlo.py);
    a missing one hides its tile instead of being filled in. No methodology
    drawer (project owner, 2026-09-24) -- each figure's "*" carries its formula."""
    if _pf_joint(result):
        # A portfolio: the joint run, never the merged-order-book bootstrap
        # (which leaves out hidden members and loses the same-day co-movement).
        return _render_joint_monte_carlo(result, compact)
    mc = result.get("mc")
    if not isinstance(mc, dict) or not mc:
        return ""
    f = _mc_f
    iterations = f(mc.get("iterations"))
    horizon = f(mc.get("horizon_trades"))
    sample = f(mc.get("sample_size"))
    uid = re.sub(r"[^A-Za-z0-9]", "", str(result.get("code") or "x"))[:16] or "x"
    parts: List[str] = []

    if mc.get("deferred_loss_bias"):
        _ol = next((re.search(r"([\d,]+) USDT of unrealised loss", w) for w in (mc.get("warnings") or [])
                    if isinstance(w, str) and "unrealised loss" in w), None)
        _ol_txt = f"{_ol.group(1)} USDT of unrealized loss" if _ol else "The unrealized loss"
        parts.append(_note_chip("Optimistic: open loss not included",
            f"{_ol_txt} in open positions is not in this simulation: paths are resampled from closed trades only. "
            "Real risk is higher than the figures below (P(loss), max drawdown, VaR)."
        ))
    if mc.get("sample_is_thin"):
        warns = mc.get("warnings")
        thin_text = "; ".join(_esc(w) for w in warns if isinstance(w, str)) if isinstance(warns, list) else ""
        if not thin_text:
            thin_text = (
                f"Thin sample ({_int_text(mc.get('sample_size'))} observations): the "
                "simulation still runs, but should only be read as a reference range, "
                "not a firm estimate -- a bootstrap percentile can only resolve to "
                "about 1/n, so at this sample size the figures at both tails (the 5th "
                "percentile, probability of ruin, the 95th percentile of drawdown) "
                "carry a large standard error."
            )
        parts.append(_note_chip("Thin sample: read as a range", thin_text))

    chips = []
    if iterations:
        chips.append(f"{iterations:,.0f} paths")
    if sample:
        chips.append(f"Bootstrap · {sample:,.0f} trades")
    if horizon:
        chips.append(f"Horizon {horizon:,.0f} trades")
    parts.append(
        f'<div class="mc-head"><span class="mc-title" >Monte Carlo simulation</span>'
        f'<span class="mc-chips">{"".join(f"<span class=mc-chip>{_esc(c)}</span>" for c in chips)}</span></div>'
    )

    def pcard(label: str, key: str, v: float, tone: str) -> str:
        w = max(0.0, min(100.0, v))
        return (
            f'<div class="mc-pcard"><div class="mc-pcard-l">{_calc_label_html(label, key)}</div>'
            f'<div class="mc-pcard-v mc-t-{tone}">{v:.1f}%</div>'
            f'<span class="mc-pbar"><span class="mc-pbar-fill mc-bg-{tone}" style="width:{w:.1f}%"></span></span>'
            f'<div class="mc-pcard-s">{_esc(_mc_one_in(v, iterations))}</div></div>'
        )

    cards = []
    ruin = f(mc.get("p_ruin"))
    if ruin is not None:
        cards.append(pcard("Probability of ruin", "mc_p_ruin", ruin, "good" if ruin <= 1 else ("warn" if ruin <= 5 else "bad")))
    mdd = f(mc.get("p_mdd_gt_25"))
    if mdd is not None:
        cards.append(pcard("P(max DD > 25%)", "mc_p_mdd25", mdd, "good" if mdd < 10 else ("warn" if mdd < 25 else "bad")))
    ploss = f(mc.get("p_loss_after_horizon"))
    if ploss is not None:
        cards.append(pcard("P(loss)", "mc_p_loss", ploss, "good" if ploss < 15 else ("warn" if ploss < 35 else "bad")))
    pprof = f(mc.get("probability_of_profit"))
    if pprof is None and ploss is not None:
        pprof = 100.0 - ploss
    if pprof is not None:
        cards.append(pcard("P(profit)", "mc_p_profit", pprof, "good" if pprof > 85 else ("warn" if pprof > 65 else "bad")))
    if cards and not compact:
        parts.append(f'<div class="mc-pcards">{"".join(cards)}</div>')

    p05, p50, p95 = f(mc.get("profit_pct_p05")), f(mc.get("profit_pct_p50")), f(mc.get("profit_pct_p95"))
    stats = []
    var95, cvar95 = f(mc.get("var_95_pct")), f(mc.get("cvar_95_pct"))
    if var95 is not None:
        stats.append(("VaR 95%", "mc_var95", f"{-var95:+.1f}%", "bad" if var95 > 0 else "good"))
    if cvar95 is not None:
        stats.append(("CVaR 95%", "mc_cvar95", f"{-cvar95:+.1f}%", "bad" if cvar95 > 0 else "good"))
    mar = f(mc.get("mar_ratio_median"))
    if mar is not None:
        stats.append(("Median MAR", "mc_mar", f"{mar:.2f}", "ink"))
    pfm = f(mc.get("profit_factor_median"))
    if pfm is not None:
        stats.append(("Median PF", "mc_pf", f"{pfm:.2f}", "ink"))
    if p05 is not None and p50 is not None and p95 is not None and p50 - max(p05, -100.0) > 0.01:
        skew = max(0.0, p95 - p50) / (p50 - max(p05, -100.0))
        stats.append(("Upside/downside ratio", "mc_skew", f"{skew:.1f}x", "good" if skew >= 1.4 else ("bad" if skew <= 0.7 else "ink")))
    if sample:
        stats.append(("Sample", "sample_size", f"{sample:,.0f}", "ink"))
    if stats:
        parts.append(
            '<div class="mc-strip">'
            + "".join(
                f'<div class="mc-stat"><div class="mc-stat-l">{_calc_label_html(l, k)}</div>'
                f'<div class="mc-stat-v mc-t-{t}">{_esc(v)}</div></div>'
                for l, k, v, t in stats
            )
            + "</div>"
        )

    sc = _mdd_scenarios(result)
    rows_dd = []
    if _is_finite_number(sc.get("p50")):
        rows_dd.append(("Typical · P50", "mc_mdd_p50", f"{float(sc['p50']):.1f}%", "good"))
    if _is_finite_number(sc.get("hist")):
        rows_dd.append(("Actual max drawdown", "mc_mdd_hist", f"{float(sc['hist']):.1f}%", "ink"))
    if _is_finite_number(sc.get("p95")):
        rows_dd.append(("Bad · P95", "mc_mdd_p95", f"{float(sc['p95']):.1f}%", "warn"))
    if _is_finite_number(sc.get("p99")):
        rows_dd.append(("Very bad · P99", "mc_mdd_p99", f"{float(sc['p99']):.1f}%", "bad"))
    if _is_finite_number(sc.get("p_exceed")):
        pe = float(sc["p_exceed"])
        rows_dd.append(("P(worse than actual)", "mc_mdd_exceed", f"{pe:.1f}%", "good" if pe < 10 else ("warn" if pe < 30 else "bad")))
    if len(rows_dd) >= 2 and not compact:
        parts.append(
            '<div class="st-label mc-dd-h">Max drawdown scenarios</div><div class="mc-strip mc-dd-strip">'
            + "".join(
                f'<div class="mc-stat"><div class="mc-stat-l">{_calc_label_html(l, k)}</div>'
                f'<div class="mc-stat-v mc-t-{t}">{_esc(v)}</div></div>'
                for l, k, v, t in rows_dd
            )
            + "</div>"
        )

    points = _mc_pct_points(mc)
    if compact:
        # Overview: no probability cards, no drawdown scenarios, no ladder,
        # no streaks/horizons -- the six figures above and the median path.
        if points:
            parts.append(
                f'<div class="mc-ov-median mc-ov-{"good" if points[-1]["p50"] >= 0 else "bad"}"><span class="mc-legend mc-legend-median">'
                '<span><i class="mc-lg-med"></i>Median path</span></span>'
                f'{_mc_median_svg(points, uid + "ov")}</div>'
            )
        if not (stats or points):
            return ""
        # Title first, then its caveat chips (preview order).
        heads = [x for x in parts if x.startswith('<div class="mc-head">')]
        parts = heads + [x for x in parts if x not in heads]
        return _section("Monte Carlo simulation", '<div class="mc-wrap">' + "".join(parts) + "</div>")
    paths = _mc_sample_paths(result, mc) if points else []
    views = []
    if points:
        views.append(("band", "Confidence bands", _mc_band_svg(points, paths, uid)))
    hist = _mc_hist_svg(mc)
    if hist:
        views.append(("dist", "Distribution", hist))
    if points:
        views.append(("median", "Median path", _mc_median_svg(points, uid)))
    chart_html = ""
    if views:
        btns = "".join(
            f'<button type="button" class="mc-vbtn" data-view="{k}" '
            f"onclick=\"this.closest('.mc-chart').setAttribute('data-view','{k}')\">{_esc(lbl)}</button>"
            for k, lbl, _ in views
        )
        path_note = (
            f"{len(paths)} paths redrawn with the same bootstrap from this bot's own trades, to show the spread; "
            "all percentiles come from the full simulation."
        )
        legends = (
            '<span class="mc-legend mc-legend-band">'
            '<span><i class="mc-lg-med"></i>Median</span><span><i class="mc-lg-in"></i>P25–P75</span>'
            '<span><i class="mc-lg-out"></i>P05–P95</span>'
            + (f'<span title="{_esc(path_note)}"><i class="mc-lg-loss"></i>Losing path</span>' if paths else "")
            + "</span>"
            '<span class="mc-legend mc-legend-dist"><span><i class="mc-lg-win"></i>Profit</span><span><i class="mc-lg-lossbar"></i>Loss</span></span>'
            '<span class="mc-legend mc-legend-median"><span><i class="mc-lg-med"></i>Median path</span></span>'
        )
        panes = "".join(f'<div class="mc-view mc-view-{k}">{svg}</div>' for k, _, svg in views)
        chart_html = (
            f'<div class="mc-chart" data-view="{views[0][0]}">'
            f'<div class="mc-chart-bar"><span class="mc-vtabs">{btns}</span>{legends}</div>'
            f'<div class="mc-chart-body">{panes}<div class="mc-tipbox"></div></div></div>'
        )
    ladder_rows = [
        ("Best", f(mc.get("profit_pct_best")), "best"),
        ("P95 · good case", p95, "p95"),
        ("Median", p50, "med"),
        ("P05 · bad case", p05, "p05"),
        ("Worst", f(mc.get("profit_pct_worst")), "worst"),
    ]
    ladder_rows = [r for r in ladder_rows if r[1] is not None]
    ladder_html = ""
    if ladder_rows:
        items = "".join(
            f'<div class="mc-lad-row mc-lad-{cls}"><i></i><span>{_esc(name)}</span>'
            f'<b class="{"mc-t-good" if v >= 0 else "mc-t-bad"}">{("-100% (ruin)" if v <= -100 else f"{v:+.1f}%")}</b></div>'
            for name, v, cls in ladder_rows
        )
        head = f'<div class="st-label mc-lad-h">Return at trade {horizon:,.0f}</div>' if horizon else ""
        ladder_html = f'<div class="mc-ladder-card">{head}<div class="mc-ladder">{items}</div></div>'
    if chart_html or ladder_html:
        parts.append(f'<div class="mc-mid">{chart_html}{ladder_html}</div>')

    # Losing streaks + horizons, behind a toggle (preview: "Show streaks & horizons")
    streak_rows = []
    for n_ in (5, 10):
        obs, base = f(mc.get(f"p_{n_}_loss_streak")), f(mc.get(f"p_{n_}_loss_streak_baseline"))
        if obs is None or base is None:
            continue
        exc = f(mc.get(f"p_{n_}_loss_streak_excess"))
        exc = max(0.0, obs - base) if exc is None else exc
        streak_rows.append(
            f'<div class="mc-streak"><div class="mc-streak-h"><span>≥ {n_} in a row</span>'
            f'<span class="st-chip {"st-chip-warn" if exc >= 1 else "st-chip-flat"} mc-streak-x" '
            f'title="Excess over the random baseline, clamped at zero">+{exc:.1f}pp</span></div>'
            f'<div class="mc-bar"><span class="mc-bar-obs" style="width:{max(0.0, min(100.0, obs)):.1f}%"></span><b>{obs:.1f}%</b></div>'
            f'<div class="mc-bar"><span class="mc-bar-base" style="width:{max(0.0, min(100.0, base)):.1f}%"></span><b>{base:.1f}%</b></div></div>'
        )
    streak_html = ""
    if streak_rows:
        streak_html = (
            '<div class="mc-streaks"><div class="gc-head">'
            '<span class="st-label" title="Share of simulated paths with at least one losing streak of that length, '
            'against the same chance for independent trades at this bot\'s own loss rate.">Losing streaks</span>'
            '<span class="mc-streak-lg"><span><i class="mc-lg-obs"></i>This bot</span><span><i class="mc-lg-base"></i>Random</span></span></div>'
            + "".join(streak_rows) + "</div>"
        )
    scen = [s for s in (mc.get("horizon_scenarios") or []) if isinstance(s, dict)]
    by = {s.get("label"): s for s in scen}
    hz_cards = []
    hz_trades = []
    for key, name in (("SHORT", "Short"), ("MEDIUM", "Medium"), ("LONG", "Long")):
        s = by.get(key)
        if not s:
            continue
        pop = f(s.get("probability_of_profit"))
        if pop is None and f(s.get("p_loss_after_horizon")) is not None:
            pop = 100.0 - float(s["p_loss_after_horizon"])
        sp05, sp50, sp95 = f(s.get("profit_pct_p05")), f(s.get("profit_pct_p50")), f(s.get("profit_pct_p95"))
        dd, its, tr = f(s.get("median_max_drawdown")), f(s.get("iterations")), f(s.get("horizon_trades"))
        if tr is not None:
            hz_trades.append(f"{name.lower()} {tr:,.0f}")

        def pc(v: Optional[float]) -> str:
            if v is None:
                return "—"
            if v <= -100:
                return "-100%"
            return "0.0%" if abs(v) < 0.05 else f"{v:+.1f}%"

        hz_cards.append(
            f'<div class="mc-hz{" mc-hz-main" if key == "MEDIUM" else ""}">'
            f'<div class="mc-hz-h"><b>{name}</b><span>{"" if tr is None else f"{tr:,.0f} trades"}</span></div>'
            f'<div class="mc-hz-pop"><b>{"—" if pop is None else f"{pop:.1f}%"}</b><span>P(profit)</span></div>'
            f'<span class="mc-pbar"><span class="mc-pbar-fill mc-bg-{"good" if (pop or 0) > 85 else ("warn" if (pop or 0) > 65 else "bad")}" style="width:{max(0.0, min(100.0, pop or 0.0)):.1f}%"></span></span>'
            '<div class="mc-hz-q"><span>P05</span><span>Median</span><span>P95</span>'
            f'<b class="mc-t-bad">{pc(sp05)}</b><b>{pc(sp50)}</b><b class="mc-t-good">{pc(sp95)}</b></div>'
            '<div class="mc-hz-f">'
            f'<span>Median max DD</span><b>{"—" if dd is None else f"{dd:.1f}%"}</b>'
            f'<span>Paths</span><b>{"—" if its is None else f"{its:,.0f}"}</b></div></div>'
        )
    hz_html = ""
    if hz_cards:
        label = str(mc.get("horizon_stability_label") or "")
        tone = {"STABLE ACROSS HORIZONS": "good", "HOLDS ONLY AT SHORT HORIZON": "bad", "NEEDS MORE TIME": "warn"}.get(label.upper(), "flat")
        pill = f'<span class="st-chip st-chip-{tone}">{_esc(label.capitalize())}</span>' if label else ""
        exceeds = ""
        if mc.get("horizon_exceeds_observed"):
            days, span = f(mc.get("horizon_calendar_days")), f(mc.get("observed_span_days"))
            detail = f" (simulated ≈ {days:.0f} days, only {span:.0f} days observed)" if days and span else ""
            exceeds = _note_chip("Longer than the observed data", (
                '<div class="notice notice-warning">The simulated horizon is longer than the actual '
                f"observed data{_esc(detail)}: this is an EXTRAPOLATION beyond the observed data, "
                "not a validated result.</div>"
            ))
        hz_html = (
            '<div class="mc-hzs" aria-label="Outcome distribution by horizon">'
            '<div class="gc-head"><span class="st-label" title="The same bootstrap re-run over a shorter and a longer trade count.">By horizon</span>'
            f"{pill}</div>"
            f'<div class="mc-hz-grid">{"".join(hz_cards)}</div>{exceeds}</div>'
        )
    if streak_html or hz_html:
        tags = []
        if streak_rows:
            tags.append("Losing streaks (≥5, ≥10)")
        if hz_trades:
            tags.append(" / ".join(hz_trades) + " trades")
        if hz_cards:
            tags.append("P(profit) · max DD")
        parts.append(
            _collapse_toggle(
                "Show streaks & horizons", "Hide streaks & horizons", " · ".join(tags),
                f'<div class="mc-bottom">{streak_html}{hz_html}</div>',
            )
        )

    if not (cards or stats or chart_html or ladder_html or hz_html):
        return ""
    body = '<div class="mc-wrap">' + "".join(parts) + "</div>"
    return _section("Monte Carlo simulation", body, anchor="monte-carlo")


def _subsection(title: str, chart: str, theory: str = "") -> str:
    if not chart:
        return ""
    return f'<div class="subsection" aria-label="{_esc(title)}">{chart}{theory}</div>'


# --------------------------------------------------------------------------- #
# Section 5 -- statistical inference
# --------------------------------------------------------------------------- #




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




def _render_ledger_reconciliation_notice(evidence: Dict[str, Any]) -> str:
    """States WHY a PARTIAL_LEDGER ledger is partial, distinguishing its two
    non-overlapping causes instead of one generic status label.

    Boss's own correction on a real bot (58D7D205FB591484, 2026-09-23): a
    report of mine attributed this bot's PARTIAL_LEDGER to hitting the fetch
    page cap, when the real cause -- readable right here from
    `ledger_truncated=False` -- was `short_coverage` (the fetched trades
    cover only 90 of its 325 days as lead trader). `service.py`'s own
    `elif truncated or short_coverage:` branch never told these two apart in
    the UI before this; `reconciliation_warnings` already carries the exact
    sentence service.py wrote for whichever one applied, so this just
    surfaces it instead of writing a second copy of that logic here.
    """
    if evidence.get("reconciliation_status") != "PARTIAL_LEDGER":
        return ""
    warnings = evidence.get("reconciliation_warnings")
    if not isinstance(warnings, list) or not warnings:
        return ""
    truncated = evidence.get("ledger_truncated")
    tag = "Hit the fetch page limit" if truncated else "Covers only part of its lead-trader history"
    return _note_chip(f"Partial ledger: {tag.lower()}", "; ".join(str(w) for w in warnings))


# --------------------------------------------------------------------------- #
# Section 7 -- traded assets
# --------------------------------------------------------------------------- #




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
        # Không có nhánh dữ liệu thật nào cho BOT NÀY -- trả rỗng (xem
        # `_render_limited_market_scope`'s docstring cho lý do).
        return ""
    # Same `.expert-summary-box` treatment the FULL page gives its "Core
    # Strategy Thesis" paragraph (see the FULL-mode expert-assessment
    # renderer above) -- previously this LIMITED paragraph sat bare in
    # `.narrative-prose-content` with no box/label, reading as a flat wall
    # of document text next to the FULL page's styled cards (boss's report
    # on a real 60004-blocked OKX bot: "trình bày thì dạng document like").
    body = (
        '<div class="narrative-body-wrap">'
        '<div class="narrative-meta-bar">'
        '<span class="badge badge-info">SYNTHESISED FROM PUBLIC SOURCES</span>'
        "</div>"
        '<div class="expert-summary-box">'
        f'<div class="expert-summary-text">{_esc(text)}</div>'
        "</div>"
        "</div>"
    )
    return _section("Expert assessment", body, anchor="nhan-dinh")


def _render_limited_growth(result: Dict[str, Any], anchor: Optional[str] = "tang-truong") -> str:
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
        parts.append(
            '<div class="subsection" aria-label="Capital curve inferred from weekly PnL">'
            + chart + caption + "</div>"
        )

    ratio_pts = limited_view.pnl_ratio_points(evidence)
    if ratio_pts:
        chart = _line_chart(
            ratio_pts,
            y_unit="%",
            x_label_prefix="Point",
            aria_label="Published pnlRatio over time",
        )
        parts.append(
            '<div class="subsection" aria-label="Published return ratio over time (pnlRatio)">'
            + chart + "</div>"
        )

    if not parts:
        # Không có nhánh dữ liệu thật nào cho BOT NÀY -- trả rỗng (xem
        # `_render_limited_market_scope`'s docstring cho lý do).
        return ""

    theory = _theory(
        "Comparative tracking: cumulative equity reconstructed from weekly PnL versus official OKX pnlRatio time series.",
        "Equity reconstructed via EquityCurveBuilder: Equity(w) = PnL(w) / pnlRatio(w) per weekly reporting cycle."
    )
    return _section(
        "Growth & outcome composition", "".join(parts) + theory, anchor=anchor
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
    # Không có nhánh dữ liệu thật nào cho BOT NÀY -- trả rỗng (xem
    # `_render_limited_market_scope`'s docstring cho lý do). Lý do MC không
    # chạy được đã có sẵn trong `text` của `limited.py` (bullet `mc_text`,
    # tự hiện ở mục QUANTITATIVE EVIDENCE ngay đầu report), không cần lặp ở
    # đây bằng một card riêng.
    return ""


def _render_limited_market_scope(result: Dict[str, Any]) -> str:
    """ "thi-truong" cho LIMITED: bot 60004 không có `primary_share_pct`
    (cần sổ lệnh để tính tỉ trọng theo mã) nên không thể trả lời "thị
    trường được chấm chiếm bao nhiêu % hoạt động" -- KHÔNG có nhánh dữ liệu
    thật nào cho mục này, chỉ có lý do vì sao không đo được.

    Trả rỗng, không dựng `_section` chỉ để chứa mỗi lời giải thích -- yêu
    cầu của project owner sau khi xem report thật trên một bot 60004
    (2026-09-22): "cái nào k có dữ kiện xử lý vì bị ẩn thì nêu ngay từ đầu
    -> và ẩn các mục không thể tính toán xử lý view khi thiếu dữ liệu".
    Lý do đã được nêu MỘT LẦN, ngay từ đầu report, trong bullet cuối cùng
    của `assess_limited_bot`'s `text` (xem `limited.py`) -- mục lục bên trái
    (tự sinh từ `_SECTION_HEADING_RE`) cũng tự rụng đúng mục này vì không có
    `<section>` nào được render.
    """
    return ""


def _render_limited_playstyle(result: Dict[str, Any]) -> str:
    """ "cach-choi" cho LIMITED: tái dựng cách bot chơi (`strategy_drift`,
    `behavioral_risk` ở FULL) cần chuỗi lệnh với thời điểm mở/đóng, đòn bẩy,
    hướng lệnh -- không có gì trong số đó công khai cho một bot 60004.

    Không có nhánh dữ liệu thật nào -- trả rỗng thay vì một card chỉ chứa
    lời xin lỗi (xem `_render_limited_market_scope`'s docstring cho lý do).
    """
    return ""


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
        # Không có nhánh dữ liệu thật nào cho BOT NÀY -- trả rỗng (xem
        # `_render_limited_market_scope`'s docstring cho lý do).
        return ""
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
    table = _table_caption("Public-source performance metrics") + _table(["Metric (public source)", "Value"], rows)
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
        # Không có nhánh dữ liệu thật nào cho BOT NÀY -- trả rỗng (xem
        # `_render_limited_market_scope`'s docstring cho lý do).
        return ""
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

    Không có nhánh dữ liệu thật nào -- trả rỗng thay vì một card chỉ chứa
    lời xin lỗi (xem `_render_limited_market_scope`'s docstring cho lý do).
    """
    return ""


def _render_limited_inference(result: Dict[str, Any]) -> str:
    """ "suy-luan" cho LIMITED: PSR/DSR (Bailey &amp; López de Prado) cần
    chuỗi lợi nhuận TỪNG LỆNH để tính skew/kurtosis/Sharpe mỗi lệnh -- một
    chuỗi PnL tuần chỉ có 12 điểm không đứng vào vai trò đó, kể cả khi
    Monte Carlo ở mục trên vẫn chạy được (chạy trên PnL tuần, không phải
    trên PnL từng lệnh).

    Không có nhánh dữ liệu thật nào -- trả rỗng thay vì một card chỉ chứa
    lời xin lỗi (xem `_render_limited_market_scope`'s docstring cho lý do).
    """
    return ""


def _render_limited_assets(result: Dict[str, Any]) -> str:
    """ "tai-san" cho LIMITED: danh sách hợp đồng bot đang chạy
    (`profile.traderInsts`) khi đọc được -- KHÔNG có tỉ trọng vốn/PnL theo
    từng tài sản (cần sổ lệnh để tính) như bảng "Tài sản đang giao dịch"
    của một bot FULL.
    """
    evidence = result.get("evidence") or {}
    instruments = limited_view.traded_instruments(evidence)
    if not instruments:
        # Không có nhánh dữ liệu thật nào cho BOT NÀY -- trả rỗng (xem
        # `_render_limited_market_scope`'s docstring cho lý do).
        return ""
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
    table = _table_caption("Running instruments") + _table(["Running instruments (traderInsts)"], rows)
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

    Không có nhánh dữ liệu thật nào -- trả rỗng thay vì một card chỉ chứa
    lời xin lỗi (xem `_render_limited_market_scope`'s docstring cho lý do).
    """
    return ""


def _render_limited_dimensions(result: Dict[str, Any]) -> str:
    """Mục "Điểm từng chiều rủi ro" của trang LIMITED: y hệt bản đầy đủ.

    Bằng chứng thô của từng chiều đo được nằm trong khối "Score explanation
    notes (*)" (xem `_render_score_basis`), không còn tự nó là một khối
    luôn-hiện riêng ngay dưới biểu đồ -- project owner's own report,
    2026-09-22: "không view ra ngoài tóm tắt và đưa vào mục score note".
    """
    return _render_dimensions_section(result)


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


def _scenario_lab(result: Dict[str, Any]) -> Dict[str, Any]:
    """The scenario laboratory: from the live dossier, else the one
    recomputed from the bot's own files (`data.offline_bot_metrics`)."""
    lab = _insights(result).get("scenario_laboratory")
    if isinstance(lab, dict) and lab.get("scenarios"):
        return lab
    lab = result.get("_offline_lab")
    return lab if isinstance(lab, dict) else {}


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








def _render_methodology_footer(result: Dict[str, Any]) -> str:
    """Data limitations and open questions, folded away at the foot of the tab.

    Deliberately NOT a `<section class="card">`: the result tab is the
    user-facing overview and must not grow another card. This is a closed
    accordion after the last card, so an ordinary reader is not stopped by it
    and an auditor can still open it.
    """
    insights = _insights(result)
    if not insights:
        # A saved record: what it does not carry is not talked about
        # (project owner, 2026-09-24).
        return ""
        missing = (
            "Behavioural DNA" if _scenario_lab(result) else
            "Behavioural DNA, the scenario laboratory and the cost-sensitivity "
            "scenarios"
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


_DEEP_DIVE_IDS = ("cach-choi", "tang-truong", "nhan-dinh", "diem-chieu")


def _deep_dive_summaries(result: Dict[str, Any], expert_html: str) -> Dict[str, str]:
    """The one-line figure under each tab label, read from the same fields
    the pane itself shows."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    out: Dict[str, str] = {}
    strategy = evidence.get("strategy") if isinstance(evidence.get("strategy"), dict) else {}
    rows = [r for r in (strategy.get("phase_breakdown") or []) if isinstance(r, dict)]
    traded = {r.get("phase") for r in rows if _is_finite_number(r.get("trades")) and float(r["trades"]) > 0}
    if traded:
        out["cach-choi"] = f"{len(traded)}/6 phases traded"
    elif strategy.get("observed_profile"):
        prof = _split_label(OBSERVED_PROFILE_LABEL_VI.get(strategy.get("observed_profile"), ""))[0]
        if prof:
            out["cach-choi"] = prof[0].upper() + prof[1:]
    pnls = _extract_trade_pnls(result)
    if pnls:
        out["tang-truong"] = f"Net PnL {sum(pnls):+,.0f}"
    modes = _insights(result).get("failure_modes") or []
    if modes:
        out["nhan-dinh"] = f"{len(modes)} root cause{'s' if len(modes) != 1 else ''}"
    elif expert_html:
        k = len(re.findall(r'st-chip-(?:warn|bad|flat) ex-badge', expert_html))
        out["nhan-dinh"] = f"{k} watch-out{'s' if k != 1 else ''}" if k else "No watch-outs"
    dims = _dimension_rows(evidence)
    if dims and dims[0]["score"] is not None:
        tier = dict((t, n) for t, n, _ in _DIM_TIERS).get(dims[0]["tier"], str(dims[0]["tier"]).title())
        out["diem-chieu"] = f"Highest {dims[0]['score']:.0f} · {tier}"
    return out


def _render_deep_dive(result: Dict[str, Any]) -> str:
    """How it trades / Growth / Expert assessment / Risk dimensions in ONE
    card, switched by a tab bar -- the redesign preview's "deep dive" card.

    Each pane stays its own `<section class="card" id="...">` (so anchors,
    the section-id invariants and the per-section tests are unchanged); the
    wrapper's `data-active` attribute picks the visible one through CSS, and
    the tab buttons only set that attribute (inline `onclick`, which also
    works after the SPA injects this HTML).
    """
    panes = [
        ("cach-choi", "How it trades", _render_strategy_section(result)),
        ("tang-truong", "Growth", _render_growth_section(result)),
        # A bot with no public trade: the assessment could only talk about
        # what is missing (project owner, 2026-09-24), so it is left out.
        ("nhan-dinh", "Expert assessment", "" if _no_trades(result) else _render_narrative(result)),
        ("diem-chieu", "Risk dimensions", _render_dimensions_section(result)),
    ]
    panes = [p for p in panes if p[2]]
    if not panes:
        return ""
    if len(panes) == 1:
        return panes[0][2]
    summaries = _deep_dive_summaries(result, dict((k, h) for k, _, h in panes).get("nhan-dinh", ""))
    tabs = "".join(
        f'<button type="button" class="dd-tab" data-pane="{key}" role="tab" '
        f"onclick=\"this.closest('.dd-card').setAttribute('data-active','{key}')\">"
        f'<span class="dd-tab-l">{_esc(label)}</span>'
        f'<span class="dd-tab-v">{_esc(summaries.get(key, ""))}</span>'
        "</button>"
        for key, label, _ in panes
    )
    return (
        f'<div class="dd-card" data-active="{panes[0][0]}">'
        f'<div class="dd-tabbar" role="tablist">{tabs}</div>'
        + "".join(html for _, _, html in panes)
        + "</div>"
    )


def _render_overview(result: Dict[str, Any]) -> str:
    """Overview: the Summary tab cut to its essentials -- the two main
    causes and the headline evidence figures, the three growth charts, and
    the six Monte Carlo figures with the median path. Same renderers, same
    numbers as Detail; nothing here is computed on its own."""
    limited = result.get("status") == "LIMITED"
    blocks = [
        ("", "ket-luan", "", _render_conclusion(result, compact=True)),
        ("Growth", "tang-truong", "tang-truong",
         # Its own gradient id: the Detail copy of the same chart keeps the original.
         (_render_limited_growth(result, anchor=None) if limited else _render_growth_section(result, anchor=None))
         .replace('id="gc-fill-', 'id="gc-fill-ov-').replace("url(#gc-fill-", "url(#gc-fill-ov-")),
        ("", "monte-carlo", "", _render_monte_carlo(result, compact=True)),
    ]
    # No "Details" links: the Overview / Detail switch right above does that.
    out = []
    for title, _target, _pane, html in blocks:
        if not html:
            continue
        if title:
            # The title sits inside the card, as its first line (preview).
            html = re.sub(r'(<section\b[^>]*><div class="block-b">)', lambda m: m.group(1) + f'<div class="ov-title">{_esc(title)}</div>', html, count=1)
        out.append(f'<div class="ov-block">{html}</div>')
    return "".join(out)


def _render_report_modes(overview_html: str, detail_html: str) -> str:
    """Overview (basic) / Detail (the three tabs, unchanged)."""
    if not overview_html:
        return detail_html
    btn = (
        '<button type="button" class="rm-btn rm-btn-{k}" '
        "onclick=\"this.closest('.report-modes').setAttribute('data-mode','{k}')\">{label}</button>"
    )
    return (
        '<div class="report-modes" data-mode="overview">'
        '<div class="rm-bar"><div class="rm-seg" role="tablist">'
        + btn.format(k="overview", label="Overview")
        + btn.format(k="detail", label="Detail")
        + '</div><span class="rm-hint rm-hint-overview">Key figures at a glance</span>'
        '<span class="rm-hint rm-hint-detail">Full analysis &middot; 3 tabs</span></div>'
        f'<div class="rm-overview">{overview_html}</div>'
        f'<div class="rm-detail">{detail_html}</div>'
        "</div>"
    )


def _render_tab_report(result: Dict[str, Any]) -> str:
    if result.get("status") == "LIMITED":
        return _render_tab_report_limited(result)
    sections = [
        _render_conclusion(result),
        # HỒI QUY 23/09: `ideallm.md` §8.1 xếp "Essence -> Behavioral DNA ->
        # ..." NGAY TRONG tab 1 (Analyst Result), miễn phí cho cả admin lẫn
        # user -- đây từng nằm nhầm trong `_render_tab_market` (Premium),
        # trong khi `chat.py`'s `_collect_evidence` đã đọc đúng spec này từ
        # đầu và thu thập observed_profile/directional_bias/entry_style*
        # KHÔNG điều kiện vai trò. Hai nơi lệch nhau khiến chat lộ đúng nội
        # dung mà report tĩnh đang khoá sau thẻ "PRO/INSTITUTIONAL" cho vai
        # USER -- sửa ở ĐÂY (dời đúng chỗ theo spec) thay vì khoá thêm bên
        # chat.py, vì §8.2 (Premium Market) chỉ nói về phân tích THỊ TRƯỜNG
        # (cấu trúc thị trường, thanh khoản, orderflow...), không phải hành
        # vi giao dịch riêng của bot.
        _render_deep_dive(result),
        _render_monte_carlo(result),
        _render_methodology_footer(result),
    ]
    return "".join(s for s in sections if s)


# --------------------------------------------------------------------------- #
# Other & Position tab, laid out like the redesign preview (2026-09-24).
# --------------------------------------------------------------------------- #


def _kv_row(label_html: str, value: str, tone: str = "") -> str:
    cls = f" pv-v-{tone}" if tone else ""
    return f'<div class="pv-kv"><span class="pv-kv-l">{label_html}</span><b class="pv-kv-v{cls}">{_esc(value)}</b></div>'


def _signed_tone(v: Any) -> str:
    if not _is_finite_number(v):
        return ""
    return "good" if float(v) > 0 else ("bad" if float(v) < 0 else "")


# Drawdown / Calmar computed by `data._risk_fallbacks` on another basis than
# the engine's: each basis gets its own formula text (the * next to the row).
_DD_BASIS_INFO = {
    "WEEKLY_EQUITY": {"max_drawdown_pct": "dd_weekly_max", "current_drawdown_pct": "dd_weekly_cur"},
    "POOLED_WEEKLY_EQUITY": {"max_drawdown_pct": "dd_pooled_max", "current_drawdown_pct": "dd_pooled_cur"},
    "MARGIN_FLOOR": {"max_drawdown_pct": "dd_margin_max", "current_drawdown_pct": "dd_margin_cur"},
}
# Rows a bot without any public closed trade can still show (they come
# from OKX's weekly returns, not from trades).
_PUBLIC_WITHOUT_TRADES = frozenset({"max_drawdown_pct", "current_drawdown_pct", "calmar_ratio"})

_CALMAR_BASIS_INFO = {
    "WEEKLY_RETURNS": "calmar_ratio_weekly",
    "POOLED_WEEKLY_EQUITY": "calmar_ratio_equity",
    "MARGIN_FLOOR": "calmar_ratio_equity",
    "NO_DRAWDOWN": "calmar_ratio_nodd",
    "WIPED_OUT": "calmar_ratio_wiped",
}


def _render_trade_metrics(result: Dict[str, Any]) -> str:
    """Trade metrics in three columns (Return / Risk-adjusted / Activity),
    every value straight from `evidence.performance`."""
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return ""
    perf = evidence.get("performance")
    if not isinstance(perf, dict) or not perf:
        return ""
    # Activity figures a saved record may lack, derived from the same closed
    # trades the rest of the page reads (never a guessed default).
    perf = dict(perf)
    if not _is_finite_number(perf.get("trade_frequency_per_day")) and _is_finite_number(perf.get("trade_count")) \
            and _is_finite_number(perf.get("ledger_coverage_days")) and float(perf["ledger_coverage_days"]) > 0:
        perf["trade_frequency_per_day"] = float(perf["trade_count"]) / float(perf["ledger_coverage_days"])
    holds = [(float(r["close_ms"]) - float(r["open_ms"])) / 60000.0 for r in (result.get("_ledger") or [])
             if isinstance(r, dict) and _is_finite_number(r.get("open_ms")) and _is_finite_number(r.get("close_ms")) and float(r["close_ms"]) >= float(r["open_ms"])]
    if not _is_finite_number(perf.get("average_hold_time_minutes")) and holds:
        perf["average_hold_time_minutes"] = sum(holds) / len(holds)
    signs = [float(x["realized_pnl"]) for x in sorted((x for x in (evidence.get("closed_trade_series") or []) if isinstance(x, dict)
             and _is_finite_number(x.get("realized_pnl")) and _is_finite_number(x.get("close_time"))), key=lambda x: float(x["close_time"]))]
    if signs:
        def longest(pred: Callable[[float], bool]) -> int:
            best = cur = 0
            for v in signs:
                cur = cur + 1 if pred(v) else 0
                best = max(best, cur)
            return best
        if perf.get("max_win_streak") is None:
            perf["max_win_streak"] = longest(lambda v: v > 0)
        if perf.get("max_loss_streak") is None:
            perf["max_loss_streak"] = longest(lambda v: v < 0)

    no_trades = _no_trades(result)

    def money(v: Any) -> str:
        return f"{float(v):+,.1f} USDT" if _is_finite_number(v) else "—"

    groups = [
        ("Return", [
            ("total_pnl", "Total PnL", lambda v: money(v), _signed_tone),
            ("expectancy", "Expectancy / trade", lambda v: money(v), _signed_tone),
            ("profit_factor", "Profit factor", lambda v: _num(v, 2), lambda v: "good" if _is_finite_number(v) and float(v) >= 1 else "bad"),
            ("payoff_ratio", "Payoff ratio", lambda v: _num(v, 2), lambda v: ""),
            ("win_rate", "Win rate", lambda v: _pct(v, 1), lambda v: ""),
        ]),
        ("Risk-adjusted", [
            # "from peak": divided by the capital peak (see its formula
            # note), not by the reference capital the header strip and the
            # Drawdown card use -- same fall, different denominator.
            ("max_drawdown_pct", "Max drawdown", lambda v: _pct(v, 1), lambda v: "bad" if _is_finite_number(v) and float(v) > 0 else ""),
            ("current_drawdown_pct", "Current drawdown", lambda v: _pct(v, 1), lambda v: "bad" if _is_finite_number(v) and float(v) > 0 else ""),
            ("sharpe_ratio", "Sharpe ratio", lambda v: _num(v, 2), _signed_tone),
            ("sortino_ratio", "Sortino ratio", lambda v: _num(v, 2), _signed_tone),
            ("calmar_ratio", "Calmar ratio", lambda v: _num(v, 2), _signed_tone),
        ]),
        ("Activity", [
            ("trade_count", "Closed trades", lambda v: _int_text(v), lambda v: ""),
            ("trade_frequency_per_day", "Trades / day", lambda v: _num(v, 2), lambda v: ""),
            ("average_hold_time_minutes", "Average hold", lambda v: f"{_num(v, 1)} min" if _is_finite_number(v) else "—", lambda v: ""),
            ("max_win_streak", "Longest winning streak", lambda v: _int_text(v), lambda v: ""),
            ("max_loss_streak", "Longest losing streak", lambda v: _int_text(v), lambda v: ""),
        ]),
    ]
    cols = []
    tiles: List[Tuple[str, str, str]] = []
    for title, rows in groups:
        items = []
        for key, label, fmt, tone in rows:
            if key not in perf and not (key in ("current_drawdown_pct", "calmar_ratio") and perf.get("_calmar_basis")):
                continue
            info, val, tn = key, fmt(perf.get(key)), tone(perf.get(key))
            if key in ("max_drawdown_pct", "current_drawdown_pct") and _is_finite_number(perf.get(key)) and 0 < float(perf[key]) < 1:
                # Small drawdowns keep their significant digits (0.008%, not 0.0%).
                val = _pct(perf[key], 3 if float(perf[key]) < 0.1 else 2)
            if key in ("max_drawdown_pct", "current_drawdown_pct") and perf.get("_dd_basis") in _DD_BASIS_INFO:
                info = _DD_BASIS_INFO[perf["_dd_basis"]][key]
                exact_zero = _is_finite_number(perf.get(key)) and float(perf[key]) == 0
                if perf["_dd_basis"] == "MARGIN_FLOOR" and val != "—" and not exact_zero:
                    val = "≤ " + val
                elif perf["_dd_basis"] == "POOLED_WEEKLY_EQUITY" and val != "—" and not exact_zero:
                    val = "≈ " + val
            if key == "calmar_ratio":
                cb = perf.get("_calmar_basis")
                info = _CALMAR_BASIS_INFO.get(cb, key)
                if cb == "NO_DRAWDOWN" and perf.get(key) is None:
                    val, tn = "No drawdown", "good"
                elif cb == "WIPED_OUT" and perf.get(key) is None:
                    val, tn = "Wiped out", "bad"
                elif cb in ("POOLED_WEEKLY_EQUITY", "MARGIN_FLOOR") and val != "—":
                    val = "≈ " + val
            if key == "current_drawdown_pct" and perf.get(key) is None and key not in perf:
                continue
            if val == "—" or (no_trades and key not in _PUBLIC_WITHOUT_TRADES):
                # Nothing public to show for this row (project owner,
                # 2026-09-24): leave it out instead of a dash.
                continue
            items.append(_kv_row(_calc_label_html(label, info), val, tn))
            tiles.append((_calc_label_html(label, info), val, tn))
        if items:
            cols.append(f'<div class="pv-col"><div class="st-label">{_esc(title)}</div>{"".join(items)}</div>')
    if not cols:
        return ""
    if len(cols) == 1 and len(tiles) <= 4:
        # One short group (e.g. only the weekly-return rows of a bot with no
        # public trade): tiles read better than a lone column.
        cols = ["".join(
            f'<div class="pv-tile"><div class="pv-tile-l">{l}</div><div class="pv-tile-v pv-v-{t}">{_esc(v)}</div></div>'
            for l, v, t in tiles)]
    chips = []
    if _is_finite_number(perf.get("trade_count")) and not no_trades:
        chips.append(f"{int(float(perf['trade_count'])):,} closed trades")
    lead = perf.get("declared_lead_days")
    if _is_finite_number(perf.get("ledger_coverage_days")):
        cov = float(perf["ledger_coverage_days"])
        # A partial ledger (fewer days than the time as lead trader) says so
        # in the chip itself rather than in a separate warning box.
        chips.append(f"{cov:.0f} of {float(lead):.0f} days" if perf.get("reconciliation_status") == "PARTIAL_LEDGER"
                     and _is_finite_number(lead) and float(lead) > cov else f"{cov:.0f} days")
    warn = "; ".join(str(w) for w in (perf.get("reconciliation_warnings") or []) if w) if perf.get("reconciliation_status") == "PARTIAL_LEDGER" else ""
    head = (
        '<div class="pv-head"><span class="mc-title" >Trade metrics</span>'
        + (f'<span class="mc-chip"{f" title={chr(34)}{_esc(warn)}{chr(34)}" if warn else ""}>{_esc(" · ".join(chips))}</span>' if chips else "")
        + "</div>"
    )
    body = head + (f'<div class="pv-tiles pv-tiles-{len(tiles)}">{cols[0]}</div>' if len(cols) == 1 and cols[0].startswith('<div class="pv-tile">')
                   else f'<div class="pv-cols">{"".join(cols)}</div>')
    return _section("Trade metrics", body, anchor="so-lieu")


def _ref_capital(result: Dict[str, Any]) -> Optional[float]:
    """The reference capital loss_analysis.py sizes drawdowns against."""
    prof = compute_loss_profile(result.get("evidence")) or {}
    cap = prof.get("capital")
    return float(cap) if _is_finite_number(cap) and float(cap) > 0 else None


def _episode_indices(pnls: List[float], capital: Optional[float] = None) -> Optional[Tuple[int, int, Optional[int]]]:
    """(peak, trough, back-at-peak) indices on the cumulative curve with
    point 0 = start -- same rule as loss_analysis.py `_deepest_episode`
    (deepest in percent of peak equity when a capital is known), so the
    chart marks the episode that section reports."""
    cum, peak, peak_i, best = 0.0, 0.0, 0, None
    pts = [0.0]
    for v in pnls:
        cum += v
        pts.append(cum)
    for i, v in enumerate(pts):
        if v >= peak:
            peak, peak_i = v, i
            continue
        depth = peak - v
        score = (min(1.0, depth / (capital + peak)) if capital + peak > 0 else 1.0) if capital else depth
        if best is None or score > best[0]:
            best = (score, peak_i, i)
    if best is None:
        return None
    _, pi, ti = best
    back = next((j for j in range(ti + 1, len(pts)) if pts[j] >= pts[pi]), None)
    return pi, ti, back


def _episode_svg(pnls: List[float], idx: Tuple[int, int, Optional[int]]) -> str:
    pi, ti, back = idx
    pts = [0.0]
    for v in pnls:
        pts.append(pts[-1] + v)
    span = max(ti - pi, 4)
    a = max(0, pi - span // 2)
    b = min(len(pts) - 1, (back if back is not None else ti) + span // 2)
    seg = pts[a:b + 1]
    if len(seg) < 3:
        return ""
    W, H, L, R, T, B = 600.0, 214.0, 4.0, 4.0, 28.0, 30.0
    lo, hi = min(seg), max(seg)
    rng = (hi - lo) or 1.0

    def X(i: int) -> float:
        return L + (W - L - R) * (i - a) / max(b - a, 1)

    def Y(v: float) -> float:
        return T + (H - T - B) * (1 - (v - lo) / rng)

    d = " ".join(f"{'M' if k == 0 else 'L'}{_coord(X(a + k))},{_coord(Y(v))}" for k, v in enumerate(seg))

    def LX(i: int) -> float:
        # Marker labels stay inside the plot even at its edges.
        return min(max(X(i), L + 14.0), W - R - 14.0)
    fill_pts = " ".join(f"L{_coord(X(i))},{_coord(Y(pts[i]))}" for i in range(pi, ti + 1))
    parts = [
        '<defs><linearGradient id="epFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d04a3c" stop-opacity=".14"/>'
        '<stop offset="1" stop-color="#d04a3c" stop-opacity="0"/></linearGradient></defs>',
        f'<line class="ep-peakline" x1="{_coord(L)}" y1="{_coord(Y(pts[pi]))}" x2="{_coord(W - R)}" y2="{_coord(Y(pts[pi]))}"/>',
        f'<path class="ep-fill" d="M{_coord(X(pi))},{_coord(Y(pts[pi]))} {fill_pts} L{_coord(X(ti))},{_coord(Y(pts[pi]))} Z"/>',
        f'<path class="ep-line" d="{d}"/>',
        '<path class="ep-line ep-line-dd" d="'
        + " ".join(f"{'M' if k == 0 else 'L'}{_coord(X(i))},{_coord(Y(pts[i]))}" for k, i in enumerate(range(pi, ti + 1)))
        + '"/>',
        f'<circle class="ep-mk ep-mk-peak" cx="{_coord(X(pi))}" cy="{_coord(Y(pts[pi]))}" r="4"/>',
        f'<text class="ep-lbl ep-lbl-peak" x="{_coord(LX(pi))}" y="{_coord(Y(pts[pi]) - 10)}" text-anchor="middle">#{pi}</text>',
        f'<circle class="ep-mk ep-mk-trough" cx="{_coord(X(ti))}" cy="{_coord(Y(pts[ti]))}" r="4"/>',
        f'<text class="ep-lbl ep-lbl-trough" x="{_coord(LX(ti))}" y="{_coord(Y(pts[ti]) + 18)}" text-anchor="middle">#{ti}</text>',
        f'<text class="ep-axis" x="{_coord(L)}" y="{_coord(H - 4)}">#{a}</text>',
        f'<text class="ep-axis" x="{_coord(W - R)}" y="{_coord(H - 4)}" text-anchor="end">#{b}</text>',
    ]
    if back is not None:
        parts.append(f'<circle class="ep-mk ep-mk-back" cx="{_coord(X(back))}" cy="{_coord(Y(pts[back]))}" r="4"/>')
        parts.append(f'<text class="ep-lbl ep-lbl-back" x="{_coord(LX(back))}" y="{_coord(Y(pts[back]) - 10)}" text-anchor="middle">#{back}</text>')
    return f'<svg class="ep-svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Deepest drawdown episode">{"".join(parts)}</svg>'


def _pf_underwater(result: Dict[str, Any], capital: Optional[float]) -> str:
    """Portfolio only: how far the merged book and each member sit below
    their own running peak, trade by trade, all as % of the combined
    reference capital so every line is on one ruler."""
    members, lines = _pf_member_series(result)
    pnls = _extract_trade_pnls(result) or []
    if not members or not pnls or not (_is_finite_number(capital) and capital and capital > 0):
        return ""
    cap = float(capital)

    cum, run = [], 0.0
    for v in pnls:
        run += v
        cum.append(run)
    # The standard drawdown the rest of the section uses (loss_analysis
    # `_deepest_episode`): fall below the running peak / peak equity, with
    # equity = reference capital + cumulative PnL. Each member's fall is on
    # that SAME denominator at every trade, so the lines share one ruler.
    denom, peak = [], 0.0
    for v in cum:
        peak = max(peak, v)
        denom.append(max(cap + peak, 1e-9))

    def under(values: Sequence[float]) -> List[float]:
        out, top = [], 0.0
        for k, v in enumerate(values):
            top = max(top, v)
            out.append((v - top) / denom[k] * 100.0)
        return out

    comb = under(cum)
    mem = [under(line) for line in lines]
    n = len(comb)
    if n < 2 or any(len(m) != n for m in mem):
        return ""
    W, H, L, R, T, B = 820.0, 210.0, 52.0, 12.0, 14.0, 28.0
    low = min(min(comb), min(min(m) for m in mem))
    step = _nice_step(abs(low) or 1.0, 4)
    lo = -math.ceil(abs(low) / step) * step or -step

    def X(k: int) -> float:
        return L + (W - L - R) * k / (n - 1)

    def Y(v: float) -> float:
        return T + (H - T - B) * (0.0 - v) / (0.0 - lo)

    def path(vals: Sequence[float]) -> str:
        return " ".join(f"{'M' if k == 0 else 'L'}{_coord(X(k))},{_coord(Y(v))}" for k, v in enumerate(vals))

    parts = []
    v = 0.0
    while v >= lo - 1e-9:
        parts.append(f'<line class="{"uw-zero" if v == 0 else "uw-grid"}" x1="{_coord(L)}" x2="{_coord(W - R)}" y1="{_coord(Y(v))}" y2="{_coord(Y(v))}"/>')
        parts.append(f'<text class="uw-tick" x="{_coord(L - 8)}" y="{_coord(Y(v) + 3.5)}" text-anchor="end">{v:.0f}%</text>')
        v -= step
    parts.append(f'<path class="uw-area" d="{path(comb)} L{_coord(X(n - 1))},{_coord(Y(0))} L{_coord(X(0))},{_coord(Y(0))} Z"/>')
    for m, line in zip(members, mem):
        parts.append(f'<path class="uw-member" stroke="{_esc(m.get("colour"))}" d="{path(line)}"/>')
    parts.append(f'<path class="uw-line" d="{path(comb)}"/>')
    k = comb.index(min(comb))
    parts.append(f'<circle class="uw-mk" cx="{_coord(X(k))}" cy="{_coord(Y(comb[k]))}" r="4"/>')
    anchor, lx = ("start", X(k) + 8) if X(k) < W - 160 else ("end", X(k) - 8)
    parts.append(f'<text class="uw-lbl" x="{_coord(lx)}" y="{_coord(Y(comb[k]) + 4)}" text-anchor="{anchor}">{comb[k]:.1f}% · #{k + 1}</text>')
    parts.append(f'<text class="uw-tick" x="{_coord(L)}" y="{_coord(H - 8)}">Trade #1</text>')
    parts.append(f'<text class="uw-tick" x="{_coord(W - R)}" y="{_coord(H - 8)}" text-anchor="end">#{n} (merged book)</text>')
    below = sum(1 for line in mem if line[k] < -1e-9)
    hidden = [m for m in _pf_members(result) if m.get("ledger_hidden")]
    legend = _pf_line_legend(members, f"Combined {min(comb):.1f}%", "--down", [f"{min(line):.1f}%" for line in mem])
    if hidden:
        legend = legend[:-len("</div>")] + (
            f'<span class="gc-mlegend-off"><i style="background:var(--muted)"></i>{len(hidden)} concealed · daily PnL only, not drawn</span></div>'
        )
    chip_tone = "bad" if below == len(members) else ("warn" if below else "good")
    return (
        '<div class="uw-block"><div class="gc-head">'
        '<span class="st-label" title="How far each bot&#39;s own realised PnL sits below its own running peak, as a share of '
        'the combined book&#39;s peak equity so every bot is on one ruler. The combined line is the merged book; a bot&#39;s '
        'drawdown on its own capital is in Contribution by bot.">Drawdown from peak · combined &amp; by bot</span>'
        f'<span class="st-chip st-chip-{chip_tone}">{below} of {len(members)} bots below peak at #{k + 1}</span></div>'
        f'<svg class="uw-svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Drawdown from peak, combined and by bot">{"".join(parts)}</svg>'
        f"{legend}</div>"
    )


def _render_drawdown_vs_capital(result: Dict[str, Any]) -> str:
    """Drawdown vs. capital -- all numbers from `loss_analysis.compute_loss_profile`
    (the same deepest-episode rule as the header strip); laid out like the
    redesign preview: four loss tiles, the deepest episode drawn with its
    peak / trough / back-at-peak, and the five worst losing trades."""
    profile = compute_loss_profile(result.get("evidence"))
    if not profile:
        return ""
    capital = profile.get("capital")
    has_capital = _is_finite_number(capital)
    worst = profile.get("worst_trade")
    episode = profile.get("deepest_episode")
    streak = profile.get("worst_losing_streak")
    gross = profile.get("gross_loss") or {}

    def main_val(pct: Any, amount: Any, cap_at_100: bool = False) -> str:
        if has_capital and _is_finite_number(pct):
            # A drawdown past 100% of the capital means the account was
            # wiped out; the USDT amount stays in the sub-line.
            if cap_at_100 and float(pct) >= 99.95:
                return "100% · wiped out"
            return _pct(pct, 1)
        return _money(amount)

    def date(ms: Any) -> str:
        return datetime.fromtimestamp(float(ms) / 1000, tz=_VN_TZ).strftime("%d/%m") if _is_finite_number(ms) else ""

    # Trade number (#1 = first closed trade) in the same close-time order
    # loss_analysis.py uses.
    ordered = sorted(
        (x for x in ((result.get("evidence") or {}).get("closed_trade_series") or [])
         if isinstance(x, dict) and _is_finite_number(x.get("close_time")) and _is_finite_number(x.get("realized_pnl"))),
        key=lambda x: float(x["close_time"]),
    )

    def trade_no(ms: Any, pnl: Any) -> str:
        if not (_is_finite_number(ms) and _is_finite_number(pnl)):
            return ""
        for i, x in enumerate(ordered, 1):
            if float(x["close_time"]) == float(ms) and abs(float(x["realized_pnl"]) - float(pnl)) < 1e-6:
                return f"#{i}"
        return ""

    tiles = []
    if worst:
        tiles.append(("Largest losing trade", main_val(worst.get("pct_of_capital"), worst.get("pnl")),
                      " · ".join(x for x in (_money(worst.get("pnl")), trade_no(worst.get("close_time"), worst.get("pnl"))) if x)))
    else:
        tiles.append(("Largest losing trade", "No losing trades yet", ""))
    if episode:
        tiles.append(("Max drawdown period", main_val(episode.get("depth_pct"), -float(episode.get("depth_abs", 0.0)), True),
                      f"{_money(-float(episode.get('depth_abs', 0.0)))} · {_int_text(episode.get('trade_count'))} trades"))
    else:
        tiles.append(("Max drawdown period", "No drawdown yet", ""))
    if streak:
        tiles.append(("Max consecutive loss", main_val(streak.get("pct_of_capital"), streak.get("total_loss"), True),
                      f"{_money(streak.get('total_loss'))} · {_int_text(streak.get('count'))} trades"))
    else:
        tiles.append(("Max consecutive loss", "No losing streak", ""))
    tiles.append(("Gross loss", main_val(gross.get("pct_of_capital"), gross.get("total")),
                  f"{_money(gross.get('total'))} · {_int_text(profile.get('losing_trade_count'))} trades"))
    tiles_html = "".join(
        f'<div class="pv-tile"><div class="pv-tile-l">{_esc(l)}</div><div class="pv-tile-v pv-v-bad">{_esc(v)}</div>'
        f'<div class="pv-tile-s">{_esc(s)}</div></div>'
        for l, v, s in tiles
    )
    chip = (
        f'% of reference capital · {float(capital):,.0f} USDT' if has_capital else "absolute USDT (no reference capital)"
    )
    body = (
        f'<div class="pv-head"><span class="mc-title" >Drawdown vs. capital</span><span class="mc-chip">{_esc(chip)}</span></div>'
        f'<div class="pv-tiles">{tiles_html}</div>'
    )
    if streak:
        body = body.replace(
            '<div class="pv-tile"><div class="pv-tile-l">Most costly losing streak</div>',
            '<div class="pv-tile" title="Selected by TOTAL MONEY LOST rather than trade count: a short streak that '
            'loses a lot is more dangerous than a long streak that loses little."><div class="pv-tile-l">Most costly losing streak</div>',
            1,
        )
    if not has_capital:
        body += _note_chip("No reference capital: shown in USDT", (
            '<div class="notice notice-warning">Could not infer reference capital from'
            " this bot's public capital curve, so every loss figure below is shown as"
            " an absolute amount -- NOT converted to a percentage of capital (no"
            " denominator means no percentage; this is missing data, not low risk).</div>"
        ))

    left = ""
    if episode:
        pnls = _extract_trade_pnls(result) or []
        idx = _episode_indices(pnls, _ref_capital(result)) if pnls else None
        chart = _episode_svg(pnls, idx) if idx else ""
        rec = episode.get("recovered")
        dur = episode.get("duration_hours")
        mini = [
            ("Peak", f"{float(episode.get('peak_cum', 0.0)):+,.0f}", "good"),
            ("Trough", f"{float(episode.get('trough_cum', 0.0)):+,.0f}", "bad"),
            ("Depth", f"{-float(episode.get('depth_abs', 0.0)):+,.0f}", "bad"),
            ("Trades", _int_text(episode.get("trade_count")), ""),
            ("Duration", f"{_num(dur, 1)} h" if _is_finite_number(dur) else "—", ""),
            ("Recovered at", (f"#{idx[2]}" if idx and idx[2] is not None else "Yes") if rec else "Not yet", "good" if rec else "bad"),
        ]
        mini_html = "".join(
            f'<div class="pv-mini"><span>{_esc(k)}</span><b class="pv-v-{t}">{_esc(v)}</b></div>' for k, v, t in mini
        )
        left = (
            '<div class="pv-box"><div class="gc-head"><span class="st-label">Max drawdown period</span>'
            f'<span class="st-chip {"st-chip-good" if rec else "st-chip-bad"}">{"Recovered" if rec else "Not recovered"}</span></div>'
            f'{chart}<div class="pv-minis">{mini_html}</div></div>'
        )
    right = ""
    worst_list = profile.get("worst_trades") or []
    pairs = _pair_lookup(result)
    owner_of = _series_owner_lookup(result)
    if worst_list:
        biggest = max((abs(float(w.get("pnl") or 0.0)) for w in worst_list), default=1.0) or 1.0
        rows = []
        for w in worst_list:
            pnl = float(w.get("pnl") or 0.0)
            pct = w.get("pct_of_capital")
            rows.append(
                f'<div class="pv-worst"><div class="pv-worst-l"><b>{_esc(" · ".join(x for x in (date(w.get("close_time")), trade_no(w.get("close_time"), w.get("pnl"))) if x) or "—")}</b>'
                f'<span>{_esc(" · ".join(x for x in ((owner_of.get((int(float(w.get("close_time") or 0)), round(pnl, 4))) or {}).get("short", ""), pairs.get((int(float(w.get("close_time") or 0)), round(pnl, 4)), ""), (_pct(pct, 1) + " of capital") if _is_finite_number(pct) else "") if x))}</span></div>'
                f'<span class="pv-worst-bar"><span style="width:{abs(pnl) / biggest * 100:.0f}%"></span></span>'
                f'<b class="pv-worst-v">{pnl:+,.0f}</b></div>'
            )
        right = (
            '<div class="pv-box"><div class="gc-head"><span class="st-label">Largest losing trades</span>'
            '<span class="gc-note">USDT</span></div>' + "".join(rows) + "</div>"
        )
    if left or right:
        body += f'<div class="pv-2col">{left}{right}</div>'
    body += _pf_underwater(result, capital)
    return _section("Drawdown vs. capital", body, anchor="sut-giam-von")






_ASSET_DOT = ("#f7931a", "#627eea", "#9945ff", "#7c8597", "#c2a633", "#2775ca", "#e84142", "#26a17b")


def _asset_colors(result: Dict[str, Any]) -> Dict[str, str]:
    """Base symbol -> dot colour, ranked by exposure share exactly like the
    Market tab, so a pair keeps one colour across the report."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    share = evidence.get("symbol_exposure_share") if isinstance(evidence.get("symbol_exposure_share"), dict) else {}
    order = [k for k, _ in sorted(((str(k), float(v)) for k, v in share.items() if _is_finite_number(v)), key=lambda x: -x[1])]
    for a in result.get("assets") or []:
        if isinstance(a, dict) and a.get("asset") and str(a["asset"]) not in order:
            order.append(str(a["asset"]))
    return {k: _ASSET_DOT[i % len(_ASSET_DOT)] for i, k in enumerate(order)}


def _inst_names(result: Dict[str, Any]) -> Dict[str, str]:
    """Base symbol -> traded pair name ("BTC" -> "BTC-USDT") from the stored ledger."""
    out: Dict[str, str] = {}
    for r in result.get("_ledger") or []:
        if isinstance(r, dict) and r.get("pair") and r.get("inst"):
            out.setdefault(str(r["pair"]), str(r["inst"]))
    return out


def _pf_members(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A portfolio's members with their page colour and short label
    (`portfolio_section.member_palette`), or [] for a single bot."""
    portfolio = result.get("portfolio")
    if not isinstance(portfolio, dict) or not portfolio.get("members"):
        return []
    return member_palette(portfolio)


def _owner_index(result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Merged-ledger owner prefix (first 8 of the member code, see
    `PortfolioAggregator._merge_trades`) -> member."""
    return {str(m.get("unique_code") or "")[:8]: m for m in _pf_members(result) if m.get("unique_code")}


def _ledger_from_series(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`_ledger`-shaped rows from `closed_trade_series` when its rows carry
    their instrument -- what a merged book (whose ledger is on no single
    file) and any fresh result use instead of the (time, PnL) join against
    `trade_list.json`."""
    out: List[Dict[str, Any]] = []
    for row in (result.get("evidence") or {}).get("closed_trade_series") or []:
        if not (isinstance(row, dict) and row.get("symbol") and _is_finite_number(row.get("close_time"))
                and _is_finite_number(row.get("realized_pnl"))):
            continue
        out.append({"close_ms": float(row["close_time"]), "open_ms": None, "pnl": float(row["realized_pnl"]),
                    "pair": str(row["symbol"]), "inst": row.get("inst")})
    return out


def _series_owner_lookup(result: Dict[str, Any]) -> Dict[Tuple[int, float], Dict[str, Any]]:
    """(close ms, pnl) -> member, for rows the merged series tags with an owner."""
    owners = _owner_index(result)
    if not owners:
        return {}
    out: Dict[Tuple[int, float], Dict[str, Any]] = {}
    for row in (result.get("evidence") or {}).get("closed_trade_series") or []:
        if isinstance(row, dict) and row.get("owner") in owners and _is_finite_number(row.get("close_time")) \
                and _is_finite_number(row.get("realized_pnl")):
            out[(int(float(row["close_time"])), round(float(row["realized_pnl"]), 4))] = owners[row["owner"]]
    return out


_LG_PER = 10


def _lg_pager_html(page: int, pages: int) -> str:
    """Pager buttons -- the same rule as the runtime script's `render`
    (first, last and the pages next to the current one)."""
    out = [f'<button type="button" class="lg-pg" data-p="{page - 1}"{" disabled" if page <= 0 else ""}>‹</button>']
    for p in range(pages):
        if p in (0, pages - 1) or abs(p - page) <= 1:
            out.append(f'<button type="button" class="lg-pg{" on" if p == page else ""}" data-p="{p}">{p + 1}</button>')
        elif abs(p - page) == 2:
            out.append('<span class="lg-gap">…</span>')
    out.append(f'<button type="button" class="lg-pg" data-p="{page + 1}"{" disabled" if page >= pages - 1 else ""}>›</button>')
    return "".join(out)


def _lg_box(box: str, unit: str, head: str, rows: Sequence[str], total: int, wrap: str = "lg-scroll") -> str:
    """A paged list (10 per page, client-side): the header row, the rows
    (the first page visible, the rest `hidden`) and a footer with the range
    and the pager. The runtime script re-pages on filter and pager clicks;
    `data-box` ties a card's filter buttons to their own list."""
    pages = max(1, (total + _LG_PER - 1) // _LG_PER)
    foot = (
        f'<div class="lg-foot"><span class="pv-num lg-info">1–{min(_LG_PER, total)} of {total:,} {unit}</span>'
        + (f'<span class="lg-pager">{_lg_pager_html(0, pages)}</span>' if pages > 1 else "")
        + "</div>"
    )
    return (
        f'<div class="lg-box" data-box="{box}" data-unit="{unit}" data-f="a" data-b="all" data-p="0">'
        f'<div class="{wrap}">{head}<div class="lg-body">{"".join(rows)}</div></div>{foot}</div>'
    )


def _render_assets(result: Dict[str, Any]) -> str:
    assets = [a for a in (result.get("assets") or []) if isinstance(a, dict)]
    if not assets:
        return ""
    assets.sort(key=lambda a: -float(a.get("closed_seen") or 0))
    top = max((float(a.get("closed_seen") or 0) for a in assets), default=1.0) or 1.0
    colors, names = _asset_colors(result), _inst_names(result)
    # Portfolio: which member(s) trade each pair (`symbol_breakdown.members`
    # holds member labels).
    by_label = {m["label"]: m for m in _pf_members(result)}
    owners: Dict[str, List[Dict[str, Any]]] = {}
    for row in ((result.get("portfolio") or {}).get("symbol_breakdown") or []) if by_label else []:
        if isinstance(row, dict) and row.get("symbol"):
            owners[str(row["symbol"])] = [by_label[l] for l in (row.get("members") or []) if l in by_label]
    rows = []
    for i, a in enumerate(assets):
        sym = str(a.get("asset") or "—")
        state = str(a.get("state") or "—")
        tone = {"TRADING": "good", "HOLDING ONLY": "warn", "EXITED": "flat"}.get(state, "flat")
        closed = float(a.get("closed_seen") or 0)
        last = a.get("last_close_days")
        last_txt = f"{float(last):.1f} d ago" if _is_finite_number(last) else "never closed"
        stale = _is_finite_number(last) and float(last) > 7
        color = colors.get(sym, _ASSET_DOT[0])
        n_open = int(a.get("open_positions") or 0)
        own = owners.get(sym) or []
        own_html = (
            f'<span class="as-own" title="{_esc(", ".join(m["label"] for m in own))}">'
            f'{_esc(own[0]["short"])}{f" +{len(own) - 1}" if len(own) > 1 else ""}</span>'
            if own else ""
        )
        rows.append(
            f'<div class="as-row" data-r="x"{" hidden" if i >= _LG_PER else ""}>'
            f'<span class="as-name"><i style="background:{color}"></i><b>{_esc(names.get(sym, sym))}</b>{own_html}</span>'
            f'<span><span class="st-chip st-chip-{tone} pv-state">{_esc(state.capitalize())}</span></span>'
            f'<span class="pv-num as-r{"" if n_open else " pv-muted"}">{_int_text(a.get("open_positions"))}</span>'
            f'<span class="as-closed"><span class="as-track"><span style="width:{closed / top * 100:.0f}%"></span></span>'
            f'<b class="pv-num">{_int_text(a.get("closed_seen"))}</b></span>'
            f'<span class="pv-num as-r{" pv-stale" if stale else " as-last"}">{_esc(last_txt)}</span>'
            "</div>"
        )
    head = ('<div class="as-row as-head"><span>Asset</span><span>Status</span><span class="as-r">Open</span>'
            '<span>Closed trades</span><span class="as-r">Last closed</span></div>')
    return _section("Traded assets", _lg_box("assets", "pairs", head, rows, len(rows), wrap="as-list"), anchor="tai-san")


def _ledger_rows(result: Dict[str, Any]) -> List[Tuple[int, Any, float, float, str, str]]:
    """(trade #, close ms, pnl, cumulative pnl, base symbol, owner prefix),
    newest first. Symbol and owner are "" when the series does not carry
    them (older records)."""
    series = (result.get("evidence") or {}).get("closed_trade_series")
    if not isinstance(series, list):
        return []
    running, out = 0.0, []
    items = [x for x in series if isinstance(x, dict)]
    for n, item in enumerate(items, 1):
        pnl = float(item["realized_pnl"]) if _is_finite_number(item.get("realized_pnl")) else 0.0
        running += pnl
        out.append((n, item.get("close_time"), pnl, running, str(item.get("symbol") or ""), str(item.get("owner") or "")))
    return list(reversed(out))


_LG_TONE = {"w": ("win", "good", "good", "Win"), "l": ("loss", "bad", "bad", "Loss"), "e": ("even", "", "flat", "Even")}


def _lg_row_html(idx: int, when: str, pnl_s: str, cum_s: str, tone: str, cum_tone: str,
                 pair_html: str, owner: str, bar_w: int) -> str:
    """One ledger row. The runtime script's `lgRow` builds the very same
    markup from the row's data -- keep the two in step."""
    word, pnl_cls, chip, label = _LG_TONE[tone]
    return (
        f'<div class="lg-row" data-r="{tone}" data-b="{_esc(owner or "all")}">'
        f'<span class="pv-num pv-muted">#{idx}</span>{pair_html}'
        f'<span class="pv-num lg-t">{_esc(when)}</span>'
        f'<span class="lg-pl"><span class="lg-pl-bar lg-pl-{word}" style="width:{bar_w}px"></span>'
        f'<b class="pv-num pv-v-{pnl_cls}">{_esc(pnl_s)}</b></span>'
        f'<span class="pv-num as-r lg-cum pv-v-{cum_tone}">{_esc(cum_s)}</span>'
        f'<span class="as-r"><span class="st-chip st-chip-{chip} pv-state">{label}</span></span>'
        "</div>"
    )


def _render_closed_trades_table(result: Dict[str, Any]) -> str:
    """Closed-trades ledger. Only the first page is markup; every row (all
    pages, every filter) travels as compact JSON beside it and the runtime
    script builds the page being viewed from it. A 1,200-trade book used to
    put 1,200 rows (~15,000 elements) into the page to show ten."""
    recent = _ledger_rows(result)
    if not recent:
        return ""
    pairs, colors, names = _pair_lookup(result), _asset_colors(result), _inst_names(result)
    owners = _owner_index(result)
    # Bar length vs. the 95th-percentile trade size (longer trades clip at
    # full width), so one outlier does not flatten every other bar.
    sizes = sorted(abs(r[2]) for r in recent)
    biggest = sizes[min(len(sizes) - 1, int(len(sizes) * 0.95))] or max(sizes) or 1.0
    cells: List[str] = []
    cell_index: Dict[str, int] = {}
    data_rows: List[List[Any]] = []
    first_page: List[str] = []
    for i, (idx, ct, pnl, run, sym, owner) in enumerate(recent):
        tone = "w" if pnl > 0 else ("l" if pnl < 0 else "e")
        cum_tone = "good" if run > 0 else ("bad" if run < 0 else "")
        if not sym and _is_finite_number(ct):
            sym = pairs.get((int(float(ct)), round(pnl, 4)), "")
        when = datetime.fromtimestamp(float(ct) / 1000, tz=_VN_TZ).strftime("%d/%m %H:%M") if _is_finite_number(ct) else "—"
        member = owners.get(owner) if owner else None
        if member:
            pair_html = (f'<span class="as-name" title="{_esc(member["label"])}"><i style="background:{member["colour"]}"></i>'
                         f'<b>{_esc(member["short"])}</b><span class="lg-inst">{_esc(names.get(sym, sym))}</span></span>')
        elif sym:
            pair_html = f'<span class="as-name"><i style="background:{colors.get(sym, _ASSET_DOT[0])}"></i><b>{_esc(names.get(sym, sym))}</b></span>'
        else:
            pair_html = '<span class="pv-muted">—</span>'
        if pair_html not in cell_index:
            cell_index[pair_html] = len(cells)
            cells.append(pair_html)
        bar_w = int(f"{max(4.0, min(1.0, abs(pnl) / biggest) * 80):.0f}")
        pnl_s, cum_s = f"{pnl:+,.2f}", f"{run:+,.2f}"
        data_rows.append([idx, when, pnl_s, cum_s, tone, cum_tone, cell_index[pair_html], owner or "", bar_w])
        if i < _LG_PER:
            first_page.append(_lg_row_html(idx, when, pnl_s, cum_s, tone, cum_tone, pair_html, owner, bar_w))
    col = "Bot · pair" if owners and any(r[5] for r in recent) else "Pair"
    head = (f'<div class="lg-row lg-head"><span>#</span><span>{col}</span><span>Close time</span>'
            '<span class="as-r">Profit / loss (USDT)</span><span class="as-r">Cumulative PnL</span><span class="as-r">Result</span></div>')
    payload = json.dumps({"k": cells, "r": data_rows}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    box = _lg_box("ledger", "trades", head, first_page, len(recent))
    box = box.replace('<div class="lg-box"', '<div class="lg-box lg-box-data"', 1)
    box = box[: -len("</div>")] + f'<script type="application/json" class="lg-data">{payload}</script></div>'
    if col != "Pair":
        box = box.replace('class="lg-box lg-box-data"', 'class="lg-box lg-box-data lg-box-pf"', 1)
    return _section("Most recent closed trades", box, anchor="danh-sach-lenh")


def _ledger_filter_html(result: Dict[str, Any]) -> str:
    recent = _ledger_rows(result)
    if not recent:
        return ""
    wins = sum(1 for r in recent if r[2] > 0)
    losses = sum(1 for r in recent if r[2] < 0)
    bots = ""
    owners = _owner_index(result)
    present = {r[5] for r in recent if r[5]}
    if owners and present:
        bots = (
            '<div class="mk-ftabs lg-filter lg-bots" data-box="ledger">'
            '<button type="button" class="mk-ftab lg-b on" data-b="all">All bots</button>'
            + "".join(
                f'<button type="button" class="mk-ftab lg-b" data-b="{_esc(p)}" title="{_esc(m["label"])}">'
                f'<i style="background:{m["colour"]}"></i>{_esc(m["short"])}</button>'
                for p, m in owners.items() if p in present
            )
            + "</div>"
        )
    return (
        bots
        + '<div class="mk-ftabs lg-filter" data-box="ledger">'
        f'<button type="button" class="mk-ftab lg-f on" data-f="a">All<span>{len(recent):,}</span></button>'
        f'<button type="button" class="mk-ftab lg-f" data-f="w">Win<span>{wins:,}</span></button>'
        f'<button type="button" class="mk-ftab lg-f" data-f="l">Loss<span>{losses:,}</span></button></div>'
    )


def _cb_svg(members: Sequence[Dict[str, Any]], curves: Dict[str, List[Tuple[int, float]]], total: int,
            window: Optional[Tuple[int, int]]) -> str:
    """Cumulative realised PnL of each member along the merged book's trade
    order (x = merged trade #), the portfolio's deepest drawdown shaded."""
    W, H, L, R, T, B = 1200.0, 260.0, 60.0, 14.0, 16.0, 28.0
    values = [v for pts in curves.values() for _, v in pts] + [0.0]
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        hi = lo + 1.0
    pad = (hi - lo) * 0.08
    lo, hi = lo - pad, hi + pad

    def X(i: float) -> float:
        return L + (W - L - R) * (i / max(1, total))

    def Y(v: float) -> float:
        return T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    parts = []
    if window:
        a, b = window
        parts.append(f'<rect class="cb-win" x="{X(a):.1f}" y="{T:.1f}" width="{max(2.0, X(b) - X(a)):.1f}" height="{H - T - B:.1f}" rx="4"/>')
        mid = (X(a) + X(b)) / 2
        # Near an edge the label hangs inwards from the band, so it is never clipped.
        anchor, lx = ("end", X(b)) if mid > W * 0.8 else (("start", X(a)) if mid < W * 0.2 else ("middle", mid))
        parts.append(f'<text class="cb-win-l" x="{lx:.1f}" y="{T + 11:.1f}" text-anchor="{anchor}">deepest DD #{a + 1}–{b}</text>')
    step = _nice_axis_step(hi - lo)
    k = math.ceil(lo / step) * step
    while k <= hi:
        parts.append(f'<line class="cb-grid" x1="{L}" x2="{W - R}" y1="{Y(k):.1f}" y2="{Y(k):.1f}"/>')
        parts.append(f'<text class="cb-tick" x="{L - 6}" y="{Y(k) + 3.5:.1f}" text-anchor="end">{k / 1000:+,.0f}k</text>')
        k += step
    for m in members:
        pts = curves.get(m["prefix"]) or []
        if not pts:
            continue
        d = f"M{X(0):.1f},{Y(0):.1f}"
        prev = 0.0
        for i, v in pts:
            d += f" L{X(i):.1f},{Y(prev):.1f} L{X(i):.1f},{Y(v):.1f}"
            prev = v
        d += f" L{X(total):.1f},{Y(prev):.1f}"
        parts.append(f'<path class="cb-line" d="{d}" style="stroke:{m["colour"]}"/>')
        parts.append(f'<circle cx="{X(total):.1f}" cy="{Y(prev):.1f}" r="3.5" style="fill:{m["colour"]}"/>')
    parts.append(f'<text class="cb-tick" x="{L}" y="{H - 6}">Trade #1</text>')
    parts.append(f'<text class="cb-tick" x="{W - R}" y="{H - 6}" text-anchor="end">#{total} (merged book)</text>')
    return f'<svg class="cb-svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Cumulative realised PnL by bot">{"".join(parts)}</svg>'


def _nice_axis_step(span: float) -> float:
    raw = span / 4.0 if span > 0 else 1.0
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if m * mag >= raw:
            return m * mag
    return 10 * mag


def _render_contribution(result: Dict[str, Any]) -> str:
    """Contribution by bot (portfolio page only): the merged ledger split back
    by member -- trades, win rate, PF, realised PnL and its share, each bot's
    own max drawdown on its own capital, its PnL inside the portfolio's
    deepest drawdown, and its open book. Needs the owner tag on each row of
    the merged series; an older record without it shows nothing rather than
    a guess."""
    members = _pf_members(result)
    if not members:
        return ""
    series = [x for x in ((result.get("evidence") or {}).get("closed_trade_series") or [])
              if isinstance(x, dict) and _is_finite_number(x.get("realized_pnl"))]
    if not series or not any(x.get("owner") for x in series):
        return ""
    ledger_members = [dict(m, prefix=str(m.get("unique_code") or "")[:8]) for m in members if not m.get("ledger_hidden")]
    hidden = [m for m in members if m.get("ledger_hidden")]
    pnls = [float(x["realized_pnl"]) for x in series]
    idx = _episode_indices(pnls, _ref_capital(result))
    window = (idx[0], idx[1]) if idx else None
    stats: Dict[str, Dict[str, Any]] = {m["prefix"]: {"n": 0, "w": 0, "gp": 0.0, "gl": 0.0, "cum": 0.0, "peak": 0.0,
                                                      "dd": 0.0, "inwin": 0.0, "pts": []} for m in ledger_members}
    for i, x in enumerate(series, 1):
        s = stats.get(str(x.get("owner") or ""))
        if s is None:
            continue
        p = float(x["realized_pnl"])
        s["n"] += 1
        s["w"] += p > 0
        s["gp"] += max(p, 0.0)
        s["gl"] += max(-p, 0.0)
        s["cum"] += p
        s["peak"] = max(s["peak"], s["cum"])
        s["dd"] = max(s["dd"], s["peak"] - s["cum"])
        if window and window[0] < i <= window[1]:
            s["inwin"] += p
        s["pts"].append((i, s["cum"]))
    gross = sum(abs(s["cum"]) for s in stats.values()) or 1.0
    top = max((abs(s["cum"]) for s in stats.values()), default=1.0) or 1.0
    win_label = f"In #{window[0] + 1}–{window[1]}" if window else "In deepest DD"

    def tone(v: float) -> str:
        return "good" if v > 0 else ("bad" if v < 0 else "")

    rows = []
    for m in ledger_members:
        s = stats[m["prefix"]]
        cap = m.get("ledger_capital") or (m.get("capital_at_risk") if m.get("capital_source") != "OKX_INVEST_AMT" else None)
        dd_txt = f"{s['dd'] / float(cap) * 100:.1f}%" if _is_finite_number(cap) and float(cap) > 0 else f"{-s['dd']:,.0f}"
        pf = s["gp"] / s["gl"] if s["gl"] > 0 else None
        opens, unreal = m.get("open_positions"), m.get("unrealized_pnl")
        open_txt = ("—" if not opens else
                    (f"{float(unreal):+,.0f} · {int(opens)}" if _is_finite_number(unreal) else f"— · {int(opens)}"))
        code = str(m.get("unique_code") or "")
        rows.append(
            f'<a class="cb-row pf-member-link" data-code="{_esc(code)}" href="/bot/{_esc(code)}">'
            f'<span class="as-name" title="{_esc(m["label"])}"><i style="background:{m["colour"]}"></i><b>{_esc(m["label"][:26])}</b>'
            f'<span class="lg-inst">{_esc(m.get("symbol") or "")}</span></span>'
            f'<span class="pv-num as-r" data-l="Trades">{s["n"]:,}</span>'
            f'<span class="pv-num as-r" data-l="Win">{(s["w"] / s["n"] * 100 if s["n"] else 0):.0f}%</span>'
            f'<span class="pv-num as-r" data-l="PF">{_num(pf, 2)}</span>'
            f'<span class="cb-share" data-l="Realised"><span class="as-track"><span style="width:{abs(s["cum"]) / top * 100:.0f}%;background:{m["colour"]}"></span></span>'
            f'<b class="pv-num pv-v-{tone(s["cum"])}">{s["cum"]:+,.0f}</b><span class="pv-num pv-muted">{abs(s["cum"]) / gross * 100:.0f}%</span></span>'
            f'<span class="pv-num as-r pv-v-bad" data-l="Max DD">{dd_txt}</span>'
            f'<span class="pv-num as-r pv-v-{tone(s["inwin"])}" data-l="{_esc(win_label)}">{s["inwin"]:+,.0f}</span>'
            f'<span class="pv-num as-r{" pv-v-bad" if _is_finite_number(unreal) and float(unreal) < 0 else ""}" data-l="Open · unreal.">{_esc(open_txt)}</span>'
            "</a>"
        )
    for m in hidden:
        rows.append(
            '<div class="cb-row cb-off">'
            f'<span class="as-name" title="{_esc(m["label"])}"><i style="background:{m["colour"]}"></i><b>{_esc(m["label"][:26])}</b></span>'
            '<span class="cb-off-note">order book hidden on OKX · not in the merged book (public daily PnL only)</span></div>'
        )
    # Merged-book total row.
    n = len(series)
    wins = sum(1 for p in pnls if p > 0)
    gp, gl = sum(p for p in pnls if p > 0), -sum(p for p in pnls if p < 0)
    total = sum(pnls)
    profile = compute_loss_profile(result.get("evidence")) or {}
    ep = profile.get("deepest_episode") or {}
    inwin_total = sum(p for i, p in enumerate(pnls, 1) if window and window[0] < i <= window[1])
    opens_all = [m.get("open_positions") for m in ledger_members]
    unreal_all = [m.get("unrealized_pnl") for m in ledger_members]
    open_total = sum(int(o or 0) for o in opens_all)
    unreal_total = sum(float(u) for u in unreal_all if _is_finite_number(u)) if all(_is_finite_number(u) for u in unreal_all) else None
    rows.append(
        '<div class="cb-row cb-total">'
        '<span class="as-name"><b>Merged book</b></span>'
        f'<span class="pv-num as-r" data-l="Trades">{n:,}</span>'
        f'<span class="pv-num as-r" data-l="Win">{wins / n * 100 if n else 0:.0f}%</span>'
        f'<span class="pv-num as-r" data-l="PF">{_num(gp / gl if gl > 0 else None, 2)}</span>'
        f'<span class="cb-share" data-l="Realised"><b class="pv-num pv-v-{tone(total)}">{total:+,.0f}</b></span>'
        f'<span class="pv-num as-r pv-v-bad" data-l="Max DD">{_pct(ep.get("depth_pct"), 1) if _is_finite_number(ep.get("depth_pct")) else "—"}</span>'
        f'<span class="pv-num as-r pv-v-{tone(inwin_total)}" data-l="{_esc(win_label)}">{inwin_total:+,.0f}</span>'
        f'<span class="pv-num as-r" data-l="Open · unreal.">{(f"{unreal_total:+,.0f} · " if unreal_total is not None else "") + str(open_total) if open_total else "—"}</span>'
        "</div>"
    )
    losers = [m for m in ledger_members if window and stats[m["prefix"]]["inwin"] < 0]
    lead = max(ledger_members, key=lambda m: abs(stats[m["prefix"]]["cum"]), default=None)
    chips = ""
    if window:
        chips += (f'<span class="st-chip st-chip-{"bad" if len(losers) == len(ledger_members) else "warn"}">'
                  f'{len(losers)} of {len(ledger_members)} bots lost in the deepest drawdown</span>')
    if lead:
        chips += (f'<span class="st-chip st-chip-flat">Largest share: {_esc(lead["short"])} '
                  f'{abs(stats[lead["prefix"]]["cum"]) / gross * 100:.0f}%</span>')
    legend = "".join(
        f'<span><i style="background:{m["colour"]}"></i>{_esc(m["label"][:26])}</span>' for m in ledger_members
    )
    head = ('<div class="cb-row cb-head"><span>Bot</span><span class="as-r">Trades</span><span class="as-r">Win</span>'
            '<span class="as-r">PF</span><span>Realised · share</span><span class="as-r">Max DD</span>'
            f'<span class="as-r">{_esc(win_label)}</span><span class="as-r">Open · unreal.</span></div>')
    tip = ("The merged ledger split back by member. Max DD is on each bot's own capital; "
           f"“{win_label}” is each bot's realised PnL inside the portfolio's deepest drawdown. "
           "Share = the bot's |realised PnL| over the sum across bots.")
    body = (
        f'<div class="pv-head"><span class="mc-title" >Contribution by bot<span class="info-ic">i<span class="info-tip">{_esc(tip)}</span></span></span>'
        f'<span class="cb-chips">{chips}</span></div>'
        f'<div class="cb-legend">{legend}<span class="cb-legend-r">Cumulative realised PnL, USDT</span></div>'
        + _cb_svg(ledger_members, {k: v["pts"] for k, v in stats.items()}, n, window)
        + f'<div class="cb-table">{head}{"".join(rows)}</div>'
    )
    return _section("Contribution by bot", body, anchor="dong-gop")


def _tab_group_card(groups: Sequence[Tuple[str, str, str, str]], extras: Optional[Dict[str, str]] = None, compact: bool = False) -> str:
    """Several sections behind one tab bar (preview's switchable cards).
    `groups` = (key, label, summary, html of one or more sections). Tab
    buttons only set `data-active` on the card; CSS shows the matching group.
    `extras` = per-group controls shown at the right of the tab bar while
    that group is active (compact tab bar)."""
    groups = [g for g in groups if g[3]]
    if not groups:
        return ""
    if len(groups) == 1:
        return f'<div class="pv-group pv-group-solo">{groups[0][3]}</div>'
    tabs = "".join(
        f'<button type="button" class="dd-tab" data-pane="{k}" role="tab" '
        f"onclick=\"this.closest('.dd-card').setAttribute('data-active','{k}')\">"
        f'<span class="dd-tab-l">{_esc(l)}</span><span class="dd-tab-v">{_esc(s)}</span></button>'
        for k, l, s, _ in groups
    )
    bar = f'<div class="dd-tabbar pv-tabbar" role="tablist">{tabs}</div>'
    if compact or extras:
        bar = (f'<div class="pv-tabhead">{bar}'
               + "".join(f'<div class="pv-extra" data-for="{k}">{h}</div>' for k, h in (extras or {}).items() if h)
               + "</div>")
    panes = "".join(f'<div class="pv-group" data-group="{k}">{h}</div>' for k, _, _, h in groups)
    return f'<div class="dd-card pv-card{" pv-card-compact" if compact else ""}" data-active="{groups[0][0]}">{bar}{panes}</div>'


# --------------------------------------------------------------------------- #
# The short answer (top of the page) and the one-line answer of each tab.
#
# Plain words for a reader who is not a quant, built by fixed rules from
# figures the page already shows -- never a new calculation, never free
# text. The full evidence stays where it was, below.
# --------------------------------------------------------------------------- #

# An assessment of the record, never advice to copy or not.
# Row headers of the WHY list that describe the score, not a finding.
_SA_NOT_A_FINDING = frozenset({"Score is the average across dimensions", "Main risk drivers"})
_SA_LEAD = {ZONE_DANGER: "High risk", ZONE_WARNING: "Elevated risk", ZONE_NORMAL: "Risk within normal range"}


def _sentence(text: str) -> str:
    """"Losing money per trade" -> "losing money per trade" (acronyms kept)."""
    text = str(text or "").strip().rstrip(".")
    if len(text) > 1 and text[0].isupper() and not text[1].isupper():
        return text[0].lower() + text[1:]
    return text


def _one_in_text(p: Optional[float]) -> str:
    """9.8 -> "1 in 10", 51 -> "5 in 10" (the Monte Carlo cards' own wording)."""
    return _mc_one_in(p).replace("≈ ", "") if p is not None and p > 0 else ""


def _portfolio_reason(result: Dict[str, Any]) -> Tuple[Optional[str], Optional[float], str]:
    """(what the diversification findings say in a few words, share of the
    capital the headline score covers, that share in words) -- (None, None,
    "") for a single bot."""
    pf = result.get("portfolio")
    if not isinstance(pf, dict) or not pf:
        return None, None, ""
    cov = pf.get("score_coverage_pct")
    if not _is_finite_number(cov):
        cov = pf.get("measurement_coverage_pct")
    cov = float(cov) if _is_finite_number(cov) else None
    cov_text = f"{cov:.0f}% of capital" if cov is not None else ""
    if cov is None:
        # Older records carry no coverage figure: fall back to headcount,
        # the same fallback the portfolio layer uses.
        members = [m for m in (pf.get("members") or []) if isinstance(m, dict)]
        scored = sum(1 for m in members if not m.get("ledger_hidden"))
        in_book = {str(m.get("unique_code")) for m in members}
        missing = {str(c) for c in (pf.get("concealed_member_codes") or [])}
        missing |= {str(f.get("bot_folder_name") or "").removeprefix("bot_")
                    for f in (result.get("failures") or []) if isinstance(f, dict)}
        absent = len({c for c in missing if c and c not in in_book})
        total = len(members) + absent
        if total and scored < total:
            cov = 100.0 * scored / total
            cov_text = f"{scored} of {total} bots"
    verdict, style = str(pf.get("verdict") or ""), str(pf.get("style_verdict") or "")
    if pf.get("style_vs_pnl_conflict") or style == "SAME_PLAYBOOK":
        reason = "the bots trade the same way"
    elif verdict == "HIGH_CORRELATION_CLUSTER":
        reason = "the bots move together"
    elif verdict == "MODERATE_CO_MOVEMENT":
        reason = "the bots partly move together"
    elif verdict == "DIVERSIFIED" and style in ("DISTINCT_PLAYBOOKS", "PARTIAL_OVERLAP"):
        reason = "the bots spread the risk"
    else:
        reason = None
    return reason, cov, cov_text


def _positive_pf_reason(reason: Optional[str]) -> Optional[str]:
    """The one portfolio reason that is good news (no "but")."""
    return reason if reason == "the bots spread the risk" else None


def _render_short_answer(result: Dict[str, Any]) -> str:
    """One headline, two or three figures, the verdict as a small line."""
    headline_verdict, zone = _verdict_headline_and_tone(result)
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    mc = result.get("mc") if isinstance(result.get("mc"), dict) else {}
    pf_reason, cov, cov_text = _portfolio_reason(result)

    trades = perf.get("trade_count") if _is_finite_number(perf.get("trade_count")) else result.get("trade_count")
    no_trades = not (_is_finite_number(trades) and float(trades) > 0)
    if result.get("status") == "LIMITED" or no_trades:
        lead, zone = "Not enough data to assess", ZONE_WARNING
        reason = ("the order book is hidden" if result.get("status") == "LIMITED" or result.get("limited_reason")
                  else "no closed trades to measure")
    elif cov is not None and cov < 50:
        lead, reason, zone = "Not enough data to assess", f"the score covers only {cov_text}", ZONE_WARNING
    else:
        lead = _SA_LEAD.get(zone, _SA_LEAD[ZONE_NORMAL])
        parsed = _parse_conclusion_lines(result.get("text") or [])
        facts = _conclusion_facts(result, parsed["why_items"], parsed["proof_items"], zone) if parsed["why_items"] else []
        wanted = ("bad",) if zone == ZONE_DANGER else ("bad", "warn")
        fact_reason = next((_sentence(label) for label, _chip, tone in facts
                            if tone in wanted and not _is_prose(label) and label not in _SA_NOT_A_FINDING), None)
        # A portfolio is first a question about the combination; a bot that
        # must not be copied is first about why not.
        reason = fact_reason if zone == ZONE_DANGER else (pf_reason or fact_reason)

    figs: List[Tuple[str, str, str]] = []
    pnl = perf.get("total_pnl")
    ruin = float(mc["p_ruin"]) if _is_finite_number(mc.get("p_ruin")) else None
    ploss = float(mc["p_loss_after_horizon"]) if _is_finite_number(mc.get("p_loss_after_horizon")) else None
    joint = _pf_joint(result)
    if joint:
        # A portfolio reads its joint run: every member, same-day co-movement kept.
        ruin = float(joint["p_ruin"]) if _is_finite_number(joint.get("p_ruin")) else None
        pp = joint.get("probability_of_profit")
        ploss = max(0.0, 100.0 - float(pp)) if _is_finite_number(pp) else None
    mc_label = "Monte Carlo"
    # A PORTFOLIO's headline figures describe the whole book: every member's
    # PnL (the book as one account) and the JOINT simulation (all members,
    # co-movement kept). The merged order book above covers only members whose
    # ledger OKX shows -- on a live 4-bot book (2026-09-25) its net PnL was
    # +342,460 against the book's +786,998, and its simulation "1 in 8 runs
    # end in a loss" against ~1 in 6 for the joint one.
    _pf = result.get("portfolio") if isinstance(result.get("portfolio"), dict) else {}
    _book = _pf.get("book") if isinstance(_pf.get("book"), dict) else {}
    _joint = _pf.get("joint_simulation") if isinstance(_pf.get("joint_simulation"), dict) else {}
    if _is_finite_number(_book.get("total_pnl")):
        pnl = _book.get("total_pnl")
    if _joint.get("is_valid"):
        ruin = float(_joint["p_ruin"]) if _is_finite_number(_joint.get("p_ruin")) else None
        profit = _joint.get("probability_of_profit")
        ploss = 100.0 - float(profit) if _is_finite_number(profit) else None
        mc_label = "Monte Carlo (joint)"
    if _is_finite_number(pnl) and result.get("status") != "LIMITED" and not no_trades:
        figs.append(("Net PnL", f"{float(pnl):+,.0f} USDT",
                     "good" if float(pnl) > 0 else ("bad" if float(pnl) < 0 else "")))
    if no_trades:
        pass
    elif ruin is not None and ruin >= 5:
        k = _one_in_text(ruin)
        figs.append((mc_label, f"{k} runs wipe out the account", "bad"))
    elif ploss is not None and ploss > 0:
        k = _one_in_text(ploss)
        figs.append((mc_label, f"{k} runs end in a loss",
                     "good" if ploss < 15 else ("warn" if ploss < 35 else "bad")))
    if cov is not None and cov < 100:
        figs.append(("Data coverage", cov_text, "warn"))
    if not (lead or figs):
        return ""
    # "Risk within normal range" with a caution reads as "…, but …".
    joiner = " — but " if zone == ZONE_NORMAL and reason and lead == _SA_LEAD[ZONE_NORMAL] and reason != _positive_pf_reason(pf_reason) else " — "
    title = f"{lead}{joiner}{reason}" if reason else lead
    verdict_line = ""
    if headline_verdict:
        words = " · ".join(
            re.sub(r"\b([A-Z])([A-Z]+)\b", lambda m: m.group(1) + m.group(2).lower(), part.strip())
            for part in headline_verdict.split("·")
        )
        verdict_line = (f'<div class="sa-verdict"><i style="background:{_verdict_color(result.get("verdict"))}"></i>'
                        f'{_esc(words)}</div>')
    figs_html = "".join(
        f'<div class="sa-fig"><div class="sa-fig-l">{_esc(l)}</div><div class="sa-fig-v sa-t-{t}">{_esc(v)}</div></div>'
        for l, v, t in figs
    )
    return (
        f'<div class="short-answer sa-{zone}"><div class="sa-head"><h2 class="sa-title">{_esc(title)}</h2>{verdict_line}</div>'
        + (f'<div class="sa-figs">{figs_html}</div>' if figs_html else "")
        + "</div>"
    )


def _tab_answer(title: str, chips: Sequence[Tuple[str, str, str]]) -> str:
    chips_html = "".join(
        f'<span><b class="sa-t-{t}">{_esc(v)}</b>{_esc(l)}</span>' for v, l, t in chips if v
    )
    return f'<div class="tab-answer"><div class="tab-answer-h">{_esc(title)}</div><div class="tab-answer-f">{chips_html}</div></div>'


def _exposure_by_regime(result: Dict[str, Any]) -> Dict[str, float]:
    """Share of trading value (%) in pairs whose trend is up / sideways /
    down right now -- the Traded markets exposure bar."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    share_map = evidence.get("symbol_exposure_share") if isinstance(evidence.get("symbol_exposure_share"), dict) else {}
    resolved = {str(m.get("symbol")): m for m in (evidence.get("resolved_markets") or []) if isinstance(m, dict) and m.get("symbol")}
    out: Dict[str, float] = {}
    for sym, v in share_map.items():
        if not _is_finite_number(v):
            continue
        m = resolved.get(str(sym))
        reg = _REGIME_OF_TREND.get(str(m.get("trend")), "No data") if m else "No data"
        out[reg] = out.get(reg, 0.0) + float(v) * 100.0
    return out


def _render_market_tab_answer(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    strategy = evidence.get("strategy") if isinstance(evidence.get("strategy"), dict) else {}
    exposure = _exposure_by_regime(result)
    known = {k: v for k, v in exposure.items() if k != "No data"}
    breakdown = [r for r in (strategy.get("phase_breakdown") or []) if isinstance(r, dict)]
    down = [r for r in breakdown if str(r.get("phase", "")).startswith("DOWNTREND")]
    down_trades = sum(int(r.get("trades") or 0) for r in down)
    down_pnl = sum(float(r.get("total_pnl") or 0.0) for r in down if _is_finite_number(r.get("total_pnl")))
    cov = evidence.get("coverage_achieved_pct")
    if not known and not breakdown:
        return ""
    word = {"Uptrend": "rising", "Downtrend": "falling", "Sideways": "sideways"}
    dom, share = max(known.items(), key=lambda kv: kv[1]) if known else (None, 0.0)
    lead = f"Mostly {word.get(dom, dom.lower())} markets" if dom and share >= 50 else ("Mixed markets" if dom else "Markets")
    if breakdown:
        clause = ("untested in a fall" if down_trades == 0 else
                  ("loses in a fall" if down_pnl < 0 else "holds up in a fall"))
        title = f"{lead} — {clause}"
    else:
        title = lead
    chips = []
    if dom:
        chips.append((f"{share:.0f}%", f"in {word.get(dom, dom.lower())} markets", ""))
    if breakdown:
        chips.append((f"{down_trades:,}", "downtrend trades", "warn" if down_trades == 0 else ""))
    if _is_finite_number(cov):
        chips.append((f"{float(cov):.0f}%", "checked", ""))
    return _tab_answer(title, chips)


def _losers_in_deepest(result: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    """(members that lost money inside the merged book's deepest drawdown,
    members with trades) -- the Contribution by bot figure."""
    members = [m for m in _pf_members(result) if not m.get("ledger_hidden")]
    series = [x for x in ((result.get("evidence") or {}).get("closed_trade_series") or [])
              if isinstance(x, dict) and _is_finite_number(x.get("realized_pnl"))]
    if not members or not series or not any(x.get("owner") for x in series):
        return None
    idx = _episode_indices([float(x["realized_pnl"]) for x in series], _ref_capital(result))
    if not idx:
        return None
    a, b = idx[0], idx[1]
    inwin: Dict[str, float] = {str(m.get("unique_code") or "")[:8]: 0.0 for m in members}
    for i, x in enumerate(series, 1):
        o = str(x.get("owner") or "")
        if o in inwin and a < i <= b:
            inwin[o] += float(x["realized_pnl"])
    return sum(1 for v in inwin.values() if v < 0), len(inwin)


def _render_trades_tab_answer(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    profile = compute_loss_profile(evidence) or {}
    ep = profile.get("deepest_episode") if isinstance(profile.get("deepest_episode"), dict) else {}
    depth = ep.get("depth_pct")
    if not _is_finite_number(depth):
        return ""
    depth = float(depth)
    lead = "Small losses" if depth < 10 else ("Moderate losses" if depth < 25 else "Deep losses")
    lead += ", recovered" if ep.get("recovered") else ", not recovered yet"
    booked, marked = perf.get("profit_factor"), perf.get("marked_profit_factor")
    hidden = _is_finite_number(booked) and _is_finite_number(marked) and float(booked) >= 1.0 > float(marked)
    losers = _losers_in_deepest(result)
    if losers and losers[1] > 1 and losers[0] == losers[1]:
        clause = "the bots fell together"
    elif hidden:
        clause = "a loss is hidden in open trades"
    else:
        clause = "nothing hidden"
    chips = [(f"−{depth:.1f}%", "max drawdown", "bad")]
    if losers and losers[1] > 1:
        chips.append((f"{losers[0]} of {losers[1]}", "bots lost", "bad" if losers[0] == losers[1] else ""))
    else:
        lp = perf.get("open_loss_to_capital_pct")
        if _is_finite_number(lp):
            chips.append((f"−{abs(float(lp)):.1f}%", "open", "bad" if hidden else ""))
    hv = _holdout_data(result)
    if hv.get("status") == "EVALUATED" and _is_finite_number(hv.get("folds_evaluated")):
        chips.append((f"{_int_text(hv.get('oos_profitable_folds'))} of {_int_text(hv.get('folds_evaluated'))}", "tests held", ""))
    return _tab_answer(f"{lead} — {clause}", chips)


def _render_tab_trades(result: Dict[str, Any]) -> str:
    if result.get("status") == "LIMITED":
        return _render_tab_trades_limited(result)
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    mc = result.get("mc") if isinstance(result.get("mc"), dict) else {}

    holdout, lab = _render_validation_section(result), _render_scenario_lab(result)
    openpos, infer = _render_open_positions_audit(result), _render_statistical_inference(result)
    assets, ledger = _render_assets(result), _render_closed_trades_table(result)

    hv = _holdout_data(result)
    robust_bits = []
    if holdout and hv.get("status") == "EVALUATED":
        robust_bits.append(f"OOS: {_GRADE_WORD.get(str(hv.get('stability_grade')), ('?', ''))[0].lower()} "
                           f"{_int_text(hv.get('oos_profitable_folds'))}/{_int_text(hv.get('folds_evaluated'))}")
    if lab:
        n_sc = len([x for x in ((_scenario_lab(result)).get("scenarios") or []) if isinstance(x, dict) and x.get("family") != "EXECUTION"])
        robust_bits.append(f"{n_sc} scenarios")
    robust_sum = " · ".join(robust_bits)
    mpf = perf.get("marked_profit_factor")
    psr = _ratio_to_pct(mc.get("probabilistic_sharpe"))
    hidden_loss = _is_finite_number(perf.get("profit_factor")) and _is_finite_number(mpf) and float(perf["profit_factor"]) >= 1.0 > float(mpf)
    open_sum = " · ".join(
        x for x in (
            ("Hidden loss" if hidden_loss else "No hidden loss") if perf.get("open_positions") is not None or _is_finite_number(mpf) else "",
            f"MTM PF {_num(mpf, 2)}" if _is_finite_number(mpf) else (
                f"MTM PF {_num(perf.get('profit_factor'), 2)}" if _is_finite_number(perf.get("profit_factor"))
                and _is_finite_number(perf.get("open_positions")) and int(float(perf["open_positions"])) == 0 else ""),
            f"PSR {_pct(psr, 1)}" if psr is not None else "",
        ) if x
    )
    assets_list = [a for a in (result.get("assets") or []) if isinstance(a, dict)]
    open_n = sum(int(a.get("open_positions") or 0) for a in assets_list)
    series = evidence.get("closed_trade_series") if isinstance(evidence.get("closed_trade_series"), list) else []
    last_ct = max((float(x["close_time"]) for x in series if isinstance(x, dict) and _is_finite_number(x.get("close_time"))), default=None)
    ledger_sum = f"{len(series):,} trades" + (f" · last {datetime.fromtimestamp(last_ct / 1000, tz=_VN_TZ).strftime('%d/%m %H:%M')}" if last_ct else "")
    sections = [
        _render_trades_tab_answer(result),
        _render_drawdown_vs_capital(result),
        _render_contribution(result),
        _render_trade_metrics(result),
        _tab_group_card([
            ("robust", "Robustness", robust_sum, (holdout + lab) and f'<div class="pv-pair">{holdout}{lab}</div>'),
            ("openstats", "Open positions & statistics", open_sum, (openpos + infer) and f'<div class="pv-pair">{openpos}{infer}</div>'),
        ]),
        _tab_group_card([
            ("assets", "Traded assets", f"{len(assets_list)} pairs · {open_n} open", assets),
            ("ledger", "Most recent closed trades", ledger_sum, ledger),
        ], extras={
            "assets": '<span class="mk-foot-note as-legend">Status legend<span class="info-ic">i<span class="info-tip">Trading = recent '
                      'closed trade. Holding only = open position, no recent close. Exited = no exposure, no recent trade.</span></span></span>',
            "ledger": _ledger_filter_html(result) if ledger else "",
        }, compact=True),
    ]
    return "".join(s for s in sections if s)






_REGIME_OF_TREND = {"BULLISH": "Uptrend", "BEARISH": "Downtrend", "SIDEWAYS": "Sideways", "RANGE": "Sideways"}
_VOL_WORD = {"LOW": "calm", "NORMAL": "normal volatility", "HIGH": "highly volatile"}
_FLOW_WORD = {"NEUTRAL": "balanced", "BUY": "buy-side", "SELL": "sell-side", "BULLISH": "buy-side", "BEARISH": "sell-side"}


def _mk_switch_js(key: str) -> str:
    return (
        "var c=this.closest('.mk-card');"
        f"c.querySelectorAll('.mk-pane').forEach(function(p){{p.hidden=p.getAttribute('data-a')!=='{key}';}});"
        f"c.querySelectorAll('.mk-ftab').forEach(function(b){{b.classList.toggle('on',b.getAttribute('data-a')==='{key}');}});"
    )


_PAIR_MIN_TRADES = 5


def _same_market_comparison(result: Dict[str, Any], symbol: str) -> str:
    """This bot against the other analyzed bots that traded the same pair,
    on that pair only (web/data.py `pair_stats_table`, split from each bot's
    stored closed-trade ledger): profit factor, max drawdown of the pair's
    cumulative PnL as % of the bot's reference capital, and win rate. A bot
    enters the group with at least `_PAIR_MIN_TRADES` closed trades on the
    pair; a metric needs 3 such peers; with no metric left the block is not
    rendered. Rank #1 = best (lowest drawdown, highest PF / win rate)."""
    table = result.get("_pair_stats")
    code = str(result.get("code") or "")
    if not isinstance(table, dict) or code not in table:
        return ""
    mine = (table.get(code) or {}).get(symbol) or {}
    if int(mine.get("trades") or 0) < _PAIR_MIN_TRADES:
        return ""
    peers = [
        stats[symbol] for c, stats in table.items()
        if c != code and isinstance(stats, dict) and isinstance(stats.get(symbol), dict)
        and int(stats[symbol].get("trades") or 0) >= _PAIR_MIN_TRADES
    ]
    specs = (
        ("[PROFIT FACTOR]", "profit_factor", False, lambda v: f"{v:.2f}", "PF"),
        ("[MAX DRAWDOWN]", "max_drawdown_pct", True, lambda v: f"{v:.1f}%", "max DD"),
        ("[WIN RATE]", "win_rate", False, lambda v: f"{v:.1f}%", "win rate"),
    )
    # A portfolio's row is its merged book, not one bot.
    subject = "This book" if result.get("portfolio") else "This bot"
    out_rows, tags = [], []
    for tag, key, lower_better, fmt, short in specs:
        me = mine.get(key)
        vals = [float(p[key]) for p in peers if _is_finite_number(p.get(key))]
        if not _is_finite_number(me) or len(vals) < 3:
            continue
        me = float(me)
        ordered = sorted(vals)
        n = len(ordered)
        median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        rank = 1 + sum(1 for v in vals if (v < me if lower_better else v > me))
        group = n + 1
        tone = "good" if rank / group <= 1 / 3 else ("warn" if rank / group <= 2 / 3 else "bad")
        out_rows.append(
            f'<div class="quant-audit-row"><div class="quant-audit-tag">{tag}</div>'
            f'<div class="quant-audit-main"><span class="ev-chunk">{subject} <b class="quant-num">{fmt(me)}</b></span>'
            f'<span class="ev-chunk">Median <b class="quant-num">{fmt(median)}</b></span></div>'
            f'<div class="quant-audit-end"><span class="ev-pill ev-pill-{tone}" title="Rank {rank} of {group}">#{rank}</span></div></div>'
        )
        tags.append(f"{short} #{rank}")
    if not out_rows:
        return ""
    inner = (
        f'<div class="quant-audit-rows mk-compare">{"".join(out_rows)}</div>'
        f'<div class="gc-note mk-foot">Closed trades on {_esc(symbol)}-USDT only · drawdown as % of each bot&#39;s reference capital · '
        f"bots with at least {_PAIR_MIN_TRADES} closed trades on the pair.</div>"
    )
    return _collapse_toggle(
        "Show same-market comparison", "Hide same-market comparison",
        f"vs. {len(peers)} other analyzed bots on {symbol}-USDT · {int(mine.get('trades') or 0)} closed trades · " + " · ".join(tags),
        inner,
    )


def _render_dominant_market_card(result: Dict[str, Any]) -> str:
    """Traded markets, laid out like the redesign preview: pair tabs (All
    markets + every pair whose market data was looked up), the exposure bar
    by the regime each pair is in now, one row per traded pair, and a pane per
    pair. Every figure is the analysis' own (`symbol_exposure_share`,
    `resolved_markets`, `unresolved_markets`, `assets`, `market_analysis`);
    order-book depth and posture exist for the primary pair only, so only its
    pane shows them. No 180-day return column: the analysis does not produce
    one per pair."""
    market = result.get("market_analysis") or ((result.get("evidence") or {}).get("market_analysis")) or {}
    evidence = result.get("evidence") or {}
    symbol = str(market.get("symbol") or evidence.get("traded_symbol") or "Premium Market")
    venue = market.get("venue_type") or "CEX"
    posture = market.get("posture") or ("STABLE" if market.get("available") else "UNDETERMINED")
    stable = "ỔN" in str(posture) or posture == "STABLE"
    share_map = evidence.get("symbol_exposure_share") if isinstance(evidence.get("symbol_exposure_share"), dict) else {}
    resolved = {str(m.get("symbol")): m for m in (evidence.get("resolved_markets") or []) if isinstance(m, dict) and m.get("symbol")}
    unresolved = {str(m.get("symbol")): m for m in (evidence.get("unresolved_markets") or []) if isinstance(m, dict) and m.get("symbol")}
    assets = {str(a.get("asset")): a for a in (result.get("assets") or []) if isinstance(a, dict) and a.get("asset")}
    primary = str(evidence.get("traded_symbol") or market.get("symbol") or "")
    rows_src = sorted(((s, float(v) * 100.0) for s, v in share_map.items() if _is_finite_number(v)), key=lambda x: -x[1])
    if not rows_src and primary:
        rows_src = [(primary, float(evidence.get("primary_share_pct") or 100.0))]
    colors = {s_: _ASSET_DOT[i % len(_ASSET_DOT)] for i, (s_, _) in enumerate(rows_src)}
    shares = dict(rows_src)

    def regime_of(s_: str) -> Tuple[str, str]:
        m = resolved.get(s_)
        if not m:
            return "No data", "na"
        reg = _REGIME_OF_TREND.get(str(m.get("trend")), "No data")
        return reg, {"Uptrend": "up", "Downtrend": "down", "Sideways": "side"}.get(reg, "na")

    # --- pair tabs
    # A pair gets its own tab only when there is market data to show for it
    # (the primary pair, or a pair whose market data was resolved); the
    # others stay as rows of the All markets table.
    tab_syms = [s_ for s_, _ in rows_src if s_ in resolved or (s_ == primary and market)]
    if not tab_syms:
        # No traded pair has market data: nothing to show (project owner,
        # 2026-09-24 -- what is not public is not talked about).
        return ""
    ftabs = f'<button type="button" class="mk-ftab on" data-a="ALL" onclick="{_mk_switch_js("ALL")}">All markets</button>' + "".join(
        f'<button type="button" class="mk-ftab" data-a="{_esc(s_)}" onclick="{_mk_switch_js(_esc(s_))}">'
        f'{_esc(s_)} <span>{("&lt;1" if 0 < shares.get(s_, 0) < 0.5 else f"{shares.get(s_, 0):.0f}")}%</span></button>'
        for s_ in tab_syms
    )
    tip = ("Every pair the bot traded, weighted by trading value. Every resolved pair gets trend, volatility, "
           "liquidity tier and order flow. Depth, spread and market posture are checked on the primary pair only.")
    head = (
        f'<div class="mk-head"><span class="mc-title">Traded markets<i class="info-ic" tabindex="0">i<span class="info-tip">{_esc(tip)}</span></i></span>'
        f'<span class="mk-ftabs">{ftabs}</span></div>'
    )

    # --- ALL pane
    all_parts: List[str] = []
    buckets: Dict[str, List[Tuple[str, float]]] = {"up": [], "side": [], "down": [], "na": []}
    for s_, sh in rows_src:
        buckets[regime_of(s_)[1]].append((s_, sh))
    seg, leg = [], []
    for cls, name in (("up", "Uptrend"), ("side", "Sideways"), ("down", "Downtrend"), ("na", "No data")):
        tot = sum(sh for _, sh in buckets[cls])
        if tot <= 0:
            continue
        label = (f"{name} {tot:.0f}%" if tot >= 25 and cls != "na" else f"{tot:.0f}%") if tot >= 5 else ""
        seg.append(f'<span class="mk-seg mk-seg-{cls}" style="flex:{tot:.3f} 1 0" title="{_esc(name)}: {tot:.1f}% of trading value">{_esc(label)}</span>')
        syms = ", ".join(s for s, _ in buckets[cls][:4]) + ("…" if len(buckets[cls]) > 4 else "")
        leg.append(f'<span><i class="mk-seg-{cls}"></i>{_esc(name)} · {_esc(syms)}</span>')
    all_parts.append(
        '<div class="st-label mk-sub">Exposure by trading volume</div>'
        f'<div class="mk-bar">{"".join(seg)}</div><div class="mk-legend">{"".join(leg)}</div>'
    )
    top = rows_src[0][1] if rows_src else 1.0
    trs = []
    # Only pairs with market data get a row (same set as the pair tabs); the
    # rest are summed in one line under the table and stay visible, pair by
    # pair, in the exposure bar above and in "Market being scored".
    hidden_rows = [(s_, sh) for s_, sh in rows_src if s_ not in tab_syms]
    for s_, share in [(s_, sh) for s_, sh in rows_src if s_ in tab_syms]:
        a = assets.get(s_) or {}
        state = str(a.get("state") or "")
        tone = {"TRADING": "good", "HOLDING ONLY": "warn", "EXITED": "flat"}.get(state, "flat")
        reg, reg_cls = regime_of(s_)
        if s_ in resolved:
            vol = _VOL_WORD.get(str(resolved[s_].get("volatility")), "")
            regime = f'<i class="mk-sq mk-seg-{reg_cls}"></i>{_esc(reg)}{", " + _esc(vol) if vol else ""}'
            data = '<span class="st-chip st-chip-good pv-state">Resolved</span>'
        elif s_ in unresolved:
            regime = '<span class="pv-muted">—</span>'
            reason = str(unresolved[s_].get("reason") or "")
            lbl = "Timed out" if "TIMEOUT" in reason else "No data"
            data = f'<span class="st-chip st-chip-warn pv-state" title="{_esc(reason or lbl)}">{lbl}</span>'
        else:
            regime = '<span class="pv-muted">—</span>'
            data = '<span class="st-chip st-chip-flat pv-state" title="Too small a share of trading value to be looked up">Not looked up</span>'
        activity = f'<span class="st-chip st-chip-{tone} pv-state">{_esc(state.capitalize())}</span>' if state else '<span class="pv-muted">—</span>'
        trades = (f'{_int_text(a.get("closed_seen"))}<span class="pv-muted"> · {_int_text(a.get("open_positions"))} open</span>' if a else '<span class="pv-muted">—</span>')
        click = f' onclick="{_mk_switch_js(_esc(s_))}" style="cursor:pointer"' if s_ in tab_syms else ""
        trs.append(
            f"<tr{click}>"
            f'<td><span class="pv-dot" style="background:{colors[s_]}"></span><b class="pv-asset">{_esc(s_)}-USDT</b>'
            + (' <span class="mk-primary">Primary</span>' if s_ == primary else "") + "</td>"
            f'<td><span class="mk-share"><span class="pv-abar"><span style="width:{share / (top or 1) * 100:.0f}%;background:#9aa0aa"></span></span><b>{("&lt;1" if 0 < share < 0.5 else f"{share:.0f}")}%</b></span></td>'
            f'<td class="pv-num mk-r">{trades}</td><td>{activity}</td><td>{regime}</td><td class="mk-r">{data}</td></tr>'
        )
    all_parts.append(
        '<div class="table-scroll"><table class="pv-table mk-table"><colgroup><col style="width:24%"><col style="width:15%">'
        '<col style="width:13%"><col style="width:14%"><col style="width:22%"><col style="width:12%"></colgroup>'
        '<thead><tr><th>Pair</th><th>Volume share</th>'
        '<th class="mk-r">Trades</th><th>Activity</th><th>Current regime</th><th class="mk-r">Market data</th></tr></thead>'
        f'<tbody>{"".join(trs)}</tbody></table></div>'
    )
    if hidden_rows:
        all_parts.append(
            f'<div class="gc-note mk-foot">+{len(hidden_rows)} more pairs without market data · '
            f'{sum(sh for _, sh in hidden_rows):.1f}% of trading value ({_esc(", ".join(s for s, _ in hidden_rows[:6]))}'
            f'{"…" if len(hidden_rows) > 6 else ""})</div>'
        )
    panes = [f'<div class="mk-pane" data-a="ALL">{"".join(all_parts)}</div>']

    # --- one pane per traded pair, same structure as the portfolio redesign
    # mockup (portfolio-report-redesign.html `tradedMarkets`): header pills,
    # the four regime tiles (or the "no market data" box -- never inferred
    # from another market), "Bot activity on this pair", the primary-only
    # note, and the same-market comparison toggle.
    tr_word_of = {"BULLISH": "Bullish", "BEARISH": "Bearish", "SIDEWAYS": "Sideways", "RANGE": "Sideways"}
    for s_ in tab_syms:
        a = assets.get(s_) or {}
        m = resolved.get(s_)
        is_primary = s_ == primary
        state = str(a.get("state") or "")
        act_tone = {"TRADING": "good", "HOLDING ONLY": "warn", "EXITED": "flat"}.get(state, "flat")
        pills = [f'<span class="st-chip st-chip-flat mk-pill">{_esc(str((m or {}).get("venue_type") or venue))} · OKX</span>']
        if is_primary:
            pills.append(f'<span class="mk-primary mk-primary-lg">Primary · {shares.get(s_, 0):.0f}% of value</span>')
            right = f'<span class="st-chip {"st-chip-good" if stable else "st-chip-warn"} mk-right mk-pill">Status: {_esc(str(posture).capitalize())}</span>' if market else ""
        else:
            pills.append(f'<span class="st-chip st-chip-flat mk-pill">Secondary · {shares.get(s_, 0):.1f}% of value</span>')
            right = f'<span class="st-chip st-chip-{act_tone} mk-right mk-pill">{_esc(state.capitalize())}</span>' if state else ""
        body = f'<div class="mk-pair"><b class="mk-pair-n">{_esc(s_)}-USDT</b>{"".join(pills)}{right}</div>'

        def tile(label: str, value: str, tone: str = "") -> str:
            return f'<div class="pv-mini mk-spec"><span>{_esc(label)}</span><b class="pv-v-{tone}">{_esc(value)}</b></div>'

        if is_primary and market:
            t = market.get("trend")
            body += '<div class="mk-specs">' + tile("Market trend", tr_word_of.get(str(t), "Undetermined"), "good" if t == "BULLISH" else ("bad" if t == "BEARISH" else "")) \
                + tile("Volatility", str(market.get("volatility") or "—").capitalize()) \
                + tile("Order book depth", str(market.get("liquidity") or "—").capitalize()) \
                + tile("Data quality", _pct(float(market["data_quality"]) * 100 if _is_finite_number(market.get("data_quality")) else 100.0, 0)) + "</div>"
            ev = [str(e) for e in (market.get("posture_evidence") or [])]
            if ev:
                body += ('<div class="st-label mk-sub" title="Step 1 + 2 basis: order-book liquidity, volatility range and two-way order flow, '
                         'from the order book and historical candles.">Market evidence</div><div class="mk-notes" aria-label="Status evidence from Step 1 + 2">'
                         + "".join(f'<span class="mk-note">{_highlight_quant_numbers(e)}</span>' for e in ev) + "</div>")
        elif m:
            t = m.get("trend")
            body += '<div class="mk-specs">' + tile("Market trend", tr_word_of.get(str(t), "—"), "good" if t == "BULLISH" else ("bad" if t == "BEARISH" else "")) \
                + tile("Volatility", str(m.get("volatility") or "—").capitalize()) \
                + tile("Order book depth", str(m.get("liquidity_tier") or "—").capitalize()) \
                + tile("Order flow", _FLOW_WORD.get(str(m.get("flow_bias")), str(m.get("flow_bias") or "—")).capitalize()) + "</div>"
            reg, reg_cls = regime_of(s_)
            vol = _VOL_WORD.get(str(m.get("volatility")), "")
            extra = [f'<span class="mk-note"><i class="mk-sq mk-seg-{reg_cls}"></i>Current regime: {_esc(reg)}{", " + _esc(vol) if vol else ""}</span>']
            if _is_finite_number(m.get("last_price")):
                extra.append(f'<span class="mk-note">Last price <b class="quant-num">{float(m["last_price"]):,.6g}</b></span>')
            extra.append('<span class="st-chip st-chip-good mk-pill">Market data resolved</span>')
            body += f'<div class="mk-notes">{"".join(extra)}</div>'
        else:
            reason = str((unresolved.get(s_) or {}).get("reason") or "")
            head_txt = ("No market data · request timed out" if "TIMEOUT" in reason else
                        "No market data" if s_ in unresolved else "No market data · not looked up")
            sub = ("Trend, volatility and regime are not inferred from another market." if s_ in unresolved else
                   f"{shares.get(s_, 0):.1f}% of trading value is below the share the analysis looks up; "
                   "trend, volatility and regime are not inferred from another market.")
            body += f'<div class="mk-empty"><b>{_esc(head_txt)}</b><span>{_esc(sub)}</span></div>'

        if a:
            chips_a = [
                f'<span class="mk-note">Closed trades <b class="quant-num">{_int_text(a.get("closed_seen"))}</b></span>',
                f'<span class="mk-note">Open <b class="quant-num">{_int_text(a.get("open_positions"))}</b></span>',
            ]
            if _is_finite_number(a.get("last_close_days")):
                chips_a.append(f'<span class="mk-note">Last close <b class="quant-num">{float(a["last_close_days"]):.1f} d ago</b></span>')
            body += f'<div class="st-label mk-sub">Bot activity on this pair</div><div class="mk-notes">{"".join(chips_a)}</div>'
        if not is_primary:
            body += ('<div class="mk-foot-note"><i class="info-ic" tabindex="0">i<span class="info-tip">Every resolved pair gets trend, volatility, '
                     'liquidity tier and flow. The detailed order-book check (depth, spread, posture) runs on the primary pair only.</span></i>'
                     "Depth, spread, data age and market posture: primary pair only.</div>")

        cmp_html = _same_market_comparison(result, s_)
        if cmp_html:
            body += cmp_html
        panes.append(f'<div class="mk-pane" data-a="{_esc(s_)}" hidden>{body}</div>')
    return _section("Bot's primary trading market", f'<div class="mk-card">{head}{"".join(panes)}</div>', anchor="thi-truong-chinh")


_RG_ORDER = ("UPTREND_CALM", "UPTREND_VOLATILE", "RANGE_CALM", "RANGE_VOLATILE", "DOWNTREND_CALM", "DOWNTREND_VOLATILE")
_RG_CLS = {
    "UPTREND_CALM": "uc", "UPTREND_VOLATILE": "uv", "RANGE_CALM": "sc",
    "RANGE_VOLATILE": "sv", "DOWNTREND_CALM": "dc", "DOWNTREND_VOLATILE": "dv",
}


def _rg_bar(days: List[Any], start: int, span: int) -> str:
    """One asset's regime row: consecutive days of the same phase merged."""
    segs: List[Tuple[str, int, int]] = []
    for day, phase in days:
        idx = (int(day) - start) // 86_400_000
        if idx < 0 or idx >= span:
            continue
        if segs and segs[-1][0] == phase and segs[-1][2] == idx:
            segs[-1] = (phase, segs[-1][1], idx + 1)
        else:
            segs.append((str(phase), idx, idx + 1))
    out = []
    cursor = 0
    for phase, a, b in segs:
        if a > cursor:
            out.append(f'<span class="rg-seg rg-na" style="left:{cursor / span * 100:.3f}%;width:{(a - cursor) / span * 100:.3f}%"></span>')
        out.append(
            f'<span class="rg-seg rg-{_RG_CLS.get(phase, "na")}" style="left:{a / span * 100:.3f}%;width:{(b - a) / span * 100:.3f}%" '
            f'title="{_esc(_phase_label_vi(phase))} · {b - a} day{"s" if b - a != 1 else ""}"></span>'
        )
        cursor = b
    return "".join(out)


def _regime_asset_view(t: Dict[str, Any], start: int, span: int, trades: List[Tuple[float, float]], asset: Optional[Dict[str, Any]]) -> str:
    """One asset of Market compatibility, as in the redesign mockup: summary
    chips, the pair's daily close over the window drawn over its regime
    bands, the bot's closed trades under it, and the share of time the pair
    spent in each regime. Everything comes from that pair's own candles
    (web/data.py `regime_timeline`); the ledger carries no pair per trade, so
    the trade marks are the bot's trades on all pairs and there is no
    per-regime trade count for a single pair."""
    sym = str(t["symbol"])
    days = t.get("days") or []
    hours = {str(k): int(v) for k, v in (t.get("hours") or {}).items() if _is_finite_number(v)}
    total_h = sum(hours.values()) or 1
    now_phase = str(t.get("last_phase_hourly") or (days[-1][1] if days else "UNKNOWN"))
    known = {k: v for k, v in hours.items() if k != "UNKNOWN"}
    most = max(known, key=known.get) if known else None
    down_h = sum(v for k, v in hours.items() if k.startswith("DOWNTREND"))
    ret = t.get("return_pct")
    chips = [
        f'<span class="st-chip st-chip-{"good" if now_phase.startswith("UPTREND") else ("bad" if now_phase.startswith("DOWNTREND") else "flat")} rg-chip">'
        f"Now: {_esc(_phase_label_vi(now_phase).capitalize())}"
        + (f' · as of {datetime.fromtimestamp(int(days[-1][0]) / 1000, tz=timezone.utc).strftime("%d/%m")}' if days else "")
        + "</span>"
    ]
    if most:
        chips.append(f'<span class="st-chip st-chip-flat rg-chip rg-chip-info">Most time: {_esc(_phase_label_vi(most).capitalize())} {known[most] / total_h * 100:.1f}%</span>')
    chips.append(f'<span class="st-chip {"st-chip-warn" if down_h else "st-chip-flat"} rg-chip">Downtrend: {down_h:,} h in window</span>')
    if _is_finite_number(ret):
        chips.append(f'<span class="st-chip st-chip-{"good" if ret >= 0 else "bad"} rg-chip">{span}d {float(ret):+.1f}%</span>')
    if asset and _is_finite_number(asset.get("closed_seen")):
        chips.append(f'<span class="st-chip st-chip-flat rg-chip">{_int_text(asset.get("closed_seen"))} trades</span>')

    # price over regime bands
    closes = [(int(d), float(c)) for d, c in (t.get("closes") or []) if _is_finite_number(c)]
    chart = ""
    if len(closes) >= 2:
        W, H, L, R, T, B = 1200.0, 330.0, 56.0, 8.0, 8.0, 46.0
        pw, ph = W - L - R, H - T - B
        lo, hi = min(c for _, c in closes), max(c for _, c in closes)
        padv = (hi - lo) * 0.06 or hi * 0.01 or 1.0
        lo, hi = lo - padv, hi + padv

        def X(ms: float) -> float:
            return L + pw * ((ms - start) / 86_400_000 + 0.5) / span

        def Y(v: float) -> float:
            return T + ph * (1 - (v - lo) / (hi - lo))

        parts = []
        # regime bands
        seg_start, seg_phase = None, None
        for i, (d, p) in enumerate(days + [[None, None]]):
            if d is not None and p == seg_phase:
                continue
            if seg_phase is not None:
                x0 = max(L, L + pw * ((seg_start - start) / 86_400_000) / span)
                x1 = min(L + pw, L + pw * (((int(days[i - 1][0]) - start) / 86_400_000) + 1) / span)
                if x1 > x0:
                    parts.append(f'<rect class="rgb rg-{_RG_CLS.get(str(seg_phase), "na")}" x="{_coord(x0)}" y="{_coord(T)}" width="{_coord(x1 - x0)}" height="{_coord(ph)}"/>')
            if d is not None:
                seg_start, seg_phase = int(d), p
        for k in range(5):
            v = lo + (hi - lo) * k / 4
            y = Y(v)
            parts.append(f'<line class="rgc-grid" x1="{_coord(L)}" y1="{_coord(y)}" x2="{_coord(L + pw)}" y2="{_coord(y)}"/>')
            lbl = f"{v / 1000:.0f}k" if v >= 10000 else (f"{v:,.0f}" if v >= 100 else f"{v:.4g}")
            parts.append(f'<text class="rgc-tick" x="{_coord(L - 6)}" y="{_coord(y + 3.5)}" text-anchor="end">{lbl}</text>')
        dpath = " ".join(f"{'M' if i == 0 else 'L'}{_coord(X(d))},{_coord(Y(c))}" for i, (d, c) in enumerate(closes))
        parts.append(f'<path class="rgc-line" d="{dpath}"/>')
        dt = datetime.fromtimestamp(start / 1000, tz=timezone.utc)
        y_, m_ = dt.year, dt.month
        while True:
            m_ += 1
            if m_ > 12:
                m_, y_ = 1, y_ + 1
            ms = int(datetime(y_, m_, 1, tzinfo=timezone.utc).timestamp() * 1000)
            if ms > start + span * 86_400_000:
                break
            parts.append(f'<text class="rgc-tick" x="{_coord(X(ms))}" y="{_coord(T + ph + 14)}" text-anchor="middle">{datetime(y_, m_, 1).strftime("%b")}</text>')
        # the bot's closed trades (all pairs -- the ledger has no pair per trade)
        ty = T + ph + 26
        if trades:
            parts.append(f'<rect class="rgc-trackbg" x="{_coord(L)}" y="{_coord(ty - 7)}" width="{_coord(pw)}" height="14" rx="3"/>')
            parts.append(f'<text class="rgc-tick" x="{_coord(L - 6)}" y="{_coord(ty + 3.5)}" text-anchor="end">Trades</text>')
            # One tick per trade drew 1,000+ <line>s per asset, most of them
            # at an x another trade already used. Ticks at the same x are the
            # same opaque rectangle, so only the last one painted shows:
            # keep that one, in its place -- same pixels, same order.
            last: Dict[str, str] = {}
            for ms, pnl in trades:
                if start <= ms <= start + span * 86_400_000:
                    xs = _coord(L + pw * ((ms - start) / 86_400_000) / span)
                    last.pop(xs, None)
                    last[xs] = "rgc-win" if pnl > 0 else "rgc-loss"
            y0, y1 = _coord(ty - 6), _coord(ty + 6)
            for xs, cls in last.items():
                parts.append(f'<line class="rgc-mk {cls}" x1="{xs}" y1="{y0}" x2="{xs}" y2="{y1}"/>')
        chart = f'<svg class="rgc-svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="{_esc(sym)} daily close over its market regime">{"".join(parts)}</svg>'

    order = list(_RG_ORDER) + ["UNKNOWN"]
    top = max(hours.values()) if hours else 1
    items = []
    for ph_ in order:
        h = hours.get(ph_, 0)
        pct = h / total_h * 100
        name = "Unclassified" if ph_ == "UNKNOWN" else _phase_label_vi(ph_).capitalize()
        cls = _RG_CLS.get(ph_, "na")
        items.append(
            f'<div class="rga-row{" rga-zero" if h == 0 else ""}"><span class="rga-n"><i class="rg-sq rg-{cls}"></i>{_esc(name)}</span>'
            f'<span class="pv-abar"><span class="rg-{cls}" style="width:{h / (top or 1) * 100:.1f}%"></span></span>'
            f'<b class="pv-num">{pct:.1f}%</b></div>'
        )
    half = (len(items) + 1) // 2
    table = (
        '<div class="rga-grid">'
        f'<div><div class="rga-row rga-head"><span>Phase · {_esc(sym)}</span><span>Time in market</span><span></span></div>{"".join(items[0::2])}</div>'
        f'<div><div class="rga-row rga-head"><span>Phase · {_esc(sym)}</span><span>Time in market</span><span></span></div>{"".join(items[1::2])}</div>'
        "</div>"
    )
    return f'<div class="rg-chips">{"".join(chips)}</div>{chart}{table}'


def _render_market_compatibility(result: Dict[str, Any]) -> str:
    """Market compatibility across every market the bot trades, laid out like
    the portfolio redesign mockup: each traded pair's own regime over the last
    180 days (web/data.py `regime_timelines`, same phase rule as scoring), the
    bot's closed trades on the same time axis, chips for what the reader must
    not miss, and the results by phase behind a toggle
    (`evidence.strategy.phase_breakdown`, every regime listed including the
    ones with no trade). A pair without candles is shown as "no market data",
    never with another market's phases. Closed trades carry no pair in the
    saved ledger, so they are drawn once for all pairs rather than per pair."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    strategy = evidence.get("strategy") if isinstance(evidence.get("strategy"), dict) else {}
    timelines = [t for t in (result.get("_regime_timelines") or []) if isinstance(t, dict) and t.get("symbol")]
    breakdown = [r for r in (strategy.get("phase_breakdown") or []) if isinstance(r, dict)]
    compat = _insights(result).get("market_compatibility") or {}
    if not timelines and not breakdown and not compat.get("cells"):
        return ""

    share_map = evidence.get("symbol_exposure_share") if isinstance(evidence.get("symbol_exposure_share"), dict) else {}
    shares = {str(k): float(v) * 100.0 for k, v in share_map.items() if _is_finite_number(v)}
    parts: List[str] = []
    tip = ("Trades on every pair, each tagged with its own pair's phase. Every regime is listed, including ones "
           "with no trades -- hiding them would show only the conditions that went well.")
    parts.append(
        '<div class="gc-head"><span class="mc-title" >Market compatibility</span>'
        f'<span class="gc-note mk-head">All assets · results by regime<i class="info-ic" tabindex="0">i<span class="info-tip">{_esc(tip)}</span></i></span></div>'
    )

    # Only pairs with a regime history are shown (same rule as Traded
    # markets): a pair with no candles has nothing to draw, and the data
    # coverage section already lists it as not measured.
    timelines = [t for t in timelines if t.get("available") and t.get("days")]
    if not timelines and not any(_is_finite_number(r.get("trades")) and float(r["trades"]) > 0 for r in breakdown) and not compat.get("cells"):
        return ""
    with_data = timelines
    if timelines:
        end = max((int(t["days"][-1][0]) for t in with_data), default=0)
        span = 180
        start = end - (span - 1) * 86_400_000 if end else 0
        # chips
        down_on = [t["symbol"] for t in with_data if any(p in ("DOWNTREND_CALM", "DOWNTREND_VOLATILE") for _, p in t["days"])]
        down_trades = sum(int(r.get("trades") or 0) for r in breakdown if str(r.get("phase", "")).startswith("DOWNTREND"))
        no_data = [t["symbol"] for t in timelines if not (t.get("available") and t.get("days"))]
        chips = []
        if down_on:
            chips.append(f'<span class="st-chip st-chip-warn rg-chip">Downtrend seen on: {_esc(", ".join(down_on))}</span>')
        if breakdown:
            chips.append(f'<span class="st-chip st-chip-flat rg-chip">Bot trades in a downtrend: {down_trades}</span>')

        # month ticks
        ticks = []
        if start:
            d = datetime.fromtimestamp(start / 1000, tz=timezone.utc)
            y, mth = d.year, d.month
            while True:
                mth += 1
                if mth > 12:
                    mth, y = 1, y + 1
                ms = int(datetime(y, mth, 1, tzinfo=timezone.utc).timestamp() * 1000)
                if ms > end:
                    break
                pos = (ms - start) / 86_400_000 / span * 100
                ticks.append(f'<span class="rg-tick" style="left:{pos:.2f}%">{datetime(y, mth, 1).strftime("%b")}</span>')

        # bot trades (all pairs) on the same axis
        series = [x for x in (evidence.get("closed_trade_series") or []) if isinstance(x, dict)]
        # Same position = same box: only the mark painted last shows, so
        # keep that one (order of the rest unchanged).
        latest: Dict[str, str] = {}
        for x in series:
            ct, pnl = x.get("close_time"), x.get("realized_pnl")
            if not (_is_finite_number(ct) and _is_finite_number(pnl)) or not start or float(ct) < start:
                continue
            pos = (float(ct) - start) / 86_400_000 / span * 100
            if pos <= 100.5:
                key = f"{min(pos, 100):.2f}"
                latest.pop(key, None)
                latest[key] = "rg-win" if float(pnl) > 0 else "rg-loss"
        marks = [f'<span class="rg-mark {cls}" style="left:{key}%"></span>' for key, cls in latest.items()]

        def row(t: Dict[str, Any]) -> str:
            sym = str(t["symbol"])
            label = f'<div class="rg-l"><b>{_esc(sym)}-USDT</b><span>{shares.get(sym, 0):.1f}% of value</span></div>'
            if t.get("available") and t.get("days"):
                now_phase = str(t["days"][-1][1])
                bar = f'<div class="rg-bar">{_rg_bar(t["days"], start, span)}</div>'
                as_of = datetime.fromtimestamp(int(t["days"][-1][0]) / 1000, tz=timezone.utc).strftime("%d/%m")
                right = (f'<div class="rg-now" title="Majority phase of the last day with candles"><i class="rg-sq rg-{_RG_CLS.get(now_phase, "na")}"></i>'
                         f'<span>{_esc(_phase_label_vi(now_phase).capitalize())}<em>as of {as_of}</em></span></div>')
            else:
                bar = '<div class="rg-bar rg-bar-empty"><span>No market data · no candle history for this pair</span></div>'
                right = '<div class="rg-now rg-now-na">no data</div>'
            return f'<div class="rg-row">{label}{bar}{right}</div>'

        trades_row = (
            '<div class="rg-row rg-row-trades"><div class="rg-l"><b>Bot trades</b><span>all pairs · closed</span></div>'
            f'<div class="rg-marks">{"".join(marks)}</div><div class="rg-now rg-now-na"></div></div>'
            if marks else ""
        )
        axis = f'<div class="rg-row rg-axis-row"><div class="rg-l"></div><div class="rg-axis">{"".join(ticks)}</div><div class="rg-now"></div></div>'

        def mix(t: Dict[str, Any]) -> str:
            days = t.get("days") or []
            n = len(days) or 1
            counts = {p: 0 for p in _RG_ORDER}
            for _, p in days:
                if p in counts:
                    counts[p] += 1
            items = "".join(
                f'<span class="mk-note"><i class="rg-sq rg-{_RG_CLS[p]}"></i>{_esc(_phase_label_vi(p).capitalize())} '
                f'<b class="quant-num">{counts[p] / n * 100:.0f}%</b></span>'
                for p in _RG_ORDER
            )
            return f'<div class="st-label mk-sub">Days in each regime · last {len(days)} days</div><div class="mk-notes">{items}</div>'

        tab_syms = [str(t["symbol"]) for t in timelines]
        ftabs = f'<button type="button" class="mk-ftab on" data-a="ALL" onclick="{_mk_switch_js("ALL")}">All assets</button>' + "".join(
            f'<button type="button" class="mk-ftab" data-a="{_esc(s_)}" onclick="{_mk_switch_js(_esc(s_))}">{_esc(s_)} '
            f'<span>{("&lt;1" if 0 < shares.get(s_, 0) < 0.5 else f"{shares.get(s_, 0):.0f}")}%</span></button>'
            for s_ in tab_syms
        )
        panes = [
            f'<div class="mk-pane" data-a="ALL"><div class="rg-chips">{"".join(chips)}</div>'
            f'<div class="rg-grid">{"".join(row(t) for t in timelines)}{trades_row}{axis}</div></div>'
        ]
        assets_by = {str(x.get("asset")): x for x in (result.get("assets") or []) if isinstance(x, dict)}
        trade_pts = [
            (float(x["close_time"]), float(x["realized_pnl"])) for x in series
            if _is_finite_number(x.get("close_time")) and _is_finite_number(x.get("realized_pnl"))
        ]
        for t in timelines:
            panes.append(
                f'<div class="mk-pane" data-a="{_esc(str(t["symbol"]))}" hidden>'
                f"{_regime_asset_view(t, start, span, trade_pts, assets_by.get(str(t['symbol'])))}</div>"
            )
        legend = "".join(
            f'<span><i class="rg-sq rg-{_RG_CLS[p]}"></i>{_esc(_phase_label_vi(p).capitalize())}</span>' for p in _RG_ORDER
        ) + '<span><i class="rg-sq rg-na"></i>Unclassified / no data</span><span><i class="rg-tk rg-win"></i>Win</span><span><i class="rg-tk rg-loss"></i>Loss</span>'
        parts.append(
            '<div class="mk-card rg-card"><div class="mk-head"><span class="st-label" title="Each pair gets its own hourly phase '
            '(trend from the EMA50/EMA200 gap, volatility from the ATR percentile), shown here as the majority phase of each day.">'
            f'Market regime by asset · {span} days</span><span class="mk-ftabs">{ftabs}</span></div>'
            + "".join(panes)
            + f'<div class="mk-legend rg-legend">{legend}</div></div>'
        )

    # Results by phase (+ cost sensitivity when the live analysis ran it)
    by_phase = {str(r.get("phase")): r for r in breakdown}
    untested = [str(p) for p in (strategy.get("untested_phases") or [])]
    rows = []
    top = max((abs(float(r.get("total_pnl") or 0.0)) for r in breakdown), default=0.0) or 1.0
    for p in _RG_ORDER:
        r = by_phase.get(p)
        if r and int(r.get("trades") or 0) > 0:
            pnl = float(r.get("total_pnl") or 0.0)
            conf = _phase_confidence_vi(r.get("trades"))
            rows.append(
                f'<div class="rg-prow"><b>{_esc(_phase_label_vi(p).capitalize())}</b>'
                f'<span class="pv-num mk-r">{_int_text(r.get("trades"))}</span>'
                f'<span class="pv-num mk-r">{_pct(r.get("win_rate"), 0)}</span>'
                f'<span class="pv-abar"><span style="width:{abs(pnl) / top * 100:.1f}%;background:{"#17a565" if pnl >= 0 else "#d04a3c"}"></span></span>'
                f'<span class="pv-num mk-r pv-v-{"good" if pnl > 0 else ("bad" if pnl < 0 else "")}">{pnl:+,.0f}</span>'
                f'<span class="mk-r"><span class="st-chip {"st-chip-good" if conf == PHASE_CONFIDENCE_ENOUGH_VI else "st-chip-flat"} pv-state">{_esc(conf.capitalize())}</span></span></div>'
            )
        else:
            rows.append(
                f'<div class="rg-prow rg-prow-na"><b>{_esc(_phase_label_vi(p).capitalize())}</b>'
                '<span class="pv-num mk-r">0</span><span class="pv-num mk-r">—</span><span class="pv-muted">no trades</span>'
                '<span class="pv-num mk-r">—</span>'
                f'<span class="mk-r"><span class="st-chip st-chip-flat pv-state">{"Untested" if p in untested or not r else "No trades"}</span></span></div>'
            )
    table = (
        '<div class="rg-prow rg-phead"><span>Market phase</span><span class="mk-r">Trades</span><span class="mk-r">Win</span>'
        '<span>Net PnL</span><span class="mk-r">USDT</span><span class="mk-r">Reliability</span></div>' + "".join(rows)
    )
    lab = _scenario_lab(result)
    exec_rows = []
    for sc in lab.get("scenarios") or []:
        if sc.get("family") != "EXECUTION":
            continue
        band = sc.get("total_pnl") or {}
        sim = sc.get("status") == "SIMULATED" and band.get("p50") is not None
        exec_rows.append(
            f'<div class="quant-audit-row"><div class="quant-audit-tag">[{_esc(str(sc.get("name") or ""))}]</div>'
            + (f'<div class="quant-audit-main"><span class="ev-chunk">Median <b class="quant-num">{_num(band.get("p50"), 0)}</b></span>'
               f'<span class="ev-chunk">P05–P95 <b class="quant-num">{_num(band.get("p05"), 0)} … {_num(band.get("p95"), 0)}</b></span></div>'
               if sim else '<div class="quant-audit-main"><span class="ev-chunk pv-muted">not simulated</span></div>')
            + f'<div class="quant-audit-end"><span class="ev-pill ev-pill-flat">{_esc(str(sc.get("status") or "").capitalize())}</span></div></div>'
        )
    inner = table
    if exec_rows:
        inner += f'<div class="st-label mk-sub">Cost sensitivity · net PnL (USDT)</div><div class="quant-audit-rows">{"".join(exec_rows)}</div>'
    limitations = [str(x) for x in (compat.get("limitations") or [])]
    if limitations:
        inner += f'<div class="gc-note mk-foot">{_esc("; ".join(limitations))}</div>'
    tags = "6 phases · trades · win rate · net PnL · reliability" + (f" · cost sensitivity ({len(exec_rows)} scenarios)" if exec_rows else "")
    parts.append(_collapse_toggle("Show results by phase", "Hide results by phase", tags, f'<div class="rg-ptable">{inner}</div>'))
    return _section("Market compatibility", "".join(parts), anchor="market-compatibility")


def _pair_lookup(result: Dict[str, Any]) -> Dict[Tuple[int, float], str]:
    """(close time ms, pnl) -> pair, from the stored ledger (`_ledger`)."""
    out: Dict[Tuple[int, float], str] = {}
    for r in result.get("_ledger") or []:
        if isinstance(r, dict) and r.get("pair") and _is_finite_number(r.get("close_ms")) and _is_finite_number(r.get("pnl")):
            out[(int(float(r["close_ms"])), round(float(r["pnl"]), 4))] = str(r["pair"])
    return out


_RB_PER = 4
_RB_ITEM = re.compile(r'^<div class="(rb-row|rb-group)"')


def _paged_rows(items: Sequence[str], per: int, unit: str, box: str) -> str:
    """Bar rows, `per` at a time: the first page visible, the rest `hidden`,
    and a pager under them (same runtime script as the ledger). A list that
    fits on one page is left exactly as it was."""
    if len(items) <= per:
        return f'<div class="rb-rows">{"".join(items)}</div>'
    rows = [
        _RB_ITEM.sub(lambda m: f'<div class="{m.group(1)}" data-r="x"' + (" hidden" if i >= per else ""), item, count=1)
        for i, item in enumerate(items)
    ]
    pages = (len(items) + per - 1) // per
    return (
        f'<div class="lg-box rb-box" data-box="{_esc(box)}" data-unit="{_esc(unit)}" data-per="{per}" data-f="a" data-b="all" data-p="0">'
        f'<div class="rb-rows lg-body">{"".join(rows)}</div>'
        f'<div class="lg-foot"><span class="pv-num lg-info">1–{per} of {len(items)} {_esc(unit)}</span>'
        f'<span class="lg-pager">{_lg_pager_html(0, pages)}</span></div></div>'
    )


def _pv_card(title: str, badge: Tuple[str, str], tiles: Sequence[Tuple[str, str, str, str]], label: str,
             label_tip: str, rows_html: Any, foot: str = "", notice: str = "", unit: str = "rows",
             plain: str = "") -> str:
    """Card layout shared by the Robustness / Open positions panes (redesign
    mockup): title + verdict chip, three tiles (label, value, sub, tone),
    a section label and bar rows -- `_RB_PER` per page when `rows_html` is a
    list of rows (a string is shown whole)."""
    if isinstance(rows_html, (list, tuple)):
        # Robustness pair: 2 windows (4 rows) beside 4 scenarios; open
        # positions pair: up to 4 metrics shown whole, paged only beyond --
        # the two cards of a pair stay level page by page.
        per = {"windows": 2}.get(unit, _RB_PER)
        rows_block = _paged_rows(rows_html, per, unit,
                                 re.sub(r"[^a-z]+", "-", title.lower()).strip("-"))
    else:
        rows_block = f'<div class="rb-rows">{rows_html}</div>'
    tiles_html = "".join(
        f'<div class="pv-tile rb-tile"><div class="pv-tile-l">{_esc(l)}</div><div class="pv-tile-v pv-v-{t}">{_esc(v)}</div>'
        f'<div class="pv-tile-s">{_esc(s)}</div></div>'
        for l, v, s, t in tiles
    )
    return (
        f'<div class="gc-head"><span class="mc-title"{f' title="{_esc(title)}"' if plain else ""}>{_esc(plain or title)}</span>'
        f'<span class="st-chip st-chip-{badge[1]}">{_esc(badge[0])}</span></div>'
        f'<div class="rb-tiles">{tiles_html}</div>{notice}'
        f'<div class="st-label mk-sub" title="{_esc(label_tip)}">{_esc(label)}</div>'
        f'{rows_block}'
        + (f'<div class="gc-note mk-foot">{foot}</div>' if foot else "")
    )


def _rb_row(label: str, sub: str, fill_pct: float, fill_cls: str, value: str, value_tone: str = "", chip: Tuple[str, str] = ("", "")) -> str:
    return (
        f'<div class="rb-row"><span class="rb-l"><b>{_esc(label)}</b><span>{_esc(sub)}</span></span>'
        f'<span class="rb-bar"><span class="{fill_cls}" style="width:{max(0.0, min(100.0, fill_pct)):.1f}%"></span></span>'
        f'<b class="rb-v pv-v-{value_tone}">{_esc(value)}</b>'
        + '<span class="rb-c">' + (f'<span class="ev-pill ev-pill-{chip[1]}">{_esc(chip[0])}</span>' if chip[0] else "") + "</span></div>"
    )


def _holdout_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """The engine's holdout validation: from the live dossier when present,
    else run with the SAME function (report/qc/reporting/validation.py
    `build_out_of_sample_validation`) on the saved closed-trade series -- it
    only needs each trade's close time and realized PnL."""
    v = _insights(result).get("validation")
    if isinstance(v, dict) and v:
        return v
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    series = [x for x in (evidence.get("closed_trade_series") or []) if isinstance(x, dict)
              and _is_finite_number(x.get("close_time")) and _is_finite_number(x.get("realized_pnl"))]
    if not series:
        return {}
    try:
        from types import SimpleNamespace
        from Agent.backend.report.qc.reporting.validation import build_out_of_sample_validation

        ledger = [SimpleNamespace(close_time=int(float(x["close_time"])), realized_pnl=float(x["realized_pnl"])) for x in series]
        perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
        bot = SimpleNamespace(
            trade_ledger_summary=ledger,
            reconciliation=SimpleNamespace(ledger_truncated=bool(perf.get("ledger_truncated"))),
        )
        return build_out_of_sample_validation(bot).model_dump(mode="json")
    except Exception:  # noqa: BLE001 - optional section
        logger.warning("holdout validation could not be computed", exc_info=True)
        return {}


_GRADE_WORD = {"STABLE": ("Stable", "good"), "DEGRADED": ("Degraded", "warn"),
               "SEVERELY_DEGRADED": ("Severely degraded", "bad"), "UNRELIABLE": ("Unreliable", "flat"),
               "UNKNOWN": ("Unknown", "flat")}


def _render_validation_section(result: Dict[str, Any]) -> str:
    """Did what the early trades showed keep being true later? Laid out like
    the redesign mockup: grade chip, three tiles, earlier -> later profit
    factor per window with the later/earlier ratio."""
    v = _holdout_data(result)
    if not v:
        return ""
    if v.get("status") != "EVALUATED":
        reasons = [str(r) for r in (v.get("limitations") or [])]
        if not reasons:
            return ""
        return _section("Out-of-sample validation",
                        '<div class="gc-head"><span class="mc-title">Out-of-sample validation</span></div>'
                        f'<p class="gc-note mk-foot">{_esc("; ".join(reasons))}</p>', anchor="holdout")
    folds = [f for f in (v.get("folds") or []) if isinstance(f, dict)]
    grade, tone = _GRADE_WORD.get(str(v.get("stability_grade") or "UNKNOWN"), ("Unknown", "flat"))
    later_pfs = [(f.get("fold_index", 0), (f.get("out_of_sample") or {}).get("profit_factor")) for f in folds]
    worst = min(((i, pf) for i, pf in later_pfs if _is_finite_number(pf)), key=lambda x: x[1], default=None)
    med = v.get("median_profit_factor_ratio")
    tiles = [
        ("Profitable OOS windows", f"{_int_text(v.get('oos_profitable_folds'))} / {_int_text(v.get('folds_evaluated'))}", "out-of-sample", ""),
        ("Worst OOS PF", _num(worst[1], 2) if worst else "—", f"Window {int(worst[0]) + 1}" if worst else "", "bad" if worst and worst[1] < 1 else "good"),
        ("Median OOS/IS PF", f"×{_num(med, 2)}" if _is_finite_number(med) else "—", "OOS PF ÷ IS PF", "good" if _is_finite_number(med) and med >= 0.8 else "bad"),
    ]
    top = max([float(pf) for f in folds for pf in ((f.get("in_sample") or {}).get("profit_factor"), (f.get("out_of_sample") or {}).get("profit_factor")) if _is_finite_number(pf)] or [1.0])
    rows = []
    for f in folds:
        i = int(f.get("fold_index", 0)) + 1
        ins, oos = f.get("in_sample") or {}, f.get("out_of_sample") or {}
        ipf, opf, ratio = ins.get("profit_factor"), oos.get("profit_factor"), f.get("profit_factor_ratio")
        rows.append('<div class="rb-group">' + _rb_row(
            f"Window {i} · IS", f"{_int_text(ins.get('trades'))} trades",
            (float(ipf) / top * 100) if _is_finite_number(ipf) else 0, "rb-f-grey", _num(ipf, 2) if _is_finite_number(ipf) else "—")
            + _rb_row(
            f"Window {i} · OOS", f"{_int_text(oos.get('trades'))} trades",
            (float(opf) / top * 100) if _is_finite_number(opf) else 0,
            "rb-f-good" if _is_finite_number(opf) and opf >= 1 else "rb-f-bad",
            _num(opf, 2) if _is_finite_number(opf) else "no loss", "good" if _is_finite_number(opf) and opf >= 1 else ("bad" if _is_finite_number(opf) else ""),
            (f"×{_num(ratio, 2)}", "good" if ratio >= 0.8 else "bad") if _is_finite_number(ratio) else ("", "")) + "</div>")
    grades: Dict[str, int] = {}
    for f in folds:
        g = _GRADE_WORD.get(str(f.get("reliability")), (str(f.get("reliability")), ""))[0]
        grades[g] = grades.get(g, 0) + 1
    sizes = [int((f.get("out_of_sample") or {}).get("trades") or 0) for f in folds]
    size_txt = (f"{min(sizes)}" if min(sizes) == max(sizes) else f"{min(sizes)}–{max(sizes)}") if sizes else ""
    foot = ("Per window: " + _esc(" · ".join(f"{n} {g.lower()}" for g, n in sorted(grades.items(), key=lambda x: -x[1])))
            + (f" · {size_txt} trades each" if size_txt else ""))
    body = _pv_card("Out-of-sample validation", (grade, tone), tiles, "Profit factor · in-sample (IS) → out-of-sample (OOS)",
                    "Walk-forward: each window compares the profit factor on all trades before a split (in-sample) with the next block of trades (out-of-sample).",
                    rows, foot, unit="windows")
    return _section("Out-of-sample validation", body, anchor="holdout")


def _render_scenario_lab(result: Dict[str, Any]) -> str:
    """Named what-ifs (live analysis only), laid out like the redesign
    mockup: tiles, then each scenario's median total PnL with its P05-P95
    range and chance of loss."""
    lab = _scenario_lab(result)
    scenarios = [s for s in (lab.get("scenarios") or []) if isinstance(s, dict) and s.get("family") != "EXECUTION"]
    if not scenarios:
        return ""
    sim = [s for s in scenarios if s.get("status") == "SIMULATED" and (s.get("total_pnl") or {}).get("p50") is not None]
    untested = [_phase_label_vi(u) for u in (lab.get("untested_conditions") or [])]

    def label_of(s: Dict[str, Any]) -> str:
        name = str(s.get("name") or "")
        return _phase_label_vi(name).capitalize() if s.get("family") == "REGIME" else name

    def k(v: Any) -> str:
        v = float(v)
        return f"{v / 1000:,.1f}k" if abs(v) >= 1000 else f"{v:,.0f}"

    def ploss(v: Any) -> str:
        v = float(v)
        return ">99%" if v > 99 else ("<1%" if 0 < v < 1 else f"{v:.0f}%")

    worst = min(sim, key=lambda s: float(s["total_pnl"]["p50"]), default=None)
    riskiest = max((s for s in sim if _is_finite_number(s.get("probability_of_loss_pct"))), key=lambda s: float(s["probability_of_loss_pct"]), default=None)
    tiles = [
        ("Scenarios run", str(len(sim)), f"{len(untested)} untested" if untested else "all simulated", ""),
        ("Worst median PnL", f"{float(worst['total_pnl']['p50']):+,.0f}" if worst else "—", label_of(worst) if worst else "", "bad" if worst and float(worst["total_pnl"]["p50"]) < 0 else "good"),
        ("Highest P(loss)", ploss(riskiest["probability_of_loss_pct"]) if riskiest else "—", label_of(riskiest) if riskiest else "", "warn" if riskiest else ""),
    ]
    top = max([abs(float(s["total_pnl"]["p50"])) for s in sim] or [1.0])
    rows = []
    for s in scenarios:
        band = s.get("total_pnl") or {}
        ok = s in sim
        med = float(band["p50"]) if ok else None
        loss = s.get("probability_of_loss_pct")
        sub = f"{_int_text(s.get('sample_size'))} tr" + (f" · {k(band['p05'])}…{k(band['p95'])}" if ok and _is_finite_number(band.get("p05")) and _is_finite_number(band.get("p95")) else (" · not simulated" if not ok else ""))
        lt = "good" if _is_finite_number(loss) and loss < 5 else ("warn" if _is_finite_number(loss) and loss < 25 else "bad")
        rows.append(_rb_row(label_of(s), sub, (abs(med) / top * 100) if med is not None else 0, "rb-f-good" if (med or 0) >= 0 else "rb-f-bad",
                            f"{med:+,.0f}" if med is not None else "—", "good" if (med or 0) > 0 else ("bad" if med is not None and med < 0 else ""),
                            (ploss(loss), lt) if _is_finite_number(loss) else ("", "")))
    foot = ("Not simulated: " + "".join(f'<span class="st-chip st-chip-warn pv-state">{_esc(u.capitalize())}</span>' for u in untested)) if untested else ""
    body = _pv_card("Scenario analysis", ("Simulated", "flat"), tiles, "Median total PnL · P(loss)",
                    "Bar = median simulated total PnL (USDT) relative to the largest one; red = loss. Sub-line: P05 … P95 range.",
                    rows, foot, unit="scenarios")
    return _section("Scenario analysis", body, anchor="scenario-lab")


def _render_open_positions_audit(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence") or {}
    perf = evidence.get("performance") or {}
    open_pos = perf.get("open_positions")
    open_loss = perf.get("open_loss")
    loss_pct = perf.get("open_loss_to_capital_pct")
    booked, marked = perf.get("profit_factor"), perf.get("marked_profit_factor")
    skew, kurt = perf.get("pnl_skew"), perf.get("pnl_kurtosis")
    if all(v is None for v in (open_pos, open_loss, marked, skew, kurt)):
        return ""
    hidden = _is_finite_number(booked) and _is_finite_number(marked) and float(booked) >= 1.0 > float(marked)
    badge = ("Hidden loss", "bad") if hidden else ("No hidden loss", "good")
    assets = [a for a in (result.get("assets") or []) if isinstance(a, dict) and int(a.get("open_positions") or 0) > 0]
    capital = compute_loss_profile(evidence) or {}
    cap = capital.get("capital") if isinstance(capital, dict) else None
    # Already a percentage -- see `_render_quick_risk_strip`.
    lp = abs(float(loss_pct)) if _is_finite_number(loss_pct) else None
    tiles = [
        # The four largest, then a count: a many-pair book listed every
        # symbol here and the tile grew to four lines.
        ("Open positions", _int_text(open_pos), (" · ".join(
            f"{a.get('asset')} {_int_text(a.get('open_positions'))}"
            for a in sorted(assets, key=lambda a: -int(a.get("open_positions") or 0))[:4])
            + (f" · +{len(assets) - 4} more" if len(assets) > 4 else "")) or "none open", ""),
        ("Unrealized loss", f"{-abs(float(open_loss)):+,.0f}" if _is_finite_number(open_loss) and float(open_loss) else "0", "USDT", "bad" if _is_finite_number(open_loss) and float(open_loss) else ""),
        ("Unrealized loss / capital", _pct(lp, 1) if lp is not None else "0.0%", f"of {float(cap):,.0f}" if _is_finite_number(cap) else "", "bad" if lp and lp >= 5 else "good"),
    ]
    pf_top = max([float(x) for x in (booked, marked) if _is_finite_number(x)] + [3.0])
    rows = []
    if _is_finite_number(booked):
        rows.append(_rb_row("Realized PF", "closed trades only", float(booked) / pf_top * 100, "rb-f-good" if float(booked) >= 1.5 else ("rb-f-warn" if float(booked) >= 1 else "rb-f-bad"), _num(booked, 2), "good" if float(booked) >= 1.5 else ("warn" if float(booked) >= 1 else "bad")))
    if not _is_finite_number(marked) and _is_finite_number(booked) and _is_finite_number(open_pos) and int(float(open_pos)) == 0:
        # Nothing is open, so marking to market changes nothing: marked PF is
        # the booked PF by definition.
        rows.append(_rb_row("Mark-to-market PF", "0 open positions", float(booked) / pf_top * 100, "rb-f-good" if float(booked) >= 1 else "rb-f-bad",
                            _num(booked, 2), "good" if float(booked) >= 1 else "bad", ("±0%", "good")))
    if _is_finite_number(marked):
        diff = (float(marked) / float(booked) - 1) * 100 if _is_finite_number(booked) and float(booked) else None
        rows.append(_rb_row("Mark-to-market PF", "open positions closed now", float(marked) / pf_top * 100, "rb-f-good" if not hidden else "rb-f-bad",
                            _num(marked, 2), "bad" if hidden else "good", (f"{diff:+.0f}%", "bad" if hidden else "good") if diff is not None else ("", "")))
    if _is_finite_number(skew):
        sk = float(skew)
        rows.append(_rb_row("PnL skewness", "alert below −0.5", min(100.0, abs(sk) / 3 * 100), "rb-f-good" if sk >= -0.5 else "rb-f-bad",
                            _num(sk, 2), "bad" if sk < -0.5 else "", ("OK", "good") if sk >= -0.5 else ("Alert", "bad")))
    if _is_finite_number(kurt):
        ku = float(kurt)
        rows.append(_rb_row("PnL kurtosis", "normal ≈ 3", min(100.0, ku / 10 * 100), "rb-f-good" if ku <= 6 else "rb-f-warn",
                            _num(ku, 2), "warn" if ku > 6 else "", ("OK", "good") if ku <= 6 else ("Fat tails", "warn")))
    if not rows and not (_is_finite_number(open_pos) and float(open_pos) > 0):
        return ""
    notice = ""
    if hidden:
        notice = _note_chip(f"Hidden loss: PF {_num(booked, 2)} → {_num(marked, 2)} with open trades",
                            "Hidden loss-holding: profit factor on the closed book is "
                            f"{_num(booked, 2)}, but with open positions marked to market it drops to {_num(marked, 2)}.",
                            "danger")
    body = _pv_card("Open-position audit", badge, tiles, "Mark-to-market & distribution shape",
                    "Marked PF = the result if every open position were closed now. Skewness below −0.5 = rare large losses; kurtosis far above 3 = fat tails.",
                    rows, notice=notice, unit="metrics")
    return _section("Open-position audit & return distribution", body, anchor="vi-the-mo")


def _render_statistical_inference(result: Dict[str, Any]) -> str:
    mc = result.get("mc")
    if not isinstance(mc, dict) or not mc:
        return ""
    keys = ("probabilistic_sharpe", "deflated_sharpe", "min_track_record_trades", "sharpe_per_trade")
    if not any(_is_finite_number(mc.get(k)) for k in keys) and not mc.get("inference_notes"):
        return ""
    reliable = mc.get("inference_reliable")
    psr, dsr = _ratio_to_pct(mc.get("probabilistic_sharpe")), _ratio_to_pct(mc.get("deflated_sharpe"))
    mintrl, sample, trials = mc.get("min_track_record_trades"), mc.get("sample_size"), mc.get("selection_trials")
    passes = [x for x in (psr is not None and psr >= 95, dsr is not None and dsr >= 95 if dsr is not None else None,
                          (float(sample) >= float(mintrl)) if _is_finite_number(mintrl) and _is_finite_number(sample) else None) if x is not None]
    edge = bool(passes) and all(passes)
    tiles = [
        ("Verdict", "Real edge" if edge else "Not proven", "not luck" if edge else "could still be luck", "good" if edge else "warn"),
        ("Sample size", _int_text(sample), "trades", ""),
        ("Number of trials", _int_text(trials) if _is_finite_number(trials) else "—", "candidates" if _is_finite_number(trials) else "not known", ""),
    ]
    spt = mc.get("sharpe_per_trade")
    rows = []
    if _is_finite_number(spt):
        rows.append(_rb_row("Sharpe per trade", "mean ÷ st. dev.", min(100.0, abs(float(spt)) * 100), "rb-f-good" if float(spt) > 0 else "rb-f-bad",
                            f"{float(spt):+.2f}", "good" if float(spt) > 0 else "bad"))
    if psr is not None:
        rows.append(_rb_row("Probabilistic Sharpe", "PSR · target 95%", psr, "rb-f-good" if psr >= 95 else "rb-f-warn",
                            ">99.9%" if psr > 99.9 else _pct(psr, 1), "good" if psr >= 95 else "warn", ("Pass", "good") if psr >= 95 else ("Fail", "bad")))
    rows.append(_rb_row("Deflated Sharpe", f"DSR · after {_int_text(trials)} trials" if _is_finite_number(trials) else "DSR · trial count not known",
                        dsr or 0, "rb-f-good" if dsr is not None and dsr >= 95 else "rb-f-warn",
                        _pct(dsr, 1) if dsr is not None else "—", "good" if dsr is not None and dsr >= 95 else "",
                        (("Pass", "good") if dsr >= 95 else ("Fail", "bad")) if dsr is not None else ("n/a", "flat")))
    if _is_finite_number(mintrl) and _is_finite_number(sample):
        ok = float(sample) >= float(mintrl)
        rows.append(_rb_row("MinTRL", "needed vs. used", min(100.0, float(mintrl) / max(float(sample), 1) * 100), "rb-f-grey",
                            f"{float(mintrl):,.0f} / {float(sample):,.0f}", "" , ("Pass", "good") if ok else ("Fail", "bad")))
    notice = ""
    if reliable is False:
        notes = [n for n in (mc.get("inference_notes") or []) if isinstance(n, str) and n.strip()]
        short = notes[0].split(":")[0].strip().rstrip(".") if notes else "the approximation does not hold for this sample"
        notice = (f'<div class="rb-warn" title="{_esc("; ".join(notes))}"><b>Not reliable here</b> · {_esc(short)} · '
                  'read as a reference only</div>')
    body = _pv_card("Statistical inference", ("Reliable", "good") if reliable is not False else ("Not reliable", "warn"), tiles,
                    "Significance tests", "PSR corrects the Sharpe ratio for skew and fat tails; DSR also for how many candidates it was picked from; MinTRL = trades needed for 95% confidence.",
                    rows, notice=notice, unit="metrics")
    return _section("Statistical inference", body, anchor="suy-luan")


def _render_tab_market(result: Dict[str, Any]) -> str:
    if result.get("status") == "LIMITED":
        return _render_tab_market_limited(result)
    sections = [
        _render_market_tab_answer(result),
        _render_dominant_market_card(result),
        _render_market_compatibility(result),
        _render_market_coverage(result),
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
        f'Nâng cấp gói để mở khóa'
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

    # Text-only tab labels (project owner asked for no icons). A locked tab
    # still carries `tab-label-locked`, and its panel still opens on the
    # explicit "withheld" notice from `_render_locked_panel`.
    market_class = "tab-label label-market" + (" tab-label-locked" if "panel-market" in hidden else "")
    trades_class = "tab-label label-trades" + (" tab-label-locked" if "panel-trades" in hidden else "")
    # A tab with nothing public to show keeps its element (the contract
    # above) but not its label.
    market_style = ' hidden style="display:none"' if not tab2_content.strip() else ""
    trades_style = ' hidden style="display:none"' if not tab3_content.strip() else ""
    if not tab2_content.strip():
        market_class += " tab-label-empty"
    if not tab3_content.strip():
        trades_class += " tab-label-empty"

    return (
        f'<div class="tabs-control-wrapper"{tab_label_attr}>'
        '<input type="radio" name="main_tabs" id="tab-nav-report" class="tab-nav-radio" checked style="display:none!important;position:absolute!important;opacity:0!important;pointer-events:none!important;">'
        '<input type="radio" name="main_tabs" id="tab-nav-market" class="tab-nav-radio" style="display:none!important;position:absolute!important;opacity:0!important;pointer-events:none!important;">'
        '<input type="radio" name="main_tabs" id="tab-nav-trades" class="tab-nav-radio" style="display:none!important;position:absolute!important;opacity:0!important;pointer-events:none!important;">'
        '<div class="tabs-header-container">'
        '<div class="tabs-nav-bar" role="tablist">'
        '<label class="tab-label label-report" for="tab-nav-report" id="label-tab-report" tabindex="0">'
        '<span class="tab-title">Summary</span>'
        "</label>"
        f'<label class="{market_class}" for="tab-nav-market" id="label-tab-market" tabindex="0"{market_style}>'
        '<span class="tab-title">Markets</span>'
        "</label>"
        f'<label class="{trades_class}" for="tab-nav-trades" id="label-tab-trades" tabindex="0"{trades_style}>'
        '<span class="tab-title">Trades &amp; positions</span>'
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
    r'<section class="card[^"]*" id="([^"]+)" aria-label="([^"]*)"'
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
        '<span class="theme-icon theme-icon-light"><span class="ic-mask ic-sun"></span> Light</span>'
        '<span class="theme-icon theme-icon-dark"><span class="ic-mask ic-moon"></span> Dark</span>'
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
    --amber: #EAB308;
    --amber-bg: rgba(234, 179, 8, 0.12);
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
  --amber: #EAB308;
  --amber-bg: rgba(234, 179, 8, 0.12);
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
  --amber: #CA8A04;
  --amber-bg: #FEF9C3;
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
/* Score tiles + quick risk strip, global to every tab -- see
   _render_header's key_metrics_block. No outer card of its own (project
   owner: "bỏ layout tổng"): the score tiles and the strip each already
   carry their own frame, a third one around both was just nesting. */
.report-key-metrics {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 0 24px 0 !important;
}
.report-key-metrics .report-hero-scores {
  margin-bottom: 0 !important;
}
.report-key-metrics .quick-risk-strip {
  margin: 14px 0 0 0 !important;
}

/* Hero score tile with a half-circle gauge on the left, label + value on
   the right (see _gauge_svg / _stat_tile(with_gauge=True)). */
.report-hero-scores .stat-tile-hero:has(.stat-gauge) {
  flex-direction: row !important;
  align-items: center !important;
  justify-content: flex-start !important;
  gap: 18px !important;
  padding: 18px 22px !important;
}
.stat-gauge {
  width: 92px;
  height: auto;
  flex-shrink: 0;
  overflow: visible;
}
.stat-gauge .gauge-track {
  fill: none;
  stroke: var(--track, #eef0f3);
  stroke-width: 10;
  stroke-linecap: round;
}
.stat-gauge .gauge-arc {
  fill: none;
  stroke: var(--tile-accent, var(--s1, #2563eb));
  stroke-width: 10;
  stroke-linecap: round;
}
.report-hero-scores .stat-tile-hero .stat-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1 1 auto;
  min-width: 0;
}
.report-hero-scores .stat-tile-hero .stat-body .stat-label {
  margin-top: 0 !important;
}
.report-hero-scores .stat-tile-hero .stat-body .stat-value {
  font-size: 34px !important;
}
.report-hero-scores .stat-tile-hero .stat-unit {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink-3, #94a3b8);
  margin-left: 2px;
  letter-spacing: 0;
}

/* Verdict chip on the bot-name row, right-aligned (see _verdict_chip_html).
   The solid .verdict-badge in the meta row stays in the markup -- the SPA
   and the tokens.css color tests read it -- but is not shown twice. */
.report-hero-top.has-verdict-chip {
  display: flex !important;
  align-items: flex-start !important;
  justify-content: space-between !important;
  gap: 16px !important;
}
.report-hero-top.has-verdict-chip .report-hero-identity {
  width: auto !important;
  flex: 1 1 auto !important;
  min-width: 0 !important;
}
.report-hero-top.has-verdict-chip .report-hero-meta .verdict-badge {
  display: none !important;
}
.report-verdict-chip {
  flex-shrink: 0;
  padding: 8px 14px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--line);
  background: var(--panel-2);
  white-space: nowrap;
}
.report-verdict-chip.tone-danger {
  border-color: rgba(244, 63, 94, 0.35);
  background: rgba(244, 63, 94, 0.08);
}
.report-verdict-chip.tone-warning {
  border-color: rgba(234, 179, 8, 0.35);
  background: rgba(234, 179, 8, 0.08);
}
.report-verdict-chip.tone-success {
  border-color: rgba(16, 185, 129, 0.35);
  background: rgba(16, 185, 129, 0.08);
}
/* The axis words ("DRAWDOWN:", "QUALITY:", "·") in the plain ink colour;
   only the values (HIGH/WEAK/LOW/GOOD, .verdict-val-badge) keep their tone
   colour. `[class*="tone-"]` lifts specificity above `.tone-* .verdict-chip`
   and its light-theme variant, which sit LATER in this stylesheet. */
.report-verdict-chip[class*="tone-"] .verdict-chip,
:root[data-theme="light"] .report-verdict-chip[class*="tone-"] .verdict-chip {
  color: var(--ink);
}
@media (max-width: 640px) {
  .report-hero-top.has-verdict-chip {
    flex-direction: column !important;
  }
  .report-verdict-chip {
    white-space: normal;
  }
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
  border-radius: var(--radius-md, 12px) !important;
  padding: 22px 26px !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  box-shadow: var(--card-shadow, 0 4px 16px -2px rgba(0, 0, 0, 0.15)) !important;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
}
:root[data-theme="light"] .report-hero-scores .stat-tile-hero {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
}
.report-hero-scores .stat-tile-hero:hover {
  border-color: var(--tile-accent, var(--line)) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px -2px rgba(0, 0, 0, 0.25), 0 0 15px rgba(59, 130, 246, 0.15) !important;
}
:root[data-theme="light"] .report-hero-scores .stat-tile-hero:hover {
  border-color: var(--tile-accent, #94a3b8) !important;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08) !important;
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
  border-radius: var(--radius-md, 12px) !important;
  padding: 18px 24px !important;
  color: var(--ink) !important;
  font-size: 14px !important;
  line-height: 1.65 !important;
  margin: 0 !important;
  box-shadow: var(--card-shadow, 0 4px 16px -2px rgba(0, 0, 0, 0.1)) !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.notice-danger:hover {
  border-color: #f43f5e !important;
  box-shadow: 0 4px 18px rgba(244, 63, 94, 0.15) !important;
}
.notice-danger strong {
  color: var(--down, #F43F5E) !important;
  font-weight: 700 !important;
}
:root[data-theme="light"] .notice-danger {
  background: #FFF1F2 !important;
  border: 1px solid #FDA4AF !important;
  color: #4C0519 !important;
  font-size: 14.5px !important;
  line-height: 1.65 !important;
  font-weight: 500 !important;
}
:root[data-theme="light"] .notice-danger:hover {
  border-color: #E11D48 !important;
  box-shadow: 0 4px 16px rgba(225, 29, 72, 0.12) !important;
}
:root[data-theme="light"] .notice-danger strong {
  color: #881337 !important;
  font-weight: 800 !important;
}
:root[data-theme="light"] .notice-warning {
  background: #FFFBEB !important;
  border: 1px solid #FDE68A !important;
  color: #78350F !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
:root[data-theme="light"] .notice-warning:hover {
  border-color: #CA8A04 !important;
  box-shadow: 0 4px 16px rgba(217, 119, 6, 0.12) !important;
}
:root[data-theme="light"] .notice-warning strong {
  color: #B45309 !important;
}

/* Methodology Framework (Cơ sở phương pháp luận định lượng) */
.verdict-basis {
  background: var(--panel-2) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius-md, 12px) !important;
  padding: 12px 18px !important;
  margin: 0 !important;
  display: block !important;
  box-shadow: var(--card-shadow, 0 4px 20px -2px rgba(0, 0, 0, 0.15)) !important;
  -webkit-line-clamp: unset !important;
  overflow: visible !important;
  max-width: none !important;
  transition: all 0.25s ease !important;
}
:root[data-theme="light"] .verdict-basis {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
}
.verdict-basis:hover {
  border-color: rgba(59, 130, 246, 0.5) !important;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.15) !important;
  transform: translateY(-1px) !important;
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
  background: rgba(234, 179, 8, 0.15) !important;
  color: #eab308 !important;
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
  border: 1px solid var(--line);
  background: var(--panel-2, #161f32);
  transition: all 0.2s ease;
}
:root[data-theme="light"] .conclusion-verdict-box {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
}
.conclusion-verdict-box.tone-danger {
  border-color: rgba(225, 29, 72, 0.25);
}
.conclusion-verdict-box.tone-warning {
  border-color: rgba(234, 179, 8, 0.25);
}
.conclusion-verdict-box.tone-success {
  border-color: rgba(16, 185, 129, 0.25);
}
:root[data-theme="light"] .conclusion-verdict-box.tone-danger {
  border-color: #fecdd3 !important;
}
:root[data-theme="light"] .conclusion-verdict-box.tone-warning {
  border-color: #fde68a !important;
}
:root[data-theme="light"] .conclusion-verdict-box.tone-success {
  border-color: #a7f3d0 !important;
}
.conclusion-verdict-box:hover,
.conclusion-verdict-box.tone-danger:hover {
  border-color: #e11d48 !important;
  box-shadow: 0 4px 16px rgba(225, 29, 72, 0.12) !important;
  transform: translateY(-1px);
}
.conclusion-verdict-box.tone-warning:hover {
  border-color: #eab308 !important;
  box-shadow: 0 4px 16px rgba(234, 179, 8, 0.12) !important;
  transform: translateY(-1px);
}
.conclusion-verdict-box.tone-success:hover {
  border-color: #10b981 !important;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.12) !important;
  transform: translateY(-1px);
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
  color: #eab308;
}
:root[data-theme="light"] .tone-warning .verdict-chip {
  color: #ca8a04;
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
/* Small grey uppercase section label (WHY / QUANTITATIVE EVIDENCE) --
   a label, not a heading competing with the numbers under it. */
.conclusion-sub-title {
  margin: 0;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--ink-3);
}
.conclusion-body-wrap .conclusion-section-block + .conclusion-section-block {
  margin-top: 6px;
}
/* WHY label row: label left, action pill right */
.why-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 26px;
}
.action-pill {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  background: rgba(56, 189, 248, 0.14);
  color: var(--info);
}
.action-pill.tone-danger { background: rgba(244, 63, 94, 0.14); color: var(--down); }
.action-pill.tone-warning { background: rgba(234, 179, 8, 0.14); color: var(--amber); }
:root[data-theme="light"] .action-pill { background: #eef2fe; color: #2454e0; }
:root[data-theme="light"] .action-pill.tone-danger { background: #fbeae9; color: #af3327; }
:root[data-theme="light"] .action-pill.tone-warning { background: #fef6d8; color: #ca8a04; }

/* Small "i" with a hover tooltip (same as the redesign preview) */
.info-ic {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 13px;
  height: 13px;
  margin-left: 5px;
  border-radius: 50%;
  border: 1px solid currentColor;
  opacity: 0.7;
  font-family: var(--mono);
  font-size: 8.5px;
  font-style: normal;
  font-weight: 500;
  line-height: 1;
  cursor: default;
}
.info-ic .info-tip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: 150%;
  right: -8px;
  z-index: 30;
  width: 240px;
  padding: 7px 10px;
  border-radius: 6px;
  background: #14161a;
  color: #fff;
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 400;
  line-height: 1.45;
  white-space: normal;
  text-align: left;
  transition: opacity 0.12s ease;
}
.info-ic .info-tip {
  text-transform: none;
  letter-spacing: normal;
}
.info-ic:hover,
.info-ic:focus-visible {
  opacity: 1;
}
.info-ic:hover .info-tip,
.info-ic:focus-visible .info-tip {
  visibility: hidden;
  opacity: 0;
}
/* The tip is shown by the runtime script in one body-level layer, so a
   card's overflow or a neighbouring card never cuts it off. */
#nb-float-tip { position: fixed; z-index: 2147483000; max-width: 320px; padding: 8px 11px; border-radius: 8px;
  background: #14161a; color: #fff; font-family: var(--sans, system-ui, sans-serif); font-size: 12px; font-weight: 400;
  line-height: 1.45; text-align: left; text-transform: none; letter-spacing: normal; white-space: normal;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28); pointer-events: none; display: none; }

/* Key figure chip after a WHY sentence */
.why-chip {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: 6px;
  font-family: var(--mono);
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  vertical-align: 1px;
}
.why-chip-good { background: rgba(16, 185, 129, 0.14); color: var(--up); }
.why-chip-warn { background: rgba(234, 179, 8, 0.14); color: var(--amber); }
.why-chip-bad { background: rgba(244, 63, 94, 0.14); color: var(--down); }
:root[data-theme="light"] .why-chip-good { background: #e4f5ea; color: #16794a; }
:root[data-theme="light"] .why-chip-warn { background: #fef6d8; color: #ca8a04; }
:root[data-theme="light"] .why-chip-bad { background: #fbeae9; color: #af3327; }

/* Peer comparison: 4 small cards, value + median, histogram of the group */
.peer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.peer-head-note {
  display: inline-flex;
  align-items: center;
  font-size: 11.5px;
  color: var(--ink-3);
}
:root[data-theme="light"] .peer-head-note { color: #9296a0; }
.peer-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.peer-card {
  min-width: 0;
  padding: 14px 16px 10px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.peer-card:hover {
  border-color: var(--line-2);
  box-shadow: 0 10px 22px -18px rgba(20, 22, 26, 0.35);
}
:root[data-theme="light"] .peer-card { background: #fff; border-color: #eceef1; }
:root[data-theme="light"] .peer-card:hover { border-color: #d9dce2; }
.peer-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.peer-card-label {
  font-size: 12.5px;
  color: var(--ink-3);
}
:root[data-theme="light"] .peer-card-label { color: #62666f; }
.peer-rank {
  padding: 2px 8px;
  border-radius: 999px;
  font-family: var(--mono);
  font-size: 11.5px;
  font-weight: 600;
}
.peer-rank.tone-good { background: rgba(16, 185, 129, 0.14); color: var(--up); }
.peer-rank.tone-warn { background: rgba(234, 179, 8, 0.14); color: var(--amber); }
.peer-rank.tone-bad { background: rgba(244, 63, 94, 0.14); color: var(--down); }
:root[data-theme="light"] .peer-rank.tone-good { background: #e4f5ea; color: #16794a; }
:root[data-theme="light"] .peer-rank.tone-warn { background: #fef6d8; color: #ca8a04; }
:root[data-theme="light"] .peer-rank.tone-bad { background: #fbeae9; color: #af3327; }
.peer-card-value {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 4px;
}
.peer-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.peer-median-text {
  font-size: 12px;
  color: var(--ink-3);
}
:root[data-theme="light"] .peer-median-text { color: #9296a0; }
.peer-hist {
  display: block;
  width: 100%;
  height: 62px;
  margin-top: 10px;
}
.peer-bar { fill: var(--panel-3); }
:root[data-theme="light"] .peer-bar { fill: #e4e6ea; }
.peer-bar-me.tone-good, .peer-marker.tone-good { fill: var(--up); }
.peer-bar-me.tone-warn, .peer-marker.tone-warn { fill: var(--amber); }
.peer-bar-me.tone-bad, .peer-marker.tone-bad { fill: var(--down); }
:root[data-theme="light"] .peer-bar-me.tone-good,
:root[data-theme="light"] .peer-marker.tone-good { fill: #2f9a64; }
:root[data-theme="light"] .peer-bar-me.tone-warn,
:root[data-theme="light"] .peer-marker.tone-warn { fill: #eab308; }
:root[data-theme="light"] .peer-bar-me.tone-bad,
:root[data-theme="light"] .peer-marker.tone-bad { fill: #c8473b; }
.peer-median {
  stroke: var(--ink-3);
  stroke-width: 1;
  stroke-dasharray: 2 2;
  vector-effect: non-scaling-stroke;
}
.peer-axis {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--ink-3);
}
:root[data-theme="light"] .peer-axis { color: #9296a0; }
@media (max-width: 900px) {
  .peer-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .peer-grid { grid-template-columns: minmax(0, 1fr); }
}

/* WHY -- each cause sentence with one marker, two columns */
.why-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 28px;
}
.why-grid.why-grid-single {
  grid-template-columns: minmax(0, 1fr);
}
.why-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;
}
.why-icon {
  width: 14px;
  height: 14px;
  margin-top: 3px;
  flex-shrink: 0;
  fill: none;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.why-icon.tone-good { stroke: var(--up); }
.why-icon.tone-warn { stroke: var(--amber); }
.why-icon.tone-bad { stroke: var(--down); }
:root[data-theme="light"] .why-icon.tone-good { stroke: #17a565; }
:root[data-theme="light"] .why-icon.tone-warn { stroke: #b8720a; }
:root[data-theme="light"] .why-icon.tone-bad { stroke: #c8473b; }
.why-text {
  font-size: 13px;
  line-height: 1.55;
  color: var(--ink-2);
}
:root[data-theme="light"] .why-text { color: #40444d; }
:root[data-theme="light"] .conclusion-sub-title { color: #9296a0; }
@media (max-width: 768px) {
  .why-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.narrative-sub-title {
  font-size: 13px !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  color: var(--ink, #f1f5f9) !important;
}
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
  color: #eab308;
}
.verdict-val-badge.badge-weak:hover,
.verdict-val-badge.badge-elevated:hover,
.verdict-val-badge.badge-warning:hover {
  background: rgba(234, 179, 8, 0.15);
  box-shadow: 0 0 0 1px rgba(234, 179, 8, 0.35);
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
  color: #ca8a04;
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

/* QUANTITATIVE EVIDENCE — top scorecard chips: flat tile, colour only on
   the value (no tinted background / border per status). */
.qe-scorecard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px;
  margin-bottom: 4px;
}
.qe-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 8px 11px;
  border-radius: 10px;
  border: 0;
  background: var(--panel-2);
  transition: background 0.15s ease;
}
:root[data-theme="light"] .qe-chip {
  background: #f6f7f9;
}
.qe-chip:hover {
  background: var(--panel-3);
}
:root[data-theme="light"] .qe-chip:hover {
  background: #eef0f3;
}
.qe-chip-label {
  font-size: 10.5px;
  font-weight: 500;
  color: var(--ink-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.qe-chip-label .metric-label-row {
  display: inline-flex !important;
  justify-content: flex-start !important;
  width: auto !important;
  gap: 0 !important;
}
.qe-chip-label .metric-label-row .param-label {
  flex: 0 0 auto;
}
.qe-chip-label .metric-label-row .formula-star-btn {
  margin: 0 0 0 3px !important;
  font-size: 11px !important;
}
.qe-chip-value {
  font-size: 14px;
  font-weight: 700;
  font-family: var(--mono);
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.qe-chip-good .qe-chip-value { color: var(--up); }
.qe-chip-warn .qe-chip-value { color: var(--amber); }
.qe-chip-bad .qe-chip-value { color: var(--down); }
:root[data-theme="light"] .qe-chip-label { color: #9296a0; }
:root[data-theme="light"] .qe-chip-good .qe-chip-value { color: #16794a; }
:root[data-theme="light"] .qe-chip-warn .qe-chip-value { color: #b8720a; }
:root[data-theme="light"] .qe-chip-bad .qe-chip-value { color: #af3327; }

/* Revisit condition -- a quiet grey bar, blue mono tag */
.qe-revisit-banner {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 6px 0 0;
  padding: 9px 12px;
  border-radius: 10px;
  background: var(--panel-2);
  font-size: 12.5px;
  line-height: 1.5;
}
:root[data-theme="light"] .qe-revisit-banner {
  background: #f6f7f9;
}
.qe-revisit-tag {
  font-family: var(--mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--amber);
  white-space: nowrap;
}
.qe-revisit-text {
  color: var(--ink-2);
}

/* Evidence rows: [TAG] | value chunks | verdict pill -- thin dividers,
   no terminal box (same grid as the redesign preview's `.ev-row`). */
.quant-audit-terminal {
  margin: 2px 0 0;
  padding: 0;
  border: 0;
  background: none;
}
.quant-audit-rows {
  display: flex;
  flex-direction: column;
}
.quant-audit-row {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr) auto;
  align-items: center;
  column-gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
}
.quant-audit-row:last-child {
  border-bottom: 0;
}
:root[data-theme="light"] .quant-audit-row {
  border-bottom-color: #f1f2f4;
}
.quant-audit-tag {
  font-family: var(--mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--ink-3);
  white-space: nowrap;
}
:root[data-theme="light"] .quant-audit-tag {
  color: #62666f;
}
/* Star pinned to the right edge of the tag column, so every row's "*"
   lines up in one vertical line. */
.quant-audit-tag .metric-label-row {
  display: flex !important;
  justify-content: space-between !important;
  width: 100% !important;
  gap: 6px !important;
}
.quant-audit-tag .metric-label-row .param-label {
  flex: 0 1 auto;
}
.quant-audit-tag .metric-label-row .formula-star-btn {
  margin: 0 !important;
  font-size: 11px !important;
}
.quant-audit-main {
  display: flex;
  flex-wrap: wrap;
  gap: 3px 16px;
  min-width: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--ink-2);
}
:root[data-theme="light"] .quant-audit-main {
  color: #62666f;
}
.ev-chunk {
  min-width: 0;
  overflow-wrap: anywhere;
}
.ev-chunk.ev-join {
  margin-left: -11px;
}
.quant-audit-end {
  display: flex;
  justify-content: flex-end;
  max-width: 340px;
}
.quant-audit-end:empty {
  display: none;
}
.ev-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  white-space: nowrap;
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1.35;
  text-align: right;
  background: var(--panel-2);
  color: var(--ink-2);
}
.ev-pill-flat { background: var(--panel-2); color: var(--ink-3); }
:root[data-theme="light"] .ev-pill-flat { background: #eef0f3; color: #62666f; }
.ev-pill-good { background: rgba(16, 185, 129, 0.14); color: var(--up); }
.ev-pill-warn { background: rgba(234, 179, 8, 0.14); color: var(--amber); }
.ev-pill-bad { background: rgba(244, 63, 94, 0.14); color: var(--down); }
:root[data-theme="light"] .ev-pill-good { background: #e4f5ea; color: #16794a; }
:root[data-theme="light"] .ev-pill-warn { background: #fef6d8; color: #ca8a04; }
:root[data-theme="light"] .ev-pill-bad { background: #fbeae9; color: #af3327; }
.quant-num {
  font-family: var(--mono);
  font-weight: 700;
  color: var(--ink);
}
:root[data-theme="light"] .quant-num {
  color: #14161a;
}
.quant-num.quant-num-neg {
  color: var(--down);
}
.quant-num.quant-num-warn {
  color: var(--amber);
}
:root[data-theme="light"] .quant-num.quant-num-neg { color: #af3327; }
:root[data-theme="light"] .quant-num.quant-num-warn { color: #b8720a; }
@media (max-width: 768px) {
  .quant-audit-row {
    grid-template-columns: minmax(0, 1fr);
    row-gap: 4px;
  }
  .quant-audit-end {
    justify-content: flex-start;
    max-width: none;
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
  color: var(--amber, #EAB308);
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
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  transition: all 0.2s ease;
}
:root[data-theme="dark"] .conclusion-verdict-block:hover,
:root:not([data-theme="light"]) .conclusion-verdict-block:hover {
  border-color: var(--amber, #EAB308);
  box-shadow: 0 4px 16px rgba(234, 179, 8, 0.15);
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
  transition: all 0.2s ease;
}
:root[data-theme="dark"] .conclusion-why:hover,
:root:not([data-theme="light"]) .conclusion-why:hover {
  border-color: var(--down, #F43F5E);
  box-shadow: 0 4px 16px rgba(244, 63, 94, 0.15);
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
  transition: all 0.2s ease;
}
:root[data-theme="dark"] .conclusion-proof:hover,
:root:not([data-theme="light"]) .conclusion-proof:hover {
  border-color: var(--info, #38BDF8);
  box-shadow: 0 4px 16px rgba(56, 189, 248, 0.15);
}
:root[data-theme="dark"] .conclusion-proof .conclusion-eyebrow,
:root:not([data-theme="light"]) .conclusion-proof .conclusion-eyebrow {
  color: var(--info, #38BDF8);
}
:root[data-theme="dark"] .conclusion-proof-list li.proof-card,
:root:not([data-theme="light"]) .conclusion-proof-list li.proof-card {
  background: var(--panel, #111726);
  border: 1px solid var(--line, #1E293B);
  color: var(--ink, #F8FAFC);
  transition: all 0.2s ease;
}
:root[data-theme="dark"] .conclusion-proof-list li.proof-card:hover,
:root:not([data-theme="light"]) .conclusion-proof-list li.proof-card:hover {
  border-color: var(--info, #38BDF8);
}
:root[data-theme="dark"] .proof-dot,
:root:not([data-theme="light"]) .proof-dot {
  color: var(--info, #38BDF8);
}

:root[data-theme="dark"] .conclusion-warning-block,
:root:not([data-theme="light"]) .conclusion-warning-block {
  background: rgba(234, 179, 8, 0.08);
  border: 1px solid rgba(234, 179, 8, 0.25);
  transition: all 0.2s ease;
}
:root[data-theme="dark"] .conclusion-warning-block:hover,
:root:not([data-theme="light"]) .conclusion-warning-block:hover {
  border-color: var(--amber, #EAB308);
  box-shadow: 0 4px 16px rgba(234, 179, 8, 0.15);
}
:root[data-theme="dark"] .warning-eyebrow,
:root:not([data-theme="light"]) .warning-eyebrow {
  color: #FBBF24;
}
:root[data-theme="dark"] .badge-warning,
:root:not([data-theme="light"]) .badge-warning {
  background: rgba(234, 179, 8, 0.2);
  color: #FBBF24;
  border: 1px solid rgba(234, 179, 8, 0.35);
}
:root[data-theme="dark"] .warning-bullet-item,
:root:not([data-theme="light"]) .warning-bullet-item {
  background: var(--panel, #111726);
  border: 1px solid rgba(234, 179, 8, 0.2);
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
  transition: all 0.2s ease;
}
:root[data-theme="light"] .conclusion-verdict-block:hover {
  border-color: #CA8A04 !important;
  box-shadow: 0 4px 16px rgba(217, 119, 6, 0.12) !important;
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
  transition: all 0.2s ease;
}
:root[data-theme="light"] .conclusion-why:hover {
  border-color: #E11D48 !important;
  box-shadow: 0 4px 16px rgba(225, 29, 72, 0.12) !important;
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
  transition: all 0.2s ease;
}
:root[data-theme="light"] .conclusion-proof:hover {
  border-color: #2563EB !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.12) !important;
}
:root[data-theme="light"] .conclusion-proof .conclusion-eyebrow {
  color: #1D4ED8 !important;
}
:root[data-theme="light"] .conclusion-proof-list li.proof-card {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  color: #1E293B !important;
  transition: all 0.2s ease;
}
:root[data-theme="light"] .conclusion-proof-list li.proof-card:hover {
  border-color: #2563EB !important;
}
:root[data-theme="light"] .proof-dot {
  color: #2563EB !important;
}

:root[data-theme="light"] .conclusion-warning-block {
  background: #FFFBEB !important;
  border: 1px solid #FDE68A !important;
  transition: all 0.2s ease;
}
:root[data-theme="light"] .conclusion-warning-block:hover {
  border-color: #CA8A04 !important;
  box-shadow: 0 4px 16px rgba(217, 119, 6, 0.12) !important;
}
:root[data-theme="light"] .warning-eyebrow {
  color: #B45309 !important;
}
:root[data-theme="light"] .badge-warning {
  background: #FEF9C3 !important;
  color: #B45309 !important;
  border: 1px solid #FDE68A !important;
}
:root[data-theme="light"] .warning-bullet-item {
  background: #FFFFFF !important;
  border: 1px solid #FEF9C3 !important;
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

/* Formula modal -- opened by clicking a "*" star (`openFormulaModal`).
   Hidden by default (no `.open` class); the hover tooltip already shown by
   `title=`/the rich-tip system on the star itself keeps working regardless. */
.formula-modal-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.6);
  z-index: 999;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.formula-modal-overlay.open { display: flex; }
.formula-modal {
  max-width: 480px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--panel, #0f172a);
  border: 1px solid var(--line, rgba(255,255,255,0.12));
  border-radius: var(--radius-md, 12px);
  padding: 22px 24px;
  position: relative;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
:root[data-theme="light"] .formula-modal {
  background: #ffffff;
  border-color: #e2e8f0;
}
.formula-modal-close {
  position: absolute;
  top: 10px;
  right: 12px;
  background: transparent;
  border: none;
  font-size: 22px;
  line-height: 1;
  color: var(--muted, #94a3b8);
  cursor: pointer;
  padding: 4px 8px;
}
.formula-modal-close:hover { color: var(--text, #ffffff); }
.formula-modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text, #ffffff);
  margin: 0 24px 14px 0;
}
.formula-modal-row { margin-bottom: 12px; }
.formula-modal-row:last-child { margin-bottom: 0; }
.formula-modal-tag {
  display: block;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--muted, #94a3b8);
  margin-bottom: 4px;
}
.formula-modal-formula {
  font-family: var(--mono);
  font-size: 13px;
  color: #38bdf8;
  line-height: 1.5;
  word-break: break-word;
}
.formula-modal-desc {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--ink-1, #cbd5e1);
}
:root[data-theme="light"] .formula-modal-desc { color: #334155; }

.param-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.formula-star {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--amber, #eab308);
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
  color: var(--amber, #eab308);
  margin-bottom: 6px;
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.1));
  padding-bottom: 4px;
}
.ft-formula {
  display: block;
  font-size: 11.5px;
  font-family: var(--mono);
  background: rgba(234, 179, 8, 0.08);
  border: 1px dashed rgba(234, 179, 8, 0.35);
  padding: 6px 8px;
  border-radius: 4px;
  margin-bottom: 6px;
  word-break: break-word;
}
.ft-formula code {
  font-size: 11.5px;
  color: var(--amber, #eab308);
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
  border: 1px solid var(--border);
  transition: border-color 0.2s ease;
}
.stat-tile-hero:hover {
  border-color: var(--tile-accent, var(--line));
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
.subsection { margin-top: 1.1rem; }
.table-caption {
  font-family: var(--mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted, #94a3b8);
  margin: 0.85rem 0 0.35rem;
}
.table-caption:first-child { margin-top: 0; }
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
  transition: border-color 0.2s ease;
}
.card-primary:hover {
  border-color: var(--primary-accent);
}
.card-quiet { background: var(--panel-2); }

.notice {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.6rem 0.85rem;
  margin-top: 0.75rem;
  font-size: var(--font-size-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.notice-warning { background: var(--notice-warning-bg); border-color: var(--notice-warning-border); }
.notice-warning:hover { border-color: var(--amber, #eab308); }
.notice-danger { background: var(--notice-danger-bg); border-color: var(--notice-danger-border); }
.notice-danger:hover { border-color: var(--down, #f43f5e); }
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
  vertical-align: middle !important;
}
/* Hàng tiêu đề dính khi cuộn bảng dài (`.table-scroll` có max-height) -- đọc
   tới hàng thứ 40 vẫn biết cột nào là cột nào. */
thead th {
  color: var(--muted);
  font-family: var(--mono);
  font-weight: 600;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: var(--panel-2);
  position: sticky;
  top: 0;
  z-index: 1;
  vertical-align: middle !important;
}
tbody td {
  vertical-align: middle !important;
}
tbody tr:last-child td { border-bottom: none; }
td:first-child, th:first-child { white-space: normal; text-align: left !important; }
/* Căn phải mọi cột số liệu trừ cột đầu (luôn là nhãn/tên) -- thẳng hàng cả header lẫn value */
td:not(:first-child), th:not(:first-child) { text-align: right !important; }
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
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.04);
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  vertical-align: middle !important;
}
:root[data-theme="light"] .score-basis-table th,
:root[data-theme="light"] .data-table th {
  background: #f1f5f9;
  color: #64748b;
  border-bottom-color: #e2e8f0;
}
.score-basis-table td,
.data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: #cbd5e1;
  vertical-align: middle !important;
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

/* Căn chỉnh thẳng hàng chính xác giữa tên cột và giá trị trong Score basis table */
.score-basis-table th:first-child,
.score-basis-table td:first-child {
  text-align: left !important;
}
.score-basis-table th:nth-child(2),
.score-basis-table td:nth-child(2),
.score-basis-table th:nth-child(3),
.score-basis-table td:nth-child(3),
.score-basis-table th:nth-child(4),
.score-basis-table td:nth-child(4) {
  text-align: right !important;
}
.score-basis-table th:last-child,
.score-basis-table td:last-child {
  text-align: center !important;
}

/* Căn chỉnh thẳng hàng chính xác giữa tên cột và giá trị trong Data tables */
.data-table th:first-child,
.data-table td:first-child {
  text-align: left !important;
}
.data-table th:not(:first-child):not(:last-child),
.data-table td:not(:first-child):not(:last-child),
.data-table th.dim-col-num,
.data-table td.dim-col-num {
  text-align: right !important;
}
.data-table th:last-child,
.data-table td:last-child,
.data-table th.dim-col-status,
.data-table td.dim-col-status {
  text-align: center !important;
}
.dim-col-status {
  text-align: center !important;
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
/* LIMITED bot -- per-dimension raw evidence (see `_render_limited_dimensions`),
   previously unstyled so it rendered as bare text with no card boundary. */
.limited-evidence-head {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 0.75rem;
}
.limited-evidence-row {
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 10px 14px;
}
:root[data-theme="light"] .limited-evidence-row {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.limited-evidence-row h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.limited-evidence-row .findings { margin-top: 0.4rem; }
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
/* Nút nổi -- luôn ở góc phải dưới, mọi tab. Biến mất khi panel đang mở
   (`aria-expanded="true"`, JS tự đặt) -- nút đóng trong panel thay thế vai
   trò của nó, tránh hai affordance "đóng" chồng nhau trên màn hình. */
/* ========================================================================= */
/* NORA AI CHAT ASSISTANT (MINI CHATGPT FLOATING WIDGET) */
/* ========================================================================= */

/* Floating Launch Button (FAB) -- icon-only, no label/status dot (24/09) */
.nora-chat-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 48px;
  height: 48px;
  padding: 0;
  border: 1px solid rgba(56, 189, 248, 0.4);
  border-radius: 50%;
  background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 8px 24px -4px rgba(2, 132, 199, 0.5), 0 2px 6px rgba(0, 0, 0, 0.2);
  z-index: 900;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  font-family: var(--font-base, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
}

.nora-chat-fab:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 12px 30px -4px rgba(2, 132, 199, 0.65), 0 4px 10px rgba(0, 0, 0, 0.3);
  border-color: #38bdf8;
}

.nora-chat-fab[aria-expanded="true"] {
  display: none;
}

.nora-chat-fab-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Chat Widget Panel (Mini ChatGPT Window) */
.nora-chat-widget {
  position: fixed;
  right: 24px;
  bottom: 84px;
  width: 410px;
  max-width: calc(100vw - 32px);
  height: 590px;
  max-height: min(650px, calc(100vh - 100px));
  z-index: 901;
  display: flex;
  flex-direction: column;
  background: var(--panel, #0f131a);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.1));
  border-radius: 20px;
  box-shadow: 0 24px 60px -10px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
  overflow: hidden;
  box-sizing: border-box;
  animation: nora-chat-pop-in 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

:root[data-theme="light"] .nora-chat-widget {
  background: #ffffff;
  border-color: #e2e8f0;
  box-shadow: 0 24px 60px -10px rgba(15, 23, 42, 0.2), 0 0 0 1px rgba(0, 0, 0, 0.05);
}

.nora-chat-widget[hidden] {
  display: none;
}

@keyframes nora-chat-pop-in {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Header */
.nora-chat-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  background: rgba(255, 255, 255, 0.02);
  flex-shrink: 0;
}

:root[data-theme="light"] .nora-chat-head {
  background: #f8fafc;
  border-bottom-color: #e2e8f0;
}

.nora-chat-avatar-head {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #38bdf8;
  flex-shrink: 0;
}

.nora-chat-title-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.nora-chat-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nora-chat-title-row h2 {
  font-size: 14.5px;
  font-weight: 700;
  margin: 0;
  color: var(--ink, #ffffff);
  letter-spacing: -0.01em;
}

:root[data-theme="light"] .nora-chat-title-row h2 {
  color: #0f172a;
}

.nora-chat-title-row .badge {
  font-family: var(--mono);
  font-size: 9.5px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.nora-chat-status-sub {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--ink-3, #94a3b8);
}

.nora-chat-online-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.nora-chat-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--ink-3, #94a3b8);
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.nora-chat-close:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--ink, #ffffff);
}

:root[data-theme="light"] .nora-chat-close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

/* Chat Message Log */
.nora-chat-log {
  flex: 1;
  overflow-y: auto;
  padding: 16px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-sizing: border-box;
}

.nora-chat-log:empty {
  display: none;
}

/* Message Rows & Alignment */
.nora-chat-msg-row {
  display: flex;
  width: 100%;
  gap: 8px;
  align-items: flex-end;
  box-sizing: border-box;
}

/* User Message: ALIGNED TO THE RIGHT */
.nora-chat-msg-row.msg-user {
  justify-content: flex-end;
}

/* Assistant Message: ALIGNED TO THE LEFT */
.nora-chat-msg-row.msg-assistant {
  justify-content: flex-start;
}

.nora-chat-msg-row.msg-error {
  justify-content: flex-start;
}

.nora-chat-avatar-head::before,
.nora-chat-avatar::before {
  content: "✦";
  font-size: 13px;
  line-height: 1;
  color: #38bdf8;
  filter: drop-shadow(0 0 4px rgba(56, 189, 248, 0.4));
}

/* Assistant Avatar next to message */
.nora-chat-avatar {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: rgba(56, 189, 248, 0.15);
  border: 1px solid rgba(56, 189, 248, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #38bdf8;
  flex-shrink: 0;
  margin-bottom: 2px;
}

/* Bubbles */
.nora-chat-bubble {
  font-size: 13px;
  line-height: 1.6;
  box-sizing: border-box;
  white-space: pre-wrap;
  word-break: break-word;
}

/* User Bubble: Right, Gradient Blue/Cyan with White text */
.nora-chat-bubble.role-user {
  background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
  color: #ffffff;
  border-radius: 16px 16px 4px 16px;
  padding: 10px 15px;
  max-width: 82%;
  box-shadow: 0 3px 12px rgba(37, 99, 235, 0.28);
}

/* Assistant Bubble: Left, Sleek Surface */
.nora-chat-bubble.role-assistant {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
  color: var(--ink-2, #e2e8f0);
  border-radius: 16px 16px 16px 4px;
  padding: 11px 15px;
  max-width: 86%;
}

:root[data-theme="light"] .nora-chat-bubble.role-assistant {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #0f172a;
}

/* Số liệu được tô đậm trong câu trả lời của assistant -- CÙNG ngôn ngữ thị
   giác với `.expert-metric` (đoạn nhận định ở trang report: mono, đậm,
   nền nhẹ, bo góc nhỏ) để một con số trông giống nhau dù xuất hiện ở chat
   hay ở báo cáo tĩnh. */
.nora-chat-metric {
  font-family: var(--mono);
  font-weight: 700;
  color: inherit;
  background: rgba(255, 255, 255, 0.1);
  padding: 0 4px;
  border-radius: 3px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
:root[data-theme="light"] .nora-chat-metric {
  background: rgba(15, 23, 42, 0.07);
}

/* Error Bubble */
.nora-chat-bubble.role-error {
  background: rgba(244, 63, 94, 0.1);
  border: 1px solid rgba(244, 63, 94, 0.3);
  color: #fda4af;
  border-radius: 12px;
  padding: 10px 14px;
  max-width: 90%;
}

/* Typing / Thinking Indicator */
.nora-chat-status {
  padding: 0 16px 6px;
  min-height: 0;
}

.nora-chat-status:empty {
  display: none;
}

.nora-chat-typing {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 20px;
  padding: 5px 12px;
  font-size: 11.5px;
  color: #7dd3fc;
}

.typing-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: 2px;
}

.tdot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #38bdf8;
  animation: typingBounce 1.4s infinite ease-in-out both;
}

.tdot:nth-child(1) { animation-delay: -0.32s; }
.tdot:nth-child(2) { animation-delay: -0.16s; }
.tdot:nth-child(3) { animation-delay: 0s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
  40% { transform: scale(1.2); opacity: 1; }
}

/* Prompt Chips */
.nora-chat-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 2px 16px 8px;
  flex-shrink: 0;
}

.nora-chat-chips:empty {
  display: none;
}

.nora-chat-chip {
  font-family: inherit;
  font-size: 11.5px;
  color: #7dd3fc;
  background: rgba(56, 189, 248, 0.07);
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 16px;
  padding: 5px 12px;
  cursor: pointer;
  transition: all 0.18s ease;
  text-align: left;
}

.nora-chat-chip:hover {
  color: #ffffff;
  background: rgba(56, 189, 248, 0.18);
  border-color: #38bdf8;
  transform: translateY(-1px);
}

:root[data-theme="light"] .nora-chat-chip {
  background: #f0f9ff;
  border-color: #bae6fd;
  color: #0284c7;
}

:root[data-theme="light"] .nora-chat-chip:hover {
  background: #e0f2fe;
  border-color: #0284c7;
  color: #0369a1;
}

/* Thanh nhập -- dạng "viên thuốc" (pill) một khối duy nhất, theo đúng ảnh
   tham chiếu chủ dự án gửi (22/09): placeholder nằm thẳng trong viên, nút
   gửi tròn nổi bật ở cuối, KHÔNG có khung/hover bọc quanh riêng ô nhập --
   viên pill là ranh giới thị giác DUY NHẤT, input bên trong luôn trong
   suốt/không viền dù có focus hay không (yêu cầu tường minh: "tránh thêm
   hover bọc nhập text"). */
.nora-chat-form {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 16px 8px;
  background: var(--panel-2, #141822);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.12));
  border-radius: 999px;
  padding: 4px 4px 4px 16px;
  flex-shrink: 0;
}

:root[data-theme="light"] .nora-chat-form {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.nora-chat-input {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-family: inherit;
  color: var(--ink, #ffffff);
  background: transparent;
  border: none;
  outline: none;
  box-shadow: none;
  padding: 9px 0;
}

/* Cố tình LẶP LẠI "không viền" ở trạng thái focus -- không phải thừa: nếu
   không có quy tắc riêng cho `:focus`, một số trình duyệt (Safari, Firefox
   cũ) tự vẽ viền/outline mặc định của hệ điều hành lên input khi focus,
   đúng thứ "hover bọc nhập text" cần tránh. */
.nora-chat-input:focus {
  outline: none;
  border: none;
  box-shadow: none;
}

:root[data-theme="light"] .nora-chat-input {
  color: #0f172a;
}

.nora-chat-input::placeholder {
  color: var(--ink-3, #64748b);
  opacity: 0.85;
}

.nora-chat-send {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #0284c7, #2563eb);
  color: #ffffff;
  font-size: 15px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.15s ease;
  flex-shrink: 0;
}

.nora-chat-send:hover:not(:disabled) {
  transform: scale(1.06);
}

.nora-chat-send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.nora-chat-disclaimer {
  font-size: 10.5px;
  line-height: 1.45;
  color: var(--ink-3, #94a3b8);
  text-align: center;
  margin: 0 16px 10px;
  opacity: 0.75;
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .nora-chat-widget {
    right: 12px;
    left: 12px;
    bottom: 80px;
    width: auto;
    max-width: none;
    height: calc(100vh - 120px);
    max-height: none;
  }
  .nora-chat-fab {
    right: 16px;
    bottom: 16px;
  }
}
/* HỒI QUY (22/09) VỪA SỬA: khối `@media` ở trên từng đóng ngoặc sớm ngay
   sau `.nora-chat-fab-label`, để lại hai rule mồ côi phía sau nó --
   ".nora-chat-form { flex-direction: column }" và một rule `.nora-chat-send`
   -- khiến cả hai áp dụng cho MỌI kích thước màn hình chứ không riêng
   mobile, và một dấu `}` thừa đứng một mình. Dáng "viên thuốc" (pill) mới
   vốn đã là một hàng ngang gọn (input co giãn + nút tròn cố định 34px),
   không cần xếp dọc trên mobile nữa nên hai rule đó bị bỏ hẳn thay vì sửa
   lại vị trí ngoặc. */
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
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
  border: 1px solid rgba(234, 179, 8, 0.35);
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
  border-left: 2px dashed #eab308;
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
  color: #eab308;
  background: var(--card-bg, #0b1120);
  padding: 1px 4px;
  border-radius: 3px;
  border: 1px solid rgba(234, 179, 8, 0.3);
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
  color: #eab308;
  font-weight: 700;
}
.cov-warning-box {
  border-left: 3px solid #eab308;
  background: rgba(234, 179, 8, 0.08);
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
  color: #eab308;
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
  border: 1px solid rgba(234, 179, 8, 0.35);
  color: #fbbf24;
  margin: 0 2px;
  transition: all 0.15s ease;
  cursor: pointer;
}
.cov-dim-pill:hover {
  background: rgba(234, 179, 8, 0.25);
  border-color: #eab308;
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
  color: #ca8a04 !important;
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
  border-color: #ca8a04 !important;
}
:root[data-theme="light"] .cov-warning-head {
  color: #b45309 !important;
}
:root[data-theme="light"] .cov-warning-body {
  color: #1e293b !important;
}
:root[data-theme="light"] .cov-dim-pill {
  background: #fef9c3 !important;
  border-color: #fde68a !important;
  color: #ca8a04 !important;
}
:root[data-theme="light"] .cov-dim-pill:hover {
  background: #fde68a !important;
  color: #ca8a04 !important;
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
  vertical-align: middle !important;
}
.hz-matrix-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: var(--ink, #e2e8f0);
  font-size: 12px;
  vertical-align: middle !important;
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
  text-align: left !important;
}
.hz-matrix-table .col-sample {
  text-align: right !important;
}
.hz-matrix-table .col-pop {
  text-align: right !important;
}
.hz-matrix-table .col-loss-ruin {
  text-align: center !important;
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
  background: rgba(234, 179, 8, 0.08);
  border: 1px solid rgba(234, 179, 8, 0.25);
  color: #fde68a;
}
.hz-insight-warn strong {
  color: #eab308;
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
  background: rgba(234, 179, 8, 0.12);
  border: 1px solid rgba(234, 179, 8, 0.3);
  color: #fbbf24;
}
.kp-badge-warn .kp-badge-dot {
  background: #eab308;
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
  color: #dc2626 !important;
}
:root[data-theme="light"] .hz-insight-decay strong {
  color: #b91c1c !important;
}
:root[data-theme="light"] .hz-insight-warn {
  background: #fffbeb !important;
  border-color: #fde68a !important;
  color: #ca8a04 !important;
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
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: stretch;
}
@media (max-width: 960px) {
  .growth-dashboard-grid {
    grid-template-columns: 1fr;
    gap: 20px;
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
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.growth-dashboard-right {
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.win-loss-composition-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.pie-stack-vertical {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  height: 100%;
  flex: 1 1 auto;
}
.growth-curve-panel > .theory,
.win-loss-composition-panel > .theory {
  margin-top: auto !important;
  padding-top: 14px;
}
.pie-card-stacked {
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
  box-shadow: none !important;
}
.pie-card-stacked h4 { margin: 0 0 0.4rem; font-size: var(--font-size-md); color: var(--muted); }
.pie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
  margin-top: 0.5rem;
}
.pie-cell { min-width: 0; }
.btn-subnav-back {
  background: var(--panel-2, rgba(255, 255, 255, 0.05));
  color: var(--ink, #f1f5f9);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.14));
  font-weight: 600;
  font-size: 13.5px;
  padding: 8px 16px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.btn-subnav-back:hover {
  background: rgba(56, 189, 248, 0.12);
  border-color: rgba(56, 189, 248, 0.4);
  color: #38bdf8;
  transform: translateX(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
:root[data-theme="light"] .btn-subnav-back {
  background: #ffffff;
  color: #334155;
  border: 1px solid #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
:root[data-theme="light"] .btn-subnav-back:hover {
  background: #f8fafc;
  border-color: #0284c7;
  color: #0284c7;
  box-shadow: 0 2px 8px rgba(2, 132, 199, 0.15);
  transform: translateX(-2px);
}
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
  color: #ca8a04;
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
#label-tab-market.tab-label-empty, #label-tab-trades.tab-label-empty,
.bot-report-inner-main #label-tab-market.tab-label-empty, .bot-report-inner-main #label-tab-trades.tab-label-empty { display: none !important; }
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
/* Premium Market & Other & Position tabs: bold text even when inactive */
.label-market .tab-title,
.label-trades .tab-title {
  font-weight: 700;
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

/* id="cach-choi" laid out like the redesign preview: 4 tiles, chip
   rows, a light phase table. `#cach-choi` + `!important` because the SPA's
   global.css styles every report table with `!important`. */
/* id="monte-carlo": redesign preview layout */
.mc-wrap { display: flex; flex-direction: column; gap: 12px; }
.mc-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 2px; }
.mc-title { font-size: 15px; font-weight: 700; color: var(--ink); }
.mc-chips { display: inline-flex; flex-wrap: wrap; gap: 6px; }
.mc-chip { padding: 5px 12px; border-radius: 999px; font-family: var(--mono); font-size: 12px; background: var(--panel-2); color: var(--ink-2); }
:root[data-theme="light"] .mc-chip { background: #eceef1; color: #40444d; }
.mc-t-good { color: var(--up); } .mc-t-warn { color: var(--amber); } .mc-t-bad { color: var(--down); }
.mc-t-info { color: #6f8cff; } .mc-t-ink { color: var(--ink); }
:root[data-theme="light"] .mc-t-good { color: #16794a; }
:root[data-theme="light"] .mc-t-warn { color: #b8720a; }
:root[data-theme="light"] .mc-t-bad { color: #af3327; }
:root[data-theme="light"] .mc-t-info { color: #2454e0; }
.mc-bg-good { background: var(--up); } .mc-bg-warn { background: var(--amber); } .mc-bg-bad { background: var(--down); } .mc-bg-info { background: #4a6cf0; }
:root[data-theme="light"] .mc-bg-good { background: #17a565; }
:root[data-theme="light"] .mc-bg-warn { background: #c38f2a; }
:root[data-theme="light"] .mc-bg-bad { background: #d04a3c; }
:root[data-theme="light"] .mc-bg-info { background: #2454e0; }
.mc-dd-h { display: block; margin: 14px 0 6px; }

.mc-pcards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.mc-pcard { display: flex; flex-direction: column; gap: 5px; padding: 13px 15px; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); min-width: 0; transition: box-shadow 0.18s ease, border-color 0.18s ease; }
.mc-pcard:hover { border-color: var(--line-2); box-shadow: 0 14px 28px -18px rgba(20, 22, 26, 0.3); }
:root[data-theme="light"] .mc-pcard { background: #fff; border-color: rgba(20, 22, 26, 0.06); }
.mc-pcard-l, .mc-stat-l { font-size: 11.5px; color: var(--ink-3); }
:root[data-theme="light"] .mc-pcard-l, :root[data-theme="light"] .mc-stat-l { color: #9296a0; }
.mc-pcard-l .metric-label-row, .mc-stat-l .metric-label-row { display: inline-flex !important; justify-content: flex-start !important; width: auto !important; gap: 0 !important; }
.mc-pcard-l .metric-label-row .formula-star-btn, .mc-stat-l .metric-label-row .formula-star-btn { margin: 0 0 0 4px !important; font-size: 11px !important; }
.mc-pcard-v { font-family: var(--mono); font-size: 22px; font-weight: 700; letter-spacing: -0.01em; }
.mc-pbar { display: block; height: 5px; border-radius: 3px; background: var(--panel-3); overflow: hidden; }
:root[data-theme="light"] .mc-pbar { background: #eceef1; }
.mc-pbar-fill { display: block; height: 100%; border-radius: 3px; min-width: 3px; }
.mc-pcard-s { font-family: var(--mono); font-size: 11px; color: var(--ink-3); }
:root[data-theme="light"] .mc-pcard-s { color: #9296a0; }
.mc-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); border-radius: 12px; background: var(--panel-2); padding: 10px 4px; }
:root[data-theme="light"] .mc-strip { background: #f6f7f9; }
.mc-stat { display: flex; flex-direction: column; gap: 3px; padding: 0 14px; border-left: 1px solid var(--line); min-width: 0; }
.mc-stat:first-child { border-left: 0; }
:root[data-theme="light"] .mc-stat { border-left-color: #e6e8ec; }
.mc-stat-v { font-family: var(--mono); font-size: 14px; font-weight: 700; }
.mc-mid { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 18px; align-items: stretch; margin-top: 8px; }
.mc-chart { min-width: 0; }
.mc-chart-bar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.mc-vtabs { display: inline-flex; gap: 2px; padding: 3px; border-radius: 9px; background: var(--panel-2); }
:root[data-theme="light"] .mc-vtabs { background: #eceef1; }
.mc-vbtn { border: 0; background: transparent; padding: 5px 12px; border-radius: 7px; font-family: inherit; font-size: 11.5px; font-weight: 500; color: var(--ink-3); cursor: pointer; transition: background 0.15s ease, color 0.15s ease; }
:root[data-theme="light"] .mc-vbtn { color: #62666f; }
.mc-vbtn:hover { color: var(--ink); }
.mc-chart[data-view="band"] .mc-vbtn[data-view="band"],
.mc-chart[data-view="dist"] .mc-vbtn[data-view="dist"],
.mc-chart[data-view="median"] .mc-vbtn[data-view="median"] { background: var(--panel); color: var(--ink); font-weight: 600; box-shadow: 0 1px 2px rgba(20, 22, 26, 0.08); }
.mc-chart:not([data-view="band"]) .mc-view-band,
.mc-chart:not([data-view="dist"]) .mc-view-dist,
.mc-chart:not([data-view="median"]) .mc-view-median,
.mc-chart:not([data-view="band"]) .mc-legend-band,
.mc-chart:not([data-view="dist"]) .mc-legend-dist,
.mc-chart:not([data-view="median"]) .mc-legend-median { display: none; }
.mc-legend { display: flex; gap: 12px; flex-wrap: wrap; }
.mc-legend span, .mc-streak-lg span { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--ink-3); }
:root[data-theme="light"] .mc-legend span, :root[data-theme="light"] .mc-streak-lg span { color: #62666f; }
.mc-legend i, .mc-streak-lg i { display: inline-block; width: 12px; height: 9px; border-radius: 2px; }
.mc-lg-med { height: 2px !important; background: #2454e0; }
.mc-lg-in { background: rgba(36, 84, 224, 0.25); }
.mc-lg-out { background: rgba(36, 84, 224, 0.1); }
.mc-lg-loss { height: 2px !important; background: #d04a3c; }
.mc-lg-win { background: #2454e0; }
.mc-lg-lossbar { background: #e8a39c; }
.mc-chart-body { position: relative; margin-top: 10px; }
.mc-svg { display: block; width: 100%; height: auto; overflow: visible; }
.mc-svg .mc-grid { stroke: var(--line); stroke-width: 1; }
.mc-svg .mc-zero { stroke: var(--line-2); stroke-width: 1; stroke-dasharray: 4 3; }
:root[data-theme="light"] .mc-svg .mc-grid { stroke: #f0f1f3; }
:root[data-theme="light"] .mc-svg .mc-zero { stroke: #c7cad0; }
.mc-svg .mc-tick { font-family: var(--mono); font-size: 10.5px; fill: var(--ink-3); }
:root[data-theme="light"] .mc-svg .mc-tick { fill: #9296a0; }
.mc-svg .mc-fan-stop { stop-color: #4a6cf0; }
:root[data-theme="light"] .mc-svg .mc-fan-stop { stop-color: #2454e0; }
.mc-svg .mc-band-inner { fill: rgba(74, 108, 240, 0.14); }
:root[data-theme="light"] .mc-svg .mc-band-inner { fill: rgba(36, 84, 224, 0.10); }
.mc-svg .mc-path { fill: none; stroke-width: 1; }
.mc-svg .mc-path-win { stroke: #6f8cff; stroke-opacity: 0.2; }
.mc-svg .mc-path-loss { stroke: #e06a5a; stroke-opacity: 0.55; }
:root[data-theme="light"] .mc-svg .mc-path-win { stroke: #2454e0; stroke-opacity: 0.16; }
:root[data-theme="light"] .mc-svg .mc-path-loss { stroke: #d04a3c; stroke-opacity: 0.45; }
.mc-svg .mc-edge { fill: none; stroke-width: 1.3; stroke-dasharray: 4 3; }
.mc-svg .mc-edge-up { stroke: #17a565; }
.mc-svg .mc-edge-down { stroke: #d04a3c; }
.mc-svg .mc-median { fill: none; stroke: #4a6cf0; stroke-width: 2.4; stroke-linejoin: round; }
.mc-svg .mc-median-thick { stroke-width: 2.6; }
:root[data-theme="light"] .mc-svg .mc-median { stroke: #2454e0; }
.mc-svg .mc-median-pt { fill: var(--panel); stroke: #4a6cf0; stroke-width: 2; }
:root[data-theme="light"] .mc-svg .mc-median-pt { fill: #fff; stroke: #2454e0; }
.mc-svg .mc-median-lbl { font-family: var(--mono); font-size: 11px; font-weight: 700; fill: var(--ink); }
.mc-svg .mc-tag-up { fill: #17a565; } .mc-svg .mc-tag-mid { fill: #2454e0; } .mc-svg .mc-tag-down { fill: #d04a3c; }
.mc-svg .mc-tag-text { font-family: var(--mono); font-size: 10.5px; font-weight: 700; fill: #fff; }
.mc-svg .mc-cross { stroke: var(--ink); stroke-opacity: 0.25; }
.mc-svg .mc-dot { fill: #2454e0; stroke: #fff; stroke-width: 2; }
.mc-svg .mc-hit { cursor: crosshair; }
.mc-svg .mc-bin-win { fill: #4a6cf0; }
.mc-svg .mc-bin-loss { fill: #e8a39c; }
:root[data-theme="light"] .mc-svg .mc-bin-win { fill: #2454e0; }
.mc-svg .mc-bin { cursor: default; transition: fill-opacity 0.12s ease; }
.mc-svg .mc-bin:hover { fill-opacity: 1; }
.mc-svg .mc-cvar-zone { fill: rgba(208, 74, 60, 0.07); }
.mc-svg .mc-cvar-lbl { font-family: var(--mono); font-size: 9.5px; font-weight: 700; fill: #d04a3c; }
:root[data-theme="light"] .mc-svg .mc-cvar-lbl { fill: #af3327; }
.mc-svg .mc-pline { stroke-width: 1.4; stroke-dasharray: 4 3; }
.mc-svg .mc-pline-up { stroke: #17a565; } .mc-svg .mc-pline-mid { stroke: #2454e0; } .mc-svg .mc-pline-down { stroke: #d04a3c; }
.mc-tipbox { display: none; position: absolute; pointer-events: none; min-width: 150px; background: #14161a; color: #fff; border-radius: 9px; padding: 8px 10px; font-size: 11.5px; box-shadow: 0 6px 20px rgba(20, 22, 26, 0.18); z-index: 5; }
.mc-tip-h { font-weight: 600; margin-bottom: 4px; color: #c7cad0; font-size: 11px; }
.mc-tip-r { display: flex; align-items: center; gap: 6px; line-height: 1.7; }
.mc-tip-r i { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.mc-tip-r b { margin-left: auto; font-family: var(--mono); padding-left: 12px; }
.mc-ladder-card { display: flex; flex-direction: column; padding: 16px 18px; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); }
.mc-ladder-card .mc-ladder { flex: 1; justify-content: space-around; }
:root[data-theme="light"] .mc-ladder-card { background: #fff; border-color: rgba(20, 22, 26, 0.06); }
.mc-lad-h { margin: 0 0 10px; }
.mc-ladder { position: relative; display: flex; flex-direction: column; gap: 4px; }
.mc-ladder::before { content: ""; position: absolute; left: 5px; top: 12px; bottom: 12px; width: 2px; background: linear-gradient(#17a565, #2454e0 50%, #d04a3c); opacity: 0.35; }
.mc-lad-row { position: relative; display: flex; align-items: center; gap: 10px; padding: 8px 8px 8px 0; border-radius: 8px; font-size: 12px; color: var(--ink-3); }
:root[data-theme="light"] .mc-lad-row { color: #62666f; }
.mc-lad-row i { width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--panel); box-shadow: 0 0 0 1px var(--line); flex-shrink: 0; }
:root[data-theme="light"] .mc-lad-row i { border-color: #fff; box-shadow: 0 0 0 1px #e6e8ec; }
.mc-lad-row b { margin-left: auto; font-family: var(--mono); font-size: 13.5px; }
.mc-lad-best i { background: #9fd8bb; } .mc-lad-p95 i { background: #17a565; } .mc-lad-med i { background: #2454e0; }
.mc-lad-p05 i { background: #d04a3c; } .mc-lad-worst i { background: #e8a39c; }
.mc-lad-med { background: var(--panel-2); color: var(--ink) !important; font-weight: 600; }
:root[data-theme="light"] .mc-lad-med { background: #f3f4f6; color: #14161a !important; }
.mc-toggle { margin-top: 6px; width: 100%; display: flex; align-items: center; gap: 12px; padding: 9px 12px; border: 1px dashed var(--line-2); border-radius: 10px; background: transparent; cursor: pointer; font-family: inherit; color: #6f8cff; transition: background 0.15s ease, border-color 0.15s ease; }
:root[data-theme="light"] .mc-toggle { border-color: #dcdfe4; background: #fff; color: #2454e0; }
.mc-toggle:hover { background: rgba(74, 108, 240, 0.06); border-color: rgba(74, 108, 240, 0.4); }
.mc-toggle-l { font-size: 12.5px; font-weight: 600; white-space: nowrap; }
.mc-toggle-tags { flex: 1; min-width: 0; text-align: left; font-family: var(--mono); font-size: 11px; color: var(--ink-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mc-toggle-ic { flex-shrink: 0; width: 7px; height: 7px; margin: 0 3px 3px; border-right: 1.6px solid currentColor; border-bottom: 1.6px solid currentColor; transform: rotate(45deg); transition: transform 0.2s ease; }
.mc-toggle[aria-expanded="true"] .mc-toggle-ic { transform: rotate(225deg); margin: 3px 3px 0; }
.mc-toggle[aria-expanded="true"] .mc-toggle-tags { visibility: hidden; }
.mc-more { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.25s ease; }
.mc-more.open { grid-template-rows: 1fr; }
.mc-more-in { overflow: hidden; min-height: 0; }
.mc-bottom { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 2fr); gap: 18px; padding-top: 8px; }
.mc-streaks { display: flex; flex-direction: column; min-width: 0; }
.mc-streak-lg { display: inline-flex; gap: 10px; }
.mc-lg-obs { background: #2454e0; } .mc-lg-base { background: #d3d6dc; }
.mc-streak { margin-top: 12px; }
.mc-streak-h { display: flex; justify-content: space-between; align-items: center; font-family: var(--mono); font-size: 12px; font-weight: 600; color: var(--ink); margin-bottom: 6px; }
.mc-streak-x { font-size: 11px; padding: 1px 8px; }
.mc-bar { position: relative; height: 16px; border-radius: 5px; background: var(--panel-2); margin-top: 4px; }
:root[data-theme="light"] .mc-bar { background: #f1f2f4; }
.mc-bar span { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 5px; min-width: 4px; }
.mc-bar-obs { background: #2454e0; } .mc-bar-base { background: #9aa0aa; }
:root[data-theme="light"] .mc-bar-base { background: #d3d6dc; }
.mc-bar b { position: absolute; right: 3px; top: 2px; line-height: 12px; padding: 0 4px; border-radius: 3px; font-family: var(--mono); font-size: 10.5px; color: var(--ink); background: var(--panel); }
:root[data-theme="light"] .mc-bar b { background: rgba(255, 255, 255, 0.9); color: #14161a; }
.mc-hzs { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.mc-hz-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.mc-hz { padding: 12px 14px; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); min-width: 0; }
:root[data-theme="light"] .mc-hz { background: #fff; border-color: rgba(20, 22, 26, 0.06); }
.mc-hz-main { box-shadow: inset 0 0 0 1.5px #4a6cf0; border-color: transparent; }
:root[data-theme="light"] .mc-hz-main { box-shadow: inset 0 0 0 1.5px #2454e0; }
.mc-hz-h { display: flex; justify-content: space-between; align-items: baseline; }
.mc-hz-h b { font-size: 13px; color: var(--ink); }
.mc-hz-h span { font-family: var(--mono); font-size: 11px; color: var(--ink-3); }
.mc-hz-pop { display: flex; align-items: baseline; gap: 6px; margin: 6px 0 8px; }
.mc-hz-pop b { font-family: var(--mono); font-size: 20px; color: #6f8cff; }
:root[data-theme="light"] .mc-hz-pop b { color: #2454e0; }
.mc-hz-pop span { font-size: 11.5px; color: var(--ink-3); }
.mc-hz-q { display: grid; grid-template-columns: repeat(3, auto); justify-content: space-between; row-gap: 2px; margin-top: 10px; font-size: 11px; color: var(--ink-3); }
.mc-hz-q span:nth-child(2), .mc-hz-q b:nth-child(5) { text-align: center; }
.mc-hz-q span:nth-child(3), .mc-hz-q b:nth-child(6) { text-align: right; }
.mc-hz-q b { font-family: var(--mono); font-size: 11.5px; color: var(--ink); }
.mc-hz-f { display: grid; grid-template-columns: 1fr auto; row-gap: 6px; margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--ink-3); }
.mc-hz-f b { font-family: var(--mono); font-size: 11.5px; color: var(--ink); text-align: right; }
@media (max-width: 1000px) {
  .mc-pcards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .mc-mid, .mc-bottom { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 640px) {
  .mc-hz-grid { grid-template-columns: minmax(0, 1fr); }
}
/* Even spacing between the top-level blocks of a tab: the tab panel's own
   flex gap is the only spacing (the SPA adds a 24px bottom margin to every
   card, which stacked on top of that gap made some distances ~3x others). */
.tab-panel > .card, .tab-panel > .dd-card, .tab-panel > details,
.bot-report-inner-main .tab-panel > .card,
.bot-report-inner-main .tab-panel > .dd-card,
.bot-report-inner-main .tab-panel > details {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}
/* Robustness / Open positions cards (redesign mockup) */
.rb-tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.rb-tile .pv-tile-v { font-size: 20px; }
.rb-rows { display: flex; flex-direction: column; }
.rb-group { border-bottom: 1px solid var(--line); }
:root[data-theme="light"] .rb-group { border-bottom-color: #eef0f3; }
.rb-group:last-child { border-bottom: 0; }
.rb-group .rb-row { border-bottom: 0; }
.rb-row { min-height: 46px; display: grid; grid-template-columns: minmax(0, 150px) minmax(0, 1fr) 80px 76px; align-items: center; gap: 12px; border-bottom: 1px solid var(--line); }
:root[data-theme="light"] .rb-row { border-bottom-color: #f3f4f6; }
.rb-rows > .rb-row:last-child { border-bottom: 0; }
.rb-l { display: flex; flex-direction: column; min-width: 0; }
.rb-l b { font-size: 12.5px; font-weight: 600; color: var(--ink); }
.rb-l span { font-family: var(--mono); font-size: 10.5px; color: var(--ink-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rb-bar { display: block; height: 6px; border-radius: 3px; background: var(--panel-3); overflow: hidden; }
:root[data-theme="light"] .rb-bar { background: #eceef1; }
.rb-bar span { display: block; height: 100%; border-radius: 3px; min-width: 2px; }
.rb-f-grey { background: #c2c6cd; } .rb-f-good { background: #3f9d63; } .rb-f-bad { background: #c8473b; }
.rb-f-info { background: #2f4fd8; } .rb-f-warn { background: #eab308; }
.rb-v { text-align: right; font-family: var(--mono); font-size: 13px; color: var(--ink); }
.rb-c { text-align: right; }
.rb-c .ev-pill { font-family: var(--mono); font-size: 11px; padding: 2px 8px; }
.rb-notice { font-size: 12.5px !important; margin-top: 10px !important; }
.ev-pill-info, .st-chip-info { background: rgba(92, 124, 250, 0.16); color: #8ea6ff; }
:root[data-theme="light"] .ev-pill-info, :root[data-theme="light"] .st-chip-info { background: #eef2fe; color: #2454e0; }
@media (max-width: 700px) { .rb-tiles { grid-template-columns: minmax(0, 1fr); } .rb-row { grid-template-columns: minmax(0, 1fr) 70px 50px; } .rb-bar { display: none; } }
/* Other & Position tab (redesign preview) */
.pv-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.pv-cols { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 28px; }
.pv-col { min-width: 0; }
.pv-col .st-label { display: block; margin-bottom: 4px; }
.pv-kv { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.pv-kv:last-child { border-bottom: 0; }
:root[data-theme="light"] .pv-kv { border-bottom-color: #f1f2f4; }
.pv-kv-l { color: var(--ink-2); min-width: 0; }
:root[data-theme="light"] .pv-kv-l { color: #40444d; }
.pv-kv-l .metric-label-row { display: inline-flex !important; width: auto !important; justify-content: flex-start !important; gap: 0 !important; }
.pv-kv-l .metric-label-row .formula-star-btn { margin: 0 0 0 4px !important; font-size: 11px !important; }
.pv-kv-v { font-family: var(--mono); font-weight: 700; color: var(--ink); white-space: nowrap; }
.pv-v-good { color: var(--up); } .pv-v-bad { color: var(--down); } .pv-v-warn { color: var(--amber); } .pv-v-info { color: #4a6cf0; }
:root[data-theme="light"] .pv-v-good { color: #16794a; }
:root[data-theme="light"] .pv-v-bad { color: #af3327; }
:root[data-theme="light"] .pv-v-warn { color: #b8720a; }
:root[data-theme="light"] .pv-v-info { color: #2454e0; }
.pv-tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.pv-tiles-1 { grid-template-columns: minmax(0, 1fr); } .pv-tiles-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); } .pv-tiles-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.pv-tile-l .metric-label-row { display: inline-flex !important; width: auto !important; gap: 4px !important; }
.pv-tile { padding: 12px 14px; border-radius: 12px; background: var(--panel-2); min-width: 0; }
:root[data-theme="light"] .pv-tile { background: #f6f7f9; }
.pv-tile-l { font-size: 11.5px; color: var(--ink-3); }
.pv-tile-v { margin-top: 4px; font-family: var(--mono); font-size: 22px; font-weight: 700; }
.pv-tile-s { margin-top: 2px; font-family: var(--mono); font-size: 11px; color: var(--ink-3); }
.pv-2col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; margin-top: 18px; }
.pv-box { min-width: 0; }
.ep-svg { display: block; width: 100%; height: auto; margin-top: 6px; overflow: visible; }
.ep-svg .ep-line { fill: none; stroke: var(--ink); stroke-width: 1.6; stroke-linejoin: round; stroke-linecap: round; }
.ep-svg .ep-peakline { stroke: #9296a0; stroke-opacity: 0.6; stroke-dasharray: 3 3; stroke-width: 1; }
.ep-svg .ep-fill { fill: url(#epFill); }
.ep-svg .ep-line-dd { stroke: #d04a3c; stroke-width: 2.2; }
.ep-svg .ep-mk { fill: var(--panel); stroke-width: 2; }
:root[data-theme="light"] .ep-svg .ep-mk { fill: #fff; }
.ep-svg .ep-mk-peak { stroke: #3fbf7f; } .ep-svg .ep-mk-trough { stroke: #e5675a; } .ep-svg .ep-mk-back { stroke: #3fbf7f; }
.ep-svg .ep-lbl { font-family: var(--mono); font-size: 10px; font-weight: 700; }
.ep-svg .ep-lbl-peak { fill: #3fbf7f; } .ep-svg .ep-lbl-trough { fill: #e5675a; } .ep-svg .ep-lbl-back { fill: #3fbf7f; }
:root[data-theme="light"] .ep-svg .ep-mk-peak { stroke: #16794a; } :root[data-theme="light"] .ep-svg .ep-lbl-peak { fill: #16794a; }
:root[data-theme="light"] .ep-svg .ep-mk-trough { stroke: #af3327; } :root[data-theme="light"] .ep-svg .ep-lbl-trough { fill: #af3327; }
:root[data-theme="light"] .ep-svg .ep-mk-back { stroke: #16794a; } :root[data-theme="light"] .ep-svg .ep-lbl-back { fill: #16794a; }
:root[data-theme="light"] .ep-svg .ep-line { stroke: #14161a; }
.ep-svg .ep-line.ep-line-dd, :root[data-theme="light"] .ep-svg .ep-line.ep-line-dd { stroke: #d04a3c; stroke-width: 2.2; }
.ep-svg .ep-axis { font-family: var(--mono); font-size: 9.5px; fill: var(--ink-3); }
.pv-minis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
.pv-mini { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; border-radius: 10px; background: var(--panel-2); font-size: 11px; color: var(--ink-3); }
:root[data-theme="light"] .pv-mini { background: #f6f7f9; }
.pv-mini b { font-family: var(--mono); font-size: 13px; color: var(--ink); }
.pv-mini b.pv-v-good { color: var(--up); } .pv-mini b.pv-v-bad { color: var(--down); } .pv-mini b.pv-v-info { color: #6f8cff; }
:root[data-theme="light"] .pv-mini b.pv-v-good { color: #16794a; }
:root[data-theme="light"] .pv-mini b.pv-v-bad { color: #af3327; }
:root[data-theme="light"] .pv-mini b.pv-v-info { color: #2454e0; }
.pv-worst { display: grid; grid-template-columns: 150px minmax(0, 1fr) 80px; align-items: center; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--line); }
.pv-worst:last-child { border-bottom: 0; }
:root[data-theme="light"] .pv-worst { border-bottom-color: #f1f2f4; }
.pv-worst-l { display: flex; flex-direction: column; min-width: 0; }
.pv-worst-l b { font-family: var(--mono); font-size: 12px; color: var(--ink); font-weight: 600; }
.pv-worst-l span { font-size: 11px; color: var(--ink-3); }
.pv-worst-bar { display: block; height: 6px; border-radius: 3px; background: var(--panel-3); overflow: hidden; }
:root[data-theme="light"] .pv-worst-bar { background: #eceef1; }
.pv-worst-bar span { display: block; height: 100%; border-radius: 3px; background: #d04a3c; }
.pv-worst-v { font-family: var(--mono); font-size: 13px; color: var(--down); text-align: right; }
:root[data-theme="light"] .pv-worst-v { color: #af3327; }
.pv-kvs { margin-top: 4px; }
.pv-pair { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; margin-top: 14px; }
.pv-pair > section.card,
.bot-report-inner-main .pv-pair > section.card { margin: 0 !important; padding: 16px 18px !important; border: 1px solid var(--line) !important; border-radius: 14px !important; box-shadow: none !important; background: var(--panel) !important; }
:root[data-theme="light"] .pv-pair > section.card { border-color: #eceef1 !important; background: #fff !important; }
.pv-pair > section.card > .block-b { padding: 0; }
.pv-pair > section:only-child { grid-column: 1 / -1; }
.pv-card > .pv-group > section.card,
.bot-report-inner-main .pv-card > .pv-group > section.card { margin: 14px 0 0 !important; padding: 0 !important; border: 0 !important; box-shadow: none !important; background: transparent !important; }
.pv-card > .pv-group > section.card > .block-b { padding: 0; }
.pv-card[data-active="robust"] > .pv-group:not([data-group="robust"]),
.pv-card[data-active="openstats"] > .pv-group:not([data-group="openstats"]),
.pv-card[data-active="assets"] > .pv-group:not([data-group="assets"]),
.pv-card[data-active="ledger"] > .pv-group:not([data-group="ledger"]) { display: none; }
.pv-card[data-active="robust"] .dd-tab[data-pane="robust"],
.pv-card[data-active="openstats"] .dd-tab[data-pane="openstats"],
.pv-card[data-active="assets"] .dd-tab[data-pane="assets"],
.pv-card[data-active="ledger"] .dd-tab[data-pane="ledger"] { background: var(--panel); box-shadow: 0 1px 3px rgba(20, 22, 26, 0.12); }
.pv-card[data-active="robust"] .dd-tab[data-pane="robust"] .dd-tab-l,
.pv-card[data-active="openstats"] .dd-tab[data-pane="openstats"] .dd-tab-l,
.pv-card[data-active="assets"] .dd-tab[data-pane="assets"] .dd-tab-l,
.pv-card[data-active="ledger"] .dd-tab[data-pane="ledger"] .dd-tab-l { color: var(--ink); }
.pv-tabbar { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
#tai-san .pv-table, #danh-sach-lenh table { min-width: 560px !important; border: 0 !important; background: transparent !important; }
#tai-san .pv-table th, #danh-sach-lenh th { background: transparent !important; font-family: var(--sans) !important; font-size: 10.5px !important; font-weight: 600 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; color: var(--ink-3) !important; padding: 8px 10px !important; border-bottom: 1px solid var(--line) !important; }
#tai-san .pv-table td, #danh-sach-lenh td { padding: 9px 10px !important; font-size: 13px !important; color: var(--ink-2) !important; border-bottom: 1px solid var(--line) !important; background: transparent !important; }
:root[data-theme="light"] #tai-san .pv-table th, :root[data-theme="light"] #danh-sach-lenh th { color: #9296a0 !important; border-bottom-color: #eceef1 !important; }
:root[data-theme="light"] #tai-san .pv-table td, :root[data-theme="light"] #danh-sach-lenh td { color: #40444d !important; border-bottom-color: #f1f2f4 !important; }
#tai-san .pv-table td:nth-child(4) { width: 40%; }
.pv-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; vertical-align: 1px; }
.pv-asset { font-family: var(--mono); color: var(--ink); }
.pv-state { font-size: 11px; padding: 2px 9px; }
.pv-num { font-family: var(--mono); }
.pv-muted { color: var(--ink-3) !important; }
.pv-stale { color: var(--amber) !important; }
.pv-abar { display: block; height: 6px; border-radius: 3px; background: var(--panel-3); overflow: hidden; }
:root[data-theme="light"] .pv-abar { background: #eceef1; }
.pv-abar span { display: block; height: 100%; border-radius: 3px; }
/* Positions tab: trade book (assets / closed trades) as in the redesign preview */
.pv-tabhead { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.pv-card-compact .pv-tabhead > .pv-tabbar { flex: 0 1 560px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.pv-extra { display: none; }
.pv-card[data-active="assets"] .pv-extra[data-for="assets"],
.pv-card[data-active="ledger"] .pv-extra[data-for="ledger"] { display: flex; align-items: center; }
.as-legend { margin-top: 0 !important; }
.as-legend .info-tip { left: auto !important; right: -8px !important; }
.as-list, .lg-scroll { overflow-x: auto; }
.as-row { display: grid; grid-template-columns: 160px 120px 56px minmax(0, 1fr) 110px; align-items: center; gap: 14px; min-width: 620px; padding: 9px 0; border-bottom: 1px solid var(--line); font-size: 12.5px; }
.as-row:last-child { border-bottom: 0; }
.as-row.as-head, .lg-row.lg-head { padding: 0 0 6px !important; font-size: 10.5px; font-weight: 600; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.04em; }
.as-r { text-align: right; }
.as-name { display: flex; align-items: center; gap: 8px; min-width: 0; }
.as-name i { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.as-name b { font-family: var(--mono); font-size: 13px; font-weight: 700; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.as-closed { display: flex; align-items: center; gap: 10px; }
.as-closed b { width: 34px; text-align: right; font-size: 13px; color: var(--ink); }
.as-track { flex: 1; height: 6px; border-radius: 3px; background: var(--panel-3); overflow: hidden; }
.as-track span { display: block; height: 100%; border-radius: 3px; background: #9aa0aa; }
.as-last { color: var(--ink-2); }
.lg-row { display: grid; grid-template-columns: 56px 140px 110px minmax(0, 1fr) 140px 64px; align-items: center; gap: 12px; min-width: 680px; padding: 8px 6px; border-bottom: 1px solid var(--line); border-radius: 8px; font-size: 12.5px; transition: background 0.12s ease; }
.lg-row[hidden] { display: none !important; }
.lg-body .lg-row:hover { background: var(--panel-2); }
.lg-row.lg-head { padding-left: 6px !important; padding-right: 6px !important; border-radius: 0; }
.lg-t { color: var(--ink-2); }
.lg-pl { display: flex; align-items: center; justify-content: flex-end; gap: 8px; }
.lg-pl b { min-width: 88px; text-align: right; font-size: 13px; }
.lg-pl-bar { display: inline-block; height: 6px; border-radius: 3px; opacity: 0.35; }
.lg-pl-win { background: #17a565; } .lg-pl-loss { background: #d04a3c; } .lg-pl-even { background: var(--ink-3); }
.lg-cum { font-size: 13px; font-weight: 600; }
.lg-foot { margin-top: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.lg-info { font-size: 11.5px; color: var(--ink-3); }
.lg-pager { display: flex; gap: 4px; }
.bot-report-inner-main .lg-pg, .lg-pg { min-width: 30px; height: 30px; padding: 0 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); font-family: var(--mono); font-size: 12px; color: var(--ink-2); cursor: pointer; transition: background 0.12s ease; }
.lg-pg:hover:not([disabled]) { background: var(--panel-2); }
.bot-report-inner-main .lg-pg.on, .lg-pg.on { background: var(--ink); border-color: var(--ink); color: var(--panel); }
.lg-pg[disabled] { opacity: 0.35; cursor: default; }
.lg-gap { align-self: center; padding: 0 2px; color: var(--ink-3); }
:root[data-theme="light"] .as-row, :root[data-theme="light"] .lg-row { border-bottom-color: #f3f4f6; }
:root[data-theme="light"] .as-head, :root[data-theme="light"] .lg-head { border-bottom-color: #eef0f3; }
:root[data-theme="light"] .as-track { background: #f1f2f4; }
:root[data-theme="light"] .lg-body .lg-row:hover { background: #f7f8fa; }
:root[data-theme="light"] .lg-pg { background: #fff; border-color: #e6e8ec; color: #40444d; }
:root[data-theme="light"] .lg-pg.on { background: #14161a; border-color: #14161a; color: #fff; }
/* Robustness / open-position cards: equal height, rows share the space */
.pv-pair { align-items: stretch; }
.pv-pair > section.card, .bot-report-inner-main .pv-pair > section.card { display: flex !important; flex-direction: column; }
.pv-pair > section.card > .block-b { flex: 1; display: flex; flex-direction: column; }
.pv-pair .rb-rows { flex: 1; }
.pv-pair .rb-rows > .rb-row, .pv-pair .rb-group { flex: 1; }
.rb-group { display: flex; flex-direction: column; }
.rb-group .rb-row { flex: 1; }
.rb-warn { margin-top: 10px; padding: 7px 12px; border-radius: 10px; background: rgba(201, 138, 42, 0.12); color: var(--amber); font-size: 12px; }
:root[data-theme="light"] .rb-warn { background: #fef6d8; color: #ca8a04; }
.pv-2col { align-items: stretch; }
.pv-2col > .pv-box { display: flex; flex-direction: column; }
.pv-2col > .pv-box > .pv-worst { flex: 1; }
@media (max-width: 1000px) {
  .pv-cols, .pv-2col, .pv-pair { grid-template-columns: minmax(0, 1fr); }
  .pv-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
/* Premium Market tab (redesign preview) */
.mk-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.mk-ftabs { display: inline-flex; flex-wrap: wrap; gap: 2px; padding: 4px; border-radius: 12px; background: var(--panel-2); }
:root[data-theme="light"] .mk-ftabs { background: #eceef1; }
.mk-ftab { border: 0; background: transparent; padding: 6px 12px; border-radius: 9px; font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--ink-3); cursor: pointer; }
.mk-ftab span { font-family: var(--mono); font-size: 11px; font-weight: 500; color: var(--ink-3); margin-left: 3px; }
.mk-ftab:hover { color: var(--ink); }
.mk-ftab.on { background: var(--panel); color: var(--ink); box-shadow: 0 1px 2px rgba(20, 22, 26, 0.1); }
:root[data-theme="light"] .mk-ftab.on { background: #fff; }
.mk-r { text-align: right !important; }
.mk-empty { height: 96px; margin-top: 12px; border-radius: 12px; background: repeating-linear-gradient(45deg, var(--panel-2), var(--panel-2) 8px, var(--panel-3) 8px, var(--panel-3) 16px); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; text-align: center; font-size: 12px; color: var(--ink-3); padding: 0 16px; }
:root[data-theme="light"] .mk-empty { background: repeating-linear-gradient(45deg, #f6f7f9, #f6f7f9 8px, #eef0f3 8px, #eef0f3 16px); color: #62666f; }
.mk-empty b { font-size: 13px; color: var(--ink); }
.mk-foot-note { margin-top: 12px; display: flex; align-items: center; gap: 8px; font-size: 11.5px; color: var(--ink-3); }
.mk-foot-note .info-ic { margin: 0; }
.mk-foot-note .info-tip { right: auto !important; left: -8px; }
.mk-note .mk-sq { margin-right: 4px; }
#thi-truong-chinh .mk-table .mk-r { text-align: right !important; }
#thi-truong-chinh .mk-table td { font-size: 14px !important; }
#thi-truong-chinh .mk-table td.pv-num { font-size: 14px !important; }
.mk-share .pv-abar { width: 36px !important; }
.mk-share { gap: 14px !important; }
.mk-share b { font-size: 14px !important; min-width: 40px; }
#thi-truong-chinh .pv-asset { font-size: 14.5px !important; font-weight: 700; }
.mk-pair { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.mk-pair-n { font-family: var(--mono); font-size: 22px; color: var(--ink); margin-right: 4px; }
.mk-primary-lg { font-size: 11.5px; padding: 3px 9px; }
.mk-right { margin-left: auto; }
.mk-spec b { font-family: var(--sans) !important; font-size: 15px !important; }
.mk-pane .mk-spec { padding: 12px 14px; border: 1px solid var(--line); background: var(--panel); font-size: 11.5px; }
:root[data-theme="light"] .mk-pane .mk-spec { background: #fff; border-color: rgba(20, 22, 26, 0.06); }
.mk-specs-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.mk-foot { display: block; margin-top: 10px; }
#thi-truong-chinh .mk-table td { font-size: 13.5px !important; padding: 11px 10px !important; }
#thi-truong-chinh .mk-table tbody tr:hover td { background: var(--panel-2) !important; }
:root[data-theme="light"] #thi-truong-chinh .mk-table tbody tr:hover td { background: #f8f9fb !important; }
#thi-truong-chinh .pv-asset { font-size: 14px; }
.mk-card .mc-toggle { margin-top: 14px; }

.mk-head-r { display: inline-flex; gap: 6px; flex-wrap: wrap; }
.mk-sub { display: block; margin: 14px 0 6px; }
.mk-bar { display: flex; height: 28px; border-radius: 7px; overflow: hidden; gap: 2px; }
.mk-seg { display: flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 12px; font-weight: 600; color: #14161a; white-space: nowrap; overflow: hidden; }
.mk-seg-up { background: #2f7a55; color: #e3f6ec; } .mk-seg-side { background: #3d4f82; color: #e3e9ff; } .mk-seg-down { background: #b8483d; color: #fff; }
.mk-seg-na { background: repeating-linear-gradient(45deg, #26303f, #26303f 4px, #1a2230 4px, #1a2230 8px); }
:root[data-theme="light"] .mk-seg-up { background: #a7dcbc; color: #14161a; } :root[data-theme="light"] .mk-seg-side { background: #c9d6f7; color: #14161a; } :root[data-theme="light"] .mk-seg-down { background: #d9695c; color: #fff; }
:root[data-theme="light"] .mk-seg-na { background: repeating-linear-gradient(45deg, #e2e5ea, #e2e5ea 4px, #f4f5f7 4px, #f4f5f7 8px); }
.mk-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 8px 0 6px; font-size: 11.5px; color: var(--ink-3); }
.mk-legend span { display: inline-flex; align-items: center; gap: 6px; }
.mk-legend i, .mk-sq { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
.mk-primary { margin-left: 6px; padding: 1px 7px; border-radius: 999px; font-size: 10.5px; font-weight: 600; background: var(--panel-2); color: var(--ink-2); }
:root[data-theme="light"] .mk-primary { background: #eef0f3; color: #40444d; }
.mk-share { display: inline-flex; align-items: center; gap: 10px; }
.mk-share .pv-abar { width: 70px; }
.mk-share b { font-family: var(--mono); font-size: 12.5px; color: var(--ink); min-width: 44px; text-align: right; }
#thi-truong-chinh .mk-table { min-width: 680px !important; border: 0 !important; background: transparent !important; margin-top: 6px; }
#thi-truong-chinh .mk-table th { background: transparent !important; font-family: var(--sans) !important; font-size: 10.5px !important; font-weight: 600 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; color: var(--ink-3) !important; padding: 8px 10px !important; border-bottom: 1px solid var(--line) !important; text-align: left !important; }
#thi-truong-chinh .mk-table td { padding: 10px !important; font-size: 13px !important; color: var(--ink-2) !important; border-bottom: 1px solid var(--line) !important; background: transparent !important; text-align: left !important; }
:root[data-theme="light"] #thi-truong-chinh .mk-table th { color: #9296a0 !important; border-bottom-color: #eceef1 !important; }
:root[data-theme="light"] #thi-truong-chinh .mk-table td { color: #40444d !important; border-bottom-color: #f1f2f4 !important; }
.mk-primary-box { margin-top: 16px; padding: 14px 16px; border-radius: 14px; background: var(--panel-2); }
:root[data-theme="light"] .mk-primary-box { background: #f6f7f9; }
.mk-specs { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.mk-specs .pv-mini { background: var(--panel); }
:root[data-theme="light"] .mk-specs .pv-mini { background: #fff; }
.mk-notes { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.mk-note { padding: 5px 11px; border-radius: 999px; font-size: 12.5px; background: var(--panel-2); color: var(--ink-2); }
:root[data-theme="light"] .mk-note { background: #eef0f3; color: #40444d; }
.mk-note .quant-num { font-family: var(--mono); font-weight: 700; color: var(--ink); }
.mk-pill { font-size: 12px; padding: 4px 11px; }
.mk-head .info-tip { right: auto !important; left: -8px; }
.mk-head .mc-title { display: inline-flex; align-items: center; }
.mk-primary-lg { font-size: 12.5px !important; padding: 4px 12px !important; }
.mk-compare { margin-top: 8px; }
.mk-compare { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; color: var(--ink-2); }
.mk-compare-row::before { content: "↳ "; color: var(--ink-3); }
.cv-wrap { display: flex; flex-direction: column; gap: 12px; }
.cv-legend { display: flex; flex-wrap: wrap; gap: 8px 18px; font-size: 12px; margin-top: 4px; }
.cv-leg { display: inline-flex; align-items: center; gap: 6px; }
.cv-leg i { width: 9px; height: 9px; border-radius: 3px; display: inline-block; }
.cv-leg b { font-family: var(--mono); font-weight: 600; color: var(--ink); }
.cv-leg em { font-style: normal; font-family: var(--mono); color: var(--ink-3); }
.cv-hatch { background: repeating-linear-gradient(45deg, #3a4556, #3a4556 3px, #1f2735 3px, #1f2735 6px); }
:root[data-theme="light"] .cv-hatch { background: repeating-linear-gradient(45deg, #d6d9df, #d6d9df 3px, #f1f2f4 3px, #f1f2f4 6px); }
.cv-wrap .cov-bar-wrapper { margin-top: 34px !important; }
.cv-wrap .cov-stacked-bar { height: 30px !important; border-radius: 8px !important; }
.cv-wrap .cov-target-line { background: var(--ink) !important; width: 2px !important; top: -14px !important; bottom: -6px !important; }
.cv-wrap .cov-target-pin { background: var(--ink) !important; color: var(--panel) !important; border: 0 !important; border-radius: 5px !important; font-family: var(--mono) !important; font-weight: 700 !important; }
/* Market compatibility: regime timeline per asset */
.rgc-svg { display: block; width: 100%; height: auto; margin-top: 8px; }
.rgc-svg .rgb { opacity: 0.5; }
.rgc-svg .rg-uc { fill: #2c6a4b; } .rgc-svg .rg-uv { fill: #3fbf7f; } .rgc-svg .rg-sc { fill: #34426b; }
.rgc-svg .rg-sv { fill: #6c8cf0; } .rgc-svg .rg-dc { fill: #7a3b36; } .rgc-svg .rg-dv { fill: #e0564a; } .rgc-svg .rg-na { fill: #26303f; }
:root[data-theme="light"] .rgc-svg .rg-uc { fill: #a7dcbc; } :root[data-theme="light"] .rgc-svg .rg-uv { fill: #3fa066; } :root[data-theme="light"] .rgc-svg .rg-sc { fill: #cdd8f6; }
:root[data-theme="light"] .rgc-svg .rg-sv { fill: #7f9ff0; } :root[data-theme="light"] .rgc-svg .rg-dc { fill: #eeb6ad; } :root[data-theme="light"] .rgc-svg .rg-dv { fill: #d04a3c; } :root[data-theme="light"] .rgc-svg .rg-na { fill: #e2e5ea; }
.rgc-svg .rgc-trackbg { fill: var(--panel-2); }
:root[data-theme="light"] .rgc-svg .rgc-trackbg { fill: #f4f5f7; }
.rgc-svg .rgc-mk { stroke-width: 1.6; } .rgc-svg .rgc-win { stroke: #17a565; } .rgc-svg .rgc-loss { stroke: #d04a3c; }
.rgc-svg .rgc-grid { stroke: rgba(255, 255, 255, 0.08); stroke-width: 1; }
:root[data-theme="light"] .rgc-svg .rgc-grid { stroke: rgba(255, 255, 255, 0.5); }
.rgc-svg .rgc-line { fill: none; stroke: var(--ink); stroke-width: 1.6; stroke-linejoin: round; }
.rgc-svg .rgc-tick { font-family: var(--mono); font-size: 10.5px; fill: var(--ink-3); }
.rgc-trades { grid-template-columns: 54px minmax(0, 1fr) !important; margin-top: 4px; }
.rgc-trades .rg-l span { font-size: 10px; }
.rga-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0 28px; margin-top: 16px; }
.rga-row { display: grid; grid-template-columns: minmax(0, 1fr) 120px 58px; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
:root[data-theme="light"] .rga-row { border-bottom-color: #f3f4f6; }
.rga-n { display: flex; align-items: center; gap: 4px; font-weight: 600; color: var(--ink); }
.rga-row b { text-align: right; color: var(--ink); }
.rga-row .pv-abar span { opacity: 1; }
.rga-zero .rga-n, .rga-zero b { color: var(--ink-3); font-weight: 500; }
.rga-head { font-size: 10.5px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; color: var(--ink-3); padding-top: 0; }
.rg-chip-info { background: #eef2fe !important; color: #2454e0 !important; }
@media (max-width: 900px) { .rga-grid { grid-template-columns: minmax(0, 1fr); } }

.rg-card { margin-top: 12px; }
.rg-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0 6px; }
.rg-chip { font-family: var(--mono); font-size: 12px; padding: 4px 11px; }
.rg-grid { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
.rg-row { display: grid; grid-template-columns: 130px minmax(0, 1fr) 150px; align-items: center; gap: 14px; }
.rg-l { display: flex; flex-direction: column; min-width: 0; }
.rg-l b { font-family: var(--mono); font-size: 12.5px; color: var(--ink); }
.rg-l span { font-family: var(--mono); font-size: 10.5px; color: var(--ink-3); }
.rg-bar { position: relative; height: 18px; border-radius: 4px; overflow: hidden; background: var(--panel-2); }
.rg-seg { position: absolute; top: 0; bottom: 0; }
.rg-bar-empty { display: flex; align-items: center; justify-content: center; background: repeating-linear-gradient(45deg, var(--panel-2), var(--panel-2) 6px, var(--panel-3) 6px, var(--panel-3) 12px); font-size: 11.5px; color: var(--ink-3); }
:root[data-theme="light"] .rg-bar-empty { background: repeating-linear-gradient(45deg, #f6f7f9, #f6f7f9 6px, #eef0f3 6px, #eef0f3 12px); }
.rg-uc { background: #2c6a4b; } .rg-uv { background: #3fbf7f; } .rg-sc { background: #34426b; }
.rg-sv { background: #6c8cf0; } .rg-dc { background: #7a3b36; } .rg-dv { background: #e0564a; }
.rg-na { background: repeating-linear-gradient(45deg, #26303f, #26303f 3px, #1a2230 3px, #1a2230 6px); }
:root[data-theme="light"] .rg-uc { background: #a7dcbc; } :root[data-theme="light"] .rg-uv { background: #3fa066; } :root[data-theme="light"] .rg-sc { background: #cdd8f6; }
:root[data-theme="light"] .rg-sv { background: #7f9ff0; } :root[data-theme="light"] .rg-dc { background: #eeb6ad; } :root[data-theme="light"] .rg-dv { background: #d04a3c; }
:root[data-theme="light"] .rg-na { background: repeating-linear-gradient(45deg, #e2e5ea, #e2e5ea 3px, #f4f5f7 3px, #f4f5f7 6px); }
.rg-now { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--ink-2); }
.rg-now span { display: flex; flex-direction: column; line-height: 1.2; }
.rg-now em { font-style: normal; font-family: var(--mono); font-size: 10.5px; color: var(--ink-3); }
.rg-now-na { font-family: var(--mono); font-size: 11.5px; color: var(--ink-3); }
.rg-sq { display: inline-block; width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; margin-right: 4px; vertical-align: -1px; }
.rg-marks { position: relative; height: 14px; }
.rg-mark { position: absolute; top: 1px; width: 1.5px; height: 12px; }
.rg-win { background: #17a565; } .rg-loss { background: #d04a3c; }
.rg-axis { position: relative; height: 16px; }
.rg-tick { position: absolute; transform: translateX(-50%); font-family: var(--mono); font-size: 10.5px; color: var(--ink-3); }
.rg-axis-row { margin-top: -2px; }
.rg-legend .rg-tk { display: inline-block; width: 2px; height: 10px; margin-right: 4px; }
.rg-ptable { margin-top: 8px; }
.rg-prow { display: grid; grid-template-columns: 190px 56px 64px minmax(0, 1fr) 80px 110px; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 12.5px; }
:root[data-theme="light"] .rg-prow { border-bottom-color: #f3f4f6; }
.rg-prow b { font-weight: 600; color: var(--ink); }
.rg-phead { font-size: 10.5px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; color: var(--ink-3); padding-top: 0; }
.rg-prow-na b { color: var(--ink-3); }
@media (max-width: 900px) {
  .rg-row { grid-template-columns: 90px minmax(0, 1fr); }
  .rg-now { display: none; }
}
/* Narrow screens: each phase is a small card -- name and reliability chip
   on the first line, Trades / Win / Net PnL as three labelled columns on
   the second -- so no column header has to squeeze (or drop) a value. */
@media (max-width: 900px) {
  .rg-prow.rg-phead { display: none; }
  .rg-prow { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px 12px; padding: 10px 0; }
  .rg-prow > b { grid-column: 1 / 3; grid-row: 1; min-width: 0; }
  .rg-prow > :nth-child(4) { display: none; }
  .rg-prow > :last-child { grid-column: 3; grid-row: 1; justify-self: end; }
  .rg-prow > :is(:nth-child(2), :nth-child(3), :nth-child(5)) { grid-row: 2; text-align: left !important; white-space: nowrap; }
  .rg-prow > :is(:nth-child(2), :nth-child(3), :nth-child(5))::before {
    display: block; margin-bottom: 2px; font-family: var(--sans); font-size: 10.5px; font-weight: 500; color: var(--ink-3); }
  .rg-prow > :nth-child(2)::before { content: "Trades"; }
  .rg-prow > :nth-child(3)::before { content: "Win"; }
  .rg-prow > :nth-child(5)::before { content: "Net PnL (USDT)"; }
}
/* Phones: the Monte Carlo charts are drawn at ~40% of their 760-unit
   viewBox, so the axis text is sized up to stay readable; the x labels drop
   half a line to keep clear of the lowest y label. */
@media (max-width: 640px) {
  .mc-svg { overflow: visible; }
  .mc-svg .mc-tick { font-size: 26px; }
  .mc-svg .mc-tick-x { transform: translateY(0.8em); }
  .mc-svg .mc-x0, .mc-svg .mc-tick-note { display: none; }
}

.cv-tiles { display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 10px; }
.cv-tile { padding: 14px 16px; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); }
:root[data-theme="light"] .cv-tile { background: #fff; border-color: rgba(20, 22, 26, 0.06); }
.cv-tile-l { font-size: 12px; color: var(--ink-3); }
.cv-big { margin-top: 6px; font-family: var(--mono); font-size: 28px; font-weight: 700; }
.cv-big span { margin-left: 6px; font-family: var(--sans); font-size: 12px; font-weight: 500; color: var(--ink-3); }
.cv-mid { margin-top: 6px; font-family: var(--mono); font-size: 20px; font-weight: 700; color: var(--ink); }
.cv-unit { font-family: var(--sans); font-size: 12px; font-weight: 500; color: var(--ink-3); }
.cv-wrap .cov-stacked-bar { border-radius: 10px !important; overflow: hidden; }
@media (max-width: 1000px) {
  .mk-specs { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cv-tiles { grid-template-columns: minmax(0, 1fr); }
}
.pv-pair .notice { font-size: 12.5px !important; line-height: 1.5; }
/* Deep-dive card: four panes behind one tab bar (redesign preview) */
.dd-card {
  margin-top: 1.15rem;
  padding: 18px 26px 22px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  min-width: 0;
}
:root[data-theme="light"] .dd-card { background: #fff; border-color: rgba(20, 22, 26, 0.06); box-shadow: 0 1px 2px rgba(20, 22, 26, 0.03), 0 10px 24px -16px rgba(20, 22, 26, 0.08); }
.tab-panel > .dd-card { grid-column: 1 / -1; width: 100%; box-sizing: border-box; }
.dd-tabbar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: var(--panel-2);
}
:root[data-theme="light"] .dd-tabbar { background: #f1f2f4; }
.dd-tab {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 8px 12px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s ease, box-shadow 0.15s ease;
}
.dd-tab:hover { background: rgba(255, 255, 255, 0.06); }
:root[data-theme="light"] .dd-tab:hover { background: rgba(255, 255, 255, 0.6); }
.dd-tab-l { font-size: 12.5px; font-weight: 600; color: var(--ink-3); }
:root[data-theme="light"] .dd-tab-l { color: #62666f; }
.dd-tab-v { font-family: var(--mono); font-size: 11px; color: var(--ink-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
:root[data-theme="light"] .dd-tab-v { color: #9296a0; }
.dd-card:not([data-active="cach-choi"]) > #cach-choi { display: none !important; }
.dd-card[data-active="cach-choi"] .dd-tab[data-pane="cach-choi"] { background: var(--panel); box-shadow: 0 1px 3px rgba(20, 22, 26, 0.12); }
.dd-card[data-active="cach-choi"] .dd-tab[data-pane="cach-choi"] .dd-tab-l { color: var(--ink); }
.dd-card:not([data-active="tang-truong"]) > #tang-truong { display: none !important; }
.dd-card[data-active="tang-truong"] .dd-tab[data-pane="tang-truong"] { background: var(--panel); box-shadow: 0 1px 3px rgba(20, 22, 26, 0.12); }
.dd-card[data-active="tang-truong"] .dd-tab[data-pane="tang-truong"] .dd-tab-l { color: var(--ink); }
.dd-card:not([data-active="nhan-dinh"]) > #nhan-dinh { display: none !important; }
.dd-card[data-active="nhan-dinh"] .dd-tab[data-pane="nhan-dinh"] { background: var(--panel); box-shadow: 0 1px 3px rgba(20, 22, 26, 0.12); }
.dd-card[data-active="nhan-dinh"] .dd-tab[data-pane="nhan-dinh"] .dd-tab-l { color: var(--ink); }
.dd-card:not([data-active="diem-chieu"]) > #diem-chieu { display: none !important; }
.dd-card[data-active="diem-chieu"] .dd-tab[data-pane="diem-chieu"] { background: var(--panel); box-shadow: 0 1px 3px rgba(20, 22, 26, 0.12); }
.dd-card[data-active="diem-chieu"] .dd-tab[data-pane="diem-chieu"] .dd-tab-l { color: var(--ink); }
/* The panes sit flat inside the deep-dive card, not as cards of their own. */
.dd-card > section.card,
.bot-report-inner-main .dd-card > section.card {
  margin: 16px 0 0 !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
  animation: ddIn 0.18s ease;
}
.dd-card > section.card > .block-b { padding: 0; }
@keyframes ddIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }
@media (max-width: 700px) {
  .dd-card { padding: 14px 16px 18px; }
  .dd-tabbar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
/* id="diem-chieu": dimension rows + "by tier" donut card, redesign preview */
.dm-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
.dm-left { min-width: 0; }
.dm-rows { margin-top: 8px; display: flex; flex-direction: column; }
.dm-row {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 118px;
  align-items: center;
  gap: 14px;
  padding: 6px 0;
}
.dm-name { font-size: 13px; color: var(--ink-2); min-width: 0; }
:root[data-theme="light"] .dm-name { color: #40444d; }
.dm-name .metric-label-row { justify-content: space-between !important; }
.dm-name .metric-label-row .formula-star-btn { margin: 0 !important; font-size: 11px !important; }
.dm-track { position: relative; display: block; height: 10px; border-radius: 5px; background: var(--panel-3); overflow: hidden; }
:root[data-theme="light"] .dm-track { background: #f1f2f4; }
.dm-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 5px; }
.dm-val { display: flex; align-items: center; justify-content: flex-end; gap: 8px; }
.dm-num { font-family: var(--mono); font-size: 13px; font-weight: 700; color: var(--ink); }
.dm-num-na { color: var(--ink-3); font-weight: 500; }
.dm-pill { font-size: 10.5px; font-weight: 600; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.dm-t-healthy, .dm-dot-healthy { background: #4f9d5d; }
.dm-t-watch, .dm-dot-watch { background: #eab308; }
.dm-t-elevated, .dm-dot-elevated { background: #eab308; }
.dm-t-high, .dm-dot-high { background: #cf5a4a; }
.dm-t-critical, .dm-dot-critical { background: #9b3b32; }
.dm-p-healthy { background: rgba(79, 157, 93, 0.16); color: #5fb36d; }
.dm-p-watch { background: rgba(195, 144, 46, 0.16); color: #facc15; }
.dm-p-elevated { background: rgba(217, 129, 74, 0.16); color: #facc15; }
.dm-p-high { background: rgba(207, 90, 74, 0.16); color: #e06a5a; }
.dm-p-critical { background: rgba(155, 59, 50, 0.22); color: #e0786c; }
.dm-p-na { background: var(--panel-2); color: var(--ink-3); }
:root[data-theme="light"] .dm-p-healthy { background: #e4f5ea; color: #3f8c4d; }
:root[data-theme="light"] .dm-p-watch { background: #fef6d8; color: #ca8a04; }
:root[data-theme="light"] .dm-p-elevated { background: #fef6d8; color: #ca8a04; }
:root[data-theme="light"] .dm-p-high { background: #fbe4e1; color: #b8443a; }
:root[data-theme="light"] .dm-p-critical { background: #f6dcd9; color: #8c2f27; }
:root[data-theme="light"] .dm-p-na { background: #eef0f3; color: #62666f; }
.dm-t-healthy, .dm-dot-healthy { background: #3f9d63; }
.dm-t-watch, .dm-dot-watch, .dm-t-elevated, .dm-dot-elevated { background: #eab308; }
.dm-t-high, .dm-dot-high, .dm-t-critical, .dm-dot-critical { background: #c8473b; }
.dm-p-healthy { background: rgba(16, 185, 129, 0.14); color: var(--up); }
.dm-p-watch, .dm-p-elevated { background: rgba(234, 179, 8, 0.14); color: var(--amber); }
.dm-p-high, .dm-p-critical { background: rgba(244, 63, 94, 0.14); color: var(--down); }
:root[data-theme="light"] .dm-p-healthy { background: #e4f5ea; color: #16794a; }
:root[data-theme="light"] .dm-p-watch, :root[data-theme="light"] .dm-p-elevated { background: #fef6d8; color: #ca8a04; }
:root[data-theme="light"] .dm-p-high, :root[data-theme="light"] .dm-p-critical { background: #fbeae9; color: #af3327; }
.dm-card { padding: 16px 18px; }
.dm-donut { display: flex; justify-content: center; margin: 10px 0 12px; }
.dm-donut .pie-chart { width: 150px; height: 150px; }
.dm-legend { gap: 7px; }
.dm-band { font-family: var(--mono); font-size: 11px; color: var(--ink-3); margin-left: 4px; }
.dm-leg-zero { opacity: 0.45; }
.dn-seg.dn-dm-healthy { stroke: #4f9d5d; }
.dn-seg.dn-dm-watch { stroke: #eab308; }
.dn-seg.dn-dm-elevated { stroke: #eab308; }
.dn-seg.dn-dm-high { stroke: #cf5a4a; }
.dn-seg.dn-dm-critical { stroke: #9b3b32; }
.dn-seg.dn-dm-healthy { stroke: #3f9d63; }
.dn-seg.dn-dm-watch, .dn-seg.dn-dm-elevated { stroke: #eab308; }
.dn-seg.dn-dm-high, .dn-seg.dn-dm-critical { stroke: #c8473b; }
@media (max-width: 900px) {
  .dm-grid { grid-template-columns: minmax(0, 1fr); }
  .dm-row { grid-template-columns: minmax(0, 1fr) 90px; }
  .dm-row .dm-track { grid-column: 1 / -1; order: 3; }
}
/* id="nhan-dinh": core thesis bar + three evidence cards, redesign preview */
.ex-wrap { display: flex; flex-direction: column; gap: 12px; }
.ex-thesis {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 12px;
  background: rgba(56, 189, 248, 0.08);
  font-size: 13px;
  line-height: 1.5;
  color: var(--ink-2);
}
:root[data-theme="light"] .ex-thesis { background: #f3f6fe; color: #40444d; }
.ex-thesis-k {
  flex-shrink: 0;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--info);
}
:root[data-theme="light"] .ex-thesis-k { color: #2454e0; }
.ex-thesis-v b { color: var(--ink); }
.ex-thesis-sub { display: block; margin-top: 2px; font-size: 12px; color: var(--ink-3); }
.ex-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.ex-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding: 13px 15px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ex-card:hover { border-color: var(--line-2); box-shadow: 0 14px 28px -18px rgba(20, 22, 26, 0.3); }
:root[data-theme="light"] .ex-card { background: #fff; border-color: #eceef1; }
.ex-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ex-tag { font-family: var(--mono); font-size: 10.5px; font-weight: 600; letter-spacing: 0.02em; color: var(--ink-3); }
:root[data-theme="light"] .ex-tag { color: #62666f; }
.ex-badge { font-size: 10.5px; padding: 1px 8px; }
.ex-card-value { display: flex; align-items: baseline; gap: 6px; min-width: 0; }
.ex-num { font-family: var(--mono); font-size: 18px; font-weight: 700; color: var(--ink); white-space: nowrap; }
.ex-unit { font-size: 12px; color: var(--ink-3); }
:root[data-theme="light"] .ex-unit { color: #62666f; }
.ex-meta { display: flex; flex-wrap: wrap; gap: 4px 14px; font-family: var(--mono); font-size: 11.5px; color: var(--ink-3); }
.ex-meta em { font-style: normal; font-family: var(--sans); }
.ex-meta b { font-weight: 500; color: var(--ink-2); }
:root[data-theme="light"] .ex-meta { color: #9296a0; }
:root[data-theme="light"] .ex-meta b { color: #40444d; }
.ex-list { display: flex; flex-direction: column; gap: 6px; }
.ex-rows .quant-audit-tag { white-space: normal; font-family: var(--sans); font-size: 12.5px; font-weight: 600; color: var(--ink); letter-spacing: 0; }
.ex-note { display: flex; align-items: baseline; gap: 10px; padding: 9px 12px; border-radius: 10px; background: var(--panel-2); font-size: 12.5px; color: var(--ink-2); }
:root[data-theme="light"] .ex-note { background: #f6f7f9; color: #40444d; }
.ex-findings { display: flex; flex-direction: column; }
.ex-finding { display: flex; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 12.5px; line-height: 1.5; color: var(--ink-2); }
.ex-finding:last-child { border-bottom: 0; }
.ex-finding-n { flex-shrink: 0; font-family: var(--mono); font-size: 10.5px; font-weight: 600; color: var(--ink-3); padding-top: 2px; }
@media (max-width: 900px) {
  .ex-cards { grid-template-columns: minmax(0, 1fr); }
}
/* id="tang-truong": capital curve + two donut cards, redesign preview */
.gc-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}
.gc-right .win-loss-composition-panel { display: flex; flex-direction: column; gap: 12px; height: 100%; }
.gc-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.gc-note { font-size: 11px; color: var(--ink-3); }
.gc-note-mono { font-family: var(--mono); }
:root[data-theme="light"] .gc-note { color: #9296a0; }
.gc-svg { display: block; width: 100%; height: auto; margin-top: 6px; overflow: visible; }
.gc-grid line.gc-grid, .gc-svg .gc-grid { stroke: var(--line); stroke-width: 1; }
.gc-svg .gc-zero { stroke: var(--line-2); stroke-width: 1; stroke-dasharray: 4 3; }
:root[data-theme="light"] .gc-svg .gc-grid { stroke: #f1f2f4; }
:root[data-theme="light"] .gc-svg .gc-zero { stroke: #e5e7eb; }
.gc-svg .gc-tick { font-family: var(--mono); font-size: 10px; fill: var(--ink-3); }
:root[data-theme="light"] .gc-svg .gc-tick { fill: #9296a0; }
.gc-svg .gc-dd-band { fill: rgba(244, 63, 94, 0.08); }
:root[data-theme="light"] .gc-svg .gc-dd-band { fill: #fbeae9; opacity: 0.6; }
.gc-svg .gc-dd-label { font-family: var(--mono); font-size: 10px; font-weight: 600; fill: var(--down); }
.gc-svg .gc-fill-up { stop-color: var(--up); }
.gc-svg .gc-fill-down { stop-color: var(--down); }
.gc-svg .gc-line { stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.gc-svg .gc-line-up { stroke: var(--up); }
.gc-svg .gc-line-down { stroke: var(--down); }
:root[data-theme="light"] .gc-svg .gc-line-up, :root[data-theme="light"] .gc-svg .gc-end-up { stroke: #3f9d63; }
:root[data-theme="light"] .gc-svg .gc-end-up { fill: #3f9d63; }
.gc-svg .gc-end-up { fill: var(--up); }
.gc-svg .gc-end-down { fill: var(--down); }
.gc-svg .gc-mk { fill: var(--panel); stroke-width: 2; }
:root[data-theme="light"] .gc-svg .gc-mk { fill: #fff; }
.gc-svg .gc-mk-peak { stroke: var(--up); }
.gc-svg .gc-mk-trough { stroke: var(--down); }
.gc-svg .gc-mk-label { font-family: var(--mono); font-size: 10.5px; font-weight: 700; }
.gc-svg .gc-mk-label-peak { fill: var(--up); }
.gc-svg .gc-mk-label-trough { fill: var(--down); }
:root[data-theme="light"] .gc-svg .gc-mk-label-peak, :root[data-theme="light"] .gc-svg .gc-mk-peak { fill: #16794a; }
:root[data-theme="light"] .gc-svg .gc-mk-peak { fill: #fff; stroke: #16794a; }
:root[data-theme="light"] .gc-svg .gc-mk-label-trough { fill: #af3327; }
:root[data-theme="light"] .gc-svg .gc-mk-trough { stroke: #af3327; }
.gc-svg .gc-end-label { font-family: var(--mono); font-size: 11.5px; font-weight: 700; fill: var(--ink); }
.gc-card {
  flex: 1;
  padding: 14px 18px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}
:root[data-theme="light"] .gc-card { background: #fff; border-color: #eceef1; }
.gc-card-body { display: flex; align-items: center; gap: 18px; margin-top: 8px; }
.gc-card-body .pie-chart { width: 112px; height: 112px; flex: 0 0 112px; margin: 0; }
.gc-legend { flex: 1; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.gc-leg-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); }
:root[data-theme="light"] .gc-leg-row { color: #40444d; }
.gc-leg-name { flex: 1; }
.gc-leg-val { font-family: var(--mono); font-weight: 700; color: var(--ink); }
.gc-dot { width: 9px; height: 9px; border-radius: 50%; flex: 0 0 9px; }
.dn-track { stroke: var(--panel-3); }
:root[data-theme="light"] .dn-track { stroke: #eef0f3; }
.dn-seg.dn-good { stroke: var(--up); }
.dn-seg.dn-bad { stroke: rgba(244, 63, 94, 0.55); }
.dn-seg.dn-flat { stroke: var(--ink-3); }
.gc-dot.dn-good { background: var(--up); }
.gc-dot.dn-bad { background: rgba(244, 63, 94, 0.55); }
.gc-dot.dn-flat { background: var(--ink-3); }
:root[data-theme="light"] .dn-seg.dn-good { stroke: #3f9d63; }
:root[data-theme="light"] .dn-seg.dn-bad { stroke: #e3a59c; }
:root[data-theme="light"] .gc-dot.dn-good { background: #3f9d63; }
:root[data-theme="light"] .gc-dot.dn-bad { background: #e3a59c; }
.pie-chart .dn-center { font-family: var(--mono); font-size: 17px; font-weight: 700; fill: var(--ink); }
.pie-chart .dn-sub { font-family: var(--sans); font-size: 8px; font-weight: 600; letter-spacing: 0.05em; fill: var(--ink-3); }
@media (max-width: 900px) {
  .gc-grid { grid-template-columns: minmax(0, 1fr); }
}
.cap { display: inline-block; }
.cap::first-letter { text-transform: uppercase; }
.st-wrap { display: flex; flex-direction: column; gap: 14px; }
.st-tiles {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.st-tile {
  min-width: 0;
  padding: 11px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.st-tile:hover { border-color: var(--line-2); box-shadow: 0 10px 22px -18px rgba(20, 22, 26, 0.35); }
:root[data-theme="light"] .st-tile { background: #fff; border-color: #eceef1; }
.st-tile-l { font-size: 11.5px; color: var(--ink-3); }
:root[data-theme="light"] .st-tile-l { color: #9296a0; }
.st-tile-v {
  margin-top: 3px;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.st-tile-sub { font-family: var(--mono); font-size: 11.5px; font-weight: 500; color: var(--ink-3); }
.st-num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.st-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; }
.st-label, .st-head .st-label {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--ink-3);
  cursor: default;
}
:root[data-theme="light"] .st-label { color: #9296a0; }
.st-chips, .st-pills { display: inline-flex; flex-wrap: wrap; gap: 6px; }
.st-chip, .st-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  cursor: default;
}
.st-chip-good, .st-pill-good { background: rgba(16, 185, 129, 0.14); color: var(--up); }
.st-chip-warn { background: rgba(234, 179, 8, 0.14); color: var(--amber); }
.st-chip-bad, .st-pill-bad { background: rgba(244, 63, 94, 0.14); color: var(--down); }
.st-chip-flat { background: var(--panel-2); color: var(--ink-3); }
:root[data-theme="light"] .st-chip-good, :root[data-theme="light"] .st-pill-good { background: #e4f5ea; color: #16794a; }
:root[data-theme="light"] .st-chip-warn { background: #fef6d8; color: #ca8a04; }
:root[data-theme="light"] .st-chip-bad, :root[data-theme="light"] .st-pill-bad { background: #fbeae9; color: #af3327; }
:root[data-theme="light"] .st-chip-flat { background: #eef0f3; color: #62666f; }
.st-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
#cach-choi .st-phase .table-scroll { margin-top: 6px !important; }
#cach-choi .st-phase table {
  min-width: 720px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
}
#cach-choi .st-phase th {
  background: transparent !important;
  font-family: var(--sans) !important;
  font-size: 10.5px !important;
  font-weight: 600 !important;
  letter-spacing: 0.06em !important;
  color: var(--ink-3) !important;
  padding: 8px 12px !important;
  border-bottom: 1px solid var(--line) !important;
}
#cach-choi .st-phase td {
  padding: 10px 12px !important;
  font-size: 13px !important;
  color: var(--ink-2) !important;
  border-bottom: 1px solid var(--line) !important;
  background: transparent !important;
}
#cach-choi .st-phase tr:last-child td { border-bottom: 0 !important; }
#cach-choi .st-phase tr:hover td { background: var(--panel-2) !important; }
:root[data-theme="light"] #cach-choi .st-phase th { color: #9296a0 !important; border-bottom-color: #eceef1 !important; }
:root[data-theme="light"] #cach-choi .st-phase td { color: #40444d !important; border-bottom-color: #f1f2f4 !important; }
:root[data-theme="light"] #cach-choi .st-phase tr:hover td { background: #f8f9fb !important; }
.st-phase-name { font-weight: 600; color: var(--ink); }
.st-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 9px;
  border-radius: 50%;
  vertical-align: 1px;
}
.st-dot-best { background: var(--up); }
.st-dot-worst { background: var(--down); }
.st-conf {
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 600;
  background: var(--panel-2);
  color: var(--ink-3);
}
.st-conf-bad { background: rgba(244, 63, 94, 0.14); color: var(--down); }
.st-pnl-pos { font-weight: 700; color: var(--up); }
.st-pnl-neg { font-weight: 700; color: var(--down); }
:root[data-theme="light"] .st-pnl-pos { color: #16794a; }
:root[data-theme="light"] .st-pnl-neg { color: #af3327; }
.st-barcell { display: inline-flex; align-items: center; justify-content: flex-end; gap: 8px; }
.st-bar {
  display: inline-block;
  width: 56px;
  height: 5px;
  border-radius: 3px;
  background: var(--panel-3);
  overflow: hidden;
}
:root[data-theme="light"] .st-bar { background: #eceef1; }
.st-bar-fill { display: block; height: 100%; border-radius: 3px; }
.st-bar-win { background: #9aa0aa; }
.st-bar-share { background: var(--up); }
:root[data-theme="light"] .st-bar-share { background: #2f9a64; }
@media (max-width: 900px) {
  .st-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
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

/* Metric tables in Trade metrics, Statistical inference, and Drawdown vs. capital */
#so-lieu table,
#suy-luan table,
#sut-giam-von table {
  width: 100% !important;
  table-layout: fixed !important;
}
#so-lieu th, #so-lieu td,
#suy-luan th, #suy-luan td,
#sut-giam-von th, #sut-giam-von td {
  vertical-align: middle !important;
}
#so-lieu table th:first-child,
#so-lieu table td:first-child,
#suy-luan table th:first-child,
#suy-luan table td:first-child,
#sut-giam-von table th:first-child,
#sut-giam-von table td:first-child {
  width: 68% !important;
  text-align: left !important;
}
#so-lieu table th:last-child,
#so-lieu table td:last-child,
#suy-luan table th:last-child,
#suy-luan table td:last-child,
#sut-giam-von table th:last-child,
#sut-giam-von table td:last-child {
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
  background: rgba(234, 179, 8, 0.15);
  color: #EAB308;
  border: 1px solid rgba(234, 179, 8, 0.35);
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
  filter: drop-shadow(0 0 3px rgba(234, 179, 8, 0.8));
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
  vertical-align: middle !important;
}
.okx-trades-table tbody td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.05));
  font-variant-numeric: tabular-nums;
  vertical-align: middle !important;
}
.okx-trades-table thead th:nth-child(1),
.okx-trades-table tbody td:nth-child(1) {
  text-align: center !important;
  width: 48px;
}
.okx-trades-table thead th:nth-child(2),
.okx-trades-table tbody td:nth-child(2) {
  text-align: left !important;
}
.okx-trades-table thead th:nth-child(3),
.okx-trades-table tbody td:nth-child(3) {
  text-align: left !important;
}
.okx-trades-table thead th:nth-child(4),
.okx-trades-table tbody td:nth-child(4),
.okx-trades-table thead th:nth-child(5),
.okx-trades-table tbody td:nth-child(5) {
  text-align: right !important;
}
.okx-trades-table thead th:nth-child(6),
.okx-trades-table tbody td:nth-child(6) {
  text-align: center !important;
}

/* Traded assets table (#tai-san) */
#tai-san table {
  width: 100% !important;
}
#tai-san th,
#tai-san td {
  vertical-align: middle !important;
}
#tai-san th:nth-child(1),
#tai-san td:nth-child(1) {
  text-align: left !important;
}
#tai-san th:nth-child(2),
#tai-san td:nth-child(2) {
  text-align: center !important;
}
#tai-san th:nth-child(n+3),
#tai-san td:nth-child(n+3) {
  text-align: right !important;
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
/* No frame around the strip as a whole, and no tinted background/border per
   item: the value's own colour carries the good/watch/bad signal (project
   owner: keep only the coloured number). Items share the hero tiles'
   neutral card so the two rows read as one set. */
.quick-risk-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  margin: 14px 0 16px 0;
  padding: 0;
  background: transparent;
  border: none;
}
.qrs-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  background: var(--panel-2);
  border-radius: 6px;
  border: 1px solid var(--line);
  transition: border-color 0.2s ease;
}
:root[data-theme="light"] .qrs-item {
  background: #ffffff;
  border-color: #e2e8f0;
}
.qrs-item:hover {
  border-color: var(--ink-3, #94a3b8);
}
.qrs-label .metric-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
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
.qrs-warn .qrs-value { color: #eab308; }
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
  background: rgba(234, 179, 8, 0.12);
  border: 1px solid rgba(234, 179, 8, 0.35);
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

/* Monte Carlo View Mode Tabs */
.mc-view-tabs {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0 12px 0;
  padding: 4px;
  background: var(--surface-2, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  width: fit-content;
}
:root[data-theme="light"] .mc-view-tabs {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.mc-view-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted, #94a3b8);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  outline: none;
  user-select: none;
}
:root[data-theme="light"] .mc-view-tab-btn {
  color: #64748b;
}
.mc-view-tab-btn:hover {
  color: var(--ink, #ffffff);
  background: rgba(255, 255, 255, 0.05);
}
:root[data-theme="light"] .mc-view-tab-btn:hover {
  color: #0f172a;
  background: #e2e8f0;
}
.mc-view-tab-btn.active {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
  border-color: rgba(56, 189, 248, 0.35);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
:root[data-theme="light"] .mc-view-tab-btn.active {
  color: #0284c7;
  background: #e0f2fe;
  border-color: #7dd3fc;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.mc-tab-icon {
  font-size: 13px;
  line-height: 1;
}
.mc-views-wrapper {
  position: relative;
  width: 100%;
}
.mc-view-panel {
  width: 100%;
}
.mc-view-panel svg {
  display: block;
  width: 100%;
  max-width: 820px;
  height: auto;
  margin: 0 auto;
}

/* Parameter glossary (* notes) below the Outcome distribution chart */
.mc-param-notes {
  margin: 6px 0 2px;
  padding: 6px 14px;
  border-top: 1px solid var(--border, rgba(255,255,255,0.08));
}
:root[data-theme="light"] .mc-param-notes {
  border-top: 1px solid var(--line, #e2e8f0);
}
.mc-param-notes-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  align-items: center;
}
/* mc-param-star: inline-flex so * button aligns perfectly with label text */
.mc-param-star {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 10px;
  font-family: var(--mono, 'SFMono-Regular', monospace);
  font-weight: 700;
  white-space: nowrap;
  color: var(--accent, #818cf8);
}
:root[data-theme="light"] .mc-param-star {
  color: var(--accent-dark, #4f46e5);
}
/* formula-star-btn inside mc-param-star: static position, centered by flex */
.mc-param-star .formula-star-btn {
  position: static !important;
  top: 0 !important;
  margin-left: 0 !important;
  flex-shrink: 0 !important;
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
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
  border: 1px solid rgba(234, 179, 8, 0.35);
}
:root[data-theme="light"] .mc-skew-badge.balanced {
  background: #fffbeb;
  color: #ca8a04;
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
/* Line icons (chat bubble, theme sun/moon) drawn as CSS masks in the text
   colour -- kept out of the markup so the inline vector elements on the
   page stay the charts only. */
.ic-mask { display: inline-block; width: 1em; height: 1em; vertical-align: -0.125em;
  background-color: currentColor; -webkit-mask: var(--ic) center / contain no-repeat;
  mask: var(--ic) center / contain no-repeat; }
.ic-chat { --ic: url('data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"%3E%3Cpath d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/%3E%3C/svg%3E'); width: 18px; height: 18px; }
.ic-sun { --ic: url('data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round"%3E%3Ccircle cx="12" cy="12" r="4"/%3E%3Cpath d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/%3E%3C/svg%3E'); }
.ic-moon { --ic: url('data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"%3E%3Cpath d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/%3E%3C/svg%3E'); }
/* Phones: the page's own top header (seen when a report link is opened
   directly, outside the app) on two rows -- brand + actions, then the
   three tabs full width -- instead of one 700px-wide row. The SPA hides
   this header and draws its own, so this only reaches the static page. */
@media (max-width: 768px) {
  .top-header {
    display: grid; grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas: "brand actions" "nav nav"; align-items: center;
    gap: 10px 8px; height: auto; padding: 10px 12px; }
  .top-header .header-left { display: contents; }
  .top-header .brand { grid-area: brand; min-width: 0; }
  .top-header .header-divider, .top-header .brand-badge-fintech, .top-header .brand-sub,
  .top-header .user-badge-capsule, .top-header .btn-header-cta-text { display: none; }
  .top-header .header-nav-tabs {
    grid-area: nav; width: 100%; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 2px; overflow: visible; }
  .top-header .header-tab { justify-content: center; white-space: nowrap; min-width: 0;
    padding: 0 6px; font-size: 12.5px; }
  .top-header .top-bar-actions { grid-area: actions; gap: 6px; flex-wrap: nowrap; }
  .top-header .btn-header-cta { width: 30px; padding: 0; justify-content: center; }
  .report-subnav-bar { flex-wrap: wrap; gap: 8px 12px; }
  .subnav-crumb { flex-wrap: wrap; font-size: 12px; }
  .subnav-crumb > * { white-space: nowrap; }
}
/* Portfolio additions on the Positions tab: owner tags on the asset and
   ledger rows, the per-bot ledger filter, and "Contribution by bot". */
.as-own, .lg-inst { margin-left: 2px; font-size: 11px; font-weight: 500; color: var(--ink-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lg-inst { font-family: var(--mono); }
.lg-box-pf .lg-row { grid-template-columns: 56px 220px 110px minmax(0, 1fr) 140px 64px; }
.lg-bots .mk-ftab { display: inline-flex; align-items: center; gap: 6px; }
.lg-bots .mk-ftab i { width: 7px; height: 7px; border-radius: 50%; }
.pv-card[data-active="ledger"] .pv-extra[data-for="ledger"] { flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
.as-row[hidden], .rb-row[hidden], .rb-group[hidden] { display: none !important; }
/* Paged bar rows keep the card's stretch layout: the list takes the space,
   the pager sits under it. */
.pv-pair .rb-box { flex: 1; display: flex; flex-direction: column; }
.rb-box .lg-foot { margin-top: 8px; }
/* The status-legend tip sits at the card's right edge: open it leftwards so
   it never widens the page. */
.pv-extra .info-tip { left: auto !important; right: 0 !important; }
a.cb-row { color: var(--ink) !important; }
.cb-row .as-name b { font-family: var(--sans); }
.cb-chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; }
.cb-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; font-size: 11.5px; color: var(--ink-2); }
.cb-legend span { display: inline-flex; align-items: center; gap: 6px; }
.cb-legend i { width: 12px; height: 2px; display: inline-block; }
.cb-legend-r { margin-left: auto; color: var(--ink-3); }
.cb-svg { width: 100%; height: auto; display: block; margin-top: 6px; overflow: visible; }
.cb-svg .cb-grid { stroke: var(--line); stroke-width: 1; stroke-dasharray: 4 3; }
.cb-svg .cb-tick { font-family: var(--mono); font-size: 11px; fill: var(--ink-3); }
.cb-svg .cb-line { fill: none; stroke-width: 1.8; stroke-linejoin: round; }
.cb-svg .cb-win { fill: color-mix(in srgb, var(--down) 10%, transparent); }
.cb-svg .cb-win-l { font-family: var(--mono); font-size: 11px; font-weight: 700; fill: var(--down); }
.cb-table { margin-top: 8px; }
.cb-row { display: grid; grid-template-columns: minmax(0, 1.5fr) 60px 50px 52px minmax(0, 1.6fr) 70px 96px 110px; align-items: center; gap: 12px;
  padding: 9px 6px; border-bottom: 1px solid var(--line); font-size: 12.5px; color: var(--ink-2); text-decoration: none; border-radius: 8px; }
a.cb-row:hover { background: var(--panel-2); }
.cb-head { padding-top: 0; font-size: 10.5px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; color: var(--ink-3); border-radius: 0; }
.cb-total { background: var(--panel-2); border-bottom: 0; margin-top: 4px; }
.cb-total .as-name b { font-family: var(--sans); }
.cb-share { display: flex; align-items: center; gap: 8px; min-width: 0; }
.cb-share .as-track { max-width: 120px; }
.cb-share b { white-space: nowrap; }
.cb-off .cb-off-note { grid-column: 2 / -1; font-size: 12px; color: var(--ink-3); }
@media (max-width: 900px) {
  .cb-head { display: none; }
  .cb-row { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px 12px; padding: 12px 4px; }
  .cb-row > .as-name, .cb-row > .cb-share, .cb-off .cb-off-note { grid-column: 1 / -1; }
  .cb-row > [data-l] { text-align: left !important; }
  .cb-row > [data-l]::before { content: attr(data-l); display: block; font-family: var(--sans); font-size: 10.5px; font-weight: 500; color: var(--ink-3); margin-bottom: 2px; }
  .cb-share::before { margin-right: 6px; }
  .cb-legend-r { margin-left: 0; width: 100%; }
  .cb-svg .cb-tick, .cb-svg .cb-win-l { font-size: 30px; }
}
/* Conclusion card: title row like the other cards, "Why" under it. */
.conclusion-title { font-size: 14px; font-weight: 700; color: var(--ink); }
.conclusion-why-label { margin: 14px 0 8px; }
/* The short answer (top of every report) and the one-line answer that opens
   the Markets / Trades & positions tabs. */
.short-answer { margin: 0 0 12px; padding: 18px 22px; border-radius: 14px; background: var(--panel);
  border: 1px solid var(--line); border-left: 5px solid var(--ink-3); }
.short-answer.sa-danger { border-left-color: var(--down); }
.short-answer.sa-warning { border-left-color: var(--amber); }
.short-answer.sa-success { border-left-color: var(--up); }
.sa-title { margin: 0; font-size: 19px; font-weight: 700; letter-spacing: -0.01em; line-height: 1.3; color: var(--ink); }
.sa-verdict { margin-top: 6px; display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--ink-3); }
.sa-verdict i { width: 6px; height: 6px; border-radius: 50%; flex: none; }
.sa-figs { margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
.sa-fig { background: var(--panel-2); border-radius: 12px; padding: 11px 14px; min-width: 0; }
.sa-fig-l { font-size: 12px; color: var(--ink-3); }
.sa-fig-v { margin-top: 3px; font-size: 16px; font-weight: 700; color: var(--ink); }
.sa-t-good { color: var(--up) !important; } .sa-t-bad { color: var(--down) !important; } .sa-t-warn { color: var(--amber) !important; }
.tab-answer { display: flex; align-items: center; gap: 12px 20px; flex-wrap: wrap; margin: 0 0 16px; padding: 14px 20px;
  border-radius: 14px; background: var(--panel); border: 1px solid var(--line); }
.tab-answer-h { flex: 1 1 260px; font-size: 15px; font-weight: 700; color: var(--ink); }
.tab-answer-f { display: flex; gap: 8px; flex-wrap: wrap; }
.tab-answer-f span { display: inline-flex; align-items: baseline; gap: 6px; padding: 6px 11px; border-radius: 10px;
  background: var(--panel-2); font-size: 12px; color: var(--ink-3); white-space: nowrap; }
.tab-answer-f b { font-family: var(--mono); font-size: 13px; font-weight: 700; color: var(--ink); }
.stat-hint { display: block; flex-basis: 100%; font-size: 10.5px; font-weight: 500; color: var(--ink-3); text-transform: none; letter-spacing: 0; }
/* The verdict now reads inside the short answer; the header copy is hidden. */
.short-answer ~ * .report-verdict-chip, .report-hero-top .report-verdict-chip { display: none !important; }
@media (max-width: 640px) {
  .short-answer { padding: 14px; }
  .sa-title { font-size: 17px; }
  .sa-figs { grid-template-columns: minmax(0, 1fr); gap: 8px; }
  .tab-answer { padding: 12px 14px; }
  .tab-answer-f span { white-space: normal; }
}
/* Caveats as one short line; the full text behind the ⓘ. */
.note-chip { display: inline-flex; align-items: center; gap: 7px; width: fit-content; align-self: flex-start; max-width: 100%; margin: 0 0 12px; padding: 5px 11px;
  border-radius: 12px; font-size: 12px; font-weight: 600; background: color-mix(in srgb, var(--amber) 12%, transparent);
  color: color-mix(in srgb, var(--amber) 75%, var(--ink)); }
.note-chip.notice-danger-chip { background: color-mix(in srgb, var(--down) 11%, transparent); color: color-mix(in srgb, var(--down) 80%, var(--ink)); }
.note-chip .nc-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }
.note-chip .nc-text { white-space: normal; }
.note-chip .info-ic .info-tip { width: min(280px, 78vw); left: -20px; right: auto; font-weight: 400; }

/* ---- Overview / Detail ------------------------------------------------ */
.report-modes { display: flex; flex-direction: column; gap: 16px; }
.rm-bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.rm-seg { display: inline-flex; gap: 4px; padding: 4px; border-radius: 10px;
  background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.07); }
:root[data-theme="light"] .rm-seg { background: rgba(15, 23, 42, 0.04); border-color: rgba(15, 23, 42, 0.08); }
.rm-btn { border: 1px solid transparent; background: transparent; padding: 7px 20px; border-radius: 7px;
  font: inherit; font-size: 13px; font-weight: 600; color: var(--ink-2); cursor: pointer; }
.rm-btn:hover { color: var(--ink); }
.report-modes[data-mode="overview"] .rm-btn-overview,
.report-modes[data-mode="detail"] .rm-btn-detail { background: var(--panel); color: var(--ink); border-color: var(--line); box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08); }
.rm-hint { font-size: 12px; color: var(--muted); }
.report-modes[data-mode="overview"] .rm-hint-detail,
.report-modes[data-mode="detail"] .rm-hint-overview,
.report-modes[data-mode="overview"] > .rm-detail,
.report-modes[data-mode="detail"] > .rm-overview { display: none; }
.rm-overview { display: flex; flex-direction: column; gap: 18px; }
/* One even rhythm: the cards' own stacking margins (page + SPA) are for
   the long Detail flow, not for these three blocks. */
.rm-overview .ov-block > .card,
.bot-report-spa-container .rm-overview .ov-block > .card { margin: 0 !important; }
.ov-title { font-size: 15px; font-weight: 700; color: var(--ink); margin: 0 0 12px; }
/* Overview cards: the preview's soft card -- one padding, rounder corners,
   a hairline border instead of the Detail flow's framed block. */
.rm-overview .ov-block > .card,
.bot-report-spa-container .rm-overview .ov-block > .card { padding: 0 !important; border-radius: 16px !important; overflow: hidden; }
.rm-overview .ov-block > .card > .block-b,
.bot-report-spa-container .rm-overview .ov-block > .card > .block-b { padding: 22px 26px !important; }
:root[data-theme="light"] .rm-overview .ov-block > .card { border-color: #eceef1 !important; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important; }
@media (max-width: 760px) {
  .rm-overview .ov-block > .card > .block-b,
  .bot-report-spa-container .rm-overview .ov-block > .card > .block-b { padding: 16px 14px !important; }
}
.mc-ov-median { margin-top: 14px; }
.rm-overview .mc-wrap > .note-chip { margin: 10px 0 0; }
.mc-ov-median .mc-svg { width: 100%; height: auto; }
/* Assessment colour only: a median that ends in profit is green, in loss red. */
.rm-overview .mc-ov-good .mc-svg .mc-median, .rm-overview .mc-ov-good .mc-svg .mc-median-pt { stroke: var(--up); }
.rm-overview .mc-ov-good .mc-svg .mc-fan-stop { stop-color: var(--up); }
.rm-overview .mc-ov-good .mc-lg-med { background: var(--up) !important; }
.rm-overview .mc-ov-bad .mc-svg .mc-median, .rm-overview .mc-ov-bad .mc-svg .mc-median-pt { stroke: var(--down); }
.rm-overview .mc-ov-bad .mc-svg .mc-fan-stop { stop-color: var(--down); }
.rm-overview .mc-ov-bad .mc-lg-med { background: var(--down) !important; }
.mc-ov-median .mc-legend-median { display: inline-flex; margin-bottom: 6px; }
@media (max-width: 760px) {
  .rm-seg { width: 100%; display: grid; grid-template-columns: 1fr 1fr; }
  .rm-hint { display: none; }
}

/* ---- Portfolio: joint Monte Carlo, per-bot lines ------------------------ */
.mc-svg .mc-member { fill: none; stroke-width: 1.4; stroke-opacity: 0.9; stroke-linejoin: round; }
.mc-pcards.mc-pcards-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.mc-ov-note { margin-top: 12px; font-size: 12.5px; color: var(--muted); }
.jv-grid { margin-top: 18px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.jv-card { border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.jv { display: grid; grid-template-columns: minmax(84px, 130px) minmax(0, 1fr) 56px; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--line); }
.jv:last-of-type { border-bottom: none; }
.jv-l { display: flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 600; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.jv-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.jv-plot { position: relative; height: 6px; border-radius: 3px; background: rgba(148, 163, 184, 0.18); overflow: hidden; }
.jv-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 3px; }
.jv-good { background: var(--up); } .jv-warn { background: var(--amber); } .jv-bad { background: var(--down); } .jv-ink { background: var(--muted); }
.jv-v { text-align: right; font-family: var(--mono); font-size: 13px; }
.jv-foot { margin-top: 8px; display: flex; gap: 16px; font-size: 11.5px; color: var(--muted); font-family: var(--mono); }
.jv-foot em { font-style: normal; margin-right: 6px; }
.gc-mlegend { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 11.5px; color: var(--ink-2); }
.gc-mlegend span { display: inline-flex; align-items: center; gap: 6px; }
.gc-mlegend i { width: 14px; height: 2px; border-radius: 2px; display: inline-block; }
.gc-mlegend .gc-mlegend-off { color: var(--muted); }
.gc-svg .gc-member { fill: none; stroke-width: 1.3; stroke-opacity: 0.9; stroke-linejoin: round; }
.gc-svg text, .uw-svg text { paint-order: stroke; stroke: var(--panel); stroke-width: 3px; stroke-linejoin: round; }
.uw-block { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--line); }
.uw-svg { width: 100%; height: auto; display: block; margin-top: 8px; }
.uw-svg .uw-grid { stroke: rgba(148, 163, 184, 0.18); } .uw-svg .uw-zero { stroke: rgba(148, 163, 184, 0.55); stroke-dasharray: 4 3; }
.uw-svg .uw-tick { font-family: var(--mono); font-size: 10px; fill: var(--muted); }
.uw-svg .uw-area { fill: var(--down); fill-opacity: 0.12; }
.uw-svg .uw-line { fill: none; stroke: var(--down); stroke-width: 2.2; stroke-linejoin: round; }
.uw-svg .uw-member { fill: none; stroke-width: 1.3; stroke-opacity: 0.9; stroke-linejoin: round; }
.uw-svg .uw-mk { fill: var(--panel); stroke: var(--down); stroke-width: 2; }
.uw-svg .uw-lbl { font-family: var(--mono); font-size: 10.5px; font-weight: 700; fill: var(--down); }
@media (max-width: 760px) {
  .jv-grid { grid-template-columns: minmax(0, 1fr); }
  .mc-pcards.mc-pcards-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

/* Joint Monte Carlo: assessment colours only -- the combined median and its
   band green when the median ends in profit, red when in loss. */
.mc-joint.mc-tone-good .mc-svg .mc-median, :root[data-theme="light"] .mc-joint.mc-tone-good .mc-svg .mc-median { stroke: var(--up); }
.mc-joint.mc-tone-good .mc-svg .mc-fan-stop, :root[data-theme="light"] .mc-joint.mc-tone-good .mc-svg .mc-fan-stop { stop-color: var(--up); }
.mc-joint.mc-tone-good .mc-svg .mc-band-inner, :root[data-theme="light"] .mc-joint.mc-tone-good .mc-svg .mc-band-inner { fill: var(--up); fill-opacity: 0.12; }
.mc-joint.mc-tone-good .mc-svg .mc-path-win, :root[data-theme="light"] .mc-joint.mc-tone-good .mc-svg .mc-path-win { stroke: var(--up); }
.mc-joint.mc-tone-good .mc-svg .mc-median-pt, :root[data-theme="light"] .mc-joint.mc-tone-good .mc-svg .mc-median-pt { stroke: var(--up); }
.mc-joint.mc-tone-good .mc-lg-med { background: var(--up) !important; }
.mc-joint.mc-tone-good .mc-svg .mc-tag-mid { fill: var(--up); }
.mc-joint.mc-tone-bad .mc-svg .mc-median, :root[data-theme="light"] .mc-joint.mc-tone-bad .mc-svg .mc-median { stroke: var(--down); }
.mc-joint.mc-tone-bad .mc-svg .mc-fan-stop, :root[data-theme="light"] .mc-joint.mc-tone-bad .mc-svg .mc-fan-stop { stop-color: var(--down); }
.mc-joint.mc-tone-bad .mc-svg .mc-median-pt, :root[data-theme="light"] .mc-joint.mc-tone-bad .mc-svg .mc-median-pt { stroke: var(--down); }
.mc-joint.mc-tone-bad .mc-lg-med { background: var(--down) !important; }
.mc-joint.mc-tone-bad .mc-svg .mc-tag-mid { fill: var(--down); }
.mc-joint .mc-lad-med i { background: var(--up); }
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


def _apply_std_drawdown(result: Dict[str, Any]) -> Dict[str, Any]:
    """One max drawdown for the whole page (project owner, 2026-09-25): the
    standard (peak equity - trough equity) / peak equity on the bot's real
    closed trades, equity = reference capital + cumulative PnL -- the same
    path and formula the Monte Carlo uses, and the figure the header strip,
    the Drawdown card and the simulation's "actual" all show. Replaces the
    engine's per-trade-equity figure in Trade metrics (kept as
    `_engine_max_drawdown_pct`); Calmar is re-based on it so it divides by
    the drawdown shown next to it."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    pnls = [float(x["realized_pnl"]) for x in (evidence.get("closed_trade_series") or [])
            if isinstance(x, dict) and _is_finite_number(x.get("realized_pnl"))]
    cap = _ref_capital(result)
    if not pnls or cap is None or not perf:
        return result
    eq = peak = cap
    mdd = 0.0
    for v in pnls:
        eq += v
        peak = max(peak, eq)
        mdd = max(mdd, min(1.0, (peak - eq) / peak) if peak > 0 else 1.0)
    cur = min(1.0, max(0.0, (peak - eq) / peak)) if peak > 0 else 1.0
    perf = dict(perf)
    old = perf.get("max_drawdown_pct")
    perf["_engine_max_drawdown_pct"] = old
    perf["max_drawdown_pct"] = mdd * 100.0
    perf["current_drawdown_pct"] = cur * 100.0
    perf["_dd_basis"] = "STD"
    cal = perf.get("calmar_ratio")
    detail = perf.get("_calmar_detail") if isinstance(perf.get("_calmar_detail"), dict) else {}
    if mdd > 0 and _is_finite_number(detail.get("annualised_pct")):
        perf["calmar_ratio"] = float(detail["annualised_pct"]) / (mdd * 100.0)
    elif mdd > 0 and _is_finite_number(cal) and _is_finite_number(old) and float(old) > 0:
        perf["calmar_ratio"] = float(cal) * float(old) / (mdd * 100.0)
    return {**result, "evidence": {**evidence, "performance": perf}}


def _apply_offline(result: Dict[str, Any], offline: Dict[str, Any]) -> Dict[str, Any]:
    """Fill what a saved report does not store (current drawdown, Calmar,
    scenario laboratory) from `data.offline_bot_metrics` -- only when the
    bot's files still describe the same ledger as the saved report (same
    trade count and max drawdown); otherwise nothing is taken."""
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
    tc, dd = perf.get("trade_count"), perf.get("max_drawdown_pct")
    if not (_is_finite_number(tc) and _is_finite_number(offline.get("trade_count")) and int(tc) == int(offline["trade_count"])):
        return result
    edd = offline.get("engine_max_drawdown_pct", offline.get("max_drawdown_pct"))
    if _is_finite_number(dd) and _is_finite_number(edd) and abs(float(dd) - float(edd)) > 0.05:
        return result
    tp = perf.get("total_pnl")
    if _is_finite_number(tp) and _is_finite_number(offline.get("total_pnl")) and abs(float(tp) - float(offline["total_pnl"])) > max(0.05, abs(float(tp)) * 1e-6):
        return result
    perf = dict(perf)
    dd_basis = offline.get("drawdown_basis")
    if perf.get("current_drawdown_pct") is None and _is_finite_number(offline.get("current_drawdown_pct")):
        perf["current_drawdown_pct"] = float(offline["current_drawdown_pct"])
        # Max drawdown only comes along when the saved one is missing, so the
        # two rows always share one basis.
        if perf.get("max_drawdown_pct") is None and _is_finite_number(offline.get("max_drawdown_pct")):
            perf["max_drawdown_pct"] = float(offline["max_drawdown_pct"])
            perf["_dd_basis"] = dd_basis
        elif dd_basis != "EQUITY_AT_TRADE" and perf.get("max_drawdown_pct") is not None:
            # A saved max drawdown on another basis: do not pair it with a
            # current drawdown measured differently.
            perf["current_drawdown_pct"] = None
        else:
            perf["_dd_basis"] = dd_basis
    if perf.get("calmar_ratio") is None and _is_finite_number(offline.get("calmar_ratio")):
        perf["calmar_ratio"] = float(offline["calmar_ratio"])
    if offline.get("calmar_basis"):
        perf["_calmar_basis"] = offline["calmar_basis"]
        perf["_calmar_detail"] = offline.get("calmar_detail")
    out = {**result, "evidence": {**evidence, "performance": perf}}
    if isinstance(offline.get("scenario_laboratory"), dict):
        out["_offline_lab"] = offline["scenario_laboratory"]
    return out


def _render_bot_report_html(
    result: Dict[str, Any],
    *,
    is_admin: bool = False,
    admin_back_url: str = "/#/admin",
    snapshot_at_ms: Optional[int] = None,
    refresh_url: Optional[str] = None,
    is_stale: bool = False,
    hidden_panels: Sequence[str] = (),
    peer_rows: Optional[List[Dict[str, Any]]] = None,
    regime_timelines: Optional[List[Dict[str, Any]]] = None,
    pair_stats: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
    ledger: Optional[List[Dict[str, Any]]] = None,
    offline: Optional[Dict[str, Any]] = None,
    stylesheet_href: Optional[str] = None,
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

    `peer_rows` (the `/api/bots` rows) feeds the Conclusion's peer comparison;
    without it that block is simply not rendered.
    """
    if not isinstance(result, dict):
        result = {}
    if peer_rows:
        # Shallow copy: the caller's dict (possibly a cached snapshot) is
        # never mutated; `_render_peer_comparison` reads it from here.
        result = {**result, "_peer_rows": peer_rows}
    if regime_timelines:
        result = {**result, "_regime_timelines": regime_timelines}
    if pair_stats:
        result = {**result, "_pair_stats": pair_stats}
    if not ledger:
        # A merged book has no single ledger file; any fresh result carries
        # the instrument on each series row anyway.
        ledger = _ledger_from_series(result) or None
    if ledger:
        result = {**result, "_ledger": ledger}
    if offline:
        result = _apply_offline(result, offline)
    result = _apply_std_drawdown(result)
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
        # Đứng NGOÀI `tabs_html` có chủ đích -- hiện xuyên suốt bất kể tab
        # nào đang mở, không đếm vào bất kỳ tab nào. Nếu cả ba tab rỗng,
        # nhánh ngay dưới đây thay thế TOÀN BỘ `body` bằng trang "not found",
        # nên widget cũng biến mất theo -- đúng ý, không cần điều kiện riêng.
        modes_html = _render_report_modes(_render_overview(result), tabs_html)
        body = f"{header_html}{modes_html}{_render_chat_widget(result)}{_FORMULA_MODAL_MARKUP}"
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
        '<span class="theme-icon theme-icon-light"><span class="ic-mask ic-sun"></span> Light</span>'
        '<span class="theme-icon theme-icon-dark"><span class="ic-mask ic-moon"></span> Dark</span>'
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
        # Theme applied before first paint: the runtime script that also does
        # this sits at the end of <body>, so the page used to paint in the
        # default palette first and then flip (dark -> light on every reload).
        "<script data-theme-init>try{var t=localStorage.getItem('norabt_theme');"
        "if(t==='dark'||t==='light'){document.documentElement.setAttribute('data-theme',t);}}catch(e){}</script>\n"
        # Served routes pass `stylesheet_href` (see `report_stylesheet`): the
        # 260 KB of CSS is then fetched once and cached by the browser instead
        # of riding inside every report. Without it the page stays
        # self-contained (tests, saved copies).
        + (f'<link rel="stylesheet" href="{_esc(stylesheet_href)}">\n' if stylesheet_href
           else f"<style>{_design_tokens_css_text()}\n{_CSS}</style>\n")
        + "</head>\n<body>\n"
        f"{top_header}"
        f'<div class="page">{sidebar_html}'
        f'<div class="main">{admin_banner}{snapshot_banner}{body}{footer}</div>'
        "</div>\n"
        f"{_RUNTIME_SCRIPT}\n"
        f"{_formula_override_script()}"
        "</body>\n</html>\n"
    )



def render_bot_report_html(result: Dict[str, Any], **kwargs: Any) -> str:
    """Render one report page; see `_render_bot_report_html` for the options.

    Sets this render's formula overrides (`result["formula_overrides"]`,
    present on portfolio pages only) for every label drawn below, and clears
    them afterwards so one page's wording can never leak into the next.
    """
    overrides = result.get("formula_overrides") if isinstance(result, dict) else None
    token = _FORMULA_OVERRIDES.set(
        overrides if isinstance(overrides, dict) and overrides else None
    )
    try:
        return _render_bot_report_html(result, **kwargs)
    finally:
        _FORMULA_OVERRIDES.reset(token)

_FORMULA_MODAL_MARKUP = (
    '<div id="formula-modal-overlay" class="formula-modal-overlay" '
    'onclick="closeFormulaModal()" role="presentation">'
    '<div class="formula-modal" role="dialog" aria-modal="true" '
    'aria-labelledby="formula-modal-title" onclick="event.stopPropagation()">'
    '<button type="button" class="formula-modal-close" '
    'onclick="closeFormulaModal()" aria-label="Close">&times;</button>'
    '<div id="formula-modal-title" class="formula-modal-title"></div>'
    '<div class="formula-modal-row">'
    '<span class="formula-modal-tag">FORMULA</span>'
    '<div id="formula-modal-formula" class="formula-modal-formula"></div>'
    '</div>'
    '<div class="formula-modal-row">'
    '<span class="formula-modal-tag">CRITERIA</span>'
    '<div id="formula-modal-desc" class="formula-modal-desc"></div>'
    '</div>'
    '</div>'
    '</div>'
)


_RUNTIME_SCRIPT = (
    '<script id="report-runtime">\n'
    f'window.METRIC_INFO = {json.dumps(METRIC_FORMULA_INFO, ensure_ascii=False)};\n'
    """// One handler per job on `document`, however many times this script runs:
// the SPA re-runs it on every report it opens, and a plain addEventListener
// stacked one more copy each time. The newest copy replaces the previous one.
window.__noraOn = window.__noraOn || function(key, type, fn) {
  var reg = window.__noraHandlers || (window.__noraHandlers = {});
  if (reg[key]) document.removeEventListener(reg[key][0], reg[key][1]);
  reg[key] = [type, fn];
  document.addEventListener(type, fn);
};
window.openFormulaModal = function(key) {
  var info = (window.METRIC_INFO || {})[key];
  var overlay = document.getElementById('formula-modal-overlay');
  if (!info || !overlay) return;
  var titleEl = document.getElementById('formula-modal-title');
  var formulaEl = document.getElementById('formula-modal-formula');
  var descEl = document.getElementById('formula-modal-desc');
  if (titleEl) titleEl.textContent = info.title || key;
  if (formulaEl) formulaEl.textContent = info.formula || '';
  if (descEl) descEl.textContent = info.desc || '';
  overlay.classList.add('open');
};
window.closeFormulaModal = function() {
  var overlay = document.getElementById('formula-modal-overlay');
  if (overlay) overlay.classList.remove('open');
};
__noraOn('r1', 'keydown', function(ev) {
  if (ev.key === 'Escape') window.closeFormulaModal();
});
window.switchMcViewTab = function(btn, tabId) {
  try {
    var panel = btn.closest('.mc-unified-panel');
    if (!panel) return;
    var btns = panel.querySelectorAll('.mc-view-tab-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.remove('active');
    }
    btn.classList.add('active');
    var views = panel.querySelectorAll('.mc-view-panel');
    for (var j = 0; j < views.length; j++) {
      var v = views[j];
      if (v.getAttribute('data-view') === tabId) {
        v.style.display = 'block';
        v.classList.add('active');
      } else {
        v.style.display = 'none';
        v.classList.remove('active');
      }
    }
  } catch (e) {}
};
(function() {
  try {
    __noraOn('r2', 'click', function(e) {
      var btn = e.target && e.target.closest && e.target.closest('.mc-view-tab-btn');
      if (btn) {
        var tabId = btn.getAttribute('data-tab');
        if (window.switchMcViewTab && tabId) {
          window.switchMcViewTab(btn, tabId);
        }
      }
    });
    // Chuyển tiếp mượt mà vào SPA để giữ header cố định, không load lại trang
    if (window.location.pathname.startsWith('/bot/') || /^\\/[a-zA-Z0-9]+_[a-zA-Z0-9]+$/.test(window.location.pathname)) {
      var seg = window.location.pathname.replace(/^\\/bot\\//, '').replace(/^\\/[^_]+_/, '');
      if (seg && !window.location.hash) {
        window.location.replace('/#/admin?tab=bot&code=' + seg);
        return;
      }
    }
    // Monte Carlo hover read-out: the band chart carries its checkpoints
    // (data-cps) and plot geometry (data-geo); histogram bars carry data-tip.
    (function() {
      function fmt(v) { return (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(1) + '%'; }
      function tipFor(svg) { var body = svg.closest('.mc-chart-body'); return body ? body.querySelector('.mc-tipbox') : null; }
      function place(tip, svg, px, py) {
        var r = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal, k = r.width / (vb.width || 760);
        var x = px * k, left = x + 14; if (left + 170 > r.width) left = x - 184;
        tip.style.left = left + 'px'; tip.style.top = Math.max(0, py * k - 20) + 'px'; tip.style.display = 'block';
      }
      __noraOn('r3', 'mousemove', function(e) {
        var t = e.target;
        if (!t || !t.closest) return;
        var hit = t.closest('.mc-hit'), bin = t.closest('.mc-bin');
        document.querySelectorAll('.mc-tipbox').forEach(function(tb) {
          if (!(hit || bin) || !tb.parentElement.contains(t)) tb.style.display = 'none';
        });
        if (hit) {
          var svg = hit.ownerSVGElement, tip = tipFor(svg); if (!tip) return;
          var cps = JSON.parse(svg.getAttribute('data-cps') || '[]'), g = JSON.parse(svg.getAttribute('data-geo') || '[]');
          if (!cps.length || g.length < 7) return;
          var r = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal, px = (e.clientX - r.left) / r.width * vb.width;
          var tc = Math.max(0, Math.min(g[6], (px - g[0]) / g[1] * g[6])), i = 1;
          while (i < cps.length - 1 && cps[i][0] < tc) i++;
          var a = cps[i - 1], b = cps[i], f = b[0] > a[0] ? (tc - a[0]) / (b[0] - a[0]) : 0;
          var v = function(k) { return a[k] + (b[k] - a[k]) * f; };
          var X = g[0] + g[1] * tc / g[6], Y = function(val) { return g[2] + g[3] * (1 - (val - g[4]) / ((g[5] - g[4]) || 1)); };
          var cross = svg.querySelector('.mc-cross'), dot = svg.querySelector('.mc-dot');
          cross.setAttribute('x1', X); cross.setAttribute('x2', X); cross.setAttribute('visibility', 'visible');
          dot.setAttribute('cx', X); dot.setAttribute('cy', Y(v(3))); dot.setAttribute('visibility', 'visible');
          tip.innerHTML = '<div class="mc-tip-h">' + (svg.getAttribute('data-unit') === 'day' ? 'Day ' : 'Trade #') + Math.round(tc) + '</div>' +
            [['P95', 5, '#17a565'], ['P75', 4, '#7aa0f0'], ['Median', 3, '#2454e0'], ['P25', 2, '#7aa0f0'], ['P05', 1, '#d04a3c']]
              .map(function(q) { return '<div class="mc-tip-r"><i style="background:' + q[2] + '"></i>' + q[0] + '<b>' + fmt(v(q[1])) + '</b></div>'; }).join('');
          place(tip, svg, X, Y(v(3)));
        } else if (bin) {
          var svg2 = bin.ownerSVGElement, tip2 = tipFor(svg2); if (!tip2) return;
          var p = (bin.getAttribute('data-tip') || '').split('|');
          tip2.innerHTML = '<div class="mc-tip-h">' + p[0] + '</div><div class="mc-tip-r">' + (p[1] || '') + '<b>' + (p[2] || '') + '</b></div>';
          place(tip2, svg2, parseFloat(bin.getAttribute('x')) + parseFloat(bin.getAttribute('width')) / 2, parseFloat(bin.getAttribute('y')));
        }
        if (!hit) document.querySelectorAll('.mc-cross, .mc-dot').forEach(function(n) { n.setAttribute('visibility', 'hidden'); });
      });
    })();
    // Paged lists (traded assets, closed-trades ledger): 10 per page, with
    // the ledger's Win / Loss filter and, on a portfolio, its per-bot filter.
    // A filter bar names its list with `data-box`, so two lists in one card
    // never drive each other.
    (function() {
      function pagerHtml(p, n) {
        var h = '<button type="button" class="lg-pg" data-p="' + (p - 1) + '"' + (p <= 0 ? ' disabled' : '') + '>\u2039</button>';
        for (var i = 0; i < n; i++) {
          if (i === 0 || i === n - 1 || Math.abs(i - p) <= 1) h += '<button type="button" class="lg-pg' + (i === p ? ' on' : '') + '" data-p="' + i + '">' + (i + 1) + '</button>';
          else if (Math.abs(i - p) === 2) h += '<span class="lg-gap">\u2026</span>';
        }
        return h + '<button type="button" class="lg-pg" data-p="' + (p + 1) + '"' + (p >= n - 1 ? ' disabled' : '') + '>\u203a</button>';
      }
      // Ledger row from its data -- the same markup as `_lg_row_html`.
      var TONE = { w: ['win', 'good', 'good', 'Win'], l: ['loss', 'bad', 'bad', 'Loss'], e: ['even', '', 'flat', 'Even'] };
      function esc(v) { return String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;'); }
      function lgRow(r, cells) {
        var t = TONE[r[4]];
        return '<div class="lg-row" data-r="' + r[4] + '" data-b="' + esc(r[7] || 'all') + '">'
          + '<span class="pv-num pv-muted">#' + r[0] + '</span>' + cells[r[6]]
          + '<span class="pv-num lg-t">' + esc(r[1]) + '</span>'
          + '<span class="lg-pl"><span class="lg-pl-bar lg-pl-' + t[0] + '" style="width:' + r[8] + 'px"></span>'
          + '<b class="pv-num pv-v-' + t[1] + '">' + esc(r[2]) + '</b></span>'
          + '<span class="pv-num as-r lg-cum pv-v-' + r[5] + '">' + esc(r[3]) + '</span>'
          + '<span class="as-r"><span class="st-chip st-chip-' + t[2] + ' pv-state">' + t[3] + '</span></span></div>';
      }
      function dataOf(box) {
        if (box.__lgData === undefined) {
          var s = box.querySelector('script.lg-data');
          try { box.__lgData = s ? JSON.parse(s.textContent) : null; } catch (e) { box.__lgData = null; }
        }
        return box.__lgData;
      }
      function render(box) {
        var f = box.getAttribute('data-f') || 'a', b = box.getAttribute('data-b') || 'all';
        var p = +(box.getAttribute('data-p') || 0), per = +(box.getAttribute('data-per') || 10), unit = box.getAttribute('data-unit') || 'trades';
        var data = dataOf(box), list = [], n;
        if (data) {
          data.r.forEach(function(r) {
            if ((f === 'a' || r[4] === f) && (b === 'all' || (r[7] || 'all') === b)) list.push(r);
          });
          n = Math.max(1, Math.ceil(list.length / per)); p = Math.max(0, Math.min(p, n - 1)); box.setAttribute('data-p', p);
          var body = box.querySelector('.lg-body');
          if (body) body.innerHTML = list.slice(p * per, p * per + per).map(function(r) { return lgRow(r, data.k); }).join('');
        } else {
          var rows = box.querySelectorAll('.lg-body > [data-r]');
          rows.forEach(function(r) {
            if ((f === 'a' || r.getAttribute('data-r') === f) && (b === 'all' || r.getAttribute('data-b') === b)) list.push(r);
          });
          n = Math.max(1, Math.ceil(list.length / per)); p = Math.max(0, Math.min(p, n - 1)); box.setAttribute('data-p', p);
          rows.forEach(function(r) { r.hidden = true; });
          list.slice(p * per, p * per + per).forEach(function(r) { r.hidden = false; });
        }
        var info = box.querySelector('.lg-info');
        if (info) info.textContent = list.length ? (p * per + 1) + '\u2013' + Math.min(list.length, p * per + per) + ' of ' + list.length.toLocaleString('en-US') + ' ' + unit : 'No ' + unit;
        var pg = box.querySelector('.lg-pager');
        if (!pg && n > 1) { pg = document.createElement('span'); pg.className = 'lg-pager'; var ft = box.querySelector('.lg-foot'); if (ft) ft.appendChild(pg); }
        if (pg) { pg.innerHTML = n > 1 ? pagerHtml(p, n) : ''; }
      }
      __noraOn('r4', 'click', function(e) {
        var t = e.target && e.target.closest ? e.target : null; if (!t) return;
        var fb = t.closest('.lg-f, .lg-b'), pb = t.closest('.lg-pg');
        if (fb) {
          var bar = fb.closest('.lg-filter'), card = fb.closest('.pv-card') || document;
          var box = card.querySelector('.lg-box[data-box="' + ((bar && bar.getAttribute('data-box')) || 'ledger') + '"]');
          if (!box) return;
          if (bar) bar.querySelectorAll('.lg-f, .lg-b').forEach(function(x) { x.classList.toggle('on', x === fb); });
          if (fb.classList.contains('lg-b')) box.setAttribute('data-b', fb.getAttribute('data-b'));
          else box.setAttribute('data-f', fb.getAttribute('data-f'));
          box.setAttribute('data-p', '0'); render(box);
        } else if (pb && !pb.disabled) {
          var box2 = pb.closest('.lg-box'); if (!box2) return;
          box2.setAttribute('data-p', pb.getAttribute('data-p')); render(box2);
        }
      });
    })();
    // Floating tip for every (i): drawn in one fixed layer on <body>, kept
    // inside the viewport (above the icon, or below it when there is no room).
    (function() {
      var tip = null, owner = null;
      function layer() {
        if (!tip || !document.body.contains(tip)) {
          tip = document.createElement('div'); tip.id = 'nb-float-tip'; tip.setAttribute('role', 'tooltip');
          document.body.appendChild(tip);
        }
        return tip;
      }
      function show(ic) {
        var src = ic.querySelector('.info-tip'); if (!src) return;
        var t = layer(); t.innerHTML = src.innerHTML; t.style.display = 'block'; owner = ic;
        var r = ic.getBoundingClientRect(), w = t.offsetWidth, h = t.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
        var left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), vw - w - 8);
        var top = r.top - h - 8;
        if (top < 8) top = Math.min(r.bottom + 8, vh - h - 8);
        t.style.left = left + 'px'; t.style.top = Math.max(8, top) + 'px';
      }
      function hide() { if (tip) tip.style.display = 'none'; owner = null; }
      document.addEventListener('mouseover', function(e) {
        var ic = e.target && e.target.closest ? e.target.closest('.info-ic') : null;
        if (ic) { if (ic !== owner) show(ic); } else if (owner) hide();
      });
      document.addEventListener('focusin', function(e) {
        var ic = e.target && e.target.closest ? e.target.closest('.info-ic') : null;
        if (ic) show(ic);
      });
      document.addEventListener('focusout', hide);
      window.addEventListener('scroll', hide, true);
    })();
    // A link to a pane of the deep-dive card (#cach-choi, #diem-chieu...)
    // switches that card's tab first, so the target is visible.
    __noraOn('r5', 'click', function(e) {
      var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!a) return;
      var el = document.getElementById(a.getAttribute('href').slice(1));
      var dd = el && el.parentElement;
      if (dd && dd.classList && dd.classList.contains('dd-card')) dd.setAttribute('data-active', el.id);
    });
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

      __noraOn('r6', 'mouseover', function(e) {
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

      __noraOn('r7', 'mousemove', function(e) {
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

      __noraOn('r8', 'mouseout', function(e) {
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
    + """
<script id="nora-chat-runtime">
(function() {
  try {
    // TỰ RÚT LUI KHI KHÔNG CẦN THIẾT -- lỗi thật đã đo hai lượt (22/09):
    //
    // Lượt 1 (đã sửa): trong luồng SPA, mỗi lần `BotDetailView.jsx` fetch
    // lại trang đều duyệt lại toàn bộ thẻ script tìm thấy và CHẠY LẠI TỪ
    // ĐẦU. `document.addEventListener` không tự khử trùng lặp, nên không
    // chặn thì mỗi lượt chạy lại cộng thêm một listener chồng lên listener
    // cũ -- `window.__noraChatWired` bên dưới chặn đúng việc này.
    //
    // Lượt 2 (lỗi thật vẫn còn SAU lượt 1, tin nhắn vẫn lặp): `BotDetailView.jsx`
    // giờ TỰ nối sự kiện riêng cho đúng các phần tử này (`#nora-chat-fab`,
    // `#nora-chat-chips`, `#nora-chat-form`...) bằng `useEffect` chạy SAU
    // khi HTML đã thật sự được chèn vào DOM -- cùng cách nó đã làm cho tab/
    // nút back/link hash từ trước. Vậy trong luồng SPA giờ có HAI hệ thống
    // độc lập cùng lắng nghe cùng một cú click: script này (qua uỷ quyền
    // trên `document`) VÀ `useEffect` kia (qua `root.querySelector` sau khi
    // chèn thật) -- mỗi bên gọi `ask()` một lần, ra đúng hai tin nhắn giống
    // hệt nhau như ảnh chụp thật cho thấy.
    //
    // CÁCH PHÂN BIỆT: script này chạy vào một trong hai thời điểm, và chỉ
    // một trong hai có nghĩa là "tôi phải tự lo nối sự kiện":
    //   * Trang gốc (không qua SPA, `#x` bỏ qua chuyển hướng): trình duyệt
    //     phân tích cú pháp HTML THEO THỨ TỰ, nên tới lúc chạy script này,
    //     `<button id="nora-chat-fab">` (đứng TRƯỚC nó trong mã nguồn) chắc
    //     chắn ĐÃ có trong DOM thật.
    //   * SPA: `BotDetailView.jsx` chạy lại script này TRƯỚC khi chèn HTML
    //     thật (đọc từ một `doc` đã tách rời, xem module docstring của
    //     `_render_chat_widget`), nên tại đúng thời điểm này, phần tử ĐÓ
    //     CHƯA tồn tại trong DOM thật (kể cả ở lượt refetch thứ hai trở đi
    //     -- nút CŨ từ lượt render trước có thể vẫn còn, nhưng cờ
    //     `__noraChatWired` bên dưới đã chặn từ lượt đầu nên không quan
    //     trọng nữa).
    // Do đó: phần tử CHƯA tồn tại lúc này => đang ở luồng SPA => tự thoát
    // ngay, không gắn bất kỳ listener nào, nhường toàn quyền cho
    // `useEffect` của React lo -- đúng NƠI DUY NHẤT nên xử lý việc này khi
    // chạy trong SPA, vì nó chạy đúng lúc DOM thật đã sẵn sàng.
    if (!document.getElementById('nora-chat-fab')) { return; }
    if (window.__noraChatWired) { return; }
    window.__noraChatWired = true;

    // Event delegation on document to handle dynamic rendering cleanly
    function el(id) {
      return document.getElementById(id);
    }

    var HISTORY_CAP = 6;
    var history = [];
    var busy = false;

    // Thoát HTML bằng chính DOM (gán `textContent` rồi đọc lại `innerHTML`)
    // -- không tự viết regex thoát tay, vì trình duyệt escape đúng MỌI ký
    // tự đặc biệt, kể cả những ký tự một regex tự viết dễ bỏ sót. Câu trả
    // lời của model đi qua đây TRƯỚC khi tô đậm số liệu, nên số liệu tô
    // đậm không thể mở lại một lỗ XSS nào.
    function escapeHtml(text) {
      var div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Tô đậm số liệu trong câu trả lời -- CÙNG một biểu thức chính quy với
    // `report_page._format_expert_metric_highlights` (dùng cho đoạn nhận
    // định ở trang report) để hai nơi hiển thị số liệu nhất quán về mặt
    // hình ảnh. Chỉ khớp số có `%`, hậu tố `x` (bội số, "4.04x"), hoặc có
    // dấu thập phân -- một số nguyên trần ("212 closed trades") không được
    // tô, đúng chủ đích bản gốc: tô những con số ĐỌC NHƯ MỘT CHỈ SỐ, không
    // tô mọi con số.
    var METRIC_RE = /(\\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?%|\\b\\d+(?:\\.\\d+)?x\\b|\\b\\d+\\.\\d+\\b)/g;
    function highlightMetrics(escapedHtml) {
      return escapedHtml.replace(METRIC_RE, '<strong class="nora-chat-metric">$1</strong>');
    }

    // Tách câu để xuống dòng cho dễ đọc trong khung chat hẹp -- model trả
    // lời 2-6 câu liền một mạch (xem STYLE trong chat.py), dồn hết vào một
    // đoạn văn trông rất bí. Tách theo ranh giới câu: dấu kết câu + khoảng
    // trắng + MỘT CHỮ HOA ngay sau -- điều kiện "chữ hoa ngay sau" cố ý để
    // KHÔNG cắt nhầm vào số thập phân kiểu "57.08%" (sau dấu "." ở đó là
    // chữ số "08", không phải chữ hoa, nên không khớp).
    var SENTENCE_SPLIT_RE = /(?<=[.!?])\\s+(?=[A-Z])/;
    function formatAnswer(text) {
      var sentences = text.split(SENTENCE_SPLIT_RE)
        .map(function(s) { return s.trim(); })
        .filter(function(s) { return s.length > 0; });
      return sentences.map(function(s) {
        return highlightMetrics(escapeHtml(s));
      }).join('<br><br>');
    }

    function addBubble(role, text) {
      var log = el('nora-chat-log');
      if (!log) { return; }
      var row = document.createElement('div');
      row.className = 'nora-chat-msg-row msg-' + role;

      if (role === 'assistant') {
        var avatar = document.createElement('div');
        avatar.className = 'nora-chat-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        row.appendChild(avatar);
      }

      var bubble = document.createElement('div');
      bubble.className = 'nora-chat-bubble role-' + role;
      if (role === 'assistant') {
        // CHỈ vai assistant được định dạng -- câu hỏi của người dùng và
        // câu lỗi giữ nguyên `textContent` thuần, không cần tô/tách câu.
        bubble.innerHTML = formatAnswer(text);
      } else {
        bubble.textContent = text;
      }
      row.appendChild(bubble);

      log.appendChild(row);
      log.scrollTop = log.scrollHeight;
    }

    function setChips(questions) {
      var chipsBox = el('nora-chat-chips');
      if (!chipsBox) { return; }
      chipsBox.innerHTML = '';
      if (!questions || !questions.forEach) { return; }
      questions.forEach(function(q) {
        if (typeof q !== 'string' || !q) { return; }
        var chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'nora-chat-chip';
        chip.textContent = q;
        chipsBox.appendChild(chip);
      });
    }

    function setBusy(next, message) {
      busy = next;
      var input = el('nora-chat-input');
      var sendBtn = el('nora-chat-send');
      var status = el('nora-chat-status');
      if (input) { input.disabled = next; }
      if (sendBtn) { sendBtn.disabled = next; }
      if (status) {
        if (next) {
          status.innerHTML = '<div class="nora-chat-typing"><span class="tdot"></span><span class="tdot"></span><span class="tdot"></span><span style="margin-left:6px;font-size:11.5px;color:var(--ink-3);">Nora AI is thinking...</span></div>';
        } else {
          status.innerHTML = '';
        }
      }
      var log = el('nora-chat-log');
      if (log) { log.scrollTop = log.scrollHeight; }
    }

    function ask(question) {
      question = (question || '').trim();
      if (!question || busy) { return; }
      var widget = el('nora-chat-widget');
      var input = el('nora-chat-input');
      var code = widget ? (widget.getAttribute('data-bot-code') || '') : '';
      if (!code) { return; }
      addBubble('user', question);
      history.push({ role: 'user', text: question });
      if (history.length > HISTORY_CAP) { history = history.slice(-HISTORY_CAP); }
      if (input) { input.value = ''; }
      setChips([]);
      setBusy(true);
      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code, question: question, history: history })
      }).then(function(resp) {
        return resp.json().catch(function() { return null; }).then(function(data) {
          return { ok: resp.ok, status: resp.status, data: data };
        });
      }).then(function(result) {
        setBusy(false);
        var data = result.data;
        if (result.ok && data && typeof data.answer === 'string') {
          addBubble('assistant', data.answer);
          history.push({ role: 'assistant', text: data.answer });
          if (history.length > HISTORY_CAP) { history = history.slice(-HISTORY_CAP); }
          // CỐ TÌNH không gọi lại `setChips(data.suggested_questions)` ở
          // đây nữa: gợi ý chỉ hiện MỘT LẦN lúc mở panel (trong `openChat`),
          // trước khi có tin nhắn nào. Một khi cuộc trò chuyện đã bắt đầu,
          // dải chip che mất khoảng trống hẹp giữa log và ô nhập trong một
          // panel nhỏ -- yêu cầu tường minh của chủ dự án (22/09): "gợi ý
          // khi đã chat thì ẩn nó đi, tránh che nội dung". `data` vẫn trả
          // về `suggested_questions` từ server (không đổi API) -- chỉ phía
          // hiển thị này không dùng tới sau lượt hỏi đầu tiên.
        } else {
          var message = (data && data.message) || 'Something went wrong answering that. Please try again.';
          addBubble('error', message);
        }
      }).catch(function() {
        setBusy(false);
        addBubble('error', 'Could not reach the server. Please check your connection and try again.');
      });
    }

    function openChat() {
      var widget = el('nora-chat-widget');
      var fab = el('nora-chat-fab');
      if (!widget || !fab) { return; }
      widget.hidden = false;
      widget.setAttribute('aria-hidden', 'false');
      fab.setAttribute('aria-expanded', 'true');
      var log = el('nora-chat-log');
      var chipsBox = el('nora-chat-chips');
      if (log && chipsBox && !log.childElementCount && !chipsBox.childElementCount) {
        addBubble('assistant', 'Hello! I am Nora AI risk assistant. Ask me anything about this bot\\'s risk rating, Monte Carlo stress tests, drawdowns, or classification verdict.');
        setChips([
          'What does the Risk Score measure?',
          'Why did this bot get warned or vetoed?',
          'Explain the verdict and Monte Carlo tests',
          'Is this bot vulnerable to slippage or illiquidity?'
        ]);
      }
      var input = el('nora-chat-input');
      if (input) { input.focus(); }
    }
    function closeChat() {
      var widget = el('nora-chat-widget');
      var fab = el('nora-chat-fab');
      if (!widget || !fab) { return; }
      widget.hidden = true;
      widget.setAttribute('aria-hidden', 'true');
      fab.setAttribute('aria-expanded', 'false');
      fab.focus();
    }

    document.addEventListener('click', function(ev) {
      var target = ev.target;
      if (!target || typeof target.closest !== 'function') { return; }
      if (target.closest('#nora-chat-fab')) { openChat(); return; }
      if (target.closest('#nora-chat-close')) { closeChat(); return; }
      var chip = target.closest('.nora-chat-chip');
      if (chip) { ask(chip.textContent); }
    });
    document.addEventListener('submit', function(ev) {
      if (ev.target && ev.target.id === 'nora-chat-form') {
        ev.preventDefault();
        var input = el('nora-chat-input');
        ask(input ? input.value : '');
      }
    });
    document.addEventListener('keydown', function(ev) {
      if (ev.key !== 'Escape') { return; }
      var widget = el('nora-chat-widget');
      if (widget && !widget.hidden) { closeChat(); }
    });
  } catch (err) {}
})();
</script>"""
)
