"""The one block a portfolio report has that a single-bot report cannot.

WHY THIS IS A SEPARATE MODULE AND NOT PART OF report_page.py. A portfolio is
rendered by the SAME `render_bot_report_html` a single bot is, because its
subject is an ordinary `RiskSupervisionResult` whose bot happens to be several
ledgers merged into one (see `bot.mcp.aggregate.PortfolioAggregator`). That is
the whole point: one renderer, one stylesheet, one set of tabs, so the two
reports cannot drift apart. This module adds the diversification block on top
of that finished document instead of teaching the renderer a second subject,
which would have meant every future change to the report being made twice.

ON THE FIVE-SECTION RULE. `test_render_invariants.py::test_result_tab_stays_an
_overview` pins the Analyst Result tab to exactly five sections, and this block
is injected as a sixth -- on the PORTFOLIO page only. That invariant is a
product decision about the single-bot page, which this module never touches:
it runs against a single-bot fixture and keeps passing. The correlation verdict
is put on that tab deliberately, because for a set of bots it is the headline
answer, not a detail: a reader who never leaves the first tab must still be
told that their three bots are one position.

EVERY value rendered here is escaped at the point of use. Bot nicknames come
from OKX and are attacker-controlled for practical purposes; the fact that the
surrounding document escapes its own values buys this module nothing.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Sequence

# Anchor inside the finished document. One anchor, not two, is why the block
# is a section on an existing tab rather than a fourth tab: adding a tab means
# matching the tab BAR markup as well, and that is the part currently being
# reworked.
_PANEL_ANCHOR = '<div class="tab-panel panel-report" id="panel-report" role="tabpanel">'

_VERDICT_TONE = {
    "DIVERSIFIED": ("ok", "Diversified"),
    "MODERATE_CO_MOVEMENT": ("warn", "Moderate co-movement"),
    "HIGH_CORRELATION_CLUSTER": ("bad", "High correlation cluster"),
    "INSUFFICIENT_EVIDENCE": ("mute", "Insufficient evidence"),
}
_STYLE_TONE = {
    "DISTINCT_PLAYBOOKS": ("ok", "Distinct playbooks"),
    "PARTIAL_OVERLAP": ("warn", "Partial overlap"),
    "SAME_PLAYBOOK": ("bad", "Same playbook"),
    "INSUFFICIENT_EVIDENCE": ("mute", "Insufficient evidence"),
}

_CSS = """
<style>
/* Colours come from the page's own tokens, never hard-coded. The default
   :root palette in report_page.py is the LIGHT one, with a dark variant
   switched by data-theme/prefers-color-scheme, so a literal #94a3b8 or an
   rgba(255,255,255,...) background is wrong in one of the two themes. The
   tints below are translucent on purpose: they layer correctly over either
   background, and every one of them keeps its text on var(--ink). */
.pf-wrap{display:flex;flex-direction:column;gap:18px;min-width:0}
.pf-wrap>*{min-width:0;max-width:100%}
.pf-wrap p,.pf-wrap li,.pf-sub{overflow-wrap:anywhere}
.pf-verdicts{display:flex;flex-wrap:wrap;gap:10px}
.pf-badge{display:inline-flex;align-items:baseline;gap:8px;padding:6px 14px;
 border-radius:999px;font-size:13px;font-weight:700;letter-spacing:.02em;
 border:1px solid currentColor;max-width:100%;overflow-wrap:anywhere}
.pf-badge small{font-weight:400;color:var(--ink-2);letter-spacing:0}
.pf-ok{color:var(--up);background:color-mix(in srgb,var(--up) 12%,transparent)}
.pf-warn{color:var(--amber);background:color-mix(in srgb,var(--amber) 14%,transparent)}
.pf-bad{color:var(--down);background:color-mix(in srgb,var(--down) 14%,transparent)}
.pf-mute{color:var(--ink-3);background:color-mix(in srgb,var(--ink-3) 12%,transparent)}
@supports not (background:color-mix(in srgb,red 10%,transparent)){
 .pf-ok,.pf-warn,.pf-bad,.pf-mute{background:var(--panel-2)}
}
.pf-conflict{border-left:3px solid var(--down);padding:12px 14px;border-radius:8px;
 background:var(--panel-2);line-height:1.55;overflow-wrap:anywhere}
.pf-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
 gap:12px;min-width:0}
.pf-grid>*{min-width:0}
/* Every wide block gets its OWN horizontal scroller. `.main` sets
   overflow-x:hidden, so anything that overflows the page is CLIPPED, not
   scrollable -- an 8-bot matrix would simply lose its right-hand columns. */
