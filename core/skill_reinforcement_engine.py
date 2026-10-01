"""
Skill Reinforcement Engine for MARK XLVIII / JARVIS.
Reinforces skills on verified real-world success and demotes or retires repeatedly failing skills.
"""

from __future__ import annotations

from core.skill_contract import SkillContract, SkillStatus
from core.skill_registry import skill_registry


class SkillReinforcementEngine:
    """
    Manages reinforcement and degradation lifecycles for learned skills.
    """

    def on_skill_success(self, skill_id: str) -> bool:
        """Reinforces confidence and resets failure counters after verified outcome."""
        return skill_registry.reinforce_skill(skill_id)

    def on_skill_failure(self, skill_id: str, error: str = "") -> bool:
        """Records execution failure, penalizes confidence, and transitions to DEGRADED or RETIRED."""
        return skill_registry.record_failure(skill_id, error=error)


# Global singleton instance
skill_reinforcement_engine = SkillReinforcementEngine()
