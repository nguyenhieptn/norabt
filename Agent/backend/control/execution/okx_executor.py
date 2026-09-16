from __future__ import annotations

import logging

from Agent.backend.control.schemas.control_decision import (
    ControlAction,
    ControlDecision,
    ExecutionMode,
    ExecutionStatus,
)

logger = logging.getLogger("ControlExecutor")


class OKXControlExecutor:
    """Fail-closed control boundary. This project currently has no authorized trade adapter."""

    MUTATING_ACTIONS = {
        ControlAction.REDUCE,
        ControlAction.BLOCK_NEW_TRADES,
        ControlAction.PAUSE,
        ControlAction.EMERGENCY_STOP,
    }

    @staticmethod
    def execute(decision: ControlDecision) -> ControlDecision:
        if decision.execution_status == ExecutionStatus.SKIPPED_COOLDOWN:
            decision.execution_details = {
                "note": "Decision suppressed by policy cooldown"
            }
            return decision
        if decision.execution_mode == ExecutionMode.READ_ONLY:
            decision.execution_status = ExecutionStatus.RECORDED_READ_ONLY
            decision.execution_details = {
                "action": decision.action.value,
                "note": "READ_ONLY: assessment recorded; no external request was sent",
            }
            return decision
        if decision.execution_mode == ExecutionMode.ADVISORY:
            decision.execution_status = ExecutionStatus.RECORDED_ADVISORY
            decision.execution_details = {
                "action": decision.action.value,
                "note": "Advisory recorded locally; no notification transport is configured",
            }
            return decision
        if decision.execution_mode == ExecutionMode.AUTOMATED:
            decision.execution_status = ExecutionStatus.DENIED
            decision.execution_details = {
                "action": decision.action.value,
                "reason": "Automated OKX execution is outside the approved capability boundary",
                "external_request_sent": False,
            }
            logger.warning("Denied automated control decision %s", decision.decision_id)
            return decision
        decision.execution_status = ExecutionStatus.FAILED
        decision.execution_details = {
            "reason": "Unknown execution mode",
            "external_request_sent": False,
        }
        return decision
