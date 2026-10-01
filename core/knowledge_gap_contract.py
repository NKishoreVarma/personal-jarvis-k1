"""
Knowledge Gap Contract for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Defines formal contracts for detected gaps in knowledge, diagnostic uncertainties, and verification requirements.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class KnowledgeGapType(str, Enum):
    NO_GAP = "NO_GAP"
    EXTERNAL_LOOKUP_REQUIRED = "EXTERNAL_LOOKUP_REQUIRED"
    FACTUAL_GAP = "FACTUAL_GAP"
    TECHNICAL_GAP = "TECHNICAL_GAP"
    ENVIRONMENT_GAP = "ENVIRONMENT_GAP"
    DOCUMENTATION_GAP = "DOCUMENTATION_GAP"
    DEPENDENCY_GAP = "DEPENDENCY_GAP"
    DIAGNOSTIC_GAP = "DIAGNOSTIC_GAP"
    VERIFICATION_GAP = "VERIFICATION_GAP"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    STALE_KNOWLEDGE = "STALE_KNOWLEDGE"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    RISK_UNCERTAINTY = "RISK_UNCERTAINTY"


class KnowledgeGapState(str, Enum):
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    RESEARCH_PLANNED = "RESEARCH_PLANNED"
    RESEARCHING = "RESEARCHING"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    SYNTHESIZED = "SYNTHESIZED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


_SENSITIVE_PATTERNS = [
    re.compile(r"(password|passwd|secret|api_key|token|bearer|auth|credential)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
]


def _scrub_sensitive(text: str) -> str:
    cleaned = text
    for pat in _SENSITIVE_PATTERNS:
        cleaned = pat.sub("[REDACTED_CREDENTIAL]", cleaned)
    return cleaned


@dataclass
class KnowledgeGapContract:
    gap_id: str
    gap_type: KnowledgeGapType
    question: str
    context: str = ""
    goal_id: str = ""
    project_id: str = "GLOBAL"
    session_id: str = "default_session"
    importance: float = 0.70
    urgency: float = 0.50
    confidence_in_existing_knowledge: float = 0.20
    evidence_references: List[str] = field(default_factory=list)
    state: KnowledgeGapState = KnowledgeGapState.DETECTED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ttl_seconds: float = 86400.0  # 24 hours default
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        if self.state in [KnowledgeGapState.EXPIRED, KnowledgeGapState.INVALIDATED]:
            return True
        now = current_time if current_time is not None else time.time()
        return (now - self.created_at) > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type.value,
            "question": self.question,
            "context": self.context,
            "goal_id": self.goal_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "importance": round(self.importance, 3),
            "urgency": round(self.urgency, 3),
            "confidence_in_existing_knowledge": round(self.confidence_in_existing_knowledge, 3),
            "evidence_references": self.evidence_references,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }


def create_knowledge_gap(
    gap_type: KnowledgeGapType,
    question: str,
    context: str = "",
    goal_id: str = "",
    project_id: str = "GLOBAL",
    importance: float = 0.70,
    urgency: float = 0.50,
    confidence_in_existing_knowledge: float = 0.20,
    evidence_references: Optional[List[str]] = None,
    ttl_seconds: float = 86400.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[KnowledgeGapContract], str]:
    if not question or not question.strip():
        return None, "Validation error: Knowledge gap question cannot be empty."

    if not isinstance(gap_type, KnowledgeGapType):
        return None, "Validation error: Invalid KnowledgeGapType."

    if ttl_seconds <= 0:
        return None, "Validation error: TTL must be a positive number."

    conf = 0.20 if confidence_in_existing_knowledge is None else float(confidence_in_existing_knowledge)
    clamped_importance = max(0.0, min(1.0, importance))
    clamped_urgency = max(0.0, min(1.0, urgency))
    clamped_confidence = max(0.0, min(1.0, conf))

    scrubbed_question = _scrub_sensitive(question.strip())
    scrubbed_context = _scrub_sensitive(context.strip())

    now = time.time()
    contract = KnowledgeGapContract(
        gap_id=f"gap_{uuid.uuid4().hex[:8]}",
        gap_type=gap_type,
        question=scrubbed_question,
        context=scrubbed_context,
        goal_id=goal_id,
        project_id=project_id,
        importance=clamped_importance,
        urgency=clamped_urgency,
        confidence_in_existing_knowledge=clamped_confidence,
        evidence_references=evidence_references or [],
        state=KnowledgeGapState.DETECTED,
        created_at=now,
        updated_at=now,
        ttl_seconds=ttl_seconds,
        metadata=metadata or {},
    )
    return contract, "Knowledge gap contract created successfully."
