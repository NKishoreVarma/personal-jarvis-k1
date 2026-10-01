"""
Context Contract for MARK XLVIII / JARVIS.
Defines the operational context schema representing active project, application,
task states, verified actions, confidence scores, and strict privacy/TTL boundaries.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ContextTaskState(str, Enum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Regex to detect tokens, API keys, private passwords in context
SECRET_PATTERN = re.compile(
    r"(bearer\s+[a-zA-Z0-9_\-\.]{16,}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{20,}|password\s*=\s*\S+|api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


@dataclass
class ContextContract:
    context_id: str
    turn_id: str
    goal_id: str
    active_project: str = ""
    active_application: str = ""
    active_task: str = ""
    task_state: ContextTaskState = ContextTaskState.IDLE
    visible_context: Dict[str, Any] = field(default_factory=dict)
    recent_verified_actions: List[Dict[str, Any]] = field(default_factory=list)
    user_requested_notifications: bool = True
    current_risk_level: str = "low_risk"
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 60.0)  # 60s TTL
    confidence: float = 0.95
    source_evidence: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def sanitize(self) -> None:
        """Removes secrets or private strings from context fields."""
        if SECRET_PATTERN.search(self.active_task):
            self.active_task = "[REDACTED_TASK]"
        if SECRET_PATTERN.search(self.active_project):
            self.active_project = "[REDACTED_PROJECT]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "turn_id": self.turn_id,
            "goal_id": self.goal_id,
            "active_project": self.active_project,
            "active_application": self.active_application,
            "active_task": self.active_task,
            "task_state": self.task_state.value if isinstance(self.task_state, ContextTaskState) else str(self.task_state),
            "visible_context": self.visible_context,
            "recent_verified_actions": self.recent_verified_actions,
            "user_requested_notifications": self.user_requested_notifications,
            "current_risk_level": self.current_risk_level,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "confidence": self.confidence,
            "source_evidence": self.source_evidence,
            "is_expired": self.is_expired(),
        }


def create_context_contract(
    turn_id: str,
    goal_id: str,
    active_project: str = "",
    active_application: str = "",
    active_task: str = "",
    task_state: ContextTaskState = ContextTaskState.IDLE,
    visible_context: Optional[Dict[str, Any]] = None,
    recent_verified_actions: Optional[List[Dict[str, Any]]] = None,
    ttl_seconds: float = 60.0,
    confidence: float = 0.95,
) -> ContextContract:
    now = time.time()
    ctx = ContextContract(
        context_id=f"ctx_{uuid.uuid4().hex[:8]}",
        turn_id=turn_id,
        goal_id=goal_id,
        active_project=active_project,
        active_application=active_application,
        active_task=active_task,
        task_state=task_state,
        visible_context=visible_context or {},
        recent_verified_actions=recent_verified_actions or [],
        created_at=now,
        expires_at=now + ttl_seconds,
        confidence=confidence,
    )
    ctx.sanitize()
    return ctx
