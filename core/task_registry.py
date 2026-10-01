"""
Task Registry for MARK XLVIII / JARVIS.
Tracks active background agent tasks, progress statuses, associated process IDs,
and enables natural status querying ('What are you doing?') and clean task cancellation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.process_manager import process_manager


@dataclass
class TaskRecord:
    task_id: str
    goal: str
    status: str = "RUNNING"  # RUNNING | COMPLETED | FAILED | CANCELLED
    progress: str = "Initializing task"
    process_id: Optional[str] = None
    started_at: float = field(default_factory=time.monotonic)
    result: Optional[str] = None
    error: Optional[str] = None


class TaskRegistry:
    """
    Manages active and historical background tasks executed by JARVIS.
    """

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}
        self._latest_task_id: Optional[str] = None

    def register_task(self, goal: str, process_id: Optional[str] = None) -> str:
        """Registers a new active background task."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        record = TaskRecord(
            task_id=task_id,
            goal=goal,
            status="RUNNING",
            progress=f"Starting task: {goal}",
            process_id=process_id,
        )
        self._tasks[task_id] = record
        self._latest_task_id = task_id
        print(f"[TASK_REGISTRY] Registered task {task_id}: '{goal}'")
        return task_id

    def update_progress(self, task_id: str, progress: str, status: Optional[str] = None, process_id: Optional[str] = None) -> None:
        """Updates progress description and optional status."""
        record = self._tasks.get(task_id)
        if record:
            record.progress = progress
            if status:
                record.status = status
            if process_id:
                record.process_id = process_id
            print(f"[TASK_REGISTRY] [{task_id}] {progress}")

    def complete_task(self, task_id: str, result: str) -> None:
        """Marks a task as completed with final result message."""
        record = self._tasks.get(task_id)
        if record:
            record.status = "COMPLETED"
            record.progress = "Completed"
            record.result = result
            print(f"[TASK_REGISTRY] Completed task {task_id}: {result}")

    def fail_task(self, task_id: str, error: str) -> None:
        """Marks a task as failed."""
        record = self._tasks.get(task_id)
        if record:
            record.status = "FAILED"
            record.progress = f"Failed: {error}"
            record.error = error
            print(f"[TASK_REGISTRY] Failed task {task_id}: {error}")

    def cancel_task(self, task_id: Optional[str] = None) -> bool:
        """
        Cancels the active task, terminates its associated process if started by JARVIS,
        and cleans up resources.
        """
        target_id = task_id or self._latest_task_id
        if not target_id or target_id not in self._tasks:
            return False

        record = self._tasks[target_id]
        if record.status == "RUNNING":
            record.status = "CANCELLED"
            record.progress = "Cancelled by user"
            if record.process_id:
                process_manager.stop_process(record.process_id)
            print(f"[TASK_REGISTRY] Cancelled task {target_id}")
            return True
        return False

    def get_latest_active_task(self) -> Optional[TaskRecord]:
        """Returns the most recent active running task."""
        for t in reversed(list(self._tasks.values())):
            if t.status == "RUNNING":
                return t
        return None

    def get_active_task_summary(self) -> str:
        """
        Returns a concise, natural response explaining current background activity.
        """
        active = self.get_latest_active_task()
        if not active:
            return "I'm not currently running any background tasks."
        return f"I'm currently working on {active.goal.lower()}: {active.progress}."

    def clear(self) -> None:
        self._tasks.clear()
        self._latest_task_id = None


# Global singleton
task_registry = TaskRegistry()
