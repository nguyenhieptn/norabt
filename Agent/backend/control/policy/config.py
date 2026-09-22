"""Env-driven config for `ControlDecisionEngine`, replacing 3 literals that
used to be hardcoded directly in `decision_engine.py`.

Deliberately env vars, not a new YAML+profiles system: every other tunable
in this codebase (`Agent.backend.infra.config.AppConfig`, `X402Settings`,
`OkLinkSettings`) already works this way, so this stays consistent with the
one config idiom the project actually uses, needs no new dependency
(`pyyaml` isn't in `Agent/requirements.txt` today), and needs no container
rebuild to change a running deployment -- only `Agent/.env` + a restart,
exactly like every other flag here.

Defaults below are IDENTICAL to the values `decision_engine.py` hardcoded
before this change -- this is a pure extraction, not a behavior change.
Unlike `Agent.backend.report.qc.scoring.verdict.DANGEROUS_RISK`/`PROMISING_QUALITY`
(empirically calibrated against a 36-bot out-of-sample validation study,
cited in that module's own `VERDICT_BASIS_VI` text), the three values here
are operational policy knobs -- how eagerly the control layer flags/cools
down an intervention -- with no such citation, which is why only these are
being extracted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_COOLDOWN_SECONDS = 300
DEFAULT_TRIGGER_DIMENSION_SCORE = 60.0
DEFAULT_MIN_CONFIDENCE_FOR_ACTION = 40.0


@dataclass(frozen=True)
class ControlPolicyConfig:
    cooldown_seconds: int
    trigger_dimension_score: float
    min_confidence_for_action: float

    @classmethod
    def from_env(cls) -> "ControlPolicyConfig":
        return cls(
            cooldown_seconds=max(
                0,
                int(
                    os.getenv(
                        "CONTROL_POLICY_COOLDOWN_SECONDS",
                        str(DEFAULT_COOLDOWN_SECONDS),
                    )
                ),
            ),
            trigger_dimension_score=float(
                os.getenv(
                    "CONTROL_POLICY_TRIGGER_DIMENSION_SCORE",
                    str(DEFAULT_TRIGGER_DIMENSION_SCORE),
                )
            ),
            min_confidence_for_action=float(
                os.getenv(
                    "CONTROL_POLICY_MIN_CONFIDENCE",
                    str(DEFAULT_MIN_CONFIDENCE_FOR_ACTION),
                )
            ),
        )
