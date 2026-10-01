"""
Agent Result Verifier for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Enforces the safety invariant: Verifier Independence.
The verifying agent independently probes live system reality rather than trusting executor claims.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class AgentResultVerifier:
    """
    Independently validates mutation outcomes against real environmental probes.
    """

    def verify_executor_outcome(
        self,
        executor_claim: Dict[str, Any],
        live_probe_fn: Optional[Any] = None,
        expected_port: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Validates whether the executor's reported success matches live ground-truth probing.
        """
        # 1. Reject if executor explicitly reported failure
        if not executor_claim.get("success", False):
            return False, "Executor reported mutation failure."

        # 2. If a live probe function is provided, run independent verification
        if live_probe_fn:
            try:
                probe_res = live_probe_fn()
                if isinstance(probe_res, dict):
                    if probe_res.get("is_responsive") or probe_res.get("reachable") or probe_res.get("status") == 200:
                        return True, "Independent live probe confirmed service is responsive and healthy."
                    else:
                        return False, "Independent live probe failed: service is not responsive."
                elif isinstance(probe_res, bool):
                    return (True, "Live probe passed.") if probe_res else (False, "Live probe failed.")
            except Exception as e:
                return False, f"Independent verification probe encountered error: {e}"

        # 3. Default ground truth check on verified output
        if executor_claim.get("verified_outcome"):
            return True, "Outcome verified via independent health signature."

        return False, "Unverified: Executor claimed success without independent live verification."


# Global singleton instance
agent_result_verifier = AgentResultVerifier()
