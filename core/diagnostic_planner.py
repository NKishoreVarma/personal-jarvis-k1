"""
Diagnostic Planner for MARK XLVIII / JARVIS.
Generates safe, read-only diagnostic plans to validate hypotheses before any system modification.
Enforces the principle: "Separate DIAGNOSE from MODIFY".
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.reasoning_state import Hypothesis


class DiagnosticPlanner:
    """
    Creates ordered, minimal-risk diagnostic plans.
    """

    def create_diagnostic_plan(
        self,
        hypothesis: Hypothesis,
        target_project: str,
        target_port: int = 3000,
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes a read-only diagnostic action sequence tailored to the selected hypothesis.
        """
        category = hypothesis.category
        steps: List[Dict[str, Any]] = []

        if category == "PORT_CONFLICT":
            steps.append({
                "action": "inspect_port",
                "target": target_port,
                "purpose": f"Check if port {target_port} is currently bound or responsive",
                "risk_level": "READ_ONLY",
                "timeout_sec": 2.0,
            })
            steps.append({
                "action": "inspect_active_processes",
                "target": target_project,
                "purpose": f"Identify any existing or zombie processes for '{target_project}'",
                "risk_level": "READ_ONLY",
                "timeout_sec": 2.0,
            })

        elif category == "MISSING_DEPENDENCY":
            steps.append({
                "action": "inspect_manifest_files",
                "target": target_project,
                "purpose": "Verify package.json / requirements.txt / pyproject.toml presence and integrity",
                "risk_level": "READ_ONLY",
                "timeout_sec": 3.0,
            })

        elif category == "RUNTIME_ERROR":
            steps.append({
                "action": "inspect_stderr_logs",
                "target": target_project,
                "purpose": "Analyze full traceback and locate exact error source line",
                "risk_level": "READ_ONLY",
                "timeout_sec": 3.0,
            })

        else:  # CONFIG_ERROR or Generic
            steps.append({
                "action": "inspect_project_profile",
                "target": target_project,
                "purpose": f"Re-profile '{target_project}' framework and startup configuration",
                "risk_level": "READ_ONLY",
                "timeout_sec": 3.0,
            })

        return steps


# Global singleton instance
diagnostic_planner = DiagnosticPlanner()
