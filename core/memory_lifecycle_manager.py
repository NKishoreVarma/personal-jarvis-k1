"""
Memory Lifecycle Manager for Persistent Memory in MARK XLVIII / JARVIS.
Coordinates state transitions across memory lifecycles (ACTIVE, STALE, EXPIRED, CONTRADICTED, INVALIDATED, ARCHIVED)
and enforces TTL invalidation policies without destroying audit trails.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from core.memory_contract import MemoryContract, VerificationState
from core.postgres_memory_store import postgres_memory_store


class MemoryLifecycleManager:
    """
    Evaluates memory expiration and invalidation transitions.
    """

    def check_and_expire_memories(self, current_time: Optional[float] = None) -> int:
        """
        Scans all memories, marks expired items as EXPIRED.
        Returns count of newly expired memories.
        """
        now = current_time if current_time is not None else time.time()
        all_mems = postgres_memory_store.list_memories(limit=1000, include_expired=True)
        count = 0

        for mem in all_mems:
            if mem.expires_at is not None and now > mem.expires_at and mem.verification_state != VerificationState.EXPIRED:
                mem.verification_state = VerificationState.EXPIRED
                mem.updated_at = now
                postgres_memory_store.save_memory(mem)
                count += 1

        return count

    def invalidate_memory(self, memory_id: str, reason: str = "Explicit invalidation") -> bool:
        mem = postgres_memory_store.get_memory(memory_id)
        if not mem:
            return False

        mem.verification_state = VerificationState.INVALIDATED
        mem.metadata["invalidation_reason"] = reason
        mem.updated_at = time.time()
        postgres_memory_store.save_memory(mem)
        return True


# Global singleton instance
memory_lifecycle_manager = MemoryLifecycleManager()
