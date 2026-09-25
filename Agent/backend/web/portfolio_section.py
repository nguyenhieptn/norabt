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
import re
from typing import Any, Dict, List, Optional, Sequence

from Agent.backend.report.qc.portfolio.correlation import CorrelationAnalyzer
from Agent.backend.report.qc.portfolio.service import PortfolioQCService
from Agent.backend.web.portfolio_formulas import PF_FORMULAS

# The page's colour bands ARE the engine's bands. A pair the engine labels
# HIGH ("effectively one position") must not sit in an amber "watch" cell:
# the matrix used 0.7/0.4 from the mockup while the engine and the verdict
# use 0.6/0.3, so an r of 0.62 read as two different findings (2026-09-25).
_R_HIGH = CorrelationAnalyzer.MODERATE_THRESHOLD      # >= : HIGH
_R_MODERATE = CorrelationAnalyzer.LOW_THRESHOLD       # >= : MODERATE
_R_INVERSE = CorrelationAnalyzer.INVERSE_THRESHOLD    # <= : offsetting
_R_FAINT = 0.1                                        # >= : low but visible
_D_SAME = PortfolioQCService.SAME_PLAYBOOK_DISTANCE   # <= : same playbook
_D_DISTINCT = PortfolioQCService.PARTIAL_OVERLAP_DISTANCE  # >= : distinct
_TRAP_R = PortfolioQCService.CONFLICT_PEARSON_MAX

# Anchor inside the finished document. One anchor, not two, is why the block
# is a section on an existing tab rather than a fourth tab: adding a tab means
# matching the tab BAR markup as well, and that is the part currently being
# reworked.
_PANEL_ANCHOR = '<div class="tab-panel panel-report" id="panel-report" role="tabpanel">'
# The Overview's own container (report_page `_render_report_modes`).
_OVERVIEW_ANCHOR = '<div class="rm-overview">'

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
/* Colours come from the page's own tokens, never hard-coded: the report has a
   light and a dark palette, and a literal colour is right in only one of them.
   Tints are `color-mix` over a token so they layer over either background.
   Member identity hues are the one fixed palette -- they name a bot, not a
   state -- and live in custom properties so no rule carries a literal.

   The four views switch with radio inputs, not script: this block is also
   injected into the SPA, and markup set through innerHTML must work without
   running anything. */
.pf-wrap{--pf-c1:#f7931a;--pf-c2:#627eea;--pf-c3:#9945ff;--pf-c4:#0d9488;
 --pf-c5:#d97706;--pf-c6:#db2777;--pf-c7:#65a30d;--pf-c8:#64748b;
 --pf-amber-ink:var(--amber);
 --pf-down-ink:color-mix(in srgb,var(--down) 82%,var(--ink));
 --pf-tint-bad:color-mix(in srgb,var(--down) 18%,transparent);
 --pf-tint-warn:color-mix(in srgb,var(--amber) 20%,transparent);
 --pf-tint-low:color-mix(in srgb,var(--info) 16%,transparent);
 --pf-tint-ok:color-mix(in srgb,var(--up) 16%,transparent);
 display:flex;flex-direction:column;gap:14px;min-width:0;padding:4px 2px}
#portfolio-correlation{padding:20px 24px}
.pf-mtm{font-size:8.5px;font-weight:700;letter-spacing:.04em;color:var(--ink-3);margin-left:3px;vertical-align:super}
.report-members{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.pf-mchip{display:inline-flex;align-items:center;gap:6px;max-width:220px;padding:3px 10px;border-radius:999px;font-family:var(--sans) !important;
 background:var(--panel-2);border:1px solid var(--line);font-size:12px;font-weight:600;color:var(--ink) !important;
 text-decoration:none !important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pf-mchip i{width:7px;height:7px;border-radius:50%;flex:none}
a.pf-mchip:hover{border-color:var(--ink-3)}
.pf-mchip-pub{border-color:color-mix(in srgb,var(--down) 45%,var(--line))}
.pf-mchip-off{color:var(--down) !important;background:color-mix(in srgb,var(--down) 10%,transparent);border-color:transparent}
.pf-mchip-off i{background:var(--down)}
.report-subline{margin-top:6px;font-size:12.5px;color:var(--ink-3)}
@supports not (background:color-mix(in srgb,red 10%,transparent)){
 .pf-wrap{--pf-tint-bad:var(--panel-2);--pf-tint-warn:var(--panel-2);
  --pf-tint-low:var(--panel-2);--pf-tint-ok:var(--panel-2)}
}
.pf-wrap>*{min-width:0;max-width:100%}
.pf-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.pf-title{margin:0;font-size:15px;font-weight:700;color:var(--ink)}
.pf-chips{display:flex;flex-wrap:wrap;gap:6px}
.pf-chip{position:relative;display:inline-flex;align-items:center;padding:3px 10px;
 border-radius:999px;font-size:11.5px;font-weight:600;cursor:default;white-space:nowrap}
.pf-chip-bad{background:var(--pf-tint-bad);color:var(--pf-down-ink)}
.pf-chip-warn{background:var(--pf-tint-warn);color:var(--pf-amber-ink)}
.pf-chip-mute{background:var(--panel-2);color:var(--ink-2)}
.pf-chip-ok{background:var(--pf-tint-ok);color:var(--up)}
.pf-pop{visibility:hidden;opacity:0;position:absolute;right:0;top:calc(100% + 6px);
 width:280px;padding:8px 10px;border-radius:8px;background:var(--ink);color:var(--panel);
 font-size:11.5px;font-weight:400;line-height:1.45;white-space:normal;z-index:30;
 transition:opacity .12s ease}
.pf-chip:hover .pf-pop,.pf-chip:focus .pf-pop{visibility:visible;opacity:1}
.pf-pop-i{display:block;margin-bottom:4px}
.pf-verdicts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.pf-v{display:flex;align-items:baseline;gap:10px;padding:12px 16px;border-radius:12px;min-width:0}
.pf-v-k{font-size:10.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;opacity:.8}
.pf-v b{font-size:16px}
.pf-v-n{margin-left:auto;font-family:var(--mono);font-size:12.5px;font-weight:600;white-space:nowrap}
.pf-v-ok{background:var(--pf-tint-ok);color:var(--up)}
.pf-v-warn{background:var(--pf-tint-warn);color:var(--pf-amber-ink)}
.pf-v-bad{background:var(--pf-tint-bad);color:var(--pf-down-ink)}
.pf-i{display:inline-flex;align-items:center;justify-content:center;width:13px;height:13px;
 margin-left:6px;border-radius:50%;border:1px solid var(--ink-3);color:var(--ink-3);
 font-size:8.5px;font-style:normal;font-weight:600;font-family:var(--mono);vertical-align:1px;
 text-transform:none;letter-spacing:0}
.pf-v-mute{background:var(--panel-2);color:var(--ink-2)}
.pf-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}
.pf-kpi{background:var(--panel-2);border-radius:12px;padding:11px 13px;min-width:0}
.pf-kpi-l{font-size:11px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pf-kpi-v{margin-top:3px;font-family:var(--mono);font-size:18px;font-weight:700;color:var(--ink);white-space:nowrap}
.pf-tabradio{position:absolute;opacity:0;pointer-events:none;width:1px;height:1px}
.pf-tabbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;padding:4px;
 border-radius:12px;background:var(--panel-2)}
.pf-tabbar label{display:flex;flex-direction:column;gap:1px;padding:8px 12px;border-radius:9px;
 cursor:pointer;min-width:0;transition:background .15s ease}
.pf-tabbar label:hover{background:color-mix(in srgb,var(--panel) 60%,transparent)}
.pf-tab-l{font-size:12.5px;font-weight:600;color:var(--ink-2)}
.pf-tab-v{font-family:var(--mono);font-size:11px;color:var(--ink-3);white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis}
.pf-pane{display:none;min-width:0;margin-top:14px}
#pf-tab-corr:checked~.pf-tabbar label[for="pf-tab-corr"],
#pf-tab-risk:checked~.pf-tabbar label[for="pf-tab-risk"],
#pf-tab-book:checked~.pf-tabbar label[for="pf-tab-book"],
#pf-tab-mem:checked~.pf-tabbar label[for="pf-tab-mem"]{background:var(--panel);
 box-shadow:0 1px 3px color-mix(in srgb,var(--ink) 10%,transparent)}
#pf-tab-corr:checked~.pf-tabbar label[for="pf-tab-corr"] .pf-tab-l,
#pf-tab-risk:checked~.pf-tabbar label[for="pf-tab-risk"] .pf-tab-l,
#pf-tab-book:checked~.pf-tabbar label[for="pf-tab-book"] .pf-tab-l,
#pf-tab-mem:checked~.pf-tabbar label[for="pf-tab-mem"] .pf-tab-l{color:var(--ink)}
#pf-tab-corr:checked~.pf-pane-corr,#pf-tab-risk:checked~.pf-pane-risk,
#pf-tab-book:checked~.pf-pane-book,#pf-tab-mem:checked~.pf-pane-mem{display:block}
.pf-tabradio:focus-visible~.pf-tabbar{outline:2px solid var(--info);outline-offset:2px}
.pf-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));
 gap:14px;align-items:stretch}
.pf-cols>*{min-width:0}
.pf-box{border:1px solid var(--line);border-radius:14px;padding:16px 18px;display:flex;
 flex-direction:column;min-width:0}
.pf-box-h{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px}
.pf-lbl{font-size:10.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3)}
.pf-tag{display:inline-flex;align-items:center;padding:2px 9px;border-radius:999px;
 font-size:10.5px;font-weight:600;white-space:nowrap}
.pf-tag-bad{background:var(--pf-tint-bad);color:var(--pf-down-ink)}
.pf-tag-warn{background:var(--pf-tint-warn);color:var(--pf-amber-ink)}
.pf-tag-ok{background:var(--pf-tint-ok);color:var(--up)}
.pf-tag-mute{background:var(--panel-2);color:var(--ink-3)}
.pf-scroll{overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch}
.pf-matrix{border-collapse:separate;border-spacing:4px;font-size:12px;width:100%;
 min-width:max-content;table-layout:fixed}
/* Matrix and statistics side by side, balanced -- the mockup's own split
   (portfolio-report-redesign.html: `minmax(0,1fr) minmax(0,1.08fr)`), with
   the table filling its card rather than capped inside it. A narrower
   "hug the table" card was tried and rejected by the project owner
   (2026-09-24: "2 nội dung view cân bằng nhau"). Stacked below 900px. */
.pf-pane-corr .pf-cols{grid-template-columns:minmax(0,1fr) minmax(0,1.08fr)}
.pf-matrix thead th:first-child{width:22%}
@media (max-width:900px){.pf-pane-corr .pf-cols{grid-template-columns:minmax(0,1fr)}}
.pf-matrix th{font-weight:600;color:var(--ink-2);padding:2px 4px;white-space:nowrap;
 background:transparent;border:none;text-transform:none;letter-spacing:0;font-family:inherit;font-size:12px;
 max-width:110px;overflow:hidden;text-overflow:ellipsis;text-align:center}
.pf-matrix th.pf-row-head{text-align:left;position:sticky;left:0;background:var(--panel);z-index:1}
.pf-matrix td{text-align:center;padding:11px 4px;border-radius:8px;font-family:var(--mono);
 font-weight:700;white-space:nowrap;color:var(--ink);min-width:60px}
