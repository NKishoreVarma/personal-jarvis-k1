"""
Skill Evolution Engine for MARK XLVIII / JARVIS.
Handles version evolution of learned skills when safer or more effective workflows are discovered.
Preserves prior versions in historical evolution trace.
"""

from __future__ import annotations

import copy
import time
from typing import Any, Dict, List, Optional

from core.skill_contract import SkillContract
from core.skill_registry import skill_registry


class SkillEvolutionEngine:
    """
    Coordinates versioned evolution of learned skills.
    """

    def evolve_skill(
        self,
        skill_id: str,
        improved_workflow_steps: List[Dict[str, Any]],
        change_reason: str,
    ) -> Optional[SkillContract]:
        """
        Creates a versioned upgrade (e.g. v1 -> v2) for a skill, archiving previous steps.
        """
        skill = skill_registry.retrieve_skill(skill_id)
        if not skill:
            return None

        # Snapshot current version
        snapshot = {
            "version": skill.version,
            "workflow_steps": copy.deepcopy(skill.workflow_steps),
            "updated_at": time.time(),
            "change_reason": change_reason,
            "success_count": skill.success_count,
            "confidence": skill.confidence,
        }

        skill.evolution_history.append(snapshot)
        skill.version += 1
        skill.workflow_steps = improved_workflow_steps
        skill.last_verified_at = time.time()
        skill.confidence = min(1.0, skill.confidence + 0.1)

        skill_registry._persist_to_disk()
        print(f"[SKILL_EVOLUTION] 🌟 Evolved skill '{skill.skill_name}' to version {skill.version} ({change_reason})")
        return skill


# Global singleton instance
skill_evolution_engine = SkillEvolutionEngine()
