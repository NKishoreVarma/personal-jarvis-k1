"""
Memory Contract for Long-Term Memory & PGVector Intelligence in MARK XLVIII / JARVIS.
Defines formal memory records, embedding references, verification states, provenance,
contradiction tracking, and privacy boundaries.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Sensitive patterns to reject or scrub
SENSITIVE_REGEX = re.compile(
    r"(bearer\s+[a-zA-Z0-9_\-\.]{16,}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{20,}|password\s*=\s*\S+|api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


class MemoryType(str, Enum):
    FACT = "FACT"
    PROJECT_KNOWLEDGE = "PROJECT_KNOWLEDGE"
    WORKFLOW_EXPERIENCE = "WORKFLOW_EXPERIENCE"
    CAPABILITY_EXPERIENCE = "CAPABILITY_EXPERIENCE"
    USER_PREFERENCE = "USER_PREFERENCE"
    SYSTEM_CONFIGURATION = "SYSTEM_CONFIGURATION"
    RECOVERY_EXPERIENCE = "RECOVERY_EXPERIENCE"
    RETRIEVAL_KNOWLEDGE = "RETRIEVAL_KNOWLEDGE"
    TEMPORARY_CONTEXT = "TEMPORARY_CONTEXT"
    LESSON = "LESSON"
    # Backward-compatible aliases
    PREFERENCE = "USER_PREFERENCE"
    PROJECT_CONTEXT = "PROJECT_KNOWLEDGE"
    WORKFLOW = "WORKFLOW_EXPERIENCE"
    EXPERIENCE = "CAPABILITY_EXPERIENCE"
    REPAIR_PATTERN = "WORKFLOW_EXPERIENCE"
    FAILURE_PATTERN = "WORKFLOW_EXPERIENCE"
    ENTITY_RELATION = "PROJECT_KNOWLEDGE"
    TASK_OUTCOME = "CAPABILITY_EXPERIENCE"


class VerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    OBSERVED = "OBSERVED"
    CORROBORATED = "CORROBORATED"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    # Backward-compatible alias
    CONFIRMED = "VERIFIED"


def scrub_sensitive_data(text: str) -> str:
    """Replaces passwords, bearer tokens, and API keys with [REDACTED_SECRET]."""
    return SENSITIVE_REGEX.sub("[REDACTED_SECRET]", text)


def contains_sensitive_data(text: str) -> bool:
    """Checks if text contains raw credentials."""
    return bool(SENSITIVE_REGEX.search(text))


@dataclass
class MemoryContract:
    memory_id: str
    memory_type: MemoryType
    subject: str
    content: str
    embedding_reference: Optional[str] = None
    goal_id: Optional[str] = None
    turn_id: Optional[str] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    source_type: str = "experience_learning"
    source_id: Optional[str] = None
    verification_state: VerificationState = VerificationState.UNVERIFIED
    confidence: float = 0.8
    importance: float = 0.5  # 0.0 = trivial, 1.0 = critical
    freshness_score: float = 1.0  # 1.0 = recent, decays over time
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    supersedes_memory_id: Optional[str] = None
    contradiction_group_id: Optional[str] = None
    privacy_scope: str = "LOCAL"  # LOCAL, USER, SHARED, GLOBAL, PROJECT, GOAL, SESSION
    project_scope: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def freshness(self) -> float:
        return self.freshness_score

    @freshness.setter
    def freshness(self, value: float) -> None:
        self.freshness_score = value

    @property
    def source(self) -> str:
        return self.source_type

    @source.setter
    def source(self, value: str) -> None:
        self.source_type = value

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if self.verification_state in [VerificationState.EXPIRED, VerificationState.INVALIDATED]:
            return True
        if self.expires_at is not None and now > self.expires_at:
            return True
        return False

    def is_contradicted(self) -> bool:
        return self.verification_state == VerificationState.CONTRADICTED

    def touch(self) -> None:
        self.last_accessed_at = time.time()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value if isinstance(self.memory_type, MemoryType) else str(self.memory_type),
            "subject": self.subject,
            "content": self.content,
            "embedding_reference": self.embedding_reference,
            "goal_id": self.goal_id,
            "turn_id": self.turn_id,
            "project_id": self.project_id or self.project_scope,
            "session_id": self.session_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source": self.source_type,
            "confidence": round(self.confidence, 3),
            "importance": round(self.importance, 3),
            "freshness_score": round(self.freshness_score, 3),
            "freshness": round(self.freshness_score, 3),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "supersedes_memory_id": self.supersedes_memory_id,
            "contradiction_group_id": self.contradiction_group_id,
            "verification_state": self.verification_state.value if isinstance(self.verification_state, VerificationState) else str(self.verification_state),
            "privacy_scope": self.privacy_scope,
            "project_scope": self.project_scope or self.project_id,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryContract:
        type_val = data.get("memory_type", "FACT")
        try:
            type_enum = MemoryType(type_val)
        except ValueError:
            type_enum = MemoryType.FACT

        ver_val = data.get("verification_state", "UNVERIFIED")
        try:
            ver_enum = VerificationState(ver_val)
        except ValueError:
            ver_enum = VerificationState.UNVERIFIED

        proj = data.get("project_id") or data.get("project_scope")
        freshness_val = data.get("freshness_score", data.get("freshness", 1.0))
        src_val = data.get("source_type", data.get("source", "experience_learning"))

        return cls(
            memory_id=data.get("memory_id", f"mem_{uuid.uuid4().hex[:8]}"),
            memory_type=type_enum,
            subject=data.get("subject", ""),
            content=data.get("content", ""),
            embedding_reference=data.get("embedding_reference"),
            goal_id=data.get("goal_id"),
            turn_id=data.get("turn_id"),
            project_id=proj,
            session_id=data.get("session_id"),
            source_type=src_val,
            source_id=data.get("source_id"),
            verification_state=ver_enum,
            confidence=data.get("confidence", 0.8),
            importance=data.get("importance", 0.5),
            freshness_score=freshness_val,
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            expires_at=data.get("expires_at"),
            last_accessed_at=data.get("last_accessed_at", time.time()),
            access_count=data.get("access_count", 0),
            supersedes_memory_id=data.get("supersedes_memory_id"),
            contradiction_group_id=data.get("contradiction_group_id"),
            privacy_scope=data.get("privacy_scope", "LOCAL"),
            project_scope=proj,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


def create_memory_contract(
    memory_type: MemoryType,
    subject: str,
    content: str,
    project_scope: Optional[str] = None,
    confidence: float = 0.8,
    importance: float = 0.5,
    ttl_seconds: Optional[float] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    goal_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    session_id: Optional[str] = None,
    supersedes_memory_id: Optional[str] = None,
) -> MemoryContract:
    now = time.time()
    clean_subject = scrub_sensitive_data(subject)
    clean_content = scrub_sensitive_data(content)
    return MemoryContract(
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        memory_type=memory_type,
        subject=clean_subject,
        content=clean_content,
        confidence=confidence,
        importance=importance,
        created_at=now,
        updated_at=now,
        expires_at=now + ttl_seconds if ttl_seconds else None,
        last_accessed_at=now,
        verification_state=VerificationState.UNVERIFIED,
        project_scope=project_scope,
        project_id=project_scope,
        goal_id=goal_id,
        turn_id=turn_id,
        session_id=session_id,
        supersedes_memory_id=supersedes_memory_id,
        tags=tags or [],
        metadata=metadata or {},
    )
