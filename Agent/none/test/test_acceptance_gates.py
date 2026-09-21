"""Executable form of the acceptance gates in Agent/docs/ideallm.md section 12.

Each test below is one checkbox from that document. They exist so the gates
cannot quietly rot into prose: if a future change lets a missing value become a
safe-looking number, or lets a user view receive a different score, one of
these fails.
"""

from __future__ import annotations

import pytest

from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.qc.reporting.adapters import build_report_document
from Agent.backend.qc.reporting.contracts import ReportProduct
from Agent.backend.qc.reporting.dossier import (
    CODE_VERSION,
    EvidenceProvenance,
    build_analysis_dossier,
)
from Agent.backend.qc.reporting.evidence import WORDING_LEVELS
from Agent.backend.qc.reporting.persisted import build_persisted_dossier_view
from Agent.backend.qc.reporting.view_policy import (
    WITHHELD_MARKER,
    ViewRole,
    apply_view_policy,
    scoring_fingerprint,
)
from Agent.none.test.conftest import FIXED_AS_OF_MS


@pytest.fixture(scope="module")
def dossier():
    result = RiskSupervisionPipeline(persist_history=False).run(
        "MU",
        "bot_BB3398A957270A39",
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=50,
        simulation_horizon=20,
    )
    return build_analysis_dossier(
        result, generated_at_ms=FIXED_AS_OF_MS, simulation_seed=42
    )


# --------------------------------------------------------------------------- #
# Core correctness
# --------------------------------------------------------------------------- #


def test_every_claim_carries_evidence_references(dossier):
    assert dossier.claims, "expected the claim engine to produce claims"
    for claim in dossier.claims:
        assert claim.supporting_evidence, f"{claim.claim_id} has no supporting evidence"
        assert claim.falsifiers, f"{claim.claim_id} states nothing that would refute it"
        assert claim.allowed_wording_level in WORDING_LEVELS


def test_claim_wording_never_exceeds_measured_reliability(dossier):
    reliability = dossier.uncertainty.overall_reliability
    if reliability == "HIGH":
        pytest.skip("no ceiling applies at HIGH reliability")
    ceiling = "CONSISTENT_WITH" if reliability == "MEDIUM" else "SUGGESTS"
    limit = WORDING_LEVELS.index(ceiling)
    for claim in dossier.claims:
        # Negative statements are about absent evidence and keep their level.
        if claim.allowed_wording_level in ("DATA_DOES_NOT_ESTABLISH", "CANNOT_DETERMINE"):
            continue
        assert WORDING_LEVELS.index(claim.allowed_wording_level) <= limit


def test_observed_inferred_and_simulated_stay_distinct(dossier):
    statuses = {item.status for item in dossier.evidence}
    assert EvidenceProvenance.OBSERVED in statuses
    assert EvidenceProvenance.SIMULATED in statuses
    simulated = [
        item for item in dossier.evidence if item.status is EvidenceProvenance.SIMULATED
    ]
    for item in simulated:
        assert "simulation" in item.evidence_id or item.category == "simulation"
    for scenario in dossier.scenario_laboratory.scenarios:
        assert scenario.status in ("SIMULATED", "UNTESTED", "INSUFFICIENT")
        assert scenario.assumptions, "a scenario must state its assumptions"
        if scenario.status == "SIMULATED":
            # A simulated result without an interval is a point estimate
            # dressed up as a measurement.
            assert scenario.total_pnl is not None


def test_missing_data_never_becomes_a_safe_looking_value(dossier):
    for trait in dossier.behavioral_dna.traits:
        if trait.value is None:
            assert trait.status == "UNKNOWN"
    for cell in dossier.market_compatibility.cells:
        if cell.observed_trades == 0:
            # An untested regime must say so rather than show a zero result.
            assert cell.status == "UNKNOWN"
            assert cell.total_pnl is None
    # Every uncertainty component is either a real number or explicitly absent.
    for name, value in dossier.uncertainty.component_scores().items():
        assert 0.0 <= value <= 1.0, name


def test_reported_marked_and_stressed_states_stay_distinct(dossier):
    twin = dossier.risk_twin
    assert twin.reported.state == "REPORTED"
    assert twin.marked.state == "MARKED"
    assert twin.reported.metrics is not twin.marked.metrics
    for state in twin.stressed:
        assert state.state not in ("REPORTED", "MARKED")


