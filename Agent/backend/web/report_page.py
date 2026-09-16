"""Self-contained HTML for `GET /bot/<code>` -- the "final destination" page
a human (or another agent) lands on to actually read one bot's risk
assessment, as opposed to the raw JSON `/api/analyze` returns.

Everything needed to render the page is already sitting in the dict
`WebDataService.analyze()` returns (see `Agent/backend/web/data.py`'s module
docstring for its 14 top-level keys): this module only turns that dict into
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
`<details>` "Đọc thế nào / Dựa trên đâu" block -- see `_theory` -- because a
dashboard of numbers with no explanation of what they mean or where they
come from is exactly the failure mode the project owner's own brief called
out ("thiếu vế thứ ba là hỏng"). The Vietnamese in those blocks and in this
module's own prose is written in the same register as
`Agent/backend/qc/reporting/reasons.py`: plain, evidence-first, no hedging
filler, no marketing.

LIMITED and NOT_FOUND are first-class inputs, not error cases: a LIMITED
bot's `evidence` dict has a different shape from a FULL bot's (a flat
`components` list -- see `Agent/backend/analysis/limited.py` -- instead of
the FULL pipeline's `dimensions` dict + `score_breakdown`), so the
dimensions section below branches on which shape is actually present rather
than assuming FULL's. NOT_FOUND renders a short standalone page and skips
every other section outright.
"""

from __future__ import annotations

import html
import logging
import math
import re
from numbers import Real
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from Agent.backend.infra.config import config

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
# here (rather than imported from Agent/backend/qc/**) deliberately: that
# tree is off-limits to touch for this task and owned by other work in
# flight, and a presentation-only module has no business depending on it for
# a handful of label strings anyway -- see Agent/backend/qc/scoring/fusion.py
# (DIMENSION_LABEL_VI) and Agent/backend/qc/reporting/reasons.py (TIER_VI) if
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
    "market_alignment": "Đồng thuận thị trường",
    "performance_quality": "Chất lượng hiệu suất",
    "return_r_quality": "Chất lượng lợi nhuận / R",
    "drawdown_risk": "Rủi ro sụt vốn",
    "tail_risk": "Rủi ro đuôi",
    "leverage_exposure": "Đòn bẩy / Exposure",
    "behavioral_risk": "Hành vi giao dịch",
    "strategy_drift": "Độ bền chiến lược qua các pha",
    "liquidity_execution": "Thanh khoản / Khớp lệnh",
    "portfolio_risk": "Rủi ro danh mục",
}

TIER_LABEL_VI: Dict[str, str] = {
    "EMERGENCY": "KHẨN CẤP",
    "CRITICAL": "NGHIÊM TRỌNG",
    "HIGH": "CAO",
    "ELEVATED": "NÂNG CAO",
    "WATCH": "THEO DÕI",
    "HEALTHY": "AN TOÀN",
    "UNKNOWN": "CHƯA ĐO ĐƯỢC",
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

ASSET_STATE_COLOR: Dict[str, str] = {
    "ĐANG GIAO DỊCH": "#16a34a",
    "CHỈ ĐANG ÔM": "#dc2626",
    "ĐÃ RỜI": "#6b7280",
}

# --------------------------------------------------------------------------- #
# Shared design tokens (task's Việc 3) -- Agent/web/tokens.css is now the ONE
# place a verdict-tier color (or a page-chrome/type-scale/spacing/radius
# value) is written down; this module previously hardcoded its own copy of
# the 4-tier `VERDICT_COLOR` values as Python string literals, with no
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

_DESIGN_TOKENS_PATH = Path(config.BASE_DIR) / "web" / "tokens.css"

# Same 5 values this module hardcoded before tokens.css existed -- used
# verbatim whenever the token file cannot be read/parsed at all (missing
# checkout, bad permissions, a syntax error a human introduced by hand-
# editing the CSS), so a broken/absent token file degrades this module's
# OWN color choices back to exactly what they always were, rather than
# breaking every rendered page's verdict badge.
_FALLBACK_VERDICT_COLOR: Dict[str, str] = {
    "NGUY HIỂM": "#dc2626",
    "TIỀM ẨN": "#d97706",
    "TIỀM NĂNG": "#16a34a",
    "AN TOÀN": "#0284c7",
    "THIẾU BẰNG CHỨNG": "#6b7280",
}

# CSS custom-property name -> the Vietnamese verdict label it colors, per
# tokens.css's own "Verdict classification" block. A dict, not a reverse
# lookup built from `_FALLBACK_VERDICT_COLOR`'s keys, because the CSS
# variable NAME is deliberately English/semantic ("danger"/"watch"/
# "positive"/"safe"/"unknown") while the Python-side key stays the
# Vietnamese label every call site (`_verdict_color`, admin_page.py's own
# `VERDICT_COLOR.get(verdict, ...)`) already looks up by.
_VERDICT_TOKEN_TO_LABEL: Dict[str, str] = {
    "--verdict-danger": "NGUY HIỂM",
    "--verdict-watch": "TIỀM ẨN",
    "--verdict-positive": "TIỀM NĂNG",
    "--verdict-safe": "AN TOÀN",
    "--verdict-unknown": "THIẾU BẰNG CHỨNG",
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
            "Không đọc được design token %s -- dùng màu mặc định trong mã "
            "nguồn: %s",
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
        value = tokens.get(var_name)
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
    "SHORT": "NGẮN",
    "MEDIUM": "TRUNG",
    "LONG": "DÀI",
}


def _tier_color(tier: Any) -> str:
    return TIER_COLOR.get(str(tier or "UNKNOWN").upper(), TIER_COLOR["UNKNOWN"])


def _verdict_color(verdict: Any) -> str:
    return VERDICT_COLOR.get(str(verdict or ""), "#6b7280")


# --------------------------------------------------------------------------- #
# Small HTML fragment builders
# --------------------------------------------------------------------------- #


def _theory(
    read_html: str, basis_html: str, *, label: str = "Đọc thế nào & dựa trên đâu"
) -> str:
    """One collapsible "sở cứ + lý thuyết" block -- the task's own explicit
    third requirement, distinct from a chart or a raw number: what a value
    means for THIS bot, and what method/source produced it. `read_html` and
    `basis_html` are trusted, hand-written Vietnamese prose from this module
    with numbers interpolated through the `_num`/`_pct`/`_esc` helpers above
    (never raw f-string values), so they are safe to place directly.
    """
    return (
        '<details class="theory">'
        f"<summary>{_esc(label)}</summary>"
        '<div class="theory-body">'
        f"<p><strong>Đọc thế nào:</strong> {read_html}</p>"
        f"<p><strong>Dựa trên đâu:</strong> {basis_html}</p>"
        "</div></details>"
    )


def _section(title: str, body: str, *, anchor: Optional[str] = None) -> str:
    if not body:
        return ""
    anchor_attr = f' id="{_esc(anchor)}"' if anchor else ""
    return f'<section class="card"{anchor_attr}><h2>{_esc(title)}</h2>{body}</section>'


def _stat_tile(label: str, value: str, *, color: Optional[str] = None) -> str:
    style = f' style="color:{color}"' if color else ""
    return (
        '<div class="stat-tile">'
        f'<div class="stat-value"{style}>{_esc(value)}</div>'
        f'<div class="stat-label">{_esc(label)}</div>'
        "</div>"
    )


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
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
    return (
        '<div class="table-scroll"><table>'
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
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}"{cls}{aria_attr} '
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
) -> str:
    dash_attr = f' stroke-dasharray="{_esc(dash)}"' if dash else ""
    return (
        f'<line x1="{_coord(x1)}" y1="{_coord(y1)}" x2="{_coord(x2)}" y2="{_coord(y2)}" '
        f'stroke="{_esc(stroke)}" stroke-width="{_coord(width)}"{dash_attr}/>'
    )


