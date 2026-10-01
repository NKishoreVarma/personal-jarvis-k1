"""
Preference Lifecycle Manager for Human Collaboration in MARK XLVIII / JARVIS.
Tracks preference lifecycle states (CANDIDATE, INFERRED, CONFIRMED, STALE, REJECTED, INVALIDATED)
and handles TTL expirations and preference resets.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from core.preference_confirmation_manager import preference_confirmation_manager
from core.preference_learning_engine import preference_learning_engine
from core.user_preference_contract import (
    PreferenceState,
    UserPreferenceContract,
)


class PreferenceLifecycleManager:
    """
    Coordinates lifecycle transitions, expiration, and user reset directives.
    """

    def __init__(self):
        self._all_preferences: Dict[str, UserPreferenceContract] = {}

    def register_preference(self, preference: UserPreferenceContract) -> None:
        key = f"{preference.project_scope or 'global'}:{preference.key}"
        self._all_preferences[key] = preference

    def reset_all_preferences(self) -> None:
        """
        Clears all learned and confirmed preferences upon explicit user command.
        """
        self._all_preferences.clear()
        preference_learning_engine.clear()
        preference_confirmation_manager.clear()

    def reap_stale_preferences(self, current_time: Optional[float] = None) -> List[str]:
        now = current_time if current_time is not None else time.time()
        stale_keys = []
        for key, pref in list(self._all_preferences.items()):
            if pref.is_stale(current_time=now):
                pref.verification_state = PreferenceState.STALE
                stale_keys.append(key)
        return stale_keys

    def get_preference(self, key: str, project_scope: Optional[str] = None) -> Optional[UserPreferenceContract]:
        full_key = f"{project_scope or 'global'}:{key}"
        return self._all_preferences.get(full_key)


# Global singleton instance
preference_lifecycle_manager = PreferenceLifecycleManager()
