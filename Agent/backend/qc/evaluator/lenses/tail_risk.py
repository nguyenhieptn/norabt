from __future__ import annotations


from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.evaluator.common import available, unknown

# Translation boundary for `sim.warnings`, which is built inside
# Agent/backend/mcp/analytics/simulation/monte_carlo.py -- a sibling module
# this task's file list does not cover. Only two templates exist there (both
# fire when the simulation could not run at all), enumerated and matched
# exactly, same approach as Agent/backend/mcp/service.py's own
# `_vi_upstream_warning`. Falls back to the original English text for
# anything that does not match, rather than dropping it.
# Cùng lý do như `mcp/service.py`: khối dịch Anh -> Việt cho hai cảnh báo của
# `monte_carlo.py` đã thành thừa khi sản phẩm chuyển sang tiếng Anh. Giữ tên
# hàm để nơi gọi khỏi sửa.
def _vi_mc_warning(text: str) -> str:
    """Trả về chính `text`."""
    return text


class TailRiskLens:
    @staticmethod
    def evaluate(bot: BotResult):
        sim = bot.simulation_results
        if not sim.is_valid or sim.p_mdd_gt_15 is None:
            reason = "; ".join(_vi_mc_warning(w) for w in sim.warnings) or (
                "Could not run the simulation"
            )
            return unknown("Tail risk", 1.3, reason)
        score = 15.0
        findings = [
            f"{sim.simulation_method}: {sim.iterations} simulated paths, "
            f"{sim.horizon_trades} trades/path, capital basis {sim.capital_basis}"
        ]
        if sim.trades_per_day is not None and sim.horizon_calendar_days is not None:
            findings.append(
                f"Horizon {sim.horizon_trades} trades ≈ {sim.horizon_calendar_days:.1f} calendar days "
                f"at this bot's own pace of {sim.trades_per_day:.1f} trades/day"
            )
        if sim.horizon_exceeds_observed:
            findings.append(
                f"The simulated horizon is longer than the observed history "
                f"({(sim.observed_span_days or 0.0):.1f} days), so this is an extrapolation "
                f"beyond the data on hand"
            )
        if sim.p_ruin is not None and sim.p_ruin > 0:
            findings.append(
                f"Probability of ruin over {sim.horizon_trades} trades = {sim.p_ruin:.1f}% "
                f"of simulated paths wipe out reference capital entirely"
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
            findings.append(f"Probability of max drawdown >25% = {sim.p_mdd_gt_25:.1f}%")
        elif sim.p_mdd_gt_15 > 30:
            score += 30
            findings.append(f"Probability of max drawdown >15% = {sim.p_mdd_gt_15:.1f}%")
        elif (sim.p_mdd_gt_10 or 0.0) > 50:
            score += 20
            findings.append(f"Probability of max drawdown >10% = {sim.p_mdd_gt_10:.1f}%")
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
                f"P(>=5 consecutive losing trades) observed={sim.p_5_loss_streak:.1f}%, "
                f"pure statistical baseline for {sim.horizon_trades} trades traded="
                f"{sim.p_5_loss_streak_baseline:.1f}%, real excess="
                f"{sim.p_5_loss_streak_excess:.1f}%"
            )
        if sim.p_10_loss_streak_baseline is None:
            if (sim.p_10_loss_streak or 0.0) > 10:
                score += 20
        elif (sim.p_10_loss_streak_excess or 0.0) > 10:
            score += 20
            findings.append(
                f"P(>=10 consecutive losing trades) observed={sim.p_10_loss_streak:.1f}%, "
                f"pure statistical baseline for {sim.horizon_trades} trades traded="
                f"{sim.p_10_loss_streak_baseline:.1f}%, real excess="
                f"{sim.p_10_loss_streak_excess:.1f}%"
            )
        if (sim.p_loss_after_horizon or 0.0) > 25:
            score += 20
            findings.append(
                f"Probability of loss after the horizon = {sim.p_loss_after_horizon:.1f}%"
            )
        if (
            bot.stress_results
            and bot.stress_results.is_valid
            and bot.stress_results.stress_survival_verdict == "LIQUIDATED"
        ):
            score = 100
            findings.append("The stress scenario ends in liquidation")
        elif (
            bot.stress_results
            and bot.stress_results.is_valid
            and bot.stress_results.stress_survival_verdict == "VULNERABLE"
        ):
            score += 20
            findings.append("The stress scenario places this bot in the vulnerable bracket")
        confidence = min(1.0, sim.sample_size / 100.0)
        if sim.deferred_loss_bias:
            # The distribution is missing the losses the bot has not taken yet.
            confidence *= 0.6
            score = max(score, 60.0)
            findings.append(
                "This distribution is drawn only from closed trades and does not "
                "count the unrealised loss still being held, so the probabilities "
                "above are more optimistic than reality"
            )
        return available("Tail risk", score, 1.3, findings, confidence)