def _text(
    x: float,
    y: float,
    text: str,
    *,
    anchor: str = "start",
    cls: str = "",
    fill: str = "",
) -> str:
    fill_attr = f' fill="{_esc(fill)}"' if fill else ""
    cls_attr = f' class="{_esc(cls)}"' if cls else ""
    return (
        f'<text x="{_coord(x)}" y="{_coord(y)}" text-anchor="{_esc(anchor)}"'
        f"{cls_attr}{fill_attr}>{_esc(text)}</text>"
    )


# --------------------------------------------------------------------------- #
# Chart: horizontal bars, 0..100 scale -- used for per-dimension scores.
# --------------------------------------------------------------------------- #


class _BarRow:
    __slots__ = ("label", "value", "color", "value_text", "measured", "tag")

    def __init__(
        self,
        label: str,
        value: Optional[float],
        color: str,
        value_text: str,
        *,
        measured: bool = True,
        tag: Optional[str] = None,
    ) -> None:
        self.label = label
        self.value = value
        self.color = color
        self.value_text = value_text
        self.measured = measured
        self.tag = tag


def _horizontal_bars(
    rows: Sequence[_BarRow], *, max_value: float = 100.0, width: float = 640.0
) -> str:
    if not rows:
        return ""
    row_h = 34.0
    top_pad = 6.0
    label_w = 190.0
    value_w = 90.0
    track_x = label_w + 10.0
    track_w = max(width - track_x - value_w - 10.0, 40.0)
    height = top_pad * 2 + row_h * len(rows)
    parts: List[str] = []
    for i, row in enumerate(rows):
        y = top_pad + i * row_h
        mid = y + row_h * 0.62
        label_text = row.label if len(row.label) <= 26 else row.label[:25] + "…"
        parts.append(_text(0, mid, label_text, cls="bar-label"))
        parts.append(
            _rect(track_x, y + 6, track_w, row_h - 16, fill="var(--track)", rx=5)
        )
        if row.measured and row.value is not None:
            frac = _clamp(float(row.value) / max_value if max_value else 0.0, 0.0, 1.0)
            parts.append(
                _rect(track_x, y + 6, track_w * frac, row_h - 16, fill=row.color, rx=5)
            )
        else:
            # Unmeasured: a flat hatched-looking muted bar rather than a
            # numeric value -- a neutral placeholder score must never look
            # like a real measurement (task's own LIMITED requirement).
            parts.append(
                _rect(
                    track_x, y + 6, track_w, row_h - 16, fill="var(--track-muted)", rx=5
                )
            )
        value_x = track_x + track_w + 8
        parts.append(_text(value_x, mid, row.value_text, cls="bar-value"))
        if row.tag:
            parts.append(_text(track_x + 4, y + row_h - 3, row.tag, cls="bar-tag"))
    return _svg(width, height, "".join(parts), extra_class="bar-chart")


def _diverging_bars(
    rows: Sequence[Tuple[str, Optional[float]]],
    *,
    width: float = 640.0,
    unit: str = "%",
) -> str:
    """Percentiles that can be negative or positive, drawn as bars growing
    left (loss) or right (profit) from a shared zero/breakeven line. Used
    for the Monte Carlo terminal-outcome percentile spread.
    """
    values = [v for _, v in rows if _is_finite_number(v)]
    if not values:
        return ""
    span = max(max(values, default=1.0), abs(min(values, default=-1.0)), 1.0)
    row_h = 32.0
    top_pad = 6.0
    label_w = 70.0
    value_w = 90.0
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
        frac = _clamp(abs(v) / span, 0.0, 1.0) * half_track
        color = "#16a34a" if v >= 0 else "#dc2626"
        if v >= 0:
            parts.append(_rect(zero_x, y + 5, frac, row_h - 14, fill=color, rx=4))
        else:
            parts.append(
                _rect(zero_x - frac, y + 5, frac, row_h - 14, fill=color, rx=4)
            )
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
        "AN TOÀN" tier this run) still shows up as "0 · 0.0%" rather than
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
            + _text(cx, cy, "Không có dữ liệu", anchor="middle", cls="pie-empty")
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
        aria_label="Biểu đồ tròn",
    )


# --------------------------------------------------------------------------- #
# Chart: cumulative line -- the "tăng trưởng" chart, plotting a running total
# (vốn tích luỹ) against sequence order (thứ tự lệnh), point by point.
# --------------------------------------------------------------------------- #


