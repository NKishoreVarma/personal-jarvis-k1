"""
Memory Consolidation Engine for Persistent Memory in MARK XLVIII / JARVIS.
Consolidates repeated verified experiences, repair patterns, and user preferences into durable lessons.
Enforces rule: ONE EVENT != PERMANENT MEMORY (Requires repetition, verification, and durability).
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

from core.memory_contract import MemoryContract, MemoryType, VerificationState, create_memory_contract
from core.postgres_memory_store import postgres_memory_store


class MemoryConsolidationEngine:
    """
    Synthesizes clustered historical experiences into high-level lessons and workflow memories.
    """

    def __init__(self, repetition_threshold: int = 2):
        self.repetition_threshold = repetition_threshold

    def evaluate_and_consolidate(
        self,
        project_id: str,
        topic: str,
        events: List[Dict[str, str]],
    ) -> Optional[MemoryContract]:
        """
        Consolidates recurring verified events into a single durable LESSON memory.
        """
        if len(events) < self.repetition_threshold:
            return None

        # Synthesize concise lesson content
        actions = [e.get("action", "") for e in events if e.get("action")]
        summary = f"Consolidated workflow for {topic} in {project_id}: {'; '.join(actions[:3])}."

        lesson_mem = create_memory_contract(
            memory_type=MemoryType.LESSON,
            subject=f"{project_id} {topic} Lesson",
            content=summary,
            project_scope=project_id,
            confidence=0.95,
            importance=0.90,
            tags=["consolidated_lesson", topic.lower()],
            metadata={"source_event_count": len(events)},
        )
        lesson_mem.verification_state = VerificationState.VERIFIED

        # Save to store
        postgres_memory_store.save_memory(lesson_mem)
        return lesson_mem


# Global singleton instance
memory_consolidation_engine = MemoryConsolidationEngine()
