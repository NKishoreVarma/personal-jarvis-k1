"""
Memory Quality Gate for Persistent Memory in MARK XLVIII / JARVIS.
Screens prospective memories before durable persistence to reject temporary noise,
sensitive credentials, unverified claims, duplicates, or contradicted facts.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from core.memory_contract import MemoryContract, MemoryType, VerificationState, contains_sensitive_data


class MemoryRejectionReason(str, Enum):
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    TEMPORARY = "TEMPORARY"
    DUPLICATE = "DUPLICATE"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    NO_DURABLE_VALUE = "NO_DURABLE_VALUE"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_PROVENANCE = "INSUFFICIENT_PROVENANCE"


class MemoryQualityGate:
    """
    Validates quality, privacy, and durability before long-term memory insertion.
    """

    def validate_memory_for_storage(self, memory: MemoryContract) -> Tuple[bool, Optional[MemoryRejectionReason], str]:
        """
        Determines whether memory contract meets persistent quality standards.
        """
        # 1. Reject temporary context
        if memory.memory_type == MemoryType.TEMPORARY_CONTEXT:
            return False, MemoryRejectionReason.TEMPORARY, "Temporary context cannot enter durable long-term memory."

        # 2. Reject sensitive data
        if contains_sensitive_data(memory.subject) or contains_sensitive_data(memory.content):
            return False, MemoryRejectionReason.SENSITIVE_DATA, "Memory contains raw credentials or sensitive tokens."

        # 3. Reject low confidence
        if memory.confidence < 0.60:
            return False, MemoryRejectionReason.LOW_CONFIDENCE, f"Confidence too low ({memory.confidence:.2f} < 0.60)."

        # 4. Reject contradicted memories
        if memory.verification_state == VerificationState.CONTRADICTED:
            return False, MemoryRejectionReason.CONTRADICTED, "Memory is contradicted by verified observations."

        # 5. Reject empty content
        if not memory.subject.strip() or not memory.content.strip():
            return False, MemoryRejectionReason.NO_DURABLE_VALUE, "Empty memory content has no durable value."

        return True, None, "Memory passed quality gate."


# Global singleton instance
memory_quality_gate = MemoryQualityGate()
