"""
Source Reliability Engine for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Evaluates source authority, recency, provenance, and corroboration to compute deterministic reliability scores.
Enforces rule: SOURCE AUTHORITY != TRUTH (Primary verified observations always supersede external sources).
"""

from __future__ import annotations

from typing import Dict

from core.source_evaluation_contract import (
    SourceEvaluationContract,
    SourceReliabilityState,
    SourceType,
)

_BASE_METRICS: Dict[SourceType, Dict[str, float]] = {
    SourceType.PRIMARY: {"auth": 1.0, "rec": 0.95, "prov": 1.0, "corr": 0.85, "rel": 0.95},
    SourceType.OFFICIAL_DOCUMENTATION: {"auth": 0.95, "rec": 0.90, "prov": 0.95, "corr": 0.80, "rel": 0.90},
    SourceType.OFFICIAL_CHANGELOG: {"auth": 0.90, "rec": 0.90, "prov": 0.90, "corr": 0.75, "rel": 0.90},
    SourceType.REPOSITORY: {"auth": 0.80, "rec": 0.80, "prov": 0.85, "corr": 0.70, "rel": 0.80},
    SourceType.ACADEMIC: {"auth": 0.70, "rec": 0.75, "prov": 0.80, "corr": 0.65, "rel": 0.75},
    SourceType.TECHNICAL_ARTICLE: {"auth": 0.65, "rec": 0.70, "prov": 0.65, "corr": 0.55, "rel": 0.70},
    SourceType.ISSUE_TRACKER: {"auth": 0.60, "rec": 0.70, "prov": 0.60, "corr": 0.50, "rel": 0.65},
    SourceType.COMMUNITY: {"auth": 0.45, "rec": 0.50, "prov": 0.40, "corr": 0.35, "rel": 0.50},
    SourceType.FORUM: {"auth": 0.40, "rec": 0.50, "prov": 0.30, "corr": 0.30, "rel": 0.45},
    SourceType.SEARCH_RESULT: {"auth": 0.30, "rec": 0.50, "prov": 0.20, "corr": 0.20, "rel": 0.40},
    SourceType.UNKNOWN: {"auth": 0.10, "rec": 0.30, "prov": 0.10, "corr": 0.10, "rel": 0.20},
}


class SourceReliabilityEngine:
    """
    Ranks source reliability using multi-factor evaluation.
    """

    def evaluate_source(self, source: SourceEvaluationContract) -> float:
        """
        Computes composite reliability score and sets the evaluation state.
        Formula:
        RELIABILITY = 0.30 * AUTH + 0.20 * REC + 0.20 * PROV + 0.15 * CORR + 0.15 * REL
        """
        base = _BASE_METRICS.get(source.source_type, {"auth": 0.5, "rec": 0.8, "prov": 0.8, "corr": 0.5, "rel": 0.8})

        auth = source.authority_score if source.authority_score != 0.50 else base["auth"]
        rec = source.recency_score if source.recency_score != 0.80 else base["rec"]
        prov = source.provenance_score if source.provenance_score != 0.80 else base["prov"]
        corr = source.corroboration_score if source.corroboration_score != 0.50 else base["corr"]
        rel = source.relevance_score if source.relevance_score != 0.80 else base["rel"]

        reliability = (
            0.30 * auth
            + 0.20 * rec
            + 0.20 * prov
            + 0.15 * corr
            + 0.15 * rel
        )

        clamped = max(0.0, min(1.0, reliability))
        source.reliability_score = clamped

        if clamped >= 0.75:
            source.evaluation_state = SourceReliabilityState.VERY_HIGH
        elif clamped >= 0.60:
            source.evaluation_state = SourceReliabilityState.HIGH
        elif clamped >= 0.40:
            source.evaluation_state = SourceReliabilityState.MODERATE
        elif clamped >= 0.20:
            source.evaluation_state = SourceReliabilityState.LOW
        else:
            source.evaluation_state = SourceReliabilityState.REJECTED

        return clamped


# Global singleton instance
source_reliability_engine = SourceReliabilityEngine()
