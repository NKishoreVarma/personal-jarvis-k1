"""
Skill Composition Engine for Autonomous Skill Composition in MARK XLVIII / JARVIS.
Combines multiple verified child skills into higher-level composite workflows.
Enforces rule: Composite skill authority = STRICTEST authority of any child skill.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional, Tuple

from core.evolved_skill_contract import (
    EvolvedSkillContract,
    SkillScope,
    SkillStatus,
    SkillType,
    create_evolved_skill_contract,
)

AUTHORITY_LEVELS = {
    "READ_ONLY": 0,
    "DIAGNOSTIC": 1,
    "LOCAL_MUTATION": 2,
    "HIGH_RISK": 3,
}


class SkillCompositionEngine:
    """
    Composes verified atomic or workflow skills into verified composite skills.
    """

    def compose_skills(
        self,
        composite_name: str,
        description: str,
        child_skills: List[EvolvedSkillContract],
        scope: SkillScope = SkillScope.PROJECT,
    ) -> Tuple[Optional[EvolvedSkillContract], str]:
        """
        Creates a new composite skill contract from active child skills.
        """
        if not child_skills:
            return None, "Rejected: Child skills list cannot be empty."

        # 1. Verify all children are active/verified
        for s in child_skills:
            if not s.is_active():
                return None, f"Rejected: Child skill '{s.skill_name}' is not in active/verified state ({s.status.value})."

        # 2. Determine strictest authority required
        strictest_auth = "READ_ONLY"
        max_level = 0
        for s in child_skills:
            lvl = AUTHORITY_LEVELS.get(s.authority_required, 0)
            if lvl > max_level:
                max_level = lvl
                strictest_auth = s.authority_required

        # 3. Aggregate execution steps preserving child ordering
        combined_steps = []
        combined_tools = set()
        combined_verif = []

        for s in child_skills:
            combined_steps.extend(s.execution_steps)
            combined_tools.update(s.required_tools)
            combined_verif.extend(s.verification_requirements)

        composition_id = f"comp_{uuid.uuid4().hex[:8]}"

        composite = create_evolved_skill_contract(
            skill_name=composite_name,
            description=description,
            skill_type=SkillType.COMPOSITE,
            scope=scope,
            execution_steps=combined_steps,
            required_tools=list(combined_tools),
            authority_required=strictest_auth,
            verification_requirements=list(set(combined_verif)),
            metadata={
                "composition_id": composition_id,
                "child_count": len(child_skills),
            },
        )
        composite.parent_skill_ids = [s.skill_id for s in child_skills]
        composite.composition_id = composition_id
        composite.status = SkillStatus.VERIFIED

        return composite, "Successfully composed skills."


# Global singleton instance
skill_composition_engine = SkillCompositionEngine()
