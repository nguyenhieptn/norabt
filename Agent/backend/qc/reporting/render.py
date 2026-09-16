from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence

from Agent.backend.qc.reporting.cohort import BotEvaluationRow, CohortReport
from Agent.backend.qc.reporting.market_report import MarketRegimeReport
from Agent.backend.qc.reporting.reasons import (
    TIER_VI,
    computed_summary_vi,
    phase_vi,
    recommendation_vi,
    explain_vi,
    score_story_vi,
)


def _stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%d/%m/%Y %H:%M UTC"
    )


def display_width(text: str) -> int:
    """Vietnamese and CJK glyphs take two cells in most terminals."""
    return sum(2 if ord(c) > 0x2E80 else 1 for c in str(text))


def _cell(value: Optional[object], width: int, decimals: Optional[int] = None) -> str:
    if value is None:
        text = "—"
    elif decimals is not None and isinstance(value, (int, float)):
        text = f"{value:,.{decimals}f}"
    else:
        text = str(value)
    # Vietnamese and CJK glyphs are wider than one cell in most terminals.
    pad = width - display_width(text)
    if pad < 0:
        while text and pad < 0:
            dropped = text[-1]
            text = text[:-1]
            pad += 2 if ord(dropped) > 0x2E80 else 1
        text += "…"
        pad -= 1
    return text + " " * max(pad, 0)


def _header(columns: Sequence[tuple], title: str, subtitle: str) -> List[str]:
    line = " ".join(_cell(name, width) for name, width in columns)
    rule = "=" * len(line)
    return [rule, title, subtitle, rule, line, "-" * len(line)]


# ---------------------------------------------------------------- REPORT 1
MARKET_COLUMNS = (
    ("ASSET", 12),
    ("TƯ THẾ", 16),
    ("CHẾ ĐỘ THỊ TRƯỜNG", 30),
    ("THANH KHOẢN", 13),
    ("DÒNG TIỀN", 14),
    ("ATR%", 7),
    ("VỊ TRÍ BIÊN", 12),
    ("CHẤT LƯỢNG", 11),
    ("BOT", 4),
    ("ĐỦ ĐK", 7),
)


def render_market_report(report: MarketRegimeReport, detail: bool = True) -> str:
    lines = _header(
        MARKET_COLUMNS,
        "BƯỚC 2.1 — PHÂN TÍCH THỊ TRƯỜNG (CHẾ ĐỘ VÀ TƯ THẾ)",
        f"{_stamp(report.generated_at_ms)} | Quan sát {report.markets_observed} thị trường | "
        f"Đạt điều kiện giám sát {report.markets_eligible}",
    )
    for row in report.rows:
        lines.append(
            " ".join(
                [
                    _cell(f"{row.symbol}/{row.venue_type}", 12),
                    _cell(row.posture, 16),
                    _cell(row.regime, 30),
                    _cell(row.liquidity_tier, 13),
                    _cell(row.flow_bias, 14),
                    _cell(row.atr_pct, 7, 2),
                    _cell(row.range_position_pct, 12, 0),
                    _cell(row.data_quality * 100, 11, 0),
                    _cell(row.bots_trading, 4),
                    _cell("có" if row.eligible else "không", 7),
                ]
            )
        )
    lines.append("-" * len(lines[4]))
    lines.append(
        "Phân bố tư thế: "
        + " | ".join(
            f"{k}: {v}"
            for k, v in sorted(report.posture_summary.items(), key=lambda kv: -kv[1])
        )
    )
    lines.append(
        "Phân bố chế độ: "
        + " | ".join(
            f"{k}: {v}"
            for k, v in sorted(report.regime_summary.items(), key=lambda kv: -kv[1])
        )
    )
    if detail:
        lines.append("")
        lines.append("DIỄN GIẢI TỪNG THỊ TRƯỜNG")
        lines.append("=" * len(lines[4]))
        for row in report.rows:
            lines.append(f"[{row.symbol}/{row.venue_type}] {row.note}")
            if row.posture_evidence:
                lines.append(f"    {row.posture} vì: {'; '.join(row.posture_evidence)}")
            if row.missing_sources:
                lines.append(f"    Nguồn còn thiếu: {', '.join(row.missing_sources)}")
    return "\n".join(lines)


# ---------------------------------------------------------------- REPORT 2
BOT_COLUMNS = (
    ("BOT", 22),
    ("ASSET", 11),
    ("LỆNH", 6),
    ("WIN%", 6),
    ("PF SỔ", 7),
    ("PF CHỐT", 8),
    ("SỤT VỐN", 9),
    ("VỊ THẾ", 7),
    ("EXPOSURE", 11),
    ("LỖ CHƯA CHỐT", 14),
)