def test_results_are_reproducible_from_recorded_metadata(dossier):
    evaluation = dossier.evaluation
    assert evaluation.code_version == CODE_VERSION
    assert evaluation.simulation_seed == 42
    assert evaluation.simulation_iterations is not None
    # A dossier that cannot be reproduced must say why, rather than imply it can.
    if evaluation.dataset_digest is None:
        assert evaluation.reproducibility_warnings


def test_source_ledger_addresses_each_raw_input(dossier):
    assert dossier.source_ledger, "expected raw source records in the ledger"
    ids = [record.evidence_id for record in dossier.source_ledger]
    assert ids == sorted(ids), "the ledger must be in a stable order"
    assert len(ids) == len(set(ids)), "source evidence ids must be unique"
    evidence_ids = {item.evidence_id for item in dossier.evidence}
    for record in dossier.source_ledger:
        assert record.evidence_id in evidence_ids


# --------------------------------------------------------------------------- #
# Report / UI stability
# --------------------------------------------------------------------------- #


def test_user_and_admin_views_share_one_core_result(dossier):
    payload = dossier.model_dump(mode="json")
    user_view = apply_view_policy(payload, ViewRole.USER)
    admin_view = apply_view_policy(payload, ViewRole.ADMIN)
    assert scoring_fingerprint(user_view) == scoring_fingerprint(admin_view)
    assert user_view["dossier_digest"] == admin_view["dossier_digest"]


def test_withheld_detail_is_marked_not_silently_dropped(dossier):
    payload = dossier.model_dump(mode="json")
    user_view = apply_view_policy(payload, ViewRole.USER)
    assert user_view["withheld_paths"], "expected a user view to withhold something"
    assert user_view["bot_result"] == WITHHELD_MARKER
    assert any(
        limitation.startswith(WITHHELD_MARKER)
        for limitation in user_view["limitations"]
    )
    # The original payload is untouched, so a role view can never corrupt core.
    assert payload["bot_result"] != WITHHELD_MARKER


def test_each_tab_carries_only_its_own_subject(dossier):
    analyst = build_report_document(dossier, ReportProduct.ANALYST)
    premium = build_report_document(dossier, ReportProduct.PREMIUM_MARKET)
    position = build_report_document(dossier, ReportProduct.OTHER_POSITION)

    premium_ids = [section.section_id for section in premium.sections]
    position_ids = [section.section_id for section in position.sections]
    analyst_ids = [section.section_id for section in analyst.sections]

    assert all(sid.startswith("market.") for sid in premium_ids)
    assert all(sid.startswith("other.") for sid in position_ids)
    assert all(sid.startswith("analyst.") for sid in analyst_ids)
    # The three products must not share a section id.
    assert len(set(premium_ids) | set(position_ids) | set(analyst_ids)) == len(
        premium_ids
    ) + len(position_ids) + len(analyst_ids)


def test_no_report_product_carries_narrative_text(dossier):
    for product in ReportProduct:
        document = build_report_document(dossier, product)
        assert document.narrative is None


# --------------------------------------------------------------------------- #
# Legacy compatibility
# --------------------------------------------------------------------------- #


def test_persisted_view_never_fabricates_live_only_fields():
    view = build_persisted_dossier_view(
        {
            "status": "FULL",
            "bot": {"unique_code": "ABC123", "traded_symbol": "MU", "nick_name": "n"},
            "recommendation": {"verdict": "CAUTION", "confidence": 55.0},
            "scoring": {"risk_score": 61.0, "total_weight": None},
            "evidence": {"trade_count": 12, "profit_factor": 1.4},
        }
    )
    assert view.source_shape == "COMPACT_ASSESSMENT_RECORD"
    assert view.risk_twin["stressed"] == []
    assert view.uncertainty["overall_reliability"] == "UNKNOWN"
    assert "scenarios" in view.unavailable_fields
    # A trait the record does not carry is UNKNOWN, never a default number.
    marked = [t for t in view.behavioral_dna["traits"] if t["key"] == "marked_profit_factor"]
    assert marked and marked[0]["status"] == "UNKNOWN"
    assert any("saved record" in item for item in view.limitations)


def test_persisted_view_reports_absence_rather_than_raising():
    view = build_persisted_dossier_view(None)
    assert view.status == "NOT_FOUND"
    assert view.limitations


# --------------------------------------------------------------------------- #
# Section 5 contract completeness and methodology versioning
# --------------------------------------------------------------------------- #


