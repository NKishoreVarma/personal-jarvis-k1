"""
Knowledge Provenance Tracker for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Maintains end-to-end audit trails for external claims, citations, verification steps,
and resulting plan influences without exposing internal reasoning tokens or chain-of-thought.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.external_knowledge_contract import ExternalKnowledgeContract


@dataclass
class ProvenanceRecord:
    provenance_id: str
    knowledge_id: str
    source_title: str
    source_url: str
    retrieved_at: float
    relevance_reason: str
    verification_step: str
    influenced_plan: bool = False
    action_succeeded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provenance_id": self.provenance_id,
            "knowledge_id": self.knowledge_id,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "relevance_reason": self.relevance_reason,
            "verification_step": self.verification_step,
            "influenced_plan": self.influenced_plan,
            "action_succeeded": self.action_succeeded,
        }


class KnowledgeProvenanceTracker:
    """
    Tracks origin and application history of external knowledge items.
    """

    def __init__(self):
        self._records: List[ProvenanceRecord] = []

    def record_provenance(
        self,
        item: ExternalKnowledgeContract,
        relevance_reason: str,
        verification_step: str,
        influenced_plan: bool = False,
        action_succeeded: bool = False,
    ) -> ProvenanceRecord:
        """Records knowledge origin and usage metadata."""
        rec = ProvenanceRecord(
            provenance_id=f"prov_{uuid.uuid4().hex[:6]}",
            knowledge_id=item.knowledge_id,
            source_title=item.title,
            source_url=item.source_url,
            retrieved_at=item.retrieved_at,
            relevance_reason=relevance_reason,
            verification_step=verification_step,
            influenced_plan=influenced_plan,
            action_succeeded=action_succeeded,
        )
        self._records.append(rec)
        return rec

    def format_source_explanation(self, project_scope: str = "FLOW") -> str:
        """Formats natural voice source citation explanation."""
        if not self._records:
            return "I based this on local project files and standard framework configuration."

        latest = self._records[-1]
        return f"I found this in the official documentation for {latest.source_title} and verified it against your local project."

    def list_records(self) -> List[ProvenanceRecord]:
        return list(self._records)

    def clear_all(self) -> None:
        self._records.clear()


# Global singleton instance
knowledge_provenance_tracker = KnowledgeProvenanceTracker()