def render_bot_report(report: CohortReport, detail: bool = True) -> str:
    rows = sorted(report.rows, key=lambda r: (r.traded_symbol, r.nick_name))
    lines = _header(
        BOT_COLUMNS,
        "BƯỚC 2 — PHÂN TÍCH TỪNG BOT THEO ASSET ĐANG TRADE",
        f"{_stamp(report.generated_at_ms)} | {report.distinct_bots} bot | "
        f"Số liệu thuần quan sát, chưa phải phán quyết rủi ro",
    )
    current = None
    for row in rows:
        if row.traded_symbol != current:
            current = row.traded_symbol
        lines.append(
            " ".join(
                [
                    _cell(row.nick_name, 22),
                    _cell(f"{row.traded_symbol}/{row.venue_type}", 11),
                    _cell(row.trade_count, 6),
                    _cell(row.win_rate, 6, 0),
                    _cell(row.profit_factor, 7, 2),
                    _cell(row.marked_profit_factor, 8, 2),
                    _cell(
                        f"{row.max_drawdown_pct:.1f}%"
                        if row.max_drawdown_pct is not None
                        else (
                            f"{row.max_drawdown_abs / 1000:,.0f}k$"
                            if row.max_drawdown_abs
                            else None
                        ),
                        9,
                    ),
                    _cell(row.open_positions, 7),
                    _cell(
                        f"{row.gross_exposure / 1000:,.0f}k$"
                        if row.gross_exposure
                        else None,
                        11,
                    ),
                    _cell(
                        f"{row.open_loss / 1000:,.0f}k$"
                        if row.open_loss
                        else ("0" if row.open_loss == 0 else None),
                        14,
                    ),
                ]
            )
        )
    lines.append("-" * len(lines[4]))
    if detail:
        lines.append("")
        lines.append("CHI TIẾT QUAN SÁT")
        lines.append("=" * len(lines[4]))
        for row in rows:
            lines.append(f"[{row.nick_name}] giao dịch {row.traded_symbol}")
            lines.append(
                f"    Sổ lệnh: {row.trade_count} lệnh, đối soát {row.reconciliation_status}, "
                f"đo lường {row.measurement_mode}"
            )
            lines.append(
                f"    Nền vốn: {row.capital_basis}"
                + (f" ({row.capital_at_risk:,.0f} USDT)" if row.capital_at_risk else "")
            )
            if row.open_positions:
                lines.append(
                    f"    Vị thế: {row.open_positions} lệnh mở, "
                    f"{row.observed_positions_count} có instId, "
                    f"{row.inferred_positions_count} suy luận, "
                    f"{row.positions_outside_ledger_universe} ngoài sổ lệnh"
                )
            if row.loss_representativeness in ("PARTIAL", "UNREPRESENTATIVE"):
                lines.append(
                    f"    Lỗ hoãn nhận: {row.loss_representativeness}, "
                    f"{row.open_loss:,.0f} USDT chưa chốt"
                )
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- REPORT 3
QC_COLUMNS = (
    ("#", 3),
    ("TÊN BOT", 21),
    ("ASSET", 10),
    ("TRADE", 6),
    ("WIN%", 5),
    ("PF SỔ", 6),
    ("PF CHỐT", 8),
    ("SỤT VỐN", 8),
    ("P95 ĐUÔI", 9),
    ("RỦI RO", 7),
    ("CHẤT LG", 8),
    ("XẾP LOẠI", 14),
    ("NHẬN XÉT", 46),
)

# Ordered worst first, which is the order the table is read in.
VERDICT_ORDER = {"NGUY HIỂM": 0, "TIỀM ẨN": 1, "AN TOÀN": 2, "TIỀM NĂNG": 3}


def _wrap(text: str, width: int, indent: str) -> List[str]:
    """Wrap on word boundaries; the cause text must never be cut mid-sentence."""
    out: List[str] = []
    line = ""
    for word in str(text).split():
        candidate = f"{line} {word}".strip()
        if display_width(candidate) > width and line:
            out.append(indent + line)
            line = word
        else:
            line = candidate
    if line:
        out.append(indent + line)
    return out


