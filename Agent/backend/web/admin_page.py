"""Self-contained HTML for `GET /admin` -- the admin-only listing page a
human on the team lands on to see EVERY bot this service has an opinion
about at a glance, ranked by how worried they should be, instead of having
to already know a `code` before looking at `GET /bot/<code>`.

This module is a pure renderer, exactly like `report_page.py` next to it: it
takes plain data structures in and returns an HTML string out, with no I/O
of its own (no disk reads, no OKX calls, no access-token checks). All of
that lives in `app.py`'s `GET /admin` route handler -- see that route's own
docstring for the access-control story (this page must 404, not 401/403,
for anyone who is not the configured admin) and for the short-TTL disk-read
cache that keeps a human refreshing this page from re-walking
`Agent/data/assessment/**` on every single load.

Same hard constraints as `report_page.py`, and for the same reasons (see
that module's own docstring): no JavaScript, no external stylesheet/font/
CDN, one self-contained HTML document, every untrusted string HTML-escaped
via `_esc` before it is ever concatenated into a template, every numeric SVG
attribute funnelled through `_coord` so it can never render as "nan"/"inf"/
"None". Every chart primitive (`_pie_chart`, `_horizontal_bars`,
`_vertical_bars`, `_stat_tile`, `_table`, `_badge`, `_theory`, ...) is
IMPORTED from `report_page.py` rather than re-implemented here -- a pie is a
pie regardless of which page draws it, and having exactly one implementation
of each primitive is what keeps both pages' charts behaving identically
(same edge-case handling for a 100%/0%/empty slice, the same escaping
discipline) without anyone having to remember to fix both.

Two data sources feed the table (see `merge_bot_rows`):

  1. `scored_bots` -- the raw `assessment.json` documents `list_scored_bots()`
     / `WebDataService.list_bots()` already read off disk (Vietnamese-keyed:
     `bot`, `khuyen_nghi`, `cham_diem`, `bang_chung`, `mo_phong` -- a
     DIFFERENT shape from the English-keyed `/api/analyze` result
     `report_page.py` consumes; see `_row_from_assessment` for the mapping).
  2. `recent_codes` -- bot codes `access.RecentCodeRegistry` has seen
     analyzed live in this process's own lifetime, with no persisted
     assessment behind them at all. A code that appears ONLY here (never on
     disk) becomes a placeholder row: real code, everything else "chưa có
     dữ liệu" -- this module never calls back into the scoring pipeline to
     fill that in (that would make loading this page as expensive as
     `/api/analyze`, defeating the whole point of it being a cheap listing).

Sort is a plain query-string parameter the CALLER (app.py) re-renders the
whole page for -- there is no client-side sort/filter here at all, on
purpose (task's own explicit "không sắp xếp/lọc bằng JavaScript" rule).
"""

from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlencode

from Agent.backend.web.report_page import (
    VERDICT_COLOR,
    _BarRow,
    _badge,
    _esc,
    _horizontal_bars,
    _int_text,
    _is_finite_number,
    _num,
    _pct,
    _pie_chart,
    _risk_color,
    _stat_tile,
    _table,
    _theory,
    _vertical_bars,
)

# --------------------------------------------------------------------------- #
# Row model -- one dict per bot, built from EITHER an assessment.json
# document OR a bare registry code (see this module's own docstring).
# Every reader below (sort keys, table cells, overview stats) only ever
# touches this normalized shape, never the raw assessment.json keys, so a
# future change to the on-disk schema only has to be taught to
# `_row_from_assessment`.
# --------------------------------------------------------------------------- #


def _venue_asset_label(bot: Mapping[str, Any]) -> Optional[str]:
    venue = bot.get("venue_type")
    asset = bot.get("traded_symbol") or bot.get("asset_context")
    parts = [p for p in (venue, asset) if isinstance(p, str) and p.strip()]
    return " · ".join(parts) if parts else None


