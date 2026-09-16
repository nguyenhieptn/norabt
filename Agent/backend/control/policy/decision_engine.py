from __future__ import annotations

import time
import uuid
from typing import Dict, Tuple

from Agent.backend.control.schemas.control_decision import (
    ControlAction,
    ControlDecision,
    ExecutionMode,
    ExecutionStatus,
)
from Agent.backend.qc.schemas.risk_assessment import BotRiskAssessment, RiskTier


class ControlDecisionEngine:
    """Map QC recommendations into auditable, idempotent policy decisions."""

    POLICY_VERSION = "control_policy.v1"

    def __init__(
        self, mode: ExecutionMode = ExecutionMode.READ_ONLY, cooldown_seconds: int = 300
    ) -> None:
        self.mode = mode
        self.cooldown_seconds = max(0, cooldown_seconds)
        self._last_actions: Dict[str, Tuple[ControlAction, int]] = {}

    def decide(
        self, assessment: BotRiskAssessment, now_ms: int | None = None
    ) -> ControlDecision:
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        action_map = {action.value: action for action in ControlAction}
        target = action_map.get(assessment.recommended_action, ControlAction.WARN)
        if assessment.risk_tier == RiskTier.UNKNOWN or assessment.confidence < 40:
            target = ControlAction.WARN

        status = ExecutionStatus.PENDING
        previous = self._last_actions.get(assessment.bot_id)
        if (
            previous
            and previous[0] == target
            and now - previous[1] < self.cooldown_seconds * 1000
        ):
            status = ExecutionStatus.SKIPPED_COOLDOWN
        else:
            self._last_actions[assessment.bot_id] = (target, now)

        triggered = []
        for name, dimension in assessment.dimensions:
            if dimension.score >= 60 and dimension.status.value == "AVAILABLE":
                triggered.append(name)
        reason = f"QC tier {assessment.risk_tier.value}; recommendation {target.value}; confidence {assessment.confidence:.1f}%"
        key = f"{assessment.assessment_id}:{target.value}:{self.POLICY_VERSION}"
        decision_id = f"DEC_{uuid.uuid5(uuid.NAMESPACE_URL, key).hex[:16].upper()}"
        reduction_pct = (
            assessment.suggested_reduction_pct
            if target == ControlAction.REDUCE
            else (100.0 if target == ControlAction.EMERGENCY_STOP else 0.0)
        )
        return ControlDecision(
            policy_version=self.POLICY_VERSION,
            decision_id=decision_id,
            idempotency_key=key,
            assessment_id=assessment.assessment_id,
            bot_id=assessment.bot_id,
            asset=assessment.asset,
            timestamp=now,
            action=target,
            execution_mode=self.mode,
            reduction_pct=reduction_pct,
            reason=reason,
            triggered_by_dimensions=triggered,
            cooldown_seconds=self.cooldown_seconds,
            execution_status=status,
            authorization_required=self.mode == ExecutionMode.AUTOMATED
            and target not in (ControlAction.MONITOR, ControlAction.WARN),
        )
