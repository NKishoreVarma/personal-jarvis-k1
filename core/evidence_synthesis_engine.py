"""
Evidence Synthesis Engine for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Synthesizes multiple evidence streams into nuanced, uncertainty-aware conclusions with explicit verification criteria.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.evidence_conflict_resolver import ConflictResolutionState, evidence_conflict_resolver
from core.evidence_extraction_engine import ExtractedEvidence


@dataclass
class SynthesizedFindings:
    synthesis_id: str
    gap_id: str
    conclusion: str
    confidence: float
    supporting_evidence: List[ExtractedEvidence]
    contradicting_evidence: List[ExtractedEvidence]
    uncertainty_description: str
    remaining_gaps: List[str]
    verification_requirements: List[str]
    recommended_next_step: str
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "gap_id": self.gap_id,
            "conclusion": self.conclusion,
            "confidence": round(self.confidence, 3),
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "contradicting_evidence": [e.to_dict() for e in self.contradicting_evidence],
            "uncertainty_description": self.uncertainty_description,
            "remaining_gaps": self.remaining_gaps,
            "verification_requirements": self.verification_requirements,
            "recommended_next_step": self.recommended_next_step,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class EvidenceSynthesisEngine:
    """
    Synthesizes research findings, calibrates confidence, and frames explicit verification requirements.
    """

    def synthesize(
        self,
        gap_id: str,
        question: str,
        evidence_items: List[ExtractedEvidence],
    ) -> SynthesizedFindings:
        """
        Executes conflict analysis and builds structured synthesis findings.
        """
        if not evidence_items:
            return SynthesizedFindings(
                synthesis_id=f"syn_{uuid.uuid4().hex[:8]}",
                gap_id=gap_id,
                conclusion=f"Insufficient evidence available to address '{question}'.",
                confidence=0.0,
                supporting_evidence=[],
                contradicting_evidence=[],
                uncertainty_description="No source evidence was extracted.",
                remaining_gaps=[question],
                verification_requirements=["Execute targeted research or manual inspection."],
                recommended_next_step="Plan targeted documentation lookup.",
            )

        # Conflict resolution check
        state, winner, losers, rationale = evidence_conflict_resolver.resolve_conflicts(evidence_items)

        if state == ConflictResolutionState.UNRESOLVED:
            return SynthesizedFindings(
                synthesis_id=f"syn_{uuid.uuid4().hex[:8]}",
                gap_id=gap_id,
                conclusion=f"Evidence regarding '{question}' is inconclusive due to conflicting source claims.",
                confidence=0.40,
                supporting_evidence=evidence_items[:1],
                contradicting_evidence=evidence_items[1:],
                uncertainty_description=rationale,
                remaining_gaps=[f"Resolve conflict: {rationale}"],
                verification_requirements=["Perform live environmental probe to determine reality."],
                recommended_next_step="Inspect local package version and runtime error signature directly.",
            )

        supporting = [winner] if winner else evidence_items
        contradicting = losers
        base_conf = winner.confidence if winner else 0.80

        # Adjust confidence based on whether direct observation exists
        has_direct_obs = any(e.is_direct_observation for e in supporting)
        final_conf = min(1.0, base_conf + 0.10) if has_direct_obs else min(0.85, base_conf)

        conclusion_prefix = "Verified:" if has_direct_obs else "Evidence suggests:"
        conclusion = f"{conclusion_prefix} {winner.claim_text if winner else evidence_items[0].claim_text}"

        uncertainty = (
            "Observation verified directly in local environment."
            if has_direct_obs
            else "Finding is grounded in external documentation; local environment verification recommended."
        )

        verif_reqs = []
        if not has_direct_obs:
            verif_reqs.append("Verify local dependency version and runtime reproduction.")

        return SynthesizedFindings(
            synthesis_id=f"syn_{uuid.uuid4().hex[:8]}",
            gap_id=gap_id,
            conclusion=conclusion,
            confidence=final_conf,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            uncertainty_description=uncertainty,
            remaining_gaps=[],
            verification_requirements=verif_reqs,
            recommended_next_step="Proceed with verified diagnostic plan." if has_direct_obs else "Verify hypothesis against local environment.",
        )


# Global singleton instance
evidence_synthesis_engine = EvidenceSynthesisEngine()
