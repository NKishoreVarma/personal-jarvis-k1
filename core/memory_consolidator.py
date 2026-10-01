"""
Memory Consolidator for MARK XLVIII / JARVIS.
Merges compatible partial memories for a project or workflow into unified, high-density profiles
to prevent memory database fragmentation.
"""

from __future__ import annotations

import time
import uuid
from typing import List, Optional

from core.memory_contract import MemoryContract, MemoryType, VerificationState
from core.memory_service import memory_service


class MemoryConsolidator:
    """
    Consolidates multiple fragmented memories into unified records.
    """

    def consolidate_project_memories(self, project_name: str) -> Optional[MemoryContract]:
        """
        Gathers all facts and context memories for a project and merges them into a single profile.
        """
        memories = memory_service.retrieve(project_scope=project_name, min_confidence=0.3)
        if len(memories) < 2:
            return memories[0] if memories else None

        facts: List[str] = []
        highest_conf = 0.0
        all_tags = set()

        for m in memories:
            facts.append(m.content)
            highest_conf = max(highest_conf, m.confidence)
            all_tags.update(m.tags)

        # Merge into consolidated profile
        consolidated_content = f"{project_name} Profile: " + " | ".join(facts)
        consolidated_mem = MemoryContract(
            memory_id=f"mem_cons_{uuid.uuid4().hex[:8]}",
            memory_type=MemoryType.PROJECT_CONTEXT,
            subject=f"Consolidated profile for {project_name}",
            content=consolidated_content,
            confidence=highest_conf,
            importance=0.9,
            verification_state=VerificationState.CONFIRMED,
            project_scope=project_name,
            tags=list(all_tags) + ["consolidated"],
        )

        # Invalidate old fragmented items and store new consolidated memory
        for m in memories:
            memory_service.invalidate(m.memory_id)

        memory_service.store(consolidated_mem)
        print(f"[MEMORY_CONSOLIDATOR] 📦 Consolidated {len(memories)} memories for '{project_name}'.")
        return consolidated_mem


# Global singleton instance
memory_consolidator = MemoryConsolidator()
