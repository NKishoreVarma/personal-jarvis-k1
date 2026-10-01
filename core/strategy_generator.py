"""
Strategy Generator for MARK XLVIII / JARVIS.
Generates bounded execution strategies for a given objective or goal,
evaluating learned skills, standard workflows, and diagnostic paths.
Enforces a maximum candidate limit of 3 strategies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.skill_registry import skill_registry


class StrategyType(str, Enum):
    VERIFIED_SKILL = "VERIFIED_SKILL"
    STANDARD_WORKFLOW = "STANDARD_WORKFLOW"
    DIAGNOSTIC_FIRST = "DIAGNOSTIC_FIRST"
    DIRECT_EXECUTION = "DIRECT_EXECUTION"


@dataclass
class Strategy:
    strategy_id: str
    title: str
    description: str
    strategy_type: StrategyType
    required_steps: List[str]
    estimated_cost: str = "low"  # low, medium, high
    estimated_risk: str = "low"  # low, medium, high
    confidence: float = 0.90
    expected_success: float = 0.95
    required_approvals: bool = False
    reversibility: bool = True
    assumptions: List[str] = field(default_factory=list)
    skill_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "title": self.title,
            "description": self.description,
            "strategy_type": self.strategy_type.value,
            "required_steps": self.required_steps,
            "estimated_cost": self.estimated_cost,
            "estimated_risk": self.estimated_risk,
            "confidence": self.confidence,
            "expected_success": self.expected_success,
            "required_approvals": self.required_approvals,
            "reversibility": self.reversibility,
            "assumptions": self.assumptions,
            "skill_id": self.skill_id,
        }


class StrategyGenerator:
    """
    Produces candidate strategies for GoalContracts without executing any mutations.
    """

    MAX_CANDIDATES = 3

    def generate_strategies(
        self,
        objective: str,
        project_name: str = "FLOW",
        current_evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Strategy]:
        """
        Generates up to 3 candidate execution strategies for the objective.
        """
        strategies: List[Strategy] = []
        obj_lower = objective.lower()

        # 1. Strategy A: Check for verified learned skill
        skills = skill_registry.search_skills(query=objective, project_name=project_name)
        matching_skill = skills[0] if skills else None

        if matching_skill and matching_skill.is_executable():
            rate = matching_skill.success_count / max(1, matching_skill.success_count + matching_skill.failure_count)
            strategies.append(
                Strategy(
                    strategy_id=f"strat_skill_{uuid.uuid4().hex[:6]}",
                    title=f"Apply verified skill: {matching_skill.skill_name}",
                    description=f"Use learned workflow '{matching_skill.skill_name}' with success rate {rate:.0%}",
                    strategy_type=StrategyType.VERIFIED_SKILL,
                    required_steps=["Verify pre-conditions", f"Execute skill {matching_skill.skill_name}", "Verify outcome"],
                    confidence=0.98,
                    expected_success=0.96,
                    estimated_risk="low",
                    estimated_cost="low",
                    reversibility=True,
                    assumptions=[f"{project_name} matches skill environment"],
                    skill_id=matching_skill.skill_id,
                )
            )

        # 2. Strategy B: Standard Workflow / Direct Start
        if "run" in obj_lower or "start" in obj_lower:
            strategies.append(
                Strategy(
                    strategy_id=f"strat_std_{uuid.uuid4().hex[:6]}",
                    title=f"Standard project startup for {project_name}",
                    description=f"Profile framework and start {project_name} using detected dev server configuration",
                    strategy_type=StrategyType.STANDARD_WORKFLOW,
                    required_steps=[
                        f"Locate {project_name}",
                        f"Profile {project_name}",
                        f"Start server",
                        "Verify localhost",
                    ],
                    confidence=0.92,
                    expected_success=0.90,
                    estimated_risk="low",
                    estimated_cost="low",
                    reversibility=True,
                    assumptions=[f"{project_name} exists", "default port available"],
                )
            )

        # 3. Strategy C: Diagnostic First Workflow
        if "fix" in obj_lower or "repair" in obj_lower or not strategies:
            strategies.append(
                Strategy(
                    strategy_id=f"strat_diag_{uuid.uuid4().hex[:6]}",
                    title=f"Diagnostic-first investigation for {project_name}",
                    description=f"Collect logs, process states, and port usage before applying minimal repair",
                    strategy_type=StrategyType.DIAGNOSTIC_FIRST,
                    required_steps=[
                        "Inspect logs and processes",
                        "Rank diagnostic hypotheses",
                        "Execute targeted repair",
                        "Verify server reachability",
                    ],
                    confidence=0.88,
                    expected_success=0.92,
                    estimated_risk="low",
                    estimated_cost="medium",
                    reversibility=True,
                    assumptions=["diagnostics are observable"],
                )
            )

        return strategies[: self.MAX_CANDIDATES]


# Global singleton instance
strategy_generator = StrategyGenerator()
