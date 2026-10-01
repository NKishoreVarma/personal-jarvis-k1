"""
Memory Contradiction Engine for Persistent Memory in MARK XLVIII / JARVIS.
Detects contradictions between live observations and stored memories, updates verification states,
links superseding memories, and preserves historical audit traces.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.memory_contract import MemoryContract, VerificationState
from core.postgres_memory_store import postgres_memory_store


class MemoryContradictionEngine:
    """
    Manages contradiction detection and superseding memory linking.
    """

    def process_contradiction(
        self,
        stale_memory_id: str,
        new_memory: MemoryContract,
        conflict_reason: str = "Live reality contradiction",
    ) -> Optional[MemoryContract]:
        """
        Marks stale memory as CONTRADICTED, links superseding ID, and persists updated states.
        """
        stale_mem = postgres_memory_store.get_memory(stale_memory_id)
        if not stale_mem:
            return None

        # 1. Update stale memory
        group_id = stale_mem.contradiction_group_id or f"cg_{uuid.uuid4().hex[:8]}"
        stale_mem.verification_state = VerificationState.CONTRADICTED
        stale_mem.contradiction_group_id = group_id
        stale_mem.metadata["contradicted_by"] = new_memory.memory_id
        stale_mem.metadata["conflict_reason"] = conflict_reason
        stale_mem.updated_at = time.time()
        postgres_memory_store.save_memory(stale_mem)

        # 2. Update new memory
        new_memory.supersedes_memory_id = stale_memory_id
        new_memory.contradiction_group_id = group_id
        new_memory.verification_state = VerificationState.VERIFIED
        new_memory.updated_at = time.time()
        postgres_memory_store.save_memory(new_memory)

        return stale_mem


# Global singleton instance
memory_contradiction_engine = MemoryContradictionEngine()
