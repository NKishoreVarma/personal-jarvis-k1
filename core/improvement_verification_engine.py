"""
Improvement Verification Engine for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Independently verifies candidate improvements against baseline metrics, regression criteria, and safety invariants.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Tuple

from core.improvement_opportunity_contract import ImprovementOpportunityContract, ImprovementState


class ImprovementVerificationResult(str, Enum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_IMPROVEMENT = "NO_IMPROVEMENT"
    IMPROVED = "IMPROVED"
    REGRESSION = "REGRESSION"
    SAFETY_REJECTED = "SAFETY_REJECTED"


class ImprovementVerificationEngine:
    """
    Validates that a simulated improvement candidate meets empirical improvement thresholds without regressions.
    """

    def verify_candidate(
        self,
        candidate: ImprovementOpportunityContract,
        sandbox_result: Dict[str, Any],
    ) -> Tuple[ImprovementVerificationResult, str]:
        """
        Determines verification state for a candidate.
        """
        # 1. Safety check
        if sandbox_result.get("safety_status") != "SAFE":
            candidate.state = ImprovementState.REJECTED
            return ImprovementVerificationResult.SAFETY_REJECTED, "Candidate violated safety boundary."

        # 2. Regression check
        if sandbox_result.get("regression_detected", False):
            candidate.state = ImprovementState.REJECTED
            return ImprovementVerificationResult.REGRESSION, "Candidate caused performance or reliability regression."

        # 3. Evidence check
        if not candidate.evidence_references:
            return ImprovementVerificationResult.INSUFFICIENT_EVIDENCE, "Candidate lacks empirical evidence references."

        # 4. Metric delta check
        success_delta = sandbox_result.get("success_delta", 0.0)
        duration_delta = sandbox_result.get("duration_delta", 0.0)

        if success_delta > 0.05 or duration_delta > 1.0:
            candidate.state = ImprovementState.VERIFIED
            return ImprovementVerificationResult.IMPROVED, "Candidate demonstrates measurable improvement without regression."

        return ImprovementVerificationResult.NO_IMPROVEMENT, "Candidate failed to demonstrate sufficient improvement over baseline."


# Global singleton instance
improvement_verification_engine = ImprovementVerificationEngine()
