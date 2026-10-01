"""
User Correction Engine for Human Collaboration in MARK XLVIII / JARVIS.
Processes direct user corrections as highest-value preference learning signals.
Enforces invariant: Current Correction > Inferred Preference.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.preference_confirmation_manager import preference_confirmation_manager
from core.user_preference_contract import (
    PreferenceState,
    PreferenceType,
    UserPreferenceContract,
    create_user_preference,
)


class UserCorrectionEngine:
    """
    Parses user correction signals and immediately creates confirmed preferences.
    """

    def apply_user_correction(
        self,
        key: str,
        corrected_value: Any,
        preference_type: PreferenceType = PreferenceType.EXECUTION_STYLE,
        project_scope: Optional[str] = None,
    ) -> UserPreferenceContract:
        """
        Creates and immediately confirms a preference derived from a direct user correction.
        """
        pref = create_user_preference(
            key=key,
            value=corrected_value,
            preference_type=preference_type,
            project_scope=project_scope,
            confidence=1.0,
            source="correction",
            verification_state=PreferenceState.CONFIRMED,
        )
        return preference_confirmation_manager.confirm_preference(pref)


# Global singleton instance
user_correction_engine = UserCorrectionEngine()
