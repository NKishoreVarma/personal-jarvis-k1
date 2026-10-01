"""
Retrieval Learning Loop for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Tracks whether external knowledge retrieval materially contributed to successful outcomes,
penalizes unhelpful or redundant searches, and adjusts retrieval confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RetrievalOutcomeRecord:
    query: str
    source_title: str
    influenced_plan: bool
    outcome_succeeded: bool
    was_redundant: bool = False


class RetrievalLearningLoop:
    """
    Evaluates historical retrieval effectiveness and trains retrieval preference weights.
    """

    def __init__(self):
        self._records: List[RetrievalOutcomeRecord] = []
        self._source_usefulness: Dict[str, float] = {}  # source_title -> usefulness ratio

    def record_retrieval_outcome(
        self,
        query: str,
        source_title: str,
        influenced_plan: bool,
        outcome_succeeded: bool,
        was_redundant: bool = False,
    ) -> None:
        """Records retrieval audit record and updates usefulness ratio."""
        rec = RetrievalOutcomeRecord(
            query=query,
            source_title=source_title,
            influenced_plan=influenced_plan,
            outcome_succeeded=outcome_succeeded,
            was_redundant=was_redundant,
        )
        self._records.append(rec)

        current = self._source_usefulness.get(source_title, 0.80)
        if outcome_succeeded and influenced_plan:
            self._source_usefulness[source_title] = min(1.0, current + 0.05)
        elif not outcome_succeeded or was_redundant:
            self._source_usefulness[source_title] = max(0.1, current - 0.10)

    def get_source_usefulness(self, source_title: str) -> float:
        return self._source_usefulness.get(source_title, 0.80)

    def get_unnecessary_retrieval_rate(self) -> float:
        if not self._records:
            return 0.0
        redundant_count = sum(1 for r in self._records if r.was_redundant)
        return redundant_count / len(self._records)

    def clear_all(self) -> None:
        self._records.clear()
        self._source_usefulness.clear()


# Global singleton instance
retrieval_learning_loop = RetrievalLearningLoop()
