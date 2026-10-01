"""
Research Verification Engine for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Validates external research hypotheses against local project state and live environmental observations.
Enforces rule: RESEARCH FINDING != VERIFIED PROJECT FACT.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple

from core.evidence_synthesis_engine import SynthesizedFindings


class ResearchVerificationResult(str, Enum):
    EXTERNAL_CLAIM = "EXTERNAL_CLAIM"
    CORROBORATED_CLAIM = "CORROBORATED_CLAIM"
    LOCAL_OBSERVATION = "LOCAL_OBSERVATION"
    LIVE_VERIFIED_RESULT = "LIVE_VERIFIED_RESULT"


class ResearchVerificationEngine:
    """
    Independently verifies research synthesis against local environment telemetry.
    """

    def verify_synthesis_against_reality(
        self,
        synthesis: SynthesizedFindings,
        local_environment_facts: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResearchVerificationResult, bool, str]:
        """
        Cross-checks research findings against observed local environment facts.
        """
        if not local_environment_facts:
            # External claim only without local verification
            return (
                ResearchVerificationResult.EXTERNAL_CLAIM,
                False,
                "Research finding remains an external claim; no local environment observation provided.",
            )

        # Check if local observation corroborates the research claim
        observed_version = local_environment_facts.get("installed_version")
        researched_version = synthesis.metadata.get("target_version")
        signature_match = local_environment_facts.get("signature_match", False)

        if signature_match or (observed_version and observed_version == researched_version):
            return (
                ResearchVerificationResult.LIVE_VERIFIED_RESULT,
                True,
                "Research finding corroborated by matching local environment observation and error signature.",
            )

        if local_environment_facts.get("contradicts_research", False):
            return (
                ResearchVerificationResult.EXTERNAL_CLAIM,
                False,
                "Local environment observation contradicts research finding.",
            )

        return (
            ResearchVerificationResult.CORROBORATED_CLAIM,
            False,
            "Research finding is plausible but not yet definitively reproduced in local environment.",
        )


# Global singleton instance
research_verification_engine = ResearchVerificationEngine()
