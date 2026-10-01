"""
Skill Adapter for MARK XLVIII / JARVIS.
Adapts learned parameterized skills to current environmental observations and context.
Enforces the principle: CURRENT OBSERVATION > HISTORICAL PARAMETERS.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from core.skill_contract import SkillContract


class SkillAdapter:
    """
    Binds live environmental parameters to parameterized skill workflow steps.
    """

    def adapt_skill(
        self,
        skill: SkillContract,
        context: Dict[str, Any],
        observation: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Substitutes template variables ({project}, {port}) with current observed values.
        """
        # Current observation overrides historical context
        port_obs = observation.get("port_state", {})
        proj_obs = observation.get("project_state", {})

        current_project = context.get("project") or proj_obs.get("project_name") or skill.project_scope or "Project"
        current_port = port_obs.get("port") or context.get("port") or 3000

        adapted_steps: List[Dict[str, Any]] = []

        for step in skill.workflow_steps:
            step_copy = copy.deepcopy(step)

            # 1. Substitute target string
            if "target" in step_copy and isinstance(step_copy["target"], str):
                step_copy["target"] = step_copy["target"].replace("{project}", current_project)

            # 2. Substitute purpose string
            if "purpose" in step_copy and isinstance(step_copy["purpose"], str):
                step_copy["purpose"] = step_copy["purpose"].replace("{project}", current_project)

            # 3. Substitute nested parameters
            if "params" in step_copy and isinstance(step_copy["params"], dict):
                p_copy = {}
                for k, v in step_copy["params"].items():
                    if isinstance(v, str):
                        v_sub = v.replace("{project}", current_project).replace("{port}", str(current_port))
                        p_copy[k] = v_sub
                    else:
                        p_copy[k] = v
                step_copy["params"] = p_copy

            adapted_steps.append(step_copy)

        return adapted_steps


# Global singleton instance
skill_adapter = SkillAdapter()
