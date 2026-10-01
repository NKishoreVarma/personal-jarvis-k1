"""
Temporal Contract for Time Awareness, Scheduling & Temporal Task Intelligence in MARK XLVIII / JARVIS.
Defines formal temporal items, lifecycle states, deadline bounds, and validation rules.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class TemporalType(str, Enum):
    DEADLINE = "DEADLINE"
    SCHEDULED = "SCHEDULED"
    RECURRING = "RECURRING"
    DEFERRED = "DEFERRED"
    FOLLOW_UP = "FOLLOW_UP"
    EXPIRATION = "EXPIRATION"
    TIME_WINDOW = "TIME_WINDOW"
    STALE_CHECK = "STALE_CHECK"
    COOLDOWN = "COOLDOWN"
    REMINDER = "REMINDER"


class TemporalState(str, Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    DEFERRED = "DEFERRED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


@dataclass
class TemporalContract:
    temporal_id: str
    title: str
    description: str
    temporal_type: TemporalType
    state: TemporalState = TemporalState.PENDING
    source_goal_id: str = ""
    project_id: str = "GLOBAL"
    session_id: str = "default_session"
    created_at: float = field(default_factory=time.time)
    scheduled_at: Optional[float] = None
    due_at: Optional[float] = None
    expires_at: Optional[float] = None
    recurrence_rule: Optional[str] = None  # e.g. "interval:3600", "daily", "weekly"
    timezone: str = "UTC"
    priority: float = 0.50
    required_authority: str = "READ_ONLY"
    approval_required: bool = False
    last_triggered_at: Optional[float] = None
    next_trigger_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.state in [TemporalState.PENDING, TemporalState.SCHEDULED, TemporalState.ACTIVE, TemporalState.DUE, TemporalState.OVERDUE]

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        if self.state == TemporalState.EXPIRED:
            return True
        if self.expires_at is not None:
            now = current_time if current_time is not None else time.time()
            return now > self.expires_at
        return False

    def is_due(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if self.due_at is not None:
            return now >= self.due_at
        if self.scheduled_at is not None:
            return now >= self.scheduled_at
        return False

    def is_overdue(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if self.due_at is not None:
            return now > self.due_at
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temporal_id": self.temporal_id,
            "title": self.title,
            "description": self.description,
            "temporal_type": self.temporal_type.value,
            "state": self.state.value,
            "source_goal_id": self.source_goal_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "scheduled_at": self.scheduled_at,
            "due_at": self.due_at,
            "expires_at": self.expires_at,
            "recurrence_rule": self.recurrence_rule,
            "timezone": self.timezone,
            "priority": round(self.priority, 3),
            "required_authority": self.required_authority,
            "approval_required": self.approval_required,
            "last_triggered_at": self.last_triggered_at,
            "next_trigger_at": self.next_trigger_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


def create_temporal_contract(
    title: str,
    description: str,
    temporal_type: TemporalType,
    scheduled_at: Optional[float] = None,
    due_at: Optional[float] = None,
    expires_at: Optional[float] = None,
    recurrence_rule: Optional[str] = None,
    source_goal_id: str = "",
    project_id: str = "GLOBAL",
    priority: float = 0.50,
    required_authority: str = "READ_ONLY",
    approval_required: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[TemporalContract], str]:
    now = time.time()

    # Strict timestamp validations
    if due_at is not None and due_at < now - 1.0:
        return None, "Validation error: due_at cannot be in the past at creation time."

    if scheduled_at is not None and scheduled_at < now - 1.0:
        return None, "Validation error: scheduled_at cannot be in the past at creation time."

    if due_at is not None and expires_at is not None and expires_at < due_at:
        return None, "Validation error: expires_at cannot precede due_at."

    if scheduled_at is not None and due_at is not None and due_at < scheduled_at:
        return None, "Validation error: due_at cannot precede scheduled_at."

    contract = TemporalContract(
        temporal_id=f"temp_{uuid.uuid4().hex[:8]}",
        title=title,
        description=description,
        temporal_type=temporal_type,
        state=TemporalState.SCHEDULED if scheduled_at else (TemporalState.DEFERRED if temporal_type == TemporalType.DEFERRED else TemporalState.PENDING),
        source_goal_id=source_goal_id,
        project_id=project_id,
        created_at=now,
        scheduled_at=scheduled_at,
        due_at=due_at,
        expires_at=expires_at,
        recurrence_rule=recurrence_rule,
        priority=priority,
        required_authority=required_authority,
        approval_required=approval_required,
        next_trigger_at=scheduled_at or due_at,
        metadata=metadata or {},
    )
    return contract, "Temporal contract validated and created successfully."
