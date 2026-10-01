"""
Natural Response Selector for MARK XLVIII / JARVIS.
The central decision engine deciding whether to speak, what type of response to give,
and when silence is the optimal user experience.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from core.response_length_policy import ResponseVerbosity, response_length_policy
from core.voice_personality_engine import voice_personality_engine


class SelectedResponseType(str, Enum):
    SILENT = "SILENT"
    SHORT_ACK = "SHORT_ACK"
    PROGRESS = "PROGRESS"
    COMPLETION = "COMPLETION"
    FAILURE = "FAILURE"
    CLARIFICATION = "CLARIFICATION"
    STATE_UPDATE = "STATE_UPDATE"
    REDUNDANCY = "REDUNDANCY"


class NaturalResponseSelector:
    """
    Evaluates execution context and user speech to choose the most concise, helpful response type.
    """

    QUIET_KEYWORDS = {"quietly", "silently", "in the background", "silent", "no audio", "don't speak", "dont speak", "shh"}
    NOTIFICATION_KEYWORDS = {"tell me when", "notify me", "let me know", "when it's ready", "when it finishes", "alert me", "ping me"}

    def is_quiet_requested(self, raw_text: str) -> bool:
        raw_lower = raw_text.lower()
        return any(kw in raw_lower for kw in self.QUIET_KEYWORDS)

    def is_notification_requested(self, raw_text: str) -> bool:
        raw_lower = raw_text.lower()
        return any(kw in raw_lower for kw in self.NOTIFICATION_KEYWORDS)

    def select_initial_response(
        self,
        turn_id: str,
        task_type: str,
        entities: Dict[str, Any],
        raw_text: str,
        is_already_running: bool = False,
        is_already_open: bool = False,
        is_ambiguous: bool = False,
    ) -> Dict[str, Any]:
        """
        Selects the initial response type and generated text upon command commitment.
        Decision executes in < 1ms.
        """
        # 1. Quiet execution requested
        if self.is_quiet_requested(raw_text):
            return {
                "response_type": SelectedResponseType.SILENT,
                "spoken_text": "",
                "requires_speech": False,
            }

        # 2. Ambiguity resolution
        if is_ambiguous:
            text = voice_personality_engine.render_response(
                response_type="CLARIFICATION",
                task_type=task_type,
                entities=entities,
            )
            return {
                "response_type": SelectedResponseType.CLARIFICATION,
                "spoken_text": text,
                "requires_speech": True,
            }

        # 3. Already running / redundant request
        if is_already_running:
            text = voice_personality_engine.render_response(
                response_type="REDUNDANCY",
                task_type=task_type,
                entities=entities,
            )
            return {
                "response_type": SelectedResponseType.REDUNDANCY,
                "spoken_text": text,
                "requires_speech": True,
            }

        # 4. App is already open
        if is_already_open:
            text = voice_personality_engine.render_response(
                response_type="STATE_UPDATE",
                task_type=task_type,
                entities=entities,
            )
            return {
                "response_type": SelectedResponseType.STATE_UPDATE,
                "spoken_text": text,
                "requires_speech": True,
            }

        # 5. Standard Short Acknowledgement
        verbosity = response_length_policy.determine_verbosity(raw_text)
        text = voice_personality_engine.render_response(
            response_type="ACKNOWLEDGEMENT",
            task_type=task_type,
            entities=entities,
            verbosity=verbosity,
        )
        return {
            "response_type": SelectedResponseType.SHORT_ACK,
            "spoken_text": text,
            "requires_speech": True,
        }

    def select_completion_response(
        self,
        turn_id: str,
        task_type: str,
        entities: Dict[str, Any],
        raw_text: str,
        success: bool = True,
        error: Optional[str] = None,
        is_visible_action: bool = False,
    ) -> Dict[str, Any]:
        """
        Selects whether and what to speak when execution completes or fails.
        Enforces the Silence Policy for fast, visible actions.
        """
        # 1. Quiet requested: Silence even on completion (unless critical failure)
        if self.is_quiet_requested(raw_text) and success:
            return {
                "response_type": SelectedResponseType.SILENT,
                "spoken_text": "",
                "requires_speech": False,
            }

        # 2. Failure: Always speak calm, concise error
        if not success:
            text = voice_personality_engine.render_response(
                response_type="FAILURE",
                task_type=task_type,
                entities=entities,
                error=error,
            )
            return {
                "response_type": SelectedResponseType.FAILURE,
                "spoken_text": text,
                "requires_speech": True,
            }

        # 3. User explicitly requested notification ("tell me when it's ready")
        explicit_notif = self.is_notification_requested(raw_text)
        if explicit_notif:
            text = voice_personality_engine.render_response(
                response_type="COMPLETION",
                task_type=task_type,
                entities=entities,
            )
            return {
                "response_type": SelectedResponseType.COMPLETION,
                "spoken_text": text,
                "requires_speech": True,
            }

        # 4. Fast, visible application actions (e.g. "open Chrome") -> SILENCE on completion
        if is_visible_action or task_type in ("OPEN_APP", "LAUNCH_APP", "CLOSE_APP", "QUIT_APP"):
            return {
                "response_type": SelectedResponseType.SILENT,
                "spoken_text": "",
                "requires_speech": False,
            }

        # 5. Long-running background project (e.g. "run FLOW") -> Speak verified port
        if task_type in ("RUN_PROJECT", "PROJECT_OPERATION"):
            text = voice_personality_engine.render_response(
                response_type="COMPLETION",
                task_type=task_type,
                entities=entities,
            )
            return {
                "response_type": SelectedResponseType.COMPLETION,
                "spoken_text": text,
                "requires_speech": True,
            }

        # 6. Default: SILENT on completion to avoid chatbot chatter
        return {
            "response_type": SelectedResponseType.SILENT,
            "spoken_text": "",
            "requires_speech": False,
        }


# Global singleton instance
natural_response_selector = NaturalResponseSelector()
