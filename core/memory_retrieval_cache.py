"""
Memory Retrieval Cache for Persistent Memory in MARK XLVIII / JARVIS.
Caches semantic query results, memory IDs, and similarity scores with project-aware keys and TTL invalidation.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.memory_contract import MemoryContract


@dataclass
class MemoryCacheEntry:
    key: str
    items: List[Tuple[MemoryContract, float]]
    cached_at: float
    ttl_seconds: float

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return (now - self.cached_at) > self.ttl_seconds


class MemoryRetrievalCache:
    """
    LRU-style retrieval cache for semantic query results.
    """

    def __init__(self, default_ttl: float = 300.0):
        self.default_ttl = default_ttl
        self._cache: Dict[str, MemoryCacheEntry] = {}

    def _hash_key(self, query: str, project_id: Optional[str] = None) -> str:
        raw = f"{query.strip().lower()}:{str(project_id).strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def get(self, query: str, project_id: Optional[str] = None) -> Optional[List[Tuple[MemoryContract, float]]]:
        k = self._hash_key(query, project_id)
        entry = self._cache.get(k)
        if not entry:
            return None
        if entry.is_expired():
            self._cache.pop(k, None)
            return None
        return entry.items

    def put(
        self,
        query: str,
        items: List[Tuple[MemoryContract, float]],
        project_id: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        k = self._hash_key(query, project_id)
        self._cache[k] = MemoryCacheEntry(
            key=k,
            items=items,
            cached_at=time.time(),
            ttl_seconds=ttl_seconds or self.default_ttl,
        )
        if len(self._cache) > 500:
            self._cache.pop(next(iter(self._cache)))

    def invalidate_all(self) -> None:
        self._cache.clear()

    def clear_all(self) -> None:
        self._cache.clear()


# Global singleton instance
memory_retrieval_cache = MemoryRetrievalCache()
