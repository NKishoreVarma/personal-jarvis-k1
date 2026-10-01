"""
Long-Term Memory Service for MARK XLVIII / JARVIS.
Provides persistent storage, semantic retrieval via PGVector, quality gating, project isolation,
contradiction management, and graceful fallback when PostgreSQL is unavailable.
"""

from __future__ import annotations

import json
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.embedding_service import embedding_service
from core.memory_access_governor import memory_access_governor
from core.memory_contract import MemoryContract, MemoryType, VerificationState
from core.memory_quality_gate import memory_quality_gate
from core.memory_retrieval_cache import memory_retrieval_cache
from core.postgres_memory_store import postgres_memory_store
from core.semantic_memory_retriever import semantic_memory_retriever
from core.storage_configuration import StorageHealthStatus, storage_configuration


class MemoryServiceMode(str, Enum):
    POSTGRES_ACTIVE = "POSTGRES_ACTIVE"
    FALLBACK_MEMORY = "FALLBACK_MEMORY"
    DEGRADED = "DEGRADED"
    READ_ONLY = "READ_ONLY"


class MemoryService:
    """
    Unified persistent memory service coordinating PGVector storage, semantic retrieval, and fallback caching.
    """

    def __init__(self, storage_path: str = "data/long_term_memory.json"):
        self.storage_path = storage_path
        self._memories: Dict[str, MemoryContract] = {}
        self.enabled: bool = True
        self._load_from_disk()

    @property
    def mode(self) -> MemoryServiceMode:
        if not self.enabled:
            return MemoryServiceMode.READ_ONLY
        if storage_configuration.is_degraded():
            return MemoryServiceMode.DEGRADED
        if postgres_memory_store.is_postgres_available():
            return MemoryServiceMode.POSTGRES_ACTIVE
        return MemoryServiceMode.FALLBACK_MEMORY

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def _load_from_disk(self) -> None:
        """Loads persistent memories from JSON storage if present."""
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for item in raw_data:
                    mem = MemoryContract.from_dict(item)
                    if not mem.is_expired():
                        self._memories[mem.memory_id] = mem
                        postgres_memory_store.save_memory(mem)
        except Exception as e:
            print(f"[MEMORY_SERVICE] Warning loading memory store: {e}")

    def _persist_to_disk(self) -> None:
        """Saves active memories to JSON storage asynchronously or safely."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            active_items = [
                m.to_dict() for m in self._memories.values()
                if not m.is_expired() and m.verification_state != VerificationState.EXPIRED
            ]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(active_items, f, indent=2)
        except Exception as e:
            print(f"[MEMORY_SERVICE] Warning saving memory store: {e}")

    def store(self, memory: MemoryContract) -> str:
        """
        Validates through MemoryQualityGate and stores in PGVector repository and fallback cache.
        """
        if not self.enabled:
            return ""

        # 1. Quality Gate Check
        passed, reason_code, explanation = memory_quality_gate.validate_memory_for_storage(memory)
        if not passed:
            print(f"[MEMORY_SERVICE] ⚠️ Memory rejected by quality gate ({reason_code}): {explanation}")
            return ""

        # 2. Deduplication check
        for existing in self._memories.values():
            if (
                existing.subject.strip().lower() == memory.subject.strip().lower()
                and existing.content.strip().lower() == memory.content.strip().lower()
                and existing.project_id == (memory.project_id or memory.project_scope)
            ):
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.updated_at = time.time()
                existing.touch()
                self._persist_to_disk()
                postgres_memory_store.save_memory(existing)
                return existing.memory_id

        # 3. Store in memory store & fallback
        self._memories[memory.memory_id] = memory
        self._persist_to_disk()
        postgres_memory_store.save_memory(memory)
        memory_retrieval_cache.invalidate_all()

        return memory.memory_id

    def get_memory(self, memory_id: str) -> Optional[MemoryContract]:
        mem = self._memories.get(memory_id) or postgres_memory_store.get_memory(memory_id)
        if mem and mem.is_expired():
            self._memories.pop(memory_id, None)
            return None
        return mem

    def semantic_retrieve(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Tuple[MemoryContract, float]]:
        """
        Performs semantic similarity search with caching and project isolation.
        """
        cached = memory_retrieval_cache.get(query, project_id)
        if cached is not None:
            return cached

        results = semantic_memory_retriever.retrieve_memories(query, project_id=project_id, limit=limit)
        # Apply Access Governor
        filtered = []
        for mem, score in results:
            acc = memory_access_governor.filter_accessible_memories([mem], requesting_project_id=project_id)
            if acc:
                filtered.append((mem, score))

        memory_retrieval_cache.put(query, filtered, project_id=project_id)
        return filtered

    def retrieve(
        self,
        query: str = "",
        project_scope: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        min_confidence: float = 0.2,
        limit: int = 10,
    ) -> List[MemoryContract]:
        """
        Standard memory retrieval with semantic fallbacks and project isolation.
        """
        if query:
            semantic_res = self.semantic_retrieve(query, project_id=project_scope, limit=limit)
            if semantic_res:
                return [m for m, _ in semantic_res]

            # Keyword matching fallback
            query_words = set(query.lower().split())
            candidates = postgres_memory_store.list_memories(
                project_id=project_scope,
                memory_type=memory_type,
                limit=limit,
            )
            accessible = memory_access_governor.filter_accessible_memories(candidates, requesting_project_id=project_scope)
            matched = []
            for m in accessible:
                if m.is_contradicted() or m.confidence < min_confidence:
                    continue
                text_corpus = f"{m.subject} {m.content} {' '.join(m.tags)}".lower()
                if any(w in text_corpus for w in query_words):
                    matched.append(m)
            return matched

        # No query: return all accessible active memories
        candidates = postgres_memory_store.list_memories(
            project_id=project_scope,
            memory_type=memory_type,
            limit=limit,
        )
        accessible = memory_access_governor.filter_accessible_memories(candidates, requesting_project_id=project_scope)
        return [m for m in accessible if m.confidence >= min_confidence and not m.is_contradicted()]

    def mark_verified(self, memory_id: str) -> bool:
        mem = self.get_memory(memory_id)
        if not mem:
            return False
        mem.verification_state = VerificationState.VERIFIED
        mem.confidence = min(1.0, mem.confidence + 0.15)
        mem.updated_at = time.time()
        self._persist_to_disk()
        postgres_memory_store.save_memory(mem)
        memory_retrieval_cache.invalidate_all()
        return True

    def mark_contradicted(self, memory_id: str, reason: str = "") -> bool:
        mem = self.get_memory(memory_id)
        if not mem:
            return False
        mem.verification_state = VerificationState.CONTRADICTED
        mem.confidence = max(0.0, mem.confidence - 0.5)
        mem.updated_at = time.time()
        if reason:
            mem.metadata["contradiction_reason"] = reason
        self._persist_to_disk()
        postgres_memory_store.save_memory(mem)
        memory_retrieval_cache.invalidate_all()
        return True

    def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        mem = self.get_memory(memory_id)
        if not mem:
            return False
        for k, v in updates.items():
            if hasattr(mem, k):
                setattr(mem, k, v)
        mem.updated_at = time.time()
        self._persist_to_disk()
        postgres_memory_store.save_memory(mem)
        memory_retrieval_cache.invalidate_all()
        return True

    def invalidate(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            self._memories.pop(memory_id)
            postgres_memory_store.delete_memory(memory_id)
            self._persist_to_disk()
            memory_retrieval_cache.invalidate_all()
            return True
        return False

    def forget(self, query_or_subject: str, project_scope: Optional[str] = None) -> int:
        """
        User-controlled forget operation.
        """
        q_clean = query_or_subject.strip().lower()
        to_remove = []

        for m_id, m in list(self._memories.items()):
            if project_scope and m.project_id and m.project_id.lower() != project_scope.lower():
                continue
            if (
                m_id == query_or_subject
                or q_clean in m.subject.lower()
                or q_clean in m.content.lower()
                or (project_scope and m.project_id and project_scope.lower() in q_clean)
            ):
                to_remove.append(m_id)

        for m_id in to_remove:
            self._memories.pop(m_id, None)
            postgres_memory_store.delete_memory(m_id)

        if to_remove:
            self._persist_to_disk()
            memory_retrieval_cache.invalidate_all()

        return len(to_remove)

    def clear(self) -> None:
        self._memories.clear()
        postgres_memory_store.clear_all()
        memory_retrieval_cache.clear_all()
        self._persist_to_disk()

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "enabled": self.enabled,
            "total_memories": len(self._memories),
            "postgres_available": postgres_memory_store.is_postgres_available(),
            "storage_status": storage_configuration.status.value,
        }


# Global singleton instance
memory_service = MemoryService()
