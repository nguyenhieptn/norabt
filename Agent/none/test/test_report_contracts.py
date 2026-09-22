from __future__ import annotations

from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.report.qc.reporting.adapters import build_report_document
from Agent.backend.report.qc.reporting.contracts import ReportProduct
from Agent.backend.report.qc.reporting.dossier import build_analysis_dossier
from Agent.none.test.conftest import FIXED_AS_OF_MS


def _dossier():
    result = RiskSupervisionPipeline(persist_history=False).run(
        "MU",
        "bot_BB3398A957270A39",
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=20,
        simulation_horizon=10,
    )
    return build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)


def test_all_report_products_share_one_dossier_digest():
    dossier = _dossier()
    reports = [build_report_document(dossier, product) for product in ReportProduct]
    assert {report.dossier_id for report in reports} == {dossier.dossier_id}
    assert {report.dossier_digest for report in reports} == {dossier.dossier_digest}
    assert {report.schema_version for report in reports} == {"report_document.v1"}


def test_report_products_have_stable_semantic_ids_and_no_narrative():
    dossier = _dossier()
    analyst = build_report_document(dossier, ReportProduct.ANALYST)
    premium = build_report_document(dossier, ReportProduct.PREMIUM_MARKET)
    position = build_report_document(dossier, ReportProduct.OTHER_POSITION)

    assert [section.section_id for section in analyst.sections] == [
        "analyst.executive_essence",
        "analyst.essence",
        "analyst.behavioral_dna",
        "analyst.risk_twin",
        "analyst.failure_modes",
        "analyst.validation",
        "analyst.scenario_lab",
        "analyst.open_questions",
        "analyst.risk_dimensions",
    ]
    assert [section.section_id for section in premium.sections] == [
        "market.compatibility",
        "market.premium",
    ]
    assert [section.section_id for section in position.sections] == [
        "other.general",
        "other.position",
        "other.trade_analysis",
    ]
    assert analyst.narrative is None
    assert premium.narrative is None
    assert position.narrative is None


def test_report_adapter_does_not_mutate_dossier():
    dossier = _dossier()
    before = dossier.model_dump(mode="json")
    for product in ReportProduct:
        build_report_document(dossier, product)
    assert dossier.model_dump(mode="json") == before
