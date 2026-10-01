"""
Skill Learning Loop for MARK XLVIII / JARVIS.
Connects verified problem solving outcomes to automatic skill extraction, parameterization,
validation, and persistent registry storage asynchronously without blocking voice or audio.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.event_bus import Event, EventType, event_bus
from core.skill_extractor import skill_extractor
from core.skill_registry import skill_registry


class SkillLearningLoop:
    """
    Asynchronously converts verified task executions into reusable skills.
    """

    def __init__(self):
        self._subscribe()

    def _subscribe(self) -> None:
        event_bus.subscribe(EventType.PROJECT_READY, self.on_project_ready)

    def on_project_ready(self, event: Event) -> None:
        """Extracts and registers skill candidate when a project recovery completes."""
        payload = event.payload
        project = payload.get("project")
        port = payload.get("port", 3000)
        category = payload.get("category", "PORT_CONFLICT")
        actions = payload.get("actions", ["terminate_conflicting_processes", "restart_project_server"])

        if project and actions:
            concrete_steps = [
                {"action": act, "target": project, "risk_level": "LOW", "params": {"port": port}}
                for act in actions
            ]
            self.learn_skill_from_outcome(
                project_name=project,
                problem_category=category,
                concrete_steps=concrete_steps,
                port=port,
            )

    def learn_skill_from_outcome(
        self,
        project_name: str,
        problem_category: str,
        concrete_steps: List[Dict[str, Any]],
        port: int = 3000,
    ) -> Optional[str]:
        """
        Extracts, parameterizes, and registers a reusable skill contract.
        """
        skill = skill_extractor.extract_skill_from_goal(
            goal_text=f"Fix {project_name} {problem_category}",
            problem_category=problem_category,
            concrete_steps=concrete_steps,
            context={"project": project_name, "port": port},
        )

        if skill:
            skill_id = skill_registry.register_skill(skill)
            print(f"[SKILL_LEARNING_LOOP] 🌟 Learned and registered skill '{skill.skill_name}' (id={skill_id})")
            return skill_id
        return None


# Global singleton instance
skill_learning_loop = SkillLearningLoop()
