"""
Outcome Contract for Autonomous Continuous Learning & Outcome Evaluation in MARK XLVIII / JARVIS.
Defines formal records for task outcomes, verification states, and evidence provenance.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class OutcomeType(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    REGRESSION = "REGRESSION"
    UNEXPECTED_RESULT = "UNEXPECTED_RESULT"


class VerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    SELF_REPORTED = "SELF_REPORTED"
    OBSERVED = "OBSERVED"
    CORROBORATED = "CORROBORATED"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"


@dataclass
class OutcomeContract:
    outcome_id: str
    goal_id: str = ""
    task_id: str = ""
    project_id: str = "GLOBAL"
    session_id: str = "default_session"
    skill_id: str = ""
    plan_id: str = ""
    action_ids: List[str] = field(default_factory=list)
    outcome_type: OutcomeType = OutcomeType.SUCCESS
    expected_outcome: str = ""
    actual_outcome: str = ""
    verification_state: VerificationState = VerificationState.UNVERIFIED
    success_score: float = 1.0
    duration: float = 0.0
    evidence_references: List[str] = field(default_factory=list)
    failure_reason: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_verified(self) -> bool:
        return self.verification_state == VerificationState.VERIFIED and len(self.evidence_references) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "goal_id": self.goal_id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "skill_id": self.skill_id,
            "plan_id": self.plan_id,
            "action_ids": self.action_ids,
            "outcome_type": self.outcome_type.value,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "verification_state": self.verification_state.value,
            "success_score": round(self.success_score, 3),
            "duration": round(self.duration, 3),
            "evidence_references": self.evidence_references,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
            "metadata": self.metadata,
        }


def create_outcome_contract(
    expected_outcome: str,
    actual_outcome: str,
    outcome_type: OutcomeType = OutcomeType.SUCCESS,
    verification_state: VerificationState = VerificationState.UNVERIFIED,
    goal_id: str = "",
    task_id: str = "",
    project_id: str = "GLOBAL",
    skill_id: str = "",
    plan_id: str = "",
    action_ids: Optional[List[str]] = None,
    success_score: float = 1.0,
    duration: float = 0.0,
    evidence_references: Optional[List[str]] = None,
    failure_reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[OutcomeContract], str]:
    now = time.time()
    ev_refs = evidence_references or []

    # Rule: VERIFIED outcomes MUST contain evidence references
    if verification_state == VerificationState.VERIFIED and not ev_refs:
        return None, "Validation error: VERIFIED state requires supporting evidence references."

    # Rule: Self-reported success cannot automatically become VERIFIED without observation
    if verification_state == VerificationState.SELF_REPORTED and outcome_type == OutcomeType.VERIFIED_SUCCESS:
        return None, "Validation error: Self-reported success cannot be classified as VERIFIED_SUCCESS."

    contract = OutcomeContract(
        outcome_id=f"out_{uuid.uuid4().hex[:8]}",
        goal_id=goal_id,
        task_id=task_id,
        project_id=project_id,
        skill_id=skill_id,
        plan_id=plan_id,
        action_ids=action_ids or [],
        outcome_type=outcome_type,
        expected_outcome=expected_outcome,
        actual_outcome=actual_outcome,
        verification_state=verification_state,
        success_score=success_score,
        duration=duration,
        evidence_references=ev_refs,
        failure_reason=failure_reason,
        created_at=now,
        verified_at=now if verification_state == VerificationState.VERIFIED else None,
        metadata=metadata or {},
    )
    return contract, "Outcome contract validated and created successfully."
