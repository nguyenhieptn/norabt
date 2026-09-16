from __future__ import annotations

from typing import List, Optional

DIMENSION_VI = {
    "market_alignment": "ngược xu hướng thị trường",
    "performance_quality": "chất lượng hiệu suất kém",
    "return_r_quality": "phân phối lợi nhuận xấu",
    "drawdown_risk": "sụt vốn sâu",
    "tail_risk": "rủi ro đuôi cao",
    "leverage_exposure": "đòn bẩy và exposure lớn",
    "behavioral_risk": "hành vi giao dịch nguy hiểm",
    "strategy_drift": "chiến lược không bền qua các pha thị trường",
    "liquidity_execution": "vị thế lớn so với thanh khoản",
    "portfolio_risk": "tập trung danh mục",
}

TREND_VI = {
    "BULLISH": "tăng",
    "BEARISH": "giảm",
    "SIDEWAYS": "đi ngang",
    "BREAKOUT_BULL": "phá lên",
    "BREAKOUT_BEAR": "phá xuống",
    "UNKNOWN": "chưa rõ",
}
VOL_VI = {
    "COMPRESSED": "biến động nén",
    "NORMAL": "biến động bình thường",
    "EXPANDING": "biến động mở rộng",
    "EXTREME": "biến động cực đoan",
    "UNKNOWN": "biến động chưa rõ",
}
LIQ_VI = {
    "DEEP": "thanh khoản sâu",
    "ADEQUATE": "thanh khoản đủ",
    "THIN": "thanh khoản mỏng",
    "ILLIQUID": "gần như cạn thanh khoản",
    "UNKNOWN": "thanh khoản chưa rõ",
}
FLOW_VI = {
    "BUY_PRESSURE": "áp lực mua",
    "SELL_PRESSURE": "áp lực bán",
    "NEUTRAL": "dòng tiền cân bằng",
    "UNKNOWN": "dòng tiền chưa rõ",
}
TIER_VI = {
    "EMERGENCY": "KHẨN CẤP",
    "CRITICAL": "NGHIÊM TRỌNG",
    "HIGH": "CAO",
    "ELEVATED": "NÂNG CAO",
    "WATCH": "THEO DÕI",
    "HEALTHY": "AN TOÀN",
    "UNKNOWN": "THIẾU BẰNG CHỨNG",
}


def regime_label_vi(trend: Optional[str], volatility: Optional[str]) -> str:
    if not trend or trend == "UNKNOWN":
        return "Chưa xác định được chế độ thị trường"
    return f"{TREND_VI.get(trend, trend).capitalize()}, {VOL_VI.get(volatility or 'UNKNOWN', '')}"


def explain_vi(row) -> str:
    """Nói rõ vì sao bot nhận thứ hạng này, bằng con số cụ thể."""
    causes: List[str] = []

    if row.status != "EVALUATED":
        return "Không đánh giá được vì dữ liệu đầu vào không hợp lệ."

    if row.wiped_out:
        causes.append(
            "đường vốn tuần từng chạm 0, tức tài khoản đã cháy ít nhất một lần"
        )

    if row.loss_representativeness == "UNREPRESENTATIVE" and row.open_loss:
        shift = ""
        if (
            row.booked_profit_factor is not None
            and row.marked_profit_factor is not None
        ):
            shift = (
                f", chốt hết thì PF tụt từ {row.booked_profit_factor:.2f} "
                f"xuống {row.marked_profit_factor:.2f}"
            )
        elif row.marked_profit_factor is not None:
            shift = (
                f", chưa từng chốt lỗ nên PF vô nghĩa; chốt hết thì PF chỉ còn "
                f"{row.marked_profit_factor:.2f}"
            )
        pct = (
            f" ({row.open_loss_to_capital_pct:.0f}% vốn)"
            if row.open_loss_to_capital_pct
            else ""
        )
        causes.append(f"đang ôm {row.open_loss:,.0f} USDT lỗ chưa chốt{pct}{shift}")

    if row.p_ruin and row.p_ruin >= 5.0:
        causes.append(f"xác suất cháy tài khoản {row.p_ruin:.0f}% trong 500 lệnh tới")

    scores = row.dimension_scores or {}
    for name, score in sorted(scores.items(), key=lambda kv: -kv[1]):
        if score < 60 or len(causes) >= 4:
            continue
        label = DIMENSION_VI.get(name, name)
        if name == "behavioral_risk":
            causes.append(f"{label} (điểm {score:.0f})")
        elif name == "drawdown_risk" and row.max_drawdown_pct is not None:
            causes.append(f"{label}: tối đa {row.max_drawdown_pct:.1f}%")
        elif name == "leverage_exposure" and row.leverage:
            causes.append(f"{label}: đòn bẩy {row.leverage:.0f}x")
        elif name == "market_alignment" and row.market:
            causes.append(
                f"{label} ({TREND_VI.get(row.market.trend, row.market.trend)})"
            )
        elif name == "tail_risk" and row.p95_max_drawdown is not None:
            causes.append(f"{label}: P95 sụt vốn {row.p95_max_drawdown:.0f}%")
        else:
            causes.append(f"{label} (điểm {score:.0f})")

    if not causes:
        if row.risk_tier == "UNKNOWN":
            missing = len(row.unknown_dimensions or [])
            return f"Không đủ bằng chứng để kết luận: {missing}/10 chiều đánh giá thiếu dữ liệu."
        return "Không có chiều rủi ro nào vượt ngưỡng cảnh báo."

    text = "; ".join(causes)
    if row.confidence is not None and row.confidence < 50:
        text += f". Độ tin cậy chỉ {row.confidence:.0f}% nên cần bổ sung bằng chứng trước khi hành động"
    return text[0].upper() + text[1:] + "."


