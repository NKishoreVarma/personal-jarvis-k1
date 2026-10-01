"""
Research Task Contract for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Defines bounded research scopes, sub-question decompositions, source constraints, and strict depth limits.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ResearchTaskState(str, Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class ResearchTaskContract:
    research_id: str
    gap_id: str
    question: str
    sub_questions: List[str] = field(default_factory=list)
    scope: str = "GLOBAL"
    project_id: str = "GLOBAL"
    goal_id: str = ""
    allowed_source_types: List[str] = field(default_factory=lambda: ["OFFICIAL_DOCUMENTATION", "PRIMARY", "CHANGELOG"])
    blocked_source_types: List[str] = field(default_factory=lambda: ["UNVERIFIED_FORUM", "SEARCH_SNIPPET"])
    authority_level: str = "READ_ONLY"
    max_sources: int = 5
    max_depth: int = 2
    time_budget_seconds: float = 30.0
    state: ResearchTaskState = ResearchTaskState.PLANNED
    evidence_references: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.state in [ResearchTaskState.PLANNED, ResearchTaskState.ACTIVE, ResearchTaskState.WAITING]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "research_id": self.research_id,
            "gap_id": self.gap_id,
            "question": self.question,
            "sub_questions": self.sub_questions,
            "scope": self.scope,
            "project_id": self.project_id,
            "goal_id": self.goal_id,
            "allowed_source_types": self.allowed_source_types,
            "blocked_source_types": self.blocked_source_types,
            "authority_level": self.authority_level,
            "max_sources": self.max_sources,
            "max_depth": self.max_depth,
            "time_budget_seconds": self.time_budget_seconds,
            "state": self.state.value,
            "evidence_references": self.evidence_references,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


def create_research_task(
    gap_id: str,
    question: str,
    sub_questions: Optional[List[str]] = None,
    scope: str = "GLOBAL",
    project_id: str = "GLOBAL",
    goal_id: str = "",
    allowed_source_types: Optional[List[str]] = None,
    blocked_source_types: Optional[List[str]] = None,
    authority_level: str = "READ_ONLY",
    max_sources: int = 5,
    max_depth: int = 2,
    time_budget_seconds: float = 30.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[ResearchTaskContract], str]:
    if not question or not question.strip():
        return None, "Validation error: Research question cannot be empty."

    # Invariant: Authority must remain READ_ONLY
    if authority_level != "READ_ONLY":
        return None, "Validation error: Research tasks cannot request mutating or elevated authority."

    # Bounds validation
    bounded_max_sources = max(1, min(20, max_sources))
    bounded_max_depth = max(1, min(3, max_depth))
    bounded_time_budget = max(1.0, min(120.0, time_budget_seconds))

    now = time.time()
    task = ResearchTaskContract(
        research_id=f"res_{uuid.uuid4().hex[:8]}",
        gap_id=gap_id,
        question=question.strip(),
        sub_questions=sub_questions or [],
        scope=scope,
        project_id=project_id,
        goal_id=goal_id,
        allowed_source_types=allowed_source_types or ["OFFICIAL_DOCUMENTATION", "PRIMARY", "CHANGELOG"],
        blocked_source_types=blocked_source_types or ["UNVERIFIED_FORUM", "SEARCH_SNIPPET"],
        authority_level="READ_ONLY",
        max_sources=bounded_max_sources,
        max_depth=bounded_max_depth,
        time_budget_seconds=bounded_time_budget,
        state=ResearchTaskState.PLANNED,
        created_at=now,
        updated_at=now,
        metadata=metadata or {},
    )
    return task, "Research task contract validated and created successfully."
