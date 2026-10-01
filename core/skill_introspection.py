"""
Skill Introspection for MARK XLVIII / JARVIS.
Provides clean, structured operational explanations of learned skills, workflows,
and execution rationale without leaking raw chain-of-thought.
"""

from __future__ import annotations

from typing import List, Optional

from core.skill_contract import SkillContract
from core.skill_registry import skill_registry


class SkillIntrospection:
    """
    Translates internal skill registries into natural, human-readable explanations.
    """

    def describe_learned_skills(self) -> str:
        """Summarizes all active learned skills."""
        skills = skill_registry.search_skills(only_active=True)
        if not skills:
            return "I haven't learned any reusable workflows yet."

        descriptions = []
        for s in skills:
            descriptions.append(f"• {s.skill_name}: {s.description} (Version {s.version}, {s.success_count} successful runs)")

        return f"I've learned {len(skills)} reusable workflows:\n" + "\n".join(descriptions)

    def describe_skill_for_project(self, project_name: str) -> str:
        """Explains skills specific to a named project."""
        skills = skill_registry.search_skills(project_name=project_name, only_active=True)
        if not skills:
            return f"I haven't recorded a specific workflow for {project_name} yet."

        top = skills[0]
        return f"I learned a {top.skill_type.value.replace('_', ' ').lower()} for {project_name}: {top.description}"

    def explain_skill_selection(self, skill_name: str, matched_pattern: str) -> str:
        """Explains why a specific skill was chosen."""
        return f"The current issue matched our verified '{skill_name}' workflow (pattern: {matched_pattern})."


# Global singleton instance
skill_introspection = SkillIntrospection()
