"""
Self-Improvement Governor for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Acts as the central safety boundary ensuring continuous learning preserves ActionContract and ApprovalStore invariants.
Decision outputs: ALLOW_CANDIDATE, REQUIRE_TESTING, REQUIRE_APPROVAL, REJECT, ROLLBACK.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from core.action_contract import RiskLevel
from core.improvement_opportunity_contract import (
    ImprovementOpportunityContract,
    ImprovementState,
)


class GovernanceDecision(str, Enum):
    ALLOW_CANDIDATE = "ALLOW_CANDIDATE"
    REQUIRE_TESTING = "REQUIRE_TESTING"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REJECT = "REJECT"
    ROLLBACK = "ROLLBACK"


class SelfImprovementGovernor:
    """
    Evaluates learning and improvement operations to guarantee safety invariants are preserved.
    """

    def __init__(self):
        self.learning_enabled: bool = True

    def set_learning_enabled(self, enabled: bool) -> None:
        self.learning_enabled = enabled

    def evaluate_proposal(
        self,
        candidate: ImprovementOpportunityContract,
        user_explicit_approval: bool = False,
    ) -> Tuple[GovernanceDecision, str]:
        """
        Enforces governance rules over proposed improvement candidates.
        """
        if not self.learning_enabled:
            return GovernanceDecision.REJECT, "Continuous learning is disabled by user policy."

        # 1. Reject speculative candidates lacking evidence
        if not candidate.evidence_references and candidate.confidence < 0.80:
            return GovernanceDecision.REJECT, "Rejected: Speculative candidate lacks empirical evidence references."

        # 2. Reject attempts to alter authority rules or bypass ActionContract
        if candidate.metadata.get("modify_safety_rules", False) or candidate.metadata.get("expand_permissions", False):
            return GovernanceDecision.REJECT, "Rejected: Learning cannot modify safety authority or expand permissions."

        # 3. High-risk operations require explicit human approval
        if candidate.risk_level in [RiskLevel.HIGH_RISK, RiskLevel.DESTRUCTIVE]:
            if not user_explicit_approval:
                return GovernanceDecision.REQUIRE_APPROVAL, "High-risk improvement requires explicit human approval."

        # 4. If candidate has not been sandboxed/tested yet, require testing
        if candidate.state == ImprovementState.CANDIDATE:
            return GovernanceDecision.REQUIRE_TESTING, "Candidate must undergo isolated sandbox simulation before activation."

        return GovernanceDecision.ALLOW_CANDIDATE, "Candidate approved for progression."

    def get_status(self) -> Dict[str, Any]:
        """Provides status summary for governance telemetry."""
        return {
            "learning_enabled": self.learning_enabled,
            "rollback_protection": True,
            "governance_mode": "ACTIVE",
        }


# Global singleton instance
self_improvement_governor = SelfImprovementGovernor()
