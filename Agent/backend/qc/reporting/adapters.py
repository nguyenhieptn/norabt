"""Deterministic adapters from `AnalysisDossier` to stable report products."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from Agent.backend.qc.reporting.contracts import (
    ReportDocument,
    ReportFinding,
    ReportMetric,
    ReportProduct,
    ReportSection,
)
from Agent.backend.qc.reporting.dossier import (
    AnalysisDossier,
    DossierStatus,
    EvidenceProvenance,
)


def _evidence_ids(dossier: AnalysisDossier, *prefixes: str) -> List[str]:
    return [
        item.evidence_id
        for item in dossier.evidence
        if any(item.evidence_id.startswith(prefix) for prefix in prefixes)
    ]


def _metric(
    metric_id: str,
    label: str,
    value: Any,
    *,
    status: EvidenceProvenance,
    evidence_ids: Iterable[str] = (),
    unit: str | None = None,
    display_value: str | None = None,
    confidence: float | None = None,
    limitations: Iterable[str] = (),
) -> ReportMetric:
    return ReportMetric(
        metric_id=metric_id,
        label=label,
        value=value,
        unit=unit,
        display_value=display_value,
        status=status,
        confidence=confidence,
        evidence_ids=list(evidence_ids),
        limitations=list(limitations),
    )


def _base(dossier: AnalysisDossier, product: ReportProduct, sections: List[ReportSection]) -> ReportDocument:
    return ReportDocument(
        report_id=f"{dossier.dossier_id}:{product.value}",
        report_product=product,
        dossier_id=dossier.dossier_id,
        dossier_digest=dossier.dossier_digest,
        subject=dossier.subject,
        status=dossier.status,
        snapshot=dossier.evaluation,
        sections=sections,
        evidence=dossier.evidence,
        # Narrative remains deliberately empty. The current narrative module is
        # not changed by this adapter and cannot affect deterministic reports.
        narrative=None,
    )


def analyst_report(dossier: AnalysisDossier) -> ReportDocument:
    assessment = dossier.risk_assessment
    assessment_dump = assessment.model_dump(mode="json")
    score_breakdown = assessment_dump.get("score_breakdown") or {}
    evidence_ids = _evidence_ids(dossier, "bot.", "market.")
    summary_metrics = [
        _metric("risk.score", "Risk score", assessment.risk_score, status=EvidenceProvenance.OBSERVED, unit="/100", confidence=assessment.confidence / 100.0, evidence_ids=evidence_ids),
        _metric("quality.score", "Quality score", assessment.quality_score, status=EvidenceProvenance.OBSERVED, unit="/100", confidence=assessment.confidence / 100.0, evidence_ids=evidence_ids),
        _metric("assessment.confidence", "Assessment confidence", assessment.confidence, status=EvidenceProvenance.OBSERVED, unit="/100", evidence_ids=evidence_ids),
        _metric("assessment.verdict", "Verdict", assessment.verdict, status=EvidenceProvenance.OBSERVED, evidence_ids=evidence_ids),
    ]
    dimensions = [
        _metric("uncertainty.reliability", "Evidence reliability", dossier.uncertainty.overall_reliability, status=EvidenceProvenance.OBSERVED, evidence_ids=evidence_ids, limitations=dossier.uncertainty.abstention_reasons),
        _metric("uncertainty.coverage", "Evidence coverage", dossier.uncertainty.evidence_coverage, status=EvidenceProvenance.OBSERVED if dossier.uncertainty.evidence_coverage is not None else EvidenceProvenance.UNKNOWN, unit="ratio", evidence_ids=evidence_ids),
    ]
    raw_dimensions = (assessment_dump.get("dimensions") or {})
    for key, dimension in raw_dimensions.items():
        if not isinstance(dimension, dict):
            continue
        dimensions.append(
            _metric(
                f"risk.dimension.{key}",
                str(dimension.get("label") or key),
                dimension.get("score"),
                status=(EvidenceProvenance.OBSERVED if dimension.get("status") == "AVAILABLE" else EvidenceProvenance.UNKNOWN),
                unit="/100",
                confidence=dimension.get("confidence"),
                limitations=list(dimension.get("key_findings") or []),
            )
        )
    dna_metrics = [
        _metric(
            f"behavior.{trait.key}",
            trait.label,
            trait.value,
            status=EvidenceProvenance(trait.status),
            confidence=trait.confidence,
            evidence_ids=trait.evidence_ids,
            limitations=trait.limitations,
        )
        for trait in dossier.behavioral_dna.traits
    ]
    twin_metrics = []
    for state in (dossier.risk_twin.reported, dossier.risk_twin.marked):
        for key, value in state.metrics.items():
            twin_metrics.append(
                _metric(
                    f"risk_twin.{state.state.lower()}.{key}",
                    f"{state.state.title()} {key.replace('_', ' ')}",
                    value,
                    status=EvidenceProvenance(state.status),
                    evidence_ids=state.evidence_ids,
                    limitations=state.limitations,
                )
            )
    return _base(
        dossier,
        ReportProduct.ANALYST,
        [
            ReportSection(
                section_id="analyst.executive_essence",
                title="Executive essence",
                status=EvidenceProvenance.INFERRED,
                metrics=[
                    _metric("essence.appears_to_do", "What it appears to do", dossier.executive_essence.what_it_appears_to_do, status=EvidenceProvenance.OBSERVED, evidence_ids=dossier.executive_essence.evidence_ids),
                    _metric("essence.dominant_behavior", "Dominant behavior", dossier.executive_essence.dominant_behavior, status=EvidenceProvenance.INFERRED if dossier.executive_essence.dominant_behavior else EvidenceProvenance.UNKNOWN, evidence_ids=dossier.executive_essence.evidence_ids),
                    _metric("essence.reliability", "Evidence reliability", dossier.executive_essence.evidence_reliability, status=EvidenceProvenance.OBSERVED, evidence_ids=dossier.executive_essence.evidence_ids),
                ],
                findings=[
                    ReportFinding(finding_id="essence.positive", text=dossier.executive_essence.strongest_positive_evidence, status=EvidenceProvenance.OBSERVED, evidence_ids=dossier.executive_essence.evidence_ids)
                ] if dossier.executive_essence.strongest_positive_evidence else [],
                evidence_ids=evidence_ids,
                limitations=[dossier.executive_essence.most_important_unknown] if dossier.executive_essence.most_important_unknown else [],
            ),
            ReportSection(
                section_id="analyst.essence",
                title="Analyst Result",
                status=EvidenceProvenance.OBSERVED,
                metrics=summary_metrics,
                evidence_ids=evidence_ids,
                limitations=dossier.limitations,
            ),
            ReportSection(
                section_id="analyst.behavioral_dna",
                title="Behavioral DNA",
                status=EvidenceProvenance.OBSERVED if dna_metrics else EvidenceProvenance.UNKNOWN,
                metrics=dna_metrics,
                findings=[ReportFinding(finding_id=f"behavior.pattern.{i}", text=pattern, status=EvidenceProvenance.INFERRED, evidence_ids=["bot.behavior.observed_profile"]) for i, pattern in enumerate(dossier.behavioral_dna.dominant_patterns)],
                evidence_ids=evidence_ids,
                limitations=dossier.behavioral_dna.unknowns,
            ),
            ReportSection(
                section_id="analyst.risk_twin",
                title="Reported vs marked state",
                status=EvidenceProvenance.OBSERVED if twin_metrics else EvidenceProvenance.UNKNOWN,
                metrics=twin_metrics,
                evidence_ids=evidence_ids,
                limitations=dossier.risk_twin.marked.limitations,
            ),
            ReportSection(
                section_id="analyst.failure_modes",
                title="Observed failure modes",
                status=EvidenceProvenance.INFERRED if dossier.failure_modes else EvidenceProvenance.UNKNOWN,
                findings=[ReportFinding(finding_id=mode.code, text=mode.mechanism, status=EvidenceProvenance.INFERRED, evidence_ids=mode.evidence_ids) for mode in dossier.failure_modes],
                evidence_ids=[evidence_id for mode in dossier.failure_modes for evidence_id in mode.evidence_ids],
                limitations=[limitation for mode in dossier.failure_modes for limitation in mode.limitations],
            ),
            ReportSection(
                section_id="analyst.validation",
                title="Did earlier results hold up later",
                status=EvidenceProvenance.OBSERVED if dossier.validation.status == "EVALUATED" else EvidenceProvenance.UNKNOWN,
                metrics=[
                    _metric("validation.stability", "Stability grade", dossier.validation.stability_grade, status=EvidenceProvenance.OBSERVED if dossier.validation.status == "EVALUATED" else EvidenceProvenance.UNKNOWN, evidence_ids=dossier.validation.evidence_ids),
                    _metric("validation.windows_profitable", "Out-of-sample windows in profit", dossier.validation.oos_profitable_folds, status=EvidenceProvenance.OBSERVED if dossier.validation.folds_evaluated else EvidenceProvenance.UNKNOWN, evidence_ids=dossier.validation.evidence_ids),
                    _metric("validation.pf_ratio", "Median out-of-sample / in-sample profit factor", dossier.validation.median_profit_factor_ratio, status=EvidenceProvenance.OBSERVED if dossier.validation.median_profit_factor_ratio is not None else EvidenceProvenance.UNKNOWN, evidence_ids=dossier.validation.evidence_ids),
                ],
                evidence_ids=dossier.validation.evidence_ids,
                limitations=dossier.validation.limitations + dossier.validation.assumptions,
            ),
            ReportSection(
                section_id="analyst.scenario_lab",
                title="Scenario laboratory",
                status=EvidenceProvenance.SIMULATED if dossier.scenario_laboratory.scenarios else EvidenceProvenance.UNKNOWN,
                metrics=[
                    _metric(
                        scenario.scenario_id,
                        scenario.name,
                        scenario.central_estimate,
                        status=EvidenceProvenance.SIMULATED if scenario.status == "SIMULATED" else EvidenceProvenance.UNKNOWN,
                        evidence_ids=scenario.evidence_ids,
                        display_value=(
                            f"p05 {scenario.total_pnl.p05} / p50 {scenario.total_pnl.p50} / p95 {scenario.total_pnl.p95}"
                            if scenario.total_pnl else None
                        ),
                        limitations=scenario.limitations + scenario.assumptions,
                    )
                    for scenario in dossier.scenario_laboratory.scenarios
                ],
                evidence_ids=["bot.trade_ledger_summary"],
                limitations=dossier.scenario_laboratory.limitations,
            ),
            ReportSection(
                section_id="analyst.open_questions",
                title="What the evidence leaves open",
                status=EvidenceProvenance.OBSERVED if dossier.user_questions else EvidenceProvenance.UNKNOWN,
                findings=[
                    ReportFinding(
                        finding_id=question.question_id,
                        text=question.question,
                        status=EvidenceProvenance.OBSERVED,
                        evidence_ids=question.evidence_ids,
                    )
                    for question in dossier.user_questions
                ],
                evidence_ids=[e for q in dossier.user_questions for e in q.evidence_ids],
                limitations=[q.why_it_is_open for q in dossier.user_questions],
            ),
            ReportSection(
                section_id="analyst.risk_dimensions",
                title="Risk dimensions",
                status=EvidenceProvenance.OBSERVED if dimensions else EvidenceProvenance.UNKNOWN,
                metrics=dimensions,
                evidence_ids=evidence_ids,
                limitations=dossier.limitations,
            ),
        ],
    )


def premium_market_report(dossier: AnalysisDossier) -> ReportDocument:
    market = dossier.primary_market_result
    evidence_ids = _evidence_ids(dossier, "market.")
    metrics: List[ReportMetric] = [
        _metric(
            "market.coverage.achieved_pct",
            "Observed market coverage",
            dossier.market_coverage.achieved_pct,
            status=EvidenceProvenance.OBSERVED if dossier.market_coverage.achieved_pct is not None else EvidenceProvenance.UNKNOWN,
            unit="%",
            evidence_ids=evidence_ids,
        ),
        _metric(
            "market.primary.symbol",
            "Primary market",
            market.symbol if market else None,
            status=EvidenceProvenance.OBSERVED if market else EvidenceProvenance.UNKNOWN,
            evidence_ids=evidence_ids,
            limitations=[] if market else ["No primary market observation is available"],
        ),
    ]
    if market:
        market_metrics = dossier.premium_market.get("metrics") or {}
        metrics.extend(
            [
                _metric("market.price", "Last price", market_metrics.get("last_price"), status=EvidenceProvenance.OBSERVED, evidence_ids=evidence_ids),
                _metric("market.spread_pct", "Spread", market_metrics.get("spread_pct"), status=EvidenceProvenance.OBSERVED if market_metrics.get("spread_pct") is not None else EvidenceProvenance.UNKNOWN, unit="%", evidence_ids=evidence_ids),
                _metric("market.trend", "Trend", market_metrics.get("trend_state"), status=EvidenceProvenance.OBSERVED, evidence_ids=evidence_ids),
                _metric("market.volatility", "Volatility", market_metrics.get("volatility_state"), status=EvidenceProvenance.OBSERVED, evidence_ids=evidence_ids),
                _metric("market.realized_volatility", "Realized volatility", market_metrics.get("realized_volatility"), status=EvidenceProvenance.OBSERVED if market_metrics.get("realized_volatility") is not None else EvidenceProvenance.UNKNOWN, evidence_ids=evidence_ids),
                _metric("market.liquidity", "Liquidity", market_metrics.get("liquidity"), status=EvidenceProvenance.OBSERVED if market_metrics.get("liquidity") else EvidenceProvenance.UNKNOWN, evidence_ids=evidence_ids),
            ]
        )
    else:
        metrics.append(_metric("market.unavailable", "Market data", None, status=EvidenceProvenance.UNKNOWN, evidence_ids=evidence_ids, limitations=["Not measured"]))
    return _base(
        dossier,
        ReportProduct.PREMIUM_MARKET,
        [
            ReportSection(
                section_id="market.compatibility",
                title="Market compatibility",
                status=EvidenceProvenance.OBSERVED if dossier.market_compatibility.cells else EvidenceProvenance.UNKNOWN,
                metrics=[
                    _metric(
                        f"compatibility.{cell.regime}",
                        f"{cell.symbol} in {cell.regime}",
                        cell.total_pnl,
                        status=EvidenceProvenance(cell.status),
                        evidence_ids=cell.evidence_ids,
                        limitations=[f"Reliability: {cell.reliability}", f"Observed trades: {cell.observed_trades}"],
                    )
                    for cell in dossier.market_compatibility.cells
                ],
                evidence_ids=evidence_ids,
                limitations=dossier.market_compatibility.limitations,
            ),
            ReportSection(section_id="market.premium", title="Premium Market", status=EvidenceProvenance.OBSERVED if market else EvidenceProvenance.UNKNOWN, metrics=metrics, evidence_ids=evidence_ids, limitations=list(dict.fromkeys(dossier.premium_market.get("limitations", []) + dossier.limitations)))],
    )


def other_position_report(dossier: AnalysisDossier) -> ReportDocument:
    bot = dossier.bot_result
    evidence_ids = _evidence_ids(dossier, "bot.")
    performance = bot.performance
    current = bot.current_state
    metrics = [
        _metric("bot.trade_count", "Closed trades", performance.trade_count, status=EvidenceProvenance.OBSERVED, evidence_ids=evidence_ids),
        _metric("bot.win_rate", "Win rate", performance.win_rate, status=EvidenceProvenance.OBSERVED, unit="%", evidence_ids=evidence_ids),
        _metric("bot.open_positions", "Open positions", current.open_positions_count, status=EvidenceProvenance.OBSERVED, evidence_ids=evidence_ids),
        _metric("bot.open_loss", "Open loss", current.unrealized_pnl, status=EvidenceProvenance.OBSERVED if current.unrealized_pnl is not None else EvidenceProvenance.UNKNOWN, evidence_ids=evidence_ids),
    ]
    return _base(
        dossier,
        ReportProduct.OTHER_POSITION,
        [
            ReportSection(section_id="other.general", title="General bot analysis", status=EvidenceProvenance.OBSERVED, metrics=metrics[:2], evidence_ids=evidence_ids, limitations=dossier.limitations),
            ReportSection(section_id="other.position", title="Position analysis", status=EvidenceProvenance.OBSERVED if current.open_positions_count or current.unrealized_pnl is not None else EvidenceProvenance.UNKNOWN, metrics=metrics[2:], evidence_ids=evidence_ids, limitations=list(bot.deferred_loss.warnings)),
            ReportSection(section_id="other.trade_analysis", title="Trade analysis", status=EvidenceProvenance.OBSERVED if performance.trade_count else EvidenceProvenance.UNKNOWN, metrics=[_metric("trade.expectancy", "Expectancy", performance.expectancy, status=EvidenceProvenance.OBSERVED if performance.expectancy is not None else EvidenceProvenance.UNKNOWN, evidence_ids=evidence_ids), _metric("trade.payoff_ratio", "Payoff ratio", performance.payoff_ratio, status=EvidenceProvenance.OBSERVED if performance.payoff_ratio is not None else EvidenceProvenance.UNKNOWN, evidence_ids=evidence_ids), _metric("trade.holding_time", "Median holding time", performance.median_hold_time_minutes, status=EvidenceProvenance.OBSERVED if performance.median_hold_time_minutes is not None else EvidenceProvenance.UNKNOWN, unit="minutes", evidence_ids=evidence_ids)], evidence_ids=evidence_ids, limitations=[]),
        ],
    )


def build_report_document(dossier: AnalysisDossier, product: ReportProduct) -> ReportDocument:
    if product is ReportProduct.ANALYST:
        return analyst_report(dossier)
    if product is ReportProduct.PREMIUM_MARKET:
        return premium_market_report(dossier)
    if product is ReportProduct.OTHER_POSITION:
        return other_position_report(dossier)
    raise ValueError(f"unsupported report product: {product!r}")
