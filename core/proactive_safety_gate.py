"""
Proactive Safety Gate for Proactive Task Orchestration in MARK XLVIII / JARVIS.
Screens candidate opportunities against safety invariants and authority boundaries before presentation.
"""

from __future__ import annotations

from typing import Optional, Tuple

from core.action_contract import RiskLevel
from core.opportunity_dismissal_manager import opportunity_dismissal_manager
from core.proactive_opportunity_contract import ProactiveOpportunityContract


class ProactiveSafetyGate:
    """
    Guarantees proactive suggestions never trigger unauthorized mutations or bypass approvals.
    """

    def validate_opportunity_for_suggestion(
        self,
        opportunity: ProactiveOpportunityContract,
    ) -> Tuple[bool, str]:
        """
        Ensures opportunity is evidence-backed, active, not dismissed, and not a destructive autonomous mutation.
        """
        # 1. Reject dismissed opportunities
        if opportunity_dismissal_manager.is_suppressed(opportunity):
            return False, "Opportunity is suppressed under active dismissal policy."

        # 2. Reject expired opportunities
        if opportunity.is_expired():
            return False, "Opportunity has expired."

        # 3. Reject speculative opportunities lacking evidence
        if not opportunity.evidence_references and opportunity.confidence < 0.80:
            return False, "Rejected: Speculative opportunity lacks verified supporting evidence."

        # 4. Proactivity cannot autonomously execute destructive operations
        if opportunity.risk_level == RiskLevel.DESTRUCTIVE:
            return False, "Rejected: Destructive operations cannot be proactively staged without prior human direction."

        return True, "Opportunity approved for proactive suggestion."


# Global singleton instance
proactive_safety_gate = ProactiveSafetyGate()