def _row_from_assessment(doc: Any) -> Optional[Dict[str, Any]]:
    """One table row from one `assessment.json`-shaped document, or `None`
    when `doc` is too malformed to even carry a bot code -- a document this
    broken cannot be shown OR deduplicated against, so it is silently
    dropped rather than crashing the whole page over one bad file (same
    "skip, don't crash" rule `data.py`'s own `_read_json_documents` already
    applies one layer below this).
    """
    if not isinstance(doc, dict):
        return None
    bot = doc.get("bot")
    bot = bot if isinstance(bot, dict) else {}
    code = bot.get("unique_code")
    if not isinstance(code, str) or not code.strip():
        return None

    khuyen_nghi = doc.get("khuyen_nghi")
    khuyen_nghi = khuyen_nghi if isinstance(khuyen_nghi, dict) else {}
    cham_diem = doc.get("cham_diem")
    cham_diem = cham_diem if isinstance(cham_diem, dict) else {}
    bang_chung = doc.get("bang_chung")
    bang_chung = bang_chung if isinstance(bang_chung, dict) else {}

    risk = cham_diem.get("risk_score")
    if not _is_finite_number(risk):
        risk = khuyen_nghi.get("diem_rui_ro")
    quality = cham_diem.get("quality_score")
    if not _is_finite_number(quality):
        quality = khuyen_nghi.get("diem_chat_luong")
    confidence = khuyen_nghi.get("do_tin_cay")
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

    verdict = khuyen_nghi.get("ket_luan")
    verdict = (
        verdict if isinstance(verdict, str) and verdict.strip() else "THIẾU BẰNG CHỨNG"
    )

    return {
        "code": code,
        "name": bot.get("nick_name") if isinstance(bot.get("nick_name"), str) else None,
        "venue_asset": _venue_asset_label(bot),
        "verdict": verdict,
        "risk": float(risk) if _is_finite_number(risk) else None,
        "quality": float(quality) if _is_finite_number(quality) else None,
        "confidence": float(confidence) if _is_finite_number(confidence) else None,
        "trade_count": int(round(float(trade_count)))
        if _is_finite_number(trade_count)
        else None,
        "generated_at_ms": doc.get("generated_at_ms"),
        "is_veto": is_veto,
        "veto_reasons": veto_reasons,
        "total_pnl": float(total_pnl) if _is_finite_number(total_pnl) else None,
        "registry_only": False,
    }


def _row_from_registry_code(code: str) -> Dict[str, Any]:
    """Placeholder row for a code `RecentCodeRegistry` remembers but that
    never got a persisted `assessment.json` (see this module's own
    docstring) -- every scored field is `None`/empty rather than guessed.
    """
    return {
        "code": code,
        "name": None,
        "venue_asset": None,
        "verdict": "THIẾU BẰNG CHỨNG",
        "risk": None,
        "quality": None,
        "confidence": None,
        "trade_count": None,
        "generated_at_ms": None,
        "is_veto": False,
        "veto_reasons": [],
        "total_pnl": None,
        "registry_only": True,
    }


def merge_bot_rows(
    scored_bots: Optional[Sequence[Any]], recent_codes: Optional[Sequence[str]]
) -> List[Dict[str, Any]]:
    """Union of both sources, deduplicated by bot code -- a code present on
    disk always wins over a bare registry entry for the SAME code (real
    scored data beats a placeholder), and each source is deduplicated
    against ITSELF too (a malformed dataset with two files for one code, or
    a registry that happens to hand back a duplicate, must not double-count
    that bot in the overview stats below).
    """
    rows: List[Dict[str, Any]] = []
    seen: set = set()
    for doc in scored_bots or []:
        row = _row_from_assessment(doc)
        if row is None or row["code"] in seen:
            continue
        seen.add(row["code"])
        rows.append(row)
    for code in recent_codes or []:
        if not isinstance(code, str) or not code.strip() or code in seen:
            continue
        seen.add(code)
        rows.append(_row_from_registry_code(code))
    return rows


