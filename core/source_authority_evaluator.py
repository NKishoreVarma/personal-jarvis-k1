"""
Source Authority Evaluator for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Evaluates the authority, official standing, technical reliability, and trustworthiness
of external knowledge sources without opaque or hardcoded trust traps.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple

from core.external_knowledge_contract import ExternalKnowledgeContract, SourceCategory


class AuthorityLevel(str, Enum):
    AUTHORITATIVE = "AUTHORITATIVE"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNTRUSTED = "UNTRUSTED"


# Known authoritative tech domains
OFFICIAL_DOMAINS = [
    "nextjs.org",
    "react.dev",
    "nodejs.org",
    "python.org",
    "developer.mozilla.org",
    "github.com",
    "stackoverflow.com",
    "typescriptlang.org",
]


class SourceAuthorityEvaluator:
    """
    Computes explainable authority ratings and scores for external knowledge items.
    """

    def evaluate_authority(self, item: ExternalKnowledgeContract) -> Tuple[AuthorityLevel, float, str]:
        """
        Evaluates source authority, returning (AuthorityLevel, score, explanation).
        """
        score = 0.50
        reasons = []

        url_lower = item.source_url.lower()

        # 1. Source Category Boost
        if item.source_type == SourceCategory.OFFICIAL_DOCUMENTATION:
            score += 0.35
            reasons.append("Official project documentation")
        elif item.source_type in [SourceCategory.PROJECT_REPOSITORY, SourceCategory.PACKAGE_DOCUMENTATION]:
            score += 0.25
            reasons.append("Package or project repository source")
        elif item.source_type == SourceCategory.TECHNICAL_ARTICLE:
            score += 0.10
            reasons.append("Technical article")

        # 2. Domain Recognition
        if any(dom in url_lower for dom in OFFICIAL_DOMAINS):
            score += 0.15
            reasons.append("Recognized authoritative developer domain")

        # 3. Specificity & Claims Bonus
        if len(item.claims) >= 2:
            score += 0.05

        # Normalize score between 0.10 and 1.00
        score = max(0.10, min(1.00, score))

        # Classify Level
        if score >= 0.90:
            level = AuthorityLevel.AUTHORITATIVE
        elif score >= 0.75:
            level = AuthorityLevel.HIGH
        elif score >= 0.50:
            level = AuthorityLevel.MEDIUM
        elif score >= 0.30:
            level = AuthorityLevel.LOW
        else:
            level = AuthorityLevel.UNTRUSTED

        explanation = f"{level.value} authority: {', '.join(reasons) if reasons else 'General search result'}."
        return level, round(score, 3), explanation


# Global singleton instance
source_authority_evaluator = SourceAuthorityEvaluator()
