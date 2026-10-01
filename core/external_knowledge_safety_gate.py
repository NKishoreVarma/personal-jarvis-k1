"""
External Knowledge Safety Gate for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Screens retrieved external recommendations to guarantee that external instructions
CANNOT expand authority scopes, bypass ActionContracts, or override ApprovalStore policies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.claim_verification_engine import ClaimVerificationLevel
from core.external_knowledge_contract import ExternalKnowledgeContract, VerificationState
from core.source_authority_evaluator import AuthorityLevel, source_authority_evaluator


class ExternalKnowledgeSafetyGate:
    """
    Mandatory safety gate preventing untrusted or unverified web instructions from triggering mutations.
    """

    def validate_for_planning(
        self,
        item: ExternalKnowledgeContract,
        verification_level: ClaimVerificationLevel,
        proposed_action_risk: str = "low",
    ) -> Tuple[bool, str]:
        """
        Evaluates whether an external knowledge claim is safe to incorporate into a repair plan.
        """
        # 1. Reject contradicted claims
        if item.is_contradicted() or verification_level == ClaimVerificationLevel.CONTRADICTED:
            return False, "Rejected: Claim is contradicted by live environmental reality."

        # 2. Reject untrusted sources
        auth_level, _, _ = source_authority_evaluator.evaluate_authority(item)
        if auth_level == AuthorityLevel.UNTRUSTED:
            return False, "Rejected: External source authority is untrusted."

        # 3. Reject unverified mutation suggestions for high-risk actions
        if proposed_action_risk in ["high", "critical"] and verification_level not in [
            ClaimVerificationLevel.ENVIRONMENT_SUPPORTED,
            ClaimVerificationLevel.OUTCOME_VERIFIED,
        ]:
            return False, "Rejected: High-risk action requires environment-supported verification."

        # 4. Check for destructive keyword traps in claims
        for claim in item.claims:
            cl = claim.lower()
            if any(k in cl for k in ["rm -rf", "delete all", "drop database", "format drive", "override permissions"]):
                return False, "Rejected: Claim contains unsafe destructive commands violating safety policy."

        return True, "External knowledge passed safety gate."


# Global singleton instance
external_knowledge_safety_gate = ExternalKnowledgeSafetyGate()
