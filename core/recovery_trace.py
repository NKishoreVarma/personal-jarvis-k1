"""
Recovery Trace for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Maintains structured recovery audit logs and formats concise user-facing summaries
without exposing raw chain-of-thought or technical internal states.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.runtime_state_store import runtime_state_store


class RecoveryEventType(str, Enum):
    RUNTIME_STARTED = "RUNTIME_STARTED"
    RUNTIME_CRASH_DETECTED = "RUNTIME_CRASH_DETECTED"
    TASK_RECOVERY_STARTED = "TASK_RECOVERY_STARTED"
    CURRENT_STATE_OBSERVED = "CURRENT_STATE_OBSERVED"
    CHECKPOINT_VALIDATED = "CHECKPOINT_VALIDATED"
    TASK_ALREADY_COMPLETED = "TASK_ALREADY_COMPLETED"
    TASK_RESUMED = "TASK_RESUMED"
    PLAN_REBUILT = "PLAN_REBUILT"
    RECOVERY_FAILED = "RECOVERY_FAILED"


@dataclass
class RecoveryEvent:
    event_id: str
    event_type: RecoveryEventType
    goal_id: str
    project_name: str
    description: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "goal_id": self.goal_id,
            "project_name": self.project_name,
            "description": self.description,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class RecoveryTrace:
    """
    Logs recovery operations and generates human-readable recovery summaries.
    """

    def __init__(self):
        self._events: List[RecoveryEvent] = []

    def record_event(
        self,
        event_type: RecoveryEventType,
        goal_id: str,
        project_name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RecoveryEvent:
        """Records and persists an audit event."""
        ev = RecoveryEvent(
            event_id=f"rec_ev_{uuid.uuid4().hex[:6]}",
            event_type=event_type,
            goal_id=goal_id,
            project_name=project_name,
            description=description,
            metadata=metadata or {},
        )
        self._events.append(ev)
        runtime_state_store.record_recovery(ev.to_dict())
        return ev

    def format_user_explanation(self, project_name: str = "FLOW") -> str:
        """
        Formats a concise, natural voice explanation for what happened during recovery.
        """
        for ev in reversed(self._events):
            if ev.project_name.lower() == project_name.lower():
                if ev.event_type == RecoveryEventType.TASK_ALREADY_COMPLETED:
                    return f"{project_name} was already running when I restarted, so I verified it instead of starting it again."
                elif ev.event_type == RecoveryEventType.TASK_RESUMED:
                    return f"Recovered {project_name} execution and resumed from the last verified checkpoint."
                elif ev.event_type == RecoveryEventType.PLAN_REBUILT:
                    return f"The environment changed after restart, so I updated the plan for {project_name}."

        return "Runtime is healthy. No tasks need recovery."

    def list_events(self) -> List[RecoveryEvent]:
        return list(self._events)

    def clear_all(self) -> None:
        self._events.clear()


# Global singleton instance
recovery_trace = RecoveryTrace()
