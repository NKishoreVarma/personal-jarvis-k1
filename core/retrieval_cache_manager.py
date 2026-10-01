"""
Retrieval Cache Manager for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Maintains bounded in-memory cache of external search and documentation retrieval results
with source-specific TTL policies to avoid redundant network requests.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from core.external_knowledge_contract import ExternalKnowledgeContract


@dataclass
class CacheEntry:
    cache_key: str
    items: List[ExternalKnowledgeContract]
    cached_at: float
    ttl_seconds: float

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return (now - self.cached_at) > self.ttl_seconds


class RetrievalCacheManager:
    """
    Caches external search items with query normalization and TTL enforcement.
    """

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}

    def _normalize_key(self, query: str, project_scope: str = "FLOW", freshness: str = "recent") -> str:
        raw = f"{query.strip().lower()}:{project_scope.strip().lower()}:{freshness.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def get(self, query: str, project_scope: str = "FLOW", freshness: str = "recent") -> Optional[List[ExternalKnowledgeContract]]:
        """Retrieves non-expired cached knowledge items."""
        key = self._normalize_key(query, project_scope, freshness)
        entry = self._cache.get(key)
        if not entry:
            return None

        if entry.is_expired():
            self._cache.pop(key, None)
            return None

        return entry.items

    def put(
        self,
        query: str,
        items: List[ExternalKnowledgeContract],
        project_scope: str = "FLOW",
        freshness: str = "recent",
        ttl_seconds: float = 3600.0,
    ) -> None:
        """Stores knowledge items in cache with TTL."""
        key = self._normalize_key(query, project_scope, freshness)
        self._cache[key] = CacheEntry(
            cache_key=key,
            items=items,
            cached_at=time.time(),
            ttl_seconds=ttl_seconds,
        )

    def invalidate(self, query: str, project_scope: str = "FLOW") -> None:
        key = self._normalize_key(query, project_scope)
        self._cache.pop(key, None)

    def clear_all(self) -> None:
        self._cache.clear()


# Global singleton instance
retrieval_cache_manager = RetrievalCacheManager()
