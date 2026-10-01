"""
Skill Registry for MARK XLVIII / JARVIS.
Provides persistent storage, deduplication, search, retrieval, reinforcement, degradation,
and retirement of learned skills and workflows.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from core.skill_contract import SkillContract, SkillStatus, SkillType


class SkillRegistry:
    """
    Persistent registry and lifecycle manager for learned skills.
    """

    def __init__(self, storage_path: str = "data/learned_skills.json"):
        self.storage_path = storage_path
        self._skills: Dict[str, SkillContract] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Loads skills from JSON storage if available."""
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for item in raw_data:
                    skill = SkillContract.from_dict(item)
                    if not skill.is_expired():
                        self._skills[skill.skill_id] = skill
        except Exception as e:
            print(f"[SKILL_REGISTRY] Warning loading skills: {e}")

    def _persist_to_disk(self) -> None:
        """Persists active and non-expired skills to JSON storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            items = [
                s.to_dict() for s in self._skills.values()
                if not s.is_expired() and s.status != SkillStatus.FORGOTTEN
            ]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
        except Exception as e:
            print(f"[SKILL_REGISTRY] Warning persisting skills: {e}")

    def register_skill(self, skill: SkillContract) -> str:
        """
        Registers a new skill or merges with an existing equivalent skill.
        """
        # Deduplication check
        for existing in self._skills.values():
            if (
                existing.skill_name.lower() == skill.skill_name.lower()
                and existing.project_scope == skill.project_scope
                and existing.workflow_steps == skill.workflow_steps
            ):
                # Merge evidence & reinforce existing skill
                existing.success_count += 1
                existing.confidence = min(1.0, existing.confidence + 0.05)
                existing.last_verified_at = time.time()
                for exp_id in skill.source_experience_ids:
                    if exp_id not in existing.source_experience_ids:
                        existing.source_experience_ids.append(exp_id)
                self._persist_to_disk()
                print(f"[SKILL_REGISTRY] 🔄 Merged with existing skill '{existing.skill_name}' (id={existing.skill_id})")
                return existing.skill_id

        self._skills[skill.skill_id] = skill
        self._persist_to_disk()
        print(f"[SKILL_REGISTRY] 💾 Registered new skill '{skill.skill_name}' (id={skill.skill_id})")
        return skill.skill_id

    def retrieve_skill(self, skill_id: str) -> Optional[SkillContract]:
        skill = self._skills.get(skill_id)
        if skill and skill.is_expired():
            self._skills.pop(skill_id, None)
            return None
        return skill

    def search_skills(
        self,
        query: str = "",
        project_name: Optional[str] = None,
        skill_type: Optional[SkillType] = None,
        only_active: bool = True,
    ) -> List[SkillContract]:
        """
        Searches skills matching query, project scope, and type filters.
        """
        q_tokens = set(query.lower().split()) if query else set()
        results: List[SkillContract] = []

        for skill in self._skills.values():
            if skill.is_expired():
                continue
            if only_active and skill.status not in (SkillStatus.ACTIVE, SkillStatus.VALIDATED):
                continue
            if project_name and skill.project_scope:
                if skill.project_scope.lower() != project_name.lower():
                    continue
            if skill_type and skill.skill_type != skill_type:
                continue

            if q_tokens:
                corpus = f"{skill.skill_name} {skill.description} {skill.goal_pattern}".lower()
                if not any(tok in corpus for tok in q_tokens) and not (project_name and skill.project_scope):
                    continue

            results.append(skill)

        return results

    def reinforce_skill(self, skill_id: str) -> bool:
        """Reinforces skill confidence and increments success/reuse counters."""
        skill = self.retrieve_skill(skill_id)
        if not skill:
            return False
        skill.success_count += 1
        skill.reuse_count += 1
        skill.confidence = min(1.0, skill.confidence + 0.05)
        skill.last_used_at = time.time()
        skill.last_verified_at = time.time()
        if skill.status == SkillStatus.DEGRADED:
            skill.status = SkillStatus.ACTIVE
        self._persist_to_disk()
        return True

    def record_failure(self, skill_id: str, error: str = "") -> bool:
        """Records a failed execution, reducing confidence and degrading if repeated."""
        skill = self.retrieve_skill(skill_id)
        if not skill:
            return False
        skill.failure_count += 1
        skill.confidence = max(0.1, skill.confidence - 0.25)
        skill.last_used_at = time.time()

        if skill.failure_count >= 3:
            skill.status = SkillStatus.RETIRED
            print(f"[SKILL_REGISTRY] 🛑 Skill '{skill.skill_name}' retired due to repeated failures.")
        elif skill.failure_count >= 1:
            skill.status = SkillStatus.DEGRADED
            print(f"[SKILL_REGISTRY] ⚠️ Skill '{skill.skill_name}' degraded.")

        self._persist_to_disk()
        return True

    def degrade_skill(self, skill_id: str) -> bool:
        skill = self.retrieve_skill(skill_id)
        if not skill:
            return False
        skill.status = SkillStatus.DEGRADED
        self._persist_to_disk()
        return True

    def retire_skill(self, skill_id: str) -> bool:
        skill = self.retrieve_skill(skill_id)
        if not skill:
            return False
        skill.status = SkillStatus.RETIRED
        self._persist_to_disk()
        return True

    def forget_skill(self, skill_name_or_id: str) -> int:
        """Removes or marks forgotten matching skills."""
        clean = skill_name_or_id.strip().lower()
        to_remove = []
        for sid, skill in self._skills.items():
            if sid == skill_name_or_id or clean in skill.skill_name.lower() or (skill.project_scope and skill.project_scope.lower() in clean):
                to_remove.append(sid)

        for sid in to_remove:
            self._skills.pop(sid, None)

        if to_remove:
            self._persist_to_disk()
        return len(to_remove)

    def list_skills(self) -> List[SkillContract]:
        return [s for s in self._skills.values() if not s.is_expired()]

    def clear(self) -> None:
        self._skills.clear()
        self._persist_to_disk()


# Global singleton instance
skill_registry = SkillRegistry()