def _line_chart(
    ys: Sequence[Any],
    *,
    width: float = 640.0,
    height: float = 220.0,
    y_unit: str = "",
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

    left_pad = 56.0
    right_pad = 12.0
    top_pad = 18.0
    bottom_pad = 30.0
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
    parts: List[str] = [
        _line(
            left_pad,
            zero_y,
            left_pad + plot_w,
            zero_y,
            stroke="var(--axis)",
            dash="3,3",
        )
    ]

    stroke = "#16a34a" if pts[-1] >= 0.0 else "#dc2626"
    x_last, y_last = xy(n - 1, pts[-1])

    if n == 1:
        parts.append(
            f'<circle cx="{_coord(x_last)}" cy="{_coord(y_last)}" r="4" fill="{stroke}"/>'
        )
    else:
        coords = " ".join(
            f"{_coord(x)},{_coord(y)}" for x, y in (xy(i, v) for i, v in enumerate(pts))
        )
        parts.append(
            f'<polyline points="{coords}" fill="transparent" stroke="{stroke}" '
            'stroke-width="2.2"/>'
        )
        x0, y0 = xy(0, pts[0])
        parts.append(
            f'<circle cx="{_coord(x0)}" cy="{_coord(y0)}" r="3" fill="var(--axis)"/>'
        )
        parts.append(
            f'<circle cx="{_coord(x_last)}" cy="{_coord(y_last)}" r="4" fill="{stroke}"/>'
        )
        peak_i = max(range(n), key=lambda i: pts[i])
        trough_i = min(range(n), key=lambda i: pts[i])
        for i, tag, color in (
            (peak_i, "Đỉnh", "#16a34a"),
            (trough_i, "Đáy", "#dc2626"),
        ):
            if i in (0, n - 1):
                continue
            x, y = xy(i, pts[i])
            parts.append(
                f'<circle cx="{_coord(x)}" cy="{_coord(y)}" r="3" fill="{color}"/>'
            )
            parts.append(
                _text(
                    x,
                    y - 8,
                    f"{tag} {pts[i]:,.0f}{y_unit}",
                    anchor="middle",
                    cls="line-marker",
                )
            )

    parts.append(
        _text(
            x_last,
            y_last - 10,
            f"{pts[-1]:,.0f}{y_unit}",
            anchor="end",
            cls="line-end-label",
        )
    )
    parts.append(
        _text(left_pad, top_pad - 4, f"{hi:,.0f}{y_unit}", cls="line-axis-label")
    )
    parts.append(
        _text(
            left_pad, top_pad + plot_h + 2, f"{lo:,.0f}{y_unit}", cls="line-axis-label"
        )
    )
    parts.append(_text(left_pad, height - 2, "Lệnh #1", cls="line-axis-label"))
    parts.append(
        _text(
            left_pad + plot_w,
            height - 2,
            f"Lệnh #{n}",
            anchor="end",
            cls="line-axis-label",
        )
    )

    return _svg(
        width,
        height,
        "".join(parts),
        extra_class="line-chart",
        aria_label="Đường vốn tích luỹ theo lệnh đã chốt",
    )


# --------------------------------------------------------------------------- #
# Section 1 -- header
# --------------------------------------------------------------------------- #


def _render_header(result: Dict[str, Any]) -> str:
    name = result.get("name") or result.get("code") or "Bot"
    code = result.get("code") or ""
    verdict = result.get("verdict")
    verdict_color = _verdict_color(verdict)
    risk = result.get("risk")
    quality = result.get("quality")
    confidence = result.get("confidence")

    tiles = [
        _stat_tile(
            "Điểm rủi ro (càng thấp càng tốt)", _num(risk, 0), color=_risk_color(risk)
        ),
        _stat_tile("Điểm chất lượng", _num(quality, 0)),
        _stat_tile("Độ tin cậy đánh giá", _pct(confidence, 0)),
    ]

    veto_notice = ""
    score_breakdown = ((result.get("evidence") or {}).get("score_breakdown")) or {}
    decided_by = score_breakdown.get("decided_by")
    veto_reasons = score_breakdown.get("veto_reasons") or []
    if decided_by and decided_by != "WEIGHTED_AVERAGE":
        avg = score_breakdown.get("weighted_average")
        reason_text = "; ".join(_esc(r) for r in veto_reasons) if veto_reasons else ""
        kind = (
            "quy tắc khẩn cấp (EMERGENCY_OVERRIDE)"
            if decided_by == "EMERGENCY_OVERRIDE"
            else "sàn veto (VETO_FLOOR)"
        )
        veto_notice = (
            '<div class="notice notice-danger">'
            f"<strong>Điểm rủi ro {_num(risk, 0)} KHÔNG phải bình quân 10 chiều</strong> "
            f"— do {kind} quyết định"
            + (
                f", bình quân gia quyền thật ra chỉ {_num(avg, 1)}"
                if avg is not None
                else ""
            )
            + "."
            + (f" Lý do veto: {reason_text}." if reason_text else "")
            + "</div>"
        )

    limited_notice = ""
    if result.get("status") == "LIMITED":
        reason = (
            result.get("limited_reason") or "OKX không công khai đủ dữ liệu cho bot này"
        )
        unavailable = result.get("unavailable") or []
        unavailable_vi = ", ".join(_esc(u) for u in unavailable)
        limited_notice = (
            '<div class="notice notice-warning">'
            f"<strong>ĐÁNH GIÁ HẠN CHẾ (LIMITED)</strong> — {_esc(reason)}."
            + (
                f" Không tính được: {unavailable_vi}. Trần độ tin cậy bị hạ vì thiếu"
                " toàn bộ bằng chứng cấp độ từng lệnh."
                if unavailable_vi
                else ""
            )
            + "</div>"
        )

    return (
        '<header class="report-header">'
        f'<div class="bot-name">{_esc(name)}</div>'
        f'<div class="bot-code">Mã: <code>{_esc(code)}</code></div>'
        f'<div class="verdict-badge" style="--badge-color:{verdict_color}">{_esc(verdict or "THIẾU BẰNG CHỨNG")}</div>'
        f'<div class="stat-row">{"".join(tiles)}</div>'
        f"{limited_notice}{veto_notice}"
        "</header>"
    )


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


# --------------------------------------------------------------------------- #
# Section 2 -- conclusion / recommendation
# --------------------------------------------------------------------------- #


def _render_conclusion(result: Dict[str, Any]) -> str:
    text_lines = result.get("text")
    if not isinstance(text_lines, list) or not text_lines:
        return ""
    paragraphs = []
    for line in text_lines:
        if not isinstance(line, str) or not line.strip():
            continue
        cls = "conclusion-line"
        if line.upper().startswith("KẾT LUẬN") or line.upper().startswith(
            "NGUYÊN NHÂN"
        ):
            cls += " conclusion-strong"
        paragraphs.append(f'<p class="{cls}">{_esc(line)}</p>')
    if not paragraphs:
        return ""
    body = "".join(paragraphs)
    return _section("Kết luận và khuyến nghị", body, anchor="ket-luan")


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
        "Mỗi thanh là một chiều rủi ro độc lập, thang 0-100, <strong>càng cao càng "
        'rủi ro</strong> (ngược với thang "điểm chất lượng"). Thanh xám gạch là '
        "chiều <strong>chưa đo được</strong> — không phải rủi ro thấp, chỉ là "
        "không có bằng chứng, nên bị tính trung tính chứ không được lợi. Điểm rủi "
        "ro tổng ở đầu trang thường KHÔNG phải trung bình cộng đơn giản của các "
        "thanh này: nó là trung bình có trọng số theo mức nghiêm trọng của mỗi "
        "chiều, và có thể bị ghi đè hoàn toàn bởi một sàn veto hoặc quy tắc khẩn "
        "cấp nếu một chiều đủ tệ — xem cảnh báo ở đầu trang nếu điều đó đang xảy ra.",
        "10 chiều và trọng số của chúng đến từ bộ đánh giá QC nội bộ "
        "(<code>Agent/backend/qc/evaluator/lenses/*</code>), mỗi lens tự tính điểm "
        "0-100 từ bằng chứng riêng của nó (hiệu suất đã chốt, mô phỏng Monte Carlo, "
        "kịch bản stress, đối chiếu sổ sách...). Điểm tổng là trung bình có trọng "
        "số qua <code>Agent/backend/qc/scoring/fusion.py</code>, có thể bị ghi đè "
        "bởi veto khi một lỗi đủ nghiêm trọng để điểm trung bình đẹp không được "
        "phép che nó đi.",
    )
    return _section("Điểm từng chiều rủi ro", body + theory, anchor="diem-chieu")


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
        label = DIMENSION_LABEL_VI.get(key, dim.get("dimension_name") or key)
        status = str(dim.get("status") or "AVAILABLE").upper()
        score = dim.get("score")
        tier = dim.get("tier")
        if status == "AVAILABLE" and _is_finite_number(score):
            rows.append(
                _BarRow(
                    label,
                    float(score),
                    _tier_color(tier),
                    f"{float(score):.0f} · {TIER_LABEL_VI.get(str(tier).upper(), tier or '—')}",
                )
            )
        else:
            rows.append(
                _BarRow(
                    label, None, TIER_COLOR["UNKNOWN"], "chưa đo được", measured=False
                )
            )
    bars = _horizontal_bars(rows)
    findings_html = ""
    weak_findings = [
        (DIMENSION_LABEL_VI.get(k, k), (dimensions.get(k) or {}).get("key_findings"))
        for k in DIMENSION_ORDER
        if (dimensions.get(k) or {}).get("score", 0) is not None
        and _is_finite_number((dimensions.get(k) or {}).get("score"))
        and float((dimensions.get(k) or {}).get("score", 0)) >= 70
        and (dimensions.get(k) or {}).get("status") == "AVAILABLE"
    ]
    if weak_findings:
        items = []
        for label, findings in weak_findings[:4]:
            if isinstance(findings, list) and findings:
                items.append(
                    f"<li><strong>{_esc(label)}:</strong> {_esc(findings[0])}</li>"
                )
        if items:
            findings_html = "<ul class='findings'>" + "".join(items) + "</ul>"
    return bars + findings_html


