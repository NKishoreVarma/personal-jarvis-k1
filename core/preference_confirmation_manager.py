"""
Preference Confirmation Manager for Human Collaboration in MARK XLVIII / JARVIS.
Coordinates state transitions from INFERRED to CONFIRMED based on user feedback and consistency.
"""

from __future__ import annotations

import time
from typing import Dict, Optional

from core.user_preference_contract import (
    PreferenceState,
    UserPreferenceContract,
)


class PreferenceConfirmationManager:
    """
    Manages explicit user confirmations and validates long-term stability before promotion.
    """

    def __init__(self):
        self._confirmed_preferences: Dict[str, UserPreferenceContract] = {}

    def confirm_preference(self, preference: UserPreferenceContract) -> UserPreferenceContract:
        """
        Promotes an inferred preference to CONFIRMED state.
        """
        preference.confirm()
        pref_key = f"{preference.project_scope or 'global'}:{preference.key}"
        self._confirmed_preferences[pref_key] = preference
        return preference

    def get_confirmed_preference(self, key: str, project_scope: Optional[str] = None) -> Optional[UserPreferenceContract]:
        pref_key = f"{project_scope or 'global'}:{key}"
        return self._confirmed_preferences.get(pref_key)

    def invalidate_preference(self, key: str, project_scope: Optional[str] = None) -> bool:
        pref_key = f"{project_scope or 'global'}:{key}"
        if pref_key in self._confirmed_preferences:
            self._confirmed_preferences[pref_key].verification_state = PreferenceState.INVALIDATED
            return True
        return False

    def clear(self) -> None:
        self._confirmed_preferences.clear()


# Global singleton instance
preference_confirmation_manager = PreferenceConfirmationManager()
