"""Dữ liệu trình bày cho trang báo cáo của một bot LIMITED (OKX trả 60004 --
sổ lệnh không công khai, xem `Agent/backend/bot/analysis/limited.py`'s module
docstring cho toàn bộ bối cảnh: 7/36 lead trader trong một mẫu thật vẫn giữ
`public-lead-traders`/`public-weekly-pnl`/`public-stats` sống trong khi
đúng một tầng -- sổ lệnh từng lệnh -- bị khoá).

VÌ SAO TỒN TẠI: yêu cầu gốc là "bot private phải tận dụng những gì có thể
public để phân tích đánh giá ... đảm bảo report đều giống nhau, vì có nhiều
luồng dữ liệu nên phải kết hợp". `limited.py` đã chấm điểm xong và đã đẩy
đủ dữ liệu thô ra `evidence` (`profile`, `stats`, `weekly_series`,
`pnl_ratio_series`, `drawdown_summary`, `components`) nhưng KHÔNG tự dựng
HTML (không nên -- xem `Agent/backend/web/loss_analysis.py`'s tiền lệ cùng
lý do: tách phần tính khỏi phần trình bày để test được độc lập, và giữ phần
thêm vào `report_page.py` gọn). Module này là lớp trung gian: gom nhiều
luồng `evidence` khác nhau (hồ sơ xếp hạng, thống kê ngày, đường vốn tuần,
chuỗi pnlRatio) thành các cấu trúc phẳng, sẵn sàng để `report_page.py` chỉ
việc format/escape rồi in ra -- không tính lại bất kỳ điểm số nào của
`limited.py`.

KHÔNG BỊA SỐ -- cùng nguyên tắc `loss_analysis.py` đã nêu: mọi trường thiếu
dữ liệu trả về `None` (hoặc bị loại khỏi danh sách), KHÔNG thay bằng 0,
KHÔNG suy diễn từ một nguồn khác. Hàm nào không có gì trung thực để nói thì
trả `None`/`[]` rỗng để `report_page.py` tự quyết định hiện khối giải thích
thay vì một con số giả.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional

__all__ = [
    "public_stats_snapshot",
    "traded_instruments",
    "weekly_equity_points",
    "pnl_ratio_points",
    "drawdown_summary",
    "monte_carlo_gap_reason",
    "narrative_paragraph",
]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _finite_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None
    return number if math.isfinite(number) else None


def _finite_int(value: Any) -> Optional[int]:
    number = _finite_float(value)
    return None if number is None else int(round(number))


def _pct_from_fraction(value: Any) -> Optional[float]:
    """`value` (a fraction like public-stats' `winRatio=0.5872`) as a plain
    percentage. Same convention `Agent/backend/bot/analysis/limited.py` already
    uses for every `pnlRatio`-shaped field (weekly ratios, `pnl_ratio_pct`)
    -- kept identical here so a reader never sees the same underlying unit
    presented two different ways across the page.
    """
    fraction = _finite_float(value)
    return None if fraction is None else fraction * 100.0


def public_stats_snapshot(evidence: Any) -> Optional[Dict[str, Any]]:
    """Every public-lead-traders/public-stats field this module can still
    read for a LIMITED bot, flattened into one dict of plain numbers/strings
    -- the "so-lieu" (số liệu) table's only data source.

    Returns `None` when BOTH `profile` and `stats` are absent/empty (nothing
    honest to show at all) rather than a dict of all-`None` values, so the
    report layer's "no public stats available" fallback is a single falsy
    check away.
    """
    evidence = _mapping(evidence)
    profile = _mapping(evidence.get("profile"))
    stats = _mapping(evidence.get("stats"))
    if not profile and not stats:
        return None

    snapshot = {
        "win_ratio_pct": _pct_from_fraction(stats.get("winRatio")),
        "profit_days": _finite_int(stats.get("profitDays")),
        "loss_days": _finite_int(stats.get("lossDays")),
        "invest_amt": _finite_float(stats.get("investAmt")),
        "avg_sub_pos_notional": _finite_float(stats.get("avgSubPosNotional")),
        "cur_copy_trader_pnl": _finite_float(stats.get("curCopyTraderPnl")),
        "aum": _finite_float(profile.get("aum")),
        "pnl": _finite_float(profile.get("pnl")),
        "pnl_ratio_pct": _pct_from_fraction(profile.get("pnlRatio")),
        "lead_days": _finite_int(profile.get("leadDays")),
        "copy_trader_num": _finite_int(profile.get("copyTraderNum")),
        "max_copy_trader_num": _finite_int(profile.get("maxCopyTraderNum")),
        "acc_copy_trader_num": _finite_int(profile.get("accCopyTraderNum")),
        "rank": _finite_int(profile.get("rank")),
        "copy_state": (
            profile.get("copyState")
            if isinstance(profile.get("copyState"), str)
            else None
        ),
    }
    if all(value is None for value in snapshot.values()):
        return None
    return snapshot


def traded_instruments(evidence: Any) -> Optional[List[str]]:
    """`profile.traderInsts` (the contracts this bot is currently running)
    normalized to a flat, de-duplicated list of plain strings.

    OKX's own shape for this field is not pinned down by any fixture this
    task has seen, so entries are read defensively: a bare string is kept
    as-is, a dict is probed for the first of a few plausible identifier keys
    -- neither guessed value is ever fabricated when absent, the whole entry
    is just skipped.
    """
    profile = _mapping(_mapping(evidence).get("profile"))
    raw = profile.get("traderInsts")
    if not isinstance(raw, list) or not raw:
        return None

    names: List[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
            continue
        if isinstance(item, Mapping):
            for key in ("instId", "symbol", "inst", "name"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    names.append(value.strip())
                    break

    seen: set = set()
    ordered: List[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered or None


def _float_series(rows: Any, key: str) -> Optional[List[float]]:
    if not isinstance(rows, list) or not rows:
        return None
    values = [
        row.get(key)
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get(key), (int, float))
    ]
    values = [float(v) for v in values if math.isfinite(v)]
    return values or None


def weekly_equity_points(evidence: Any) -> Optional[List[float]]:
    """The chartable equity values out of `evidence.weekly_series` (already
    built and time-sorted by `limited.py`), skipping weeks the equity-curve
    builder itself marked unusable (`equity=None`) rather than treating a
    gap as zero equity.
    """
    return _float_series(_mapping(evidence).get("weekly_series"), "equity")


def weekly_series_coverage(evidence: Any) -> Optional[Dict[str, int]]:
    """How many of `weekly_series`'s rows actually have a usable equity
    value, for a chart caption ("X/Y tuần dùng được") -- separate from
    `drawdown_summary`'s own `usable_weeks`/`total_weeks` (that pair comes
    straight off the SAME curve so the two always agree; this helper exists
    so a chart caption doesn't have to reach into `drawdown_summary` for an
    unrelated purpose).
    """
    series = _mapping(evidence).get("weekly_series")
    if not isinstance(series, list) or not series:
        return None
    total = len(series)
    usable = sum(
        1
        for row in series
        if isinstance(row, Mapping) and isinstance(row.get("equity"), (int, float))
    )
    return {"usable": usable, "total": total}


def pnl_ratio_points(evidence: Any) -> Optional[List[float]]:
    """The chartable percentage values out of `evidence.pnl_ratio_series`
    (already normalized and time-sorted by `limited.py`)."""
    return _float_series(_mapping(evidence).get("pnl_ratio_series"), "pnl_ratio_pct")


def drawdown_summary(evidence: Any) -> Optional[Dict[str, Any]]:
    """Passthrough + shape-validation of `evidence.drawdown_summary` (built
    by `limited.py` straight off the same `EquityCurve` the drawdown
    component was scored from). Returns `None` on anything malformed so the
    report layer's fallback path is a single falsy check, never a
    `KeyError`/`TypeError` on a half-shaped dict.
    """
    raw = _mapping(evidence).get("drawdown_summary")
    if not isinstance(raw, Mapping):
        return None
    max_dd = _finite_float(raw.get("max_dd_pct"))
    if max_dd is None:
        return None
    return {
        "max_dd_pct": max_dd,
        "usable_weeks": _finite_int(raw.get("usable_weeks")),
        "total_weeks": _finite_int(raw.get("total_weeks")),
        "wiped_out": bool(raw.get("wiped_out")),
    }


def monte_carlo_gap_reason(evidence: Any) -> Optional[str]:
    """The `monte_carlo` component's own first finding string (e.g. "Không
    đủ mẫu để mô phỏng Monte Carlo: chỉ có 8 điểm PnL tuần, trong khi engine
    yêu cầu tối thiểu 10 mẫu") -- read from `evidence.components`, never
    re-derived, so the placeholder shown when `result["mc"]` is `None` gives
    the SAME reason `limited.py` already scored against, not a second
    independent guess that could drift from it.
    """
    components = _mapping(evidence).get("components")
    if not isinstance(components, list):
        return None
    for component in components:
        if not isinstance(component, Mapping) or component.get("name") != "monte_carlo":
            continue
        findings = component.get("findings")
        if isinstance(findings, list) and findings and isinstance(findings[0], str):
            return findings[0]
    return None


def narrative_paragraph(result: Any) -> Optional[str]:
    """One combined-prose reading of a LIMITED bot, drawing on every public
    stream at once (ranking profile + day-level stats + the weekly-equity
    drawdown reading + Monte Carlo status) -- the direct answer to this
    task's own brief ("có nhiều luồng dữ liệu nên phải kết hợp").

    Deliberately NOT a repeat of `result["text"]` (already shown verbatim,
    line by line, in the "Kết luận và khuyến nghị" section by
    `_render_conclusion` -- see that function's own docstring on why it
    must not reinterpret `limited.py`'s wording): this reads as ONE
    continuous paragraph that cross-references streams inline ("hạng #3
    ... trong khi tỉ lệ ngày lãi ... và đường vốn tuần suy ra ..."), which
    the line-by-line conclusion block does not attempt. Every clause is
    conditional on its own source being present; a bot missing most public
    fields gets a short paragraph, never a padded one.
    """
    result = _mapping(result)
    evidence = _mapping(result.get("evidence"))
    profile = _mapping(evidence.get("profile"))
    stats = _mapping(evidence.get("stats"))
    if not profile and not stats:
        return None

    clauses: List[str] = []

    name = result.get("name") or result.get("code")
    rank = _finite_int(profile.get("rank"))
    lead_days = _finite_int(profile.get("leadDays"))
    identity_bits = []
    if rank is not None:
        identity_bits.append(f"rank #{rank} on the lead-trader ranking")
    if lead_days is not None:
        identity_bits.append(f"{lead_days} days active")
    if identity_bits:
        clauses.append(f"{name} is {', '.join(identity_bits)}")

    aum = _finite_float(profile.get("aum"))
    pnl = _finite_float(profile.get("pnl"))
    pnl_ratio_pct = _pct_from_fraction(profile.get("pnlRatio"))
    money_bits = []
    if aum is not None:
        money_bits.append(f"AUM {aum:,.0f} USDT")
    if pnl is not None:
        money_bits.append(f"total PnL {pnl:,.0f} USDT")
    if pnl_ratio_pct is not None:
        money_bits.append(f"declared return ratio {pnl_ratio_pct:,.1f}%")
    if money_bits:
        clauses.append("Per the public profile: " + ", ".join(money_bits))

    win_ratio_pct = _pct_from_fraction(stats.get("winRatio"))
    profit_days = _finite_int(stats.get("profitDays"))
    loss_days = _finite_int(stats.get("lossDays"))
    if win_ratio_pct is not None:
        day_bit = f"winning-day ratio (public-stats) {win_ratio_pct:.1f}%"
        if profit_days is not None and loss_days is not None:
            day_bit += f" ({profit_days} winning days / {loss_days} losing days)"
        clauses.append(day_bit[0].upper() + day_bit[1:])

    dd = drawdown_summary(evidence)
    if dd is not None:
        clauses.append(
            "The inferred weekly equity curve shows a max drawdown of "
            f"{dd['max_dd_pct']:.1f}% (over {dd['usable_weeks']}/{dd['total_weeks']} "
            "weeks with usable data) -- a DIFFERENT denominator from the per-trade "
            "drawdown only a bot with a public ledger can provide"
        )

    copy_num = _finite_int(profile.get("copyTraderNum"))
    copy_max = _finite_int(profile.get("maxCopyTraderNum"))
    if copy_num is not None and copy_max is not None:
        clauses.append(f"Currently {copy_num}/{copy_max} people are copying this bot")

    mc = result.get("mc")
    if not isinstance(mc, Mapping) or not mc:
        gap = monte_carlo_gap_reason(evidence)
        if gap:
            clauses.append(gap)

    clauses.append(
        "Every assessment above is based only on what OKX still publishes for this "
        "bot; the trade-level data (profit factor, deferred loss, phase analysis, "
        "PSR/DSR) still cannot be read because the bot does not publish its ledger"
    )

    if not clauses:
        return None
    return ". ".join(clauses) + "."


def measured_component_evidence(result: Any) -> List[Dict[str, Any]]:
    """Bằng chứng thô của MỌI chiều đã đo được, theo thứ tự rủi ro giảm dần.

    VÌ SAO CẦN: `narrative_paragraph` ở trên dệt một đoạn văn từ một tập
    luồng ĐƯỢC LIỆT KÊ SẴN (hồ sơ + thống kê ngày + sụt vốn tuần + trạng
    thái mô phỏng). Hệ quả đo được trên trang thật: chiều `return_path`
    (dựng từ chuỗi `pnlRatios` 19 điểm) hiện ra một thanh điểm 39 nhưng
    toàn bộ bằng chứng của nó -- "19 điểm lợi nhuận tích luỹ, 11 kỳ tăng /
    3 kỳ giảm", "thụt lùi sâu nhất 12,1% so với đỉnh" -- không xuất hiện ở
    bất kỳ đâu. Người đọc thấy một con số không có căn cứ đi kèm, đúng thứ
    báo cáo này không được phép có.

    Hàm này đọc thẳng từ `evidence.components` nên MỌI chiều thêm về sau tự
    động hiện bằng chứng, không cần ai nhớ cập nhật một danh sách thứ hai.
    Chỉ lấy chiều `AVAILABLE`: chiều bị che đã có khối giải thích riêng nói
    vì sao không đo được, lặp lại ở đây chỉ làm loãng.
    """
    evidence = _mapping(_mapping(result).get("evidence"))
    components = evidence.get("components")
    if not isinstance(components, list):
        return []
    rows: List[Dict[str, Any]] = []
    for component in components:
        if not isinstance(component, Mapping):
            continue
        if component.get("status") != "AVAILABLE":
            continue
        findings = [
            item
            for item in (component.get("findings") or [])
            if isinstance(item, str) and item.strip()
        ]
        if not findings:
            continue
        score = component.get("score")
        rows.append(
            {
                # `_Component.to_dict()` trong `analysis/limited.py` ghi nhãn hiển thị
                # dưới khoá "label", KHÔNG phải "label_vi" -- đọc sai khoá nên
                # phép tra luôn trượt và rơi về `name`, tức tên máy
                # ("return_path") hiện ra thay cho nhãn người đọc.
                "label": component.get("label") or component.get("name") or "—",
                "score": float(score) if isinstance(score, (int, float)) else None,
                "confidence": component.get("confidence"),
                "findings": findings,
            }
        )
    rows.sort(key=lambda row: (row["score"] is None, -(row["score"] or 0.0)))
    return rows
