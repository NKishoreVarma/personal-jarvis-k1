"""
Approval Preference Manager for Human Collaboration in MARK XLVIII / JARVIS.
Learns confirmation preferences while strictly respecting system safety invariant:
User Preference Cannot Reduce System Safety Requirements.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.action_contract import RiskLevel


class ApprovalPreferenceManager:
    """
    Evaluates whether an action requires confirmation, factoring in user preferences without bypassing safety.
    """

    def requires_explicit_confirmation(
        self,
        risk_level: RiskLevel,
        user_auto_approve_preference: bool = False,
    ) -> Tuple[bool, str]:
        """
        Determines approval requirement.
        CRITICAL SAFETY RULE: High-risk mutations ALWAYS require approval, ignoring auto-approve preferences.
        """
        if risk_level in [RiskLevel.HIGH_RISK, RiskLevel.DESTRUCTIVE]:
            return True, "High-risk actions require explicit human confirmation by security policy."

        if risk_level == RiskLevel.REVERSIBLE:
            if user_auto_approve_preference:
                return False, "Reversible mutation permitted under confirmed user auto-approval preference."
            return True, "Reversible mutation requires confirmation by default policy."

        return False, "Read-only and low-risk operations do not require confirmation."


# Global singleton instance
approval_preference_manager = ApprovalPreferenceManager()
