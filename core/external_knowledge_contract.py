"""
External Knowledge Contract for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Defines schemas for external knowledge items, source categories, verification states,
confidence ratings, provenance, and TTL expiration tracking.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceCategory(str, Enum):
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    PROJECT_REPOSITORY = "PROJECT_REPOSITORY"
    PACKAGE_DOCUMENTATION = "PACKAGE_DOCUMENTATION"
    TECHNICAL_ARTICLE = "TECHNICAL_ARTICLE"
    STACK_TRACE_REFERENCE = "STACK_TRACE_REFERENCE"
    SEARCH_RESULT = "SEARCH_RESULT"
    LOCAL_DOCUMENT = "LOCAL_DOCUMENT"
    OTHER = "OTHER"


class VerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    RETRIEVED = "RETRIEVED"
    CORROBORATED = "CORROBORATED"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


@dataclass
class ExternalKnowledgeContract:
    knowledge_id: str
    query: str
    source_type: SourceCategory
    source_url: str
    title: str
    content_summary: str
    claims: List[str] = field(default_factory=list)
    confidence: float = 0.50
    authority_score: float = 0.50
    freshness_score: float = 0.90
    relevance_score: float = 0.80
    verification_state: VerificationState = VerificationState.RETRIEVED
    provenance: str = "web_search"
    retrieved_at: float = field(default_factory=time.time)
    published_at: Optional[float] = None
    ttl_seconds: float = 3600.0  # 1 hour default
    project_scope: str = "GLOBAL"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return (now - self.retrieved_at) > self.ttl_seconds

    def is_contradicted(self) -> bool:
        return self.verification_state == VerificationState.CONTRADICTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "query": self.query,
            "source_type": self.source_type.value if isinstance(self.source_type, SourceCategory) else str(self.source_type),
            "source_url": self.source_url,
            "title": self.title,
            "content_summary": self.content_summary,
            "claims": self.claims,
            "confidence": round(self.confidence, 3),
            "authority_score": round(self.authority_score, 3),
            "freshness_score": round(self.freshness_score, 3),
            "relevance_score": round(self.relevance_score, 3),
            "verification_state": self.verification_state.value if isinstance(self.verification_state, VerificationState) else str(self.verification_state),
            "provenance": self.provenance,
            "retrieved_at": self.retrieved_at,
            "published_at": self.published_at,
            "ttl_seconds": self.ttl_seconds,
            "project_scope": self.project_scope,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExternalKnowledgeContract:
        src_val = data.get("source_type", "OTHER")
        try:
            src_enum = SourceCategory(src_val)
        except ValueError:
            src_enum = SourceCategory.OTHER

        ver_val = data.get("verification_state", "RETRIEVED")
        try:
            ver_enum = VerificationState(ver_val)
        except ValueError:
            ver_enum = VerificationState.RETRIEVED

        return cls(
            knowledge_id=data.get("knowledge_id", f"kn_{uuid.uuid4().hex[:8]}"),
            query=data.get("query", ""),
            source_type=src_enum,
            source_url=data.get("source_url", ""),
            title=data.get("title", ""),
            content_summary=data.get("content_summary", ""),
            claims=data.get("claims", []),
            confidence=data.get("confidence", 0.50),
            authority_score=data.get("authority_score", 0.50),
            freshness_score=data.get("freshness_score", 0.90),
            relevance_score=data.get("relevance_score", 0.80),
            verification_state=ver_enum,
            provenance=data.get("provenance", "web_search"),
            retrieved_at=data.get("retrieved_at", time.time()),
            published_at=data.get("published_at"),
            ttl_seconds=data.get("ttl_seconds", 3600.0),
            project_scope=data.get("project_scope", "GLOBAL"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


def create_knowledge_item(
    query: str,
    title: str,
    content_summary: str,
    source_type: SourceCategory = SourceCategory.OFFICIAL_DOCUMENTATION,
    source_url: str = "",
    claims: Optional[List[str]] = None,
    confidence: float = 0.80,
    authority_score: float = 0.85,
    project_scope: str = "GLOBAL",
    ttl_seconds: float = 3600.0,
) -> ExternalKnowledgeContract:
    return ExternalKnowledgeContract(
        knowledge_id=f"kn_{uuid.uuid4().hex[:8]}",
        query=query,
        source_type=source_type,
        source_url=source_url,
        title=title,
        content_summary=content_summary,
        claims=claims or [content_summary],
        confidence=confidence,
        authority_score=authority_score,
        project_scope=project_scope,
        ttl_seconds=ttl_seconds,
    )
