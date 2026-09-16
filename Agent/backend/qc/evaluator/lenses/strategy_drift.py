from __future__ import annotations

from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.evaluator.common import available, unknown

# Below this the ledger has not been placed against enough market history to say
# anything about robustness, so the dimension abstains instead of scoring.
MIN_COVERAGE_PCT = 30.0
CONCENTRATED_PCT = 70.0
LEANING_PCT = 50.0
# A bot needs this many fills before "never traded a downtrend" means it avoided
# one rather than simply not having existed for long.
MIN_TRADES_FOR_UNTESTED = 20
BROAD_LOSS_PHASES = 3


class StrategyDriftLens:
    """How well the observed strategy holds up across market regimes.

    Why this replaced a declared-vs-observed check: OKX does not publish a
    declared strategy for any lead trader, so the old lens returned NOT_APPLICABLE
    for every bot and the whole dimension was dead weight. What is measurable from
    the public ledger is where the record was earned -- a bot whose profit comes
    from one regime, or that has never traded a downtrend, carries risk that its
    win rate hides. Declared drift is still folded in when a strategy is declared.
    """

    @staticmethod
    def evaluate(bot: BotResult):
        obs = bot.strategy_observations
        coverage = obs.phase_coverage_pct

        if coverage is None or coverage < MIN_COVERAGE_PCT:
            return unknown(
                "Strategy Drift",
                0.8,
                f"Chỉ đặt được {coverage:.0f}% số lệnh vào pha thị trường"
                if coverage is not None
                else "Không đặt được lệnh nào vào pha thị trường",
            )

        score = 15.0
        findings = [
            f"Đặt {coverage:.0f}% số lệnh vào pha thị trường; "
            f"thiên hướng {obs.directional_bias}, kiểu vào lệnh {obs.entry_style}"
        ]

        dependence = obs.regime_dependence_pct
        if dependence is not None and dependence >= CONCENTRATED_PCT:
            score += 35
            findings.append(
                f"{dependence:.0f}% lãi gộp đến từ riêng pha {obs.best_phase}: "
                "đổi chế độ thị trường là mất lợi thế"
            )
        elif dependence is not None and dependence >= LEANING_PCT:
            score += 20
            findings.append(f"{dependence:.0f}% lãi gộp dồn vào pha {obs.best_phase}")

        if (
            bot.performance.trade_count >= MIN_TRADES_FOR_UNTESTED
            and not obs.tested_in_downtrend
        ):
            score += 25
            findings.append(
                "Chưa có đủ lệnh nào trong pha giảm: chiến lược chưa được thử ở "
                "chiều xuống"
            )

        losing = len(obs.losing_phases)
        if losing >= BROAD_LOSS_PHASES:
            score += min(30.0, 10.0 * (losing - BROAD_LOSS_PHASES + 1))
            findings.append(
                f"Lỗ ở {losing}/6 pha thị trường, không chỉ riêng một chế độ"
            )

        if obs.directional_bias in ("LONG_ONLY", "SHORT_ONLY"):
            score += 15
            side = "long" if obs.directional_bias == "LONG_ONLY" else "short"
            findings.append(
                f"Sổ lệnh một chiều ({side}): kết quả phụ thuộc thị trường đi đúng "
                "một hướng"
            )

        if obs.untested_phases:
            findings.append(
                "Pha thị trường đã xuất hiện nhưng bot chưa từng trải: "
                + ", ".join(obs.untested_phases)
            )

        if obs.declared_strategy and obs.strategy_drift_score is not None:
            score += obs.strategy_drift_score * 20.0
            findings.append(
                f"Khai báo {obs.declared_strategy}, quan sát {obs.observed_profile}"
            )

        # Confidence follows how much of the ledger could actually be placed.
        return available("Strategy Drift", score, 0.8, findings, coverage / 100.0)