# --------------------------------------------------------------------------- #
# Sorting -- a plain query-string parameter, never client-side JS (task's own
# explicit rule). Unknown/missing risk (or whichever field is being sorted
# on) is always pushed to the END regardless of direction: an un-scored
# registry-only bot is neither "safe" nor "dangerous", so it must never
# outrank -- or be outranked by -- every genuinely measured bot just because
# `None` happens to compare oddly against a float.
# --------------------------------------------------------------------------- #

DEFAULT_SORT = "risk_desc"

_SORT_LABELS_VI: Tuple[Tuple[str, str], ...] = (
    ("risk_desc", "Rủi ro cao trước"),
    ("risk_asc", "Rủi ro thấp trước"),
    ("quality_desc", "Chất lượng cao trước"),
    ("confidence_desc", "Độ tin cậy cao trước"),
    ("name_asc", "Tên A → Z"),
)


def _numeric_sort_key(
    field: str, *, descending: bool
) -> Callable[[Dict[str, Any]], Tuple[bool, float]]:
    sign = -1.0 if descending else 1.0

    def key(row: Dict[str, Any]) -> Tuple[bool, float]:
        value = row.get(field)
        if not _is_finite_number(value):
            return (True, 0.0)
        return (False, sign * float(value))

    return key


_SORT_KEYS: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "risk_desc": _numeric_sort_key("risk", descending=True),
    "risk_asc": _numeric_sort_key("risk", descending=False),
    "quality_desc": _numeric_sort_key("quality", descending=True),
    "confidence_desc": _numeric_sort_key("confidence", descending=True),
    "name_asc": lambda row: (row.get("name") is None, (row.get("name") or "").lower()),
}