def computed_summary_vi(row) -> str:
    """Kết quả tính toán cô đọng: điều gì đã được đo và ra số bao nhiêu."""
    if row.status != "EVALUATED":
        return "—"
    parts: List[str] = []
    if row.profit_factor is not None:
        if (
            row.marked_profit_factor is not None
            and row.loss_representativeness == "UNREPRESENTATIVE"
        ):
            parts.append(f"PF {row.profit_factor:.2f}→{row.marked_profit_factor:.2f}")
        else:
            parts.append(f"PF {row.profit_factor:.2f}")
    elif row.marked_profit_factor is not None:
        parts.append(f"PF —→{row.marked_profit_factor:.2f}")

    if row.max_drawdown_pct is not None:
        parts.append(f"DD {row.max_drawdown_pct:.1f}%")
    elif row.max_drawdown_abs:
        parts.append(f"DD {row.max_drawdown_abs / 1000:,.0f}k$")

    if row.p95_max_drawdown is not None:
        parts.append(f"P95 {row.p95_max_drawdown:.0f}%")
    # Chỉ nêu những con số có tín hiệu; số 0 chỉ làm loãng bảng.
    if row.p_ruin:
        parts.append(f"cháy {row.p_ruin:.0f}%")
    if row.open_loss:
        parts.append(f"lỗ mở {row.open_loss / 1000:,.0f}k$")
    if row.gross_exposure:
        parts.append(f"exp {row.gross_exposure / 1000:,.0f}k$")
    return " · ".join(parts) if parts else "chưa tính được"


def score_story_vi(row) -> str:
    """Giải thích con số: nó được tạo ra thế nào và cái gì chặn nó lại."""
    if row.risk_score is None:
        return "Chưa tính được điểm."
    avg = row.weighted_average
    floor = row.veto_floor
    decided = row.score_decided_by or "WEIGHTED_AVERAGE"

    if decided == "EMERGENCY_OVERRIDE":
        head = (
            f"Điểm {row.risk_score:.1f} là mức tối đa do quy tắc khẩn cấp, "
            f"bỏ qua bình quân {avg:.1f}"
        )
    elif decided == "VETO_FLOOR" and floor is not None:
        head = (
            f"Điểm {row.risk_score:.1f} đến từ sàn veto {floor:.0f}, không phải bình quân: "
            f"bình quân gia quyền 10 chiều chỉ {avg:.1f}"
        )
    else:
        head = (
            f"Điểm {row.risk_score:.1f} chính là bình quân gia quyền của các chiều "
            f"đánh giá, không có veto nào được kích hoạt"
        )
    if row.veto_reasons:
        head += f". Veto kích hoạt bởi: {'; '.join(row.veto_reasons)}"
    return head + "."


