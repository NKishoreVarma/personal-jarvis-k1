"""
Agent Result Synthesizer for MARK XLVIII / JARVIS.
Consolidates multi-agent worker results and verification evidence into concise, natural,
user-facing operational explanations without leaking raw internal chain-of-thought.
"""

from __future__ import annotations

from typing import Any, Dict

from core.task_graph import TaskGraph


class AgentResultSynthesizer:
    """
    Produces clean, human-like summaries of multi-agent goal execution.
    """

    def synthesize_result(
        self,
        project_name: str,
        problem_category: str,
        graph: TaskGraph,
        verification: Dict[str, Any],
    ) -> str:
        """
        Creates user-facing summary based on verified outcome and executed repair steps.
        """
        outcome_ok = verification.get("outcome_verified", False)
        port = verification.get("port") or 3000

        if outcome_ok:
            if problem_category == "PORT_CONFLICT":
                return f"{project_name} was blocked by a conflicting process on port {port}. I cleared the conflict and {project_name} is running now."
            elif problem_category == "MISSING_DEPENDENCY":
                return f"{project_name} was missing required dependencies. I installed them and {project_name} is running on port {port}."
            else:
                return f"{project_name} is running successfully on port {port}."
        else:
            return f"I investigated {project_name}, but was unable to verify successful startup on port {port}."


# Global singleton instance
agent_result_synthesizer = AgentResultSynthesizer()