def render_qc_ranking(report: CohortReport) -> str:
    lines = _header(
        QC_COLUMNS,
        "BƯỚC 3 — CHẤM ĐIỂM VÀ XẾP LOẠI BOT (QC CORE)",
        f"{_stamp(report.generated_at_ms)} | {report.distinct_bots} bot | "
        f"RỦI RO càng thấp càng an toàn · CHẤT LƯỢNG càng cao càng tốt",
    )
    ordered = sorted(
        report.rows,
        key=lambda r: (
            VERDICT_ORDER.get(r.verdict or "", 9),
            -(r.risk_score or 0.0),
            r.nick_name,
        ),
    )
    width = len(lines[4])
    for index, row in enumerate(ordered, 1):
        drawdown = (
            f"{row.max_drawdown_pct:.1f}%" if row.max_drawdown_pct is not None else "—"
        )
        tail = (
            f"{row.p95_max_drawdown:.0f}%"
            if getattr(row, "p95_max_drawdown", None) is not None
            else "—"
        )
        lines.append(
            " ".join(
                [
                    _cell(index, 3),
                    _cell(row.nick_name, 21),
                    _cell(f"{row.traded_symbol}/{row.venue_type}", 10),
                    _cell(row.trade_count, 6),
                    _cell(row.win_rate, 5, 0),
                    _cell(row.profit_factor, 6, 2),
                    _cell(row.marked_profit_factor, 8, 2),
                    _cell(drawdown, 8),
                    _cell(tail, 9),
                    _cell(row.risk_score, 7, 1),
                    _cell(row.quality_score, 8, 1),
                    _cell(row.verdict, 14),
                    _cell(row.verdict_reason, 46),
                ]
            )
        )
        # The reasons are the point of the row, so they wrap rather than truncate.
        computed = computed_summary_vi(row)
        if computed:
            lines.extend(_wrap(f"↳ tính toán: {computed}", width - 6, "     "))
        cause = explain_vi(row)
        if cause:
            lines.extend(_wrap(f"↳ nguyên nhân: {cause}", width - 6, "     "))
        if row.hidden_risk_flags:
            lines.extend(
                _wrap(
                    "↳ rủi ro bị che: " + "; ".join(row.hidden_risk_flags),
                    width - 6,
                    "     ",
                )
            )
        if row.recommended_action:
            lines.append(f"     ↳ đề xuất: {row.recommended_action}")
    lines.append("-" * width)
    verdicts: dict = {}
    for row in report.rows:
        verdicts[row.verdict or "?"] = verdicts.get(row.verdict or "?", 0) + 1
    lines.append(
        "Phân loại: "
        + " | ".join(
            f"{k}: {v}"
            for k, v in sorted(
                verdicts.items(), key=lambda kv: VERDICT_ORDER.get(kv[0], 9)
            )
        )
    )
    lines.append(
        "Phân bố hạng rủi ro: "
        + " | ".join(
            f"{TIER_VI.get(k, k)}: {v}"
            for k, v in sorted(report.tier_summary.items(), key=lambda kv: -kv[1])
        )
    )
    lines.append("")
    lines.append("PHIẾU ĐÁNH GIÁ TỪNG BOT")
    lines.append("=" * width)
    for index, row in enumerate(ordered, 1):
        lines.extend(_bot_card(index, row, width))
    return "\n".join(lines)


