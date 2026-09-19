"""Place a bot on two independent axes a reader can act on, instead of one
collapsed risk ladder.

Why two axes and not four buckets ("NGUY HIỂM"/"TIỀM ẨN"/"TIỀM NĂNG"/"AN TOÀN"):
out-of-sample validation on 36 bots (Agent/docs/out_of_sample_validation.md)
found the risk score correlates with forward drawdown (rank rho 0.64, 95% CI
[0.39, 0.80]) but NOT with forward PnL (rho 0.205, 95% CI [-0.195, 0.539] --
contains zero). The old single "NGUY HIỂM" label conflated the two: a bot
scoring high on the risk axis is not thereby predicted to lose money, yet the
label read exactly that way. Splitting the label into a drawdown axis and a
quality axis stops the label from claiming more than the data supports --
each axis says only what it was actually validated to say.

  - Drawdown axis (CAO/THẤP): thresholded on `risk_score`, the axis the
    validation actually supports.
  - Quality axis (TỐT/YẾU): thresholded on `quality_score`, independent of
    the drawdown axis by construction -- a bot can be "SỤT VỐN: CAO · CHẤT
    LƯỢNG: TỐT" (the out-of-sample top-risk cohort's own median: +21.5% PnL,
    9.0% drawdown, 30% blew up at least once -- both things are true at once).

`HIDDEN RISK` stays a full override of both axes: it is not a middling
amount of risk, it is risk the surface numbers hide -- a bot showing profit
factor 11 and a 0.5% drawdown while carrying 86k of unrealised loss belongs
there regardless of where either axis would otherwise place it, because
neither axis's number can be trusted for this bot yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.mcp.schemas.bot_result import BotResult

# Two-axis labels (task's own exact strings -- do not reword).
VERDICT_HIGH_DD_GOOD_Q = "DRAWDOWN: HIGH · QUALITY: GOOD"
VERDICT_HIGH_DD_WEAK_Q = "DRAWDOWN: HIGH · QUALITY: WEAK"
VERDICT_LOW_DD_GOOD_Q = "DRAWDOWN: LOW · QUALITY: GOOD"
VERDICT_LOW_DD_WEAK_Q = "DRAWDOWN: LOW · QUALITY: WEAK"
VERDICT_HIDDEN_RISK = "HIDDEN RISK"
VERDICT_UNKNOWN = "INSUFFICIENT EVIDENCE"

# Reused verbatim from the pre-existing thresholds: DANGEROUS_RISK already
# gated the old "NGUY HIỂM" bucket, PROMISING_QUALITY already gated the old
# "TIỀM NĂNG" bucket. No new cut points invented for this redesign.
DANGEROUS_RISK = 70.0
PROMISING_QUALITY = 65.0

# The one sentence every verdict must carry alongside it (task's own exact
# wording) -- what the validation actually found, and what it did not.
# Sở cứ của điểm số, viết cho người ĐỌC BÁO CÁO chứ không cho người đọc code.
#
# Bản cũ chỉ nêu đúng một con số tương quan do chính hệ thống này tự đo. Đó là
# "chúng ta tự chấm chúng ta": người ngoài không có cách nào kiểm chứng, nên nó
# không phải sở cứ mà chỉ là một lời tự khai. Sở cứ thật phải là những phương
# pháp định lượng có tên tuổi, công bố học thuật, ai cũng tra được -- phần đo
# đạc nội bộ lùi xuống thành ghi chú kiểm chứng, đúng vị trí của nó.
VERDICT_BASIS_VI = (
    "Method: 10,000 scenarios simulated with a stationary bootstrap (Politis "
    "and Romano, 1994) on the closed trades of the bot itself \u2014 this preserves "
    "the autocorrelation of the sequence and assumes no normal distribution. Tail "
    "risk is measured with VaR at the 95% level and CVaR (expected shortfall). "
    "Sharpe quality is measured with the Probabilistic Sharpe Ratio and the "
    "Deflated Sharpe Ratio (Bailey and L\u00f3pez de Prado, 2012 and 2014) \u2014 which "
    "strip out the edge that appears by luck alone when many candidates are "
    "screened \u2014 together with the Minimum Track Record Length, which states "
    "how many trades are needed before a Sharpe ratio means anything. "
    "Out-of-sample validation on 36 bots: the Spearman rank correlation "
    "between the risk score and later drawdown is 0.64 (95% confidence "
    "interval [0.39\u20130.80]). This score does NOT predict profit or loss \u2014 the "
    "confidence interval for its correlation with return contains zero."
)


@dataclass
class Verdict:
    verdict: str
    reason: str
    hidden_flags: List[str] = field(default_factory=list)


def _hidden_risk_flags(bot: BotResult) -> List[str]:
    """Evidence that the headline numbers overstate how the bot is doing."""
    flags: List[str] = []
    deferred = bot.deferred_loss
    strategy = bot.strategy_observations
    drawdown = bot.drawdown_analysis

    booked, marked = deferred.booked_profit_factor, deferred.marked_profit_factor
    if booked is not None and marked is not None and booked >= 1.0 > marked:
        flags.append(f"closing the whole open book drops the PF from {booked:.2f} to {marked:.2f}")
    if deferred.never_realized_a_loss and bot.performance.trade_count >= 20:
        flags.append("has never booked a single losing trade")
    if (
        deferred.open_loss_to_capital_pct is not None
        and deferred.open_loss_to_capital_pct >= 20.0
    ):
        flags.append(f"unrealised loss equals {deferred.open_loss_to_capital_pct:.0f}% of capital")
    if (
        strategy.regime_dependence_pct is not None
        and strategy.regime_dependence_pct >= 70.0
    ):
        flags.append(
            f"{strategy.regime_dependence_pct:.0f}% of gross profit comes from a single market phase"
        )
    if bot.performance.trade_count >= 20 and not strategy.tested_in_downtrend:
        flags.append("has never run through a downtrend phase")
    if drawdown.max_dd_pct_capped:
        flags.append("drawdown exceeds the recorded capital, so the true figure could not be measured")
    return flags


def _horizon_notes(bot: BotResult) -> List[str]:
    """Describe how sensitive the read is to the trade horizon, and whether the
    horizon used is an extrapolation past the data on hand.

    Deliberately additive text only: this must never change which bucket a
    bot lands in (a veto stays a veto, a risk score stays whatever it was) --
    it only stops one flat label or one horizon's numbers from hiding that
    the bot was only tested that way at one particular horizon, or that the
    horizon quoted runs past the calendar time actually observed. Loosening
    the score itself is handled entirely upstream (Step 3, the excess-vs-
    baseline scoring in TailRiskLens), never here.
    """
    sim = getattr(bot, "simulation_results", None)
    if sim is None or not getattr(sim, "is_valid", False):
        return []

    notes: List[str] = []
    label = getattr(sim, "horizon_stability_label", None)
    if label and label != MonteCarloSimulationEngine.STABLE_LABEL:
        scenarios = getattr(sim, "horizon_scenarios", None) or []
        by_label = {scenario.label: scenario for scenario in scenarios}
        per_horizon = []
        for key in ("SHORT", "MEDIUM", "LONG"):
            outcome = by_label.get(key)
            if outcome is not None and outcome.probability_of_profit is not None:
                per_horizon.append(
                    f"{key} {outcome.horizon_trades} trades: "
                    f"{outcome.probability_of_profit:.0f}% probability of profit"
                )
        note = f"The result depends on the measured horizon ({label})"
        if per_horizon:
            note += ": " + "; ".join(per_horizon)
        notes.append(note)

    if getattr(sim, "horizon_exceeds_observed", None):
        days = getattr(sim, "horizon_calendar_days", None)
        span = getattr(sim, "observed_span_days", None)
        if days is not None and span is not None:
            notes.append(
                f"The simulated horizon ({sim.horizon_trades} trades ≈ {days:.0f} days) "
                f"is longer than the observed history ({span:.0f} days): this "
                "conclusion is an extrapolation beyond the actual data"
            )
        else:
            notes.append(
                "The simulated horizon exceeds the observed history: this "
                "conclusion is an extrapolation"
            )
    return notes


def decide(
    bot: BotResult,
    risk_score: Optional[float],
    quality_score: Optional[float],
    risk_drivers: Optional[List[str]] = None,
) -> Verdict:
    """Place `bot` in a bucket and phrase why, then layer on horizon context.

    The bucket and score are decided by `_decide_bucket` alone; the horizon
    notes appended afterward are strictly descriptive (see `_horizon_notes`)
    and cannot move a bot between buckets or change hidden_flags.
    """
    verdict = _decide_bucket(bot, risk_score, quality_score, risk_drivers)
    notes = _horizon_notes(bot)
    if notes:
        verdict.reason = f"{verdict.reason} " + " ".join(notes)
    return verdict


def label_from_scores(
    risk_score: Optional[float],
    quality_score: Optional[float],
    hidden_flags: Optional[List[str]],
) -> str:
    """The two-axis label as a pure function of the three inputs that are
    always available -- both fresh off `decide()` and read back from an old
    `assessment.json` on disk (`cham_diem.risk_score`/`quality_score`/
    `hidden_risk_flags`). Kept separate from `_decide_bucket` so a caller
    replaying old data never has to reconstruct a `BotResult` just to get a
    label out of stored scores; see `Agent/backend/web/admin_page.py` and
    `Agent/backend/web/data.py`'s own callers for exactly that backward-
    compatibility use.

    Deliberately NOT a string-to-string remap of the old 4 labels: the old
    label alone does not carry enough information to recover which of the
    new 6 states applies (a bot once called "NGUY HIỂM" could have been high
    risk with good OR weak quality), so the only correct migration is to
    recompute from the scores underneath it.
    """
    if risk_score is None:
        return VERDICT_UNKNOWN
    if hidden_flags:
        return VERDICT_HIDDEN_RISK
    drawdown_high = risk_score >= DANGEROUS_RISK
    quality_good = quality_score is not None and quality_score >= PROMISING_QUALITY
    if drawdown_high:
        return VERDICT_HIGH_DD_GOOD_Q if quality_good else VERDICT_HIGH_DD_WEAK_Q
    return VERDICT_LOW_DD_GOOD_Q if quality_good else VERDICT_LOW_DD_WEAK_Q


def _decide_bucket(
    bot: BotResult,
    risk_score: Optional[float],
    quality_score: Optional[float],
    risk_drivers: Optional[List[str]] = None,
) -> Verdict:
    hidden = _hidden_risk_flags(bot)

    if risk_score is None:
        return Verdict(VERDICT_UNKNOWN, "Could not score risk yet", hidden)

    # Hidden risk overrides BOTH axes: neither the drawdown score nor the
    # quality score can be trusted once the surface numbers are shown to be
    # hiding something, so there is nothing left for either axis to say.
    if hidden:
        return Verdict(
            VERDICT_HIDDEN_RISK,
            "The surface numbers hide risk: " + "; ".join(hidden[:2]),
            hidden,
        )

    drawdown_high = risk_score >= DANGEROUS_RISK
    if drawdown_high:
        # Name what pushed the score up. Restating the threshold told the reader
        # nothing they could not read off the score column itself.
        if risk_drivers:
            reason = "; ".join(risk_drivers[:2])
        else:
            reason = f"risk score {risk_score:.0f} is above the {DANGEROUS_RISK:.0f} threshold"
    else:
        reason = f"risk score {risk_score:.0f} is below the {DANGEROUS_RISK:.0f} threshold"

    if quality_score is None:
        reason += "; quality could not be scored, so it is classed as QUALITY: WEAK"
        label = VERDICT_HIGH_DD_WEAK_Q if drawdown_high else VERDICT_LOW_DD_WEAK_Q
    elif quality_score >= PROMISING_QUALITY:
        reason += f"; quality {quality_score:.0f} is at a good level"
        label = VERDICT_HIGH_DD_GOOD_Q if drawdown_high else VERDICT_LOW_DD_GOOD_Q
    else:
        reason += f"; quality {quality_score:.0f} has not reached a good level"
        label = VERDICT_HIGH_DD_WEAK_Q if drawdown_high else VERDICT_LOW_DD_WEAK_Q

    return Verdict(label, reason, hidden)
