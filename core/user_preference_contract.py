"""
User Preference Contract for Human Collaboration & Preference Learning in MARK XLVIII / JARVIS.
Defines durable operational preferences, preference types, lifecycle states, and privacy boundaries.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class PreferenceType(str, Enum):
    COMMUNICATION = "COMMUNICATION"
    EXECUTION_STYLE = "EXECUTION_STYLE"
    CONFIRMATION_STYLE = "CONFIRMATION_STYLE"
    PROACTIVE_ASSISTANCE = "PROACTIVE_ASSISTANCE"
    PROJECT_WORKFLOW = "PROJECT_WORKFLOW"
    OUTPUT_FORMAT = "OUTPUT_FORMAT"
    TOOL_PREFERENCE = "TOOL_PREFERENCE"
    INTERRUPTION_PREFERENCE = "INTERRUPTION_PREFERENCE"


class PreferenceState(str, Enum):
    CANDIDATE = "CANDIDATE"
    INFERRED = "INFERRED"
    CONFIRMED = "CONFIRMED"
    STALE = "STALE"
    REJECTED = "REJECTED"
    INVALIDATED = "INVALIDATED"


@dataclass
class UserPreferenceContract:
    preference_id: str
    user_scope: str = "default_user"
    project_scope: Optional[str] = None  # None indicates GLOBAL
    preference_type: PreferenceType = PreferenceType.COMMUNICATION
    key: str = ""
    value: Any = None
    confidence: float = 0.80
    source: str = "inference"  # "inference", "explicit_instruction", "correction"
    verification_state: PreferenceState = PreferenceState.INFERRED
    created_at: float = field(default_factory=time.time)
    last_confirmed_at: Optional[float] = None
    ttl: Optional[float] = None  # Seconds until stale
    supersedes_preference_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_confirmed(self) -> bool:
        return self.verification_state == PreferenceState.CONFIRMED

    def is_stale(self, current_time: Optional[float] = None) -> bool:
        if self.verification_state in [PreferenceState.STALE, PreferenceState.INVALIDATED, PreferenceState.REJECTED]:
            return True
        if self.ttl is not None:
            now = current_time if current_time is not None else time.time()
            return (now - self.created_at) > self.ttl
        return False

    def confirm(self) -> None:
        self.verification_state = PreferenceState.CONFIRMED
        self.last_confirmed_at = time.time()
        self.confidence = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preference_id": self.preference_id,
            "user_scope": self.user_scope,
            "project_scope": self.project_scope,
            "preference_type": self.preference_type.value,
            "key": self.key,
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "verification_state": self.verification_state.value,
            "created_at": self.created_at,
            "last_confirmed_at": self.last_confirmed_at,
            "ttl": self.ttl,
            "supersedes_preference_id": self.supersedes_preference_id,
            "metadata": self.metadata,
        }


def create_user_preference(
    key: str,
    value: Any,
    preference_type: PreferenceType = PreferenceType.COMMUNICATION,
    project_scope: Optional[str] = None,
    user_scope: str = "default_user",
    confidence: float = 0.80,
    source: str = "inference",
    verification_state: PreferenceState = PreferenceState.INFERRED,
    ttl: Optional[float] = None,
    supersedes_preference_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> UserPreferenceContract:
    return UserPreferenceContract(
        preference_id=f"pref_{uuid.uuid4().hex[:8]}",
        user_scope=user_scope,
        project_scope=project_scope,
        preference_type=preference_type,
        key=key,
        value=value,
        confidence=confidence,
        source=source,
        verification_state=verification_state,
        ttl=ttl,
        supersedes_preference_id=supersedes_preference_id,
        metadata=metadata or {},
    )
