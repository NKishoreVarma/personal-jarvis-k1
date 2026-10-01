"""
Capability Performance Tracker for MARK XLVIII / JARVIS.
Maintains historical reliability metrics, average runtimes, retry rates, and regression scores
for skills, workflows, and planning strategies.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.outcome_evaluator import OutcomeEvaluation


class CapabilityType(str, Enum):
    SKILL = "SKILL"
    WORKFLOW = "WORKFLOW"
    STRATEGY = "STRATEGY"
    PLAN = "PLAN"


@dataclass
class CapabilityPerformance:
    capability_id: str
    capability_type: CapabilityType
    success_count: int = 0
    failure_count: int = 0
    total_executions: int = 0
    average_duration: float = 0.0
    retry_rate: float = 0.0
    verification_rate: float = 1.0
    regression_score: float = 0.0  # 0.0 = clean, > 0.5 = degraded
    last_verified_success: float = 0.0
    confidence: float = 0.90
    history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 1.0
        return self.success_count / self.total_executions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "capability_type": self.capability_type.value,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_executions": self.total_executions,
            "success_rate": round(self.success_rate, 3),
            "average_duration": round(self.average_duration, 3),
            "retry_rate": round(self.retry_rate, 3),
            "verification_rate": round(self.verification_rate, 3),
            "regression_score": round(self.regression_score, 3),
            "last_verified_success": self.last_verified_success,
            "confidence": round(self.confidence, 3),
        }


class CapabilityPerformanceTracker:
    """
    Stores and updates performance statistics for all system capabilities.
    """

    def __init__(self):
        self._capabilities: Dict[str, CapabilityPerformance] = {}

    def get_or_create(self, capability_id: str, capability_type: CapabilityType = CapabilityType.STRATEGY) -> CapabilityPerformance:
        if capability_id not in self._capabilities:
            self._capabilities[capability_id] = CapabilityPerformance(
                capability_id=capability_id,
                capability_type=capability_type,
            )
        return self._capabilities[capability_id]

    def record_performance(
        self,
        capability_id: str,
        evaluation: OutcomeEvaluation,
        capability_type: CapabilityType = CapabilityType.STRATEGY,
    ) -> CapabilityPerformance:
        """
        Updates running averages and metrics from an OutcomeEvaluation.
        """
        perf = self.get_or_create(capability_id, capability_type)
        perf.total_executions += 1

        if evaluation.success:
            perf.success_count += 1
            perf.last_verified_success = time.time()
            perf.confidence = min(1.0, perf.confidence + 0.05 * evaluation.quality_score)
            perf.regression_score = max(0.0, perf.regression_score - 0.1)
        else:
            perf.failure_count += 1
            perf.confidence = max(0.1, perf.confidence - 0.20)
            perf.regression_score = min(1.0, perf.regression_score + 0.3)

        # Update running averages
        n = perf.total_executions
        perf.average_duration = ((perf.average_duration * (n - 1)) + evaluation.duration_s) / n
        perf.retry_rate = ((perf.retry_rate * (n - 1)) + min(1.0, evaluation.retry_count)) / n
        perf.verification_rate = ((perf.verification_rate * (n - 1)) + evaluation.verification_strength) / n

        # Keep recent history bounded to 20 records
        perf.history.append(evaluation.to_dict())
        if len(perf.history) > 20:
            perf.history.pop(0)

        return perf

    def get_performance(self, capability_id: str) -> Optional[CapabilityPerformance]:
        return self._capabilities.get(capability_id)

    def list_all(self) -> List[CapabilityPerformance]:
        return list(self._capabilities.values())

    def reset_capability(self, capability_id: str) -> None:
        self._capabilities.pop(capability_id, None)

    def clear_all(self) -> None:
        self._capabilities.clear()


# Global singleton instance
capability_performance_tracker = CapabilityPerformanceTracker()
