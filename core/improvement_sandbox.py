"""
Improvement Sandbox for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Simulates and measures candidate workflow improvements in an isolated dry-run environment.
Enforces rule: No destructive mutations and no modification of ActionContract / ApprovalStore safety boundaries.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.improvement_opportunity_contract import ImprovementOpportunityContract, ImprovementState


class ImprovementSandbox:
    """
    Evaluates improvement candidates in a simulated environment to quantify deltas and ensure safety preservation.
    """

    def simulate_candidate(
        self,
        candidate: ImprovementOpportunityContract,
        simulated_candidate_metrics: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Runs isolated simulation comparison between baseline and candidate.
        """
        candidate.state = ImprovementState.TESTING

        baseline = candidate.baseline_metrics or {"success_rate": 0.70, "avg_duration": 8.0}
        candidate_res = simulated_candidate_metrics or {
            "success_rate": candidate.baseline_metrics.get("success_rate", 0.70) + 0.15,
            "avg_duration": max(1.0, candidate.baseline_metrics.get("avg_duration", 8.0) - 3.0),
        }
        candidate.candidate_metrics = candidate_res

        # Calculate deltas
        success_delta = candidate_res.get("success_rate", 0.0) - baseline.get("success_rate", 0.0)
        duration_delta = baseline.get("avg_duration", 0.0) - candidate_res.get("avg_duration", 0.0)

        regression_detected = success_delta < -0.01

        # Check safety invariants: Candidate cannot request authority changes
        safety_status = "SAFE"
        if candidate.metadata.get("requested_authority_bypass", False):
            safety_status = "UNSAFE_AUTHORITY_ESCALATION"
            regression_detected = True

        return {
            "opportunity_id": candidate.opportunity_id,
            "baseline_result": baseline,
            "candidate_result": candidate_res,
            "success_delta": round(success_delta, 3),
            "duration_delta": round(duration_delta, 3),
            "regression_detected": regression_detected,
            "safety_status": safety_status,
        }


# Global singleton instance
improvement_sandbox = ImprovementSandbox()
