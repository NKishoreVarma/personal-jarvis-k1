"""
Source Evaluation Contract for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Defines source taxonomy, reliability states, authority ratings, and provenance references.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    PRIMARY = "PRIMARY"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    OFFICIAL_CHANGELOG = "OFFICIAL_CHANGELOG"
    REPOSITORY = "REPOSITORY"
    ISSUE_TRACKER = "ISSUE_TRACKER"
    ACADEMIC = "ACADEMIC"
    TECHNICAL_ARTICLE = "TECHNICAL_ARTICLE"
    COMMUNITY = "COMMUNITY"
    FORUM = "FORUM"
    SEARCH_RESULT = "SEARCH_RESULT"
    UNKNOWN = "UNKNOWN"


class SourceReliabilityState(str, Enum):
    UNASSESSED = "UNASSESSED"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    REJECTED = "REJECTED"


@dataclass
class SourceEvaluationContract:
    source_id: str
    source_type: SourceType
    url_or_path: str
    authority_score: float = 0.50
    recency_score: float = 0.80
    provenance_score: float = 0.80
    corroboration_score: float = 0.50
    relevance_score: float = 0.80
    reliability_score: float = 0.50
    evaluation_state: SourceReliabilityState = SourceReliabilityState.UNASSESSED
    evidence_references: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "url_or_path": self.url_or_path,
            "authority_score": round(self.authority_score, 3),
            "recency_score": round(self.recency_score, 3),
            "provenance_score": round(self.provenance_score, 3),
            "corroboration_score": round(self.corroboration_score, 3),
            "relevance_score": round(self.relevance_score, 3),
            "reliability_score": round(self.reliability_score, 3),
            "evaluation_state": self.evaluation_state.value,
            "evidence_references": self.evidence_references,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


def create_source_evaluation(
    source_type: SourceType,
    url_or_path: str,
    authority_score: float = 0.50,
    recency_score: float = 0.80,
    provenance_score: float = 0.80,
    corroboration_score: float = 0.50,
    relevance_score: float = 0.80,
    evidence_references: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> SourceEvaluationContract:
    now = time.time()
    return SourceEvaluationContract(
        source_id=f"src_{uuid.uuid4().hex[:8]}",
        source_type=source_type,
        url_or_path=url_or_path,
        authority_score=max(0.0, min(1.0, authority_score)),
        recency_score=max(0.0, min(1.0, recency_score)),
        provenance_score=max(0.0, min(1.0, provenance_score)),
        corroboration_score=max(0.0, min(1.0, corroboration_score)),
        relevance_score=max(0.0, min(1.0, relevance_score)),
        evidence_references=evidence_references or [],
        created_at=now,
        metadata=metadata or {},
    )
