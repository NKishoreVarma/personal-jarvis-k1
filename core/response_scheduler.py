"""
Response Scheduler for MARK XLVIII / JARVIS.
Intelligently decides the optimal verbal response strategy (Instant Ack, Silent, Progress, Completion)
based on task complexity, execution duration, and background context without adding blocking latency.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from core.acknowledgement_policy import (
    AcknowledgementClass,
    acknowledgement_policy,
)
from core.zero_wait_handoff import HandoffResult, HandoffStatus


class ResponseMode(str, Enum):
    INSTANT_ACK = "INSTANT_ACK"
    SILENT = "SILENT"
    PROGRESS = "PROGRESS"
    COMPLETION = "COMPLETION"


@dataclass
class ScheduledResponse:
    mode: ResponseMode
    spoken_text: Optional[str]
    should_speak: bool
    reason: str


class ResponseScheduler:
    """
    Evaluates execution context and selects the lowest-friction, non-blocking verbal feedback.
    """

    def schedule_response(
        self,
        task_type: str,
        handoff: Optional[HandoffResult] = None,
        target_name: Optional[str] = None,
        is_background: bool = True,
    ) -> ScheduledResponse:
        """
        Determines whether to speak immediately, stay silent, or deliver a progress acknowledgement.
        """
        # 1. Simple Utility commands (Time / Date / Mute) -> Handled via direct answer, no separate pre-ack needed
        if task_type in ("GET_TIME", "GET_DATE", "CONTROL_COMMAND"):
            return ScheduledResponse(
                mode=ResponseMode.SILENT,
                spoken_text=None,
                should_speak=False,
                reason="Utility command delivers direct answer.",
            )

        # 2. Instant Application Launch (e.g. "open Chrome")
        if task_type in ("OPEN_APP", "CLOSE_APP"):
            ack = acknowledgement_policy.get_acknowledgement(
                AcknowledgementClass.INSTANT_ACTION, target_name=target_name
            )
            return ScheduledResponse(
                mode=ResponseMode.INSTANT_ACK,
                spoken_text=ack,
                should_speak=True,
                reason="Instant app action acknowledgement.",
            )

        # 3. Background Project / Long Server Execution (e.g. "run FLOW")
        if task_type == "RUN_PROJECT":
            # If zero-wait handoff is ready, deliver fast crisp ack
            if handoff and handoff.status == HandoffStatus.READY:
                ack = "Okay."
            else:
                ack = acknowledgement_policy.get_acknowledgement(
                    AcknowledgementClass.BACKGROUND_TASK, target_name=target_name
                )
            return ScheduledResponse(
                mode=ResponseMode.INSTANT_ACK,
                spoken_text=ack,
                should_speak=True,
                reason="Background task immediate acknowledgement.",
            )

        # 4. Complex Multi-Step Agent Operations
        if task_type in ("COMPLEX_AGENT", "COMPLEX_QUERY"):
            ack = acknowledgement_policy.get_acknowledgement(AcknowledgementClass.COMPLEX_AGENT)
            return ScheduledResponse(
                mode=ResponseMode.PROGRESS,
                spoken_text=ack,
                should_speak=True,
                reason="Complex multi-step task progress feedback.",
            )

        # Default fallback
        return ScheduledResponse(
            mode=ResponseMode.INSTANT_ACK,
            spoken_text="Okay.",
            should_speak=True,
            reason="Standard fallback acknowledgement.",
        )


# Global singleton instance
response_scheduler = ResponseScheduler()