def sort_rows(rows: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
    key_fn = _SORT_KEYS.get(sort, _SORT_KEYS[DEFAULT_SORT])
    return sorted(rows, key=key_fn)


# --------------------------------------------------------------------------- #
# Overview stats + charts
# --------------------------------------------------------------------------- #

_CORE_VERDICTS: Tuple[str, ...] = ("NGUY HIỂM", "TIỀM ẨN", "TIỀM NĂNG", "AN TOÀN")

_RISK_BUCKET_LABELS: Tuple[str, ...] = ("< 30", "30 – 50", "50 – 70", "≥ 70")


def _risk_bucket_index(value: float) -> int:
    if value < 30.0:
        return 0
    if value < 50.0:
        return 1
    if value < 70.0:
        return 2
    return 3


def _compute_overview(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored = [r for r in rows if r.get("risk") is not None]
    tier_counts: Dict[str, int] = {}
    bucket_counts = [0, 0, 0, 0]
    for r in scored:
        tier = r.get("verdict") or "THIẾU BẰNG CHỨNG"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        bucket_counts[_risk_bucket_index(float(r["risk"]))] += 1

    veto_reason_counts: "Counter[str]" = Counter()
    for r in rows:
        for reason in r.get("veto_reasons") or []:
            veto_reason_counts[reason] += 1

    losing_count = sum(
        1 for r in rows if r.get("total_pnl") is not None and r["total_pnl"] < 0.0
    )
    veto_count = sum(1 for r in scored if r.get("is_veto"))
    median_risk = (
        statistics.median(float(r["risk"]) for r in scored) if scored else None
    )

    return {
        "total": len(rows),
        "scored_total": len(scored),
        "veto_count": veto_count,
        "losing_count": losing_count,
        "median_risk": median_risk,
        "tier_counts": tier_counts,
        "bucket_counts": bucket_counts,
        "veto_reason_counts": veto_reason_counts,
    }


def _render_tier_pie(tier_counts: Dict[str, int]) -> str:
    slices: List[Tuple[str, Optional[float], str]] = [
        (
            verdict,
            float(tier_counts.get(verdict, 0)),
            VERDICT_COLOR.get(verdict, "#6b7280"),
        )
        for verdict in _CORE_VERDICTS
    ]
    other = sum(
        count for verdict, count in tier_counts.items() if verdict not in _CORE_VERDICTS
    )
    if other:
        slices.append(
            (
                "Thiếu bằng chứng / khác",
                float(other),
                VERDICT_COLOR.get("THIẾU BẰNG CHỨNG", "#6b7280"),
            )
        )
    return _pie_chart(slices)


def _render_risk_bucket_bars(bucket_counts: Sequence[int]) -> str:
    rows: List[Tuple[str, Optional[float]]] = [
        (label, float(count))
        for label, count in zip(_RISK_BUCKET_LABELS, bucket_counts)
    ]
    # One fixed colour per BUCKET (what that risk range itself means), never
    # inferred from how many bots happen to land in it this run -- a bucket
    # for scores under 30 is "the low-risk one" regardless of whether 0 or
    # 20 bots are currently in it. Sampled from `_risk_color` at a
    # representative point inside each bucket so this stays visually
    # consistent with every other risk-coloured element on the site.
    colors = [
        _risk_color(15.0),
        _risk_color(40.0),
        _risk_color(60.0),
        _risk_color(75.0),
    ]
    return _vertical_bars(
        rows,
        unit="",
        value_fmt=lambda v: _int_text(v),
        colors=colors,
        max_value=max(max(bucket_counts, default=0), 1),
    )


def _render_veto_reason_bars(counts: "Counter[str]") -> str:
    top = counts.most_common(6)
    if not top:
        return '<p class="empty-note">Chưa ghi nhận lý do veto nào trong danh sách hiện có.</p>'
    max_count = max(count for _, count in top)
    rows = [
        _BarRow(reason, float(count), "#b91c1c", _int_text(count))
        for reason, count in top
    ]
    return _horizontal_bars(rows, max_value=float(max_count))


def _render_stat_tiles(stats: Dict[str, Any]) -> str:
    tiles = [
        _stat_tile("Tổng số bot trong danh sách", _int_text(stats["total"])),
        _stat_tile(
            "Bị veto (sàn / khẩn cấp)",
            _int_text(stats["veto_count"]),
            color="#dc2626" if stats["veto_count"] else None,
        ),
        _stat_tile(
            "Điểm rủi ro trung vị",
            _num(stats["median_risk"], 0) if stats["median_risk"] is not None else "—",
        ),
        _stat_tile(
            "Đang lỗ ròng (PnL đã chốt < 0)",
            _int_text(stats["losing_count"]),
            color="#dc2626" if stats["losing_count"] else None,
        ),
    ]
    return f'<div class="stat-row">{"".join(tiles)}</div>'


def _render_overview(rows: List[Dict[str, Any]]) -> str:
    stats = _compute_overview(rows)
    tiles_html = _render_stat_tiles(stats)
    tier_pie = _render_tier_pie(stats["tier_counts"])
    bucket_bars = _render_risk_bucket_bars(stats["bucket_counts"])
    veto_bars = _render_veto_reason_bars(stats["veto_reason_counts"])

    theory = _theory(
        "Biểu đồ tròn: tỉ trọng 4 xếp loại trong số bot ĐÃ CÓ điểm rủi ro (bot chỉ mới"
        " thấy trong phiên, chưa có điểm, không tính vào đây). Biểu đồ cột: bot rơi vào"
        " khoảng điểm rủi ro nào — cột bên phải cao là dấu hiệu xấu cho cả danh mục,"
        " không phải chỉ một bot lẻ. Biểu đồ ngang: lý do veto lặp lại nhiều nhất —"
        " một lý do xuất hiện ở nhiều bot là một điểm yếu HỆ THỐNG (ví dụ nhiều bot"
        " cùng phụ thuộc một kiểu hành vi rủi ro), không phải trùng hợp.",
        "Tính trực tiếp từ các trường đã có sẵn trong từng assessment.json"
        " (cham_diem.risk_score, cham_diem.score_decided_by, cham_diem.veto_reasons,"
        " khuyen_nghi.ket_luan, bang_chung.total_pnl) — không chấm lại, không gọi lại"
        " pipeline QC, chỉ tổng hợp những gì bước 3 (QC_DANH_GIA) đã ghi ra đĩa.",
    )

    return (
        "<h2>Tổng quan</h2>"
        f"{tiles_html}"
        '<div class="overview-grid">'
        f'<div class="overview-cell"><h3>Phân bố xếp loại</h3>{tier_pie}</div>'
        f'<div class="overview-cell"><h3>Phân bố điểm rủi ro</h3>{bucket_bars}</div>'
        f'<div class="overview-cell overview-cell-wide"><h3>Lý do veto hay gặp nhất</h3>{veto_bars}</div>'
        "</div>"
        f"{theory}"
    )


# --------------------------------------------------------------------------- #
# Table
# --------------------------------------------------------------------------- #


def _format_timestamp_ms(value: Any) -> str:
    if not _is_finite_number(value):
        return "—"
    try:
        dt = datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M") + " UTC"


def _render_table_row_cells(row: Dict[str, Any]) -> List[str]:
    code = row["code"]
    name = row.get("name") or code
    # A CSS-only "click anywhere in the row" link: `.admin-table tbody tr`
    # is `position: relative` (see _ADMIN_CSS) and this anchor is
    # `position: absolute; inset: 0`, which positions it against that
    # nearest POSITIONED ancestor -- the `<tr>` -- even though a plain,
    # unpositioned `<td>` sits between them. No JavaScript needed for "the
    # whole row is clickable", which the task's own "không JS" rule
    # otherwise rules out doing any other way.
    name_cell = (
        f'<a class="row-link" href="/bot/{_esc(code)}" '
        f'aria-label="Xem báo cáo chi tiết {_esc(name)}"></a>'
        f'<span class="row-name">{_esc(name)}</span>'
    )
    if row.get("registry_only"):
        name_cell += ' <span class="badge-mini">phiên gần đây</span>'

    verdict = row.get("verdict") or "THIẾU BẰNG CHỨNG"
    verdict_cell = _badge(verdict, VERDICT_COLOR.get(verdict, "#6b7280"))

    return [
        name_cell,
        f"<code>{_esc(code)}</code>",
        _esc(row.get("venue_asset") or "—"),
        verdict_cell,
        _num(row["risk"], 0) if row.get("risk") is not None else "—",
        _num(row["quality"], 0) if row.get("quality") is not None else "—",
        _pct(row["confidence"], 0) if row.get("confidence") is not None else "—",
        _int_text(row.get("trade_count"))
        if row.get("trade_count") is not None
        else "—",
        _format_timestamp_ms(row.get("generated_at_ms")),
    ]


_TABLE_HEADERS: Tuple[str, ...] = (
    "Tên",
    "Mã",
    "Sàn / Tài sản",
    "Xếp loại",
    "Điểm rủi ro",
    "Điểm chất lượng",
    "Độ tin cậy",
    "Số lệnh đã chốt",
    "Thời điểm chấm",
)


def _render_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return (
            '<p class="empty-note">Chưa có bot nào được chấm điểm sẵn trên đĩa, và'
            " chưa có bot nào được phân tích trong phiên làm việc này.</p>"
        )
    body_rows = [_render_table_row_cells(row) for row in rows]
    return _table(_TABLE_HEADERS, body_rows)


# --------------------------------------------------------------------------- #
# Sort links -- plain `<a href="?sort=...">`, never JavaScript. Preserves
# every OTHER query parameter the current request carried (in particular a
# `token` the admin may have supplied as a query parameter rather than a
# header -- see app.py's `_resolve_access_token`) so switching sort order
# never accidentally drops the very credential that got this page rendered
# in the first place.
# --------------------------------------------------------------------------- #


def _render_sort_links(sort: str, current_query: Mapping[str, str]) -> str:
    links = []
    for key, label_vi in _SORT_LABELS_VI:
        query = dict(current_query)
        query["sort"] = key
        href = "?" + urlencode(query)
        cls = "sort-link sort-link-active" if key == sort else "sort-link"
        links.append(f'<a class="{cls}" href="{_esc(href)}">{_esc(label_vi)}</a>')
    return " · ".join(links)


# --------------------------------------------------------------------------- #
# CSS -- reuses report_page.py's design tokens/section styling (imported
# indirectly through the shared classes those helpers emit: `.card`, `.badge`,
# `.stat-tile`, `.table-scroll`, `details.theory`, `svg.bar-chart`,
# `svg.pie-chart`, ...) plus a handful of rules specific to this page's own
# layout (the header, the overview grid, the clickable-row table).
# --------------------------------------------------------------------------- #

_ADMIN_CSS = """
:root {
  --bg: #f7f7f8;
  --card-bg: #ffffff;
  --text: #1a1a1a;
  --muted: #5b6270;
  --border: #e2e4e9;
  --track: #eceef2;
  --track-muted: repeating-linear-gradient(45deg, #d7d9de, #d7d9de 4px, #eceef2 4px, #eceef2 8px);
  --axis: #9aa0ab;
  --row-hover: rgba(0, 0, 0, 0.025);
  padding-top: env(safe-area-inset-top, 0px);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14161a;
    --card-bg: #1c1f26;
    --text: #eceef1;
    --muted: #9aa0ab;
    --border: #2b2f38;
    --track: #2a2e37;
    --track-muted: repeating-linear-gradient(45deg, #33384333, #333843 4px, #2a2e37 4px, #2a2e37 8px);
    --axis: #5b6270;
    --row-hover: rgba(255, 255, 255, 0.035);
  }
}
:root[data-theme="dark"] {
  --bg: #14161a;
  --card-bg: #1c1f26;
  --text: #eceef1;
  --muted: #9aa0ab;
  --border: #2b2f38;
  --track: #2a2e37;
  --track-muted: repeating-linear-gradient(45deg, #33384333, #333843 4px, #2a2e37 4px, #2a2e37 8px);
  --axis: #5b6270;
  --row-hover: rgba(255, 255, 255, 0.035);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0 16px 3rem;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  line-height: 1.55;
  font-variant-numeric: tabular-nums;
}
.page { max-width: 1080px; margin: 0 auto; }
.admin-header { padding: 1.5rem 0 0.5rem; }
.admin-title { font-size: 1.4rem; font-weight: 700; }
.admin-sub { color: var(--muted); font-size: 0.85rem; margin-top: 0.3rem; }
.sort-link { color: var(--muted); }
.sort-link-active { color: var(--text); font-weight: 700; text-decoration: none; }
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.1rem 1.2rem 1.3rem;
  margin-top: 1rem;
}
.card h2 { margin: 0 0 0.75rem; font-size: 1.15rem; }
.card h3 { margin: 0 0 0.4rem; font-size: 0.92rem; color: var(--muted); }
.stat-row { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0.25rem 0 1rem; }
.stat-tile {
  flex: 1 1 160px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
}
.stat-value { font-size: 1.5rem; font-weight: 700; }
.stat-label { color: var(--muted); font-size: 0.78rem; margin-top: 0.15rem; }
.overview-grid { display: flex; flex-wrap: wrap; gap: 1.5rem; }
.overview-cell { flex: 1 1 320px; min-width: 0; }
.overview-cell-wide { flex: 2 1 420px; }
.badge {
  display: inline-block;
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #fff;
  background: var(--badge-color, #6b7280);
  white-space: nowrap;
}
.badge-mini {
  display: inline-block;
  font-size: 0.68rem;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.02rem 0.4rem;
  margin-left: 0.35rem;
  white-space: nowrap;
}
.table-scroll { overflow-x: auto; margin-top: 0.5rem; }
table { border-collapse: collapse; width: 100%; min-width: 720px; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { color: var(--muted); font-weight: 600; }
td:first-child, th:first-child { white-space: normal; }
.admin-table-card table tbody tr { position: relative; }
.admin-table-card table tbody tr:hover { background: var(--row-hover); }
.row-link { position: absolute; inset: 0; z-index: 0; }
.row-name { position: relative; z-index: 1; font-weight: 600; }
.empty-note { color: var(--muted); font-size: 0.92rem; }
details.theory {
  margin-top: 0.9rem;
  border: 1px dashed var(--border);
  border-radius: 8px;
  padding: 0.5rem 0.8rem;
}
details.theory summary { cursor: pointer; font-weight: 600; font-size: 0.88rem; color: var(--muted); }
.theory-body { font-size: 0.88rem; margin-top: 0.5rem; color: var(--text); }
.theory-body p { margin: 0.4rem 0; }
.theory-body code { background: var(--track); padding: 0.05rem 0.3rem; border-radius: 4px; }
svg.bar-chart, svg.pie-chart { display: block; }
svg text { fill: var(--text); font-size: 12px; }
svg .bar-label, svg .bar-label-sm { fill: var(--muted); font-size: 11.5px; }
svg .bar-value, svg .bar-value-sm { font-weight: 600; font-size: 11.5px; }
svg .pie-label { font-weight: 600; font-size: 11.5px; }
svg .pie-value { fill: var(--muted); font-size: 11px; }
svg .pie-empty { fill: var(--muted); font-size: 12px; }
@media (max-width: 480px) {
  .admin-title { font-size: 1.2rem; }
  .stat-value { font-size: 1.25rem; }
}
"""


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def render_admin_page_html(
    scored_bots: Optional[Sequence[Any]],
    recent_codes: Optional[Sequence[str]],
    *,
    sort: str = DEFAULT_SORT,
    current_query: Optional[Mapping[str, str]] = None,
) -> str:
    """Render the full standalone `GET /admin` page.

    `scored_bots`: the raw list `WebDataService.list_bots()` /
    `list_scored_bots()` returns (one dict per `assessment.json` on disk).
    `recent_codes`: `access.RecentCodeRegistry.codes()`'s current snapshot.
    `sort`: one of `_SORT_LABELS_VI`'s keys; anything else (including an
    absent/blank query parameter) falls back to `DEFAULT_SORT` ("nguy hiểm
    trước" -- the task's own explicit default, not merely A default).
    `current_query`: the incoming request's own query parameters, so the
    sort links this renders can preserve everything else on the URL (a
    `token` above all -- see `_render_sort_links`'s own docstring).

    Never raises on malformed input: every field access below goes through
    `.get()`/the normalizing `_row_from_assessment` with safe fallbacks,
    matching `report_page.py`'s own "hide/placeholder, never crash" rule.
    An empty result (no assessment.json anywhere, an empty registry) still
    renders a complete, valid page -- an empty-state message instead of a
    table, and `_pie_chart`'s own "no data" circle instead of a broken one.
    """
    if sort not in _SORT_KEYS:
        sort = DEFAULT_SORT
    rows = sort_rows(merge_bot_rows(scored_bots, recent_codes), sort)

    sort_links = _render_sort_links(sort, current_query or {})
    header = (
        '<header class="admin-header">'
        '<div class="admin-title">Bảng điều khiển admin — Danh sách bot đã đánh giá</div>'
        f'<div class="admin-sub">{_int_text(len(rows))} bot trong danh sách · sắp xếp:'
        f" {sort_links}</div>"
        "</header>"
    )
    overview_section = f'<section class="card">{_render_overview(rows)}</section>'
    table_section = (
        '<section class="card admin-table-card">'
        f"<h2>Danh sách bot</h2>{_render_table(rows)}"
        "</section>"
    )

    body = header + overview_section + table_section

    return (
        "<!doctype html>\n"
        '<html lang="vi">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<title>Admin · Danh sách bot</title>\n"
        f"<style>{_ADMIN_CSS}</style>\n"
        "</head>\n<body>\n"
        f'<div class="page">{body}</div>\n'
        "</body>\n</html>\n"
    )
