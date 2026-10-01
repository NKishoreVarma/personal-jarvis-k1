"""
Goal Contract for Autonomous Problem Solving in MARK XLVIII / JARVIS.
Explicitly separates raw user intent from final verifiable outcome and success criteria.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GoalStatus(str, Enum):
    PENDING = "PENDING"
    UNDERSTANDING = "UNDERSTANDING"
    OBSERVING = "OBSERVING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class GoalContract:
    goal_id: str
    turn_id: str
    original_request: str
    normalized_goal: str
    desired_outcome: str
    constraints: List[str] = field(default_factory=list)
    success_conditions: List[str] = field(default_factory=list)
    risk_budget: str = "LOW"  # READ_ONLY, LOW, REVERSIBLE, HIGH, DESTRUCTIVE
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = field(default_factory=lambda: time.monotonic() + 300.0)
    status: GoalStatus = GoalStatus.PENDING
    target_project: Optional[str] = None
    target_app: Optional[str] = None
    verification_evidence: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at

    def update_status(self, new_status: GoalStatus) -> None:
        self.status = new_status

    def mark_completed(self, evidence: Dict[str, Any]) -> None:
        self.status = GoalStatus.COMPLETED
        self.verification_evidence.update(evidence)

    def mark_failed(self, reason: str) -> None:
        self.status = GoalStatus.FAILED
        self.failure_reason = reason


def create_goal_contract(
    turn_id: str,
    original_request: str,
    normalized_goal: str,
    desired_outcome: str,
    success_conditions: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
    risk_budget: str = "LOW",
    target_project: Optional[str] = None,
    target_app: Optional[str] = None,
    ttl_sec: float = 300.0,
) -> GoalContract:
    return GoalContract(
        goal_id=f"goal_{uuid.uuid4().hex[:8]}",
        turn_id=turn_id,
        original_request=original_request,
        normalized_goal=normalized_goal,
        desired_outcome=desired_outcome,
        constraints=constraints or [],
        success_conditions=success_conditions or ["process_running", "port_detected", "health_check_passed"],
        risk_budget=risk_budget,
        target_project=target_project,
        target_app=target_app,
        expires_at=time.monotonic() + ttl_sec,
    )
