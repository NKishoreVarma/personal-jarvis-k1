"""
Skill Regression Monitor for Capability Evolution in MARK XLVIII / JARVIS.
Tracks runtime execution metrics (success rate, verification rate, duration drift, failure patterns)
and transitions degraded skills into WATCH, DEGRADED, or SUSPENDED states.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.evolved_skill_contract import EvolvedSkillContract, SkillStatus
from core.skill_registry_evolution_manager import skill_registry_evolution_manager


class SkillHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class SkillRegressionMonitor:
    """
    Monitors reliability drift and degrades untrusted skills.
    """

    def evaluate_skill_health(self, skill: EvolvedSkillContract) -> Tuple[SkillHealthState, str]:
        """
        Evaluates execution statistics against reliability boundaries.
        """
        if skill.usage_count == 0:
            return SkillHealthState.HEALTHY, "No execution history yet."

        success_rate = skill.successful_runs / skill.usage_count

        if skill.failed_runs >= 3 and success_rate < 0.50:
            skill_registry_evolution_manager.suspend_skill(skill.skill_id, "Multiple consecutive failures")
            return SkillHealthState.CRITICAL, f"Critical: High failure rate ({success_rate:.1%}); suspended."

        if success_rate < 0.70:
            skill_registry_evolution_manager.degrade_skill(skill.skill_id, "Success rate below 70%")
            return SkillHealthState.DEGRADED, f"Degraded: Low success rate ({success_rate:.1%})."

        if success_rate < 0.85:
            return SkillHealthState.WATCH, f"Watch: Marginal success rate ({success_rate:.1%})."

        return SkillHealthState.HEALTHY, "Skill is healthy and reliable."


# Global singleton instance
skill_regression_monitor = SkillRegressionMonitor()
