"""
Concept Drift Detector and Conservative Degradation Engine for System 1 Decision Routing in MARK XLVIII / JARVIS.
Detects performance decay, confidence divergence, and disagreement spikes over time.
Enforces rule: When quality degrades, become MORE conservative (escalate to System 2), never relax thresholds.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.decision_contract import DecisionCategory
from core.decision_outcome import (
    DecisionOutcomeRecord,
    OutcomeQuality,
    decision_outcome_store,
)

logger = logging.getLogger(__name__)


class DriftState(str, Enum):
    STABLE = "STABLE"
    WARNING = "WARNING"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    DEGRADED = "DEGRADED"


@dataclass
class DriftAssessment:
    state: DriftState
    category: Optional[str]
    recent_sample_count: int
    recent_accuracy: Optional[float]
    baseline_accuracy: Optional[float]
    accuracy_delta: Optional[float]
    recent_ece: Optional[float]
    recent_disagreement_rate: float
    recent_fallback_rate: float
    threshold_penalty: float
    force_system2: bool
    halt_adaptations: bool
    rationale: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "category": self.category,
            "recent_sample_count": self.recent_sample_count,
            "recent_accuracy": round(self.recent_accuracy, 4) if self.recent_accuracy is not None else None,
            "baseline_accuracy": round(self.baseline_accuracy, 4) if self.baseline_accuracy is not None else None,
            "accuracy_delta": round(self.accuracy_delta, 4) if self.accuracy_delta is not None else None,
            "recent_ece": round(self.recent_ece, 4) if self.recent_ece is not None else None,
            "recent_disagreement_rate": round(self.recent_disagreement_rate, 4),
            "recent_fallback_rate": round(self.recent_fallback_rate, 4),
            "threshold_penalty": round(self.threshold_penalty, 4),
            "force_system2": self.force_system2,
            "halt_adaptations": self.halt_adaptations,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


class DecisionDriftDetector:
    """
    Monitors recent decision outcomes against established baseline to detect concept drift.
    Triggers conservative degradation and controls gradual recovery.
    """

    def __init__(
        self,
        recent_window_size: int = 15,
        min_samples_for_drift: int = 8,
        warning_accuracy_drop: float = 0.12,
        drift_accuracy_drop: float = 0.22,
        degraded_accuracy_threshold: float = 0.65,
        consecutive_recovery_required: int = 5,
    ):
        self.recent_window_size = recent_window_size
        self.min_samples_for_drift = min_samples_for_drift
        self.warning_accuracy_drop = warning_accuracy_drop
        self.drift_accuracy_drop = drift_accuracy_drop
        self.degraded_accuracy_threshold = degraded_accuracy_threshold
        self.consecutive_recovery_required = consecutive_recovery_required

        # Per-route state tracking
        self._route_states: Dict[str, DriftState] = {}
        self._recovery_counters: Dict[str, int] = {}
        self._baseline_accuracies: Dict[str, float] = {}

    def set_baseline_accuracy(self, category_key: str, accuracy: float) -> None:
        self._baseline_accuracies[category_key] = max(0.0, min(1.0, accuracy))

    def get_state(self, category: Optional[DecisionCategory] = None) -> DriftState:
        cat_key = category.value if category and hasattr(category, "value") else (str(category) if category else "GLOBAL")
        return self._route_states.get(cat_key, DriftState.STABLE)

    def assess_route(
        self,
        category: Optional[DecisionCategory] = None,
    ) -> DriftAssessment:
        """
        Assesses drift by comparing recent window of verified outcomes to baseline.
        """
        cat_key = category.value if category and hasattr(category, "value") else (str(category) if category else "GLOBAL")
        records = decision_outcome_store.query_records(route=category, limit=self.recent_window_size * 3)

        verified_records = [r for r in records if r.outcome_verified and r.is_correct() is not None]
        recent_records = verified_records[: self.recent_window_size]

        sample_count = len(recent_records)
        current_state = self._route_states.get(cat_key, DriftState.STABLE)

        if sample_count < self.min_samples_for_drift:
            # Insufficient recent samples to establish drift
            return DriftAssessment(
                state=current_state,
                category=cat_key,
                recent_sample_count=sample_count,
                recent_accuracy=None,
                baseline_accuracy=self._baseline_accuracies.get(cat_key, 0.85),
                accuracy_delta=None,
                recent_ece=None,
                recent_disagreement_rate=0.0,
                recent_fallback_rate=0.0,
                threshold_penalty=0.10 if current_state in [DriftState.DRIFT_DETECTED, DriftState.DEGRADED] else 0.0,
                force_system2=current_state == DriftState.DEGRADED,
                halt_adaptations=current_state in [DriftState.DRIFT_DETECTED, DriftState.DEGRADED],
                rationale="Insufficient recent verified samples to assess drift; maintaining current state.",
            )

        # Compute recent accuracy
        correct_count = sum(1.0 if r.is_correct() is True else (0.5 if r.is_correct() == 0.5 else 0.0) for r in recent_records)
        recent_acc = correct_count / sample_count

        # Historical baseline accuracy (default 0.85 if none established)
        baseline_acc = self._baseline_accuracies.get(cat_key, 0.85)
        accuracy_delta = baseline_acc - recent_acc

        # Rates
        disagreements = sum(1 for r in recent_records if r.predicted_option != r.final_decision)
        fallbacks = sum(1 for r in recent_records if r.fallback_used or r.abstained)
        recent_disagree_rate = disagreements / sample_count
        recent_fallback_rate = fallbacks / sample_count

        # Evaluate transitions
        new_state = current_state
        recovery_count = self._recovery_counters.get(cat_key, 0)
        rationale = "Behavior within normal baseline parameters."

        if recent_acc < self.degraded_accuracy_threshold:
            new_state = DriftState.DEGRADED
            recovery_count = 0
            rationale = f"Recent accuracy ({recent_acc:.2f}) dropped below critical threshold ({self.degraded_accuracy_threshold:.2f})."
        elif accuracy_delta >= self.drift_accuracy_drop or recent_disagree_rate >= 0.40:
            new_state = DriftState.DRIFT_DETECTED
            recovery_count = 0
            rationale = f"Significant accuracy drop ({accuracy_delta:.2f}) or high disagreement ({recent_disagree_rate:.2f}) detected."
        elif accuracy_delta >= self.warning_accuracy_drop or recent_disagree_rate >= 0.25:
            if current_state not in [DriftState.DRIFT_DETECTED, DriftState.DEGRADED]:
                new_state = DriftState.WARNING
                rationale = f"Moderate accuracy drop ({accuracy_delta:.2f}) observed in recent window."
        else:
            # Recovery progression based on consecutive healthy samples
            consecutive_healthy = 0
            for r in recent_records:
                if r.is_correct() is True:
                    consecutive_healthy += 1
                else:
                    break

            if current_state in [DriftState.DEGRADED, DriftState.DRIFT_DETECTED, DriftState.WARNING]:
                recovery_count = max(recovery_count + 1, consecutive_healthy)
                if current_state == DriftState.DEGRADED:
                    if recovery_count >= self.consecutive_recovery_required:
                        new_state = DriftState.WARNING
                        recovery_count = 0
                        rationale = f"Partial recovery: {self.consecutive_recovery_required} consecutive healthy samples achieved. Transitioned to WARNING."
                    else:
                        rationale = f"Recovery in progress: {recovery_count}/{self.consecutive_recovery_required} healthy samples."
                elif current_state in [DriftState.DRIFT_DETECTED, DriftState.WARNING]:
                    if recovery_count >= self.consecutive_recovery_required:
                        new_state = DriftState.STABLE
                        recovery_count = 0
                        rationale = f"Full recovery: {self.consecutive_recovery_required} healthy samples achieved. Restored to STABLE."
                    else:
                        rationale = f"Recovery in progress: {recovery_count}/{self.consecutive_recovery_required} healthy samples."
            else:
                new_state = DriftState.STABLE
                recovery_count = 0

        self._route_states[cat_key] = new_state
        self._recovery_counters[cat_key] = recovery_count

        # Conservative actions based on state
        threshold_penalty = 0.0
        force_system2 = False
        halt_adaptations = False

        if new_state == DriftState.DEGRADED:
            threshold_penalty = 0.15
            force_system2 = True
            halt_adaptations = True
        elif new_state == DriftState.DRIFT_DETECTED:
            threshold_penalty = 0.10
            force_system2 = False
            halt_adaptations = True
        elif new_state == DriftState.WARNING:
            threshold_penalty = 0.05
            force_system2 = False
            halt_adaptations = False

        return DriftAssessment(
            state=new_state,
            category=cat_key,
            recent_sample_count=sample_count,
            recent_accuracy=recent_acc,
            baseline_accuracy=baseline_acc,
            accuracy_delta=accuracy_delta,
            recent_ece=None,
            recent_disagreement_rate=recent_disagree_rate,
            recent_fallback_rate=recent_fallback_rate,
            threshold_penalty=threshold_penalty,
            force_system2=force_system2,
            halt_adaptations=halt_adaptations,
            rationale=rationale,
        )

    def reset(self) -> None:
        self._route_states.clear()
        self._recovery_counters.clear()
        self._baseline_accuracies.clear()


# Global singleton instance
decision_drift_detector = DecisionDriftDetector()
