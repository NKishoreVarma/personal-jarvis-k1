"""
Reasoning Trace for MARK XLVIII / JARVIS.
Stores concise, observable operational reasoning events to answer "What did you do?",
"Why did you do that?", and "What is the status?" without storing private chain-of-thought.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TraceEventType(str, Enum):
    GOAL_CREATED = "GOAL_CREATED"
    OBSERVATION_COLLECTED = "OBSERVATION_COLLECTED"
    HYPOTHESIS_CREATED = "HYPOTHESIS_CREATED"
    HYPOTHESIS_SELECTED = "HYPOTHESIS_SELECTED"
    PLAN_CREATED = "PLAN_CREATED"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REPLAN_CREATED = "REPLAN_CREATED"
    GOAL_COMPLETED = "GOAL_COMPLETED"
    GOAL_FAILED = "GOAL_FAILED"


@dataclass
class TraceEvent:
    event_type: TraceEventType
    goal_id: str
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.monotonic)


class ReasoningTrace:
    """
    In-memory operational event logger for explainable autonomous problem solving.
    """

    def __init__(self, max_events: int = 200):
        self.max_events = max_events
        self._events: List[TraceEvent] = []

    def record_event(
        self,
        event_type: TraceEventType,
        goal_id: str,
        details: Dict[str, Any],
    ) -> None:
        """Appends an operational milestone event."""
        if len(self._events) >= self.max_events:
            self._events.pop(0)
        self._events.append(TraceEvent(event_type=event_type, goal_id=goal_id, details=details))

    def get_events(self, goal_id: str) -> List[TraceEvent]:
        return [e for e in self._events if e.goal_id == goal_id]

    def get_summary(self, goal_id: str) -> str:
        """
        Produces a concise human-readable summary of actions taken and final verification outcome.
        """
        events = self.get_events(goal_id)
        if not events:
            return "No actions recorded for this task."

        actions_taken = []
        identified_cause = None
        verified_ok = False
        target_name = "the project"

        for e in events:
            if e.event_type == TraceEventType.HYPOTHESIS_SELECTED:
                cat = e.details.get("category")
                if cat == "PORT_CONFLICT":
                    identified_cause = "the port was occupied by an existing process"
                elif cat == "MISSING_DEPENDENCY":
                    identified_cause = "required dependencies were missing"
                elif cat == "RUNTIME_ERROR":
                    identified_cause = "a runtime exception was crashing the server"
            elif e.event_type == TraceEventType.ACTION_EXECUTED:
                act = e.details.get("action")
                target_name = e.details.get("target", target_name)
                if act == "terminate_conflicting_processes":
                    actions_taken.append("stopped the conflicting process")
                elif act == "restart_project_server":
                    actions_taken.append(f"restarted {target_name}")
                elif act == "install_dependencies":
                    actions_taken.append("installed dependencies")
                elif act == "propose_code_fix":
                    actions_taken.append("applied a code patch")
            elif e.event_type == TraceEventType.VERIFICATION_PASSED:
                verified_ok = True

        if verified_ok:
            cause_phrase = f" {identified_cause.capitalize()}, so I " if identified_cause else "I "
            actions_phrase = " and ".join(actions_taken) if actions_taken else "resolved the issue"
            return f"{target_name} is working now.{cause_phrase}{actions_phrase}. The health check passed."

        return f"Investigated {target_name}. Resolution is pending or encountered an error."


# Global singleton instance
reasoning_trace = ReasoningTrace()
