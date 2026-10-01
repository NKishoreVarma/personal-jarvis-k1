"""
Learning Quality Gate for MARK XLVIII / JARVIS.
Screens execution outcomes and rejects noisy, unverified, speculative, or stale data
before it enters long-term capability optimization.
Enforces invariant: QUALITY > QUANTITY (Only verified, high-quality evidence is learned).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.outcome_evaluator import OutcomeEvaluation, OutcomeGrade


class LearningQualityGate:
    """
    Validates the admissibility of OutcomeEvaluation records for persistent continuous learning.
    """

    def validate_evaluation(self, evaluation: OutcomeEvaluation) -> Tuple[bool, str]:
        """
        Determines if an outcome evaluation meets strict learning quality standards.
        """
        # 1. Reject unverified success
        if evaluation.success and evaluation.verification_strength < 0.60:
            return False, f"Verification strength too low ({evaluation.verification_strength:.2f} < 0.60)."

        # 2. Reject ambiguous cancellation without outcome data
        if evaluation.was_cancelled and evaluation.duration_s < 0.5:
            return False, "Instant cancellation provides insufficient operational evidence."

        # 3. Reject zero-cost / zero-duration synthetic anomalies
        if evaluation.duration_s < 0.001 and not evaluation.was_cancelled:
            return False, "Unrealistic duration anomaly (< 1ms)."

        # 4. Validated
        return True, "Outcome evaluation passed quality gate."


# Global singleton instance
learning_quality_gate = LearningQualityGate()
