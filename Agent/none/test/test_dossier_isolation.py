from __future__ import annotations

from Agent.backend.report.qc.reporting.dossier import build_analysis_dossier
from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.none.test.conftest import FIXED_AS_OF_MS


def test_dossier_build_does_not_touch_narrative_or_persistence(monkeypatch, tmp_path):
    calls = []

    def fail_if_called(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("narrative must not be part of deterministic dossier build")

    monkeypatch.setattr(
        "Agent.backend.llm.narrative.generate_narrative_sync",
        fail_if_called,
    )
    pipeline = RiskSupervisionPipeline(persist_history=False)
    monkeypatch.setattr(pipeline.history, "append", fail_if_called)
    result = pipeline.run(
        "MU",
        "bot_BB3398A957270A39",
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=10,
        simulation_horizon=5,
    )
    dossier = build_analysis_dossier(result, generated_at_ms=FIXED_AS_OF_MS)

    assert calls == []
    assert not hasattr(dossier, "narrative")
