from __future__ import annotations

import time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class RiskTrend(str, Enum):
    UNKNOWN = "UNKNOWN"
    STABLE = "STABLE"
    ACCELERATING_RISK = "ACCELERATING_RISK"
    DE_ESCALATING = "DE_ESCALATING"


class EvidenceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DimensionEvaluation(BaseModel):
    dimension_name: str
    score: float = Field(..., ge=0.0, le=100.0)
    tier: RiskTier
    weight: float = Field(..., ge=0.0)
    status: EvidenceStatus = EvidenceStatus.AVAILABLE
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    key_findings: List[str] = Field(default_factory=list)


class DimensionContribution(BaseModel):
    """How much one dimension moved the final number."""

    name: str
    label: str
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(..., ge=0.0)
    contribution: float
    status: str


class ScoreBreakdown(BaseModel):
    """Where the score came from, and what kept it from going higher."""

    weighted_average: float = Field(..., ge=0.0, le=100.0)
    total_weight: float = Field(..., ge=0.0)
    applicable_dimensions: int = Field(default=0, ge=0)
    unknown_dimensions: int = Field(default=0, ge=0)
    not_applicable_dimensions: int = Field(default=0, ge=0)
    contributions: List[DimensionContribution] = Field(default_factory=list)
    veto_floor: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    veto_reasons: List[str] = Field(default_factory=list)
    final_score: float = Field(..., ge=0.0, le=100.0)
    decided_by: str = "WEIGHTED_AVERAGE"
    raised_the_score: List[str] = Field(default_factory=list)
    held_the_score_down: List[str] = Field(default_factory=list)


class RiskDimensions(BaseModel):
    market_alignment: DimensionEvaluation
    performance_quality: DimensionEvaluation
    return_r_quality: DimensionEvaluation
    drawdown_risk: DimensionEvaluation
    tail_risk: DimensionEvaluation
    leverage_exposure: DimensionEvaluation
    behavioral_risk: DimensionEvaluation
    strategy_drift: DimensionEvaluation
    liquidity_execution: DimensionEvaluation
    portfolio_risk: DimensionEvaluation


class BotRiskAssessment(BaseModel):
    """LOGIC 3 output built only from MarketResult and BotResult contracts."""

    schema_version: str = "bot_risk_assessment.v1"
    methodology_version: str = "qc_fusion.v1"
    assessment_id: str
    bot_id: str
    asset: str
    venue: str = "OKX"
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    as_of_ms: int = Field(..., ge=0)
    market_as_of_ms: Optional[int] = Field(default=None, ge=0)
    bot_as_of_ms: int = Field(..., ge=0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    # How good the bot is, which the risk score does not answer: a bot that
    # barely trades scores safe on every dimension while earning nothing.
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    quality_components: Dict[str, float] = Field(default_factory=dict)
    quality_notes: List[str] = Field(default_factory=list)
    # Four buckets a reader can act on, combining risk, quality and concealment.
    verdict: str = "INSUFFICIENT EVIDENCE"
    verdict_reason: str = ""
    hidden_risk_flags: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=100.0)
    risk_tier: RiskTier
    risk_trend: RiskTrend
    dimensions: RiskDimensions
    score_breakdown: ScoreBreakdown
    evidence: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    positive_factors: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    recommended_action: str
    suggested_reduction_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    explanation: str