def test_dossier_carries_every_branch_of_the_section_5_contract():
    """The design document publishes an exact field tree. If a branch is
    missing, a consumer written against the document breaks."""
    from Agent.backend.qc.reporting.dossier import AnalysisDossier

    # doc branch -> the field that implements it
    implemented = {
        "identity": "subject",
        "executive_essence": "executive_essence",
        "behavioral_dna": "behavioral_dna",
        "risk_vector": "risk_assessment",
        "quality_vector": "quality",
        "risk_twin": "risk_twin",
        "market_compatibility": "market_compatibility",
        "failure_modes": "failure_modes",
        "scenarios": "scenario_laboratory",
        "uncertainty": "uncertainty",
        "evidence_graph": "evidence",
        "claims": "claims",
        "limitations": "limitations",
        "user_questions": "user_questions",
        "methodology": "evaluation",
    }
    fields = set(AnalysisDossier.model_fields)
    missing = {b: f for b, f in implemented.items() if f not in fields}
    assert not missing, f"section 5 branches with no field: {missing}"


def test_there_is_exactly_one_scenario_path(dossier):
    """A second, thinner scenario list used to live beside the laboratory. Two
    paths meant two different answers to the same question."""
    from Agent.backend.qc.reporting.dossier import AnalysisDossier

    assert "scenarios" not in AnalysisDossier.model_fields
    assert dossier.scenario_laboratory.scenarios


def test_every_deriving_module_records_its_methodology_version(dossier):
    versions = dossier.evaluation.methodology_versions
    for module in ("bot", "market", "qc", "insights", "scenarios", "validation", "evidence"):
        assert module in versions, f"{module} has no methodology version"
        assert versions[module]
    # Regime scenarios changed method (reconstruction -> real trades), so the
    # version must not still claim v1.
    assert versions["scenarios"] == "scenarios.v2"


def test_user_questions_are_about_evidence_never_about_acting(dossier):
    from Agent.backend.qc.reporting.evidence import AVAILABLE_ANALYSES

    banned = ("should i", "buy", "sell", "copy", "invest", "allocate", "recommend")
    for question in dossier.user_questions:
        lowered = question.question.lower()
        assert not any(word in lowered for word in banned), question.question
        assert question.answered_by in AVAILABLE_ANALYSES
        assert question.why_it_is_open
        assert question.evidence_ids


def test_untested_regimes_each_raise_their_own_question(dossier):
    asked = {
        q.question_id.rsplit(".", 1)[-1]
        for q in dossier.user_questions
        if q.answered_by == "UNTESTED_REGIME_SCENARIO"
    }
    assert asked == set(dossier.bot_result.strategy_observations.untested_phases)


# --------------------------------------------------------------------------- #
# Depth of the core analysis (design sections 6.2, 6.3, 6.5, 6.7)
# --------------------------------------------------------------------------- #


def test_each_trait_reports_the_sample_that_actually_supports_it(dossier):
    """Every trait used to report the whole ledger's n. A trait measured only
    on losing trades is supported by the LOSS count, and publishing the ledger
    count there overstated its confidence several times over."""
    traits = {t.key: t for t in dossier.behavioral_dna.traits}
    ledger = dossier.bot_result.trade_ledger_summary
    losses = sum(1 for t in ledger if t.realized_pnl < 0)
    wins = sum(1 for t in ledger if t.realized_pnl > 0)
    phased = sum(1 for t in ledger if t.market_phase and t.market_phase != "UNKNOWN")

    # Loss-side behaviour cannot be better supported than the loss count.
    assert traits["loss_chasing"].sample_size == losses
    assert traits["size_escalation_excess"].sample_size == min(wins, losses)
    # Regime traits cannot exceed the phase-labelled count.
    assert traits["regime_dependence"].sample_size == phased
    # Open-position traits are bounded by the number of open positions.
    assert (
        traits["attribution_quality"].sample_size
        == dossier.bot_result.current_state.open_positions_count
    )
    # And the whole point: they must not all be the same number any more.
    assert len({t.sample_size for t in dossier.behavioral_dna.traits}) > 1


def test_no_trait_claims_more_confidence_than_its_sample_allows(dossier):
    for trait in dossier.behavioral_dna.traits:
        if trait.confidence is None:
            assert trait.sample_size == 0
            continue
        assert trait.confidence <= min(1.0, trait.sample_size / 100.0) + 1e-9


