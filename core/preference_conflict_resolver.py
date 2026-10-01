"""
Preference Conflict Resolver for Human Collaboration in MARK XLVIII / JARVIS.
Enforces the inviolable decision hierarchy:
CURRENT EXPLICIT INSTRUCTION > CURRENT CORRECTION > CONFIRMED PREFERENCE > INFERRED PREFERENCE > HISTORICAL PATTERN.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.user_preference_contract import (
    PreferenceState,
    UserPreferenceContract,
)

SOURCE_PRIORITY = {
    "explicit_instruction": 5,
    "correction": 4,
    "confirmed_preference": 3,
    "repeated_behavior": 2,
    "inference": 1,
    "historical_pattern": 0,
}


class PreferenceConflictResolver:
    """
    Resolves competing preferences and directives according to authority hierarchy.
    """

    def resolve_preference(
        self,
        current_request_value: Optional[Any] = None,
        correction_value: Optional[Any] = None,
        confirmed_pref: Optional[UserPreferenceContract] = None,
        inferred_pref: Optional[UserPreferenceContract] = None,
    ) -> Tuple[Any, str]:
        """
        Determines winning preference value and authority rationale.
        """
        # 1. Current explicit instruction in prompt always wins
        if current_request_value is not None:
            return current_request_value, "Selected current explicit instruction in user prompt."

        # 2. Direct correction
        if correction_value is not None:
            return correction_value, "Selected value from active user correction."

        # 3. Confirmed preference
        if confirmed_pref and confirmed_pref.verification_state == PreferenceState.CONFIRMED:
            return confirmed_pref.value, f"Selected confirmed preference '{confirmed_pref.key}'."

        # 4. Inferred preference
        if inferred_pref and not inferred_pref.is_stale():
            return inferred_pref.value, f"Selected inferred preference '{inferred_pref.key}' (confidence: {inferred_pref.confidence:.2f})."

        return None, "No active preference found."


# Global singleton instance
preference_conflict_resolver = PreferenceConflictResolver()
