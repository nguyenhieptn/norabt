from __future__ import annotations

import json
import uuid
from typing import List, Optional

from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.scoring.quality import assess as assess_quality
from Agent.backend.qc.scoring.verdict import decide as decide_verdict
from Agent.backend.qc.schemas.risk_assessment import (
    BotRiskAssessment,
    DimensionContribution,
    EvidenceStatus,
    RiskDimensions,
    RiskTier,
    RiskTrend,
    ScoreBreakdown,
)

DIMENSION_LABEL_VI = {
    "market_alignment": "Market alignment",
    "performance_quality": "Performance quality",
    "return_r_quality": "Return / R quality",
    "drawdown_risk": "Drawdown risk",
    "tail_risk": "Tail risk",
    "leverage_exposure": "Leverage / exposure",
    "behavioral_risk": "Trading behaviour",
    "strategy_drift": "Strategy durability across phases",
    "liquidity_execution": "Liquidity / execution",
    "portfolio_risk": "Portfolio risk",
}

VETO_LABEL_VI = {
    "destructive behavioral pattern": "destructive trading behaviour",
    "extreme simulated tail risk": "extreme simulated tail risk",
    "directional conflict with high leverage": "against the trend with high leverage",
    "stress scenario liquidation": "stress scenario ends in liquidation",
}


