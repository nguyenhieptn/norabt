from __future__ import annotations

from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.evaluator.common import available, unknown


class BehavioralRiskLens:
    @staticmethod
    def evaluate(bot: BotResult):
        obs = bot.behavioral_observations
        if obs.behavioral_risk_tier == "UNKNOWN":
            return unknown(
                "Behavioral Risk",
                1.2,
                "Insufficient ledger evidence for behavioral analysis",
            )
        score = 10.0
        findings = list(obs.evidence)
        if obs.martingale_escalation_detected:
            score += 65
        if obs.averaging_down_detected:
            score += 65
        elif obs.averaging_down_suspected:
            score += 25
            findings.append(
                "Averaging down is suspected but not confirmed from available position linkage"
            )
        if obs.loss_chasing_score > 0.6:
            score += 25
        if obs.overtrading_score > 0.6:
            score += 20
        if obs.holding_time_explosion_score > 0.5:
            score += 20
        if obs.leverage_escalation_detected:
            score += 20
        confidence = min(1.0, len(bot.trade_ledger_summary) / 50.0)
        if obs.averaging_down_suspected and not obs.averaging_down_detected:
            confidence *= 0.7
        return available("Behavioral Risk", score, 1.2, findings, confidence)
