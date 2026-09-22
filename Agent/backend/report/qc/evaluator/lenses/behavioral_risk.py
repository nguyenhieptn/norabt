from __future__ import annotations

from typing import List

from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.report.qc.evaluator.common import available, unknown


# Thang điểm liên tục cho việc bơm thêm vốn vào hướng đang lỗ (xem giải
# thích đầy đủ trong `BehavioralRiskLens.evaluate`).
#
# `_ADD_TO_LOSER_BASE` là phần rủi ro CÓ THẬT ngay cả khi cỡ lệnh không hề
# tăng: vốn vẫn đang được bơm thêm vào một hướng đang sai và vị thế vẫn chưa
# được cắt. Nó cố tình đủ nhỏ để một mình không chạm ngưỡng 85 -- ngưỡng mà
# `Agent/backend/qc/scoring/fusion.py` dùng để kích sàn veto "hành vi giao
# dịch hủy hoại" (ép điểm rủi ro lên 88).
#
# Đo trên 31 bot thật: 12 bot có nhồi thêm khi lỗ, nhưng chỉ 1 bot đồng thời
# nâng cỡ lệnh. Khi cả 12 cùng bị chấm như gấp thếp, 11 bot còn lại bị đẩy
# qua ngưỡng veto (RuiJie 41 -> 88, Shallow-Pair-Frog 35 -> 88,
# Fly-000 49 -> 88) -- dán nhãn nguy hiểm cho một lối chơi bình thường.
#
# `_ESCALATION_REF` là mốc chuẩn hoá, lấy đúng bằng ngưỡng 0.3 mà quy tắc
# martingale trong detector.py dùng, để hai nơi không trôi lệch.
_ADD_TO_LOSER_BASE = 25.0
_ESCALATION_SPAN = 40.0
_ESCALATION_REF = 0.3


class BehavioralRiskLens:
    @staticmethod
    def evaluate(bot: BotResult):
        obs = bot.behavioral_observations
        if obs.behavioral_risk_tier == "UNKNOWN":
            return unknown(
                "Trading behaviour",
                1.2,
                "Not enough ledger evidence to analyze behaviour",
            )
        score = 10.0
        # Built from the same boolean/float flags
        # Agent/backend/mcp/analytics/behavior/detector.py already computed
        # (that module is a sibling this task's file list does not cover),
        # rather than from its own `obs.evidence` free-text list -- so every
        # display string below is fully in this lens's own control.
        findings: List[str] = []
        # --- Bơm thêm vốn vào một hướng đang sai -----------------------
        #
        # Một thang điểm LIÊN TỤC duy nhất, không rẽ nhánh theo tên chiến
        # lược. Hai cách gọi quen thuộc -- "DCA/lưới" và "martingale" -- thực
        # ra là hai ĐẦU của cùng một trục đo được: nhồi thêm khi đang lỗ, và
        # mỗi lần nhồi lớn hơn bao nhiêu. Gán cứng "nếu là martingale thì 65,
        # nếu là DCA thì 25" là chấm điểm theo cái nhãn, không phải theo cái
        # đo được -- và nhãn thì luôn có trường hợp nằm giữa mà không rơi vào
        # hộp nào.
        #
        # Trục đo: `size_escalation_excess` = tỉ lệ nâng cỡ lệnh sau lệnh LỖ
        # TRỪ ĐI tỉ lệ nâng cỡ sau lệnh THẮNG (detector.py tính sẵn). Việc
        # trừ nhóm đối chứng là mấu chốt: một bot chỉ hay thay đổi cỡ lệnh
        # nói chung sẽ có hai tỉ lệ xấp xỉ nhau nên rơi về 0, chỉ bot nâng cỡ
        # RIÊNG sau khi thua mới đẩy đại lượng này lên.
        #
        # Mốc chuẩn hoá `_ESCALATION_REF` dùng lại đúng 0.3 mà quy tắc
        # martingale trong detector.py đã dùng, nên hai nơi không thể trôi
        # lệch nhau.
        adding_to_loser = (
            obs.averaging_down_detected or obs.martingale_escalation_detected
        )
        if adding_to_loser:
            intensity = min(1.0, max(0.0, obs.size_escalation_excess) / _ESCALATION_REF)
            score += _ADD_TO_LOSER_BASE + _ESCALATION_SPAN * intensity
            findings.append(
                "Adding to a losing position in the same direction; the size "
                f"escalation specific to a losing trade (net of the winning-trade "
                f"control group) is {obs.size_escalation_excess:.0%} -- the higher this "
                "is, the closer to martingale; the lower, the closer to steady averaging"
            )
        elif obs.averaging_down_suspected:
            # KHÔNG cộng điểm ở đây. `averaging_down_suspected` giờ chỉ còn
            # nghĩa "không đủ dữ liệu cấp vị thế (symbol/side/PnL) để kết
            # luận có averaging down hay không" (xem
            # Agent/backend/mcp/analytics/behavior/detector.py) -- không còn
            # là cáo buộc suy ra từ việc mở >= 3 vị thế như trước. Nguyên tắc
            # "thiếu dữ liệu không được quy thành an toàn" có chiều ngược
            # lại cũng đúng: thiếu dữ liệu cũng không được quy thành có tội,
            # nên phần thiếu bằng chứng này chỉ hạ ĐỘ TIN CẬY của chiều này
            # (xem `confidence` bên dưới), không cộng điểm phạt.
            findings.append(
                "Not enough open-position data (symbol/side/PnL) to conclude "
                "whether the bot adds to a losing position -- no score is applied "
                "for this, only the confidence of the trading-behaviour dimension is lowered"
            )
        if obs.loss_chasing_score > 0.6:
            score += 25
            findings.append(
                f"Loss-chasing score {obs.loss_chasing_score:.2f}"
            )
        if obs.overtrading_score > 0.6:
            score += 20
            findings.append(
                f"Overtrading score {obs.overtrading_score:.2f}"
            )
        if obs.holding_time_explosion_score > 0.5:
            score += 20
            findings.append(
                f"Abnormally volatile holding time (score "
                f"{obs.holding_time_explosion_score:.2f})"
            )
        if obs.leverage_escalation_detected:
            score += 20
            findings.append("Detected leverage raised after a losing trade on the same instrument")
        if not findings:
            findings.append("No behavioural pattern crossed the warning threshold")
        confidence = min(1.0, len(bot.trade_ledger_summary) / 50.0)
        if obs.averaging_down_suspected and not obs.averaging_down_detected:
            confidence *= 0.7
        return available("Trading behaviour", score, 1.2, findings, confidence)
