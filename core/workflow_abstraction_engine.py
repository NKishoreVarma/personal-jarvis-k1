"""
Workflow Abstraction Engine for MARK XLVIII / JARVIS.
Converts concrete execution steps into parameterized, generalized workflows.
Substitutes concrete parameters with template variables while rigorously filtering secrets and private tokens.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class WorkflowAbstractionEngine:
    """
    Generalizes concrete actions into reusable parameterized workflow definitions.
    """

    SECRET_PATTERNS = [
        re.compile(r"(api[_-]?key|secret|password|bearer\s+[a-zA-Z0-9_\-\.]{15,}|token|private[_-]?key)", re.IGNORECASE),
        re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
        re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    ]

    def contains_secrets(self, val: Any) -> bool:
        """Recursively inspects values for sensitive tokens or credentials."""
        if isinstance(val, str):
            for pat in self.SECRET_PATTERNS:
                if pat.search(val):
                    return True
        elif isinstance(val, dict):
            for k, v in val.items():
                if self.contains_secrets(k) or self.contains_secrets(v):
                    return True
        elif isinstance(val, (list, tuple)):
            for item in val:
                if self.contains_secrets(item):
                    return True
        return False

    def abstract_steps(
        self,
        concrete_steps: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Abstracts concrete entities into template placeholders (e.g. {project}, {port}).
        Returns (abstracted_steps, discovered_parameters).
        """
        if self.contains_secrets(concrete_steps) or self.contains_secrets(context):
            raise ValueError("Workflow contains sensitive credentials or secret tokens.")

        project_name = context.get("project") or context.get("project_name", "")
        port = context.get("port") or context.get("target_port")

        parameters: Dict[str, Any] = {}
        if project_name:
            parameters["project"] = {"type": "string", "default": project_name, "description": "Target project name"}
        if port:
            parameters["port"] = {"type": "integer", "default": port, "description": "Listening TCP port"}

        abstracted_steps: List[Dict[str, Any]] = []

        for step in concrete_steps:
            step_copy = dict(step)
            # Abstract target
            if "target" in step_copy and project_name:
                if isinstance(step_copy["target"], str) and project_name.lower() in step_copy["target"].lower():
                    step_copy["target"] = "{project}"
            # Abstract port parameter
            if "params" in step_copy and isinstance(step_copy["params"], dict):
                p_copy = dict(step_copy["params"])
                if port and p_copy.get("port") == port:
                    p_copy["port"] = "{port}"
                step_copy["params"] = p_copy

            abstracted_steps.append(step_copy)

        return abstracted_steps, parameters


# Global singleton instance
workflow_abstraction_engine = WorkflowAbstractionEngine()