def _render_component_bars(components: List[Any]) -> str:
    rows: List[_BarRow] = []
    for comp in components:
        if not isinstance(comp, dict):
            continue
        label = comp.get("label") or comp.get("name") or "—"
        status = str(comp.get("status") or "AVAILABLE").upper()
        score = comp.get("score")
        if status == "AVAILABLE" and _is_finite_number(score):
            color = _risk_color(score)
            rows.append(_BarRow(label, float(score), color, f"{float(score):.0f}"))
        else:
            tag = "che giấu" if status == "UNKNOWN_CONCEALED" else "thiếu dữ liệu"
            rows.append(
                _BarRow(label, None, TIER_COLOR["UNKNOWN"], tag, measured=False)
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
    theory = _theory(
        "Trục hoành là THỨ TỰ lệnh đã chốt (lệnh #1 → lệnh cuối), không phải thời"
        " gian thực — hai lệnh liền kề trên trục này có thể cách nhau vài phút hoặc"
        " vài ngày. Trục tung là lãi/lỗ CỘNG DỒN kể từ lệnh đầu tiên, bằng USDT thực"
        " tế (không quy đổi %). Một đường đi lên đều là tăng trưởng ổn định; một"
        " đường đi ngang dài rồi tăng vọt ở một lệnh là tăng trưởng phụ thuộc vào vài"
        " lệnh may mắn — hai hình dạng này có thể cho cùng một con số 'tổng lãi' ở"
        " cuối nhưng độ tin cậy khác hẳn nhau. Điểm 'Đáy' đánh dấu đúng lúc vốn cộng"
        " dồn THẤP NHẤT trong toàn bộ lịch sử — đây là một mốc thời điểm, không phải"
        " % sụt vốn (xem mục Số liệu giao dịch cho con số phần trăm đó).",
        "Cộng dồn trực tiếp lãi/lỗ đã chốt (realized_pnl) của từng lệnh, xếp theo"
        " đúng thứ tự thời gian chốt lệnh (close_time) — không nội suy, không làm"
        " mượt, không tính vị thế đang mở.",
    )
    return _subsection("Đường vốn tích luỹ theo lệnh đã chốt", chart, theory)


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
        ("Lệnh thắng", float(win_count), "#16a34a"),
        ("Lệnh thua", float(loss_count), "#dc2626"),
    ]
    if breakeven_count:
        count_slices.append(("Hoà vốn", float(breakeven_count), "#9ca3af"))
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
                    ("Lãi gộp", gross_profit, "#16a34a"),
                    ("Lỗ gộp", gross_loss, "#dc2626"),
                ]
            )

    if not count_pie and not profit_pie:
        return ""

    cells = (
        f'<div class="pie-cell"><h4>Cơ cấu số lệnh</h4>{count_pie}</div>'
        if count_pie
        else ""
    )
    cells += (
        f'<div class="pie-cell"><h4>Cơ cấu lãi/lỗ gộp (USDT)</h4>{profit_pie}</div>'
        if profit_pie
        else ""
    )
    grid = f'<div class="pie-grid">{cells}</div>'

    theory = _theory(
        "Đặt CẠNH NHAU vì chúng trả lời hai câu khác nhau. Bên trái: trong tổng SỐ"
        " LỆNH, bao nhiêu phần trăm thắng/thua. Bên phải: trong tổng TIỀN đã kiếm/đã"
        " mất, bao nhiêu phần là lãi gộp và bao nhiêu là lỗ gộp. Tỉ lệ thắng cao (bên"
        " trái nghiêng hẳn về lãi) nhưng lỗ gộp vẫn chiếm phần lớn bên phải là dấu"
        " hiệu payoff lệch: bot thắng nhiều lệnh nhỏ và thua ít lệnh nhưng mỗi lệnh"
        " thua rất đau — một cú thua có thể xoá sạch nhiều lệnh thắng cộng lại.",
        "Cơ cấu số lệnh tính trực tiếp từ tỉ lệ thắng/thua (win_rate/loss_rate) nhân"
        " số lệnh đã chốt. Cơ cấu lãi/lỗ gộp suy ra từ lãi trung bình mỗi lệnh thắng"
        " (average_win) nhân số lệnh thắng, và lỗ trung bình mỗi lệnh thua"
        " (average_loss) nhân số lệnh thua — cùng nguồn evidence.performance đã dùng"
        " cho bảng Số liệu giao dịch ở dưới, không phải một phép đo mới.",
    )
    return f"<h3>Cơ cấu thắng/thua</h3>{grid}{theory}"


