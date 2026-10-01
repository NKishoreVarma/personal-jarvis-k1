"""
Recovery Decision Engine for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Evaluates current environmental reality against last verified checkpoints to compute safe recovery actions.
Enforces the hierarchy:
CURRENT VERIFIED OBSERVATION > LAST VERIFIED CHECKPOINT > PERSISTED EXECUTION STATE > HISTORICAL MEMORY.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.durable_task_contract import DurableTaskContract, DurableTaskStatus


class RecoveryDecision(str, Enum):
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    VERIFY_ONLY = "VERIFY_ONLY"
    SAFE_RESUME = "SAFE_RESUME"
    REPLAN_REQUIRED = "REPLAN_REQUIRED"
    USER_CONFIRMATION_REQUIRED = "USER_CONFIRMATION_REQUIRED"
    CANCEL_RECOVERY = "CANCEL_RECOVERY"


@dataclass
class RecoveryPlan:
    decision: RecoveryDecision
    durable_task_id: str
    goal_id: str
    project_scope: str
    rationale: str
    target_step_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "durable_task_id": self.durable_task_id,
            "goal_id": self.goal_id,
            "project_scope": self.project_scope,
            "rationale": self.rationale,
            "target_step_id": self.target_step_id,
            "parameters": self.parameters,
        }


class RecoveryDecisionEngine:
    """
    Computes deterministic, safety-first recovery actions based on live reality.
    """

    def decide_recovery_action(
        self,
        task: DurableTaskContract,
        live_observation: Dict[str, Any],
    ) -> RecoveryPlan:
        """
        Determines recovery course by prioritizing live observation over stale checkpoints.
        """
        # Case 0: Task was explicitly cancelled or completed prior
        if task.status == DurableTaskStatus.CANCELLED:
            return RecoveryPlan(
                decision=RecoveryDecision.CANCEL_RECOVERY,
                durable_task_id=task.durable_task_id,
                goal_id=task.goal_id,
                project_scope=task.project_scope,
                rationale="Task was cancelled by user prior to interruption.",
            )

        if task.status == DurableTaskStatus.COMPLETED:
            return RecoveryPlan(
                decision=RecoveryDecision.ALREADY_COMPLETED,
                durable_task_id=task.durable_task_id,
                goal_id=task.goal_id,
                project_scope=task.project_scope,
                rationale="Task was already marked completed in checkpoint.",
            )

        # Case A: Live observation confirms goal is already achieved
        is_process_running = live_observation.get("process_running", False)
        is_reachable = live_observation.get("reachable", False)
        port_conflict = live_observation.get("port_conflict", False)

        if is_process_running and is_reachable:
            return RecoveryPlan(
                decision=RecoveryDecision.ALREADY_COMPLETED,
                durable_task_id=task.durable_task_id,
                goal_id=task.goal_id,
                project_scope=task.project_scope,
                rationale=f"{task.project_scope} is already running and reachable on target port.",
                parameters={"port": live_observation.get("port", 3000)},
            )

        # Case B: Mutation may have succeeded or needs verification before retry
        if is_process_running and not is_reachable:
            return RecoveryPlan(
                decision=RecoveryDecision.VERIFY_ONLY,
                durable_task_id=task.durable_task_id,
                goal_id=task.goal_id,
                project_scope=task.project_scope,
                rationale=f"Process for {task.project_scope} is alive; verifying reachability before taking action.",
                parameters={"pid": live_observation.get("pid")},
            )

        # Case C: Environment changed (port conflict or broken dependencies)
        if port_conflict:
            return RecoveryPlan(
                decision=RecoveryDecision.REPLAN_REQUIRED,
                durable_task_id=task.durable_task_id,
                goal_id=task.goal_id,
                project_scope=task.project_scope,
                rationale="Observed port conflict in current environment; replanning required.",
            )

        # Case D: Safe to resume from last checkpoint
        completed_count = len(task.completed_steps)
        next_step = task.pending_steps[0] if task.pending_steps else None
        next_step_id = next_step.get("step_id") if isinstance(next_step, dict) else (next_step or "step_1")

        return RecoveryPlan(
            decision=RecoveryDecision.SAFE_RESUME,
            durable_task_id=task.durable_task_id,
            goal_id=task.goal_id,
            project_scope=task.project_scope,
            rationale=f"Resuming {task.project_scope} from step {next_step_id} (completed {completed_count} steps).",
            target_step_id=next_step_id,
        )


# Global singleton instance
recovery_decision_engine = RecoveryDecisionEngine()
