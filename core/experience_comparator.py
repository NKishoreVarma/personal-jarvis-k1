"""
Experience Comparator for MARK XLVIII / JARVIS.
Compares active execution traces against historical memory and skill experience records
to detect recurring success patterns or repeated failure signatures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.memory_service import memory_service
from core.skill_registry import skill_registry


class ExperienceComparator:
    """
    Evaluates pattern similarity between current execution outcome and historical experience traces.
    """

    def compare_experience(
        self,
        project_name: str,
        problem_signature: str,
        current_strategy: str,
    ) -> Tuple[float, Optional[str]]:
        """
        Calculates similarity score (0.0 to 1.0) and retrieves best-matching historical experience hint.
        """
        proj = project_name.lower().strip()
        sig = problem_signature.lower().strip()

        # 1. Inspect MemoryService
        memories = memory_service.retrieve(query=f"{project_name} {problem_signature}", project_scope=project_name)
        if memories:
            best_mem = memories[0]
            sim = 0.90 if proj in best_mem.subject.lower() else 0.70
            return sim, f"Matched prior experience: {best_mem.subject}"

        # 2. Inspect SkillRegistry
        skills = skill_registry.search_skills(query=problem_signature, project_name=project_name)
        if skills:
            best_skill = skills[0]
            return 0.92, f"Matched verified skill: {best_skill.skill_name}"

        return 0.0, None


# Global singleton instance
experience_comparator = ExperienceComparator()
