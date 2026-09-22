from __future__ import annotations

import pytest

from Agent.backend.control.policy.config import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_MIN_CONFIDENCE_FOR_ACTION,
    DEFAULT_TRIGGER_DIMENSION_SCORE,
    ControlPolicyConfig,
)
from Agent.backend.control.policy.decision_engine import ControlDecisionEngine
from Agent.backend.control.schemas.control_decision import ExecutionMode


def _env_names():
    return (
        "CONTROL_POLICY_COOLDOWN_SECONDS",
        "CONTROL_POLICY_TRIGGER_DIMENSION_SCORE",
        "CONTROL_POLICY_MIN_CONFIDENCE",
    )


def test_defaults_match_the_original_hardcoded_values(monkeypatch: pytest.MonkeyPatch):
    """Pure extraction: unset env must reproduce decision_engine.py's old
    literals (300/60/40) exactly, or this change silently altered behavior."""
    for name in _env_names():
        monkeypatch.delenv(name, raising=False)

    policy = ControlPolicyConfig.from_env()

    assert policy.cooldown_seconds == 300 == DEFAULT_COOLDOWN_SECONDS
    assert policy.trigger_dimension_score == 60.0 == DEFAULT_TRIGGER_DIMENSION_SCORE
    assert policy.min_confidence_for_action == 40.0 == DEFAULT_MIN_CONFIDENCE_FOR_ACTION


def test_env_vars_override_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONTROL_POLICY_COOLDOWN_SECONDS", "120")
    monkeypatch.setenv("CONTROL_POLICY_TRIGGER_DIMENSION_SCORE", "75")
    monkeypatch.setenv("CONTROL_POLICY_MIN_CONFIDENCE", "50")

    policy = ControlPolicyConfig.from_env()

    assert policy.cooldown_seconds == 120
    assert policy.trigger_dimension_score == 75.0
    assert policy.min_confidence_for_action == 50.0


def test_negative_cooldown_env_clamped_to_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONTROL_POLICY_COOLDOWN_SECONDS", "-5")

    policy = ControlPolicyConfig.from_env()

    assert policy.cooldown_seconds == 0


def test_explicit_cooldown_seconds_still_wins_over_policy(monkeypatch: pytest.MonkeyPatch):
    """Backward compatibility: existing callers passing `cooldown_seconds=`
    directly (see test_quality_and_safety.py) must be unaffected by env vars."""
    monkeypatch.setenv("CONTROL_POLICY_COOLDOWN_SECONDS", "999")

    engine = ControlDecisionEngine(mode=ExecutionMode.READ_ONLY, cooldown_seconds=30)

    assert engine.cooldown_seconds == 30


def test_engine_uses_policy_thresholds_when_no_explicit_cooldown(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CONTROL_POLICY_COOLDOWN_SECONDS", "77")
    monkeypatch.setenv("CONTROL_POLICY_TRIGGER_DIMENSION_SCORE", "88")
    monkeypatch.setenv("CONTROL_POLICY_MIN_CONFIDENCE", "55")

    engine = ControlDecisionEngine(mode=ExecutionMode.READ_ONLY)

    assert engine.cooldown_seconds == 77
    assert engine.policy.trigger_dimension_score == 88.0
    assert engine.policy.min_confidence_for_action == 55.0


def test_explicit_policy_argument_wins_over_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONTROL_POLICY_COOLDOWN_SECONDS", "999")
    custom = ControlPolicyConfig(
        cooldown_seconds=10, trigger_dimension_score=1.0, min_confidence_for_action=1.0
    )

    engine = ControlDecisionEngine(mode=ExecutionMode.READ_ONLY, policy=custom)

    assert engine.cooldown_seconds == 10
    assert engine.policy is custom