PHASE_VI = {
    "UPTREND_CALM": "Tăng, êm",
    "UPTREND_VOLATILE": "Tăng, động",
    "DOWNTREND_CALM": "Giảm, êm",
    "DOWNTREND_VOLATILE": "Giảm, động",
    "RANGE_CALM": "Đi ngang, êm",
    "RANGE_VOLATILE": "Đi ngang, động",
}


def phase_vi(name: Optional[str]) -> str:
    """Market-phase label in Vietnamese; unknown names pass through unchanged."""
    return PHASE_VI.get(name or "", name or "—")


ACTION_VI = {
    "EMERGENCY_STOP": "DỪNG NGAY, không copy trong mọi trường hợp",
    "PAUSE": "TẠM DỪNG copy cho tới khi bot tự xử lý xong phần rủi ro bên dưới",
    "REDUCE": "GIẢM tỷ trọng đang copy",
    "BLOCK_NEW_TRADES": "KHÔNG mở thêm, giữ nguyên phần đang có",
    "WARN": "THEO DÕI SÁT, chưa cần rút",
    "MONITOR": "CÓ THỂ COPY, theo dõi định kỳ",
}


def _money(value: Optional[float]) -> str:
    return "—" if value is None else f"{value:,.0f} USDT"


BIAS_TEXT_VI = {
    "LONG_ONLY": "chỉ một chiều long",
    "SHORT_ONLY": "chỉ một chiều short",
    "LONG_TILTED": "hai chiều nhưng nghiêng long",
    "SHORT_TILTED": "hai chiều nhưng nghiêng short",
    "TWO_WAY": "cả hai chiều",
    "UNKNOWN": "chưa xác định được chiều",
}
STYLE_TEXT_VI = {
    "TREND_FOLLOWING": "thuận theo biến động vừa xảy ra",
    "MEAN_REVERSION": "ngược lại biến động vừa xảy ra",
    "MIXED": "lúc thuận lúc ngược",
    "UNKNOWN": "chưa đủ dữ liệu để nói kiểu vào lệnh",
}


def _what_would_change_it(row) -> str:
    """Name the single condition that would move this bot out of its bucket.

    A verdict without an exit condition reads as permanent, and the agent
    reading it has no way to know when to look again.
    """
    if (
        row.marked_profit_factor is not None
        and row.profit_factor is not None
        and row.profit_factor >= 1.0 > row.marked_profit_factor
    ):
        return (
            "Điều kiện xem xét lại: bot chốt hết hoặc cắt phần lỗ đang treo, và "
            "profit factor sau khi chốt quay lên trên 1."
        )
    if (row.trade_count or 0) >= 20 and not row.tested_in_downtrend:
        return (
            "Điều kiện xem xét lại: bot chạy qua một pha thị trường giảm và giữ "
            "được kết quả."
        )
    if (
        row.min_track_record_trades
        and row.trade_count
        and row.trade_count < row.min_track_record_trades
    ):
        need = row.min_track_record_trades - row.trade_count
        return (
            f"Điều kiện xem xét lại: có thêm khoảng {need:,.0f} lệnh nữa để đủ cơ "
            "sở thống kê."
        )
    if row.regime_dependence_pct is not None and row.regime_dependence_pct >= 70:
        return (
            "Điều kiện xem xét lại: bot kiếm được lợi nhuận ở pha thị trường khác "
            "ngoài pha đang phụ thuộc."
        )
    if row.p_ruin and row.p_ruin >= 5:
        return (
            "Điều kiện xem xét lại: xác suất cháy tài khoản trong mô phỏng giảm "
            "xuống dưới 5%."
        )
    return ""


QUALITY_COMPONENT_VI = {
    "profitability": "sinh lời",
    "consistency": "ổn định",
    "drawdown_control": "kiểm soát sụt vốn",
    "honesty": "trung thực sổ sách",
    "robustness": "bền qua các chế độ",
}


def _surface(row) -> str:
    """What the bot looks like to someone who only reads the leaderboard."""
    bits = []
    if row.win_rate is not None:
        bits.append(f"thắng {row.win_rate:.0f}%")
    if row.profit_factor is not None:
        bits.append(f"profit factor {row.profit_factor:.2f}")
    if row.max_drawdown_pct is not None:
        bits.append(f"sụt vốn {row.max_drawdown_pct:.1f}%")
    return ", ".join(bits)


