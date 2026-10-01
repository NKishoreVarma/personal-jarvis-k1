"""
Skill Extractor for MARK XLVIII / JARVIS.
Inspects verified task outcomes, reasoning traces, and successful repairs to extract
durable, generalized skills while rejecting trivial incidental actions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.skill_contract import SkillContract, SkillType, create_skill_contract
from core.workflow_abstraction_engine import workflow_abstraction_engine


class SkillExtractor:
    """
    Evaluates completed tasks and extracts reusable parameterized SkillContracts.
    """

    INCIDENTAL_PATTERNS = [
        re.compile(r"^(what\s+time|what\s+date|open\s+([a-zA-Z0-9\._-]+)|close\s+([a-zA-Z0-9\._-]+))$", re.IGNORECASE),
    ]

    def is_incidental(self, goal_text: str, steps: List[Dict[str, Any]]) -> bool:
        """Determines if a task was a trivial single-step or non-reusable action."""
        if len(steps) < 2:
            return True
        for pat in self.INCIDENTAL_PATTERNS:
            if pat.match(goal_text.strip()):
                return True
        return False

    def extract_skill_from_goal(
        self,
        goal_text: str,
        problem_category: Optional[str],
        concrete_steps: List[Dict[str, Any]],
        context: Dict[str, Any],
        source_experience_id: Optional[str] = None,
    ) -> Optional[SkillContract]:
        """
        Extracts a reusable SkillContract if the task satisfies usefulness and verification criteria.
        """
        if self.is_incidental(goal_text, concrete_steps):
            print("[SKILL_EXTRACTOR] ℹ️ Task is incidental; skipping skill extraction.")
            return None

        # Check for sensitive data
        if workflow_abstraction_engine.contains_secrets(concrete_steps) or workflow_abstraction_engine.contains_secrets(context):
            print("[SKILL_EXTRACTOR] 🛡️ Rejected skill extraction: contains credentials or secrets.")
            return None

        project_name = context.get("project") or context.get("project_name", "Project")
        port = context.get("port", 3000)

        # Abstract steps
        abstract_steps, params = workflow_abstraction_engine.abstract_steps(concrete_steps, context)

        if problem_category == "PORT_CONFLICT" or "port" in goal_text.lower():
            skill_name = "FIX_PROJECT_PORT_CONFLICT"
            skill_type = SkillType.REPAIR_SKILL
            description = "Diagnose and resolve conflicting process occupying target project port, restart, and verify HTTP health."
            goal_pattern = "fix port conflict for {project}"
        else:
            skill_name = f"RUN_{project_name.upper()}_WORKFLOW"
            skill_type = SkillType.PROJECT_WORKFLOW
            description = f"Standard startup, diagnostic, and verification workflow for {project_name}."
            goal_pattern = f"run or repair {project_name}"

        return create_skill_contract(
            skill_name=skill_name,
            skill_type=skill_type,
            description=description,
            goal_pattern=goal_pattern,
            problem_pattern=problem_category,
            project_scope=project_name,
            parameters=params,
            workflow_steps=abstract_steps,
            expected_outcome=f"'{project_name}' is operational and responsive on port {port}",
            verification_requirements=["outcome_verified", "http_responsive"],
            risk_level="LOW",
            source_experience_ids=[source_experience_id] if source_experience_id else [],
        )


# Global singleton instance
skill_extractor = SkillExtractor()
