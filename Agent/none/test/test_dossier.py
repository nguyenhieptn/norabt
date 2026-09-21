from __future__ import annotations

import copy

import pytest

from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.qc.reporting.dossier import (
    DossierStatus,
    EvidenceProvenance,
    build_analysis_dossier,
)
from Agent.none.test.conftest import FIXED_AS_OF_MS


def _pipeline_result():
    return RiskSupervisionPipeline(persist_history=False).run(
        "MU",
        "bot_BB3398A957270A39",
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=50,
        simulation_horizon=20,
    )


def test_dossier_is_deterministic_and_contains_typed_sources():
    result = _pipeline_result()
    first = build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)
    second = build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)

    assert first.schema_version == "analysis_dossier.v1"
    assert first.dossier_digest == second.dossier_digest
    assert first.dossier_id == second.dossier_id
    assert first.status is DossierStatus.PARTIAL
    assert first.bot_result is result.bot_result
    assert first.risk_assessment is result.risk_assessment
    assert first.primary_market_result is result.market_result
    assert first.evaluation.mode.value == "SNAPSHOT"
    assert all(item.evidence_id for item in first.evidence)
    assert any(item.status is EvidenceProvenance.SIMULATED for item in first.evidence)
    assert first.behavioral_dna.traits
    assert first.risk_twin.reported.state == "REPORTED"
    assert first.risk_twin.marked.state == "MARKED"
    assert first.premium_market["status"] == "OBSERVED"


def test_dossier_digest_excludes_volatile_generation_time():
    result = _pipeline_result()
    first = build_analysis_dossier(result, generated_at_ms=1)
    second = build_analysis_dossier(result, generated_at_ms=2)
    assert first.dossier_digest == second.dossier_digest
    assert first.generated_at_ms == 1
    assert second.generated_at_ms == 2


def test_dossier_does_not_mutate_pipeline_result():
    result = _pipeline_result()
    before = copy.deepcopy(result.model_dump(mode="json"))
    build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)
    assert result.model_dump(mode="json") == before


def test_secondary_markets_are_coverage_only():
    result = _pipeline_result()
    dossier = build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)
    assert dossier.risk_assessment.model_dump(mode="json") == result.risk_assessment.model_dump(mode="json")
    assert dossier.market_coverage.primary_symbol == result.bot_result.identity.symbol
    assert dossier.market_coverage.achieved_pct == result.coverage_achieved_pct


def test_missing_primary_market_is_limited_not_fabricated():
    result = _pipeline_result()
    result.market_result = None
    result.market_available = False
    limited = build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)
    assert limited.status is DossierStatus.LIMITED
    assert limited.primary_market_result is None
    assert any("No primary market" in item for item in limited.limitations)


def test_primary_symbol_mismatch_is_rejected():
    result = _pipeline_result()
    result.market_result.symbol = "NOT_THE_BOT_SYMBOL"
    with pytest.raises(ValueError, match="does not match bot symbol"):
        build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)