def _cause_story(row) -> str:
    """Why this bot got this verdict, argued in two or three sentences.

    A reader will only ever look at one bot for a few seconds, so the
    argument has to land in one breath: cơ chế (what the bot actually does)
    then hệ quả (what that does to a copier). Longer branches used to spell
    out the same point three times over; every branch here now makes it once
    and stops, trusting the bullets below to carry the supporting numbers.
    """
    name = row.nick_name
    surface = _surface(row)

    # The book is filtered: wins are closed, losses are left open.
    if (
        row.marked_profit_factor is not None
        and row.profit_factor is not None
        and row.profit_factor >= 1.0 > row.marked_profit_factor
    ):
        text = (
            f"Nhìn bảng thì {name} rất đẹp: {surface}. Nhưng đó chỉ là các lệnh "
            f"bot tự chọn đóng — bot đang giữ {_money(row.open_loss)} lỗ chưa chốt"
        )
        if row.open_loss_to_capital_pct:
            text += f" ({row.open_loss_to_capital_pct:.0f}% vốn)"
        text += (
            f", chốt hết thì PF tụt còn {row.marked_profit_factor:.2f}, từ lãi "
            "thành lỗ. Cơ chế là chốt lời sớm, ôm lỗ chờ gỡ; khi giá không quay "
            "lại, người copy ăn trọn cú hiện lỗ."
        )
        return text

    if row.open_loss_to_capital_pct and row.open_loss_to_capital_pct >= 20:
        return (
            f"{name} đang ôm {_money(row.open_loss)} lỗ chưa chốt, bằng "
            f"{row.open_loss_to_capital_pct:.0f}% vốn tham chiếu — tiền đã mất "
            "nhưng chưa ghi nhận vì vị thế còn mở, nên không xuất hiện trong "
            f"bất kỳ chỉ số nào ({surface}). Bảng số cho thấy một bot đang ổn; "
            "tài khoản thật đã mất một phần vốn mà người copy chưa biết."
        )

    if row.never_realized_a_loss and (row.trade_count or 0) >= 30:
        return (
            f"{name} chạy {row.trade_count} lệnh mà chưa từng ghi nhận một lệnh "
            "lỗ nào — với số lệnh này, xác suất một chiến lược thật sự không "
            "thua lần nào là gần bằng không. Lời giải thích hợp lý duy nhất là "
            f"lỗ chưa được chốt chứ không phải không tồn tại, nên mọi con số "
            f"trên sổ ({surface}) chỉ là nửa đẹp của sự thật."
        )

    if row.regime_dependence_pct and row.regime_dependence_pct >= 70:
        text = (
            f"{name} có kết quả tốt trên sổ ({surface}), nhưng "
            f"{row.regime_dependence_pct:.0f}% lãi gộp đến từ riêng pha thị "
            f"trường {phase_vi(row.best_phase)}. Đây là một chiến lược hợp với "
            "một kiểu thị trường chứ không phải một lợi thế ổn định — khi pha "
            "đổi, lợi thế biến mất mà không có cảnh báo trước."
        )
        if row.losing_phases:
            text += f" Bot đã lỗ ròng ở {len(row.losing_phases)}/6 pha."
        return text

    if not row.tested_in_downtrend and (row.trade_count or 0) >= 20:
        return (
            f"{name} đang có thành tích tốt ({surface}), nhưng toàn bộ hình "
            "thành mà chưa có lấy một lệnh nào trong pha thị trường giảm. Không "
            "phải bot sẽ thua ở chiều xuống — chưa ai biết — mà là không có cơ "
            "sở nào để nói nó chịu được, đúng vào chế độ nó chưa từng gặp."
        )

    if row.expectancy is not None and row.expectancy < 0:
        text = (
            f"{name} đang lỗ, không phải đang lãi: trên {row.trade_count or 0} "
            f"lệnh đã chốt, kỳ vọng mỗi lệnh là {row.expectancy:,.0f} USDT"
        )
        if row.total_pnl is not None and row.total_pnl < 0:
            text += f", cộng dồn {_money(abs(row.total_pnl))} lỗ"
        text += ". "
        if row.win_rate is not None and row.win_rate >= 60 and row.payoff_ratio:
            text += (
                f"Tỷ lệ thắng {row.win_rate:.0f}% nghe ổn, nhưng mỗi lệnh thắng "
                f"chỉ bằng {row.payoff_ratio:.2f} lần một lệnh thua, nên trông "
                "giỏi trên bảng tỷ lệ thắng mà vẫn lỗ đều trên tài khoản. "
            )
        text += "Chiến lược đã đủ lệnh để nói, và nó đang nói rằng nó mất tiền."
        return text

    if (
        row.deflated_sharpe is not None
        and row.deflated_sharpe < 0.6
        and row.selection_trials
    ):
        return (
            f"{name} có thành tích trông khả quan ({surface}), nhưng được chọn "
            f"vì là con tốt nhất trong {row.selection_trials} ứng viên cùng "
            "asset — chọn giỏi nhất từ nhiều ứng viên luôn có phần may mắn. "
            f"Trừ phần đó theo Deflated Sharpe, xác suất bot thật sự có lợi thế "
            f"chỉ còn {row.deflated_sharpe * 100:.1f}%, gần mức tung đồng xu."
        )

    if row.veto_reasons:
        return (
            f"{name} bị chặn bởi luật veto, không phải bởi điểm bình quân: "
            + "; ".join(row.veto_reasons)
            + f". Veto tồn tại để một lỗi đủ nặng không bị điểm trung bình đẹp "
            f"che đi — bình quân 10 chiều vẫn là {row.weighted_average:.1f}, "
            "nhưng chừng nào lỗi này còn thì bot vẫn không nên copy."
        )

    if (
        row.marked_profit_factor is not None
        and row.profit_factor is not None
        and abs(row.profit_factor - row.marked_profit_factor) < 0.3
    ):
        text = (
            f"{name} có sổ sách trung thực — điểm quan trọng nhất: profit "
            f"factor {row.profit_factor:.2f} trên lệnh đã chốt, và "
            f"{row.marked_profit_factor:.2f} nếu chốt luôn mọi vị thế đang mở. "
            "Hai con số sát nhau nghĩa là bot cắt lỗ thật chứ không ôm lỗ chờ "
            "gỡ, nên thành tích đang thấy là thành tích thật."
        )
        if row.max_drawdown_pct is not None:
            text += f" Sụt vốn thật đã ghi nhận {row.max_drawdown_pct:.1f}%."
        return text

    return (
        f"{name} không có dấu hiệu bất thường nào đủ nặng để một mình nó quyết "
        f"định kết quả ({surface}). Điểm số đến từ bình quân các chiều rủi ro "
        "chứ không từ một lỗi cụ thể, nên đây là mức rủi ro tổng thể chứ không "
        "phải một chỗ hỏng cụ thể."
    )


