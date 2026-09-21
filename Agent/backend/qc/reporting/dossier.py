"""Pure deterministic analysis dossier construction.

This module is deliberately downstream of the existing typed pipeline.  It does
not fetch data, score a bot, persist history, render HTML, or invoke the
optional narrative/LLM layer.  A dossier is a sealed snapshot of deterministic
observations and QC output that can be consumed by SSR, JSON, MCP, or a future
post-analysis interpreter.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.pipeline import RiskSupervisionResult
from Agent.backend.qc.schemas.risk_assessment import BotRiskAssessment
from Agent.backend.qc.reporting.market_adapter import normalize_market_payload
from Agent.backend.qc.reporting.evidence import (
    METHODOLOGY_VERSION as EVIDENCE_VERSION,
    AnalysisClaim,
    SourceRecord,
    UncertaintyPassport,
    UserQuestion,
    build_claims,
    build_user_questions,
    build_source_ledger,
    build_uncertainty,
)
from Agent.backend.qc.reporting.scenarios import (
    METHODOLOGY_VERSION as SCENARIOS_VERSION,
    ScenarioLaboratory,
    build_scenario_laboratory,
)
from Agent.backend.qc.reporting.validation import (
    METHODOLOGY_VERSION as VALIDATION_VERSION,
    OutOfSampleValidation,
    build_out_of_sample_validation,
)
from Agent.backend.qc.reporting.insights import (
    METHODOLOGY_VERSION as INSIGHTS_VERSION,
    BehavioralDNA,
    RiskTwinState,
    ExecutiveEssence,
    FailureMode,
    MarketCompatibility,
    RiskTwin,
    build_behavioral_dna,
    build_executive_essence,
    build_failure_modes,
    build_market_compatibility,
    build_risk_twin,
)


# Build identifier recorded in every dossier. It is a plain constant rather
# than a git call so that building a dossier stays a pure function with no
# subprocess and no dependency on the checkout being a repository.
CODE_VERSION = "norabt.core.2026.09"


class DossierStatus(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    LIMITED = "LIMITED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class EvidenceProvenance(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    SIMULATED = "SIMULATED"
    UNKNOWN = "UNKNOWN"


class DossierSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bot_id: str
    unique_code: str
    nick_name: str
    symbol: str
    venue: str = "OKX"
    venue_type: str = "CEX"


class EvaluationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: EvaluationMode = EvaluationMode.SNAPSHOT
    as_of_ms: int = Field(..., ge=0)
    bot_as_of_ms: Optional[int] = Field(default=None, ge=0)
    market_as_of_ms: Optional[int] = Field(default=None, ge=0)
    methodology_versions: Dict[str, str] = Field(default_factory=dict)
    simulation_seed: Optional[int] = None
    simulation_iterations: Optional[int] = Field(default=None, ge=0)
    simulation_horizon: Optional[int] = Field(default=None, ge=0)
    code_version: str = CODE_VERSION
    dataset_digest: Optional[str] = None
    # Named reasons this dossier may not reproduce byte-for-byte from the
    # metadata above (an unrecorded seed, a stale source, a truncated ledger).
    reproducibility_warnings: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    category: str
    label: str
    status: EvidenceProvenance
    source: str
    as_of_ms: Optional[int] = Field(default=None, ge=0)
    metric_key: Optional[str] = None
    value: Optional[Any] = None
    unit: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)


class MarketCoverageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    share_pct: float = Field(..., ge=0.0, le=100.0)
    venue_type: Optional[str] = None
    status: EvidenceProvenance
    reason: Optional[str] = None


class MarketCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_symbol: str
    primary_share_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    resolved: List[MarketCoverageItem] = Field(default_factory=list)
    unresolved: List[MarketCoverageItem] = Field(default_factory=list)
    achieved_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class DossierQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bot_completeness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bot_freshness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bot_overall: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    market_completeness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    market_freshness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    market_overall: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class AnalysisDossier(BaseModel):
    """Versioned deterministic snapshot consumed by every report surface."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "analysis_dossier.v1"
    dossier_id: str
    dossier_digest: str
    status: DossierStatus
    subject: DossierSubject
    evaluation: EvaluationContext
    bot_result: BotResult
    primary_market_result: Optional[MarketResult] = None
    risk_assessment: BotRiskAssessment
    executive_essence: ExecutiveEssence
    behavioral_dna: BehavioralDNA
    risk_twin: RiskTwin
    market_compatibility: MarketCompatibility
    failure_modes: List[FailureMode] = Field(default_factory=list)
    scenario_laboratory: ScenarioLaboratory
    validation: OutOfSampleValidation
    uncertainty: UncertaintyPassport
    claims: List[AnalysisClaim] = Field(default_factory=list)
    user_questions: List[UserQuestion] = Field(default_factory=list)
    premium_market: Dict[str, Any] = Field(default_factory=dict)
    market_coverage: MarketCoverage
    quality: DossierQuality
    evidence: List[EvidenceItem] = Field(default_factory=list)
    source_ledger: List[SourceRecord] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    generated_at_ms: int = Field(..., ge=0)

    def deterministic_payload(self) -> Dict[str, Any]:
        """Return the digest input, excluding volatile generation metadata."""
        payload = self.model_dump(
            mode="json", exclude={"dossier_id", "dossier_digest", "generated_at_ms"}
        )
        return payload


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _finite_or_none(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    return value


def _evidence(
    *,
    evidence_id: str,
    category: str,
    label: str,
    source: str,
    as_of_ms: Optional[int],
    metric_key: Optional[str] = None,
    value: Any = None,
    unit: Optional[str] = None,
    status: EvidenceProvenance = EvidenceProvenance.OBSERVED,
    limitations: Optional[List[str]] = None,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        category=category,
        label=label,
        status=status,
        source=source,
        as_of_ms=as_of_ms,
        metric_key=metric_key,
        value=_finite_or_none(value),
        unit=unit,
        limitations=list(limitations or []),
    )


def _coverage(result: RiskSupervisionResult, bot: BotResult) -> MarketCoverage:
    exposure = bot.identity.symbol_exposure_share or {}
    primary_share = exposure.get(bot.identity.symbol)
    resolved: List[MarketCoverageItem] = []
    for item in result.resolved_markets:
        resolved.append(
            MarketCoverageItem(
                symbol=item.symbol,
                share_pct=max(0.0, min(100.0, float(item.share_pct))),
                venue_type=item.market.venue_type,
                status=EvidenceProvenance.OBSERVED,
            )
        )
    unresolved: List[MarketCoverageItem] = []
    for item in result.unresolved_markets:
        unresolved.append(
            MarketCoverageItem(
                symbol=item.symbol,
                share_pct=max(0.0, min(100.0, float(item.share_pct))),
                status=EvidenceProvenance.UNKNOWN,
                reason=item.reason,
            )
        )
    return MarketCoverage(
        primary_symbol=bot.identity.symbol,
        primary_share_pct=(
            max(0.0, min(100.0, float(primary_share) * 100.0))
            if isinstance(primary_share, (int, float)) and not isinstance(primary_share, bool)
            else None
        ),
        resolved=resolved,
        unresolved=unresolved,
        achieved_pct=(
            max(0.0, min(100.0, float(result.coverage_achieved_pct)))
            if result.coverage_achieved_pct is not None
            else None
        ),
    )


def build_live_analysis_dossier(
    asset: str,
    bot_folder_name: str,
    *,
    data_dir: Optional[Path] = None,
    venue_type: str = "CEX",
    seed: int = 42,
    as_of_ms: Optional[int] = None,
    simulation_iterations: int = 10_000,
    simulation_horizon: int = 500,
) -> AnalysisDossier:
    """Run one read-only pipeline and immediately seal its dossier.

    This is the explicit live entry point for future report/API integration.
    `persist_history=False` is intentional: building a report must not mutate
    trend history or assessment stores. The narrative layer is not imported or
    called here; it receives no hook from this function.
    """
    pipeline = RiskSupervisionPipeline(data_dir=data_dir, persist_history=False)
    result = pipeline.run(
        asset,
        bot_folder_name,
        venue_type=venue_type,
        seed=seed,
        as_of_ms=as_of_ms,
        simulation_iterations=simulation_iterations,
        simulation_horizon=simulation_horizon,
    )
    return build_analysis_dossier(result, generated_at_ms=as_of_ms, simulation_seed=seed)


def build_analysis_dossier(
    result: RiskSupervisionResult,
    *,
    generated_at_ms: Optional[int] = None,
    simulation_seed: Optional[int] = None,
) -> AnalysisDossier:
    """Build a deterministic dossier without side effects.

    The caller supplies a completed `RiskSupervisionResult`; this function never
    calls the pipeline, persistence stores, cache, HTML renderer, or narrative
    backend.  Secondary markets are copied into coverage only and are never
    passed back through QC.
    """
    if not isinstance(result, RiskSupervisionResult):
        raise TypeError("result must be a RiskSupervisionResult")

    bot = result.bot_result
    market = result.market_result
    assessment = result.risk_assessment
    if market is not None and market.symbol != bot.identity.symbol:
        raise ValueError(
            f"primary market {market.symbol} does not match bot symbol {bot.identity.symbol}"
        )

    generated = int(generated_at_ms if generated_at_ms is not None else assessment.timestamp)
    # Bot data quality's measurement mode (FULL/PARTIAL/LIMITED) describes
    # evidence coverage, not freshness evaluation. Pipeline snapshots are
    # judged under the existing snapshot contract; do not feed a
    # risk-measurement enum into EvaluationMode.
    mode = (market.data_quality.evaluation_mode if market is not None else EvaluationMode.SNAPSHOT)
    simulation = bot.simulation_results
    reproducibility_warnings: List[str] = []
    if simulation_seed is None:
        reproducibility_warnings.append(
            "The simulation seed was not recorded with this result, so the "
            "Monte Carlo figures cannot be reproduced exactly from this dossier"
        )
    if not bot.identity.ledger_fingerprint:
        reproducibility_warnings.append(
            "The source ledger has no fingerprint, so the input dataset cannot be pinned"
        )
    if getattr(bot.reconciliation, "ledger_truncated", False):
        reproducibility_warnings.append(
            "The source ledger is truncated, so a later run may read a different window"
        )
    evaluation = EvaluationContext(
        mode=mode,
        as_of_ms=assessment.as_of_ms,
        bot_as_of_ms=assessment.bot_as_of_ms,
        market_as_of_ms=assessment.market_as_of_ms,
        methodology_versions={
            "bot": bot.methodology_version,
            "market": market.methodology_version if market else "UNAVAILABLE",
            "qc": assessment.methodology_version,
            # One entry per module that derives a published number, so a stored
            # dossier always says WHICH method produced it. See each module's
            # own METHODOLOGY_VERSION for what a bump means.
            "insights": INSIGHTS_VERSION,
            "scenarios": SCENARIOS_VERSION,
            "validation": VALIDATION_VERSION,
            "evidence": EVIDENCE_VERSION,
        },
        simulation_iterations=simulation.iterations,
        simulation_horizon=simulation.horizon_trades,
        simulation_seed=simulation_seed,
        # The ledger fingerprint is the dataset identity the bot layer already
        # computes; reusing it keeps one notion of "which data was this".
        dataset_digest=bot.identity.ledger_fingerprint,
        reproducibility_warnings=reproducibility_warnings,
    )
    subject = DossierSubject(
        bot_id=bot.identity.bot_id,
        unique_code=bot.identity.unique_code,
        nick_name=bot.identity.nick_name,
        symbol=bot.identity.symbol,
        venue=bot.identity.venue,
        venue_type=bot.identity.venue_type if hasattr(bot.identity, "venue_type") else "CEX",
    )
    market_quality = market.data_quality if market else None
    quality = DossierQuality(
        bot_completeness=bot.data_quality.completeness_score,
        bot_freshness=bot.data_quality.freshness_score,
        bot_overall=bot.data_quality.overall_score,
        market_completeness=market_quality.completeness_score if market_quality else None,
        market_freshness=market_quality.freshness_score if market_quality else None,
        market_overall=market_quality.overall_score if market_quality else None,
        warnings=list(bot.data_quality.warnings)
        + (list(market_quality.warnings) if market_quality else []),
    )
    limitations = list(assessment.limitations) + list(quality.warnings)
    if market is None:
        limitations.append("No primary market observation is available for the traded symbol")
    evidence = [
        _evidence(
            evidence_id="bot.identity",
            category="identity",
            label="Bot identity and traded symbol",
            source="BotResult.identity",
            as_of_ms=bot.as_of_ms,
            value={"bot_id": bot.identity.bot_id, "symbol": bot.identity.symbol},
        ),
        _evidence(
            evidence_id="bot.data_quality",
            category="quality",
            label="Bot data quality",
            source="BotResult.data_quality",
            as_of_ms=bot.as_of_ms,
            value=bot.data_quality.model_dump(mode="json"),
            status=EvidenceProvenance.OBSERVED,
            limitations=list(bot.data_quality.warnings),
        ),
        _evidence(
            evidence_id="bot.deferred_loss",
            category="behavior",
            label="Reported versus marked deferred loss",
            source="BotResult.deferred_loss",
            as_of_ms=bot.as_of_ms,
            value=bot.deferred_loss.model_dump(mode="json"),
            limitations=list(bot.deferred_loss.warnings),
        ),
        _evidence(
            evidence_id="bot.simulation.closed_trades",
            category="simulation",
            label="Closed-trade simulation",
            source="BotResult.simulation_results",
            as_of_ms=bot.as_of_ms,
            value={
                "iterations": simulation.iterations,
                "horizon_trades": simulation.horizon_trades,
                "sample_size": simulation.sample_size,
                "return_basis": simulation.return_basis,
            },
            status=EvidenceProvenance.SIMULATED,
            limitations=list(simulation.warnings),
        ),
    ]
    if market is not None:
        evidence.append(
            _evidence(
                evidence_id="market.primary",
                category="market",
                label="Primary market observation",
                source="MarketResult",
                as_of_ms=market.as_of_ms,
                value={"symbol": market.symbol, "venue": market.venue},
                limitations=list(market.data_quality.warnings),
            )
        )

    # Every structured module below is a pure function of the typed results
    # already computed above. The claim engine runs last because a claim's
    # allowed wording depends on the finished uncertainty passport.
    source_ledger = build_source_ledger(bot, market)
    evidence.extend(
        _evidence(
            evidence_id=record.evidence_id,
            category="source",
            label=f"{record.domain} source: {record.source}",
            source=record.source,
            as_of_ms=record.observed_at_ms,
            value={
                "status": record.status,
                "record_count": record.record_count,
                "age_ms": record.age_ms,
            },
            status=(
                EvidenceProvenance.OBSERVED
                if record.status == "AVAILABLE"
                else EvidenceProvenance.UNKNOWN
            ),
            limitations=[record.reason] if record.reason else [],
        )
        for record in source_ledger
    )

    uncertainty = build_uncertainty(
        bot,
        market,
        coverage_pct=result.coverage_achieved_pct,
        limitations=list(assessment.limitations),
    )
    behavioral_dna = build_behavioral_dna(bot)
    failure_modes = build_failure_modes(bot, market)
    claims = build_claims(bot, market, uncertainty)
    essence = build_executive_essence(
        bot, behavioral_dna, failure_modes, uncertainty.overall_reliability
    )
    # The scenario laboratory and the holdout validation are both pure
    # functions of the ledger. The laboratory's seed is pinned to the dossier's
    # own seed so a dossier digest covers its scenario bands too.
    laboratory = build_scenario_laboratory(
        bot, market, seed=simulation_seed if simulation_seed is not None else 42
    )
    validation = build_out_of_sample_validation(bot)
    # The Risk Twin's third state comes from the laboratory rather than being
    # recomputed, so "stressed" means exactly one thing across the dossier.
    stressed_states = [
        RiskTwinState(
            state=scenario.scenario_id,
            status="SIMULATED",
            metrics={
                "total_pnl_p05": scenario.total_pnl.p05,
                "total_pnl_p50": scenario.total_pnl.p50,
                "max_drawdown_pct_p95": (
                    scenario.max_drawdown_pct.p95 if scenario.max_drawdown_pct else None
                ),
                "probability_of_loss_pct": scenario.probability_of_loss_pct,
            },
            assumptions=list(scenario.assumptions),
            evidence_ids=list(scenario.evidence_ids),
            limitations=list(scenario.limitations),
        )
        for scenario in laboratory.scenarios
        if scenario.status == "SIMULATED"
        and scenario.family != "BASELINE"
        and scenario.total_pnl is not None
    ]
    compatibility = build_market_compatibility(
        bot,
        unresolved_symbols=[item.symbol for item in result.unresolved_markets],
    )

    provisional = AnalysisDossier(
        dossier_id="PENDING",
        dossier_digest="PENDING",
        status=(
            DossierStatus.LIMITED
            if market is None or bot.data_quality.measurement_mode.value == "LIMITED"
            else DossierStatus.PARTIAL
            if bot.data_quality.measurement_mode.value == "PARTIAL"
            else DossierStatus.FULL
        ),
        subject=subject,
        evaluation=evaluation,
        bot_result=bot,
        primary_market_result=market,
        risk_assessment=assessment,
        executive_essence=essence,
        behavioral_dna=behavioral_dna,
        risk_twin=build_risk_twin(bot, stressed_states=stressed_states),
        market_compatibility=compatibility,
        failure_modes=failure_modes,
        scenario_laboratory=laboratory,
        validation=validation,
        uncertainty=uncertainty,
        claims=claims,
        user_questions=build_user_questions(
            bot, market, uncertainty, coverage_pct=result.coverage_achieved_pct
        ),
        source_ledger=source_ledger,
        premium_market=normalize_market_payload(market),
        market_coverage=_coverage(result, bot),
        quality=quality,
        evidence=evidence,
        limitations=list(dict.fromkeys(limitations)),
        generated_at_ms=generated,
    )
    digest = _digest(provisional.deterministic_payload())
    return provisional.model_copy(
        update={"dossier_id": f"DOSSIER_{digest[:16].upper()}", "dossier_digest": digest}
    )