def _bot_card(index: int, row, width: int) -> List[str]:
    """One bot, told as a verdict a person can act on.

    The table above gives the numbers; this says what they mean. Written for a
    reader who wants to know whether to copy this bot, not for someone auditing
    the maths -- so every figure quoted is one that changed the conclusion.
    """
    num = lambda v, d=2: "—" if v is None else f"{v:,.{d}f}"  # noqa: E731
    pct = lambda v: "—" if v is None else f"{v:+.1f}%"  # noqa: E731
    prob = lambda v: "—" if v is None else f"{v:.0f}%"  # noqa: E731

    lines = [
        f"[{index}] {row.nick_name} — {row.traded_symbol}/{row.venue_type}",
        f"     XẾP LOẠI: {row.verdict}"
        f"   ·   ĐIỂM NGON: {num(row.quality_score, 1)}/100"
        f"   ·   ĐIỂM RỦI RO: {num(row.risk_score, 1)}/100 (càng thấp càng an toàn)"
        f"   ·   ĐỀ XUẤT: {row.recommended_action}",
        f"     Độ tin cậy của đánh giá: {num(row.confidence, 0)}%"
        f" · đối soát sổ lệnh {row.reconciliation_status}"
        f" · chế độ đo {row.measurement_mode}",
        "",
    ]

    # 1. What the bot actually is.
    book = []
    if row.trade_count is not None:
        book.append(f"{row.trade_count} lệnh đã chốt")
    if row.win_rate is not None:
        book.append(f"thắng {row.win_rate:.0f}%")
    if row.profit_factor is not None:
        book.append(f"profit factor {row.profit_factor:.2f}")
    if row.total_pnl is not None:
        book.append(f"tổng lãi/lỗ {row.total_pnl:,.0f} USDT")
    if row.sharpe_ratio is not None:
        book.append(f"Sharpe {row.sharpe_ratio:.2f}")
    if row.max_drawdown_pct is not None:
        book.append(f"sụt vốn sâu nhất {row.max_drawdown_pct:.1f}%")
    lines.extend(_wrap("THÔNG SỐ CỦA BOT: " + " · ".join(book), width - 6, "     "))

    holding = []
    if row.open_positions:
        holding.append(f"{row.open_positions} vị thế đang mở")
    if row.gross_exposure:
        holding.append(f"exposure {row.gross_exposure:,.0f} USDT")
    if row.leverage:
        holding.append(f"đòn bẩy {row.leverage:.0f}x")
    if row.open_loss:
        holding.append(f"lỗ chưa chốt {row.open_loss:,.0f} USDT")
    if row.capital_at_risk:
        holding.append(f"vốn tham chiếu {row.capital_at_risk:,.0f} USDT")
    if holding:
        lines.extend(_wrap("ĐANG NẮM GIỮ: " + " · ".join(holding), width - 6, "     "))

    # 2. What the simulation says could happen next.
    if row.mc_iterations and row.mc_horizon:
        sim = (
            f"CHẠY MÔ PHỎNG {row.mc_iterations:,} kịch bản × {row.mc_horizon} lệnh "
            f"(bootstrap từ chính sổ lệnh đã chốt của bot): "
            f"trung vị lãi {pct(row.profit_pct_p50)} trên vốn, "
            f"kịch bản tốt (p95) {pct(row.profit_pct_p95)}, "
            f"kịch bản xấu (p05) {pct(row.profit_pct_p05)}, "
            f"XẤU NHẤT {pct(row.profit_pct_worst)}. "
            f"Sụt vốn P95 {prob(row.p95_max_drawdown)}, xấu nhất "
            f"{prob(row.worst_drawdown)}. "
            f"Xác suất thua lỗ {prob(row.p_loss_after_horizon)}, "
            f"xác suất cháy tài khoản {prob(row.p_ruin)}."
        )
        lines.extend(_wrap(sim, width - 6, "     "))

    # 3. Whether the edge behind those numbers is real.
    if row.psr is not None:
        parts = [
            f"KIỂM ĐỊNH THỐNG KÊ: xác suất Sharpe thật lớn hơn 0 là "
            f"{row.psr * 100:.1f}%"
        ]
        if not row.inference_reliable:
            parts.append(
                " (con số này không đáng tin vì vài lệnh đơn lẻ đang chi phối "
                "độ lệch và đuôi phân phối)"
            )
        if row.deflated_sharpe is not None and row.selection_trials:
            parts.append(
                f"; sau khi trừ việc bot này được chọn là con tốt nhất trong "
                f"{row.selection_trials} ứng viên cùng asset, xác suất còn "
                f"{row.deflated_sharpe * 100:.1f}%"
            )
        if row.min_track_record_trades and row.trade_count:
            need = row.min_track_record_trades
            have = row.trade_count
            parts.append(
                f". Cần tối thiểu {need:,.0f} lệnh để tin được thành tích này, "
                f"bot đang có {have}"
                + (" — đã đủ" if have >= need else f" — còn thiếu {need - have:,.0f}")
            )
        lines.extend(_wrap("".join(parts), width - 6, "     "))

    # 4. The recommendation in prose. This is what a trading agent reads; the
    # numbers above are the attachment, not the message.
    lines.append("")
    lines.append("     ĐÁNH GIÁ VÀ KHUYẾN NGHỊ:")
    previous_was_bullet = False
    for paragraph in recommendation_vi(row):
        if paragraph.startswith("• "):
            # A bullet that wraps flush with its own marker stops looking like
            # a list, so continuation lines hang under the text.
            wrapped = _wrap(paragraph[2:], width - 12, "")
            lines.append("       • " + wrapped[0])
            lines.extend("         " + line for line in wrapped[1:])
            previous_was_bullet = True
            continue
        if previous_was_bullet:
            lines.append("")
        lines.extend(_wrap(paragraph, width - 8, "       "))
        # The list header belongs against its list, not floating above a gap.
        if not paragraph.endswith(":"):
            lines.append("")
        previous_was_bullet = False

    lines.extend(
        _wrap(f"VÌ SAO XẾP LOẠI NÀY: {row.verdict_reason}", width - 6, "     ")
    )
    cause = explain_vi(row)
    if cause:
        lines.extend(_wrap(f"VÌ SAO RỦI RO: {cause}", width - 6, "     "))
    if row.hidden_risk_flags:
        lines.extend(
            _wrap(
                "RỦI RO BỊ CHE SAU SỐ ĐẸP: " + "; ".join(row.hidden_risk_flags),
                width - 6,
                "     ",
            )
        )
    lines.extend(_wrap(score_story_vi(row), width - 6, "     "))
    for item in row.raised_the_score[:4]:
        lines.append(f"       + {item}")
    for item in row.held_the_score_down[:4]:
        lines.append(f"       − {item}")
    lines.append("")
    return lines


def render_text(report: CohortReport, detail: bool = True) -> str:
    """Giữ tương thích: mặc định trả báo cáo xếp hạng."""
    return render_qc_ranking(report)


def render_gaps(report: CohortReport) -> str:
    if not report.gaps:
        return ""
    lines = ["THIẾU DỮ LIỆU — VIỆC CẦN THU THẬP", "=" * 100]
    for gap in report.gaps:
        who = (
            f" | Ảnh hưởng: {', '.join(gap.affected_bots)}" if gap.affected_bots else ""
        )
        lines.append(f"[{gap.priority:6s}] {gap.scope} — {gap.evidence}")
        lines.append(f"    {gap.detail}")
        lines.append(f"    Mở khóa: {', '.join(gap.unlocks) or '—'}{who}")
    return "\n".join(lines)


__all__ = [
    "render_market_report",
    "render_bot_report",
    "render_qc_ranking",
    "render_gaps",
    "render_text",
    "BotEvaluationRow",
]