def _render_growth_section(result: Dict[str, Any]) -> str:
    parts = [_render_growth_curve(result), _render_win_loss_composition(result)]
    body = "".join(p for p in parts if p)
    if not body:
        return ""
    return _section("Tăng trưởng & cơ cấu kết quả", body, anchor="tang-truong")


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
            '<div class="notice notice-warning">Mô phỏng này lệch lạc quan: bot đang'
            " ôm lỗ chưa chốt, và distribution bên dưới chỉ tính trên lệnh đã chốt"
            " nên KHÔNG thấy phần lỗ đó — xác suất thực tế xấu hơn số hiển thị.</div>"
        )

    fan_rows: List[Tuple[str, Optional[float]]] = [
        ("P05", mc.get("profit_pct_p05")),
        ("P25", mc.get("profit_pct_p25")),
        ("P50", mc.get("profit_pct_p50")),
        ("P75", mc.get("profit_pct_p75")),
        ("P95", mc.get("profit_pct_p95")),
    ]
    if any(_is_finite_number(v) for _, v in fan_rows):
        chart = _diverging_bars(fan_rows)
        theory = _theory(
            "Mỗi thanh là một phân vị kết quả cuối kỳ mô phỏng, tính theo % vốn tham "
            "chiếu; đường giữa là mốc hoà vốn (0%). Thanh xanh bên phải = có lãi ở "
            "phân vị đó, thanh đỏ bên trái = lỗ. Nếu P05 đã âm sâu, tức trong kịch "
            f"bản xấu (5% tệ nhất), bot lỗ {_num(abs(fan_rows[0][1]), 0) if _is_finite_number(fan_rows[0][1]) else '—'}%"
            " vốn dù kịch bản trung vị (P50) có thể vẫn dương — khoảng cách giữa hai"
            " con số đó chính là độ rủi ro thật, không phải con số trung vị một mình.",
            f"Bootstrap khối dừng (stationary bootstrap, Politis &amp; Romano 1994) trên"
            f" {_int_text(mc.get('sample_size'))} lệnh đã chốt, lặp lại"
            f" {_int_text(mc.get('iterations'))} lần, mỗi lần vẽ ra {_int_text(mc.get('horizon_trades'))}"
            " lệnh. Độ dài khối là ngẫu nhiên hình học với kỳ vọng L = n^(1/3) thay vì"
            " một số cố định, để không có một lựa chọn L nào tự áp đặt lên kết quả."
            " Mô phỏng chỉ dùng lệnh ĐÃ CHỐT, không tính vị thế đang mở — nếu bot"
            " đang ôm lỗ chưa chốt (xem cảnh báo phía trên nếu có), các xác suất này"
            " lạc quan hơn thực tế.",
        )
        parts.append(_subsection("Phân vị kết quả cuối kỳ", chart, theory))

    dd_rows: List[Tuple[str, Optional[float]]] = [
        ("Trung vị", mc.get("median_max_drawdown")),
        ("P90", mc.get("p90_max_drawdown")),
        ("P95", mc.get("p95_max_drawdown")),
        ("P99", mc.get("p99_max_drawdown")),
        ("Xấu nhất", mc.get("worst_percentile_drawdown")),
    ]
    if any(_is_finite_number(v) for _, v in dd_rows):
        chart = _vertical_bars(dd_rows, max_value=100.0)
        theory = _theory(
            "Sụt vốn tối đa mô phỏng được trong mỗi phân vị đường chạy, không phải "
            'sụt vốn đã xảy ra. Cột "Xấu nhất" là đường chạy tệ nhất trong toàn bộ'
            " số lần lặp — một cột gần 100% nghĩa là có kịch bản dẫn tới cháy gần hết"
            " vốn tham chiếu, dù trung vị vẫn có thể trông ổn.",
            "Tính trên cùng bộ mô phỏng bootstrap khối dừng ở trên, lấy sụt vốn tối đa"
            " trong mỗi đường chạy rồi xếp theo phân vị qua toàn bộ số lần lặp.",
        )
        parts.append(_subsection("Sụt vốn theo phân vị mô phỏng", chart, theory))

    parts.append(_render_horizon_comparison(mc))
    parts.append(_render_horizon_probability_chart(mc))
    parts.append(_render_key_probabilities(mc))

    body = "".join(p for p in parts if p)
    if not body:
        return ""
    return _section("Mô phỏng Monte Carlo", body, anchor="monte-carlo")


def _subsection(title: str, chart: str, theory: str) -> str:
    if not chart:
        return ""
    return f"<h3>{_esc(title)}</h3>{chart}{theory}"


