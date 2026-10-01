"""
Memory Decay Manager for MARK XLVIII / JARVIS.
Applies continuous confidence and freshness decay tailored to memory categories:
- Stable Project Facts / Profiles: Slow decay.
- Repair Patterns / Experiences: Medium decay.
- Temporary Port / Ephemeral State: Fast decay.
Automatically marks expired or sub-threshold memories as EXPIRED.
"""

from __future__ import annotations

import math
import time
from typing import Dict

from core.memory_contract import MemoryContract, MemoryType, VerificationState
from core.memory_service import memory_service


class MemoryDecayManager:
    """
    Manages temporal confidence decay and expiration for all persistent memories.
    """

    # Half-life in days per memory type
    HALF_LIVES_DAYS: Dict[MemoryType, float] = {
        MemoryType.FACT: 90.0,
        MemoryType.PROJECT_CONTEXT: 90.0,
        MemoryType.PREFERENCE: 180.0,
        MemoryType.WORKFLOW: 60.0,
        MemoryType.EXPERIENCE: 30.0,
        MemoryType.REPAIR_PATTERN: 30.0,
        MemoryType.FAILURE_PATTERN: 14.0,
        MemoryType.ENTITY_RELATION: 60.0,
        MemoryType.TASK_OUTCOME: 7.0,
    }

    MIN_ACTIVE_CONFIDENCE = 0.15

    def apply_decay(self) -> int:
        """
        Calculates and applies decay across all stored memories.
        Returns count of memories expired or invalidated.
        """
        now = time.time()
        expired_count = 0

        for mem_id, mem in list(memory_service._memories.items()):
            # 1. Check explicit expiration timestamp
            if mem.is_expired():
                mem.verification_state = VerificationState.EXPIRED
                memory_service.invalidate(mem_id)
                expired_count += 1
                continue

            # 2. Calculate category-specific temporal decay
            half_life_sec = self.HALF_LIVES_DAYS.get(mem.memory_type, 30.0) * 86400.0
            elapsed_sec = max(0.0, now - mem.updated_at)
            decay_factor = math.pow(0.5, elapsed_sec / half_life_sec)

            # Apply decay to freshness and confidence
            mem.freshness = max(0.05, mem.freshness * decay_factor)
            
            # Confirmed memories retain minimum baseline confidence
            baseline = 0.4 if mem.verification_state == VerificationState.CONFIRMED else 0.1
            mem.confidence = max(baseline, mem.confidence * decay_factor)

            if mem.confidence < self.MIN_ACTIVE_CONFIDENCE:
                mem.verification_state = VerificationState.EXPIRED
                memory_service.invalidate(mem_id)
                expired_count += 1

        memory_service._persist_to_disk()
        return expired_count


# Global singleton instance
memory_decay_manager = MemoryDecayManager()
