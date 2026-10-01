"""
Agent Message Contract for Multi-Agent Communication in MARK XLVIII / JARVIS.
Defines typed, structured message envelopes for inter-agent coordination.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class AgentMessageType(str, Enum):
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"
    EVIDENCE_SHARE = "EVIDENCE_SHARE"
    QUERY = "QUERY"
    DIAGNOSTIC_HYPOTHESIS = "DIAGNOSTIC_HYPOTHESIS"
    EXECUTION_REQUEST = "EXECUTION_REQUEST"
    VERIFICATION_REPORT = "VERIFICATION_REPORT"
    CONFLICT_ALERT = "CONFLICT_ALERT"
    HEARTBEAT = "HEARTBEAT"


@dataclass
class AgentMessageContract:
    message_id: str
    sender_id: str
    recipient_id: str  # specific agent_id or "BROADCAST"
    goal_id: str
    message_type: AgentMessageType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "goal_id": self.goal_id,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


def create_agent_message(
    sender_id: str,
    recipient_id: str,
    goal_id: str,
    message_type: AgentMessageType,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> AgentMessageContract:
    return AgentMessageContract(
        message_id=f"msg_{uuid.uuid4().hex[:8]}",
        sender_id=sender_id,
        recipient_id=recipient_id,
        goal_id=goal_id,
        message_type=message_type,
        payload=payload,
        correlation_id=correlation_id,
    )
