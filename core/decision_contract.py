"""
Decision Contract for System 1 Decision Engine (Laya Integration) in MARK XLVIII / JARVIS.
Defines strongly typed decision outputs, confidence ratings, and provenance attributes for choice, score, and noul workflows.
Enforces rule: System 1 produces a decision signal, NOT execution authority.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DecisionType(str, Enum):
    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


class DecisionCategory(str, Enum):
    INTENT = "intent"
    AGENT_ROUTING = "agent_routing"
    SKILL_SELECTION = "skill_selection"
    STRATEGY_SELECTION = "strategy_selection"
    URGENCY = "urgency"
    RISK = "risk"
    PROACTIVE = "proactive"
    TEMPORAL = "temporal"
    RESEARCH = "research"
    MEMORY = "memory"


class DecisionSource(str, Enum):
    REAL_LAYA = "real_laya"
    LAYA_SIMULATOR = "laya_simulator"
    FALLBACK_HEURISTIC = "fallback_heuristic"
    SYSTEM2_ESCALATION = "system2_escalation"
    LAYA = "laya"  # Backward compatibility alias


class ModelLifecycleState(str, Enum):
    COLD = "COLD"
    WARMING = "WARMING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNLOADING = "UNLOADING"


def compute_context_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


@dataclass
class DecisionResult:
    decision_id: str
    decision_type: DecisionType
    category: DecisionCategory
    input_context_hash: str
    selected_option: Optional[str] = None
    score: Optional[float] = None
    confidence: float = 0.0
    abstained: bool = False
    model_or_checkpoint: str = "laya"
    language: str = "en"
    latency_ms: float = 0.0
    evidence: List[str] = field(default_factory=list)
    alternatives: Dict[str, float] = field(default_factory=dict)
    reason_code: str = "DEFAULT"
    source: DecisionSource = DecisionSource.LAYA
    created_at: float = field(default_factory=time.time)
    trace_id: str = field(default_factory=lambda: f"tr_{uuid.uuid4().hex[:8]}")
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def decision_source(self) -> str:
        return self.source.value if hasattr(self.source, "value") else str(self.source)

    @property
    def model_checkpoint(self) -> str:
        return self.model_or_checkpoint

    @property
    def simulated(self) -> bool:
        if self.source in (DecisionSource.LAYA_SIMULATOR, DecisionSource.FALLBACK_HEURISTIC):
            return True
        if "is_real" in self.metadata:
            return not bool(self.metadata["is_real"])
        return self.source != DecisionSource.REAL_LAYA

    @property
    def inference_latency_ms(self) -> float:
        return self.latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "category": self.category.value,
            "input_context_hash": self.input_context_hash,
            "selected_option": self.selected_option,
            "score": round(self.score, 4) if self.score is not None else None,
            "confidence": round(self.confidence, 4),
            "abstained": self.abstained,
            "model_or_checkpoint": self.model_or_checkpoint,
            "model_checkpoint": self.model_checkpoint,
            "language": self.language,
            "latency_ms": round(self.latency_ms, 3),
            "inference_latency_ms": round(self.inference_latency_ms, 3),
            "evidence": self.evidence,
            "alternatives": {k: round(v, 4) for k, v in self.alternatives.items()},
            "reason_code": self.reason_code,
            "source": self.source.value,
            "decision_source": self.decision_source,
            "simulated": self.simulated,
            "created_at": self.created_at,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }


def create_decision_result(
    decision_type: DecisionType,
    category: DecisionCategory,
    context: str,
    selected_option: Optional[str] = None,
    score: Optional[float] = None,
    confidence: float = 0.85,
    abstained: bool = False,
    model_or_checkpoint: str = "laya",
    language: str = "en",
    latency_ms: float = 0.0,
    evidence: Optional[List[str]] = None,
    alternatives: Optional[Dict[str, float]] = None,
    reason_code: str = "SUCCESS",
    source: DecisionSource = DecisionSource.LAYA,
    trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[DecisionResult], str]:
    if not isinstance(decision_type, DecisionType):
        return None, "Validation error: Invalid DecisionType."

    if not isinstance(category, DecisionCategory):
        return None, "Validation error: Invalid DecisionCategory."

    clamped_confidence = max(0.0, min(1.0, confidence))
    clamped_score = max(0.0, min(1.0, score)) if score is not None else None

    # For score decision type, score must be provided unless abstained
    if decision_type == DecisionType.SCORE and clamped_score is None and not abstained:
        return None, "Validation error: Score decision requires numeric score value."

    # For choice decision type, selected_option must be provided unless abstained
    if decision_type == DecisionType.CHOICE and selected_option is None and not abstained:
        return None, "Validation error: Choice decision requires selected_option."

    res = DecisionResult(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        decision_type=decision_type,
        category=category,
        input_context_hash=compute_context_hash(context),
        selected_option=selected_option,
        score=clamped_score,
        confidence=clamped_confidence,
        abstained=abstained,
        model_or_checkpoint=model_or_checkpoint,
        language=language,
        latency_ms=latency_ms,
        evidence=evidence or [],
        alternatives=alternatives or {},
        reason_code=reason_code,
        source=source,
        trace_id=trace_id or f"tr_{uuid.uuid4().hex[:8]}",
        metadata=metadata or {},
    )
    return res, "DecisionResult created successfully."
