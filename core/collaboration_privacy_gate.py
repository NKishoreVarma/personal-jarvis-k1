"""
Collaboration Privacy Gate for Human Collaboration in MARK XLVIII / JARVIS.
Screens prospective preference candidates and rejects raw audio, screenshots, credentials,
temporary emotional states, and non-operational personal profiling.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from core.user_preference_contract import PreferenceType, UserPreferenceContract

SENSITIVE_PATTERNS = [
    r"(?i)(bearer\s+[a-z0-9_\-\.]{16,})",
    r"(?i)(password\s*[:=]\s*[^\s]+)",
    r"(?i)(api[_-]?key\s*[:=]\s*[a-z0-9_\-\.]{16,})",
    r"(?i)(secret\s*[:=]\s*[^\s]+)",
    r"(?i)(token\s*[:=]\s*[a-z0-9_\-\.]{16,})",
    r"(?i)(sk-[a-z0-9]{20,})",
]

DISALLOWED_KEYS = {
    "mood", "emotion", "feeling", "anger", "frustration",
    "raw_audio", "screenshot", "camera_feed", "biometric",
    "password", "secret", "private_key"
}


class CollaborationPrivacyGate:
    """
    Guards human collaboration persistence against privacy leaks and profiling.
    """

    def validate_preference_candidate(
        self,
        key: str,
        value: Any,
        preference_type: PreferenceType,
    ) -> Tuple[bool, str]:
        """
        Validates whether a key/value pair is safe and appropriate for operational memory.
        """
        k_lower = key.strip().lower()

        # 1. Reject disallowed non-operational categories
        if k_lower in DISALLOWED_KEYS or any(dis in k_lower for dis in DISALLOWED_KEYS):
            return False, f"Rejected: Key '{key}' is categorized as personal/emotional profiling."

        # 2. Reject sensitive credentials in value
        val_str = str(value)
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, val_str):
                return False, "Rejected: Preference value contains sensitive authentication tokens or credentials."

        # 3. Reject raw media payloads
        if len(val_str) > 2000:
            return False, "Rejected: Preference payload exceeds maximum bounded size (2000 chars)."

        return True, "Preference validated by privacy gate."


# Global singleton instance
collaboration_privacy_gate = CollaborationPrivacyGate()