.pf-matrix td.pf-lo{font-style:italic}
/* The SPA wraps the report in its own table styling (uppercase mono headers,
   striped rows, cell borders). This matrix is not a data table: pin its
   look so it reads the same on the standalone page and inside the app. */
#portfolio-correlation .pf-matrix th,#portfolio-correlation .pf-matrix tr,
#portfolio-correlation .pf-matrix thead,#portfolio-correlation .pf-matrix tbody{
 background:transparent !important;text-transform:none !important;letter-spacing:0 !important;
 font-family:inherit !important;border:none !important;box-shadow:none !important}
#portfolio-correlation .pf-matrix th.pf-row-head{background:var(--panel) !important}
#portfolio-correlation .pf-matrix th{padding:2px 4px !important;font-size:12px !important;
 font-weight:600 !important;color:var(--ink-2) !important;text-align:center !important}
#portfolio-correlation .pf-matrix th.pf-row-head{text-align:left !important}
#portfolio-correlation .pf-matrix td{border:none !important;padding:11px 4px !important;
 text-align:center !important;font-size:12px !important;font-family:var(--mono) !important}
.pf-matrix td.pf-diag{background:var(--panel-2);font-weight:400}
.pf-matrix td.pf-trapcell{outline:2px dashed var(--down);outline-offset:-2px}
.pf-na{color:var(--ink-3);font-weight:400}
.pf-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:0;flex-shrink:0}
.pf-key{font-family:var(--mono);font-size:11px;color:var(--ink-3);white-space:nowrap}
.pf-legend{margin-top:auto;padding-top:10px;display:flex;flex-wrap:wrap;gap:6px 12px;font-size:11px;color:var(--ink-2)}
.pf-legend span{display:inline-flex;align-items:center;gap:5px}
.pf-swatch{width:10px;height:10px;border-radius:3px;display:inline-block;flex:0 0 auto}
.pf-rows{display:flex;flex-direction:column;flex:1}
.pf-row{display:grid;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--line);
 font-size:12.5px;color:var(--ink);min-width:0}
.pf-row:last-child{border-bottom:none}
.pf-row[hidden]{display:none !important}
.pf-pages{flex:1;display:flex;flex-direction:column}
.pf-pages .lg-foot{margin-top:auto;padding-top:10px}
.pf-row-h{font-size:10.5px;font-weight:600;color:var(--ink-3);text-transform:uppercase;
 letter-spacing:.04em;padding-top:0}
