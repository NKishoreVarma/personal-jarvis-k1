"""
Knowledge Synthesis Engine for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Fuses local observations, corroborated external evidence, long-term memory, and verified skills
into an evidence-grounded operational context.
Enforces rule: Never present unverified speculation or external claims as certainty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.claim_verification_engine import ClaimVerificationLevel
from core.external_knowledge_contract import ExternalKnowledgeContract, VerificationState


@dataclass
class KnowledgeSynthesis:
    project_scope: str
    verified_facts: List[str] = field(default_factory=list)
    strong_evidence: List[str] = field(default_factory=list)
    unverified_possibilities: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    overall_confidence: float = 0.80
    operational_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_scope": self.project_scope,
            "verified_facts": self.verified_facts,
            "strong_evidence": self.strong_evidence,
            "unverified_possibilities": self.unverified_possibilities,
            "contradictions": self.contradictions,
            "unknowns": self.unknowns,
            "overall_confidence": round(self.overall_confidence, 3),
            "operational_summary": self.operational_summary,
        }


class KnowledgeSynthesisEngine:
    """
    Synthesizes multi-source evidence into structured operational intelligence.
    """

    def synthesize_knowledge(
        self,
        project_scope: str,
        local_observations: Dict[str, Any],
        external_items: List[ExternalKnowledgeContract],
        verification_level: ClaimVerificationLevel = ClaimVerificationLevel.UNVERIFIED,
    ) -> KnowledgeSynthesis:
        """
        Synthesizes facts, external evidence, and contradictions.
        """
        verified_facts = []
        strong_evidence = []
        unverified_possibilities = []
        contradictions = []
        unknowns = []

        # 1. Local reality facts
        if local_observations.get("process_running"):
            verified_facts.append(f"{project_scope} process is actively running (PID {local_observations.get('pid')}).")
        if local_observations.get("port"):
            verified_facts.append(f"Port {local_observations.get('port')} is bound to {project_scope}.")

        # 2. Categorize external items
        for item in external_items:
            if item.verification_state == VerificationState.CONTRADICTED:
                contradictions.append(f"Contradicted claim from {item.title}: {item.content_summary}")
            elif item.verification_state == VerificationState.VERIFIED or verification_level in [ClaimVerificationLevel.ENVIRONMENT_SUPPORTED, ClaimVerificationLevel.OUTCOME_VERIFIED]:
                strong_evidence.append(f"{item.title}: {item.content_summary}")
            elif item.verification_state == VerificationState.CORROBORATED:
                strong_evidence.append(f"Corroborated ({item.title}): {item.content_summary}")
            else:
                unverified_possibilities.append(f"Unverified suggestion ({item.title}): {item.content_summary}")

        # 3. Overall confidence
        if contradictions and not strong_evidence:
            conf = 0.30
        elif strong_evidence:
            conf = 0.90
        elif verified_facts:
            conf = 0.85
        else:
            conf = 0.50

        summary = f"Synthesized {len(verified_facts)} verified facts and {len(strong_evidence)} verified evidence sources."

        return KnowledgeSynthesis(
            project_scope=project_scope,
            verified_facts=verified_facts,
            strong_evidence=strong_evidence,
            unverified_possibilities=unverified_possibilities,
            contradictions=contradictions,
            unknowns=unknowns,
            overall_confidence=conf,
            operational_summary=summary,
        )


# Global singleton instance
knowledge_synthesis_engine = KnowledgeSynthesisEngine()
