"""
Temporal Safety Gate for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Enforces the inviolable safety rule: Time != Authority (Due or scheduled items cannot bypass ActionContract).
"""

from __future__ import annotations

from typing import Optional, Tuple

from core.action_contract import RiskLevel
from core.temporal_contract import TemporalContract, TemporalState


class TemporalSafetyGate:
    """
    Guarantees temporal triggers and scheduled reminders do not execute unapproved mutations.
    """

    def validate_temporal_execution(
        self,
        contract: TemporalContract,
        user_explicit_approval: bool = False,
    ) -> Tuple[bool, str]:
        """
        Validates whether a triggered temporal contract is permissible for execution.
        """
        # 1. Reject expired items
        if contract.is_expired():
            return False, "Rejected: Temporal task has expired."

        # 2. Reject cancelled items
        if contract.state == TemporalState.CANCELLED:
            return False, "Rejected: Temporal task was cancelled by user."

        # 3. High-risk mutations require explicit human confirmation
        if contract.approval_required or contract.required_authority in ["LOCAL_MUTATION", "HIGH_RISK"]:
            if not user_explicit_approval:
                return False, "Scheduled high-risk actions require explicit user approval before execution."

        return True, "Temporal task validated for execution."


# Global singleton instance
temporal_safety_gate = TemporalSafetyGate()
