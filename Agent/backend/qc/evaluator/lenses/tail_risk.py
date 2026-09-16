from __future__ import annotations

from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.evaluator.common import available, unknown


class TailRiskLens:
    @staticmethod
    def evaluate(bot: BotResult):
        sim = bot.simulation_results
        if not sim.is_valid or sim.p_mdd_gt_15 is None:
            reason = "; ".join(sim.warnings) or "Simulation is unavailable"
            return unknown("Tail Risk", 1.3, reason)
        score = 15.0
        findings = [
            f"{sim.simulation_method}: {sim.iterations} paths, {sim.horizon_trades} trades/path, "
            f"capital basis {sim.capital_basis}"
        ]
        if sim.trades_per_day is not None and sim.horizon_calendar_days is not None:
            findings.append(
                f"Horizon {sim.horizon_trades} lệnh ≈ {sim.horizon_calendar_days:.1f} ngày lịch "
                f"với nhịp độ {sim.trades_per_day:.1f} lệnh/ngày của bot này"
            )
        if sim.horizon_exceeds_observed:
            findings.append(
                f"Horizon mô phỏng dài hơn dữ liệu thực đã quan sát được "
                f"({(sim.observed_span_days or 0.0):.1f} ngày), nên đây là ngoại suy "
                f"vượt quá phạm vi dữ liệu"
            )
        if sim.p_ruin is not None and sim.p_ruin > 0:
            findings.append(
                f"P(ruin over {sim.horizon_trades} trades) = {sim.p_ruin:.1f}% of paths "
                f"wipe out the capital at risk"
            )
            if sim.p_ruin >= 50:
                score = 100.0
            elif sim.p_ruin >= 20:
                score += 55
            elif sim.p_ruin >= 5:
                score += 30
            else:
                score += 15
        if (sim.p_mdd_gt_25 or 0.0) > 20:
            score += 45
            findings.append(f"P(MDD>25%)={sim.p_mdd_gt_25:.1f}%")
        elif sim.p_mdd_gt_15 > 30:
            score += 30
            findings.append(f"P(MDD>15%)={sim.p_mdd_gt_15:.1f}%")
        elif (sim.p_mdd_gt_10 or 0.0) > 50:
            score += 20
            findings.append(f"P(MDD>10%)={sim.p_mdd_gt_10:.1f}%")
        if sim.p95_max_drawdown is not None and sim.p95_max_drawdown > 30:
            score += 25
        elif sim.p95_max_drawdown is not None and sim.p95_max_drawdown > 15:
            score += 15
        # The probability that a sequence of trades contains a run of k
        # consecutive losses rises monotonically with the number of trades --
        # a bot that has simply traded a lot is therefore near-guaranteed to
        # show a long losing streak somewhere in its history even if every
        # trade is an independent draw from its own (possibly excellent) win
        # rate. Scoring the raw probability punishes trade *volume*, not risk.
        # The excess over what an independent Bernoulli sequence at this
        # bot's own win rate and horizon would produce anyway is what is left
        # to actually indicate streak-dependence (herding / martingale-like
        # clustering) in this bot's own trades -- that is the real signal.
        if sim.p_5_loss_streak_baseline is None:
            # No baseline available (an assessment stored before this field
            # existed, or a caller-provided SimulationResults that never went
            # through the updated engine): fall back to the exact original
            # raw-number threshold rather than silently skipping the check,
            # which would be a quiet loosening of the veto for old data.
            if (sim.p_5_loss_streak or 0.0) > 40:
                score += 15
        elif (sim.p_5_loss_streak_excess or 0.0) > 15:
            score += 15
            findings.append(
                f"P(>=5 lệnh thua liên tiếp) quan sát={sim.p_5_loss_streak:.1f}%, "
                f"cơ sở thống kê thuần túy do đã giao dịch {sim.horizon_trades} lệnh="
                f"{sim.p_5_loss_streak_baseline:.1f}%, phần vượt thật="
                f"{sim.p_5_loss_streak_excess:.1f}%"
            )
        if sim.p_10_loss_streak_baseline is None:
            if (sim.p_10_loss_streak or 0.0) > 10:
                score += 20
        elif (sim.p_10_loss_streak_excess or 0.0) > 10:
            score += 20
            findings.append(
                f"P(>=10 lệnh thua liên tiếp) quan sát={sim.p_10_loss_streak:.1f}%, "
                f"cơ sở thống kê thuần túy do đã giao dịch {sim.horizon_trades} lệnh="
                f"{sim.p_10_loss_streak_baseline:.1f}%, phần vượt thật="
                f"{sim.p_10_loss_streak_excess:.1f}%"
            )
        if (sim.p_loss_after_horizon or 0.0) > 25:
            score += 20
            findings.append(
                f"P(terminal loss after horizon)={sim.p_loss_after_horizon:.1f}%"
            )
        if (
            bot.stress_results
            and bot.stress_results.is_valid
            and bot.stress_results.stress_survival_verdict == "LIQUIDATED"
        ):
            score = 100
            findings.append("Stress scenario results in liquidation")
        elif (
            bot.stress_results
            and bot.stress_results.is_valid
            and bot.stress_results.stress_survival_verdict == "VULNERABLE"
        ):
            score += 20
            findings.append("Stress scenario classifies the bot as vulnerable")
        confidence = min(1.0, sim.sample_size / 100.0)
        if sim.deferred_loss_bias:
            # The distribution is missing the losses the bot has not taken yet.
            confidence *= 0.6
            score = max(score, 60.0)
            findings.append(
                "Distribution is drawn from closed trades only and omits the unrealised "
                "loss currently held, so these probabilities are optimistic"
            )
        return available("Tail Risk", score, 1.3, findings, confidence)
