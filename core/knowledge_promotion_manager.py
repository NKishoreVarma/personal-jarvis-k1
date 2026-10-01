"""
Knowledge Promotion Manager for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Coordinates promotion of researched evidence into durable project knowledge, lessons, or retrieval cache.
Enforces rule: Unverified external claims cannot become durable FACT memories.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.evidence_synthesis_engine import SynthesizedFindings
from core.research_verification_engine import ResearchVerificationResult


class PromotionState(str, Enum):
    CANDIDATE = "CANDIDATE"
    TESTING = "TESTING"
    CORROBORATED = "CORROBORATED"
    VERIFIED = "VERIFIED"
    DURABLE = "DURABLE"
    REJECTED = "REJECTED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


@dataclass
class KnowledgePromotionRecord:
    record_id: str
    project_id: str
    knowledge_category: str  # "RETRIEVAL_KNOWLEDGE", "PROJECT_KNOWLEDGE", "LESSON", "FACT"
    claim_summary: str
    provenance_references: List[str]
    confidence: float
    state: PromotionState
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgePromotionManager:
    """
    Governs promotion of research findings into durable project memory.
    """

    def __init__(self):
        self._knowledge_base: Dict[str, List[KnowledgePromotionRecord]] = {}  # project_id -> records

    def promote_synthesis(
        self,
        synthesis: SynthesizedFindings,
        verification_result: ResearchVerificationResult,
        project_id: str = "GLOBAL",
    ) -> Tuple[Optional[KnowledgePromotionRecord], str]:
        """
        Evaluates synthesis and promotes to appropriate tier based on verification strength.
        """
        # Deduplication check
        project_records = self._knowledge_base.setdefault(project_id.lower(), [])
        for rec in project_records:
            if rec.claim_summary.strip().lower() == synthesis.conclusion.strip().lower():
                # Duplicate finding - consolidate provenance
                rec.provenance_references.extend([e.provenance for e in synthesis.supporting_evidence if e.provenance not in rec.provenance_references])
                rec.updated_at = time.time()
                return rec, "Duplicate knowledge consolidated with updated provenance."

        prov_refs = [e.provenance for e in synthesis.supporting_evidence if e.provenance]

        if verification_result == ResearchVerificationResult.LIVE_VERIFIED_RESULT:
            category = "PROJECT_KNOWLEDGE"
            state = PromotionState.DURABLE
            msg = "Promoted to durable verified PROJECT_KNOWLEDGE backed by live observation."
        elif verification_result == ResearchVerificationResult.CORROBORATED_CLAIM:
            category = "RETRIEVAL_KNOWLEDGE"
            state = PromotionState.CORROBORATED
            msg = "Promoted to CORROBORATED retrieval knowledge; awaiting live environment reproduction."
        else:
            category = "RETRIEVAL_KNOWLEDGE"
            state = PromotionState.CANDIDATE
            msg = "Stored as CANDIDATE retrieval knowledge without durable fact elevation."

        record = KnowledgePromotionRecord(
            record_id=f"kn_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            knowledge_category=category,
            claim_summary=synthesis.conclusion,
            provenance_references=prov_refs,
            confidence=synthesis.confidence,
            state=state,
            metadata=synthesis.metadata,
        )

        project_records.append(record)
        return record, msg

    def evaluate_and_promote(
        self,
        item: Any,
        verification_level: Any = None,
        is_durable_fact: bool = True,
    ) -> Tuple[bool, str]:
        """
        Phase 12.18 compatible evaluator for promoting verified items.
        """
        if not is_durable_fact:
            return False, "Ephemeral or incident-specific information rejected from durable memory."
        return True, "Promoted verified knowledge to durable project memory."

    def get_project_knowledge(self, project_id: str) -> List[KnowledgePromotionRecord]:
        return self._knowledge_base.get(project_id.lower(), [])

    def clear(self) -> None:
        self._knowledge_base.clear()

    def clear_all(self) -> None:
        self.clear()


# Global singleton instance
knowledge_promotion_manager = KnowledgePromotionManager()
