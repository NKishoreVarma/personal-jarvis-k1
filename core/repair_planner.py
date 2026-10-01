"""
Repair Planner for MARK XLVIII / JARVIS.
Generates minimal, safe, reversible repair plans based on confirmed diagnostic evidence.
Enforces the repair hierarchy: Reversible -> Local -> Low-risk -> Minimal scope -> Verifiable.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.reasoning_state import Hypothesis


class RepairPlanner:
    """
    Synthesizes targeted repair action sequences.
    """

    def create_repair_plan(
        self,
        hypothesis: Hypothesis,
        target_project: str,
        diagnostic_evidence: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Constructs a minimal-scope repair plan with explicit risk classification.
        """
        category = hypothesis.category
        steps: List[Dict[str, Any]] = []

        if category == "PORT_CONFLICT":
            # 1. Terminate conflicting zombie processes (Reversible & Local)
            steps.append({
                "action": "terminate_conflicting_processes",
                "target": target_project,
                "purpose": f"Stop conflicting or zombie processes occupying port for '{target_project}'",
                "risk_level": "REVERSIBLE",
                "timeout_sec": 5.0,
            })
            # 2. Restart target project
            steps.append({
                "action": "restart_project_server",
                "target": target_project,
                "purpose": f"Launch clean development server for '{target_project}'",
                "risk_level": "LOW",
                "timeout_sec": 8.0,
            })

        elif category == "MISSING_DEPENDENCY":
            dep_name = diagnostic_evidence.get("missing_module", "dependencies")
            steps.append({
                "action": "install_dependencies",
                "target": target_project,
                "params": {"package": dep_name},
                "purpose": f"Install required dependency '{dep_name}' for '{target_project}'",
                "risk_level": "LOW",
                "timeout_sec": 30.0,
            })
            steps.append({
                "action": "restart_project_server",
                "target": target_project,
                "purpose": f"Restart '{target_project}' server after installing dependencies",
                "risk_level": "LOW",
                "timeout_sec": 8.0,
            })

        elif category == "RUNTIME_ERROR":
            steps.append({
                "action": "propose_code_fix",
                "target": target_project,
                "purpose": f"Apply targeted code fix for runtime crash in '{target_project}'",
                "risk_level": "REVERSIBLE",
                "timeout_sec": 10.0,
            })
            steps.append({
                "action": "restart_project_server",
                "target": target_project,
                "purpose": f"Restart '{target_project}' server after code fix",
                "risk_level": "LOW",
                "timeout_sec": 8.0,
            })

        else:
            steps.append({
                "action": "restart_project_server",
                "target": target_project,
                "purpose": f"Attempt fresh startup of '{target_project}' with verified settings",
                "risk_level": "LOW",
                "timeout_sec": 8.0,
            })

        return steps


# Global singleton instance
repair_planner = RepairPlanner()