def _proof_points(row) -> List[str]:
    """The handful of numbers that carry the argument, one line each.

    Every bullet pairs the number with what it means, because a number alone
    proves nothing to a reader who does not already know the threshold. A bot
    can qualify for a dozen of these at once, which is what made the old list
    a wall of text; candidates are built in priority order below and the
    return is cut to 6 so the strongest evidence survives and the rest is
    left to the paragraph above.
    """
    points: List[str] = []

    # 1. Profit factor, closed book vs. marked-to-market -- the number the
    # paragraph above is usually arguing from, so it leads here too.
    if row.profit_factor is not None and row.marked_profit_factor is not None:
        # "Sát nhau" has to mean sát nhau: 1.68 → 1.31 is a fifth of the edge
        # gone, and calling that an honest book contradicts the paragraph above.
        gap = row.profit_factor - row.marked_profit_factor
        relative = gap / row.profit_factor if row.profit_factor else 0.0
        if row.profit_factor >= 1.0 > row.marked_profit_factor:
            verdict = " — chênh lệch này là toàn bộ vấn đề"
        elif relative >= 0.15:
            verdict = f" — chốt hết sổ mở thì mất {relative * 100:.0f}% lợi thế"
        else:
            verdict = " — hai con số sát nhau, sổ không giấu lỗ"
        points.append(
            f"Profit factor {row.profit_factor:.2f} (sổ đã chốt) → "
            f"{row.marked_profit_factor:.2f} (chốt cả sổ mở)" + verdict
        )
    elif row.profit_factor is not None:
        points.append(f"Profit factor {row.profit_factor:.2f}")

    # 2. The open loss in money and in percent of capital -- the single fact
    # a headline win rate is most likely to be hiding.
    if row.open_loss and row.open_loss_to_capital_pct:
        points.append(
            f"Lỗ chưa chốt {_money(row.open_loss)} = "
            f"{row.open_loss_to_capital_pct:.0f}% vốn, trên "
            f"{row.open_positions or 0} vị thế mở"
        )

    # 3. The stress test only earns a line when the bot did not simply
    # survive it -- a pass is the expected case, not evidence.
    if row.stress_verdict and row.stress_verdict != "SURVIVED":
        points.append(
            "Kịch bản sốc (biến động 2x, spread 3x, thanh khoản 1/2): "
            + ("bị thanh lý" if row.stress_verdict == "LIQUIDATED" else "dễ tổn thương")
        )

    # 4. Where the risk score actually came from: a veto floor overrides the
    # weighted average, so the average alone would be misleading here.
    if row.veto_reasons:
        points.append(
            f"Điểm rủi ro {row.risk_score:.0f} đến từ sàn veto (bình quân 10 "
            f"chiều chỉ {row.weighted_average:.1f}): " + "; ".join(row.veto_reasons)
        )
    elif row.top_risk_drivers:
        points.append(
            f"Điểm rủi ro {row.risk_score:.0f} là bình quân 10 chiều; nặng nhất: "
            + ", ".join(row.top_risk_drivers[:2])
        )

    # 5. Monte Carlo over the bot's own trade count.
    if row.mc_iterations and row.profit_pct_p50 is not None:
        line = (
            f"Monte Carlo {row.mc_iterations:,} kịch bản × {row.mc_horizon} lệnh: "
            f"trung vị {row.profit_pct_p50:+.1f}% vốn"
        )
        if row.profit_pct_p05 is not None:
            line += f", p05 {row.profit_pct_p05:+.1f}%"
        if row.profit_pct_worst is not None:
            line += f", xấu nhất {row.profit_pct_worst:+.1f}%"
        points.append(line)

    # 6. The tail of that same simulation: what the worst 5% of paths look like.
    tail = []
    if row.cvar_95_pct is not None:
        value = -row.cvar_95_pct
        tail.append(
            f"đuôi 5% tệ nhất {'lỗ' if value < 0 else 'vẫn lãi'} {abs(value):.1f}%"
        )
    if row.p_loss_after_horizon is not None:
        tail.append(f"xác suất lỗ {row.p_loss_after_horizon:.0f}%")
    if row.p_ruin:
        tail.append(f"xác suất cháy vốn {row.p_ruin:.0f}%")
    if tail:
        points.append("Rủi ro đuôi mô phỏng: " + ", ".join(tail))

    # 7. Its own bullet, not a tail clause: a strategy that has never met a
    # falling market is the single fact most likely to be missed, and it must
    # not disappear just because the phase breakdown could not be built.
    if not row.tested_in_downtrend and (row.trade_count or 0) >= 20:
        points.append(
            "Chưa từng bị thử ở chiều xuống — không có lệnh nào trong pha thị "
            "trường giảm"
        )

    # 8. The trade-count / win-rate / payoff triangle, which is where a "high
    # win rate" story usually falls apart.
    if row.trade_count and row.win_rate is not None and row.payoff_ratio:
        line = (
            f"{row.trade_count} lệnh, thắng {row.win_rate:.0f}%, payoff "
            f"{row.payoff_ratio:.2f}"
        )
        # "một lệnh thua xoá 1.0 lệnh thắng" is arithmetic, not evidence; the
        # ratio only says something once the two sides stop being equal.
        if row.payoff_ratio < 0.9:
            line += f" → một lệnh thua xoá {1 / row.payoff_ratio:.1f} lệnh thắng"
        elif row.payoff_ratio >= 1.5:
            line += " → lệnh thắng lớn hơn hẳn lệnh thua"
        points.append(line)

    # 9. Drawdown and Sharpe together, since either alone is easy to misread.
    if row.max_drawdown_pct is not None and row.sharpe_ratio is not None:
        points.append(
            f"Sụt vốn thực tế {row.max_drawdown_pct:.1f}%, Sharpe "
            f"{row.sharpe_ratio:.2f}"
            + (
                f", chuỗi thua dài nhất {row.max_loss_streak} lệnh"
                if row.max_loss_streak
                else ""
            )
        )

    # 10. Deflated Sharpe: how much of the edge survives after accounting for
    # how many candidates it was picked from.
    if row.deflated_sharpe is not None and row.selection_trials:
        points.append(
            f"Xác suất có lợi thế thật {row.deflated_sharpe * 100:.1f}% sau khi "
            f"trừ việc được chọn trong {row.selection_trials} ứng viên"
            + ("" if row.inference_reliable else " (kém tin cậy, đuôi quá dày)")
        )

    # 11. What the bot does and where it is strongest -- context rather than
    # a red flag on its own.
    if row.phase_coverage_pct is not None and row.best_phase:
        line = (
            f"Chiến lược: {BIAS_TEXT_VI.get(row.directional_bias or '', '')}, "
            f"{STYLE_TEXT_VI.get(row.entry_style or '', '')}; mạnh ở pha "
            f"{phase_vi(row.best_phase)}"
        )
        if row.regime_dependence_pct:
            line += f" ({row.regime_dependence_pct:.0f}% lãi gộp)"
        if row.losing_phases:
            line += f", lỗ ròng ở {len(row.losing_phases)}/6 pha"
        points.append(line)

    # 12. Which quality components dragged the composite score down.
    if row.quality_components:
        weak = [
            f"{QUALITY_COMPONENT_VI.get(key, key)} {value:.0f}"
            for key, value in row.quality_components.items()
            if value < 50
        ]
        if weak:
            points.append(
                f"Chất lượng {row.quality_score:.0f}/100 bị kéo xuống bởi: "
                + ", ".join(weak)
            )

    # 13. Data limitations last: they qualify the evidence above rather than
    # adding a new fact of their own.
    limits = []
    if row.ledger_coverage_days and row.declared_lead_days:
        if row.ledger_coverage_days / row.declared_lead_days < 0.5:
            limits.append(
                f"sổ công khai chỉ phủ {row.ledger_coverage_days:,.0f}/"
                f"{row.declared_lead_days} ngày hoạt động"
            )
    if (
        row.min_track_record_trades
        and row.trade_count
        and row.trade_count < row.min_track_record_trades
    ):
        limits.append(
            f"cần {row.min_track_record_trades:,.0f} lệnh mới đủ ý nghĩa thống "
            f"kê, mới có {row.trade_count}"
        )
    if row.measurement_mode and row.measurement_mode != "FULL":
        limits.append(f"chế độ đo {row.measurement_mode}")
    if limits:
        points.append("Giới hạn dữ liệu: " + "; ".join(limits))

    # Every branch above can fire at once; only the highest-priority handful
    # reach the reader, in the order they were appended.
    return points[:6]


