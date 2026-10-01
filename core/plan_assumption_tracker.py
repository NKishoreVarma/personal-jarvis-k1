"""
Plan Assumption Tracker for MARK XLVIII / JARVIS.
Tracks explicit assumptions underlying generated plans, validates them against live observations,
and invalidates dependent future steps when assumptions are contradicted.
Enforces invariant: CURRENT OBSERVATION > PLAN ASSUMPTION.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AssumptionState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    EXPIRED = "EXPIRED"


@dataclass
class PlanAssumption:
    assumption_id: str
    plan_id: str
    description: str
    confidence: float = 0.90
    source: str = "strategy_generator"
    verification_state: AssumptionState = AssumptionState.UNVERIFIED
    dependent_steps: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    contradiction_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "plan_id": self.plan_id,
            "description": self.description,
            "confidence": self.confidence,
            "source": self.source,
            "verification_state": self.verification_state.value,
            "dependent_steps": self.dependent_steps,
            "contradiction_reason": self.contradiction_reason,
        }


class PlanAssumptionTracker:
    """
    Monitors and validates assumptions for active plans.
    """

    def __init__(self):
        self._assumptions: Dict[str, PlanAssumption] = {}  # assumption_id -> PlanAssumption
        self._plan_assumptions: Dict[str, List[str]] = {}  # plan_id -> list of assumption_ids

    def register_assumption(
        self,
        plan_id: str,
        description: str,
        dependent_steps: Optional[List[str]] = None,
        confidence: float = 0.90,
    ) -> PlanAssumption:
        """Registers a new assumption for a plan."""
        assump = PlanAssumption(
            assumption_id=f"asmp_{uuid.uuid4().hex[:8]}",
            plan_id=plan_id,
            description=description,
            confidence=confidence,
            dependent_steps=dependent_steps or [],
        )
        self._assumptions[assump.assumption_id] = assump
        if plan_id not in self._plan_assumptions:
            self._plan_assumptions[plan_id] = []
        self._plan_assumptions[plan_id].append(assump.assumption_id)
        return assump

    def verify_assumption(self, assumption_id: str) -> None:
        """Marks assumption verified by observation."""
        assump = self._assumptions.get(assumption_id)
        if assump:
            assump.verification_state = AssumptionState.VERIFIED

    def contradict_assumption(self, assumption_id: str, reason: str) -> List[str]:
        """
        Marks assumption contradicted and returns affected dependent step IDs.
        """
        assump = self._assumptions.get(assumption_id)
        if not assump:
            return []

        assump.verification_state = AssumptionState.CONTRADICTED
        assump.contradiction_reason = reason
        return list(assump.dependent_steps)

    def get_plan_assumptions(self, plan_id: str) -> List[PlanAssumption]:
        ids = self._plan_assumptions.get(plan_id, [])
        return [self._assumptions[i] for i in ids if i in self._assumptions]

    def has_contradicted_assumptions(self, plan_id: str) -> bool:
        for a in self.get_plan_assumptions(plan_id):
            if a.verification_state == AssumptionState.CONTRADICTED:
                return True
        return False

    def clear_plan(self, plan_id: str) -> None:
        ids = self._plan_assumptions.pop(plan_id, [])
        for i in ids:
            self._assumptions.pop(i, None)

    def clear_all(self) -> None:
        self._assumptions.clear()
        self._plan_assumptions.clear()


# Global singleton instance
plan_assumption_tracker = PlanAssumptionTracker()
