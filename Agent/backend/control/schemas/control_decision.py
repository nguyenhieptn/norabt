from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ControlAction(str, Enum):
    MONITOR = "MONITOR"
    WARN = "WARN"
    REDUCE = "REDUCE"
    BLOCK_NEW_TRADES = "BLOCK_NEW_TRADES"
    PAUSE = "PAUSE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class ExecutionMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    ADVISORY = "ADVISORY"
    AUTOMATED = "AUTOMATED"


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    SKIPPED_COOLDOWN = "SKIPPED_COOLDOWN"
    RECORDED_READ_ONLY = "RECORDED_READ_ONLY"
    RECORDED_ADVISORY = "RECORDED_ADVISORY"
    DENIED = "DENIED"
    FAILED = "FAILED"


class ControlDecision(BaseModel):
    schema_version: str = "control_decision.v1"
    policy_version: str = "control_policy.v1"
    decision_id: str
    idempotency_key: str
    assessment_id: str
    bot_id: str
    asset: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    action: ControlAction
    execution_mode: ExecutionMode = ExecutionMode.READ_ONLY
    reduction_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    reason: str
    triggered_by_dimensions: List[str] = Field(default_factory=list)
    cooldown_seconds: int = Field(default=300, ge=0)
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    authorization_required: bool = False
    execution_details: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_reduction(self):
        if self.action == ControlAction.REDUCE and self.reduction_pct <= 0:
            raise ValueError("REDUCE requires reduction_pct > 0")
        if self.action != ControlAction.REDUCE and self.reduction_pct not in (
            0.0,
            100.0,
        ):
            raise ValueError(
                "reduction_pct is only valid for REDUCE or full emergency closure"
            )
        return self
