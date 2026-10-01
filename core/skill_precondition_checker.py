"""
Skill Precondition Checker for MARK XLVIII / JARVIS.
Verifies all environmental, parameter, and safety prerequisites before permitting skill execution.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.skill_contract import SkillContract, SkillStatus


class SkillPreconditionChecker:
    """
    Validates preconditions for learned skill execution.
    """

    def check_preconditions(
        self,
        skill: SkillContract,
        context: Dict[str, Any],
        observation: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates lifecycle, project existence, parameters, and environmental readiness.
        """
        # 1. Check skill lifecycle state
        if skill.status not in (SkillStatus.ACTIVE, SkillStatus.VALIDATED):
            return False, f"Skill '{skill.skill_name}' is in {skill.status.value} state (must be ACTIVE)."

        if skill.is_expired():
            return False, f"Skill '{skill.skill_name}' has expired."

        # 2. Check confidence threshold
        if skill.confidence < 0.35:
            return False, f"Skill confidence ({skill.confidence:.2f}) is below operational threshold (0.35)."

        # 3. Check project presence if required
        if "project_exists" in skill.required_preconditions:
            proj_obs = observation.get("project_state", {})
            if proj_obs and not proj_obs.get("found", True):
                return False, f"Target project required by skill '{skill.skill_name}' was not found."

        # 4. Check parameter availability
        project_name = context.get("project") or skill.project_scope
        if not project_name and "{project}" in str(skill.workflow_steps):
            return False, "Target project name cannot be resolved from context or skill."

        return True, None


# Global singleton instance
skill_precondition_checker = SkillPreconditionChecker()
