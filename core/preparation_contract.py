"""
Safe Preparation Contract for Predictive Execution in MARK XLVIII / JARVIS.
Enforces strict side-effect-free validation for all background prefetching and preparation tasks.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class PreparationRisk(str, Enum):
    READ_ONLY = "READ_ONLY"
    SIDE_EFFECT_FREE = "SIDE_EFFECT_FREE"
    PROHIBITED_MUTATING = "PROHIBITED_MUTATING"


@dataclass
class PreparationContract:
    preparation_id: str
    turn_id: str
    operation: str
    arguments: Dict[str, Any]
    risk_level: PreparationRisk = PreparationRisk.READ_ONLY
    reversible: bool = True
    side_effect_free: bool = True
    confidence: float = 0.8
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = field(default_factory=lambda: time.monotonic() + 10.0)
    result: Optional[Dict[str, Any]] = None
    is_valid: bool = True

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at

    def can_execute_predictively(self) -> bool:
        """Only side_effect_free and read_only operations are allowed to run before finalization."""
        return self.side_effect_free and self.risk_level in (
            PreparationRisk.READ_ONLY,
            PreparationRisk.SIDE_EFFECT_FREE,
        )


def create_preparation_contract(
    turn_id: str,
    operation: str,
    arguments: Dict[str, Any],
    confidence: float = 0.8,
    ttl_sec: float = 10.0,
    side_effect_free: bool = True,
) -> PreparationContract:
    return PreparationContract(
        preparation_id=f"prep_{uuid.uuid4().hex[:8]}",
        turn_id=turn_id,
        operation=operation,
        arguments=arguments,
        confidence=confidence,
        side_effect_free=side_effect_free,
        risk_level=PreparationRisk.READ_ONLY if side_effect_free else PreparationRisk.PROHIBITED_MUTATING,
        expires_at=time.monotonic() + ttl_sec,
    )
