"""
Plan Adaptation Engine for MARK XLVIII / JARVIS.
Dynamically repairs and replans active execution graphs when observations contradict assumptions
or when steps fail, preserving verified completed work without full restarts.
Enforces invariant: PRESERVE VERIFIED WORK (No unnecessary restart of completed steps).
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from core.plan_contract import PlanContract, PlanStatus
from core.plan_step_contract import PlanStepContract, PlanStepStatus, create_plan_step_contract
from core.strategy_generator import strategy_generator
from core.strategy_selector import strategy_selector


class PlanAdaptationEngine:
    """
    Coordinates dynamic graph and step adaptation upon verification failure or environmental change.
    """

    def adapt_plan(
        self,
        plan: PlanContract,
        steps: List[PlanStepContract],
        failed_step_id: str,
        failure_reason: str,
        observed_conflicts: Optional[List[str]] = None,
    ) -> Tuple[PlanContract, List[PlanStepContract]]:
        """
        Adapts the plan by preserving completed steps, invalidating broken downstream branches,
        and inserting appropriate recovery/alternative steps.
        """
        plan.status = PlanStatus.ADAPTING
        plan.touch()

        completed_steps = [s for s in steps if s.status == PlanStepStatus.COMPLETED]
        preserved_step_ids = {s.step_id for s in completed_steps}

        # Mark failed step
        failed_step = next((s for s in steps if s.step_id == failed_step_id), None)
        if failed_step:
            failed_step.status = PlanStepStatus.FAILED
            failed_step.error = failure_reason

        # Invalidate remaining unexecuted steps
        for s in steps:
            if s.step_id not in preserved_step_ids and s.step_id != failed_step_id:
                s.status = PlanStepStatus.CANCELLED

        # Re-evaluate strategy with observed conflicts
        proj = plan.verification_criteria.get("project", "FLOW")
        conflicts = observed_conflicts or [failure_reason]
        candidate_strats = strategy_generator.generate_strategies(plan.objective, proj)
        new_strat, new_reason = strategy_selector.select_strategy(candidate_strats, observed_conflicts=conflicts)

        plan.strategy = f"Adapted: {new_strat.title if new_strat else 'Fallback repair'}"
        plan.selected_reason = f"Adapted after failure: {failure_reason}. {new_reason}"

        # Build recovery step(s) and re-link downstream
        last_completed_id = completed_steps[-1].step_id if completed_steps else None
        dep_list = [last_completed_id] if last_completed_id else []

        # Insert alternative repair/retry step
        rec_step = create_plan_step_contract(
            plan_id=plan.plan_id,
            goal_id=plan.goal_id,
            title=f"Adapted repair on {proj}",
            objective=f"Resolve '{failure_reason}' via alternate configuration",
            action_type="mutating",
            authority_required="EXECUTE_LOW_RISK",
            dependencies=dep_list,
        )

        verify_step = create_plan_step_contract(
            plan_id=plan.plan_id,
            goal_id=plan.goal_id,
            title=f"Verify adapted {proj} outcome",
            objective="Confirm service reachability after adaptation",
            action_type="verify",
            authority_required="READ_ONLY",
            dependencies=[rec_step.step_id],
        )

        adapted_step_list = completed_steps + [rec_step, verify_step]
        plan.estimated_steps = len(adapted_step_list)
        plan.status = PlanStatus.READY

        return plan, adapted_step_list


# Global singleton instance
plan_adaptation_engine = PlanAdaptationEngine()
