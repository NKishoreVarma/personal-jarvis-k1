"""
Plan Execution Controller for MARK XLVIII / JARVIS.
Coordinates asynchronous DAG execution of PlanContracts and PlanStepContracts.
Enforces dependency ordering, serializes mutations, triggers milestone emissions,
and invokes adaptation upon verification failure.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.cancellation_manager import cancellation_manager
from core.milestone_manager import MilestoneType, milestone_manager
from core.plan_adaptation_engine import plan_adaptation_engine
from core.plan_assumption_tracker import plan_assumption_tracker
from core.plan_contract import PlanContract, PlanStatus
from core.plan_graph_builder import plan_graph_builder
from core.plan_step_contract import PlanStepContract, PlanStepStatus


class PlanExecutionController:
    """
    Asynchronously executes, monitors, and adapts PlanStepContracts.
    """

    def __init__(self):
        self._active_plans: Dict[str, PlanContract] = {}  # goal_id -> PlanContract
        self._active_steps: Dict[str, List[PlanStepContract]] = {}  # goal_id -> list of steps
        self._step_executor: Optional[Callable[[PlanStepContract], Any]] = None

    def register_step_executor(self, executor: Callable[[PlanStepContract], Any]) -> None:
        self._step_executor = executor

    def start_plan(self, plan: PlanContract, steps: List[PlanStepContract]) -> None:
        """Registers and primes plan for execution."""
        plan.status = PlanStatus.EXECUTING
        plan.touch()
        self._active_plans[plan.goal_id] = plan
        self._active_steps[plan.goal_id] = steps

        # Update steps whose dependencies are empty to READY
        for s in steps:
            if not s.dependencies and s.status == PlanStepStatus.PENDING:
                s.status = PlanStepStatus.READY

    def get_ready_steps(self, goal_id: str) -> List[PlanStepContract]:
        """
        Returns list of steps whose dependencies are completely satisfied.
        """
        steps = self._active_steps.get(goal_id, [])
        completed_ids = {s.step_id for s in steps if s.status == PlanStepStatus.COMPLETED}

        ready: List[PlanStepContract] = []
        for s in steps:
            if s.status in [PlanStepStatus.PENDING, PlanStepStatus.READY]:
                if all(dep_id in completed_ids for dep_id in s.dependencies):
                    s.status = PlanStepStatus.READY
                    ready.append(s)
        return ready

    def mark_step_completed(
        self,
        goal_id: str,
        step_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Marks step complete and checks for subsequent ready steps or milestone events."""
        steps = self._active_steps.get(goal_id, [])
        step = next((s for s in steps if s.step_id == step_id), None)
        if step:
            step.status = PlanStepStatus.COMPLETED
            step.completed_at = time.time()
            step.result = result or {}

            # Record milestone if appropriate
            proj = self._active_plans.get(goal_id, None)
            proj_name = proj.verification_criteria.get("project", "FLOW") if proj else "FLOW"

            if "verify" in step.action_type:
                milestone_manager.record_milestone(
                    goal_id=goal_id,
                    milestone_type=MilestoneType.SERVER_REACHABLE,
                    description=f"{proj_name} reachability verified",
                )
            elif "repair" in step.title.lower():
                milestone_manager.record_milestone(
                    goal_id=goal_id,
                    milestone_type=MilestoneType.REPAIR_APPLIED,
                    description=f"Repair applied on {proj_name}",
                )

    def mark_step_failed(
        self,
        goal_id: str,
        step_id: str,
        error_message: str,
    ) -> Tuple[PlanContract, List[PlanStepContract]]:
        """Handles step failure by triggering dynamic plan adaptation."""
        plan = self._active_plans.get(goal_id)
        steps = self._active_steps.get(goal_id, [])
        if not plan:
            return PlanContract(goal_id, "", "", "", ""), []

        adapted_plan, adapted_steps = plan_adaptation_engine.adapt_plan(
            plan=plan,
            steps=steps,
            failed_step_id=step_id,
            failure_reason=error_message,
        )

        self._active_plans[goal_id] = adapted_plan
        self._active_steps[goal_id] = adapted_steps
        return adapted_plan, adapted_steps

    def is_plan_complete(self, goal_id: str) -> bool:
        """Checks if all critical steps in the plan have verified completion."""
        steps = self._active_steps.get(goal_id, [])
        if not steps:
            return False
        return all(s.status == PlanStepStatus.COMPLETED for s in steps if s.status != PlanStepStatus.SKIPPED)

    def get_plan(self, goal_id: str) -> Optional[PlanContract]:
        return self._active_plans.get(goal_id)

    def get_steps(self, goal_id: str) -> List[PlanStepContract]:
        return self._active_steps.get(goal_id, [])

    def pause_plan(self, goal_id: str) -> None:
        plan = self._active_plans.get(goal_id)
        if plan:
            plan.status = PlanStatus.PAUSED

    def resume_plan(self, goal_id: str) -> None:
        plan = self._active_plans.get(goal_id)
        if plan and plan.status == PlanStatus.PAUSED:
            plan.status = PlanStatus.EXECUTING

    def cancel_plan(self, goal_id: str) -> None:
        plan = self._active_plans.get(goal_id)
        if plan:
            plan.status = PlanStatus.CANCELLED
            cancellation_manager.cancel_active_goal(goal_id, reason="User cancelled plan")
            for s in self._active_steps.get(goal_id, []):
                if s.status in [PlanStepStatus.PENDING, PlanStepStatus.READY, PlanStepStatus.EXECUTING]:
                    s.status = PlanStepStatus.CANCELLED

    def clear_all(self) -> None:
        self._active_plans.clear()
        self._active_steps.clear()


# Global singleton instance
plan_execution_controller = PlanExecutionController()
