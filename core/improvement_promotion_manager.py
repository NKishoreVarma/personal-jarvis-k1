"""
Improvement Promotion Manager for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Coordinates promotion lifecycle: CANDIDATE -> TESTING -> VERIFIED -> APPROVED -> ACTIVE.
Enforces rule: High-risk improvements require explicit user approval, and working versions remain recoverable.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

from core.action_contract import RiskLevel
from core.improvement_opportunity_contract import (
    ImprovementOpportunityContract,
    ImprovementState,
)


class ImprovementPromotionManager:
    """
    Manages promotion, activation, rejection, and rollback of verified workflow improvements.
    """

    def __init__(self):
        self._improvements: Dict[str, ImprovementOpportunityContract] = {}
        self._active_improvements: Dict[str, ImprovementOpportunityContract] = {}
        self._rollback_history: List[Dict] = []

    def register_candidate(self, candidate: ImprovementOpportunityContract) -> None:
        self._improvements[candidate.opportunity_id] = candidate

    def activate_improvement(
        self,
        opportunity_id: str,
        user_explicit_approval: bool = False,
    ) -> Tuple[bool, str]:
        """
        Promotes a VERIFIED candidate to APPROVED / ACTIVE.
        """
        cand = self._improvements.get(opportunity_id)
        if not cand:
            return False, "Opportunity not found."

        if cand.state not in [ImprovementState.VERIFIED, ImprovementState.APPROVED]:
            return False, f"Cannot activate improvement in '{cand.state.value}' state. Must be VERIFIED."

        # High-risk operations require explicit human approval
        if cand.risk_level in [RiskLevel.HIGH_RISK, RiskLevel.DESTRUCTIVE] and not user_explicit_approval:
            cand.state = ImprovementState.APPROVED  # Awaiting human confirmation
            return False, "High-risk improvement requires explicit human approval before activation."

        cand.state = ImprovementState.ACTIVE
        cand.updated_at = time.time()
        self._active_improvements[cand.affected_component] = cand
        return True, f"Improvement '{cand.title}' activated successfully."

    def reject_improvement(self, opportunity_id: str, reason: str = "") -> bool:
        cand = self._improvements.get(opportunity_id)
        if cand:
            cand.state = ImprovementState.REJECTED
            cand.updated_at = time.time()
            return True
        return False

    def rollback_improvement(self, opportunity_id: str, reason: str = "") -> bool:
        """
        Reverts an active improvement to ROLLED_BACK and restores baseline workflow.
        """
        cand = self._improvements.get(opportunity_id)
        if cand and cand.state == ImprovementState.ACTIVE:
            cand.state = ImprovementState.ROLLED_BACK
            cand.updated_at = time.time()
            self._active_improvements.pop(cand.affected_component, None)
            self._rollback_history.append({
                "opportunity_id": opportunity_id,
                "affected_component": cand.affected_component,
                "reason": reason,
                "timestamp": time.time(),
            })
            return True
        return False

    def get_active_improvement(self, component: str) -> Optional[ImprovementOpportunityContract]:
        return self._active_improvements.get(component)

    def list_all(self) -> List[ImprovementOpportunityContract]:
        return list(self._improvements.values())

    def clear(self) -> None:
        self._improvements.clear()
        self._active_improvements.clear()
        self._rollback_history.clear()


# Global singleton instance
improvement_promotion_manager = ImprovementPromotionManager()
