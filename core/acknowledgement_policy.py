"""
Instant Local Voice Acknowledgement Policy for MARK XLVIII / JARVIS.
Provides ultra-fast (<5ms), natural, non-repetitive local spoken acknowledgements
prior to background execution, eliminating cloud round-trips for instant user feedback.
"""

from __future__ import annotations

import random
from enum import Enum
from typing import Dict, List, Optional


class AcknowledgementClass(str, Enum):
    INSTANT_ACTION = "INSTANT_ACTION"
    BACKGROUND_TASK = "BACKGROUND_TASK"
    COMPLEX_AGENT = "COMPLEX_AGENT"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class AcknowledgementPolicy:
    """
    Generates deterministic, low-latency verbal acknowledgements locally.
    """

    BACKGROUND_PHRASES: List[str] = [
        "Okay.",
        "On it.",
        "Right away, sir.",
        "Working on it.",
    ]

    COMPLEX_PHRASES: List[str] = [
        "On it, I'll take care of that.",
        "Understood, running now.",
        "I'll handle that right away.",
    ]

    def get_acknowledgement(
        self,
        ack_class: AcknowledgementClass,
        target_name: Optional[str] = None,
        custom_msg: Optional[str] = None,
    ) -> str:
        """
        Returns a concise, natural acknowledgement string.
        """
        if custom_msg:
            return custom_msg

        if ack_class == AcknowledgementClass.INSTANT_ACTION:
            if target_name:
                return f"Opening {target_name}."
            return "Done."

        if ack_class == AcknowledgementClass.BACKGROUND_TASK:
            if target_name:
                return f"Starting {target_name}."
            return random.choice(self.BACKGROUND_PHRASES)

        if ack_class == AcknowledgementClass.COMPLEX_AGENT:
            return random.choice(self.COMPLEX_PHRASES)

        if ack_class == AcknowledgementClass.APPROVAL_REQUIRED:
            return "This action requires your confirmation. Shall I proceed?"

        return "Okay."


# Global singleton
acknowledgement_policy = AcknowledgementPolicy()
