"""
Shared Evidence Store for MARK XLVIII / JARVIS.
Turn-bound and goal-bound repository for multi-agent evidence collection, deduplication,
freshness tracking, and contradiction detection without cross-goal leakage.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceCategory(str, Enum):
    PROJECT_STATE = "PROJECT_STATE"
    PROCESS_STATE = "PROCESS_STATE"
    PORT_STATE = "PORT_STATE"
    LOG_STATE = "LOG_STATE"
    SYSTEM_STATE = "SYSTEM_STATE"
    FILE_STATE = "FILE_STATE"
    NETWORK_STATE = "NETWORK_STATE"
    VISUAL_ERROR_STATE = "VISUAL_ERROR_STATE"
    VISUAL_UI_STATE = "VISUAL_UI_STATE"


@dataclass
class EvidenceRecord:
    evidence_id: str
    goal_id: str
    agent_id: str
    category: str
    value: Any
    source: str
    observed_at: float = field(default_factory=time.time)
    confidence: float = 0.9
    verification_state: str = "OBSERVED"  # OBSERVED, CONFIRMED, CONTRADICTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "goal_id": self.goal_id,
            "agent_id": self.agent_id,
            "category": self.category,
            "value": self.value,
            "source": self.source,
            "observed_at": self.observed_at,
            "confidence": self.confidence,
            "verification_state": self.verification_state,
        }


class SharedEvidenceStore:
    """
    Goal-isolated, deduplicated evidence repository for multi-agent workflows.
    """

    def __init__(self):
        # Map: goal_id -> list of EvidenceRecord
        self._store: Dict[str, List[EvidenceRecord]] = {}

    def add_evidence(
        self,
        goal_id: str,
        agent_id: str,
        category: str,
        value: Any,
        source: str,
        confidence: float = 0.9,
    ) -> str:
        """
        Inserts new evidence or updates existing matching evidence with newer observation.
        """
        if goal_id not in self._store:
            self._store[goal_id] = []

        # Deduplication check
        records = self._store[goal_id]
        for rec in records:
            if rec.category == category and rec.source == source:
                # If identical value, just refresh timestamp
                if rec.value == value:
                    rec.observed_at = time.time()
                    rec.confidence = max(rec.confidence, confidence)
                    return rec.evidence_id
                else:
                    # Value changed -> Contradiction/Update!
                    rec.verification_state = "CONTRADICTED"

        eid = f"ev_{uuid.uuid4().hex[:8]}"
        new_rec = EvidenceRecord(
            evidence_id=eid,
            goal_id=goal_id,
            agent_id=agent_id,
            category=category,
            value=value,
            source=source,
            observed_at=time.time(),
            confidence=confidence,
        )
        records.append(new_rec)
        return eid

    def get_evidence(self, goal_id: str, category: Optional[str] = None) -> List[EvidenceRecord]:
        """Returns evidence for a specific goal_id with optional category filter."""
        items = self._store.get(goal_id, [])
        if category:
            return [i for i in items if i.category == category]
        return list(items)

    def get_consolidated_state(self, goal_id: str) -> Dict[str, Any]:
        """
        Builds a unified state dictionary for a goal, prioritizing newer confirmed evidence.
        """
        consolidated: Dict[str, Any] = {}
        for rec in self._store.get(goal_id, []):
            if rec.verification_state != "CONTRADICTED":
                consolidated[rec.category.lower()] = rec.value
        return consolidated

    def detect_contradictions(self, goal_id: str) -> List[Dict[str, Any]]:
        """Identifies any contradicted evidence records for a goal."""
        contradictions = []
        for rec in self._store.get(goal_id, []):
            if rec.verification_state == "CONTRADICTED":
                contradictions.append(rec.to_dict())
        return contradictions

    def clear_goal(self, goal_id: str) -> None:
        """Clears evidence when a goal completes or is cancelled."""
        self._store.pop(goal_id, None)

    def clear_all(self) -> None:
        self._store.clear()


# Global singleton instance
shared_evidence_store = SharedEvidenceStore()
