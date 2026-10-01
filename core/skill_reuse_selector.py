"""
Skill Reuse Selector for Autonomous Planning Integration in MARK XLVIII / JARVIS.
Matches incoming user goals against verified, active evolved skills before initiating new planning cycles.
Enforces hierarchy: CURRENT VERIFIED EVIDENCE > ENVIRONMENT COMPATIBILITY > VERIFIED ACTIVE SKILL > NEW PLANNING.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.evolved_skill_contract import EvolvedSkillContract, SkillStatus
from core.skill_registry_evolution_manager import skill_registry_evolution_manager


class SkillReuseSelector:
    """
    Selects compatible verified skills for incoming tasks.
    """

    def __init__(self):
        self.reuse_enabled: bool = True

    def set_skill_reuse_enabled(self, enabled: bool) -> None:
        self.reuse_enabled = enabled

    def select_skill_for_goal(
        self,
        goal: str,
        project_id: str,
        environment_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[EvolvedSkillContract], str]:
        """
        Finds matching active skill if reuse is enabled and environment is compatible.
        """
        if not self.reuse_enabled:
            return None, "Skill reuse is disabled by user policy."

        active_skills = skill_registry_evolution_manager.list_active_skills(project_id=project_id)
        if not active_skills:
            return None, "No active verified skills found for project."

        g_lower = goal.lower()
        for skill in active_skills:
            # Check for name or description overlap
            if any(w in g_lower for w in skill.skill_name.lower().split("_") if len(w) > 3) or any(w in g_lower for w in skill.description.lower().split() if len(w) > 4):
                # Check environment compatibility
                if environment_state and environment_state.get("incompatible"):
                    return None, "Current environment is incompatible with skill preconditions."
                return skill, f"Selected active verified skill '{skill.skill_name}' (reliability: {skill.reliability_score:.2f})."

        return None, "No matching verified skill found; fallback to autonomous goal decomposition."


# Global singleton instance
skill_reuse_selector = SkillReuseSelector()
