"""
Plan Contract for MARK XLVIII / JARVIS.
Defines the formal schema for autonomous execution plans, tracking objectives,
strategies, lifecycles, assumptions, and verification criteria.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    OBSERVING = "OBSERVING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    ADAPTING = "ADAPTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class PlanContract:
    plan_id: str
    goal_id: str
    turn_id: str
    objective: str
    strategy: str
    status: PlanStatus = PlanStatus.DRAFT
    risk_level: str = "low_risk"
    estimated_steps: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300.0)  # 5 min TTL
    assumptions: List[str] = field(default_factory=list)
    evidence_dependencies: List[str] = field(default_factory=list)
    selected_reason: str = ""
    fallback_plan_id: Optional[str] = None
    verification_criteria: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal_id": self.goal_id,
            "turn_id": self.turn_id,
            "objective": self.objective,
            "strategy": self.strategy,
            "status": self.status.value if isinstance(self.status, PlanStatus) else str(self.status),
            "risk_level": self.risk_level,
            "estimated_steps": self.estimated_steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "assumptions": self.assumptions,
            "evidence_dependencies": self.evidence_dependencies,
            "selected_reason": self.selected_reason,
            "fallback_plan_id": self.fallback_plan_id,
            "verification_criteria": self.verification_criteria,
            "is_expired": self.is_expired(),
        }


def create_plan_contract(
    goal_id: str,
    turn_id: str,
    objective: str,
    strategy: str,
    risk_level: str = "low_risk",
    estimated_steps: int = 1,
    assumptions: Optional[List[str]] = None,
    evidence_dependencies: Optional[List[str]] = None,
    selected_reason: str = "",
    verification_criteria: Optional[Dict[str, Any]] = None,
    ttl_seconds: float = 300.0,
) -> PlanContract:
    now = time.time()
    return PlanContract(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        goal_id=goal_id,
        turn_id=turn_id,
        objective=objective,
        strategy=strategy,
        status=PlanStatus.DRAFT,
        risk_level=risk_level,
        estimated_steps=estimated_steps,
        created_at=now,
        updated_at=now,
        expires_at=now + ttl_seconds,
        assumptions=assumptions or [],
        evidence_dependencies=evidence_dependencies or [],
        selected_reason=selected_reason,
        verification_criteria=verification_criteria or {},
    )