.pf-scroll{overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch}
.pf-matrix{border-collapse:separate;border-spacing:3px;font-size:12px;
 min-width:max-content}
.pf-matrix th{font-weight:700;color:var(--ink-2);padding:4px 6px;text-align:center;
 white-space:nowrap;max-width:118px;overflow:hidden;text-overflow:ellipsis}
.pf-matrix th.pf-row-head{text-align:right;position:sticky;left:0;
 background:var(--panel);z-index:1}
.pf-matrix td{text-align:center;padding:9px 8px;border-radius:6px;color:var(--ink);
 font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.pf-na{color:var(--ink-3);font-weight:400}
.pf-legend{display:flex;flex-wrap:wrap;gap:10px 14px;font-size:11.5px;
 color:var(--ink-2);margin-top:6px}
.pf-legend span{display:inline-flex;align-items:center;gap:5px}
.pf-swatch{width:12px;height:12px;border-radius:3px;display:inline-block;flex:0 0 auto}
.pf-bar{height:7px;border-radius:4px;background:var(--track);overflow:hidden}
.pf-bar i{display:block;height:100%;border-radius:4px;background:var(--info)}
.pf-sub{font-size:11.5px;color:var(--ink-2);margin-top:4px;line-height:1.5}
.pf-name{display:inline-block;max-width:210px;overflow:hidden;text-overflow:ellipsis;
 white-space:nowrap;vertical-align:bottom}
.pf-h4{margin:0 0 4px;font-size:14px}
.pf-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));
 gap:18px;min-width:0}
