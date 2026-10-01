"""
Evidence Extraction Engine for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Converts raw source documents and observations into structured claims with explicit provenance.
Enforces rule: Extracted claims do not automatically become verified memory.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.source_evaluation_contract import SourceEvaluationContract


class ClaimType(str, Enum):
    OBSERVATION = "OBSERVATION"
    DOCUMENTATION_FACT = "DOCUMENTATION_FACT"
    VERSION_CHANGE = "VERSION_CHANGE"
    ERROR_SIGNATURE = "ERROR_SIGNATURE"
    COMPATIBILITY_CLAIM = "COMPATIBILITY_CLAIM"
    DIAGNOSTIC_HYPOTHESIS = "DIAGNOSTIC_HYPOTHESIS"
    VERIFICATION_RESULT = "VERIFICATION_RESULT"
    UNKNOWN = "UNKNOWN"


@dataclass
class ExtractedEvidence:
    evidence_id: str
    source_id: str
    claim_type: ClaimType
    claim_text: str
    confidence: float = 0.80
    is_direct_observation: bool = False
    scope: str = "GLOBAL"
    extraction_timestamp: float = field(default_factory=time.time)
    provenance: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "claim_type": self.claim_type.value,
            "claim_text": self.claim_text,
            "confidence": round(self.confidence, 3),
            "is_direct_observation": self.is_direct_observation,
            "scope": self.scope,
            "extraction_timestamp": self.extraction_timestamp,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }


class EvidenceExtractionEngine:
    """
    Extracts structured claims from evaluated sources while preserving provenance.
    """

    def extract_evidence(
        self,
        source: SourceEvaluationContract,
        claim_type: ClaimType,
        claim_text: str,
        is_direct_observation: bool = False,
        scope: str = "GLOBAL",
        confidence: Optional[float] = None,
    ) -> ExtractedEvidence:
        """
        Creates a structured evidence record linked to source metadata.
        """
        calc_conf = confidence if confidence is not None else source.reliability_score
        ev = ExtractedEvidence(
            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
            source_id=source.source_id,
            claim_type=claim_type,
            claim_text=claim_text.strip(),
            confidence=calc_conf,
            is_direct_observation=is_direct_observation,
            scope=scope,
            extraction_timestamp=time.time(),
            provenance=f"{source.source_type.value}:{source.url_or_path}",
        )
        source.evidence_references.append(ev.evidence_id)
        return ev


# Global singleton instance
evidence_extraction_engine = EvidenceExtractionEngine()
