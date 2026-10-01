"""
Learning Feedback Engine for MARK XLVIII / JARVIS.
Translates OutcomeEvaluation and RegressionState into bounded, calibrated confidence adjustments.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.outcome_evaluator import OutcomeEvaluation, OutcomeGrade
from core.regression_detector import RegressionState, regression_detector


@dataclass
class FeedbackSignal:
    signal_id: str
    capability_id: str
    confidence_delta: float  # bounded between -0.40 and +0.15
    ranking_modifier: float  # bounded between -2.0 and +1.0
    rationale: str
    requires_degradation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "capability_id": self.capability_id,
            "confidence_delta": round(self.confidence_delta, 3),
            "ranking_modifier": round(self.ranking_modifier, 3),
            "rationale": self.rationale,
            "requires_degradation": self.requires_degradation,
        }


class LearningFeedbackEngine:
    """
    Computes bounded feedback signals from verified evaluations.
    """

    def generate_feedback_signal(
        self,
        capability_id: str,
        evaluation: OutcomeEvaluation,
    ) -> FeedbackSignal:
        """
        Computes feedback deltas based on success, efficiency, and regression signals.
        """
        reg_state, reg_reason = regression_detector.detect_regression(capability_id)

        if reg_state in [RegressionState.DEGRADED, RegressionState.CRITICAL]:
            delta = -0.30
            ranking_mod = -1.5
            rationale = f"Severe regression detected: {reg_reason}"
            requires_deg = True

        elif not evaluation.success or evaluation.grade == OutcomeGrade.FAILED:
            delta = -0.20
            ranking_mod = -0.8
            rationale = "Execution failed verification."
            requires_deg = False

        elif evaluation.was_cancelled:
            delta = -0.05
            ranking_mod = -0.2
            rationale = "Execution was cancelled by user."
            requires_deg = False

        elif evaluation.grade in [OutcomeGrade.INEFFICIENT, OutcomeGrade.FRAGILE]:
            delta = +0.02
            ranking_mod = -0.1
            rationale = "Task succeeded but required retries/repairs."
            requires_deg = False

        else:
            # Clean optimal or acceptable success
            delta = min(0.10, 0.05 * evaluation.quality_score)
            ranking_mod = min(0.5, 0.3 * evaluation.quality_score)
            rationale = f"Verified optimal outcome (quality={evaluation.quality_score:.2f})."
            requires_deg = False

        return FeedbackSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:6]}",
            capability_id=capability_id,
            confidence_delta=delta,
            ranking_modifier=ranking_mod,
            rationale=rationale,
            requires_degradation=requires_deg,
        )


# Global singleton instance
learning_feedback_engine = LearningFeedbackEngine()
