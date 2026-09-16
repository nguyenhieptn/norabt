from __future__ import annotations

from typing import List

from Agent.backend.qc.schemas.risk_assessment import (
    DimensionEvaluation,
    EvidenceStatus,
    RiskTier,
)


def tier_for(score: float) -> RiskTier:
    if score >= 85:
        return RiskTier.CRITICAL
    if score >= 70:
        return RiskTier.HIGH
    if score >= 50:
        return RiskTier.ELEVATED
    if score >= 30:
        return RiskTier.WATCH
    return RiskTier.HEALTHY


def available(
    name: str, score: float, weight: float, findings: List[str], confidence: float = 1.0
) -> DimensionEvaluation:
    score = min(100.0, max(0.0, score))
    return DimensionEvaluation(
        dimension_name=name,
        score=score,
        tier=tier_for(score),
        weight=weight,
        status=EvidenceStatus.AVAILABLE,
        confidence=confidence,
        key_findings=findings,
    )


def unknown(name: str, weight: float, reason: str) -> DimensionEvaluation:
    return DimensionEvaluation(
        dimension_name=name,
        score=50.0,
        tier=RiskTier.UNKNOWN,
        weight=weight,
        status=EvidenceStatus.UNKNOWN,
        confidence=0.0,
        key_findings=[reason],
    )


def not_applicable(name: str, reason: str) -> DimensionEvaluation:
    return DimensionEvaluation(
        dimension_name=name,
        score=0.0,
        tier=RiskTier.UNKNOWN,
        weight=0.0,
        status=EvidenceStatus.NOT_APPLICABLE,
        confidence=1.0,
        key_findings=[reason],
    )