BIAS_VI = {
    "LONG_ONLY": "chỉ long",
    "SHORT_ONLY": "chỉ short",
    "LONG_TILTED": "nghiêng long",
    "SHORT_TILTED": "nghiêng short",
    "TWO_WAY": "hai chiều",
    "UNKNOWN": "chưa rõ",
}
STYLE_VI = {
    "TREND_FOLLOWING": "thuận xu hướng",
    "MEAN_REVERSION": "nghịch xu hướng",
    "MIXED": "pha trộn",
    "UNKNOWN": "chưa đủ dữ liệu",
}


def render_pair_report(report, detail: bool = True) -> str:
    """Step 2, one block per asset: the market, then the pair that trades it."""
    lines = [
        "=" * 118,
        "BƯỚC 2.2 — PHÂN TÍCH VÀ MÔ PHỎNG TỪNG BOT",
        f"{_stamp(report.generated_at_ms)} | {report.slots} asset | "
        f"{report.bots_evaluated} bot phân tích được"
        + (f", {report.bots_failed} bot lỗi" if report.bots_failed else "")
        + " | Số liệu quan sát, chưa phải phán quyết rủi ro",
        "=" * 118,
    ]

    # Two tables, because they answer different questions: what the bot did,
    # and what could happen next. One combined row carried twenty columns and
    # stopped being readable.
    perf_width = 135
    lines += [
        "",
        f"BẢNG A — HIỆU SUẤT ĐÃ THỰC HIỆN ({report.slots} ASSET · "
        f"{report.bots_evaluated} BOT)",
        "-" * perf_width,
        _cell("ASSET", 10)
        + _cell("VAI", 10)
        + _cell("BOT", 20)
        + _cell("TRADE", 6)
        + _cell("WIN%", 5)
        + _cell("PROFIT", 12)
        + _cell("PF SỔ", 6)
        + _cell("PF CHỐT", 8)
        + _cell("MDD", 8)
        + _cell("SHARPE", 7)
        + _cell("LỖ MỞ", 8)
        + _cell("HƯỚNG", 14)
        + "KIỂU VÀO",
        "-" * perf_width,
    ]
    for block in report.blocks:
        for position, bot in enumerate(block.bots):
            asset_cell = f"{block.venue_type}/{block.symbol}" if not position else ""
            if bot.error:
                lines.append(
                    _cell(asset_cell, 10)
                    + _cell(bot.role, 10)
                    + _cell(bot.nick_name, 20)
                    + f"LỖI: {bot.error}"
                )
                continue
            dd = (
                f"{bot.max_drawdown_pct:.1f}%"
                + ("*" if bot.max_drawdown_capped else "")
                if bot.max_drawdown_pct is not None
                else "—"
            )
            lines.append(
                _cell(asset_cell, 10)
                + _cell(bot.role, 10)
                + _cell(bot.nick_name, 20)
                + _cell(bot.trade_count, 6)
                + _cell(bot.win_rate, 5, 0)
                + _cell(
                    f"{bot.ledger_pnl:,.0f}" if bot.ledger_pnl is not None else "—", 12
                )
                + _cell(bot.profit_factor, 6, 2)
                + _cell(bot.marked_profit_factor, 8, 2)
                + _cell(dd, 8)
                + _cell(bot.sharpe_ratio, 7, 2)
                + _cell(f"{bot.open_loss / 1000:,.0f}k$" if bot.open_loss else "0", 8)
                + _cell(BIAS_VI.get(bot.directional_bias, bot.directional_bias), 14)
                + STYLE_VI.get(bot.entry_style, bot.entry_style)
            )
    lines += [
        "-" * perf_width,
        "PROFIT = PnL sổ đã chốt · PF CHỐT = profit factor nếu chốt hết vị thế đang "
        "mở · MDD có dấu * = vượt vốn ghi nhận nên là sàn",
    ]

    mc_width = 158
    lines += [
        "",
        "BẢNG B — MÔ PHỎNG MONTE CARLO VÀ ĐÁNH GIÁ RỦI RO",
        "10.000 kịch bản/bot · stationary bootstrap (Politis-Romano 1994) · mỗi "
        "kịch bản replay đúng số lệnh "
        "của chính bot · chỉ lệnh ĐÃ CHỐT",
        "-" * mc_width,
        _cell("ASSET", 10)
        + _cell("BOT", 20)
        + _cell("LN xấu nhất", 12)
        + _cell("LN t.vị", 9)
        + _cell("LN p95", 9)
        + _cell("CVaR95", 9)
        + _cell("DD t.vị", 9)
        + _cell("DD p95", 8)
        + _cell("MAR", 7)
        + _cell("P(lãi)", 7)
        + _cell("P(cháy)", 8)
        + _cell("PSR", 7)
        + _cell("DSR", 7)
        + "MinTRL",
        "-" * mc_width,
    ]
    for block in report.blocks:
        for position, bot in enumerate(block.bots):
            if bot.error or not bot.mc_iterations:
                continue
            pct = lambda v: "—" if v is None else f"{v:+.1f}%"  # noqa: E731
            prob = lambda v: "—" if v is None else f"{v:.0f}%"  # noqa: E731
            prb = lambda v: "—" if v is None else f"{v:.3f}"  # noqa: E731
            trl = (
                f"{bot.min_track_record_trades:,.0f} (có {bot.mc_sample_size})"
                if bot.min_track_record_trades
                else "—"
            )
            lines.append(
                _cell(f"{block.venue_type}/{block.symbol}" if not position else "", 10)
                + _cell(bot.nick_name, 20)
                + _cell(pct(bot.mc_profit_worst_pct), 12)
                + _cell(pct(bot.mc_profit_p50_pct), 9)
                + _cell(pct(bot.mc_profit_p95_pct), 9)
                + _cell(
                    pct(-bot.cvar_95_pct) if bot.cvar_95_pct is not None else "—", 9
                )
                + _cell(prob(bot.mc_median_drawdown), 9)
                + _cell(prob(bot.mc_p95_drawdown), 8)
                + _cell(
                    f"{bot.mar_ratio_median:.1f}"
                    if bot.mar_ratio_median is not None
                    else "—",
                    7,
                )
                + _cell(prob(bot.probability_of_profit), 7)
                + _cell(prob(bot.mc_p_ruin), 8)
                + _cell(prb(bot.psr) + ("" if bot.inference_reliable else "?"), 7)
                + _cell(prb(bot.deflated_sharpe), 7)
                + trl
            )
    lines += [
        "-" * mc_width,
        f"Tổng: {report.slots} asset · {report.bots_evaluated} bot"
        + (f" · {report.bots_failed} bot lỗi" if report.bots_failed else ""),
        "LN = lợi nhuận trên vốn · CVaR95 = lỗ trung bình trong 5% kịch bản tệ nhất "
        "· MAR = lợi nhuận chia sụt vốn",
        "PSR = xác suất Sharpe thật > 0 sau khi tính độ dài mẫu, độ lệch và đuôi dày; "
        "dấu ? = mô men do vài lệnh đơn lẻ chi phối nên không đáng tin",
        "DSR = PSR sau khi trừ việc bot được chọn là con tốt nhất trong pool ứng viên "
        "· MinTRL = số lệnh tối thiểu để Sharpe đủ tin ở mức 95%",
        "(Bailey & López de Prado 2012, 2014)",
        "",
        "CHI TIẾT TỪNG ASSET",
    ]

    for block in report.blocks:
        lines.append("")
        market = (
            f"{block.market_posture} · {block.market_trend}/{block.market_volatility}"
            f" · thanh khoản {block.market_liquidity}"
            f" · chất lượng dữ liệu {block.market_quality:.2f}"
            if block.market_available
            else f"KHÔNG DỰNG ĐƯỢC THỊ TRƯỜNG: {block.market_error}"
        )
        lines.append(f"── {block.venue_type}/{block.symbol} ── {market}")
        if block.market_evidence:
            lines.append(f"   Vì: {'; '.join(block.market_evidence)}")

        lines.append(
            "   "
            + _cell("VAI", 10)
            + _cell("BOT", 21)
            + _cell("lệnh", 6)
            + _cell("/asset", 7)
            + _cell("win%", 6)
            + _cell("PF sổ", 7)
            + _cell("PF chốt", 8)
            + _cell("sụt vốn", 9)
            + _cell("vị thế", 7)
            + _cell("lỗ mở", 9)
            + "CHIẾN LƯỢC"
        )
        for bot in block.bots:
            if bot.error:
                lines.append(
                    "   "
                    + _cell(bot.role, 10)
                    + _cell(bot.nick_name, 21)
                    + f"LỖI: {bot.error}"
                )
                continue
            dd = (
                f"{bot.max_drawdown_pct:.1f}%"
                + ("*" if bot.max_drawdown_capped else "")
                if bot.max_drawdown_pct is not None
                else "—"
            )
            strategy = (
                f"{BIAS_VI.get(bot.directional_bias, bot.directional_bias)}, "
                f"{STYLE_VI.get(bot.entry_style, bot.entry_style)}"
                f" · phủ pha {bot.phase_coverage_pct:.0f}%"
                if bot.phase_coverage_pct is not None
                else BIAS_VI.get(bot.directional_bias, bot.directional_bias)
            )
            lines.append(
                "   "
                + _cell(bot.role, 10)
                + _cell(bot.nick_name, 21)
                + _cell(bot.trade_count, 6)
                + _cell(bot.trades_on_asset, 7)
                + _cell(bot.win_rate, 6, 0)
                + _cell(bot.profit_factor, 7, 2)
                + _cell(bot.marked_profit_factor, 8, 2)
                + _cell(dd, 9)
                + _cell(bot.open_positions, 7)
                + _cell(f"{bot.open_loss / 1000:,.0f}k$" if bot.open_loss else "0", 9)
                + strategy
            )

        if detail:
            for bot in block.bots:
                if bot.error or not bot.phase_rows:
                    continue
                num = lambda v, d=2: "—" if v is None else f"{v:,.{d}f}"  # noqa: E731
                lines.append(f"   · {bot.nick_name} — thông số đầy đủ:")
                lines.append(
                    "       hiệu suất:      "
                    f"kỳ vọng {num(bot.expectancy)}/lệnh"
                    f" · payoff {num(bot.payoff_ratio)}"
                    f" · lãi TB {num(bot.average_win)} / lỗ TB {num(bot.average_loss)}"
                    f" · tổng PnL {num(bot.ledger_pnl, 0)}"
                )
                lines.append(
                    "       hiệu chỉnh RR:  "
                    f"Sharpe {num(bot.sharpe_ratio)}"
                    f" · Sortino {num(bot.sortino_ratio)}"
                    f" · Calmar {num(bot.calmar_ratio)}"
                    f" · hồi phục {num(bot.recovery_factor)}"
                )
                lines.append(
                    "       nhịp giao dịch: "
                    f"{num(bot.trades_per_day)} lệnh/ngày"
                    f" · giữ lệnh trung vị {num(bot.median_hold_minutes, 0)} phút"
                    f" · chuỗi thắng dài nhất {bot.max_win_streak}"
                    f" · chuỗi thua dài nhất {bot.max_loss_streak}"
                )
                ci = (
                    f"[{bot.mean_pnl_ci[0]:,.0f}; {bot.mean_pnl_ci[1]:,.0f}]"
                    if bot.mean_pnl_ci and len(bot.mean_pnl_ci) == 2
                    else "—"
                )
                lines.append(
                    "       phân phối lệnh: "
                    f"trung vị {num(bot.pnl_median, 0)}"
                    f" · độ lệch chuẩn {num(bot.pnl_std, 0)}"
                    f" · skew {num(bot.pnl_skew)}"
                    f" · kurtosis {num(bot.pnl_kurtosis)}"
                    f" · p05 {num(bot.pnl_p05, 0)} / p95 {num(bot.pnl_p95, 0)}"
                    f" · KTC95 trung bình {ci}"
                )
                lines.append(
                    "       vốn và sổ:      "
                    f"vốn tham chiếu {num(bot.capital_at_risk, 0)}"
                    f" ({bot.capital_basis})"
                    f" · sổ phủ {num(bot.ledger_coverage_days, 0)}/"
                    f"{bot.declared_lead_days or '—'} ngày dẫn"
                    f" · đối soát {bot.reconciliation}"
                    f" · chế độ đo {bot.measurement_mode}"
                )
                if bot.stress_verdict:
                    lines.append(
                        "       stress tất định:"
                        f" biến động ×2 {num(bot.stress_volatility_2x, 0)}"
                        f" · spread ×3 {num(bot.stress_spread_3x, 0)}"
                        f" · thanh khoản ½ {num(bot.stress_liquidity_half, 0)}"
                        f" → {bot.stress_verdict}"
                    )
                lines.append("     theo pha thị trường:")
                for row in bot.phase_rows:
                    win = row.get("win_rate")
                    share = row.get("profit_share_pct")
                    lines.append(
                        "       "
                        + _cell(phase_vi(row["phase"]), 16)
                        + _cell(f"{row['trades']} lệnh", 10)
                        + _cell(f"win {win:.0f}%" if win is not None else "win —", 9)
                        + _cell(f"PnL {row['total_pnl']:,.0f}", 18)
                        + (
                            # Share of GROSS wins, which a net-losing phase can
                            # still hold a lot of; saying "chiếm x% lợi nhuận"
                            # there would read as if the phase made money.
                            (
                                f"góp {share:.0f}% lãi gộp"
                                + (" nhưng lỗ ròng" if row["total_pnl"] < 0 else "")
                            )
                            if share is not None
                            else "không có lãi gộp"
                        )
                    )
                if bot.mc_iterations:
                    draws = bot.mc_iterations * (bot.mc_horizon or 0)
                    lines.append(
                        f"       Monte Carlo: {bot.mc_iterations:,} kịch bản × "
                        f"{bot.mc_horizon} lệnh = {draws:,} lượt bốc"
                        + "  · phạm vi: chỉ lệnh ĐÃ CHỐT"
                        + (
                            f", bot đang giữ {bot.open_loss / 1000:,.0f}k$ lỗ chưa "
                            "chốt nằm ngoài mô phỏng"
                            if bot.mc_deferred_loss_bias and bot.open_loss
                            else ""
                        )
                    )
                    fmt = lambda v: "—" if v is None else f"{v:+.1f}%"  # noqa: E731
                    lines.append(
                        "       lợi nhuận/vốn:  "
                        + f"xấu nhất {fmt(bot.mc_profit_worst_pct)}"
                        + f" · p05 {fmt(bot.mc_profit_p05_pct)}"
                        + f" · trung vị {fmt(bot.mc_profit_p50_pct)}"
                        + f" · p95 {fmt(bot.mc_profit_p95_pct)}"
                        + f" · tốt nhất {fmt(bot.mc_profit_best_pct)}"
                    )
                    lines.append(
                        "       sụt vốn:        " + f"P95 {bot.mc_p95_drawdown:.1f}%"
                        if bot.mc_p95_drawdown is not None
                        else "       sụt vốn:        —"
                    )
                    lines[-1] += (
                        f" · xấu nhất {bot.mc_worst_drawdown:.1f}%"
                        if bot.mc_worst_drawdown is not None
                        else ""
                    )
                    lines[-1] += (
                        f" · xác suất cháy {bot.mc_p_ruin:.1f}%"
                        if bot.mc_p_ruin is not None
                        else ""
                    )
                    lines[-1] += (
                        f" · xác suất lỗ {bot.mc_p_loss:.1f}%"
                        if bot.mc_p_loss is not None
                        else ""
                    )
                if bot.entry_style_evidence:
                    lines.append(
                        f"       căn cứ kiểu vào lệnh: {bot.entry_style_evidence}"
                    )
                if bot.untested_phases:
                    lines.append(
                        "       pha thị trường đã có nhưng bot chưa từng trải: "
                        + ", ".join(phase_vi(p) for p in bot.untested_phases)
                    )

        for note in block.comparison:
            lines.append(f"   → {note}")

    lines.append("")
    lines.append("-" * 118)
    lines.append("* = mức sụt vốn vượt vốn ghi nhận tại thời điểm đó, con số là sàn.")
    for note in report.notes:
        lines.append(f"· {note}")
    return "\n".join(lines)