def test_every_failure_mode_carries_all_eight_required_fields(dossier):
    """Design section 6.5 lists eight things a mode must show."""
    assert dossier.failure_modes
    for mode in dossier.failure_modes:
        assert mode.mechanism
        assert mode.observed_support, f"{mode.code} names no measurement"
        assert mode.trigger_conditions
        assert mode.early_indicators
        assert mode.affected_metrics
        assert mode.assumptions
        assert mode.falsifiers
        assert mode.evidence_ids


def test_failure_mode_catalogue_covers_the_documented_modes():
    """The catalogue must be able to raise every mode the design names, even
    when a given bot triggers only a few of them."""
    import inspect

    from Agent.backend.qc.reporting import insights

    source = inspect.getsource(insights.build_failure_modes)
    for code in (
        "DEFERRED_LOSS_REALIZATION",
        "ADVERSE_AVERAGING",
        "LIQUIDITY_CONTRACTION",
        "LEVERAGE_ESCALATION",
        "MARGIN_EXHAUSTION",
        "PROFIT_CONCENTRATION",
        "REGIME_DEPENDENCE",
        "LOSS_CLUSTERING",
        "POSITION_CONCENTRATION",
        "FUNDING_DRAG",
        "EXECUTION_SLIPPAGE_SENSITIVITY",
        "DATA_OPACITY",
    ):
        assert f'code="{code}"' in source, f"{code} is not in the catalogue"


def test_risk_twin_carries_all_three_states(dossier):
    """Design section 6.3 asks for reported, marked AND stressed."""
    twin = dossier.risk_twin
    assert twin.reported.state == "REPORTED"
    assert twin.marked.state == "MARKED"
    assert twin.stressed, "the stressed state was left empty"
    for state in twin.stressed:
        assert state.status == "SIMULATED"
        assert state.assumptions
        # A stressed state must come from the laboratory, not be recomputed.
        assert state.state.startswith("scenario.")


def test_uncertainty_uses_every_component_it_computed(dossier):
    """extrapolation_distance and seed_stability were computed and then dropped
    from the average, so a result extrapolated far past its sample scored the
    same as one that was not."""
    passport = dossier.uncertainty
    scored = passport.component_scores()
    for name in ("extrapolation_distance", "seed_stability"):
        if getattr(passport, name) is not None:
            assert name in scored, f"{name} is computed but excluded from reliability"


# --------------------------------------------------------------------------- #
# Core / data / UI consistency (design section 3.3 and section 10)
# --------------------------------------------------------------------------- #


def test_the_page_payload_is_derived_from_the_dossier_not_rebuilt():
    """The report layer used to rebuild the insight modules itself. It called
    `build_risk_twin(bot)` with no scenario states, so the page showed an empty
    stressed state while the dossier had four, and it dropped claims, user
    questions and the source ledger entirely. One builder, one answer."""
    import inspect

    from Agent.backend.web import data

    import ast

    tree = ast.parse(inspect.getsource(data._insights_evidence).lstrip())
    fn = tree.body[0]
    # The docstring names the old builders to explain the bug; only the CODE
    # matters here, so strip it before checking.
    if (
        fn.body
        and isinstance(fn.body[0], ast.Expr)
        and isinstance(fn.body[0].value, ast.Constant)
    ):
        fn.body = fn.body[1:]
    source = ast.unparse(fn)
    assert "build_analysis_dossier" in source
    for rebuilt in (
        "build_risk_twin(",
        "build_behavioral_dna(",
        "build_failure_modes(",
        "build_scenario_laboratory(",
        "build_uncertainty(",
    ):
        assert rebuilt not in source, (
            f"{rebuilt} is rebuilt in the report layer instead of read from the dossier"
        )


def test_page_payload_carries_every_published_module(dossier):
    """Whatever the dossier publishes, the page layer must receive -- otherwise
    a module exists in the contract and silently never reaches a reader."""
    import inspect

    from Agent.backend.web import data

    source = inspect.getsource(data._insights_evidence)
    for module in (
        "executive_essence",
        "behavioral_dna",
        "risk_twin",
        "market_compatibility",
        "failure_modes",
        "scenario_laboratory",
        "validation",
        "uncertainty",
        "claims",
        "user_questions",
        "source_ledger",
    ):
        assert f'"{module}"' in source, f"{module} never reaches the page layer"
        assert hasattr(dossier, module), f"{module} is not on the dossier"
