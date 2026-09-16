"""Place a bot in one of four buckets a reader can act on.

Why four and not a risk ladder: "tiềm ẩn" is not a middling amount of risk, it is
risk that the surface numbers hide -- a bot showing profit factor 11 and a 0.5 %
drawdown while carrying 86k of unrealised loss belongs there, not two rungs below
a bot that is visibly bleeding. So the bucket reads risk, quality and concealment
together instead of slicing one score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.mcp.schemas.bot_result import BotResult

VERDICT_DANGEROUS = "NGUY HIỂM"
VERDICT_LATENT = "TIỀM ẨN"
VERDICT_PROMISING = "TIỀM NĂNG"
VERDICT_SAFE = "AN TOÀN"
VERDICT_UNKNOWN = "THIẾU BẰNG CHỨNG"

DANGEROUS_RISK = 70.0
LATENT_RISK = 50.0
PROMISING_QUALITY = 65.0
# Below this the record is not good enough to call promising however calm it looks.
SAFE_MIN_QUALITY = 40.0


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
        flags.append(f"chốt hết sổ mở thì PF rơi từ {booked:.2f} xuống {marked:.2f}")
    if deferred.never_realized_a_loss and bot.performance.trade_count >= 20:
        flags.append("chưa từng ghi nhận một lệnh lỗ nào")
    if (
        deferred.open_loss_to_capital_pct is not None
        and deferred.open_loss_to_capital_pct >= 20.0
    ):
        flags.append(f"lỗ chưa chốt bằng {deferred.open_loss_to_capital_pct:.0f}% vốn")
    if (
        strategy.regime_dependence_pct is not None
        and strategy.regime_dependence_pct >= 70.0
    ):
        flags.append(
            f"{strategy.regime_dependence_pct:.0f}% lãi gộp chỉ đến từ một pha thị trường"
        )
    if bot.performance.trade_count >= 20 and not strategy.tested_in_downtrend:
        flags.append("chưa từng chạy qua pha giảm")
    if drawdown.max_dd_pct_capped:
        flags.append("sụt vốn vượt vốn ghi nhận nên chưa đo được thật")
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
                    f"{key} {outcome.horizon_trades} lệnh: "
                    f"{outcome.probability_of_profit:.0f}% khả năng có lãi"
                )
        note = f"Kết quả phụ thuộc vào horizon đo ({label})"
        if per_horizon:
            note += ": " + "; ".join(per_horizon)
        notes.append(note)

    if getattr(sim, "horizon_exceeds_observed", None):
        days = getattr(sim, "horizon_calendar_days", None)
        span = getattr(sim, "observed_span_days", None)
        if days is not None and span is not None:
            notes.append(
                f"Horizon mô phỏng ({sim.horizon_trades} lệnh ≈ {days:.0f} ngày) "
                f"dài hơn dữ liệu quan sát được ({span:.0f} ngày): kết luận ở đây "
                "là ngoại suy vượt quá dữ liệu thực tế"
            )
        else:
            notes.append(
                "Horizon mô phỏng vượt quá dữ liệu quan sát được: kết luận ở đây "
                "là ngoại suy"
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


def _decide_bucket(
    bot: BotResult,
    risk_score: Optional[float],
    quality_score: Optional[float],
    risk_drivers: Optional[List[str]] = None,
) -> Verdict:
    hidden = _hidden_risk_flags(bot)

    if risk_score is None:
        return Verdict(VERDICT_UNKNOWN, "Chưa chấm được điểm rủi ro", hidden)

    if risk_score >= DANGEROUS_RISK:
        # Name what pushed the score up. Restating the threshold told the reader
        # nothing they could not read off the score column itself.
        if risk_drivers:
            reason = "; ".join(risk_drivers[:2])
        elif hidden:
            reason = hidden[0]
        else:
            reason = f"điểm rủi ro {risk_score:.0f} vượt ngưỡng {DANGEROUS_RISK:.0f}"
        return Verdict(VERDICT_DANGEROUS, reason, hidden)

    if hidden:
        return Verdict(
            VERDICT_LATENT,
            "Số liệu bề mặt che mất rủi ro: " + "; ".join(hidden[:2]),
            hidden,
        )

    if risk_score >= LATENT_RISK:
        return Verdict(
            VERDICT_LATENT,
            f"Điểm rủi ro {risk_score:.0f} ở vùng giữa, chưa đủ an toàn để tin",
            hidden,
        )

    if quality_score is None:
        return Verdict(
            VERDICT_SAFE,
            f"Rủi ro thấp ({risk_score:.0f}) nhưng chưa chấm được chất lượng",
            hidden,
        )

    if quality_score >= PROMISING_QUALITY:
        return Verdict(
            VERDICT_PROMISING,
            f"Rủi ro thấp ({risk_score:.0f}) và chất lượng tốt ({quality_score:.0f})",
            hidden,
        )

    if quality_score >= SAFE_MIN_QUALITY:
        return Verdict(
            VERDICT_SAFE,
            f"Rủi ro thấp ({risk_score:.0f}), chất lượng mới ở mức trung bình "
            f"({quality_score:.0f})",
            hidden,
        )

    return Verdict(
        VERDICT_SAFE,
        f"Rủi ro thấp ({risk_score:.0f}) nhưng hiệu quả kém ({quality_score:.0f}): "
        "an toàn vì gần như không kiếm được gì",
        hidden,
    )
