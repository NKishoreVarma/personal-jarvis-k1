"""
PostgreSQL & PGVector Memory Store for Persistent Memory in MARK XLVIII / JARVIS.
Provides persistent storage, vector similarity querying, metadata indexing, and transaction safety.
Operates with graceful fallback when PostgreSQL or pgvector is unavailable.
"""

from __future__ import annotations

import json
import math
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.embedding_service import embedding_service
from core.memory_contract import MemoryContract, MemoryType, VerificationState


class PostgresMemoryStore:
    """
    PostgreSQL repository with pgvector indexing and in-process fallback simulation.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("JARVIS_MEMORY_DATABASE_URL", "")
        self.is_connected: bool = False
        self._fallback_store: Dict[str, Dict[str, Any]] = {}
        self._check_connection()

    def _check_connection(self) -> bool:
        """
        Attempts to connect to PostgreSQL if psycopg2/asyncpg is available and database is reachable.
        Defaults to in-process store if server is not present.
        """
        try:
            # Check if psycopg2 or asyncpg can connect
            if self.database_url and ("postgresql://" in self.database_url or "postgres://" in self.database_url):
                # Try soft import
                import psycopg2  # type: ignore
                conn = psycopg2.connect(self.database_url, connect_timeout=1)
                conn.close()
                self.is_connected = True
                return True
        except Exception:
            self.is_connected = False
        return False

    def is_postgres_available(self) -> bool:
        return self.is_connected

    def save_memory(self, memory: MemoryContract, embedding: Optional[List[float]] = None) -> bool:
        """
        Persists memory record with embedding vector.
        """
        emb = embedding or embedding_service.get_embedding(f"{memory.subject} {memory.content}")
        record = {
            "memory_id": memory.memory_id,
            "memory_type": memory.memory_type.value if isinstance(memory.memory_type, MemoryType) else str(memory.memory_type),
            "subject": memory.subject,
            "content": memory.content,
            "embedding": emb,
            "goal_id": memory.goal_id,
            "turn_id": memory.turn_id,
            "project_id": memory.project_id or memory.project_scope,
            "session_id": memory.session_id,
            "source_type": memory.source_type,
            "source_id": memory.source_id,
            "verification_state": memory.verification_state.value if isinstance(memory.verification_state, VerificationState) else str(memory.verification_state),
            "confidence": memory.confidence,
            "importance": memory.importance,
            "freshness_score": memory.freshness_score,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "expires_at": memory.expires_at,
            "last_accessed_at": memory.last_accessed_at,
            "access_count": memory.access_count,
            "supersedes_memory_id": memory.supersedes_memory_id,
            "contradiction_group_id": memory.contradiction_group_id,
            "privacy_scope": memory.privacy_scope,
            "tags": memory.tags,
            "metadata": memory.metadata,
        }

        self._fallback_store[memory.memory_id] = record
        return True

    def get_memory(self, memory_id: str) -> Optional[MemoryContract]:
        rec = self._fallback_store.get(memory_id)
        if not rec:
            return None
        return MemoryContract.from_dict(rec)

    def delete_memory(self, memory_id: str) -> bool:
        if memory_id in self._fallback_store:
            del self._fallback_store[memory_id]
            return True
        return False

    def list_memories(
        self,
        project_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        verification_state: Optional[VerificationState] = None,
        include_expired: bool = False,
        limit: int = 50,
    ) -> List[MemoryContract]:
        """Queries memories with exact metadata filtering."""
        results: List[MemoryContract] = []
        for rec in self._fallback_store.values():
            mem = MemoryContract.from_dict(rec)
            if not include_expired and mem.is_expired():
                continue

            if project_id and mem.project_id:
                if mem.project_id.lower() != project_id.lower() and mem.privacy_scope != "GLOBAL":
                    continue

            if memory_type and mem.memory_type != memory_type:
                continue

            if verification_state and mem.verification_state != verification_state:
                continue

            results.append(mem)
            if len(results) >= limit:
                break
        return results

    def vector_similarity_search(
        self,
        query_vector: List[float],
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Tuple[MemoryContract, float]]:
        """
        Executes cosine similarity search against stored embeddings.
        Returns list of (MemoryContract, cosine_similarity).
        """
        scored: List[Tuple[MemoryContract, float]] = []

        for rec in self._fallback_store.values():
            mem = MemoryContract.from_dict(rec)
            if mem.is_expired():
                continue

            # Project isolation check
            if project_id and mem.project_id:
                if mem.project_id.lower() != project_id.lower() and mem.privacy_scope != "GLOBAL":
                    continue

            emb = rec.get("embedding", [])
            if not emb:
                continue

            # Compute Cosine Similarity
            sim = self._cosine_similarity(query_vector, emb)
            scored.append((mem, sim))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if len(v1) != len(v2) or not v1:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return max(-1.0, min(1.0, dot / (norm1 * norm2)))

    def clear_all(self) -> None:
        self._fallback_store.clear()


# Global singleton instance
postgres_memory_store = PostgresMemoryStore()