.pf-num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.pf-pairs .pf-row{grid-template-columns:minmax(0,1fr) 46px 30px 46px 38px 48px;flex:1}
.pf-pairs .pf-row-h{flex:0 0 auto}
.pf-riskshare .pf-row{grid-template-columns:minmax(0,1.2fr) minmax(0,1fr) minmax(0,1fr) 70px 84px}
.pf-pairs .pf-row-h span:not(:first-child){text-align:right;text-transform:none;font-size:11px}
.pf-pn{display:flex;align-items:center;min-width:0;font-weight:600;white-space:nowrap;overflow:hidden}
.pf-pn .pf-name{max-width:44%}
.pf-mini{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;color:var(--ink)}
.pf-mini em{font-style:normal;color:var(--ink-3);margin-right:5px;font-size:11px}
.pf-mini b{font-family:var(--mono)}
.pf-svg{display:block;width:100%;max-width:100%;overflow:visible}
.pf-svg-lab{font-size:12px;fill:var(--ink);font-weight:600}
.pf-svg-sub{font-size:10.5px;fill:var(--ink-3)}
.pf-svg-val{font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;font-family:var(--mono)}
.pf-svg-na{font-size:11px;fill:var(--ink-3)}
.pf-var{display:flex;flex-direction:column;gap:12px;padding-top:4px}
.pf-var-row{display:grid;grid-template-columns:minmax(0,190px) minmax(0,1fr) 64px;align-items:center;gap:12px}
.pf-var-l{display:flex;flex-direction:column;min-width:0;font-size:12px;font-weight:600;color:var(--ink)}
.pf-var-l em{font-style:normal;font-weight:400;font-size:10.5px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pf-var-row>b{font-family:var(--mono);font-size:12px;text-align:right;font-variant-numeric:tabular-nums}
.pf-book .pf-row{grid-template-columns:62px minmax(0,1.3fr) 70px 54px 44px 76px 1px 64px 58px 72px 84px}
.pf-book-nb .pf-row{grid-template-columns:62px minmax(0,1.6fr) 1px 70px 64px 80px 96px}
.pf-div{width:1px;align-self:stretch;background:var(--line)}
.pf-row-g{padding:0;border:none}
.pf-grp{font-size:10.5px;font-weight:700;letter-spacing:.07em;color:var(--info)}
.pf-share{display:flex;align-items:center;gap:8px;min-width:0}
.pf-track{flex:1;height:6px;border-radius:3px;background:var(--track);overflow:hidden;min-width:24px}
.pf-track i{display:block;height:100%;border-radius:3px}
.pf-share b{font-family:var(--mono);font-size:12px;min-width:44px;text-align:right}
.pf-more{margin-top:10px;border:1px dashed var(--line);border-radius:10px}
.pf-more>summary{list-style:none;cursor:pointer;padding:9px 12px;display:flex;gap:12px;
 align-items:center;font-size:12.5px;font-weight:600;color:var(--info)}
.pf-more>summary::-webkit-details-marker{display:none}
.pf-more>summary span{font-weight:400;color:var(--ink-3);font-size:11px;font-family:var(--mono);
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pf-more[open]>summary{border-bottom:1px dashed var(--line)}
.pf-more>.pf-rows{padding:0 12px}
.pf-members .pf-row{grid-template-columns:minmax(0,1.4fr) 96px 80px 52px 84px minmax(0,1fr) 52px 104px}
.pf-member-link{color:var(--info);text-decoration:none;font-family:var(--mono)}
.pf-member-link:hover{text-decoration:underline}
.pf-name{display:inline-block;max-width:220px;overflow:hidden;text-overflow:ellipsis;
 white-space:nowrap;vertical-align:bottom}
.pf-off{background:var(--pf-tint-bad);border-radius:8px;padding-left:8px;padding-right:8px}
.pf-note{margin-top:8px;font-size:11.5px;color:var(--ink-3);line-height:1.5}
@media (max-width:900px){
 .pf-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}
 .pf-tabbar{grid-template-columns:repeat(2,minmax(0,1fr))}
 .pf-verdicts{grid-template-columns:1fr}
}
/* Phones: every wide row becomes a small card -- the headline on the first
   line (symbol + exposure, bot + code, pair) and the remaining facts wrap
   underneath, each printed with its own label so no header row is needed. */
@media (max-width:640px){
 #portfolio-correlation{padding:14px 12px}
 .pf-wrap{gap:12px}
 .pf-v{flex-wrap:wrap;padding:10px 12px;gap:4px 8px}
 .pf-v b{font-size:15px}
 .pf-kpis,.pf-book .pf-kpis,.pf-book-nb .pf-kpis{grid-template-columns:repeat(2,minmax(0,1fr)) !important}
 .pf-kpi{padding:10px 12px}
 .pf-kpi-v{font-size:16px}
 .pf-tab-v{font-size:10.5px}
 .pf-box{padding:12px}
 .pf-matrix td{min-width:44px}
 /* Four or more names do not fit across a phone: they clipped to "Shall…",
    "Kelc…". Columns keep only their colour dot -- same order and colour as
    the rows, which carry the full short name in a wider first column. */
 #portfolio-correlation .pf-matrix thead th:not(.pf-row-head){font-size:0 !important}
 .pf-matrix thead th .pf-dot{margin-right:0}
 /* `table-layout:fixed` sizes columns from the FIRST row -- the empty
    corner cell of the header, not the row-name cells below it. */
 .pf-matrix thead th:first-child{width:32%}
 /* "3 measured · 1 concealed" is the one line that explains why the
    matrix has fewer rows than the reader booked; clipping it to
    "1 concea…" hid exactly that. */
 .pf-tab-v{white-space:normal;overflow:visible}
 .pf-row-h,.pf-row-g,.pf-div{display:none !important}
 .pf-pairs .pf-row,.pf-book .pf-row,.pf-book-nb .pf-row,.pf-members .pf-row{
  display:flex !important;flex-wrap:wrap;align-items:center;gap:4px 12px;min-width:0 !important}
 .pf-pairs .pf-pn{flex:1 1 100%}
 /* Capital vs risk: name on its own line, the two shares side by side
    (the header row is hidden on a phone, so each value carries its label). */
 .pf-riskshare .pf-row{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:4px 14px}
 .pf-riskshare .pf-pn{grid-column:1/-1}
 .pf-riskshare .pf-share b{min-width:0}
 .pf-riskshare .pf-row>span:last-child{text-align:right}
 .pf-pairs .pf-row>span:not(.pf-pn){font-size:11.5px}
 .pf-pairs .pf-row>span:nth-child(2)::before{content:"ρ ";color:var(--ink-3)}
 .pf-pairs .pf-row>span:nth-child(3)::before{content:"co ";color:var(--ink-3)}
 .pf-pairs .pf-row>span:nth-child(4)::before{content:"p ";color:var(--ink-3)}
 .pf-pairs .pf-row>span:nth-child(5)::before{content:"ov ";color:var(--ink-3)}
 .pf-pairs .pf-row>span:last-child{margin-left:auto}
 .pf-sym{flex:0 0 52px}
 .pf-book .pf-share,.pf-book-nb .pf-share{flex:1 1 calc(100% - 70px)}
 .pf-members .pf-pn{flex:1 1 55%}
 .pf-members .pf-share{flex:1 1 100%;order:9}
 [data-l]{font-size:11.5px;text-align:left !important}
 [data-l]::before{content:attr(data-l) " ";color:var(--ink-3);font-family:var(--sans);font-size:10.5px}
 .pf-na[style*="grid-column"]{flex:1 1 100%}
 /* The charts are drawn 600 units wide and shrink to the phone: grow their
    text in user units so it lands near 11px, and drop the sub-captions. */
 .pf-svg-lab{font-size:23px}
 .pf-svg-val{font-size:23px}
 .pf-svg-sub{display:none}
 .pf-var-row{grid-template-columns:minmax(0,1fr) 58px;gap:4px 10px}
 .pf-var-row .pf-track{grid-column:1/-1;grid-row:2}
 .pf-svg-na{font-size:21px}
 .pf-pairs .pf-row-h,.pf-book .pf-row-h,.pf-book-nb .pf-row-h,.pf-members .pf-row-h,
 .pf-book .pf-row-g,.pf-book-nb .pf-row-g{display:none !important}
}
</style>
"""

_MEMBER_COLOURS = tuple(f"var(--pf-c{index})" for index in range(1, 9))


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _num(value: Any, digits: int = 2, suffix: str = "", sign: bool = False) -> str:
    """A number, or an em dash. Never a zero standing in for 'not measured'."""
    if value is None or not isinstance(value, (int, float)):
        return "&mdash;"
    fmt = f"{{:+.{digits}f}}" if sign else f"{{:.{digits}f}}"
    return _esc(fmt.format(float(value))) + suffix


def _money(value: Any, sign: bool = False) -> str:
    """Whole units with thousands separators, or an em dash."""
    if not _is_num(value):
        return "&mdash;"
    return _esc(f"{float(value):+,.0f}" if sign else f"{float(value):,.0f}")


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _pearson_tint(value: Optional[float]) -> str:
    """Correlation cell. HIGH is the dangerous end; absence is grey, never green."""
    if not _is_num(value):
        return "background:var(--panel-2);color:var(--ink-3)"
    if value >= _R_HIGH:
        return "background:var(--pf-tint-bad);color:var(--pf-down-ink)"
    if value >= _R_MODERATE:
        return "background:var(--pf-tint-warn);color:var(--pf-amber-ink)"
    if value >= _R_FAINT:
        return "background:var(--pf-tint-ok);color:var(--up)"
    if value <= _R_INVERSE:
        return "background:var(--pf-tint-ok);color:var(--up)"
    return "background:var(--panel-2);color:var(--ink-2)"


def _distance_tint(value: Optional[float]) -> str:
    """Behaviour-distance cell. LOW distance is the dangerous end -- the
    opposite of the correlation scale, hence its own function and legend."""
    if not _is_num(value):
        return "background:var(--panel-2);color:var(--ink-3)"
    if value <= _D_SAME:
        return "background:var(--pf-tint-bad);color:var(--pf-down-ink)"
    if value < _D_DISTINCT:
        return "background:var(--pf-tint-warn);color:var(--pf-amber-ink)"
    return "background:var(--pf-tint-ok);color:var(--up)"


def _ink(style: str) -> str:
    """The text-colour half of a tint. The SPA forces `td{color:... !important}`
    on report tables, so the colour is carried by an inner span, which
    inherits nothing from that rule."""
    return ";".join(part for part in style.split(";") if part.strip().startswith("color"))


def _pair_colour(value: Any) -> str:
    """One pair's r, on the same bands as its matrix cell."""
    if not _is_num(value):
        return "var(--ink-3)"
    if value >= _R_HIGH:
        return "var(--pf-down-ink)"
    if value >= _R_MODERATE:
        return "var(--pf-amber-ink)"
    return "var(--ink)"


def _pearson_colour(value: Any) -> str:
    if not _is_num(value):
        return "var(--ink-3)"
    if value >= _R_HIGH:
        return "var(--down)"
    if value >= _R_MODERATE:
        return "var(--pf-amber-ink)"
    return "var(--up)"


def _name(value: Any, limit: int = 80) -> str:
    """A bot nickname, clipped in CSS and carried in full in `title`.

    OKX nicknames are free text: they can be long, can be a single unbroken
    run of characters with nowhere to wrap, and can be emoji. Left alone they
    stretch a cell past the page, and `.main` sets `overflow-x:hidden` so the
    overflow is CLIPPED rather than scrollable. The hard cap is a second line
    of defence for the pathological case.
    """
    text = "" if value is None else str(value)
    clipped = text if len(text) <= limit else text[: limit - 1] + "…"
    return f'<span class="pf-name" title="{_esc(text)}">{_esc(clipped)}</span>'


# A bot with no nickname is labelled by its OKX uniqueCode: 16 hex digits or
# an 18-digit number. Neither has a "first word", and clipping one to 13
# characters kept exactly the part two codes are least likely to differ in
# while hiding the rest.
_BARE_CODE = re.compile(r"^(?:[0-9A-Fa-f]{12,}|\d{12,})$")
# What OKX nicknames actually use between words. The mockup's sample names
# ("Aquila Grid") are space-separated; real ones are "Elegant-Layer-Violet",
# "Alvin_Cryptodancers", "IS.K".
_WORD_BREAK = re.compile(r"[\s\-_.|/\u00b7]+")


def _short_labels(labels: Sequence[str]) -> Dict[str, str]:
    """A compact name per bot for the matrix axes and pair rows.

    The first word when it is unique across the portfolio ("Delta Mean Rev"
    -> "Delta", "Elegant-Layer-Violet" -> "Elegant"), the first six
    characters of a bare OKX code, otherwise the full name; clipped to 12
    characters either way. The full name always stays in `title`.

    Splitting on whitespace alone -- the previous rule -- matched the
    mockup's sample data and none of the real data: every hyphenated or
    underscored nickname came through whole and was then clipped mid-word
    ("Elegant-Layer\u2026", "E9BB0FE3B8797\u2026"), which is what made a real 3-bot
    matrix read nothing like the design (2026-09-24).
    """
    def first_token(label: Any) -> str:
        text = str(label).strip()
        if _BARE_CODE.match(text):
            return text[:6]
        words = [word for word in _WORD_BREAK.split(text) if word]
        # A one- or two-letter first word ("IS.K", "A-Team") identifies
        # nothing on its own; the whole name, clipped, does.
        if not words or len(words[0]) < 3:
            return text
        return words[0]

    firsts = [first_token(label) for label in labels]
    out: Dict[str, str] = {}
    for label, first in zip(labels, firsts):
        text = first if firsts.count(first) == 1 else str(label)
        out[str(label)] = text if len(text) <= 12 else text[:11] + "\u2026"
    return out


def _dot(index: int) -> str:
    colour = _MEMBER_COLOURS[index % len(_MEMBER_COLOURS)]
    return f'<i class="pf-dot" style="background:{colour}"></i>'


def _style_distance(pair: Dict[str, Any]) -> Optional[float]:
    value = (pair.get("style") or {}).get("exit_distance")
    return float(value) if _is_num(value) else None


def _exposure_overlap(pair: Dict[str, Any]) -> Optional[float]:
    # The correlation layer writes it on the pair; an older shape kept it
    # under `style`. Read both so neither record shows a false em dash.
    value = pair.get("exposure_overlap")
    if not _is_num(value):
        value = (pair.get("style") or {}).get("exposure_overlap")
    return float(value) if _is_num(value) else None


def _is_trap(pair: Dict[str, Any]) -> bool:
    return bool((pair.get("style") or {}).get("style_vs_pnl_conflict"))


def _pair_flag(pair: Dict[str, Any]) -> str:
    """Same precedence as before: TRAP, then SAME playbook, then n/s."""
    distance = _style_distance(pair)
    if _is_trap(pair):
        return (
            '<span class="pf-tag pf-tag-bad" title="Results look independent (r &le; '
            f'{_TRAP_R:.2f}) but the exit behaviour is the same (d &le; {_D_SAME:.2f}): '
            'the offset belongs to this window, not to the strategies">Trap</span>'
        )
    if distance is not None and distance <= _D_SAME:
        return (
            f'<span class="pf-tag pf-tag-warn" title="Exit-rule distance d &le; {_D_SAME:.2f}: '
            'same playbook">Same</span>'
        )
    if not pair.get("is_significant"):
        return (
            '<span class="pf-tag pf-tag-mute" title="p &ge; 0.05: r is not distinguishable '
            'from zero at this sample size; left out of the verdict">n/s</span>'
        )
    return '<span class="pf-na">&mdash;</span>'


_NOTE_OWNER = re.compile(r"^\[([^\]]+)\]\s*(.*)$", re.S)
_NOTE_DIGITS = re.compile(r"\d[\d,.]*")


def _grouped_notes(raw: Sequence[Any]) -> List[str]:
    """Member notes arrive one log line each ("[Algo Box] Rejected trade
    3854...: missing/invalid time or PnL" six times). Collapse lines that
    differ only in their numbers into one with a count, keep the member name
    once per line, and put portfolio-level notes (no "[member]" prefix)
    first -- so the chip counts findings, not log lines."""
    order: List[str] = []
    seen: Dict[str, List[Any]] = {}
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        match = _NOTE_OWNER.match(text)
        owner, body = (match.group(1), match.group(2)) if match else ("", text)
        key = owner + "\x00" + _NOTE_DIGITS.sub("#", body)
        if key not in seen:
            seen[key] = [owner, body, 0]
            order.append(key)
        seen[key][2] += 1
    order.sort(key=lambda k: seen[k][0] != "")
    out = []
    for key in order:
        owner, body, count = seen[key]
        line = f"{owner} · {body}" if owner else body
        out.append(line + (f" (×{count})" if count > 1 else ""))
    return out


def _pop(items: Sequence[str]) -> str:
    return '<span class="pf-pop">' + "".join(
        f'<span class="pf-pop-i">{_esc(item)}</span>' for item in items
    ) + "</span>"


# --------------------------------------------------------------------------- #
# Correlation view
# --------------------------------------------------------------------------- #


def _pair_matrix(
    correlation: Dict[str, Any],
    pairs: Sequence[Dict[str, Any]],
    hidden_labels: Sequence[str] = (),
) -> str:
    """ONE matrix, two measurements: results (r) above the diagonal, behaviour
    (exit-rule distance d) below it. Same pair, same coordinates -- a cell
    calm above and red below is the trap this section exists to show, and a
    trap pair is ringed in both halves."""
    labels: List[str] = list(correlation.get("labels") or [])
    if len(labels) < 2:
        return ""
    pearson = correlation.get("pearson") or []
    index = {label: position for position, label in enumerate(labels)}
    distance: Dict[tuple, Optional[float]] = {}
    trap: Dict[tuple, bool] = {}
    by_key: Dict[tuple, Dict[str, Any]] = {}
    for pair in pairs:
        left, right = index.get(pair.get("label_a")), index.get(pair.get("label_b"))
        if left is None or right is None:
            continue
        key = (min(left, right), max(left, right))
        distance[key] = _style_distance(pair)
        trap[key] = _is_trap(pair)
        by_key[key] = pair

    hidden = set(hidden_labels)
    short = _short_labels(labels)
    head = "".join(
        f'<th title="{_esc(label)}">{_dot(position)}{_esc(short.get(str(label), label))}</th>'
        for position, label in enumerate(labels)
    )
    rows = []
    for row, label in enumerate(labels):
        cells = []
        for column in range(len(labels)):
            if row == column:
                cells.append(f'<td class="pf-diag">{_dot(row)}</td>')
                continue
            key = (min(row, column), max(row, column))
            ring = " pf-trapcell" if trap.get(key) else ""
            pair_title = _esc(f"{labels[row]} x {labels[column]}")
            if column > row:
                raw = None
                if row < len(pearson) and column < len(pearson[row]):
                    raw = pearson[row][column]
                text = '<span class="pf-na">n/a</span>' if not _is_num(raw) else _esc(f"{float(raw):+.2f}")
                tint = _pearson_tint(raw)
                stats = by_key.get(key) or {}
                p_value = stats.get("p_value")
                sig = (
                    f" &middot; p {float(p_value):.3f}"
                    + ("" if stats.get("is_significant") else ", not significant: left out of the verdict")
                    if _is_num(p_value) else ""
                )
                cells.append(
                    f'<td class="pf-up{ring}" style="{tint}" '
                    f'title="{pair_title} &middot; results r{sig}"><span style="{_ink(tint)}">{text}</span></td>'
                )
            else:
                value = distance.get(key)
                text = '<span class="pf-na">n/a</span>' if value is None else _esc(f"{value:.2f}")
                tint = _distance_tint(value)
                why = (
                    " &middot; n/a: order book hidden on OKX, no exits to compare"
                    if value is None and (labels[row] in hidden or labels[column] in hidden)
                    else ""
                )
                cells.append(
                    f'<td class="pf-lo{ring}" style="{tint}" '
                    f'title="{pair_title} &middot; exit distance d{why}"><span style="{_ink(tint)}">{text}</span></td>'
                )
        rows.append(
            f'<tr><th class="pf-row-head" title="{_esc(label)}">{_dot(row)}'
            f'{_esc(short.get(str(label), label))}</th>{"".join(cells)}</tr>'
        )

    def swatch(style: str, text: str) -> str:
        return f'<span><i class="pf-swatch" style="{style}"></i>{text}</span>'

    return (
        '<div class="pf-box">'
        '<div class="pf-box-h"><span class="pf-lbl" title="Upper right: results correlation r '
        f'(high = danger: &ge; {_R_HIGH:.2f} high, {_R_MODERATE:.2f}-{_R_HIGH:.2f} moderate). '
        f'Lower left: exit-rule distance d (low = danger: &le; {_D_SAME:.2f} same playbook, '
        f'&lt; {_D_DISTINCT:.2f} partly overlapping; 0 = identical).">'
        'Pair matrix<i class="pf-i">i</i></span><span class="pf-key">&#9701; ' + _fl("r", "pf_pair_r") + ' &nbsp; &#9699; ' + _fl("d", "pf_pair_d") + '</span></div>'
        '<div class="pf-scroll">'
        # Fills its card; the two cards of the pane are balanced by
        # `.pf-pane-corr .pf-cols`, as in the design (2026-09-24).
        '<table class="pf-matrix">'
        f'<thead><tr><th></th>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        "</div>"
        '<div class="pf-legend">'
        + swatch("background:var(--pf-tint-bad)", f"r &ge; {_R_HIGH:.1f} &middot; d &le; {_D_SAME:.2f}")
        + swatch("background:var(--pf-tint-warn)", f"r &ge; {_R_MODERATE:.1f} &middot; d &lt; {_D_DISTINCT:.1f}")
        + swatch("background:var(--pf-tint-ok)", f"r &lt; {_R_MODERATE:.1f} &middot; d &ge; {_D_DISTINCT:.1f}")
        + swatch("background:var(--panel-2)", "near 0 / n/a")
        + "</div></div>"
    )


def _paged_pairs(rows: Sequence[str], per: int) -> str:
    """Pair rows, `per` at a time, with the report's pager under them (the
    same `.lg-box` runtime the ledger and robustness cards use). A list that
    fits on one page is shown whole, with no pager."""
    if len(rows) <= per:
        return f'<div class="pf-rows">{"".join(rows)}</div>'
    from Agent.backend.web.report_page import _lg_pager_html  # avoid an import cycle

    pages = (len(rows) + per - 1) // per
    return (
        f'<div class="lg-box pf-pages" data-unit="pairs" data-per="{per}" data-f="a" data-b="all" data-p="0">'
        f'<div class="pf-rows lg-body">{"".join(rows)}</div>'
        f'<div class="lg-foot"><span class="lg-info">1–{per} of {len(rows)} pairs</span>'
        f'<span class="lg-pager">{_lg_pager_html(0, pages)}</span></div></div>'
    )


def _pair_statistics(correlation: Dict[str, Any], pairs: Sequence[Dict[str, Any]]) -> str:
    """Every statistic the matrix does NOT already show, one row per pair, in
    the order the matrix is read (by r). r and d are deliberately absent --
    they are in the matrix, and printing them twice was the complaint."""
    if not pairs:
        return ""
    labels: List[str] = list(correlation.get("labels") or [])
    index = {label: position for position, label in enumerate(labels)}
    short = _short_labels(labels)
    ordered = sorted(
        pairs,
        key=lambda p: -(p.get("pearson") if _is_num(p.get("pearson")) else -9.0),
    )
    observations = {p.get("observations") for p in pairs}
    same_n = len(observations) == 1 and _is_num(next(iter(observations)))
    # As many pairs per page as the matrix has rows (n bots give n(n-1)/2
    # pairs), so this card stays level with the Pair matrix beside it; the
    # rest are paged by the report's own pager (runtime script, `.lg-box`).
    per = max(3, len(labels))
    rows = []
    for position, pair in enumerate(ordered):
        a, b = pair.get("label_a"), pair.get("label_b")
        p_value = pair.get("p_value")
        p_style = "color:var(--pf-amber-ink)" if _is_num(p_value) and p_value >= 0.05 else ""
        rows.append(
            f'<div class="pf-row" data-r="x"{" hidden" if position >= per else ""}>'
            f'<span class="pf-pn" title="{_esc(a)} x {_esc(b)}">{_dot(index.get(a, 0))}'
            f'<span class="pf-name">{_esc(short.get(str(a), a))}</span>&nbsp;&times;&nbsp;'
            f'{_dot(index.get(b, 0))}<span class="pf-name">{_esc(short.get(str(b), b))}</span></span>'
            f'<span class="pf-num">{_num(pair.get("spearman"), 2, sign=True)}</span>'
            f'<span class="pf-num">{_esc(pair.get("co_active_buckets"))}</span>'
            f'<span class="pf-num" style="{p_style}">{"&lt;0.001" if _is_num(p_value) and p_value < 0.001 else _num(p_value, 3)}</span>'
            f'<span class="pf-num">{_num(_exposure_overlap(pair), 2)}</span>'
            f'<span style="text-align:right">{_pair_flag(pair)}</span>'
            "</div>"
        )
    significant = sum(1 for p in pairs if p.get("is_significant"))
    traps = sum(1 for p in pairs if _is_trap(p))
    alignment = correlation.get("alignment") or {}
    n_text = (
        f"<span><em>n (every pair)</em><b>{_esc(next(iter(observations)))}</b> &times; "
        f"{_esc(alignment.get('bucket_label') or '')} buckets</span>"
        if same_n
        else f"<span><em>n</em>varies by pair ({_esc(alignment.get('bucket_label') or '')} buckets)</span>"
    )
    # Which PnL every coefficient above is: the reader comparing this matrix
    # with a single bot's report needs to know it is not the realized-at-close
    # series that report is built on.
    if alignment.get("pnl_basis") == "MARK_TO_MARKET_DAILY":
        n_text += (
            '<span title="OKX public daily PnL, revalued daily -- the one series OKX '
            'publishes for every lead trader, order book or not"><em>basis</em>'
            "mark-to-market daily PnL</span>"
        )
    return (
        '<div class="pf-box pf-pairs">'
        '<div class="pf-box-h"><span class="pf-lbl" title="&rho; = rank correlation, co = buckets '
        "where both traded, p = p-value of r, ov = exposure overlap. Flag: Trap = uncorrelated "
        'results with the same exit behaviour; Same = exit distance &le; 0.15; n/s = not significant.">'
        'Pair statistics<i class="pf-i">i</i></span></div>'
        '<div class="pf-row pf-row-h"><span></span>'
        f'<span>{_fl("ρ", "pf_rho")}</span><span>{_fl("co", "pf_co")}</span>'
        f'<span>{_fl("p", "pf_p")}</span><span>{_fl("ov", "pf_ov")}</span><span>flag</span></div>'
        + _paged_pairs(rows, per)
        + f'<div class="pf-mini"><span><em>Significant</em><b>{significant}/{len(pairs)}</b></span>'
        f"<span><em>Traps</em><b>{traps}</b></span>{n_text}</div>"
        "</div>"
    )


# --------------------------------------------------------------------------- #
# Joint risk view
# --------------------------------------------------------------------------- #


def _horizon(joint: Dict[str, Any]) -> str:
    """"130 d" / "42 × 4h": how far every simulated path runs. A VaR without
    its horizon is not a number anyone can compare."""
    days = joint.get("horizon_calendar_days")
    buckets = joint.get("horizon_buckets")
    if _is_num(days) and days > 0:
        return f"{float(days):,.0f} days" if float(days) >= 1 else f"{float(days) * 24:,.0f} hours"
    return f"{int(buckets)} periods" if _is_num(buckets) and buckets else ""


def _tail_tag(ratio: Any) -> str:
    """Tail removed by combining, signed and toned: a negative ratio means
    combining made the loss tail WORSE -- never a green "-X%" badge."""
    if not _is_num(ratio):
        return ""
    pct = float(ratio) * 100.0
    if pct < 0:
        return f'<span class="pf-tag pf-tag-bad">tail +{_num(-pct, 0, "%")} worse</span>'
    tone = "ok" if pct >= 30 else "warn"
    return f'<span class="pf-tag pf-tag-{tone}">tail &minus;{_num(pct, 0, "%")}</span>'


def _var_chart(joint: Dict[str, Any]) -> str:
    """Three VaRs on one axis. The gap between the undiversified figure and
    this portfolio's IS the finding, so they share a scale and need no prose."""
    bars = [
        (_fl("Undiversified", "pf_undiversified"), "each bot's own VaR, capital-weighted",
         joint.get("sum_individual_var_95_pct"), "var(--ink-3)"),
        (_fl("This portfolio", "pf_joint_var"), "joint, real co-movement",
         joint.get("var_95_pct"), "var(--down)"),
        (_fl("Independent", "pf_independent_var"), "co-movement removed",
         joint.get("independent_var_95_pct"), "var(--amber)"),
    ]
    values = [value for _, _, value, _ in bars if _is_num(value)]
    if not values:
        return ""
    # A VaR at or below zero means even the worst 5% of runs ended flat or
    # up: there is no loss to draw, so the bar stays at its minimum rather
    # than being scaled by a negative number.
    top = max(max(values), 0.0) or 1.0
    rows = []
    for label, sub, value, colour in bars:
        if _is_num(value):
            # A VaR at or below zero is drawn as a stub: nothing to lose.
            width = max(1.0, min(100.0, 100.0 * max(float(value), 0.0) / top))
            bar = f'<i style="width:{width:.1f}%;background:{colour}"></i>'
            text = (
                f'<b style="color:{colour if colour != "var(--ink-3)" else "var(--ink-2)"}">'
                f'{_num(value, 1, "%")}</b>'
            )
        else:
            bar, text = "", '<b class="pf-na">not measured</b>'
        rows.append(
            '<div class="pf-var-row">'
            f'<span class="pf-var-l"><span>{label}</span><em>{_esc(sub)}</em></span>'
            f'<span class="pf-track">{bar}</span>{text}</div>'
        )
    horizon = _horizon(joint)
    return (
        '<div class="pf-box">'
        '<div class="pf-box-h"><span class="pf-lbl" title="Share of the combined capital lost at the '
        'end of the horizon in the worst 5% of simulated paths. Positive = loss.">95% VaR'
        + (f' &middot; {_esc(horizon)}' if horizon else "")
        + '<i class="pf-i">i</i></span>'
        + _tail_tag(joint.get("diversification_ratio"))
        + "</div>"
        '<div class="pf-var" role="img" aria-label="95% VaR: undiversified, this portfolio, independent">'
        + "".join(rows)
        + "</div></div>"
    )


def _outcome_chart(joint: Dict[str, Any]) -> str:
    """Where the simulated runs land: P05 - P50 - P95, break-even marked."""
    low, mid, high = (
        joint.get("profit_pct_p05"),
        joint.get("profit_pct_p50"),
        joint.get("profit_pct_p95"),
    )
    if not all(_is_num(v) for v in (low, mid, high)):
        return ""
    low, mid, high = float(low), float(mid), float(high)
    lo, hi = min(low, 0.0), max(high, 0.0)
    span = (hi - lo) or 1.0
    width, height = 600.0, 52.0

    def x(value: float) -> float:
        return 8.0 + (width - 16.0) * (value - lo) / span

    zero = x(0.0)
    prob = joint.get("probability_of_profit")
    # Same bands as the report's own Monte Carlo colouring: green only when
    # losing runs are rare, red when a loss is closer to a coin flip.
    prob_tone = (
        "ok" if _is_num(prob) and prob >= 80 else "warn" if _is_num(prob) and prob >= 60 else "bad"
    )
    tag = (
        f'<span class="pf-tag pf-tag-{prob_tone}">{_fl("P(profit)", "pf_prob_profit")}&nbsp;{_num(prob, 1, "%")}</span>'
        if _is_num(prob)
        else ""
    )
    iterations = joint.get("iterations")
    paths = _esc(f"{int(iterations):,}") if _is_num(iterations) else "&mdash;"
    ruin = joint.get("p_ruin")
    mini = (
        '<div class="pf-mini">'
        f'<span><em>{_fl("Max DD P95", "pf_sim_max_dd")}</em><b style="color:var(--down)">{_num(joint.get("p95_max_drawdown"), 1, "%")}</b></span>'
        f'<span><em>{_fl("CVaR 95%", "pf_cvar")}</em><b style="color:var(--down)">{_num(joint.get("cvar_95_pct"), 1, "%")}</b></span>'
        f'<span><em>{_fl("Ruin", "pf_ruin")}</em><b style="color:{"var(--down)" if _is_num(ruin) and ruin > 0 else "var(--ink)"}">{_num(ruin, 1, "%")}</b></span>'
        f"<span><em>Paths</em><b>{paths}</b></span>"
        "</div>"
    )
    horizon = _horizon(joint)
    return (
        '<div class="pf-box">'
        '<div class="pf-box-h"><span class="pf-lbl" title="5th / 50th / 95th percentile of the book\'s '
        'simulated return at the end of the horizon, % of combined capital. Dashed line = break-even.">'
        + _fl("Outcome", "pf_outcome")
        + (f' &middot; {_esc(horizon)}' if horizon else "")
        + "</span>" + tag + "</div>"
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" class="pf-svg" role="img" '
        'aria-label="Simulated return range">'
        f'<rect x="8" y="12" width="{width - 16:.0f}" height="8" rx="4" style="fill:var(--track)"/>'
        '<defs><linearGradient id="pf-outcome-band" x1="0" x2="1">'
        '<stop offset="0" style="stop-color:var(--down);stop-opacity:.45"/>'
        '<stop offset=".35" style="stop-color:var(--info);stop-opacity:.35"/>'
        '<stop offset="1" style="stop-color:var(--up);stop-opacity:.45"/></linearGradient></defs>'
        f'<rect x="{x(low):.1f}" y="12" width="{max(3.0, x(high) - x(low)):.1f}" height="8" rx="4" '
        'style="fill:url(#pf-outcome-band)"/>'
        f'<line x1="{zero:.1f}" y1="6" x2="{zero:.1f}" y2="26" style="stroke:var(--ink-3)" '
        'stroke-dasharray="2 2"/>'
        f'<circle cx="{x(mid):.1f}" cy="16" r="7" style="fill:var(--info);stroke:var(--panel)" stroke-width="3"/>'
        f'<text x="{x(low):.1f}" y="44" text-anchor="start" class="pf-svg-val" '
        f'style="fill:{"var(--down)" if low < 0 else "var(--ink-2)"}">'
        f'{_num(low, 1, "%", sign=True)}</text>'
        f'<text x="{x(mid):.1f}" y="44" text-anchor="middle" class="pf-svg-val" style="fill:var(--info)">'
        f'{_num(mid, 1, "%", sign=True)}</text>'
        f'<text x="{x(high):.1f}" y="44" text-anchor="end" class="pf-svg-val" style="fill:var(--up)">'
        f'{_num(high, 1, "%", sign=True)}</text>'
        "</svg>" + mini + "</div>"
    )


# --------------------------------------------------------------------------- #
# Book & market view
# --------------------------------------------------------------------------- #

# Open-exposure rows shown before the "more" fold, and the most rows the fold
# itself lists before rolling the tail into one line. A two-bot portfolio of
# multi-instrument bots touched 71 symbols: every one is real, but a 71-row
# table is a data dump -- the tail is summed, never dropped.
_BOOK_VISIBLE = 5
_MAX_SYMBOL_ROWS = 12

_TREND_TONE = {"BULLISH": "var(--up)", "BEARISH": "var(--down)"}
_VOL_TONE = {"HIGH": "var(--pf-amber-ink)", "EXTREME": "var(--pf-down-ink)"}


def _word(value: Any) -> str:
    text = str(value or "").replace("_", " ").strip()
    return text.capitalize() if text else "&mdash;"


def _tone_style(value: Any, table: Dict[str, str]) -> str:
    colour = table.get(str(value or "").upper())
    return f' style="color:{colour};font-weight:700"' if colour else ""


def _book_and_market(
    portfolio: Dict[str, Any],
    resolved: Sequence[Dict[str, Any]],
    unresolved: Sequence[Dict[str, Any]],
) -> str:
    block = portfolio.get("concentration") or {}
    breakdown = list(portfolio.get("symbol_breakdown") or [])
    market_by_symbol = {str(m.get("symbol", "")).upper(): m for m in resolved or []}
    missing_by_symbol = {str(m.get("symbol", "")).upper(): m for m in unresolved or []}
    has_book = bool(breakdown)
    if not has_book:
        # Older records carry the open-exposure split but no per-symbol trade
        # book: show what exists instead of inventing zero trades.
        breakdown = [
            {"symbol": symbol, "exposure_share": share}
            for symbol, share in (block.get("by_symbol") or {}).items()
        ]
    if not breakdown and not block:
        return '<div class="pf-note">No open exposure or per-symbol book was recorded for this run.</div>'

    def market_cells(symbol: str) -> str:
        market = market_by_symbol.get(symbol)
        if market:
            return (
                f'<span data-l="Trend"{_tone_style(market.get("trend"), _TREND_TONE)} '
                f'title="{_esc(market.get("trend"))} &middot; last {_num(market.get("last_price"), 2)}">'
                f'{_esc(_word(market.get("trend")))}</span>'
                f'<span data-l="Vol"{_tone_style(market.get("volatility"), _VOL_TONE)}>{_esc(_word(market.get("volatility")))}</span>'
                f'<span data-l="Liquidity">{_esc(_word(market.get("liquidity_tier")))}</span>'
                f'<span data-l="Flow">{_esc(_word(market.get("flow_bias")))}</span>'
            )
        reason = (missing_by_symbol.get(symbol) or {}).get("reason") or "no market data"
        return (
            f'<span class="pf-na" style="grid-column:span 4" title="{_esc(reason)}">'
            f'{_esc(str(reason).replace("_", " ").lower())}</span>'
        )

    top_share = max(
        (float(e.get("exposure_share") or 0.0) for e in breakdown), default=0.0
    ) or 1.0

    def row(entry: Dict[str, Any], position: int) -> str:
        symbol = str(entry.get("symbol", "")).upper()
        share = entry.get("exposure_share")
        share_html = (
            '<span class="pf-share"><span class="pf-track">'
            f'<i style="width:{float(share) / top_share * 100.0:.0f}%;background:var(--info)"></i>'
            f'</span><b>{_num(float(share) * 100.0, 1, "%")}</b></span>'
            if _is_num(share) and share > 0
            else '<span class="pf-na">&mdash;</span>'
        )
        book = ""
        if has_book:
            pnl = entry.get("realized_pnl")
            pnl_style = (
                ' style="color:var(--up)"' if _is_num(pnl) and pnl > 0
                else ' style="color:var(--down)"' if _is_num(pnl) and pnl < 0 else ""
            )
            book = (
                f'<span class="pf-num" data-l="Notional">{_money(entry.get("open_notional"))}</span>'
                f'<span class="pf-num" data-l="Trades">{_esc(entry.get("closed_trades"))}</span>'
                f'<span class="pf-num" data-l="Win">{_num(entry.get("win_rate"), 0, "%")}</span>'
                f'<span class="pf-num" data-l="Realised"{pnl_style}>{_money(pnl, sign=True)}</span>'
            )
        return (
            '<div class="pf-row">'
            f'<span class="pf-sym" style="font-family:var(--mono)"><b>{_esc(symbol)}</b></span>'
            f"{share_html}{book}"
            '<span class="pf-div"></span>'
            f"{market_cells(symbol)}"
            "</div>"
        )

    header = (
        '<div class="pf-row pf-row-h"><span>Symbol</span><span>Open exposure</span>'
        + (
            '<span style="text-align:right">Notional</span><span style="text-align:right">Trades</span>'
            '<span style="text-align:right">Win</span><span style="text-align:right">Realised</span>'
            if has_book else ""
        )
        + '<span class="pf-div"></span><span>Trend</span><span>Vol</span><span>Liquidity</span><span>Flow</span></div>'
    )
    open_rows = [e for e in breakdown if _is_num(e.get("exposure_share")) and e["exposure_share"] > 0]
    shown = open_rows[:_BOOK_VISIBLE] if open_rows else breakdown[:_BOOK_VISIBLE]
    rest = [e for e in breakdown if e not in shown]
    room = max(0, _MAX_SYMBOL_ROWS - len(shown))
    folded, tail = rest[:room], rest[room:]
    fold = ""
    if folded:
        tail_row = ""
        if tail:
            tail_share = sum(float(e.get("exposure_share") or 0.0) for e in tail)
            tail_pnl = sum(float(e.get("realized_pnl") or 0.0) for e in tail)
            tail_trades = sum(int(e.get("closed_trades") or 0) for e in tail)
            tail_row = (
                '<div class="pf-row" style="opacity:.75">'
                f"<span><i>{len(tail)} more</i></span>"
                f'<span class="pf-num" style="text-align:left">{_num(tail_share * 100.0, 1, "%")} combined</span>'
                + (
                    f'<span></span><span class="pf-num">{tail_trades}</span><span></span>'
                    f'<span class="pf-num">{_money(tail_pnl, sign=True)}</span>'
                    if has_book else ""
                )
                + '<span class="pf-div"></span><span class="pf-na" style="grid-column:span 4">rolled up</span></div>'
            )
        names = " &middot; ".join(_esc(str(e.get("symbol", "")).upper()) for e in folded[:6])
        fold = (
            '<details class="pf-more"><summary>'
            f"Show {len(rest)} more symbol{'s' if len(rest) != 1 else ''}"
            f"<span>{names}{' &middot; &hellip;' if len(folded) > 6 or tail else ''}</span></summary>"
            f'<div class="pf-rows">{"".join(row(e, i) for i, e in enumerate(folded))}{tail_row}</div>'
            "</details>"
        )
    directional = block.get("directional_alignment")
    net = block.get("net_notional")
    lean = (
        "net long" if _is_num(net) and net > 0
        else "net short" if _is_num(net) and net < 0
        else "of open notional"
    )
    largest = block.get("largest_symbol_share_pct")
    kpis = (
        '<div class="pf-kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))">'
        f'<div class="pf-kpi"><div class="pf-kpi-l">{_fl("Largest symbol", "pf_largest_symbol")}</div>'
        f'<div class="pf-kpi-v" style="color:{"var(--pf-amber-ink)" if _is_num(largest) and largest >= 50 else "var(--ink)"}">'
        f'{_num(largest, 1, "%")}</div><div class="pf-kpi-l">{_esc(block.get("largest_symbol") or "")}</div></div>'
        '<div class="pf-kpi" title="0 = even across symbols held, 1 = all in one">'
        f'<div class="pf-kpi-l">{_fl("Norm. HHI", "pf_hhi")}</div><div class="pf-kpi-v">{_num(block.get("normalised_hhi"), 3)}</div>'
        f'<div class="pf-kpi-l">{len(open_rows)} symbols open</div></div>'
        '<div class="pf-kpi" title="100% = one directional bet, however many bots placed it">'
        f'<div class="pf-kpi-l">{_fl("Same direction", "pf_direction")}</div><div class="pf-kpi-v" style="color:'
        f'{"var(--pf-amber-ink)" if _is_num(directional) and directional >= 0.8 else "var(--ink)"}">'
        f'{_num(None if directional is None else directional * 100.0, 0, "%")}</div>'
        f'<div class="pf-kpi-l">{lean}</div></div>'
        f'<div class="pf-kpi"><div class="pf-kpi-l">{_fl("Gross notional", "pf_gross")}</div>'
        f'<div class="pf-kpi-v">{_money(block.get("gross_notional"))}</div><div class="pf-kpi-l">open</div></div>'
        "</div>"
    )
    groups = (
        '<div class="pf-row pf-row-g"><span></span><span class="pf-grp">BOOK</span>'
        + ("<span></span>" * 4 if has_book else "")
        + '<span class="pf-div"></span><span class="pf-grp" style="grid-column:span 4">MARKET</span></div>'
    )
    table = (
        f'<div class="{"pf-book" if has_book else "pf-book-nb"}" style="margin-top:14px" '
        'aria-label="Book and market, per instrument">'
        f'<div class="pf-rows">{groups}{header}{"".join(row(e, i) for i, e in enumerate(shown))}</div>'
        f"{fold}</div>"
    )
    # Open positions exist only where the order book does: say whose book
    # this is when a member's is hidden, or the tab reads as the whole book.
    hidden = [
        str(m.get("label") or m.get("unique_code"))
        for m in portfolio.get("members") or [] if m.get("ledger_hidden")
    ]
    scope = (
        '<div class="pf-note">Open exposure and the per-symbol book cover the '
        f'{len(portfolio.get("members") or []) - len(hidden)} member(s) whose order book is '
        'visible. Not included: '
        + _esc(", ".join(hidden))
        + " &mdash; OKX hides its positions with its order book.</div>"
        if hidden else ""
    )
    return kpis + table + scope


# --------------------------------------------------------------------------- #
# Members view
# --------------------------------------------------------------------------- #

_ABSENT_LABEL = {"concealed": "CONCEALED", "error": "UNREADABLE"}
_ABSENT_TAG = {"concealed": "pf-tag-bad", "error": "pf-tag-warn"}
_ABSENT_MEANING = {
    "concealed": "order book hidden (OKX 60004) &middot; nothing here measures this bot",
    "error": "the read failed &middot; re-run to include this bot",
}
_ABSENT_LEGEND = {
    "concealed": "<b>CONCEALED</b> = the bot withholds its ledger, a finding about the bot",
    "error": "<b>UNREADABLE</b> = the fetch failed, a property of this run &mdash; retry it",
}


def _members(
    portfolio: Dict[str, Any], failures: Sequence[Dict[str, Any]], labels: Sequence[str]
) -> str:
    members = portfolio.get("members") or []
    index = {label: position for position, label in enumerate(labels)}
    weights = [m.get("capital_weight") for m in members if _is_num(m.get("capital_weight"))]
    top = max(weights) if weights else 1.0
    rows = []
    for position, member in enumerate(members):
        excluded = member.get("excluded_reason")
        weight = member.get("capital_weight")
        code = str(member.get("unique_code") or "")
        pnl = member.get("realized_pnl")
        colour_index = index.get(member.get("label"), position)
        ledger_hidden = bool(member.get("ledger_hidden"))
        rows.append(
            '<div class="pf-row"' + (' style="opacity:.6"' if excluded else "") + ">"
            f'<span class="pf-pn">{_dot(colour_index)}{_name(member.get("label"), 40)}</span>'
            # A real href, so the cell works when this page is opened
            # directly; the class and data-code let the SPA intercept it.
            f'<span><a class="pf-member-link" data-code="{_esc(code)}" href="/bot/{_esc(code)}" '
            f'title="{_esc(code)}">{_esc(code[:8])}{"&hellip;" if len(code) > 8 else ""}</a></span>'
            f'<span style="font-family:var(--mono)" data-l="Symbol">{_esc(member.get("symbol"))}</span>'
            + (
                '<span class="pf-num pf-na" data-l="Trades" title="Order book hidden on OKX">&mdash;</span>'
                if ledger_hidden
                else f'<span class="pf-num" data-l="Trades">{_esc(member.get("closed_trade_count"))}</span>'
            )
            + (
                # A ledger-hidden member has no closed trades: its figure is
                # OKX's public mark-to-market PnL over its own public window,
                # a different quantity over a different span -- marked so.
                f'<span class="pf-num" data-l="PnL (public)" title="OKX public daily PnL, marked to market, '
                f'summed over {_esc(member.get("public_window_days") or "its")} days -- not closed trades" '
                f'style="color:{"var(--up)" if _is_num(pnl) and pnl > 0 else "var(--down)" if _is_num(pnl) and pnl < 0 else "var(--ink)"}">'
                f'{_money(pnl, sign=True)}<sup class="pf-mtm">MTM</sup></span>'
                if ledger_hidden
                else f'<span class="pf-num" data-l="Realised" style="color:{"var(--up)" if _is_num(pnl) and pnl > 0 else "var(--down)" if _is_num(pnl) and pnl < 0 else "var(--ink)"}">'
                f"{_money(pnl, sign=True)}</span>"
            )
            + (
                f'<span class="pf-share" title="Capital: {"OKX investAmt" if member.get("capital_source") == "OKX_INVEST_AMT" else "equity-curve model"} {_money(member.get("capital_at_risk"))}"><span class="pf-track">'
                f'<i style="width:{float(weight) / top * 100.0:.0f}%;background:{_MEMBER_COLOURS[colour_index % 8]}"></i>'
                f'</span><b>{_num(weight * 100.0, 0, "%")}</b></span>'
                if _is_num(weight)
                else '<span class="pf-na">&mdash;</span>'
            )
            + f'<span data-l="Side">{_esc(_word(member.get("position_side")))}</span>'
            + (
                f'<span class="pf-na" title="{_esc(excluded)}">excluded</span>'
                if excluded
                else (
                    '<span><span class="pf-tag pf-tag-warn" title="Order book hidden on OKX '
                    "(60004): measured from OKX's public daily PnL -- no trades, positions "
                    'or exit behaviour">Public PnL</span></span>'
                )
                if ledger_hidden
                else '<span><span class="pf-tag pf-tag-ok">Measured</span></span>'
            )
            + "</div>"
        )
    absent_rows = []
    for item in sorted(
        failures or [], key=lambda f: (f.get("kind") != "concealed", f.get("bot_folder_name"))
    ):
        kind = str(item.get("kind") or "error")
        code = str(item.get("bot_folder_name") or "").removeprefix("bot_")
        absent_rows.append(
            '<div class="pf-row pf-off">'
            f'<span class="pf-pn"><span class="pf-tag {_ABSENT_TAG.get(kind, "pf-tag-warn")}">'
            f'{_esc(_ABSENT_LABEL.get(kind, kind.title()))}</span></span>'
            f'<span><a class="pf-member-link" data-code="{_esc(code)}" href="/bot/{_esc(code)}" '
            f'title="{_esc(code)}">{_esc(code[:8])}{"&hellip;" if len(code) > 8 else ""}</a></span>'
            f'<span style="font-family:var(--mono)">{_esc(item.get("asset"))}</span>'
            f'<span class="pf-na" style="grid-column:span 5">{_ABSENT_MEANING.get(kind, "")}</span>'
            "</div>"
        )
    present = {str(f.get("kind") or "error") for f in failures or []}
    legend = " &middot; ".join(_ABSENT_LEGEND[k] for k in ("concealed", "error") if k in present)
    return (
        '<div class="pf-members" style="margin-top:14px"><div class="pf-rows">'
        '<div class="pf-row pf-row-h"><span>Bot</span><span>Code</span><span>Symbol</span>'
        '<span style="text-align:right">Trades</span><span style="text-align:right">Realised</span>'
        "<span>Weight</span><span>Side</span><span>Status</span></div>"
        + "".join(rows)
        + (
            '<div class="pf-row pf-row-h" style="padding-top:14px"><span style="grid-column:1/-1">'
            "Submitted but not measured</span></div>"
            if absent_rows else ""
        )
        + "".join(absent_rows)
        + "</div></div>"
        + (f'<div class="pf-note">{legend}</div>' if legend else "")
    )


# --------------------------------------------------------------------------- #


def _fl(label: str, key: str) -> str:
    """A label that explains itself: hover shows the portfolio formula, the
    star opens it -- the same markup and handlers the report's own labels use
    (`report_page._calc_label_html`), fed from `portfolio_formulas`."""
    info = PF_FORMULAS.get(key)
    if not info:
        return _esc(label)
    title, formula, desc = (_esc(info.get(k, "")) for k in ("title", "formula", "desc"))
    tip = _esc(f"{info.get('title', '')}\n📐 Formula: {info.get('formula', '')}\n💡 {info.get('desc', '')}")
    return (
        f'<span class="param-label" title="{tip}" data-metric-key="{_esc(key)}" '
        f'data-title="{title}" data-formula="{formula}" data-desc="{desc}">{_esc(label)}</span>'
        f'<button type="button" class="formula-star-btn" onclick="openFormulaModal(\'{_esc(key)}\')" '
        f'data-metric-key="{_esc(key)}" aria-label="View formula {title}">*</button>'
    )


def _book_view(book: Dict[str, Any], labels: Sequence[str]) -> str:
    """The book as ONE account, and where its risk sits.

    The headline numbers of a single-bot report, computed the portfolio way:
    from the N aligned PnL series summed per period (see
    `report.qc.portfolio.book_metrics`), never from a pooled trade list.
    """
    if not book:
        return ""
    index = {label: position for position, label in enumerate(labels)}
    basis = (
        "mark-to-market daily PnL" if book.get("pnl_basis") == "MARK_TO_MARKET_DAILY"
        else "realized PnL by close time"
    )

    def kpi(label: str, key: str, value: str, colour: str = "var(--ink)") -> str:
        return (
            f'<div class="pf-kpi"><div class="pf-kpi-l">{_fl(label, key)}</div>'
            f'<div class="pf-kpi-v" style="color:{colour}">{value}</div></div>'
        )

    ret = book.get("return_pct")
    mdd = book.get("max_drawdown_pct")
    kpis = (
        '<div class="pf-kpis">'
        + kpi("Capital", "pf_capital", _money(book.get("capital")))
        + kpi("Return", "pf_return", _num(ret, 1, "%", sign=True),
              "var(--up)" if _is_num(ret) and ret > 0 else "var(--down)" if _is_num(ret) and ret < 0 else "var(--ink)")
        + kpi("Max drawdown", "pf_max_drawdown", "-" + _num(mdd, 1, "%") if _is_num(mdd) else "&mdash;",
              "var(--down)" if _is_num(mdd) and mdd >= 20 else "var(--pf-amber-ink)" if _is_num(mdd) and mdd >= 10 else "var(--ink)")
        + kpi("Sharpe", "pf_sharpe", _num(book.get("sharpe_annual"), 2))
        + kpi("Profitable days" if book.get("bucket_label") == "1d" else "Profitable periods",
              "pf_profitable_periods", _num(book.get("profitable_period_pct"), 1, "%"))
        + kpi("Volatility", "pf_volatility", _num(book.get("volatility_annual_pct"), 1, "%"))
        + "</div>"
        f'<div class="pf-mini"><span><em>{_fl("Profit factor", "pf_profit_factor")}</em><b>{_num(book.get("profit_factor"), 2)}</b></span>'
        f'<span><em>{_fl("Sortino", "pf_sortino")}</em><b>{_num(book.get("sortino_annual"), 2)}</b></span>'
        f'<span><em>{_fl("DD now", "pf_current_drawdown")}</em><b>{_num(book.get("current_drawdown_pct"), 1, "%")}</b></span>'
        f'<span><em>{_fl("Volatility cancelled", "pf_vol_diversification")}</em><b>{_num(book.get("volatility_diversification_pct"), 1, "%")}</b></span>'
        f'<span><em>{_fl("Periods", "pf_periods")}</em><b>{_esc(book.get("periods"))}</b> &times; {_esc(book.get("bucket_label") or "")}</span>'
        f'<span><em>basis</em>{basis}</span></div>'
    )

    rows = []
    for position, member in enumerate(book.get("members") or []):
        colour = _MEMBER_COLOURS[index.get(member.get("label"), position) % len(_MEMBER_COLOURS)]
        weight = member.get("capital_weight_pct")
        share = member.get("risk_contribution_pct")

        def bar(value: Any, tint: str, caption: str) -> str:
            width = max(0.0, min(100.0, float(value))) if _is_num(value) else 0.0
            return (
                f'<span class="pf-share" data-l="{caption}"><span class="pf-track"><i style="width:{width:.0f}%;background:{tint}"></i>'
                f'</span><b>{_num(value, 1, "%")}</b></span>'
            )

        heavier = _is_num(weight) and _is_num(share) and share > weight * 1.5 and share - weight >= 5
        rows.append(
            '<div class="pf-row">'
            f'<span class="pf-pn">{_dot(index.get(member.get("label"), position))}{_name(member.get("label"), 32)}</span>'
            + bar(weight, "var(--ink-3)", "Capital")
            + bar(share, colour, "Risk")
            + f'<span class="pf-num" data-l="Own vol.">{_num(member.get("standalone_volatility_pct"), 1, "%")}</span>'
            + (
                '<span style="text-align:right"><span class="pf-tag pf-tag-warn" '
                'title="Carries much more of the book\'s risk than of its capital">risk-heavy</span></span>'
                if heavier
                else '<span></span>'
            )
            + "</div>"
        )
    table = (
        '<div class="pf-box pf-riskshare" style="margin-top:14px"><div class="pf-box-h">'
        '<span class="pf-lbl">Capital vs risk</span></div><div class="pf-rows">'
        '<div class="pf-row pf-row-h"><span>Member</span>'
        f'<span>{_fl("Capital", "pf_weight")}</span><span>{_fl("Risk share", "pf_risk_contribution")}</span>'
        f'<span style="text-align:right">{_fl("Own vol.", "pf_standalone_vol")}</span><span></span></div>'
        + "".join(rows)
        + "</div></div>"
    ) if rows else ""
    return (
        '<div class="pf-box" style="margin-bottom:14px"><div class="pf-box-h">'
        '<span class="pf-lbl" title="The N members summed period by period and read as one account">'
        "The book as one account</span></div>"
        + kpis
        + "</div>"
        + table
    )


def _head_parts(
    portfolio: Dict[str, Any], failures: Optional[Sequence[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Header chips, the two verdict cards and the inputs every view shares --
    one computation for the Detail section and the Overview card."""
    failures = list(failures or [])
    correlation = portfolio.get("correlation") or {}
    pairs = correlation.get("pairs") or []
    joint = portfolio.get("joint_simulation") or {}
    alignment = correlation.get("alignment") or {}
    labels = list(correlation.get("labels") or [])
    members = portfolio.get("members") or []
    # A concealed bot whose public daily PnL was recovered is a MEMBER now
    # (in the matrix, flagged `ledger_hidden`), not an absence: only the
    # failures nothing could bring back are "submitted but not measured".
    hidden = [m for m in members if m.get("ledger_hidden")]
    recovered = {str(m.get("unique_code")) for m in hidden}
    failures = [
        f for f in failures
        if str(f.get("bot_folder_name") or "").removeprefix("bot_") not in recovered
    ]

    # --- header chips: caveats and limitations as counters, detail on hover
    chips = []
    if hidden:
        # The matrix and the joint VaR include these bots; the headline
        # risk/quality score, Monte Carlo, drawdown and every trade table do
        # not (they are built from order books). Say how much of the book
        # those headline figures actually describe.
        score_cov = portfolio.get("score_coverage_pct")
        requested = len(members) + len(failures)
        scored = portfolio.get("score_member_count")
        scored = scored if isinstance(scored, int) else len(members) - len(hidden)
        cov_text = f"{score_cov:.0f}%" if _is_num(score_cov) else f"{scored} of {requested} bots"
        hidden_names = ", ".join(str(m.get("label") or m.get("unique_code")) for m in hidden)
        # What is and is not whole-book changed when the book metrics and
        # the joint simulation took over the headline (2026-09-25): only
        # what needs an order book is still partial.
        chips.append(
            f'<span class="pf-chip pf-chip-bad" tabindex="0">SCORE PARTIAL &middot; covers {cov_text}'
            + _pop([
                f"Risk, quality and confidence scores and the trade, exit and position tables "
                f"need an order book: they describe {scored} of {requested} bots"
                + (f", {score_cov:.0f}% of capital." if _is_num(score_cov) else "."),
                f"{hidden_names} hide{'s' if len(hidden) == 1 else ''} the order book on OKX "
                f"(60004) and {'are' if len(hidden) != 1 else 'is'} measured from OKX's public "
                "daily PnL instead.",
                "Every member is in: Net PnL, the book's drawdown, Sharpe and profitable days, "
                "the correlation matrix and the joint simulation (VaR, Monte Carlo).",
                "Not observable for the hidden member" + ("s" if len(hidden) != 1 else "")
                + ": exit behaviour (d), open positions, trades.",
            ])
            + "</span>"
        )
    concealed = sum(1 for f in failures if f.get("kind") == "concealed")
    if concealed:
        coverage = portfolio.get("measurement_coverage_pct")
        requested = len(members) + len(failures)
        measured = (
            f"{coverage:.0f}% measured" if _is_num(coverage)
            else f"{requested - len(failures)} of {requested} measured"
        )
        # The direction matters: dropping a bot that hides its book leaves only
        # disclosers, so correlation and diversification read BETTER than the
        # book the reader holds. "Member missing" alone would not say that.
        chips.append(
            f'<span class="pf-chip pf-chip-bad" tabindex="0">RISK UNDERSTATED &middot; {measured}'
            + _pop([
                f"{concealed} of {requested} submitted "
                f"{'bot conceals' if concealed == 1 else 'bots conceal'} the order book.",
                "Correlation and diversification read better than the book actually held.",
            ])
            + "</span>"
        )
    for label, key, tone in (("caveat", "warnings", "warn"), ("limitation", "limitations", "mute")):
        items = _grouped_notes(portfolio.get(key) or [])
        if items:
            chips.append(
                f'<span class="pf-chip pf-chip-{tone}" tabindex="0">{len(items)} {label}'
                f"{'' if len(items) == 1 else 's'}{_pop(items)}</span>"
            )
    if not chips:
        chips.append('<span class="pf-chip pf-chip-ok">no caveats</span>')

    # --- verdicts
    verdict_tone, verdict_label = _VERDICT_TONE.get(
        str(portfolio.get("verdict") or ""), ("mute", str(portfolio.get("verdict") or "Unknown"))
    )
    style_tone, style_label = _STYLE_TONE.get(
        str(portfolio.get("style_verdict") or ""), ("mute", str(portfolio.get("style_verdict") or "Unknown"))
    )
    distances = [d for d in (_style_distance(p) for p in pairs) if d is not None]
    closest = min(distances) if distances else None
    # The Results verdict is decided on the SIGNIFICANT pairs (see
    # `PortfolioQCService._verdict`), so its card shows that number -- not
    # the all-pairs average in the KPI row, which is a different figure and
    # made "Moderate, r +0.48" disagree with a verdict note reading +0.57.
    significant_r = [
        float(p["pearson"]) for p in pairs if p.get("is_significant") and _is_num(p.get("pearson"))
    ]
    sig_avg = sum(significant_r) / len(significant_r) if significant_r else None
    verdicts = (
        '<div class="pf-verdicts">'
        f'<div class="pf-v pf-v-{verdict_tone}">'
        f'<span class="pf-v-k">Results</span><b>{_esc(verdict_label)}</b>'
        f'<span class="pf-v-n">{_fl("sig. r", "pf_sig_avg_r")} {_num(sig_avg, 2, sign=True)} '
        f'&middot; {len(significant_r)}/{len(pairs)} pairs</span></div>'
        f'<div class="pf-v pf-v-{style_tone}">'
        f'<span class="pf-v-k">Behaviour</span><b>{_esc(style_label)}</b>'
        f'<span class="pf-v-n">closest d {_num(closest, 2)}</span></div>'
        "</div>"
    )

    return {
        "failures": failures, "correlation": correlation, "pairs": pairs, "joint": joint,
        "alignment": alignment, "labels": labels, "members": members, "hidden": hidden,
        "chips": chips, "verdicts": verdicts,
    }


def render_portfolio_section(
    portfolio: Dict[str, Any],
    resolved_markets: Optional[Sequence[Dict[str, Any]]] = None,
    unresolved_markets: Optional[Sequence[Dict[str, Any]]] = None,
    failures: Optional[Sequence[Dict[str, Any]]] = None,
) -> str:
    """The diversification block: verdicts and six numbers up front, the detail
    in four switchable views (correlation, joint risk, book & market,
    members) so a portfolio of eight bots reads no longer than one of two."""
    if not portfolio:
        return ""
    parts = _head_parts(portfolio, failures)
    failures, correlation, pairs, joint = parts["failures"], parts["correlation"], parts["pairs"], parts["joint"]
    alignment, labels, members, hidden = parts["alignment"], parts["labels"], parts["members"], parts["hidden"]
    chips, verdicts = parts["chips"], parts["verdicts"]

    # --- six numbers
    ratio = joint.get("diversification_ratio")
    average = correlation.get("average_pearson")
    maximum = correlation.get("max_pearson")
    max_pair = " x ".join(str(x) for x in (correlation.get("max_pearson_pair") or []))
    kpis = (
        '<div class="pf-kpis">'
        '<div class="pf-kpi" title="Average pairwise correlation">'
        f'<div class="pf-kpi-l">{_fl("Avg r", "pf_avg_r")}</div><div class="pf-kpi-v" style="color:{_pearson_colour(average)}">'
        f'{_num(average, 2, sign=True)}</div></div>'
        f'<div class="pf-kpi" title="Strongest pair: {_esc(max_pair)}">'
        f'<div class="pf-kpi-l">{_fl("Max r", "pf_max_r")}</div><div class="pf-kpi-v" style="color:{_pair_colour(maximum)}">'
        f'{_num(maximum, 2, sign=True)}</div></div>'
        '<div class="pf-kpi" title="Joint 95% VaR, share of combined capital">'
        f'<div class="pf-kpi-l">{_fl("Joint VaR 95%", "pf_joint_var")}</div><div class="pf-kpi-v" style="color:var(--down)">'
        f'{_num(joint.get("var_95_pct"), 1, "%")}</div></div>'
        '<div class="pf-kpi" title="What the same bots risk if they are one bet">'
        f'<div class="pf-kpi-l">{_fl("Undiversified", "pf_undiversified")}</div><div class="pf-kpi-v">'
        f'{_num(joint.get("sum_individual_var_95_pct"), 1, "%")}</div></div>'
        '<div class="pf-kpi" title="Loss tail removed: the gap between the two figures before">'
        f'<div class="pf-kpi-l">{_fl("Tail removed", "pf_tail_removed")}</div><div class="pf-kpi-v" style="color:var(--up)">'
        f'{_num(None if ratio is None else ratio * 100.0, 0, "%")}</div></div>'
        f'<div class="pf-kpi" title="Window in which every member was trading &middot; '
        f'{_esc(alignment.get("evaluated_buckets"))} shared {_esc(alignment.get("bucket_label"))} buckets">'
        f'<div class="pf-kpi-l">{_fl("Shared history", "pf_shared_history")}</div><div class="pf-kpi-v">'
        f'{_num(alignment.get("overlap_days"), 1, " d")}</div></div>'
        "</div>"
    )

    # --- tab labels carry each view's headline, so the bar alone is a summary
    traps = sum(1 for p in pairs if _is_trap(p))
    block = portfolio.get("concentration") or {}
    symbol_count = len(portfolio.get("symbol_breakdown") or block.get("by_symbol") or {})
    failed = len(failures)
    tabs = [
        ("corr", "Correlation", f"max r {_num(maximum, 2, sign=True)} &middot; {traps} trap{'s' if traps != 1 else ''}"),
        ("risk", "Joint risk", f"VaR {_num(joint.get('var_95_pct'), 1, '%')} vs {_num(joint.get('sum_individual_var_95_pct'), 1, '%')}"),
        ("book", "Book &amp; market", f"{symbol_count} symbols &middot; {_num(block.get('largest_symbol_share_pct'), 1, '%')} {_esc(block.get('largest_symbol') or '')}"),
        ("mem", "Members", f"{len(members)} measured"
         + (f" ({len(hidden)} public PnL only)" if hidden else "") + "".join(
            f" &middot; {count} {word}" for count, word in (
                (sum(1 for f in failures if f.get("kind") == "concealed"), "concealed"),
                (sum(1 for f in failures if f.get("kind") != "concealed"), "unreadable"),
            ) if count
        )),
    ]
    radios = "".join(
        f'<input type="radio" name="pf-tab" id="pf-tab-{key}" class="pf-tabradio"'
        f'{" checked" if position == 0 else ""}>'
        for position, (key, _, _) in enumerate(tabs)
    )
    tabbar = '<div class="pf-tabbar">' + "".join(
        f'<label for="pf-tab-{key}"><span class="pf-tab-l">{label}</span>'
        f'<span class="pf-tab-v">{value}</span></label>'
        for key, label, value in tabs
    ) + "</div>"

    corr_pane = (
        '<div class="pf-pane pf-pane-corr"><div class="pf-cols">'
        + _pair_matrix(correlation, pairs, [m.get("label") for m in hidden])
        + _pair_statistics(correlation, pairs)
        + "</div></div>"
    )
    risk_pane = (
        '<div class="pf-pane pf-pane-risk">'
        + _book_view(portfolio.get("book") or {}, labels)
        + (
            '<div class="pf-cols">' + _var_chart(joint) + _outcome_chart(joint) + "</div>"
            if joint
            else '<div class="pf-note">The joint simulation was not run for this portfolio (&mdash;).</div>'
        )
        + "</div>"
    )
    book_pane = (
        '<div class="pf-pane pf-pane-book">'
        + _book_and_market(portfolio, resolved_markets or [], unresolved_markets or [])
        + "</div>"
    )
    members_pane = '<div class="pf-pane pf-pane-mem">' + _members(portfolio, failures, labels) + "</div>"

    return (
        _CSS
        + '<section class="card" id="portfolio-correlation">'
        '<div class="pf-wrap">'
        '<div class="pf-head"><h3 class="pf-title" title="Do these bots spread the risk, or only '
        'the position? Measured on results and on behaviour, which can disagree.">'
        '<span title="Diversification &amp; correlation">Do they spread the risk?</span><i class="pf-i">i</i></h3>'
        f'<div class="pf-chips">{"".join(chips)}</div></div>'
        + verdicts
        + kpis
        + '<div style="position:relative">'
        + radios
        + tabbar
        + corr_pane
        + risk_pane
        + book_pane
        + members_pane
        + "</div>"
        + "</div></section>"
    )


def render_portfolio_overview(
    portfolio: Dict[str, Any], failures: Optional[Sequence[Dict[str, Any]]] = None
) -> str:
    """Overview's first card: do the bots spread the risk -- the header
    chips, the Results / Behaviour verdicts and the pair matrix. Same inputs
    and markup as the Detail section; its statistics, joint risk, book and
    members stay in Detail."""
    if not portfolio or not (portfolio.get("correlation") or {}).get("labels"):
        return ""
    parts = _head_parts(portfolio, failures)
    hidden = parts["hidden"]
    return (
        '<div class="ov-block"><section class="card" aria-label="Diversification and correlation"><div class="block-b">'
        '<div class="pf-wrap">'
        '<div class="pf-head"><h3 class="pf-title" title="Do these bots spread the risk, or only '
        'the position? Measured on results and on behaviour, which can disagree.">'
        '<span title="Diversification &amp; correlation">Diversification &amp; correlation</span></h3>'
        f'<div class="pf-chips">{"".join(parts["chips"])}</div></div>'
        + parts["verdicts"]
        + '<div class="pf-ov-matrix">'
        + _pair_matrix(parts["correlation"], parts["pairs"], [m.get("label") for m in hidden])
        + "</div></div></div></section></div>"
    )


# The same eight colours as `--pf-c1..8`, as literals: the header chips, the
# ledger and the contribution chart sit outside `.pf-wrap`, where those
# custom properties do not reach.
MEMBER_HEX = ("#f7931a", "#627eea", "#9945ff", "#0d9488", "#d97706", "#db2777", "#65a30d", "#64748b")


def member_palette(portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Members in page order with their colour and short label -- the one
    mapping the matrix, the members view, the header chips, the ledger and
    the contribution card all share, so a bot keeps one colour everywhere."""
    members = [m for m in (portfolio.get("members") or []) if isinstance(m, dict)]
    labels = list((portfolio.get("correlation") or {}).get("labels") or [])
    index = {label: position for position, label in enumerate(labels)}
    short = _short_labels([str(m.get("label") or m.get("unique_code") or "") for m in members])
    out = []
    for position, member in enumerate(members):
        label = str(member.get("label") or member.get("unique_code") or "")
        colour = MEMBER_HEX[index.get(label, position) % len(MEMBER_HEX)]
        out.append({**member, "label": label, "short": short.get(label, label), "colour": colour})
    return out


_VENUE_BADGE = re.compile(r'\s*(?:&middot;|·)?\s*<span class="venue-symbol-badge">[^<]*</span>')


def _header_members(portfolio: Dict[str, Any], failures: Sequence[Dict[str, Any]]) -> str:
    """Who is in the book, as chips under the title (each opens that bot),
    plus one line saying what was merged -- in place of the single-bot
    "SYMBOL (CEX)" badge, which on a many-pair book named one market out of
    dozens."""
    members = member_palette(portfolio)
    if not members:
        return ""
    in_book = {str(m.get("unique_code")) for m in members}
    chips = []
    for m in members:
        code = str(m.get("unique_code") or "")
        hidden = bool(m.get("ledger_hidden"))
        chips.append(
            f'<a class="pf-mchip pf-member-link{" pf-mchip-pub" if hidden else ""}" data-code="{_esc(code)}" '
            f'href="/bot/{_esc(code)}" title="{_esc(m["label"])} · {_esc(code)}'
            f'{" · order book hidden, measured from public daily PnL" if hidden else ""}">'
            f'<i style="background:{m["colour"]}"></i>{_esc(m["label"][:28])}</a>'
        )
    for f in failures or []:
        code = str(f.get("bot_folder_name") or "").removeprefix("bot_")
        if not code or code in in_book:
            continue
        word = "concealed" if f.get("kind") == "concealed" else "unreadable"
        chips.append(
            f'<span class="pf-mchip pf-mchip-off" title="{_esc(code)} · {word}, not measured">'
            f'<i></i>{_esc(code[:8])}&hellip; &middot; {word}</span>'
        )
    scored = sum(1 for m in members if not m.get("ledger_hidden"))
    hidden = len(members) - scored
    alignment = (portfolio.get("correlation") or {}).get("alignment") or {}
    days = alignment.get("overlap_days")
    parts = [f"OKX · Merged book of {scored} bot{'s' if scored != 1 else ''}"]
    if hidden:
        parts.append(f"{hidden} via public daily PnL")
    if _is_num(days) and days > 0:
        parts.append(f"{float(days):.1f}-day shared history")
    return (
        f'<div class="report-members">{"".join(chips)}</div>'
        f'<div class="report-subline">{_esc(" · ".join(parts))}</div>'
    )


def inject_portfolio_section(
    document: str,
    portfolio: Dict[str, Any],
    resolved_markets: Optional[Sequence[Dict[str, Any]]] = None,
    unresolved_markets: Optional[Sequence[Dict[str, Any]]] = None,
    failures: Optional[Sequence[Dict[str, Any]]] = None,
) -> str:
    """Put the block at the top of the Analyst Result tab of a finished page.

    Falls back to appending before `</main>`, then `</body>`, if the anchor is
    not found. The anchor lives in a module under active rework, and a missing
    anchor must degrade to "the block is lower down the page" rather than to
    "the portfolio's headline finding silently disappeared".
    """
    section = render_portfolio_section(
        portfolio, resolved_markets, unresolved_markets, failures
    )
    if not section:
        return document
    header = _header_members(portfolio, failures or [])
    if header:
        document = _VENUE_BADGE.sub(lambda _m: header, document, count=1)
    overview = render_portfolio_overview(portfolio, failures)
    if overview and _OVERVIEW_ANCHOR in document:
        document = document.replace(_OVERVIEW_ANCHOR, _OVERVIEW_ANCHOR + overview, 1)
    if _PANEL_ANCHOR in document:
        return document.replace(_PANEL_ANCHOR, _PANEL_ANCHOR + section, 1)
    for fallback in ("</main>", "</body>"):
        if fallback in document:
            return document.replace(fallback, section + fallback, 1)
    return document + section
