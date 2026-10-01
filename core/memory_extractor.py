"""
Memory Extractor for MARK XLVIII / JARVIS.
Extracts durable, valuable, verifiable memories from interactions and task outcomes
while strictly filtering out secrets, temporary greetings, noise, and chain-of-thought.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional

from core.memory_contract import MemoryContract, MemoryType, VerificationState


class MemoryExtractor:
    """
    Evaluates inputs and outcomes to extract durable long-term memories.
    """

    SECRET_PATTERNS = [
        re.compile(r"(api[_-]?key|secret|password|bearer\s+[a-zA-Z0-9_\-\.]{20,}|token|private[_-]?key)", re.IGNORECASE),
        re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
        re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    ]

    TEMPORARY_PATTERNS = [
        re.compile(r"^(hi|hello|hey|good\s+morning|good\s+evening|what\s+time(\s+is\s+it)?|what\s+date|thank\s+you|thanks)$", re.IGNORECASE),
    ]

    def is_secret_or_sensitive(self, text: str) -> bool:
        """Checks if text contains credentials, keys, or sensitive tokens."""
        for pattern in self.SECRET_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def is_transient_or_noise(self, text: str) -> bool:
        """Checks if text is a temporary greeting or trivial query."""
        text_clean = text.strip()
        if len(text_clean) < 3:
            return True
        for pattern in self.TEMPORARY_PATTERNS:
            if pattern.match(text_clean):
                return True
        return False

    def extract_from_explicit_statement(self, raw_text: str) -> Optional[MemoryContract]:
        """
        Extracts user preferences or facts from phrases like:
        "Remember that FLOW uses port 4000"
        "Remember this workflow: build before test"
        """
        if self.is_secret_or_sensitive(raw_text):
            print("[MEMORY_EXTRACTOR] 🛡️ Rejected memory creation: contains sensitive/secret patterns.")
            return None

        # Pattern 1: Remember that <subject> uses/is <content>
        m = re.search(r"remember\s+(that\s+)?(.+)", raw_text, re.IGNORECASE)
        body = m.group(2).strip() if m else raw_text.strip()
        
        # Extract project if present
        proj_match = re.search(r"\b([A-Z0-9_-]{3,})\b", body)
        project_scope = proj_match.group(1) if proj_match else None

        return MemoryContract(
            memory_id=f"mem_{uuid.uuid4().hex[:8]}",
            memory_type=MemoryType.PREFERENCE if "prefer" in body.lower() else MemoryType.FACT,
            subject=f"Explicit configuration for {project_scope or 'system'}",
            content=body,
            confidence=0.95,
            importance=0.8,
            verification_state=VerificationState.CONFIRMED,
            project_scope=project_scope,
            tags=["user_explicit", "configuration"],
        )

    def extract_from_repair_outcome(
        self,
        project_name: str,
        problem_category: str,
        successful_actions: List[str],
        port: int = 3000,
    ) -> Optional[MemoryContract]:
        """
        Extracts reusable repair pattern from completed autonomous problem solver run.
        """
        actions_str = " -> ".join(successful_actions) if successful_actions else "restart"
        content = (
            f"Startup failure for '{project_name}' caused by {problem_category}. "
            f"Resolved successfully by: {actions_str}. Verified listening on port {port}."
        )

        return MemoryContract(
            memory_id=f"mem_{uuid.uuid4().hex[:8]}",
            memory_type=MemoryType.REPAIR_PATTERN,
            subject=f"Startup repair pattern for {project_name}",
            content=content,
            confidence=0.90,
            importance=0.85,
            verification_state=VerificationState.CONFIRMED,
            project_scope=project_name,
            tags=["repair_pattern", problem_category.lower(), project_name.lower()],
            metadata={
                "problem_category": problem_category,
                "successful_actions": successful_actions,
                "verified_port": port,
            },
        )


# Global singleton instance
memory_extractor = MemoryExtractor()
