"""
Hypothesis Engine for MARK XLVIII / JARVIS.
Generates and ranks bounded, evidence-driven hypotheses for system and project failures.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from core.reasoning_state import Hypothesis, HypothesisStatus


class HypothesisEngine:
    """
    Synthesizes ranked hypotheses based on environmental observations and log evidence.
    """

    def generate_hypotheses(
        self,
        project_name: str,
        evidence: Dict[str, Any],
        stderr_tail: Optional[List[str]] = None,
    ) -> List[Hypothesis]:
        """
        Produces a bounded list of ranked hypotheses ordered by confidence and diagnostic safety.
        """
        hypotheses: List[Hypothesis] = []
        stderr_str = " ".join(stderr_tail or []).lower()
        port_info = evidence.get("port_state", {})
        proj_info = evidence.get("project_state", {})

        # 1. Port Conflict Hypothesis
        port_conf = 0.5
        if "eaddrinuse" in stderr_str or "already in use" in stderr_str or "address already in use" in stderr_str:
            port_conf = 0.95
        elif port_info.get("is_responsive") and not evidence.get("active_processes"):
            port_conf = 0.85

        h_port = Hypothesis(
            hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
            description=f"Port for '{project_name}' is occupied by another process or zombie instance.",
            category="PORT_CONFLICT",
            confidence=port_conf,
            suggested_diagnostic="inspect_port_and_processes",
            suggested_repair="kill_conflicting_process_and_restart",
            diagnostic_cost=1.0,  # Read-only check
        )
        if port_conf > 0.6:
            h_port.add_support("Port or log indicates address conflict.")
        hypotheses.append(h_port)

        # 2. Missing Dependency Hypothesis
        dep_conf = 0.4
        if "cannot find module" in stderr_str or "modulenotfounderror" in stderr_str or "no module named" in stderr_str:
            dep_conf = 0.95
        elif proj_info.get("found") and not proj_info.get("profile", {}).get("success"):
            dep_conf = 0.7

        h_dep = Hypothesis(
            hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
            description=f"Missing dependencies required by '{project_name}'.",
            category="MISSING_DEPENDENCY",
            confidence=dep_conf,
            suggested_diagnostic="verify_dependencies_installed",
            suggested_repair="install_missing_dependencies",
            diagnostic_cost=2.0,
        )
        if dep_conf > 0.6:
            h_dep.add_support("Log indicates missing module or package.")
        hypotheses.append(h_dep)

        # 3. Runtime / Syntax Error Hypothesis
        err_conf = 0.3
        if "syntaxerror" in stderr_str or "typeerror" in stderr_str or "referenceerror" in stderr_str or "traceback" in stderr_str:
            err_conf = 0.90

        h_run = Hypothesis(
            hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
            description=f"Runtime or syntax exception during startup of '{project_name}'.",
            category="RUNTIME_ERROR",
            confidence=err_conf,
            suggested_diagnostic="inspect_crash_stack_trace",
            suggested_repair="propose_targeted_code_patch",
            diagnostic_cost=2.5,
        )
        if err_conf > 0.6:
            h_run.add_support("Stderr contains active traceback or syntax error.")
        hypotheses.append(h_run)

        # 4. Invalid Startup Command / Configuration Hypothesis
        h_cfg = Hypothesis(
            hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
            description=f"Invalid startup command or misconfigured environment for '{project_name}'.",
            category="CONFIG_ERROR",
            confidence=0.35,
            suggested_diagnostic="check_config_and_command",
            suggested_repair="correct_recommended_command",
            diagnostic_cost=1.5,
        )
        hypotheses.append(h_cfg)

        # Rank hypotheses: highest confidence first, lower diagnostic cost as tiebreaker
        hypotheses.sort(key=lambda h: (h.confidence, -h.diagnostic_cost), reverse=True)
        return hypotheses


# Global singleton instance
hypothesis_engine = HypothesisEngine()