def render_data_report(report) -> str:
    """Step 1: two inventories — the markets, then the bots."""
    lines = [
        "=" * 140,
        "BƯỚC 1 — DỮ LIỆU (KIỂM KÊ ĐẦU VÀO CHO MARKET VÀ BOT)",
        f"{_stamp(report.generated_at_ms)} | "
        f"{report.markets_complete}/{len(report.markets)} thị trường đủ nguồn | "
        f"{report.bots_complete}/{len(report.bots)} bot đủ dữ liệu",
        "=" * 140,
        "",
        f"BẢNG 1.1 — DỮ LIỆU THỊ TRƯỜNG ({len(report.markets)} ASSET)",
        "-" * 140,
        _cell("THỊ TRƯỜNG", 13)
        + _cell("NẾN 1H", 9)
        + _cell("NGUỒN ĐẠT", 11)
        + _cell("CHẤT LƯỢNG", 12)
        + "THIẾU / QUÁ HẠN",
        "-" * 140,
    ]
    for row in report.markets:
        if not row.available:
            lines.append(
                _cell(f"{row.venue_type}/{row.symbol}", 13)
                + f"KHÔNG DỰNG ĐƯỢC: {row.error}"
            )
            continue
        gaps = [f"thiếu {s}" for s in row.missing] + [f"cũ {s}" for s in row.stale]
        lines.append(
            _cell(f"{row.venue_type}/{row.symbol}", 13)
            + _cell(f"{row.candles:,}", 9)
            + _cell(f"{row.sources_ok}/{row.sources_total}", 11)
            + _cell(f"{row.quality:.2f}" if row.quality is not None else "—", 12)
            + ("; ".join(gaps) if gaps else "✓ đủ")
        )

    lines += [
        "-" * 140,
        "",
        f"BẢNG 1.2 — DỮ LIỆU BOT ({len(report.bots)} BOT)",
        "-" * 140,
        _cell("SLOT", 11)
        + _cell("VAI", 10)
        + _cell("BOT", 21)
        + _cell("LỆNH", 6)
        + _cell("/ASSET", 7)
        + _cell("VỊ THẾ", 7)
        + _cell("THIẾU inst", 11)
        + _cell("TUẦN", 6)
        + _cell("HỒ SƠ", 7)
        + _cell("HOẠT ĐỘNG", 11)
        + "CHẶN / GHI CHÚ",
        "-" * 140,
    ]
    for row in report.bots:
        if row.blocking and row.folder is None:
            lines.append(
                _cell(row.slot, 11)
                + _cell(row.role, 10)
                + _cell(row.nick_name, 21)
                + "CHƯA CRAWL"
            )
            continue
        status = "; ".join(f"CHẶN: {b}" for b in row.blocking)
        if row.notes:
            status = (status + " · " if status else "") + "; ".join(row.notes)
        lines.append(
            _cell(row.slot, 11)
            + _cell(row.role, 10)
            + _cell(row.nick_name, 21)
            + _cell(row.trades, 6)
            + _cell(row.trades_on_asset, 7)
            + _cell(row.open_positions, 7)
            + _cell(row.positions_without_instrument, 11)
            + _cell(row.weekly_points, 6)
            + _cell("có" if row.has_profile else "thiếu", 7)
            + _cell(
                f"{row.last_close_days:.1f}d"
                if row.last_close_days is not None
                else "—",
                11,
            )
            + (status or "✓ đủ")
        )

    lines.append("-" * 140)
    for note in report.notes:
        lines.append(f"· {note}")
    return "\n".join(lines)
