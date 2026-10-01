"""
Semantic Memory Retriever for PGVector Intelligence in MARK XLVIII / JARVIS.
Ranks retrieved memories using multi-factor evidence scoring:
Semantic Similarity (35%) + Verification Quality (25%) + Freshness (15%) + Importance (10%) + Project Relevance (10%) + Goal Relevance (5%).
Enforces rule: Highly similar contradicted memories rank below verified memories.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from core.embedding_service import embedding_service
from core.memory_contract import MemoryContract, MemoryType, VerificationState
from core.postgres_memory_store import postgres_memory_store


class SemanticMemoryRetriever:
    """
    Executes semantic similarity search with evidence-aware multi-factor ranking.
    """

    def retrieve_memories(
        self,
        query: str,
        project_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        min_score_threshold: float = 0.30,
        limit: int = 5,
    ) -> List[Tuple[MemoryContract, float]]:
        """
        Retrieves and ranks memories based on semantic similarity and verification quality.
        Returns list of (MemoryContract, composite_score).
        """
        query_vec = embedding_service.get_embedding(query)
        candidates = postgres_memory_store.vector_similarity_search(query_vec, project_id=project_id, limit=limit * 3)

        scored: List[Tuple[MemoryContract, float]] = []

        for mem, sim in candidates:
            if mem.is_expired():
                continue

            if sim < 0.30:
                continue

            if memory_type and mem.memory_type != memory_type:
                continue

            # 1. Verification Score (0.0 to 1.0)
            if mem.verification_state == VerificationState.VERIFIED:
                verif_score = 1.0
            elif mem.verification_state == VerificationState.CORROBORATED:
                verif_score = 0.8
            elif mem.verification_state == VerificationState.OBSERVED:
                verif_score = 0.6
            elif mem.verification_state == VerificationState.UNVERIFIED:
                verif_score = 0.3
            elif mem.verification_state == VerificationState.STALE:
                verif_score = 0.2
            elif mem.verification_state in [VerificationState.CONTRADICTED, VerificationState.INVALIDATED]:
                verif_score = -1.0  # Heavy penalty
            else:
                verif_score = 0.1

            # 2. Freshness Score (0.0 to 1.0)
            now = time.time()
            age_days = (now - mem.updated_at) / 86400.0
            freshness = max(0.1, min(1.0, 1.0 - (age_days / 30.0)))

            # 3. Importance Score (0.0 to 1.0)
            importance = mem.importance

            # 4. Project Relevance (0.0 or 1.0)
            proj_rel = 1.0 if (project_id and mem.project_id and mem.project_id.lower() == project_id.lower()) else 0.5

            # 5. Goal Relevance (0.0 or 1.0)
            goal_rel = 1.0 if (goal_id and mem.goal_id and mem.goal_id == goal_id) else 0.5

            # Composite Scoring Formula
            # If contradicted, drastically depress final score
            if verif_score < 0:
                final_score = -0.50
            else:
                final_score = (
                    sim * 0.35
                    + verif_score * 0.25
                    + freshness * 0.15
                    + importance * 0.10
                    + proj_rel * 0.10
                    + goal_rel * 0.05
                )

            if final_score >= min_score_threshold:
                scored.append((mem, round(final_score, 3)))

        # Sort by composite score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


# Global singleton instance
semantic_memory_retriever = SemanticMemoryRetriever()