class RiskFusionEngine:
    """Versioned weighted fusion with conservative UNKNOWN and explicit veto rules."""

    METHODOLOGY_VERSION = "qc_fusion.v1"

    @classmethod
    def fuse(
        cls,
        market: Optional[MarketResult],
        bot: BotResult,
        dimensions: RiskDimensions,
        previous_assessment: Optional[BotRiskAssessment] = None,
    ) -> BotRiskAssessment:
        dim_list = list(dimensions.model_dump().keys())
        evaluations = [getattr(dimensions, name) for name in dim_list]
        applicable = [
            item for item in evaluations if item.status != EvidenceStatus.NOT_APPLICABLE
        ]
        total_weight = sum(item.weight for item in applicable)
        score = sum(item.score * item.weight for item in applicable) / max(
            total_weight, 1e-12
        )

        weighted_average = score
        veto_floor: Optional[float] = None
        veto_reasons: List[str] = []
        emergency = False
        if (
            dimensions.behavioral_risk.status == EvidenceStatus.AVAILABLE
            and dimensions.behavioral_risk.score >= 85
        ):
            veto_floor = max(veto_floor or 0.0, 88.0)
            score = max(score, 88.0)
            veto_reasons.append("destructive behavioral pattern")
        if (
            dimensions.tail_risk.status == EvidenceStatus.AVAILABLE
            and dimensions.tail_risk.score >= 85
        ):
            veto_floor = max(veto_floor or 0.0, 85.0)
            score = max(score, 85.0)
            veto_reasons.append("extreme simulated tail risk")
        if (
            dimensions.market_alignment.status == EvidenceStatus.AVAILABLE
            and dimensions.leverage_exposure.status == EvidenceStatus.AVAILABLE
            and dimensions.market_alignment.score >= 85
            and dimensions.leverage_exposure.score >= 70
        ):
            veto_floor = max(veto_floor or 0.0, 85.0)
            score = max(score, 85.0)
            veto_reasons.append("directional conflict with high leverage")
        deferred = bot.deferred_loss
        if deferred.representativeness == "UNREPRESENTATIVE" and (
            deferred.turns_unprofitable_when_marked
            or (deferred.open_loss_to_capital_pct or 0.0) >= 15.0
        ):
            # Headline metrics are actively misleading: the loss is real, just not booked.
            veto_floor = max(veto_floor or 0.0, 70.0)
            score = max(score, 70.0)
            if deferred.turns_unprofitable_when_marked:
                veto_reasons.append(
                    f"closing the open book now would leave profit factor at only "
                    f"{deferred.marked_profit_factor:.2f}"
                )
            else:
                veto_reasons.append(
                    f"unrealised loss equal to {deferred.open_loss_to_capital_pct:.0f}% of capital "
                    f"with no sign of willingness to cut it"
                )
        if (
            bot.stress_results
            and bot.stress_results.is_valid
            and bot.stress_results.stress_survival_verdict == "LIQUIDATED"
        ):
            veto_floor = 100.0
            score = 100.0
            emergency = True
            veto_reasons.append("stress scenario liquidation")
        final_score = min(100.0, max(0.0, score))

        contributions = [
            DimensionContribution(
                name=name,
                label=DIMENSION_LABEL_VI.get(name, name),
                score=item.score,
                weight=item.weight,
                contribution=item.score * item.weight / max(total_weight, 1e-12),
                status=item.status.value,
            )
            for name, item in zip(dim_list, evaluations)
            if item.status != EvidenceStatus.NOT_APPLICABLE
        ]
        contributions.sort(key=lambda c: -c.contribution)

        raised = [
            f"{c.label} {c.score:.0f}/100 (weight {c.weight:.1f}) contributes "
            f"{c.contribution:.1f} points"
            for c in contributions
            if c.score >= 60 and c.status == "AVAILABLE"
        ]
        held_down = [
            f"{c.label} at only {c.score:.0f}/100 (weight {c.weight:.1f}) pulls the average down"
            for c in contributions
            if c.score <= 30 and c.status == "AVAILABLE"
        ]
        unknown_count = sum(1 for c in contributions if c.status == "UNKNOWN")
        if unknown_count:
            held_down.append(
                f"{unknown_count} dimensions lacking evidence are scored a neutral 50 points, "
                f"neither raising nor pulling down the score"
            )
        if veto_floor is not None and veto_floor > weighted_average:
            decided_by = "EMERGENCY_OVERRIDE" if emergency else "VETO_FLOOR"
        else:
            decided_by = "WEIGHTED_AVERAGE"

        breakdown = ScoreBreakdown(
            weighted_average=min(100.0, max(0.0, weighted_average)),
            total_weight=total_weight,
            applicable_dimensions=len(contributions),
            unknown_dimensions=unknown_count,
            not_applicable_dimensions=len(evaluations) - len(contributions),
            contributions=contributions,
            veto_floor=veto_floor,
            veto_reasons=[VETO_LABEL_VI.get(r, r) for r in veto_reasons],
            final_score=final_score,
            decided_by=decided_by,
            raised_the_score=raised,
            held_the_score_down=held_down,
        )

        dimension_confidence = sum(
            item.confidence * item.weight for item in applicable
        ) / max(total_weight, 1e-12)
        bot_confidence = min(
            bot.data_quality.overall_score, bot.data_quality.freshness_score
        )
        if market is None:
            source_confidence = bot_confidence
        else:
            market_confidence = min(
                market.data_quality.overall_score, market.data_quality.freshness_score
            )
            source_confidence = market_confidence * 0.4 + bot_confidence * 0.6
        confidence = min(
            100.0, max(0.0, source_confidence * dimension_confidence * 100.0)
        )

        available_weight = sum(
            item.weight
            for item in applicable
            if item.status == EvidenceStatus.AVAILABLE
        )
        evidence_coverage = available_weight / max(total_weight, 1e-12)

        if emergency:
            tier = RiskTier.EMERGENCY
        elif evidence_coverage < 0.5 and final_score < 65.0:
            # Thin evidence never downgrades an already-high measured risk.
            tier = RiskTier.UNKNOWN
        elif final_score >= 80:
            tier = RiskTier.CRITICAL
        elif final_score >= 65:
            tier = RiskTier.HIGH
        elif final_score >= 45:
            tier = RiskTier.ELEVATED
        elif final_score >= 30:
            tier = RiskTier.WATCH
        else:
            tier = RiskTier.HEALTHY

        trend = RiskTrend.UNKNOWN
        if previous_assessment and previous_assessment.bot_id == bot.identity.bot_id:
            delta = final_score - previous_assessment.risk_score
            trend = (
                RiskTrend.ACCELERATING_RISK
                if delta >= 5
                else RiskTrend.DE_ESCALATING
                if delta <= -5
                else RiskTrend.STABLE
            )

        if confidence < 40.0 or tier == RiskTier.UNKNOWN:
            action, reduction = "WARN", 0.0
        elif tier == RiskTier.EMERGENCY:
            action, reduction = "EMERGENCY_STOP", 100.0
        elif tier == RiskTier.CRITICAL:
            action, reduction = (
                ("PAUSE", 0.0)
                if dimensions.behavioral_risk.score >= 85
                else ("REDUCE", 50.0)
            )
        elif tier == RiskTier.HIGH:
            action, reduction = "REDUCE", 30.0
        elif tier == RiskTier.ELEVATED:
            action, reduction = "BLOCK_NEW_TRADES", 0.0
        elif tier == RiskTier.WATCH:
            action, reduction = "WARN", 0.0
        else:
            action, reduction = "MONITOR", 0.0

        evidence: List[str] = []
        warnings: List[str] = []
        positive: List[str] = []
        limitations = list(bot.data_quality.warnings)
        if deferred.representativeness == "UNKNOWN":
            limitations.append(
                "Unrealised PnL is unknown, so closed-trade metrics cannot be checked "
                "for deferred-loss distortion"
            )
        if market is None:
            limitations.append(
                "No market observation is available for the instrument this bot trades; "
                "market-dependent dimensions are UNKNOWN"
            )
        else:
            limitations.extend(market.data_quality.warnings)
        for item in evaluations:
            target = (
                limitations
                if item.status == EvidenceStatus.UNKNOWN
                else warnings
                if item.score >= 60
                else positive
                if item.score <= 25
                else evidence
            )
            target.extend(
                f"[{item.dimension_name}] {finding}" for finding in item.key_findings
            )

        identity = {
            "methodology": cls.METHODOLOGY_VERSION,
            "market": market.model_dump(mode="json") if market else None,
            "bot": bot.model_dump(mode="json"),
        }
        digest_source = json.dumps(
            identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        assessment_id = (
            f"QC_{uuid.uuid5(uuid.NAMESPACE_URL, digest_source).hex[:16].upper()}"
        )
        explanation = (
            f"Bot [{bot.identity.nick_name}] on [{bot.identity.symbol}] has risk tier [{tier.value}] "
            f"(score {final_score:.1f}/100, evidence confidence {confidence:.1f}%, "
            f"dimension coverage {evidence_coverage:.0%}). "
            f"Recommended control policy: [{action}]."
        )
        if veto_reasons:
            explanation += f" Veto evidence: {'; '.join(veto_reasons)}."
        if limitations:
            explanation += f" Assessment carries {len(limitations)} data limitations."

        # Risk says how much this can hurt; quality says whether it is any good.
        # Both are needed before a bot can be placed in a bucket a reader acts on.
        quality = assess_quality(bot)
        # What actually drove the risk score: the vetoes if any fired, otherwise
        # the dimensions carrying the most weighted score. Restating the
        # threshold told the reader nothing the score column did not already.
        drivers = [VETO_LABEL_VI.get(reason, reason) for reason in veto_reasons]
        if not drivers:
            ranked = sorted(
                (
                    (name, getattr(dimensions, name))
                    for name in type(dimensions).model_fields
                ),
                key=lambda pair: -(pair[1].score * pair[1].weight),
            )
            drivers = [
                f"{DIMENSION_LABEL_VI.get(name, name).lower()} {item.score:.0f}/100"
                for name, item in ranked[:2]
                if item.score >= 60.0
            ]
        verdict = decide_verdict(bot, final_score, quality.score, drivers)

        return BotRiskAssessment(
            methodology_version=cls.METHODOLOGY_VERSION,
            assessment_id=assessment_id,
            bot_id=bot.identity.bot_id,
            asset=bot.identity.symbol,
            venue=bot.identity.venue,
            timestamp=max(market.timestamp, bot.timestamp) if market else bot.timestamp,
            as_of_ms=min(market.as_of_ms, bot.as_of_ms) if market else bot.as_of_ms,
            market_as_of_ms=market.as_of_ms if market else None,
            bot_as_of_ms=bot.as_of_ms,
            risk_score=final_score,
            quality_score=quality.score,
            quality_components={k: round(v, 1) for k, v in quality.components.items()},
            quality_notes=quality.notes,
            verdict=verdict.verdict,
            verdict_reason=verdict.reason,
            hidden_risk_flags=verdict.hidden_flags,
            confidence=confidence,
            risk_tier=tier,
            risk_trend=trend,
            dimensions=dimensions,
            score_breakdown=breakdown,
            evidence=evidence,
            warnings=warnings,
            positive_factors=positive,
            limitations=limitations,
            recommended_action=action,
            suggested_reduction_pct=reduction,
            explanation=explanation,
        )