def recommendation_vi(row) -> List[str]:
    """The assessment as an argument: why, then the proof, then the call.

    Shaped for a person to read top to bottom -- the reasoning is the long part
    because that is what has to convince, and the numbers are bullets under it
    because that is how evidence gets checked.
    """
    out: List[str] = []

    intro = f"{row.nick_name} — {row.traded_symbol}/{row.venue_type}"
    if row.trade_count:
        intro += f", {row.trade_count} lệnh đã chốt"
    if row.capital_at_risk:
        intro += f", vốn tham chiếu {row.capital_at_risk:,.0f} USDT"
    if row.trades_per_day:
        intro += f", {row.trades_per_day:.1f} lệnh/ngày"
    out.append(intro + ".")

    out.append("NGUYÊN NHÂN TẠI SAO: " + _cause_story(row))

    proof = _proof_points(row)
    if proof:
        out.append("CHỨNG MINH:")
        out.extend(f"• {point}" for point in proof)

    action = ACTION_VI.get(row.recommended_action or "", row.recommended_action)
    closing = (
        f"KẾT LUẬN: {row.verdict} — chất lượng {row.quality_score:.0f}/100, rủi ro "
        f"{row.risk_score:.0f}/100. Khuyến nghị: {action}."
    )
    if row.verdict in ("AN TOÀN", "TIỀM NĂNG") and (
        (row.total_pnl is not None and row.total_pnl < 0)
        or (row.expectancy is not None and row.expectancy < 0)
    ):
        closing += (
            " Xếp loại này nói về rủi ro, không nói về lợi nhuận: bot đang lỗ nên "
            "đây không phải khuyến nghị copy, chỉ nghĩa là mức thiệt hại có giới hạn."
        )
    change = _what_would_change_it(row)
    if change:
        closing += f" {change}"
    if row.confidence is not None and row.confidence < 70:
        closing += f" Độ tin cậy của chính đánh giá này chỉ {row.confidence:.0f}%."
    out.append(closing)
    return out
