"""
Conversation Timing Controller for MARK XLVIII / JARVIS.
Enforces the priority hierarchy: USER_SPEECH > CRITICAL_ALERT > CLARIFICATION > FAILURE > DIRECT_ACK > VERIFIED_COMPLETION > PROGRESS.
Guarantees that user speech always interrupts JARVIS and drops stale turn responses.
"""

from __future__ import annotations

import time
from enum import IntEnum
from typing import Any, Optional

from core.response_interruption_manager import response_interruption_manager


class ResponsePriority(IntEnum):
    USER_SPEECH = 1
    CRITICAL_SAFETY_ALERT = 2
    CLARIFICATION = 3
    FAILURE = 4
    DIRECT_ACKNOWLEDGEMENT = 5
    VERIFIED_COMPLETION = 6
    IMPORTANT_PROGRESS = 7
    OPTIONAL_PROGRESS = 8
    BACKGROUND_INFORMATION = 9


class ConversationTimingController:
    """
    Coordinates turn state transitions and timing policies.
    """

    def __init__(self):
        self.active_turn_id: Optional[str] = None
        self.is_user_speaking: bool = False
        self.is_jarvis_speaking: bool = False

    def on_user_speech_start(self, turn_id: str, target_queue: Optional[Any] = None) -> None:
        """
        User begins speaking: Immediately interrupt and cancel all JARVIS speech.
        """
        self.is_user_speaking = True
        self.is_jarvis_speaking = False
        self.active_turn_id = turn_id

        # Hard interrupt on active queue
        response_interruption_manager.interrupt_playback(
            audio_in_queue=target_queue,
            reason="User speech started",
        )

    def on_user_speech_end(self, turn_id: str) -> None:
        """User finishes speaking."""
        self.is_user_speaking = False

    def can_speak(self, priority: ResponsePriority, turn_id: str) -> bool:
        """
        Validates if JARVIS is permitted to speak at this exact moment.
        """
        # User speech always blocks JARVIS speech
        if self.is_user_speaking and priority > ResponsePriority.USER_SPEECH:
            return False

        # Stale turn responses are blocked
        if self.active_turn_id is not None and turn_id != self.active_turn_id:
            # Critical alerts may still pass
            if priority != ResponsePriority.CRITICAL_SAFETY_ALERT:
                return False

        return True

    def on_jarvis_speech_start(self, turn_id: str) -> None:
        self.is_jarvis_speaking = True

    def on_jarvis_speech_end(self, turn_id: str) -> None:
        self.is_jarvis_speaking = False


# Global singleton instance
conversation_timing_controller = ConversationTimingController()
