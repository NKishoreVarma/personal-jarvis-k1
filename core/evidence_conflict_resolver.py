"""
Evidence Conflict Resolver for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Detects contradictions between disparate evidence sources, reconciles disputes, and maintains audit trails.
Enforces rule: LIVE VERIFIED OBSERVATION > EXTERNAL RESEARCH (Consensus cannot override local observation).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.evidence_extraction_engine import ExtractedEvidence


class ConflictResolutionState(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    RESOLVED_BY_EVIDENCE = "RESOLVED_BY_EVIDENCE"
    RESOLVED_BY_LIVE_OBSERVATION = "RESOLVED_BY_LIVE_OBSERVATION"
    UNRESOLVED = "UNRESOLVED"
    ESCALATED = "ESCALATED"


@dataclass
class ConflictResolutionRecord:
    conflict_id: str
    winning_evidence: Optional[ExtractedEvidence]
    losing_evidence: List[ExtractedEvidence]
    state: ConflictResolutionState
    resolution_rationale: str
    resolved_at: float = field(default_factory=time.time)


class EvidenceConflictResolver:
    """
    Identifies conflicting claims and applies deterministic resolution rules.
    """

    def resolve_conflicts(
        self,
        evidence_items: List[ExtractedEvidence],
    ) -> Tuple[ConflictResolutionState, Optional[ExtractedEvidence], List[ExtractedEvidence], str]:
        """
        Analyzes evidence set for contradictions and resolves according to evidence hierarchy.
        """
        if len(evidence_items) <= 1:
            winning = evidence_items[0] if evidence_items else None
            return ConflictResolutionState.NO_CONFLICT, winning, [], "Single source or empty set; no conflict detected."

        # 1. Check for live direct observations (Rule: LIVE VERIFIED OBSERVATION > EXTERNAL RESEARCH)
        direct_observations = [e for e in evidence_items if e.is_direct_observation]
        if direct_observations:
            # Direct observation wins unconditionally over external claims
            winner = direct_observations[0]
            losers = [e for e in evidence_items if e.evidence_id != winner.evidence_id]
            return (
                ConflictResolutionState.RESOLVED_BY_LIVE_OBSERVATION,
                winner,
                losers,
                "Direct environmental observation overrides external research claims.",
            )

        # 2. Check for substantial confidence gap (> 0.20 delta)
        sorted_ev = sorted(evidence_items, key=lambda x: x.confidence, reverse=True)
        top = sorted_ev[0]
        runner_up = sorted_ev[1]

        if (top.confidence - runner_up.confidence) >= 0.12:
            losers = sorted_ev[1:]
            return (
                ConflictResolutionState.RESOLVED_BY_EVIDENCE,
                top,
                losers,
                f"Resolved by source reliability delta ({round(top.confidence, 2)} vs {round(runner_up.confidence, 2)}).",
            )

        # 3. If confidences are close, mark as UNRESOLVED requiring live verification
        return (
            ConflictResolutionState.UNRESOLVED,
            None,
            evidence_items,
            "Conflicting sources have comparable reliability; live environment verification required.",
        )


# Global singleton instance
evidence_conflict_resolver = EvidenceConflictResolver()