.pf-cols>*{min-width:0}
@media (max-width:720px){
 .pf-matrix{font-size:11px}
 .pf-matrix td{padding:7px 5px}
 .pf-matrix th{max-width:84px}
 .pf-name{max-width:130px}
}
</style>
"""


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _num(value: Any, digits: int = 2, suffix: str = "", sign: bool = False) -> str:
    """A number, or an em dash. Never a zero standing in for 'not measured'."""
    if value is None or not isinstance(value, (int, float)):
        return "&mdash;"
    fmt = f"{{:+.{digits}f}}" if sign else f"{{:.{digits}f}}"
    return _esc(fmt.format(float(value))) + suffix


def _pearson_style(value: Optional[float]) -> str:
    """Colour a correlation cell. Absence is grey, never green."""
    if value is None:
        return "background:var(--panel-2);color:var(--ink-3)"
    if value >= 0.7:
        return "background:rgba(220,38,38,.26);color:var(--down)"
    if value >= 0.4:
        return "background:rgba(217,119,6,.22)"
    if value >= 0.1:
        return "background:rgba(2,132,199,.15)"
    if value <= -0.2:
        return "background:rgba(5,150,105,.20)"
    return "background:var(--panel-2)"


def _style_cell(value: Optional[float]) -> str:
    """Colour a behaviour-distance cell. LOW distance is the dangerous end,
    which is the opposite of the correlation matrix -- hence its own scale and
    its own legend rather than reusing the one above."""
    if value is None:
        return "background:var(--panel-2);color:var(--ink-3)"
    if value <= 0.15:
        return "background:rgba(220,38,38,.26);color:var(--down)"
    if value <= 0.30:
        return "background:rgba(217,119,6,.22)"
    return "background:rgba(5,150,105,.18)"


def _name(value: Any, limit: int = 80) -> str:
    """A bot nickname, clipped in CSS and carried in full in `title`.

    OKX nicknames are free text: they can be long, can be a single unbroken
    run of characters with nowhere to wrap, and can be emoji. Left alone they
    stretch a table cell past the page, and `.main` sets `overflow-x:hidden`
    so the overflow is CLIPPED rather than scrollable -- the column simply
    disappears. The hard cap is a second line of defence for the pathological
    case where even a scroller would be unusable.
    """
    text = "" if value is None else str(value)
    clipped = text if len(text) <= limit else text[: limit - 1] + "\u2026"
    return f'<span class="pf-name" title="{_esc(text)}">{_esc(clipped)}</span>'


def _stat(label: str, value: str, sub: str = "") -> str:
    return (
        '<div class="kp-stat-item">'
        f'<div class="kp-stat-label">{_esc(label)}</div>'
        f'<div class="kp-stat-val">{value}</div>'
        + (f'<div class="kp-stat-sub">{sub}</div>' if sub else "")
        + "</div>"
    )


def _badge(tone_map: Dict[str, Any], key: str, prefix: str, reason: str) -> str:
    tone, label = tone_map.get(key, ("mute", key or "UNKNOWN"))
    return (
        f'<span class="pf-badge pf-{tone}">{_esc(prefix)}: {_esc(label)}'
        + (f" <small>{_esc(reason)}</small>" if reason else "")
        + "</span>"
    )


# --------------------------------------------------------------------------- #


def _matrices(correlation: Dict[str, Any], pairs: Sequence[Dict[str, Any]]) -> str:
    labels: List[str] = list(correlation.get("labels") or [])
    if len(labels) < 2:
        return ""
    pearson = correlation.get("pearson") or []
    # Behaviour distance arrives per pair, not as a grid; rebuild the grid so
    # the two matrices can be read side by side at the same coordinates. That
    # comparison is the entire point: a cell green on the left and red on the
    # right is a pair whose results look unrelated while its trading is not.
    index = {label: position for position, label in enumerate(labels)}
    style_grid: List[List[Optional[float]]] = [
        [None] * len(labels) for _ in labels
    ]
    for pair in pairs:
        style = pair.get("style") or {}
        distance = style.get("exit_distance")
        left, right = index.get(pair.get("label_a")), index.get(pair.get("label_b"))
        if distance is None or left is None or right is None:
            continue
        style_grid[left][right] = style_grid[right][left] = float(distance)
    for position in range(len(labels)):
        style_grid[position][position] = 0.0

    def grid(values, styler, title, hint, legend) -> str:
        head = "".join(
                f'<th title="{_esc(label)}">{_esc(label)}</th>' for label in labels
            )
        rows = []
        for row, label in enumerate(labels):
            cells = []
            for column in range(len(labels)):
                raw = None
                if row < len(values) and column < len(values[row]):
                    raw = values[row][column]
                text = (
                    '<span class="pf-na">n/a</span>'
                    if raw is None
                    else _esc(f"{float(raw):+.2f}" if styler is _pearson_style
                              else f"{float(raw):.2f}")
                )
                cells.append(f'<td style="{styler(raw)}">{text}</td>')
            rows.append(
                f'<tr><th class="pf-row-head" title="{_esc(label)}">'
                f'{_esc(label)}</th>{"".join(cells)}</tr>'
            )
        return (
            "<div>"
            f'<h4 class="pf-h4">{_esc(title)}</h4>'
            f'<div class="pf-sub">{hint}</div>'
            '<div class="pf-scroll">'
            f'<table class="pf-matrix"><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            "</div>"
            f'<div class="pf-legend">{legend}</div>'
            "</div>"
        )

    def swatch(colour: str, text: str) -> str:
        return (
            f'<span><i class="pf-swatch" style="background:{colour}"></i>{_esc(text)}</span>'
        )

    return (
        '<div class="pf-cols">'
        + grid(
            pearson,
            _pearson_style,
            "Results move together (Pearson)",
            "Measured on realised PnL over the shared time buckets. "
            "High is the dangerous end.",
            swatch("rgba(220,38,38,.26)", "0.7+ moves as one")
            + swatch("rgba(217,119,6,.22)", "0.4-0.7")
            + swatch("rgba(2,132,199,.15)", "0.1-0.4")
            + swatch("rgba(5,150,105,.20)", "-0.2 or lower, offsets")
            + swatch("var(--panel-2)", "not measurable"),
        )
        + grid(
            style_grid,
            _style_cell,
            "They trade the same way (exit-rule distance)",
            "Measured on exit discipline, independent of results. "
            "<strong>LOW is the dangerous end here</strong> &mdash; 0 means "
            "identical behaviour.",
            swatch("rgba(220,38,38,.26)", "0.15 or less, same playbook")
            + swatch("rgba(217,119,6,.22)", "0.15-0.30 partial")
            + swatch("rgba(5,150,105,.18)", "0.30+ genuinely different")
            + swatch("var(--panel-2)", "ledger too thin"),
        )
        + "</div>"
    )


def _pair_table(pairs: Sequence[Dict[str, Any]]) -> str:
    if not pairs:
        return ""
    rows = []
    for pair in pairs:
        style = pair.get("style") or {}
        significant = pair.get("is_significant")
        conflict = bool(style.get("style_vs_pnl_conflict"))
        rows.append(
            "<tr>"
            f"<td>{_name(pair.get('label_a'), 34)} &times; "
            f"{_name(pair.get('label_b'), 34)}</td>"
            f"<td>{_num(pair.get('pearson'), 3, sign=True)}</td>"
            f"<td>{_num(pair.get('spearman'), 3, sign=True)}</td>"
            f"<td>{_esc(pair.get('observations'))}</td>"
            f"<td>{_num(pair.get('p_value'), 4)}"
            + ("" if significant else ' <span class="pf-na">(not significant)</span>')
            + "</td>"
            f"<td>{_num(style.get('exit_distance'), 3)}</td>"
            f"<td>{_esc(style.get('exit_style_a') or '&mdash;')} / "
            f"{_esc(style.get('exit_style_b') or '&mdash;')}</td>"
            + (
                '<td style="color:var(--down);font-weight:700">CONFLICT</td>'
                if conflict
                else "<td>&mdash;</td>"
            )
            + "</tr>"
        )
    return (
        '<div><h4 class="pf-h4">Pair by pair</h4>'
        '<div class="table-scroll">'
        '<table class="data-table"><thead><tr>'
        "<th>Pair</th><th>Pearson</th><th>Spearman</th><th>Buckets</th>"
        "<th>p-value</th><th>Style distance</th><th>Exit styles</th><th>Flag</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div></div>'
    )


def _member_table(members: Sequence[Dict[str, Any]]) -> str:
    if not members:
        return ""
    rows = []
    for member in members:
        excluded = member.get("excluded_reason")
        weight = member.get("capital_weight")
        rows.append(
            "<tr"
            + (' style="opacity:.6"' if excluded else "")
            + ">"
            f"<td>{_name(member.get('label'))}</td>"
            f"<td>{_esc(member.get('unique_code'))}</td>"
            f"<td>{_esc(member.get('symbol'))}</td>"
            f"<td>{_esc(member.get('closed_trade_count'))}</td>"
            f"<td>{_num(member.get('realized_pnl'), 0)}</td>"
            f"<td>{_num(member.get('capital_at_risk'), 0)}</td>"
            f"<td>{'&mdash;' if weight is None else _num(weight * 100.0, 1, '%')}</td>"
            f"<td>{_esc(member.get('position_side'))}</td>"
            + (
                f'<td class="pf-na">{_esc(excluded)}</td>'
                if excluded
                else "<td>in the measurement</td>"
            )
            + "</tr>"
        )
    return (
        '<div><h4 class="pf-h4">Members of this book</h4>'
        '<div class="pf-sub">Every bot submitted is listed, including any that '
        "could not enter the correlation measurement &mdash; a member vanishing "
        "from its own portfolio report would be worse than one shown with the "
        "reason it was left out.</div>"
        '<div class="table-scroll">'
        '<table class="data-table"><thead><tr>'
        "<th>Bot</th><th>Code</th><th>Symbol</th><th>Closed trades</th>"
        "<th>Realised PnL</th><th>Capital</th><th>Weight</th><th>Side</th>"
        f'<th>Status</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
        "</div></div>"
    )


def _concentration(block: Dict[str, Any]) -> str:
    by_symbol = block.get("by_symbol") or {}
    if not by_symbol:
        return ""
    bars = []
    for symbol, share in list(by_symbol.items())[:10]:
        pct = float(share) * 100.0
        bars.append(
            '<div style="margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;font-size:12px">'
            f"<span>{_esc(symbol)}</span><span>{_num(pct, 1, '%')}</span></div>"
            f'<div class="pf-bar"><i style="width:{min(100.0, pct):.1f}%"></i></div>'
            "</div>"
        )
    directional = block.get("directional_alignment")
    return (
        "<div><h4>Where the open book actually sits</h4>"
        '<div class="pf-sub">Spread across bots is not spread across risk. This '
        "reads the open positions of every member at once.</div>"
        + "".join(bars)
        + '<div class="pf-grid" style="margin-top:12px">'
        + _stat(
            "Largest single symbol",
            _num(block.get("largest_symbol_share_pct"), 1, "%"),
            _esc(block.get("largest_symbol") or ""),
        )
        + _stat(
            "Concentration (normalised HHI)",
            _num(block.get("normalised_hhi"), 3),
            "0 = even across symbols held, 1 = all in one",
        )
        + _stat(
            "Same-direction share",
            _num(None if directional is None else directional * 100.0, 0, "%"),
            "100% means one directional bet however many bots placed it",
        )
        + _stat("Gross notional", _num(block.get("gross_notional"), 0))
        + "</div></div>"
    )


def _notes(portfolio: Dict[str, Any]) -> str:
    out = []
    for title, key, tone in (
        ("What the measurement found", "evidence", "notice-neutral"),
        ("Caveats", "warnings", "notice-warning"),
        ("Limitations", "limitations", "notice-neutral"),
    ):
        items = portfolio.get(key) or []
        if not items:
            continue
        rows = "".join(f"<li>{_esc(item)}</li>" for item in items)
        out.append(
            f'<div class="notice {tone}"><strong>{_esc(title)}</strong>'
            f'<ul style="margin:8px 0 0 18px;line-height:1.6">{rows}</ul></div>'
        )
    return "".join(out)


# --------------------------------------------------------------------------- #


def render_portfolio_section(portfolio: Dict[str, Any]) -> str:
    """The diversification block, as HTML using the report page's own classes."""
    if not portfolio:
        return ""
    correlation = portfolio.get("correlation") or {}
    pairs = correlation.get("pairs") or []
    joint = portfolio.get("joint_simulation") or {}
    alignment = correlation.get("alignment") or {}

    conflict = ""
    if portfolio.get("style_vs_pnl_conflict"):
        conflict = (
            '<div class="pf-conflict"><strong>Results and behaviour disagree.</strong> '
            + _esc(portfolio.get("style_verdict_reason") or "")
            + "</div>"
        )

    ratio = joint.get("diversification_ratio")
    stats = (
        '<div class="pf-grid kp-stat-row">'
        + _stat(
            "Average pairwise correlation",
            _num(correlation.get("average_pearson"), 2, sign=True),
            f"over {_esc(alignment.get('evaluated_buckets'))} shared "
            f"{_esc(alignment.get('bucket_label'))} buckets",
        )
        + _stat(
            "Strongest pair",
            _num(correlation.get("max_pearson"), 2, sign=True),
            _esc(" x ".join(correlation.get("max_pearson_pair") or [])),
        )
        + _stat(
            "Joint 95% VaR",
            _num(joint.get("var_95_pct"), 1, "%"),
            "of the combined capital",
        )
        + _stat(
            "Undiversified benchmark",
            _num(joint.get("sum_individual_var_95_pct"), 1, "%"),
            "what the same bots risk if they are one bet",
        )
        + _stat(
            "Loss tail removed",
            _num(None if ratio is None else ratio * 100.0, 0, "%"),
            "the gap between the two figures above",
        )
        + _stat(
            "Shared history",
            _num(alignment.get("overlap_days"), 1, " days"),
            "window in which every member was trading",
        )
        + "</div>"
    )

    return (
        _CSS
        + '<section class="card" id="portfolio-correlation">'
        '<h3>Diversification &amp; correlation</h3>'
        '<div class="card-hint">The one question a single-bot report cannot be '
        "asked: do these bots actually spread the risk, or only the position? "
        "Answered twice &mdash; on results, and on behaviour &mdash; because the "
        "two routinely disagree.</div>"
        '<div class="pf-wrap">'
        '<div class="pf-verdicts">'
        + _badge(
            _VERDICT_TONE,
            str(portfolio.get("verdict") or ""),
            "Results",
            str(portfolio.get("verdict_reason") or ""),
        )
        + _badge(
            _STYLE_TONE,
            str(portfolio.get("style_verdict") or ""),
            "Behaviour",
            "" if portfolio.get("style_vs_pnl_conflict") else
            str(portfolio.get("style_verdict_reason") or ""),
        )
        + "</div>"
        + conflict
        + stats
        + _matrices(correlation, pairs)
        + _pair_table(pairs)
        + _concentration(portfolio.get("concentration") or {})
        + _member_table(portfolio.get("members") or [])
        + _notes(portfolio)
        + (
            '<div class="notice notice-neutral"><strong>What to do</strong><br>'
            + _esc(portfolio.get("recommended_action") or "")
            + "</div>"
            if portfolio.get("recommended_action")
            else ""
        )
        + "</div></section>"
    )


def inject_portfolio_section(document: str, portfolio: Dict[str, Any]) -> str:
    """Put the block at the top of the Analyst Result tab of a finished page.

    Falls back to appending before `</main>`, then `</body>`, if the anchor is
    not found. The anchor lives in a module under active rework, and a missing
    anchor must degrade to "the block is lower down the page" rather than to
    "the portfolio's headline finding silently disappeared".
    """
    section = render_portfolio_section(portfolio)
    if not section:
        return document
    if _PANEL_ANCHOR in document:
        return document.replace(_PANEL_ANCHOR, _PANEL_ANCHOR + section, 1)
    for fallback in ("</main>", "</body>"):
        if fallback in document:
            return document.replace(fallback, section + fallback, 1)
    return document + section