def _render_horizon_comparison(mc: Dict[str, Any]) -> str:
    scenarios = mc.get("horizon_scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return ""
    by_label = {s.get("label"): s for s in scenarios if isinstance(s, dict)}
    cards = []
    for key in ("SHORT", "MEDIUM", "LONG"):
        s = by_label.get(key)
        if not s:
            continue
        pop = s.get("probability_of_profit")
        cards.append(
            '<div class="horizon-card">'
            f'<div class="horizon-title">{_esc(HORIZON_LABEL_VI.get(key, key))}</div>'
            f'<div class="horizon-trades">{_int_text(s.get("horizon_trades"))} lệnh</div>'
            f'<div class="horizon-pop" style="color:{_risk_color(100 - float(pop)) if _is_finite_number(pop) else "inherit"}">'
            f"{_pct(pop, 0)} khả năng có lãi</div>"
            f'<div class="horizon-sub">P(lỗ cuối kỳ) {_pct(s.get("p_loss_after_horizon"), 0)} ·'
            f" P(cháy vốn) {_pct(s.get('p_ruin'), 0)}</div>"
            "</div>"
        )
    if not cards:
        return ""
    label = mc.get("horizon_stability_label")
    label_html = f'<div class="horizon-label">{_esc(label)}</div>' if label else ""
    exceeds_html = ""
    if mc.get("horizon_exceeds_observed"):
        days = mc.get("horizon_calendar_days")
        span = mc.get("observed_span_days")
        detail = (
            f" (mô phỏng ≈ {_num(days, 0)} ngày, dữ liệu quan sát được chỉ"
            f" {_num(span, 0)} ngày)"
            if _is_finite_number(days) and _is_finite_number(span)
            else ""
        )
        exceeds_html = (
            '<div class="notice notice-warning">Horizon mô phỏng dài hơn dữ liệu thực'
            f" đã quan sát{detail}: đây là NGOẠI SUY vượt quá dữ liệu quan sát được,"
            " không phải một kết quả đã kiểm chứng.</div>"
        )
    theory = _theory(
        "So sánh cùng một bot ở ba độ dài mô phỏng khác nhau: NGẮN (vài lệnh sắp"
        " tới), TRUNG (bằng đúng số lệnh bot đã có), DÀI (nhiều lệnh hơn, ngoại suy"
        " xa hơn). Nếu ba thẻ đồng thuận (đều cao hoặc đều thấp), kết luận không"
        " phụ thuộc vào việc chọn horizon nào. Nếu lệch nhau — ví dụ ổn ở NGẮN"
        " nhưng xấu dần ở DÀI — nhãn phía trên sẽ nói rõ kiểu lệch đó, và đó là"
        " tín hiệu quan trọng hơn bất kỳ con số đơn lẻ nào.",
        "Cùng cỗ máy bootstrap khối dừng ở trên, chạy lại ba lần với ba giá trị"
        ' horizon_trades khác nhau. "NGẮN/TRUNG/DÀI" và số ngày lịch quy đổi dùng'
        " nhịp độ giao dịch quan sát được (lệnh/ngày) của chính bot này, không phải"
        " một hằng số chung cho mọi bot.",
    )
    return _subsection(
        "So sánh đa horizon",
        f'<div class="horizon-row">{"".join(cards)}</div>{label_html}{exceeds_html}',
        theory,
    )


def _render_horizon_probability_chart(mc: Dict[str, Any]) -> str:
    """Grouped-bar counterpart to `_render_horizon_comparison`'s text cards
    above: the same three horizons' `probability_of_profit`, but as an actual
    chart rather than three numbers a reader has to compare by eye across
    separate cards. Project owner's own explicit request ("biểu đồ cột nhóm
    so sánh xác suất có lãi giữa ba horizon").
    """
    scenarios = mc.get("horizon_scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return ""
    by_label = {s.get("label"): s for s in scenarios if isinstance(s, dict)}
    rows: List[Tuple[str, Optional[float]]] = []
    for key in ("SHORT", "MEDIUM", "LONG"):
        s = by_label.get(key)
        if not s:
            continue
        rows.append((HORIZON_LABEL_VI.get(key, key), s.get("probability_of_profit")))
    if not rows or not any(_is_finite_number(v) for _, v in rows):
        return ""
    chart = _vertical_bars(rows, max_value=100.0, unit="%", higher_is_better=True)
    theory = _theory(
        "Mỗi cột là xác suất mô phỏng kết thúc horizon đó CÓ LÃI (không phải mức lãi"
        " bao nhiêu, chỉ là có hay không) — cột cao là tốt, ngược cực với biểu đồ sụt"
        " vốn ở trên (cột cao ở đó là xấu), nên màu ở đây xanh cho cột cao, đỏ cho cột"
        " thấp thay vì ngược lại. Ba cột tụt dần từ NGẮN xuống DÀI nghĩa là lợi thế"
        " thống kê mỏng dần khi nhìn xa hơn; ba cột đứng yên hoặc tăng nghĩa là kết"
        " luận không phụ thuộc việc chọn horizon nào.",
        "Cùng bộ dữ liệu `horizon_scenarios` phía trên, chỉ trực quan hoá lại một"
        " trường duy nhất (`probability_of_profit`) thành cột thay vì thẻ số để dễ so"
        " sánh ba horizon cùng lúc bằng mắt.",
    )
    return _subsection("So sánh xác suất có lãi theo horizon (biểu đồ)", chart, theory)


def _render_key_probabilities(mc: Dict[str, Any]) -> str:
    rows: List[Tuple[str, str]] = []
    if _is_finite_number(mc.get("p_ruin")):
        rows.append(("Xác suất cháy tài khoản", _pct(mc.get("p_ruin"), 1)))
    if _is_finite_number(mc.get("p_loss_after_horizon")):
        rows.append(
            (
                "Xác suất lỗ khi kết thúc horizon",
                _pct(mc.get("p_loss_after_horizon"), 1),
            )
        )

    streak_rows: List[List[str]] = []
    for n, obs_key, base_key, excess_key in (
        (5, "p_5_loss_streak", "p_5_loss_streak_baseline", "p_5_loss_streak_excess"),
        (
            10,
            "p_10_loss_streak",
            "p_10_loss_streak_baseline",
            "p_10_loss_streak_excess",
        ),
    ):
        obs = mc.get(obs_key)
        if not _is_finite_number(obs):
            continue
        base = mc.get(base_key)
        excess = mc.get(excess_key)
        streak_rows.append(
            [
                f"≥{n} lệnh thua liên tiếp",
                _pct(obs, 1),
                _pct(base, 1) if _is_finite_number(base) else "chưa có mốc",
                _pct(excess, 1) if _is_finite_number(excess) else "—",
            ]
        )

    body = ""
    if rows:
        tiles = "".join(_stat_tile(label, value) for label, value in rows)
        body += f'<div class="stat-row">{tiles}</div>'
    if streak_rows:
        body += _table(
            ["Chuỗi thua", "Quan sát", "Mốc cơ sở (ngẫu nhiên thuần)", "Phần vượt"],
            streak_rows,
        )
    if not body:
        return ""
    theory = _theory(
        '"Quan sát" là xác suất mô phỏng thấy chuỗi thua đó thật sự xảy ra. Nhưng'
        " xác suất gặp một chuỗi thua dài tăng lên khi bot giao dịch càng nhiều lệnh"
        ' — kể cả một chiến lược hoàn toàn ngẫu nhiên, độc lập giữa các lệnh. "Mốc'
        ' cơ sở" là xác suất chuỗi đó xảy ra CHỈ VÌ số lệnh nhiều, giả định mỗi'
        ' lệnh độc lập với tỉ lệ thắng y hệt bot này. "Phần vượt" (quan sát trừ'
        " mốc cơ sở) mới là tín hiệu thật về việc thua có xu hướng dồn cục ở bot"
        " này hay không — phần vượt cao nghĩa là các lệnh thua không độc lập với"
        " nhau (hành vi kiểu gồng lỗ/martingale), phần vượt gần 0 nghĩa là chuỗi"
        " thua chỉ là hệ quả tất yếu của việc đã giao dịch nhiều lệnh, không phải"
        " lỗi hành vi.",
        "Mốc cơ sở tính giải tích từ phân phối nhị thức trên đúng số lệnh và tỉ lệ"
        " thua quan sát của bot (không phải mô phỏng lại) — xem"
        " <code>MonteCarloSimulationEngine.loss_streak_baseline_probability</code>."
        " Phần vượt = quan sát − mốc cơ sở, giới hạn dưới ở 0.",
    )
    return _subsection("Các xác suất chính", body, theory)


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
            "<strong>Suy luận thống kê KHÔNG đáng tin cậy</strong> ở bot này"
            + (f": {notes_html}." if notes_html else ".")
            + " Đọc các con số bên dưới như tham khảo, không phải kết luận chắc chắn."
            "</div>"
        )

    rows = [
        ["Sharpe mỗi lệnh", _num(mc.get("sharpe_per_trade"), 2)],
        [
            "Probabilistic Sharpe Ratio (PSR)",
            _pct(_ratio_to_pct(mc.get("probabilistic_sharpe")), 1),
        ],
        [
            "Deflated Sharpe Ratio (DSR)",
            _pct(_ratio_to_pct(mc.get("deflated_sharpe")), 1),
        ],
        [
            "Số lệnh tối thiểu cần có (MinTRL)",
            _int_text(mc.get("min_track_record_trades")),
        ],
        ["Cỡ mẫu đã dùng để suy luận", _int_text(mc.get("sample_size"))],
        [
            "Số ứng viên đã so sánh để chọn bot này",
            _int_text(mc.get("selection_trials")),
        ],
    ]
    table = _table(["Chỉ số", "Giá trị"], rows)

    theory = _theory(
        "PSR trả lời: xác suất Sharpe THẬT của bot lớn hơn 0, sau khi trừ hao vì mẫu"
        " ngắn, lệch (skew) và đuôi dày của phân phối lợi nhuận — một Sharpe đẹp"
        " trên vài chục lệnh đuôi dày không phải bằng chứng ngang với Sharpe khiêm"
        " tốn trên vài trăm lệnh sạch. DSR đi xa hơn: bot này được CHỌN vì là ứng"
        " viên tốt nhất trong một nhóm — càng nhiều ứng viên so sánh, càng dễ có"
        ' một cái "tốt nhất" chỉ vì may mắn; DSR trừ luôn phần may mắn kỳ vọng đó.'
        " MinTRL là số lệnh tối thiểu bot cần thêm để Sharpe của nó đủ tin cậy ở"
        " ngưỡng đang dùng — càng lớn so với số lệnh hiện có, kết luận càng non.",
        "Probabilistic/Deflated Sharpe Ratio và MinTRL theo Bailey &amp; López de"
        " Prado (2012, 2014). Ngưỡng so sánh dùng SR* = 0 (Sharpe không có lợi thế)"
        ' — đây là mốc do hệ thống này TỰ CHỌN để hỏi "có lợi thế thật không",'
        " không phải một mốc vay mượn từ nơi khác hay từ chính bot. DSR dùng số"
        " ứng viên đã so sánh (selection_trials) để trừ hao phần may mắn của việc"
        " chọn ra cái tốt nhất.",
    )
    return _section(
        "Suy luận thống kê",
        unreliable_notice + table + theory,
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
    ("trade_count", "Số lệnh đã chốt", "int"),
    ("win_rate", "Tỉ lệ thắng", "pct"),
    ("profit_factor", "Profit factor", "num2"),
    ("payoff_ratio", "Payoff ratio", "num2"),
    ("expectancy", "Kỳ vọng mỗi lệnh", "money"),
    ("total_pnl", "Tổng lãi/lỗ", "money"),
    ("max_drawdown_pct", "Sụt vốn tối đa", "pct"),
    ("current_drawdown_pct", "Sụt vốn hiện tại", "pct"),
    ("sharpe_ratio", "Sharpe ratio", "num2"),
    ("sortino_ratio", "Sortino ratio", "num2"),
    ("calmar_ratio", "Calmar ratio", "num2"),
    ("max_win_streak", "Chuỗi thắng dài nhất", "int"),
    ("max_loss_streak", "Chuỗi thua dài nhất", "int"),
    ("average_hold_time_minutes", "Thời gian giữ lệnh trung bình (phút)", "num1"),
    ("trade_frequency_per_day", "Lệnh / ngày", "num2"),
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
        rows.append([label, _FORMATTERS[kind](perf.get(key))])
    if not rows:
        return ""
    table = _table(["Chỉ số", "Giá trị"], rows)
    theory = _theory(
        "Đây là số liệu trên SỔ ĐÃ CHỐT — lệnh đang mở không nằm trong các con số"
        " này (xem mục Tài sản đang giao dịch để biết vị thế đang mở). Profit"
        " factor dưới 1 nghĩa là tổng lệnh thua lớn hơn tổng lệnh thắng — bot đang"
        " lỗ ròng, bất kể tỉ lệ thắng trông đẹp thế nào. Sharpe/Sortino/Calmar là"
        " lợi nhuận trên một đơn vị rủi ro (biến động, biến động xấu, sụt vốn theo"
        " thứ tự) — càng cao càng tốt, nhưng chỉ đáng tin khi cỡ mẫu đủ lớn (xem"
        " mục Suy luận thống kê).",
        "Tính trực tiếp từ nhật ký giao dịch (trade ledger) công khai của bot trên"
        " OKX copy-trading, theo định nghĩa chuẩn của từng chỉ số (profit factor ="
        " tổng lãi / tổng lỗ tuyệt đối, payoff ratio = lãi trung bình / lỗ trung"
        " bình, Sharpe/Sortino/Calmar theo công thức thống kê thông thường trên"
        " chuỗi lợi nhuận từng lệnh).",
    )
    return _section("Số liệu giao dịch", table + theory, anchor="so-lieu")


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
                _num(a.get("last_close_days"), 1) + " ngày"
                if _is_finite_number(a.get("last_close_days"))
                else "chưa từng chốt",
            ]
        )
    if not rows:
        return ""
    table = _table(
        ["Tài sản", "Trạng thái", "Vị thế mở", "Lệnh đã chốt", "Lần chốt gần nhất"],
        rows,
    )
    theory = _theory(
        "<strong>ĐANG GIAO DỊCH</strong>: có lệnh chốt gần đây, bot còn hoạt động"
        " tích cực trên tài sản này. <strong>CHỈ ĐANG ÔM</strong>: còn vị thế mở"
        " nhưng đã lâu không chốt lệnh nào — bản thân trạng thái này là một tín"
        " hiệu rủi ro, mẫu hình thường gặp là ôm lỗ chờ giá quay lại thay vì cắt"
        " lỗ. <strong>ĐÃ RỜI</strong>: từng giao dịch nhưng không còn vị thế mở và"
        " cũng không còn chốt lệnh mới — tài sản này không còn đại diện cho hoạt"
        " động hiện tại của bot.",
        "Suy từ vị thế đang mở và lịch sử lệnh đã chốt trong sổ lệnh công khai:"
        " một tài sản có lệnh chốt trong cửa sổ hoạt động gần đây được coi là đang"
        " giao dịch; còn vị thế mở nhưng ngoài cửa sổ đó thì là chỉ đang ôm; không"
        " còn gì thì là đã rời.",
    )
    return _section("Tài sản đang giao dịch", table + theory, anchor="tai-san")


