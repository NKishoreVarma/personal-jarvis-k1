"""
Preference Learning Engine for Human Collaboration in MARK XLVIII / JARVIS.
Identifies recurring behavioral preferences from user interaction traces.
Enforces invariant: Inferred Preference != Confirmed Instruction (Requires repetition >= 2).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from core.collaboration_privacy_gate import collaboration_privacy_gate
from core.user_preference_contract import (
    PreferenceState,
    PreferenceType,
    UserPreferenceContract,
    create_user_preference,
)


class PreferenceLearningEngine:
    """
    Analyzes user directives and interaction telemetry to infer operational preferences.
    """

    def __init__(self, repetition_threshold: int = 2):
        self.learning_enabled: bool = True
        self.repetition_threshold = repetition_threshold
        self._interaction_history: List[Dict[str, Any]] = []
        self._inferred_preferences: Dict[str, UserPreferenceContract] = {}

    def set_learning_enabled(self, enabled: bool) -> None:
        self.learning_enabled = enabled

    def record_interaction(
        self,
        key: str,
        value: Any,
        preference_type: PreferenceType,
        project_scope: Optional[str] = None,
    ) -> Optional[UserPreferenceContract]:
        """
        Records an interaction and produces an INFERRED preference if repeated >= repetition_threshold.
        """
        if not self.learning_enabled:
            return None

        # Privacy screening
        is_safe, _ = collaboration_privacy_gate.validate_preference_candidate(key, value, preference_type)
        if not is_safe:
            return None

        self._interaction_history.append({
            "key": key,
            "value": value,
            "preference_type": preference_type,
            "project_scope": project_scope,
            "timestamp": time.time(),
        })

        # Count occurrences matching key and value
        matches = [
            i for i in self._interaction_history
            if i["key"] == key and i["value"] == value and i["project_scope"] == project_scope
        ]

        if len(matches) >= self.repetition_threshold:
            pref = create_user_preference(
                key=key,
                value=value,
                preference_type=preference_type,
                project_scope=project_scope,
                confidence=min(0.95, 0.70 + 0.10 * len(matches)),
                source="inference",
                verification_state=PreferenceState.INFERRED,
            )
            pref_key = f"{project_scope or 'global'}:{key}"
            self._inferred_preferences[pref_key] = pref
            return pref

        return None

    def get_inferred_preference(self, key: str, project_scope: Optional[str] = None) -> Optional[UserPreferenceContract]:
        pref_key = f"{project_scope or 'global'}:{key}"
        return self._inferred_preferences.get(pref_key)

    def clear(self) -> None:
        self._interaction_history.clear()
        self._inferred_preferences.clear()


# Global singleton instance
preference_learning_engine = PreferenceLearningEngine()
