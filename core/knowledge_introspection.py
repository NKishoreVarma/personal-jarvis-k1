"""
Knowledge Introspection for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Provides natural, concise explanations of external citations, verification levels, and confidence
without exposing internal reasoning tokens or raw chain-of-thought traces.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.claim_verification_engine import ClaimVerificationLevel
from core.knowledge_provenance_tracker import knowledge_provenance_tracker


class KnowledgeIntrospection:
    """
    Answers user questions regarding citations, confidence, and verification states.
    """

    def explain_source(self, project_scope: str = "FLOW") -> str:
        """Explains where the current knowledge/recommendation came from."""
        return knowledge_provenance_tracker.format_source_explanation(project_scope)

    def explain_confidence(
        self,
        verification_level: ClaimVerificationLevel = ClaimVerificationLevel.ENVIRONMENT_SUPPORTED,
        is_corroborated: bool = True,
    ) -> str:
        """Explains certainty and verification status."""
        if verification_level in [ClaimVerificationLevel.ENVIRONMENT_SUPPORTED, ClaimVerificationLevel.OUTCOME_VERIFIED]:
            return "I am confident in this approach because it is corroborated by official documentation and verified against your local configuration."
        elif is_corroborated:
            return "I found multiple matching technical references, but it still requires verification against your environment."
        else:
            return "I found one potential reference, but have not verified it against your environment yet."


# Global singleton instance
knowledge_introspection = KnowledgeIntrospection()
