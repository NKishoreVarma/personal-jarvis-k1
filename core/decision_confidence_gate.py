"""
Decision Confidence Gate for System 1 Decision Engine in MARK XLVIII / JARVIS.
Enforces strict thresholds on confidence, alternative score margins, and operational risk before allowing fast-path routing.
Extended in Phase 12.29 to support route-specific calibrated thresholds and conservative drift degradation.
Enforces rule: Never blindly trust System 1. Low confidence or high risk must abstain and escalate to System 2.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.decision_contract import DecisionCategory, DecisionResult


class DecisionConfidenceGate:
    """
    Evaluates decision confidence, margin separations, calibrated route thresholds, and risk barriers.
    """

    def __init__(
        self,
        minimum_confidence: float = 0.75,
        minimum_margin: float = 0.15,
        maximum_risk_for_fast_path: str = "medium",
        novelty_threshold: float = 0.80,
    ):
        self.minimum_confidence = minimum_confidence
        self.minimum_margin = minimum_margin
        self.maximum_risk_for_fast_path = maximum_risk_for_fast_path
        self.novelty_threshold = novelty_threshold

    def get_effective_threshold(self, category: DecisionCategory) -> float:
        """
        Calculates effective confidence threshold for a category by combining:
        1. Calibrated policy threshold from DecisionPolicyManager (or baseline 0.75)
        2. Conservative drift penalty from DecisionDriftDetector (if WARNING/DRIFT/DEGRADED)
        """
        threshold = self.minimum_confidence
        try:
            from core.decision_policy_proposal import decision_policy_manager

            threshold = max(threshold, decision_policy_manager.get_threshold(category))
        except Exception:
            pass

        try:
            from core.decision_drift_detector import decision_drift_detector

            assessment = decision_drift_detector.assess_route(category)
            threshold += assessment.threshold_penalty
        except Exception:
            pass

        # Clamp between minimum_confidence and 0.99
        return min(0.99, max(self.minimum_confidence, threshold))

    def evaluate_decision(self, decision: DecisionResult) -> Tuple[bool, str]:
        """
        Returns (is_approved_for_fast_path, rationale).
        If False, marks decision.abstained = True.
        """
        if decision.abstained:
            return False, f"Decision already abstained: {decision.reason_code}"

        # 1. High Risk Check (Absolute Invariant: High or unknown risk cannot bypass System 2)
        if decision.category == DecisionCategory.RISK:
            if decision.selected_option in ["high", "unknown"]:
                decision.abstained = True
                decision.reason_code = "HIGH_RISK_ESCALATION"
                return False, f"High or unknown risk detected ('{decision.selected_option}'). Escalating to System 2."

        # 2. Concept Drift / Conservative Degradation Check
        try:
            from core.decision_drift_detector import DriftState, decision_drift_detector

            assessment = decision_drift_detector.assess_route(decision.category)
            if assessment.state == DriftState.DEGRADED and assessment.force_system2:
                decision.abstained = True
                decision.reason_code = "CONSERVATIVE_DRIFT_DEGRADATION"
                return False, f"Concept drift degraded for route {decision.category.value}. Escalating to System 2."
        except Exception:
            pass

        # 3. Calibrated Minimum Confidence Check
        effective_threshold = self.get_effective_threshold(decision.category)
        if decision.confidence < effective_threshold:
            decision.abstained = True
            decision.reason_code = "INSUFFICIENT_CONFIDENCE"
            return (
                False,
                f"Confidence {round(decision.confidence, 3)} is below calibrated threshold {round(effective_threshold, 3)}.",
            )

        # 4. Alternative Margin Check (for Choice decisions with multiple options)
        if decision.alternatives and len(decision.alternatives) > 1:
            sorted_alts = sorted(decision.alternatives.values(), reverse=True)
            top_score = sorted_alts[0]
            runner_up = sorted_alts[1]
            margin = top_score - runner_up
            if margin < self.minimum_margin:
                decision.abstained = True
                decision.reason_code = "MARGIN_TOO_NARROW"
                return (
                    False,
                    f"Alternative margin {round(margin, 3)} is below required separation {self.minimum_margin}.",
                )

        return True, "Confidence gate passed; eligible for fast-path routing."


# Global singleton instance
decision_confidence_gate = DecisionConfidenceGate()
