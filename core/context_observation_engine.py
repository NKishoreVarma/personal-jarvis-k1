"""
Context Observation Engine for MARK XLVIII / JARVIS.
Aggregates and normalizes operational context across active goals, verified processes,
shared multi-agent evidence, task registries, and screen perception.
Enforces the priority invariant:
CURRENT VERIFIED OBSERVATION > ACTIVE GOAL STATE > CURRENT TASK CONTEXT > RELEVANT LONG-TERM MEMORY > PREDICTION.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.context_contract import ContextContract, ContextTaskState, create_context_contract
from core.event_bus import EventType, event_bus
from core.memory_service import memory_service
from core.process_manager import process_manager
from core.screen_perception_manager import screen_perception_manager
from core.shared_evidence_store import EvidenceCategory, shared_evidence_store


class ContextObservationEngine:
    """
    Synthesizes real-time operational context while respecting observational hierarchy.
    """

    def __init__(self):
        self._active_contexts: Dict[str, ContextContract] = {}  # project_name -> ContextContract
        self._event_listeners_registered = False
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        if not self._event_listeners_registered:
            event_bus.subscribe(EventType.PROJECT_READY, self._on_project_ready)
            event_bus.subscribe(EventType.TASK_COMPLETED, self._on_task_completed)
            event_bus.subscribe(EventType.TASK_FAILED, self._on_task_failed)
            self._event_listeners_registered = True

    def _on_project_ready(self, event: Any) -> None:
        payload = event.payload if hasattr(event, "payload") else (event if isinstance(event, dict) else {})
        proj = payload.get("project", "FLOW")
        port = payload.get("port", 3000)
        self.update_project_context(
            project_name=proj,
            task_state=ContextTaskState.RUNNING,
            recent_action={"action": "server_started", "port": port, "verified": True},
        )

    def _on_task_completed(self, event: Any) -> None:
        payload = event.payload if hasattr(event, "payload") else (event if isinstance(event, dict) else {})
        task_id = payload.get("task_id", "")
        # Update corresponding context if found
        for ctx in self._active_contexts.values():
            if ctx.goal_id == task_id or ctx.turn_id == task_id:
                ctx.task_state = ContextTaskState.COMPLETED

    def _on_task_failed(self, event: Any) -> None:
        payload = event.payload if hasattr(event, "payload") else (event if isinstance(event, dict) else {})
        task_id = payload.get("task_id", "")
        for ctx in self._active_contexts.values():
            if ctx.goal_id == task_id or ctx.turn_id == task_id:
                ctx.task_state = ContextTaskState.FAILED

    def observe_context(
        self,
        turn_id: str,
        goal_id: str,
        project_name: str = "FLOW",
        active_application: str = "",
        explicit_task: str = "",
        force_fresh: bool = False,
    ) -> ContextContract:
        """
        Gathers verified operational snapshot for project/goal.
        """
        proj_key = project_name.lower().strip()
        existing = self._active_contexts.get(proj_key)
        if existing and not existing.is_expired() and not force_fresh:
            return existing

        # 1. Inspect live process state (Priority #1: CURRENT VERIFIED OBSERVATION)
        procs = process_manager.list_processes()
        proj_proc = next((p for p in procs if p.get("project_name", "").lower() == proj_key), None)

        task_state = ContextTaskState.IDLE
        recent_actions: List[Dict[str, Any]] = []

        if proj_proc:
            task_state = ContextTaskState.RUNNING
            recent_actions.append({
                "action": "process_running",
                "pid": proj_proc.get("pid"),
                "port": proj_proc.get("port", 3000),
                "timestamp": time.time(),
            })

        # 2. Inspect SharedEvidenceStore
        ev_records = shared_evidence_store.get_evidence(goal_id) if goal_id else []
        ev_summaries = [r.to_dict() for r in ev_records]

        # 3. Retrieve Relevant Long-Term Memory (Priority #4)
        memories = memory_service.retrieve(query=project_name, project_scope=project_name)
        mem_summaries = [m.to_dict() for m in memories[:2]]

        # 4. Check active ScreenPerception context
        vis_ctx = screen_perception_manager.get_context(turn_id)
        vis_data = vis_ctx.to_dict() if vis_ctx else {}

        contract = create_context_contract(
            turn_id=turn_id,
            goal_id=goal_id,
            active_project=project_name,
            active_application=active_application,
            active_task=explicit_task or (f"Running {project_name}" if proj_proc else f"Inspect {project_name}"),
            task_state=task_state,
            visible_context=vis_data,
            recent_verified_actions=recent_actions,
            ttl_seconds=60.0,
            confidence=0.98 if proj_proc else 0.90,
        )
        contract.source_evidence = ev_summaries + [{"type": "memory", "data": mem_summaries}]

        self._active_contexts[proj_key] = contract
        return contract

    def update_project_context(
        self,
        project_name: str,
        task_state: ContextTaskState,
        recent_action: Optional[Dict[str, Any]] = None,
    ) -> ContextContract:
        """Updates or creates context for project."""
        proj_key = project_name.lower().strip()
        ctx = self._active_contexts.get(proj_key)
        if not ctx or ctx.is_expired():
            ctx = create_context_contract(
                turn_id=f"turn_{int(time.time())}",
                goal_id=f"goal_{proj_key}",
                active_project=project_name,
                task_state=task_state,
            )
            self._active_contexts[proj_key] = ctx

        ctx.task_state = task_state
        if recent_action:
            ctx.recent_verified_actions.append(recent_action)
        return ctx

    def clear_project_context(self, project_name: str) -> None:
        self._active_contexts.pop(project_name.lower().strip(), None)

    def clear_all(self) -> None:
        self._active_contexts.clear()


# Global singleton instance
context_observation_engine = ContextObservationEngine()
