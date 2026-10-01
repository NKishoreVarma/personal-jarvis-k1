"""
Plan Step Contract for MARK XLVIII / JARVIS.
Represents discrete, dependency-aware executable steps within a PlanContract.
Tracks preconditions, authority scopes, risk levels, and individual verification methods.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanStepStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    PREPARING = "PREPARING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


@dataclass
class PlanStepContract:
    step_id: str
    plan_id: str
    goal_id: str
    title: str
    objective: str
    action_type: str  # read_only, mutating, prepare, verify
    authority_required: str = "READ_ONLY"  # READ_ONLY, PREPARE_ONLY, EXECUTE_LOW_RISK, APPROVAL_REQUIRED
    risk_level: str = "low_risk"
    dependencies: List[str] = field(default_factory=list)  # list of prerequisite step_ids
    preconditions: Dict[str, Any] = field(default_factory=dict)
    expected_result: str = ""
    verification_method: str = "automatic"
    fallback_strategy: Optional[str] = None
    status: PlanStepStatus = PlanStepStatus.PENDING
    retry_count: int = 0
    max_retries: int = 2
    parameters: Dict[str, Any] = field(default_factory=dict)
    parent_step_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def is_mutating(self) -> bool:
        return self.action_type == "mutating" or self.authority_required in ["EXECUTE_LOW_RISK", "APPROVAL_REQUIRED"]

    @property
    def is_terminal(self) -> bool:
        return self.status in [PlanStepStatus.COMPLETED, PlanStepStatus.FAILED, PlanStepStatus.SKIPPED, PlanStepStatus.CANCELLED]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "plan_id": self.plan_id,
            "goal_id": self.goal_id,
            "parent_step_id": self.parent_step_id,
            "title": self.title,
            "objective": self.objective,
            "action_type": self.action_type,
            "authority_required": self.authority_required,
            "risk_level": self.risk_level,
            "dependencies": self.dependencies,
            "preconditions": self.preconditions,
            "expected_result": self.expected_result,
            "verification_method": self.verification_method,
            "fallback_strategy": self.fallback_strategy,
            "status": self.status.value if isinstance(self.status, PlanStepStatus) else str(self.status),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "parameters": self.parameters,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


def create_plan_step_contract(
    plan_id: str,
    goal_id: str,
    title: str,
    objective: str,
    action_type: str = "read_only",
    authority_required: str = "READ_ONLY",
    risk_level: str = "low_risk",
    dependencies: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    expected_result: str = "",
    verification_method: str = "automatic",
    parent_step_id: Optional[str] = None,
) -> PlanStepContract:
    return PlanStepContract(
        step_id=f"step_{uuid.uuid4().hex[:8]}",
        plan_id=plan_id,
        goal_id=goal_id,
        parent_step_id=parent_step_id,
        title=title,
        objective=objective,
        action_type=action_type,
        authority_required=authority_required,
        risk_level=risk_level,
        dependencies=dependencies or [],
        parameters=parameters or {},
        expected_result=expected_result,
        verification_method=verification_method,
    )
