"""
Memory Retriever for MARK XLVIII / JARVIS.
Ranks long-term memories using multi-factor scoring:
Score = Relevance + Freshness + Confidence + Verification + ProjectMatch + ReuseHistory.
Contradicted memories are penalized and ranked near zero.
"""

from __future__ import annotations

import time
from typing import List, Optional

from core.memory_contract import MemoryContract, VerificationState
from core.memory_service import memory_service


class MemoryRetriever:
    """
    Ranks and filters relevant memories for reasoning and query operations.
    """

    def retrieve_relevant(
        self,
        query: str = "",
        project_name: Optional[str] = None,
        top_k: int = 5,
    ) -> List[MemoryContract]:
        """
        Retrieves top-k ranked memories for the given query and project context.
        """
        candidates = memory_service.retrieve(
            query=query,
            project_scope=project_name,
            min_confidence=0.15,
        )

        scored: List[tuple[float, MemoryContract]] = []
        now = time.time()
        q_tokens = set(query.lower().split()) if query else set()

        for mem in candidates:
            if mem.is_expired():
                continue

            # 1. Base confidence
            conf_score = mem.confidence * 0.4

            # 2. Freshness score (exponential decay over 30 days)
            age_days = (now - mem.updated_at) / (86400.0)
            freshness_score = max(0.1, 1.0 - (age_days / 30.0)) * 0.2

            # 3. Verification score
            verif_score = 0.0
            if mem.verification_state == VerificationState.CONFIRMED:
                verif_score = 0.4
            elif mem.verification_state == VerificationState.CONTRADICTED:
                verif_score = -2.0  # de-rank completely
            elif mem.verification_state == VerificationState.STALE:
                verif_score = -0.2

            # 4. Project match score
            proj_score = 0.0
            if project_name and mem.project_scope:
                if mem.project_scope.lower() == project_name.lower():
                    proj_score = 0.5

            # 5. Semantic / Keyword Relevance
            rel_score = 0.0
            if q_tokens:
                text_corpus = f"{mem.subject} {mem.content} {' '.join(mem.tags)}".lower()
                matches = sum(1 for tok in q_tokens if tok in text_corpus)
                rel_score = (matches / max(1, len(q_tokens))) * 0.5

            # 6. Reuse history score
            reuse_score = min(0.3, mem.access_count * 0.05)

            total_score = conf_score + freshness_score + verif_score + proj_score + rel_score + reuse_score

            if total_score > 0.1:
                scored.append((total_score, mem))

        # Sort descending by composite score
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]


# Global singleton instance
memory_retriever = MemoryRetriever()
