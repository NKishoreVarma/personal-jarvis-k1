"""
Goal Decomposition Engine for MARK XLVIII / JARVIS.
Transforms high-level user objectives into bounded, dependency-aware executable plan steps.
Enforces that decomposition is purely declarative and produces zero side-effects.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.plan_contract import PlanContract, PlanStatus, create_plan_contract
from core.plan_step_contract import PlanStepContract, create_plan_step_contract
from core.strategy_generator import Strategy, strategy_generator
from core.strategy_selector import strategy_selector


class GoalDecompositionEngine:
    """
    Decomposes GoalContracts into structured PlanContracts and dependency-wired PlanStepContracts.
    """

    def decompose_goal(
        self,
        goal_id: str,
        turn_id: str,
        objective: str,
        project_name: str = "FLOW",
        selected_strategy: Optional[Strategy] = None,
    ) -> Tuple[PlanContract, List[PlanStepContract]]:
        """
        Builds a PlanContract and discrete PlanStepContracts for the given goal.
        """
        obj_lower = objective.lower()

        if not selected_strategy:
            strats = strategy_generator.generate_strategies(objective, project_name)
            selected_strategy, reason = strategy_selector.select_strategy(strats)
        else:
            reason = selected_strategy.description

        strat_title = selected_strategy.title if selected_strategy else "Standard Decomposition"

        plan = create_plan_contract(
            goal_id=goal_id,
            turn_id=turn_id,
            objective=objective,
            strategy=strat_title,
            risk_level=selected_strategy.estimated_risk if selected_strategy else "low_risk",
            assumptions=selected_strategy.assumptions if selected_strategy else [f"{project_name} exists"],
            selected_reason=reason,
            verification_criteria={"project": project_name, "expected_port": 3000},
        )

        steps: List[PlanStepContract] = []

        # Scenario A: Fix + Run + Open Workflow
        if "fix" in obj_lower or "repair" in obj_lower:
            s1 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Inspect {project_name} logs and process",
                objective="Collect live error telemetry",
                action_type="read_only",
                authority_required="READ_ONLY",
            )
            s2 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Inspect port allocations for {project_name}",
                objective="Check port 3000 binding status",
                action_type="read_only",
                authority_required="READ_ONLY",
            )
            s3 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Apply targeted repair on {project_name}",
                objective="Resolve port conflict / configuration issue",
                action_type="mutating",
                authority_required="EXECUTE_LOW_RISK",
                dependencies=[s1.step_id, s2.step_id],
            )
            s4 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Start {project_name} server",
                objective="Launch development server",
                action_type="mutating",
                authority_required="EXECUTE_LOW_RISK",
                dependencies=[s3.step_id],
            )
            s5 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Verify {project_name} reachability",
                objective="Verify HTTP 200 on localhost:3000",
                action_type="verify",
                authority_required="READ_ONLY",
                dependencies=[s4.step_id],
            )
            steps.extend([s1, s2, s3, s4, s5])

            if "open" in obj_lower:
                s6 = create_plan_step_contract(
                    plan_id=plan.plan_id,
                    goal_id=goal_id,
                    title=f"Open {project_name} in browser",
                    objective="Launch browser to http://localhost:3000",
                    action_type="mutating",
                    authority_required="EXECUTE_LOW_RISK",
                    dependencies=[s5.step_id],
                )
                s7 = create_plan_step_contract(
                    plan_id=plan.plan_id,
                    goal_id=goal_id,
                    title="Verify final browser outcome",
                    objective="Confirm application UI is active",
                    action_type="verify",
                    authority_required="READ_ONLY",
                    dependencies=[s6.step_id],
                )
                steps.extend([s6, s7])

        # Scenario B: Run + Open Workflow
        elif "open" in obj_lower:
            s1 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Locate and profile {project_name}",
                objective="Detect project path and framework configuration",
                action_type="read_only",
                authority_required="READ_ONLY",
            )
            s2 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Start {project_name} server",
                objective="Launch development server",
                action_type="mutating",
                authority_required="EXECUTE_LOW_RISK",
                dependencies=[s1.step_id],
            )
            s3 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Verify {project_name} reachability",
                objective="Verify HTTP 200 on localhost:3000",
                action_type="verify",
                authority_required="READ_ONLY",
                dependencies=[s2.step_id],
            )
            s4 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Open {project_name} in browser",
                objective="Launch browser to http://localhost:3000",
                action_type="mutating",
                authority_required="EXECUTE_LOW_RISK",
                dependencies=[s3.step_id],
            )
            s5 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title="Verify final outcome",
                objective="Confirm complete execution",
                action_type="verify",
                authority_required="READ_ONLY",
                dependencies=[s4.step_id],
            )
            steps.extend([s1, s2, s3, s4, s5])

        # Scenario C: Standard Run Workflow
        else:
            s1 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Locate and profile {project_name}",
                objective="Detect project directory and scripts",
                action_type="read_only",
                authority_required="READ_ONLY",
            )
            s2 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Start {project_name} server",
                objective="Launch dev server command",
                action_type="mutating",
                authority_required="EXECUTE_LOW_RISK",
                dependencies=[s1.step_id],
            )
            s3 = create_plan_step_contract(
                plan_id=plan.plan_id,
                goal_id=goal_id,
                title=f"Verify {project_name} reachability",
                objective="Verify HTTP 200 on localhost",
                action_type="verify",
                authority_required="READ_ONLY",
                dependencies=[s2.step_id],
            )
            steps.extend([s1, s2, s3])

        plan.estimated_steps = len(steps)
        plan.status = PlanStatus.READY
        return plan, steps


# Global singleton instance
goal_decomposition_engine = GoalDecompositionEngine()
