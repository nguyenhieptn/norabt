from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from Agent.backend.bot.mcp.schemas.bot_result import (
    BehavioralObservations,
    OpenPosition,
    PositionSide,
    TradeLedgerItem,
)


def _is_adverse_entry(
    side: PositionSide, prior_entry: float, later_entry: float
) -> bool:
    """True nếu vị thế mở SAU vào giá tệ hơn vị thế mở TRƯỚC, cùng hướng.

    LONG: giá vào sau thấp hơn giá vào trước nghĩa là thị trường đã đi xuống
    và bot vẫn mua thêm -- đúng nghĩa "trung bình giá xuống" (averaging down).
    SHORT thì ngược lại: giá vào sau cao hơn giá vào trước.
    """
    if side == PositionSide.LONG:
        return later_entry < prior_entry
    return later_entry > prior_entry


class BehavioralPatternDetector:
    """Derive behavioral flags only from ledger evidence, never fixture names."""

    @staticmethod
    def analyze(
        trades: List[TradeLedgerItem],
        current_open_positions: int = 0,
        open_positions: Optional[List[OpenPosition]] = None,
    ) -> BehavioralObservations:
        if len(trades) < 2:
            return BehavioralObservations(
                behavioral_risk_tier="UNKNOWN", evidence=["Insufficient trade history"]
            )

        ordered = sorted(trades, key=lambda trade: (trade.open_time, trade.close_time))
        evidence: List[str] = []
        # Doubling down is a within-instrument act: losing on BTC and then opening
        # a routine DOGE position is not an escalation, but comparing consecutive
        # ledger rows across instruments counted it as one. These bots run ten or
        # more markets at once, so the sequence has to be taken per symbol.
        size_hits = lev_hits = eligible_after_loss = 0
        # Control group: the same escalation measured after WINS. A bot that
        # simply varies its size will clear a bare post-loss threshold by chance,
        # so martingale has to mean "bigger after losses than after wins".
        size_hits_after_win = eligible_after_win = 0
        for symbol in {trade.symbol for trade in ordered}:
            leg = [trade for trade in ordered if trade.symbol == symbol]
            if len(leg) < 2:
                continue
            # Thiếu dữ liệu KHÔNG được thay bằng 0 rồi đem so sánh. Bản cũ
            # dùng `trade.margin or trade.notional or 0.0`, và phép so sau đó
            # lệch một chiều rất nguy hiểm: nếu lệnh TRƯỚC thiếu cỡ thì
            # `cỡ_sau > 0 * 1.25` gần như luôn đúng, tức hệ thống BỊA ra một
            # lần nâng cỡ lệnh chưa từng xảy ra. Với đòn bẩy còn tệ hơn:
            # `đòn_bẩy_sau > 0 + 1` đúng với hầu hết mọi lệnh, sinh ra cáo
            # buộc "tăng đòn bẩy sau lệnh lỗ" từ hư không (+20 điểm ở lens).
            #
            # Đo trên dữ liệu OKX thật hiện nay: 1.625 lệnh trên 5 bot đều có
            # đủ margin/notional/leverage, nên nhánh này chưa từng bắn. Nhưng
            # OKX ĐÃ giấu mã công cụ ở vị thế mở, nên đây là bẫy gài sẵn chứ
            # không phải lo xa.
            #
            # Cách đúng: cặp nào thiếu dữ liệu thì LOẠI khỏi cả tử số lẫn mẫu
            # số -- không tính là có escalation, cũng không tính là một cơ hội
            # đã quan sát được. Tỉ lệ vì thế luôn là "trên số cặp thật sự đo
            # được", không bị pha loãng bởi những cặp không biết gì.
            leg_sizes = np.asarray(
                [
                    (
                        trade.margin
                        if trade.margin is not None
                        else (trade.notional if trade.notional is not None else np.nan)
                    )
                    for trade in leg
                ],
                dtype=np.float64,
            )
            leg_leverages = np.asarray(
                [
                    trade.leverage if trade.leverage is not None else np.nan
                    for trade in leg
                ],
                dtype=np.float64,
            )
            leg_losses = np.asarray(
                [trade.realized_pnl < 0 for trade in leg], dtype=bool
            )
            prior_loss = leg_losses[:-1]
            prior_win = ~prior_loss
            size_known = np.isfinite(leg_sizes[:-1]) & np.isfinite(leg_sizes[1:])
            lev_known = np.isfinite(leg_leverages[:-1]) & np.isfinite(leg_leverages[1:])
            with np.errstate(invalid="ignore"):
                bigger = size_known & (leg_sizes[1:] > leg_sizes[:-1] * 1.25)
            eligible_after_loss += int((prior_loss & size_known).sum())
            eligible_after_win += int((prior_win & size_known).sum())
            size_hits_after_win += int((prior_win & bigger).sum())
            size_hits += int((prior_loss & bigger).sum())
            # Cùng lý do như cỡ lệnh ở trên: đòn bẩy không đo được thì loại
            # khỏi phép so, không thay bằng 0 rồi kết luận là đã tăng.
            with np.errstate(invalid="ignore"):
                lev_up = lev_known & (leg_leverages[1:] > leg_leverages[:-1] + 1.0)
            lev_hits += int((prior_loss & lev_up).sum())

        eligible_after_loss = max(1, eligible_after_loss)
        size_score = size_hits / eligible_after_loss
        win_size_score = size_hits_after_win / max(1, eligible_after_win)
        martingale = (
            size_hits >= 3 and size_score >= 0.3 and size_score >= win_size_score * 1.5
        )
        # A single leverage bump somewhere in a 500-trade ledger is noise. The
        # pattern has to repeat, on the same footing martingale is judged.
        leverage_score = lev_hits / eligible_after_loss
        leverage_escalation = lev_hits >= 3 and leverage_score >= 0.3

        loss_chases = 0
        reentries = 0
        averaging_events = 0
        for previous, current in zip(ordered[:-1], ordered[1:], strict=False):
            gap_ms = current.open_time - previous.close_time
            if previous.realized_pnl < 0 and 0 <= gap_ms <= 60 * 60 * 1000:
                loss_chases += 1
            if (
                previous.symbol == current.symbol
                and previous.side == current.side
                and 0 <= gap_ms <= 15 * 60 * 1000
            ):
                reentries += 1
            overlaps = current.open_time < previous.close_time
            adverse_entry = (
                previous.entry_price is not None
                and current.entry_price is not None
                and (
                    (
                        current.side.value == "LONG"
                        and current.entry_price < previous.entry_price
                    )
                    or (
                        current.side.value == "SHORT"
                        and current.entry_price > previous.entry_price
                    )
                )
            )
            # Cùng nguyên tắc: không đo được cỡ lệnh thì KHÔNG kết luận là
            # đã tăng cỡ. `or 0.0` ở đây từng làm `cỡ_sau > 0 * 1.10` luôn
            # đúng mỗi khi lệnh trước thiếu dữ liệu, tức đếm thêm một lần
            # "nhồi to hơn" chưa từng xảy ra.
            current_size = (
                current.margin if current.margin is not None else current.notional
            )
            previous_size = (
                previous.margin if previous.margin is not None else previous.notional
            )
            increasing_size = (
                current_size is not None
                and previous_size is not None
                and current_size > previous_size * 1.10
            )
            if (
                overlaps
                and adverse_entry
                and increasing_size
                and previous.symbol == current.symbol
                and previous.side == current.side
            ):
                averaging_events += 1

        coverage_days = max(
            (max(t.close_time for t in ordered) - min(t.open_time for t in ordered))
            / 86_400_000.0,
            1 / 24,
        )
        trades_per_day = len(ordered) / coverage_days
        overtrading_score = min(1.0, max(0.0, (trades_per_day - 10.0) / 40.0))
        loss_chasing_score = loss_chases / eligible_after_loss

        holds = np.asarray(
            [trade.holding_time_minutes for trade in ordered], dtype=np.float64
        )
        median_hold = float(np.median(holds))
        p90_hold = float(np.percentile(holds, 90))
        hold_explosion = min(
            1.0, max(0.0, (p90_hold / max(median_hold, 1.0) - 2.0) / 5.0)
        )

        if martingale:
            evidence.append(
                f"{size_hits} position-size increases right after a loss on the "
                f"same symbol ({size_score:.0%} of opportunities, vs "
                f"{win_size_score:.0%} after wins)"
            )
        # Averaging down đúng nghĩa: THÊM vị thế vào một hướng ĐANG LỖ trên
        # CÙNG một mã -- không phải "đang mở >= 3 vị thế nói chung". Số vị thế
        # mở đồng thời chỉ đo ĐỘ PHƠI NHIỄM/TẬP TRUNG danh mục, và điều đó đã
        # được portfolio_risk / leverage_exposure đo qua gross_exposure/
        # open_loss rồi (xem behavioral_risk.py + composite bên dưới) -- dùng
        # lại nó ở đây vừa sai bản chất vừa đếm trùng.
        active_averaging = False
        averaging_confirmed: List[str] = []
        averaging_ambiguous: List[str] = []
        if open_positions is not None:
            # Một vị thế chỉ được dùng làm bằng chứng khi đã gán được
            # instrument (symbol có giá trị, side là LONG/SHORT thật sự) VÀ
            # attribution_source khác "NONE". Nguyên tắc "thiếu dữ liệu không
            # được quy thành an toàn" có chiều ngược lại cũng đúng: thiếu dữ
            # liệu cũng không được quy thành có tội, nên vị thế bị OKX ẩn
            # instrument bị LOẠI khỏi phân tích, không tính là bằng chứng
            # theo hướng nào.
            usable = [
                p
                for p in open_positions
                if p.symbol
                and p.side in (PositionSide.LONG, PositionSide.SHORT)
                and p.attribution_source != "NONE"
            ]
            unusable_count = len(open_positions) - len(usable)

            groups: Dict[Tuple[str, PositionSide], List[OpenPosition]] = {}
            for p in usable:
                groups.setdefault((p.symbol, p.side), []).append(p)

            for (symbol, side), members in groups.items():
                if len(members) < 2:
                    continue  # (a) cần >= 2 vị thế cùng mã, cùng hướng
                pnl_known = all(m.unrealized_pnl is not None for m in members)
                ordering_known = all(
                    m.open_time is not None and m.entry_price is not None
                    for m in members
                )
                loss_by_entry = None
                if ordering_known:
                    ordered_members = sorted(members, key=lambda m: m.open_time)
                    loss_by_entry = any(
                        _is_adverse_entry(side, prior.entry_price, later.entry_price)
                        for prior, later in zip(
                            ordered_members[:-1], ordered_members[1:], strict=False
                        )
                    )

                # (b) "nhóm đang lỗ": ưu tiên PnL thật đo được (đáng tin nhất
                # vì phản ánh giá thị trường hiện tại); chỉ khi PnL không có
                # mới rơi về xét thứ tự giá vào lệnh làm bằng chứng thay thế.
                # Không OR hai tín hiệu khi cả hai cùng có sẵn -- PnL dương
                # (đang lãi) luôn thắng thế trước một chuỗi giá vào lệnh
                # trông có vẻ bất lợi nhưng thị trường thực ra đã hồi lại,
                # nếu không sẽ vô tình cờ nhầm bot đang lãi.
                # BUỘC TỘI chỉ khi có bằng chứng về TRÌNH TỰ: một lệnh mở
                # SAU vào giá bất lợi hơn lệnh mở TRƯỚC cùng hướng. Đó mới
                # đúng nghĩa averaging down -- nhồi thêm SAU KHI giá đã đi
                # ngược.
                #
                # Tổng PnL âm KHÔNG đủ để buộc tội, dù nó là số đo đáng tin
                # nhất về việc nhóm có đang lỗ hay không. Lý do: nhiều vị thế
                # cùng mã cùng hướng đang lỗ có thể chỉ là một bot lưới mở
                # đồng loạt rồi thị trường rớt -- đó là một vị thế thua, không
                # phải một hành vi nhồi lệnh. Đo được trên fixture thật
                # (bot HYPE 793739635259546051): 5 lệnh SOL/LONG và 6 lệnh
                # HYPE/LONG đều âm tổng, nhưng `entry_price` của TẤT CẢ đều
                # None nên không có cách nào biết lệnh sau vào giá tốt hơn hay
                # xấu hơn lệnh trước. Buộc tội trong tình huống đó là lặp lại
                # đúng sai lầm mà bản sửa này sinh ra để loại bỏ, chỉ với một
                # cái cớ tinh vi hơn.
                #
                # Khi PnL cho thấy nhóm ĐANG LÃI thì kể cả chuỗi giá vào lệnh
                # trông bất lợi cũng không buộc tội: thị trường đã hồi, đó là
                # nhồi lệnh khi đúng hướng.
                if loss_by_entry is not None and pnl_known:
                    confirmed = loss_by_entry and (
                        sum(m.unrealized_pnl for m in members) < 0
                    )
                elif loss_by_entry is not None:
                    confirmed = loss_by_entry
                elif pnl_known and sum(m.unrealized_pnl for m in members) < 0:
                    # Biết chắc nhóm đang lỗ nhưng KHÔNG biết trình tự giá
                    # vào lệnh -> chưa kết luận được là averaging down.
                    confirmed = None
                else:
                    confirmed = None  # (c) không đủ dữ liệu để kết luận

                label = f"{symbol}/{side.value}"
                if confirmed is True:
                    active_averaging = True
                    averaging_confirmed.append(label)
                elif confirmed is None:
                    averaging_ambiguous.append(label)
                # confirmed is False: nhiều lệnh cùng mã/hướng nhưng đang lãi
                # -- đây là chiến lược nhồi lệnh khi đúng hướng, không phải
                # averaging down.

            # Thiếu dữ liệu cấp vị thế cũng không được quy thành có tội: chỉ
            # hạ độ tin cậy của riêng chiều này (qua averaging_down_suspected,
            # xử lý ở behavioral_risk.py), KHÔNG cộng điểm, KHÔNG dùng làm
            # bằng chứng buộc tội.
            suspected_averaging = (not active_averaging) and (
                bool(averaging_ambiguous) or unusable_count > 0
            )
            if unusable_count:
                evidence.append(
                    f"{unusable_count} open positions missing symbol/side or PnL "
                    "(attribution hidden) -- not enough data to assess adding to "
                    "a losing position, no score applied for these positions"
                )
            for label in averaging_confirmed:
                evidence.append(
                    f"Confirmed adding to a losing position on {label}: the "
                    "later entry is at a worse price than the earlier entry, "
                    "same direction"
                )
            for label in averaging_ambiguous:
                evidence.append(
                    f"Multiple positions on {label}, same symbol/direction, but "
                    "entry prices are missing so it cannot be told whether the "
                    "later entry was worse than the earlier one -- not "
                    "classified as adding to a loser, no score applied"
                )
        else:
            # Caller chỉ truyền số đếm, không có danh sách vị thế mở chi
            # tiết -- không thể phân biệt "50 vị thế trên 50 mã khác nhau"
            # (vô hại) với "10 lệnh dồn vào một mã đang lỗ" (averaging down
            # thật). Vì vậy KHÔNG được suy ra kết luận buộc tội chỉ từ con
            # số: chỉ ghi nhận chưa đo được và hạ độ tin cậy.
            suspected_averaging = current_open_positions > 0
            if current_open_positions:
                evidence.append(
                    f"{current_open_positions} open positions but no per-position "
                    "data (symbol/side/PnL) to assess adding to a losing position "
                    "-- not measurable, no score applied"
                )
        if averaging_events:
            evidence.append(
                f"{averaging_events} overlapping trades need position-level linkage before classifying averaging down"
            )
        if loss_chases:
            evidence.append(f"{loss_chases} rapid re-entries after losses")
        if leverage_escalation:
            evidence.append(
                f"{lev_hits} leverage increases after a loss on the same symbol "
                f"({leverage_score:.0%} of opportunities)"
            )
        if not evidence:
            evidence.append(
                "No material destructive pattern detected from available ledger"
            )

        # `0.75 if current_open_positions >= 3` bị bỏ khỏi max() này: số vị
        # thế mở đồng thời là tín hiệu về ĐỘ PHƠI NHIỄM/TẬP TRUNG danh mục,
        # không phải hành vi phá hoại, và nó đã được đo ở portfolio_risk /
        # leverage_exposure (gross_exposure, open_loss) -- giữ lại ở đây vừa
        # sai chỗ vừa đếm trùng. `active_averaging` (đã xác nhận bằng bằng
        # chứng thật ở trên, không phải suy từ số đếm) thay vào vị trí đó,
        # cùng trọng số với martingale vì cả hai đều là escalation đã xác
        # nhận trên cùng một mã và được lens cộng cùng 65 điểm.
        composite = max(
            0.85 if martingale else 0.0,
            0.85 if active_averaging else 0.0,
            loss_chasing_score,
            overtrading_score,
            hold_explosion,
        )
        # LƯU Ý cho phía hiển thị (Agent/backend/web/report_page.py,
        # web/data.py): `behavioral_risk_tier` dưới đây là tier thô suy ra từ
        # composite của module này, KHÁC với tier của chính điểm chiều "Hành
        # vi giao dịch" (`tier_for(score)` ở behavioral_risk.py) -- hai tier
        # có thể lệch nhau vì trọng số/ngưỡng không giống nhau (composite này
        # không cộng dồn nhiều tín hiệu như lens, mà lấy max của các tín hiệu
        # rời rạc). Trước khi bug >=3 vị thế được sửa, sự lệch pha này gần
        # như luôn đẩy `behavioral_risk_tier` lên HIGH/CRITICAL trong khi điểm
        # chiều thật chỉ ở mức ELEVATED, và trang báo cáo hiển thị thẳng
        # `behavioral_risk_tier` như thể đó là kết luận cuối -- xem
        # report_page.py dòng hiển thị `behavioral.get("behavioral_risk_tier")`
        # và web/data.py tương tự. Việc sửa >=3 ở trên đã loại bỏ nguyên nhân
        # chính gây lệch, nhưng hai khái niệm tier vẫn độc lập về mặt kiến
        # trúc; nơi hiển thị nên ghi rõ đây là "tín hiệu hành vi thô theo sổ
        # lệnh" khác với "điểm rủi ro hành vi đã tính trọng số" để người đọc
        # không hiểu nhầm hai con số nói cùng một điều.
        tier = (
            "CRITICAL"
            if composite >= 0.8
            else "HIGH"
            if composite >= 0.6
            else "MEDIUM"
            if composite >= 0.35
            else "LOW"
        )
        return BehavioralObservations(
            averaging_down_detected=active_averaging,
            averaging_down_suspected=suspected_averaging,
            martingale_escalation_detected=martingale,
            overtrading_score=overtrading_score,
            loss_chasing_score=min(1.0, loss_chasing_score),
            reentry_loop_detected=reentries >= 3,
            holding_time_explosion_score=hold_explosion,
            leverage_escalation_detected=leverage_escalation,
            size_escalation_score=min(1.0, size_score),
            size_escalation_excess=max(0.0, min(1.0, size_score - win_size_score)),
            behavioral_risk_tier=tier,
            evidence=evidence,
        )
