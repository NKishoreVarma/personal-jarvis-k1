"""
Experience Memory for MARK XLVIII / JARVIS.
Stores structured task lessons, successful/failed action sequences, and reuse counts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExperienceRecord:
    experience_id: str
    goal_type: str
    context_signature: str
    problem_pattern: str
    observations: List[str] = field(default_factory=list)
    successful_strategy: List[str] = field(default_factory=list)
    failed_strategies: List[str] = field(default_factory=list)
    verification_result: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.85
    reuse_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def increment_reuse(self) -> None:
        self.reuse_count += 1
        self.confidence = min(1.0, self.confidence + 0.05)
        self.updated_at = time.time()


class ExperienceMemoryStore:
    """
    In-memory registry of structured problem-solving experience records.
    """

    def __init__(self):
        self._records: Dict[str, ExperienceRecord] = {}

    def record_experience(
        self,
        goal_type: str,
        context_signature: str,
        problem_pattern: str,
        successful_strategy: List[str],
        failed_strategies: Optional[List[str]] = None,
        observations: Optional[List[str]] = None,
        verification_result: Optional[Dict[str, Any]] = None,
    ) -> ExperienceRecord:
        """
        Creates or updates a structured experience record.
        """
        # Look for existing matching record to update
        for rec in self._records.values():
            if (
                rec.goal_type == goal_type
                and rec.context_signature.lower() == context_signature.lower()
                and rec.problem_pattern.lower() == problem_pattern.lower()
            ):
                rec.successful_strategy = successful_strategy
                if failed_strategies:
                    rec.failed_strategies.extend([f for f in failed_strategies if f not in rec.failed_strategies])
                rec.increment_reuse()
                return rec

        rec_id = f"exp_{uuid.uuid4().hex[:8]}"
        record = ExperienceRecord(
            experience_id=rec_id,
            goal_type=goal_type,
            context_signature=context_signature,
            problem_pattern=problem_pattern,
            observations=observations or [],
            successful_strategy=successful_strategy,
            failed_strategies=failed_strategies or [],
            verification_result=verification_result or {},
        )
        self._records[rec_id] = record
        return record

    def find_experience(
        self,
        context_signature: str,
        problem_pattern: Optional[str] = None,
    ) -> Optional[ExperienceRecord]:
        """
        Retrieves the most confident experience record matching context signature.
        """
        matches: List[ExperienceRecord] = []
        sig_norm = context_signature.strip().lower()

        for rec in self._records.values():
            if sig_norm in rec.context_signature.lower() or rec.context_signature.lower() in sig_norm:
                if problem_pattern and rec.problem_pattern.lower() != problem_pattern.lower():
                    continue
                matches.append(rec)

        if not matches:
            return None

        # Sort by confidence descending, then reuse_count
        matches.sort(key=lambda r: (r.confidence, r.reuse_count), reverse=True)
        return matches[0]

    def clear(self) -> None:
        self._records.clear()


# Global singleton instance
experience_memory = ExperienceMemoryStore()