# --------------------------------------------------------------------------- #
# NOT_FOUND page
# --------------------------------------------------------------------------- #


def _render_not_found_body(result: Dict[str, Any]) -> str:
    code = result.get("code") or ""
    text_lines = result.get("text") or []
    message = (
        text_lines[0]
        if text_lines and isinstance(text_lines[0], str)
        else (f"Không tìm thấy bot với mã {code!r} trên OKX.")
    )
    return (
        '<div class="card not-found">'
        "<h1>Không tìm thấy bot</h1>"
        f"<p>Mã tra cứu: <code>{_esc(code)}</code></p>"
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
  padding: 0 16px 3rem;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  line-height: 1.55;
}
.page { max-width: 880px; margin: 0 auto; }
.report-header {
  padding: 1.5rem 0 1rem;
}
.bot-name { font-size: 1.5rem; font-weight: 700; overflow-wrap: anywhere; }
.bot-code { color: var(--muted); font-size: 0.9rem; margin-top: 0.15rem; }
.bot-code code { background: var(--track); padding: 0.1rem 0.4rem; border-radius: 4px; }
.verdict-badge {
  display: inline-block;
  margin-top: 0.6rem;
  padding: 0.3rem 0.8rem;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.85rem;
  letter-spacing: 0.02em;
  color: #fff;
  background: var(--badge-color, #6b7280);
}
.stat-row { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1rem; }
.stat-tile {
  flex: 1 1 140px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
}
.stat-value { font-size: 1.6rem; font-weight: 700; }
.stat-label { color: var(--muted); font-size: 0.8rem; margin-top: 0.15rem; }
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.1rem 1.2rem 1.3rem;
  margin-top: 1rem;
}
.card h2 { margin: 0 0 0.75rem; font-size: 1.15rem; }
.card h3 { margin: 1.1rem 0 0.4rem; font-size: 1rem; }
.notice {
  border-left: 4px solid;
  border-radius: 6px;
  padding: 0.6rem 0.85rem;
  margin-top: 0.75rem;
  font-size: 0.92rem;
}
.notice-warning { background: var(--notice-warning-bg); border-color: var(--notice-warning-border); }
.notice-danger { background: var(--notice-danger-bg); border-color: var(--notice-danger-border); }
.conclusion-line { margin: 0.5rem 0; }
.conclusion-strong { font-weight: 600; }
.table-scroll { overflow-x: auto; margin-top: 0.5rem; }
table { border-collapse: collapse; width: 100%; min-width: 320px; font-size: 0.92rem; }
th, td { text-align: left; padding: 0.4rem 0.7rem; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { color: var(--muted); font-weight: 600; }
td:first-child, th:first-child { white-space: normal; }
.badge {
  display: inline-block;
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #fff;
  background: var(--badge-color, #6b7280);
}
details.theory {
  margin-top: 0.9rem;
  border: 1px dashed var(--border);
  border-radius: 8px;
  padding: 0.5rem 0.8rem;
}
details.theory summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--muted);
}
.theory-body { font-size: 0.88rem; margin-top: 0.5rem; color: var(--text); }
.theory-body p { margin: 0.4rem 0; }
.theory-body code { background: var(--track); padding: 0.05rem 0.3rem; border-radius: 4px; }
.findings { margin: 0.5rem 0 0; padding-left: 1.2rem; font-size: 0.88rem; color: var(--muted); }
.findings li { margin: 0.2rem 0; }
svg.bar-chart { display: block; margin-top: 0.4rem; }
svg text { fill: var(--text); font-size: 12px; }
svg .bar-label, svg .bar-label-sm { fill: var(--muted); font-size: 11.5px; }
svg .bar-value, svg .bar-value-sm { font-weight: 600; font-size: 11.5px; }
.horizon-row { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 0.5rem; }
.horizon-card {
  flex: 1 1 150px;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
}
.horizon-title { font-weight: 700; font-size: 0.85rem; letter-spacing: 0.03em; color: var(--muted); }
.horizon-trades { font-size: 0.8rem; color: var(--muted); margin-top: 0.15rem; }
.horizon-pop { font-size: 1.25rem; font-weight: 700; margin-top: 0.3rem; }
.horizon-sub { font-size: 0.78rem; color: var(--muted); margin-top: 0.25rem; }
.horizon-label { margin-top: 0.5rem; font-size: 0.85rem; font-weight: 600; }
.not-found { text-align: center; padding: 2.5rem 1.2rem; }
.not-found h1 { font-size: 1.3rem; }
svg.line-chart { display: block; margin-top: 0.4rem; }
svg .line-axis-label { fill: var(--muted); font-size: 10.5px; }
svg .line-marker { font-weight: 600; font-size: 10.5px; }
svg .line-end-label { font-weight: 700; font-size: 12.5px; }
svg.pie-chart { display: block; }
svg .pie-label { font-weight: 600; font-size: 11.5px; }
svg .pie-value { fill: var(--muted); font-size: 11px; }
svg .pie-empty { fill: var(--muted); font-size: 12px; }
.pie-grid { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 0.5rem; }
.pie-cell { flex: 1 1 220px; min-width: 0; }
.pie-cell h4 { margin: 0 0 0.3rem; font-size: 0.9rem; color: var(--muted); }
.admin-banner {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-top: 1rem;
  padding: 0.5rem 0.85rem;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.85rem;
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
footer.report-footer {
  color: var(--muted);
  font-size: 0.78rem;
  text-align: center;
  margin-top: 1.5rem;
}
@media (max-width: 480px) {
  .bot-name { font-size: 1.25rem; }
  .stat-value { font-size: 1.35rem; }
}
"""


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def render_bot_report_html(
    result: Dict[str, Any],
    *,
    is_admin: bool = False,
    admin_back_url: str = "/admin",
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
    """
    if not isinstance(result, dict):
        result = {}
    status = result.get("status")
    name = result.get("name") or result.get("code") or "Bot"

    if status == "NOT_FOUND":
        body = _render_not_found_body(result)
        title = f"Không tìm thấy · {name}"
    else:
        sections = [
            _render_header(result),
            _render_conclusion(result),
            _render_dimensions_section(result),
            _render_growth_section(result),
            _render_monte_carlo(result),
            _render_statistical_inference(result),
            _render_trade_metrics(result),
            _render_assets(result),
        ]
        body = "".join(s for s in sections if s)
        if not body:
            body = _render_not_found_body(result)
        title = f"Báo cáo bot: {name}"

    footer = (
        '<footer class="report-footer">Đánh giá tự động dựa trên dữ liệu công khai'
        " OKX copy-trading, KHÔNG PHẢI lời khuyên đầu tư. Người đọc tự chịu trách"
        " nhiệm với quyết định của mình.</footer>"
    )

    admin_banner = ""
    if is_admin:
        admin_banner = (
            '<div class="admin-banner">'
            '<span class="admin-badge">ADMIN</span>'
            f'<a href="{_esc(admin_back_url)}">← Quay lại danh sách admin</a>'
            "</div>"
        )

    return (
        "<!doctype html>\n"
        '<html lang="vi">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"<title>{_esc(title)}</title>\n"
        # Việc 3: tokens.css's raw text embedded FIRST, so the `:root`
        # custom-property definitions it declares are already in scope for
        # every `var(...)` reference `_CSS` below makes to them -- CSS custom
        # properties are read at USE time, not declaration-order-sensitive
        # the way a Sass variable would be, but keeping the token
        # declarations first still matches how a human reads the stylesheet
        # top to bottom (tokens, then the rules that consume them).
        f"<style>{_design_tokens_css_text()}\n{_CSS}</style>\n"
        "</head>\n<body>\n"
        f'<div class="page">{admin_banner}{body}{footer}</div>\n'
        "</body>\n</html>\n"
    )
