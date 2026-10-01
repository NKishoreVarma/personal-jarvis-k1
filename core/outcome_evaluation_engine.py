"""
Outcome Evaluation Engine for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Evaluates execution results, measures verification strength, and identifies failure signatures.
Enforces rule: ACTION_COMPLETED != OUTCOME_VERIFIED.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.outcome_contract import OutcomeContract, OutcomeType, VerificationState


class OutcomeEvaluationEngine:
    """
    Analyzes task outcomes to determine true verified quality and execution efficiency.
    """

    def evaluate_outcome(
        self,
        outcome: OutcomeContract,
        benchmark_duration: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generates structured evaluation of completed task outcome.
        """
        # 1. Verification strength
        verification_strength = 0.0
        if outcome.verification_state == VerificationState.VERIFIED:
            verification_strength = 1.0 if outcome.evidence_references else 0.8
        elif outcome.verification_state == VerificationState.OBSERVED:
            verification_strength = 0.7
        elif outcome.verification_state == VerificationState.SELF_REPORTED:
            verification_strength = 0.3
        elif outcome.verification_state == VerificationState.UNVERIFIED:
            verification_strength = 0.1

        # 2. Outcome quality score
        quality_score = outcome.success_score * verification_strength
        if outcome.outcome_type == OutcomeType.FAILURE:
            quality_score = 0.0
        elif outcome.outcome_type == OutcomeType.PARTIAL_SUCCESS:
            quality_score = min(0.5, quality_score)

        # 3. Efficiency score
        efficiency_score = 1.0
        if benchmark_duration and benchmark_duration > 0:
            if outcome.duration > benchmark_duration:
                ratio = benchmark_duration / outcome.duration
                efficiency_score = max(0.1, min(1.0, ratio))

        # 4. Failure signature detection
        failure_signature = None
        if outcome.outcome_type in [OutcomeType.FAILURE, OutcomeType.PARTIAL_SUCCESS, OutcomeType.REGRESSION]:
            failure_signature = outcome.failure_reason or "UNKNOWN_FAILURE"

        # 5. Improvement opportunities identification
        opportunities: List[str] = []
        if efficiency_score < 0.7:
            opportunities.append("PERFORMANCE_OPTIMIZATION")
        if verification_strength < 0.5:
            opportunities.append("VERIFICATION_STRENGTHENING")
        if failure_signature:
            opportunities.append(f"FAILURE_REPAIR_{failure_signature.upper()[:20]}")

        # Phase 12.29 Integration: Update DecisionOutcomeStore if decision_id is present
        dec_id = outcome.metadata.get("decision_id")
        if dec_id:
            try:
                from core.decision_outcome import OutcomeQuality, decision_outcome_store

                quality = OutcomeQuality.OUTCOME_UNKNOWN
                if outcome.is_verified():
                    if outcome.outcome_type in [OutcomeType.SUCCESS, OutcomeType.VERIFIED_SUCCESS]:
                        quality = OutcomeQuality.VERIFIED_CORRECT
                    elif outcome.outcome_type in [OutcomeType.FAILURE, OutcomeType.REGRESSION]:
                        quality = OutcomeQuality.VERIFIED_INCORRECT
                    elif outcome.outcome_type == OutcomeType.PARTIAL_SUCCESS:
                        quality = OutcomeQuality.PARTIALLY_CORRECT
                elif outcome.outcome_type == OutcomeType.FAILURE:
                    quality = OutcomeQuality.EXECUTION_FAILED
                elif outcome.outcome_type in [OutcomeType.SUCCESS, OutcomeType.VERIFIED_SUCCESS]:
                    quality = OutcomeQuality.EXECUTION_SUCCEEDED

                decision_outcome_store.update_outcome(
                    decision_id=dec_id,
                    actual_outcome=outcome.actual_outcome,
                    outcome_quality=quality,
                    outcome_verified=outcome.is_verified(),
                )
            except Exception:
                pass

        return {
            "outcome_id": outcome.outcome_id,
            "outcome_quality_score": round(quality_score, 3),
            "verification_strength": round(verification_strength, 3),
            "efficiency_score": round(efficiency_score, 3),
            "failure_signature": failure_signature,
            "improvement_opportunities": opportunities,
            "action_completed": outcome.success_score > 0,
            "outcome_verified": outcome.is_verified(),
        }


# Global singleton instance
outcome_evaluation_engine = OutcomeEvaluationEngine()
