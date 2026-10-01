"""
Knowledge Gap Detector for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Evaluates local memory confidence, evidence conflicts, and unexplained failures to identify bounded knowledge gaps.
Enforces rule: Not all gaps require external research; distinguishes MINOR from BLOCKING gaps.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.knowledge_gap_contract import (
    KnowledgeGapContract,
    KnowledgeGapType,
    create_knowledge_gap,
)


class KnowledgeGapSeverity(str, Enum):
    NO_GAP = "NO_GAP"
    MINOR_GAP = "MINOR_GAP"
    RESEARCH_WORTHY_GAP = "RESEARCH_WORTHY_GAP"
    BLOCKING_GAP = "BLOCKING_GAP"


class KnowledgeGapDetector:
    """
    Analyzes active diagnostic contexts, memory retrieval confidence, and evidence conflicts to surface knowledge gaps.
    """

    def detect_gap(
        self,
        question: Optional[str] = None,
        retrieved_memory_confidence: Optional[Any] = None,
        has_evidence_conflict: bool = False,
        is_unknown_dependency: bool = False,
        missing_documentation: bool = False,
        unexplained_repeated_failure: bool = False,
        project_id: str = "GLOBAL",
        goal_id: str = "",
        evidence_references: Optional[List[str]] = None,
        query: Optional[str] = None,
        project_scope: str = "GLOBAL",
        local_logs: Optional[str] = None,
        local_memory_matches: Optional[List[Any]] = None,
        explicit_search_requested: bool = False,
        *args,
        **kwargs,
    ) -> Any:
        """
        Determines gap severity and generates a structured KnowledgeGapContract if a gap exists.
        Maintains backward compatibility with Phase 12.18 (query / local_logs).
        """
        effective_query = question or query or (args[0] if args else "")
        effective_project = project_scope if project_scope != "GLOBAL" else (project_id or (args[1] if len(args) > 1 and isinstance(args[1], str) else "GLOBAL"))

        # If 2nd positional argument was a string (e.g. project_scope), route to Phase 12.18
        if isinstance(retrieved_memory_confidence, str):
            project_scope = retrieved_memory_confidence
            query = effective_query
            retrieved_memory_confidence = None

        # Phase 12.18 detection mode
        if explicit_search_requested:
            return KnowledgeGapType.EXTERNAL_LOOKUP_REQUIRED, "User explicitly requested external search."

        if local_logs:
            if "EADDRINUSE" in local_logs or "already in use" in local_logs or "port" in local_logs.lower():
                return KnowledgeGapType.NO_GAP, f"Local logs explain failure: {local_logs}"

        if query or (args and isinstance(args[0], str) and len(args) > 1 and isinstance(args[1], str)):
            if not local_logs and not local_memory_matches:
                return KnowledgeGapType.EXTERNAL_LOOKUP_REQUIRED, "Knowledge gap identified; external documentation lookup required."

        conf = 1.0
        if isinstance(retrieved_memory_confidence, (int, float)):
            conf = float(retrieved_memory_confidence)

        if (
            conf >= 0.85
            and not has_evidence_conflict
            and not is_unknown_dependency
            and not missing_documentation
            and not unexplained_repeated_failure
        ):
            return KnowledgeGapSeverity.NO_GAP, None

        # Determine severity and gap type
        gap_type = KnowledgeGapType.FACTUAL_GAP
        severity = KnowledgeGapSeverity.RESEARCH_WORTHY_GAP
        importance = 0.70
        urgency = 0.50

        if is_unknown_dependency:
            gap_type = KnowledgeGapType.DEPENDENCY_GAP
            severity = KnowledgeGapSeverity.BLOCKING_GAP
            importance = 0.90
            urgency = 0.80
        elif has_evidence_conflict:
            gap_type = KnowledgeGapType.SOURCE_CONFLICT
            severity = KnowledgeGapSeverity.BLOCKING_GAP
            importance = 0.85
            urgency = 0.75
        elif missing_documentation:
            gap_type = KnowledgeGapType.DOCUMENTATION_GAP
            severity = KnowledgeGapSeverity.RESEARCH_WORTHY_GAP
            importance = 0.75
            urgency = 0.60
        elif unexplained_repeated_failure:
            gap_type = KnowledgeGapType.DIAGNOSTIC_GAP
            severity = KnowledgeGapSeverity.BLOCKING_GAP
            importance = 0.95
            urgency = 0.85
        elif retrieved_memory_confidence < 0.50:
            gap_type = KnowledgeGapType.TECHNICAL_GAP
            severity = KnowledgeGapSeverity.RESEARCH_WORTHY_GAP
            importance = 0.70
            urgency = 0.50
        else:
            # Minor uncertainty (e.g. 0.50 <= confidence < 0.85)
            gap_type = KnowledgeGapType.FACTUAL_GAP
            severity = KnowledgeGapSeverity.MINOR_GAP
            importance = 0.40
            urgency = 0.30

        contract, _ = create_knowledge_gap(
            gap_type=gap_type,
            question=question,
            context=f"Severity: {severity.value}. RetrConf={retrieved_memory_confidence}",
            goal_id=goal_id,
            project_id=project_id,
            importance=importance,
            urgency=urgency,
            confidence_in_existing_knowledge=retrieved_memory_confidence,
            evidence_references=evidence_references or [],
        )

        return severity, contract


# Global singleton instance
knowledge_gap_detector = KnowledgeGapDetector()
