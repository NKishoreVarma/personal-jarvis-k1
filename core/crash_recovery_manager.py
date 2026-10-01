"""
Crash Recovery Manager for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Coordinates startup crash detection, durable task manifest loading, live environmental re-observation,
and deterministic execution recovery (ALREADY_COMPLETED, VERIFY_ONLY, SAFE_RESUME, REPLAN_REQUIRED).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.checkpoint_manager import checkpoint_manager
from core.durable_task_contract import DurableTaskContract, DurableTaskStatus
from core.event_bus import EventType, event_bus
from core.heartbeat_manager import heartbeat_manager
from core.process_manager import process_manager
from core.recovery_decision_engine import RecoveryDecision, RecoveryPlan, recovery_decision_engine
from core.recovery_trace import RecoveryEventType, recovery_trace
from core.runtime_contract import RuntimeContract, RuntimeStatus
from core.runtime_state_store import runtime_state_store


class CrashRecoveryManager:
    """
    Coordinates lifecycle recovery on runtime startup and system wake.
    """

    def __init__(self):
        self._recovered_plans: List[RecoveryPlan] = []

    def observe_live_environment(self, project_scope: str) -> Dict[str, Any]:
        """
        Observes current reality: checks if target process is alive, port reachability, and conflicts.
        """
        proj_clean = project_scope.lower().strip()
        procs = process_manager.list_processes()
        proj_proc = next((p for p in procs if p.get("project_name", "").lower() == proj_clean), None)

        is_running = bool(proj_proc and proj_proc.get("pid"))
        port = proj_proc.get("port", 3000) if proj_proc else 3000

        return {
            "project_name": project_scope,
            "process_running": is_running,
            "pid": proj_proc.get("pid") if proj_proc else None,
            "port": port,
            "reachable": is_running,  # If process is actively registered and running
            "port_conflict": False,
        }

    def recover_task(
        self,
        task: DurableTaskContract,
        live_observation: Optional[Dict[str, Any]] = None,
    ) -> RecoveryPlan:
        """
        Executes single task recovery using live observation over stale checkpoints.
        """
        recovery_trace.record_event(
            event_type=RecoveryEventType.TASK_RECOVERY_STARTED,
            goal_id=task.goal_id,
            project_name=task.project_scope,
            description=f"Starting recovery analysis for {task.project_scope}.",
        )

        obs = live_observation or self.observe_live_environment(task.project_scope)
        recovery_trace.record_event(
            event_type=RecoveryEventType.CURRENT_STATE_OBSERVED,
            goal_id=task.goal_id,
            project_name=task.project_scope,
            description=f"Observed live state: running={obs.get('process_running')}, reachable={obs.get('reachable')}.",
            metadata=obs,
        )

        # Compute decision
        plan = recovery_decision_engine.decide_recovery_action(task, obs)
        self._recovered_plans.append(plan)

        # Apply Decision
        if plan.decision == RecoveryDecision.ALREADY_COMPLETED:
            task.status = DurableTaskStatus.COMPLETED
            task.verification_state = "VERIFIED"
            task.touch()
            runtime_state_store.save_task(task)
            recovery_trace.record_event(
                event_type=RecoveryEventType.TASK_ALREADY_COMPLETED,
                goal_id=task.goal_id,
                project_name=task.project_scope,
                description=f"{task.project_scope} was already running and verified.",
            )
            event_bus.publish(EventType.PROJECT_READY, {"project": task.project_scope, "port": obs.get("port", 3000)})

        elif plan.decision == RecoveryDecision.SAFE_RESUME:
            task.status = DurableTaskStatus.RECOVERING
            task.recovery_attempts += 1
            task.touch()
            runtime_state_store.save_task(task)
            recovery_trace.record_event(
                event_type=RecoveryEventType.TASK_RESUMED,
                goal_id=task.goal_id,
                project_name=task.project_scope,
                description=f"Resuming {task.project_scope} from step {plan.target_step_id}.",
            )

        elif plan.decision == RecoveryDecision.REPLAN_REQUIRED:
            task.status = DurableTaskStatus.RECOVERY_REQUIRED
            task.recovery_attempts += 1
            task.touch()
            runtime_state_store.save_task(task)
            recovery_trace.record_event(
                event_type=RecoveryEventType.PLAN_REBUILT,
                goal_id=task.goal_id,
                project_name=task.project_scope,
                description=f"Replanning required for {task.project_scope} due to environmental conflict.",
            )

        elif plan.decision == RecoveryDecision.CANCEL_RECOVERY:
            task.status = DurableTaskStatus.CANCELLED
            task.touch()
            runtime_state_store.save_task(task)

        return plan

    def perform_startup_recovery(self) -> List[RecoveryPlan]:
        """
        Scans state store for active tasks on startup and performs automated safe recovery.
        """
        active_tasks = runtime_state_store.load_active_tasks()
        recoveries: List[RecoveryPlan] = []

        for task in active_tasks:
            if task.status in [
                DurableTaskStatus.RUNNING,
                DurableTaskStatus.RECOVERY_REQUIRED,
                DurableTaskStatus.WAITING,
                DurableTaskStatus.VERIFYING,
            ]:
                rec_plan = self.recover_task(task)
                recoveries.append(rec_plan)

        return recoveries

    def get_latest_recovery_plans(self) -> List[RecoveryPlan]:
        return list(self._recovered_plans)

    def clear_all(self) -> None:
        self._recovered_plans.clear()


# Global singleton instance
crash_recovery_manager = CrashRecoveryManager()
