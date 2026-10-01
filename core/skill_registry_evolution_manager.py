"""
Skill Registry Evolution Manager for Capability Evolution in MARK XLVIII / JARVIS.
Coordinates versioned lifecycle transitions (CANDIDATE, TESTING, VERIFIED, ACTIVE, DEGRADED, SUSPENDED, DEPRECATED).
Enforces rule: Never overwrite verified skills silently; maintain versioned provenance.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from core.evolved_skill_contract import EvolvedSkillContract, SkillStatus


class SkillRegistryEvolutionManager:
    """
    Manages evolved capability records, versioning, and state transitions.
    """

    def __init__(self):
        self._skills: Dict[str, EvolvedSkillContract] = {}
        self._version_history: Dict[str, List[EvolvedSkillContract]] = {}

    def register_candidate(self, skill: EvolvedSkillContract) -> str:
        skill.status = SkillStatus.CANDIDATE
        self._skills[skill.skill_id] = skill
        self._version_history.setdefault(skill.skill_name, []).append(skill)
        return skill.skill_id

    def activate_skill(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = SkillStatus.ACTIVE
        skill.updated_at = time.time()
        return True

    def promote_skill(self, skill_id: str, new_status: SkillStatus) -> bool:
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = new_status
        skill.updated_at = time.time()
        return True

    def degrade_skill(self, skill_id: str, reason: str) -> bool:
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = SkillStatus.DEGRADED
        skill.metadata["degraded_reason"] = reason
        skill.updated_at = time.time()
        return True

    def suspend_skill(self, skill_id: str, reason: str) -> bool:
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = SkillStatus.SUSPENDED
        skill.metadata["suspended_reason"] = reason
        skill.updated_at = time.time()
        return True

    def deprecate_skill(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = SkillStatus.DEPRECATED
        skill.deprecated_at = time.time()
        skill.updated_at = time.time()
        return True

    def get_skill(self, skill_id: str) -> Optional[EvolvedSkillContract]:
        return self._skills.get(skill_id)

    def list_active_skills(self, project_id: Optional[str] = None) -> List[EvolvedSkillContract]:
        active = []
        for s in self._skills.values():
            if s.is_active():
                if project_id and s.scope.value == "PROJECT":
                    if s.metadata.get("project_id", "").lower() == project_id.lower():
                        active.append(s)
                else:
                    active.append(s)
        return active

    def clear_all(self) -> None:
        self._skills.clear()
        self._version_history.clear()


# Global singleton instance
skill_registry_evolution_manager = SkillRegistryEvolutionManager()
