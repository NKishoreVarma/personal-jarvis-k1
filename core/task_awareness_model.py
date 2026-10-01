"""
Task Awareness Model for MARK XLVIII / JARVIS.
Tracks execution states across applications, servers, and background tasks.
Maps technical internal stages to clean, user-visible state without technical leak.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from core.process_manager import process_manager
from core.task_registry import task_registry


class TaskState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ALREADY_COMPLETE = "ALREADY_COMPLETE"


class TaskAwarenessModel:
    """
    Evaluates runtime system state to prevent duplicate operations and format clean user-facing status.
    """

    def is_task_running(self, target: str) -> bool:
        """Checks if a project or process with the given target name is actively running."""
        procs = process_manager.list_processes()
        target_norm = target.strip().lower()
        for p in procs:
            if p.get("project_name", "").lower() == target_norm and p.get("status") == "RUNNING":
                return True
        return False

    def is_duplicate_request(self, task_type: str, target: str) -> bool:
        """
        Determines if the requested operation is already actively running.
        """
        if task_type in ("RUN_PROJECT", "PROJECT_OPERATION"):
            return self.is_task_running(target)
        return False

    def get_current_state(self, task_id: Optional[str] = None, target: Optional[str] = None) -> TaskState:
        """Retrieves high-level lifecycle state for a task or process."""
        if task_id:
            task_info = task_registry.get_task(task_id)
            if task_info:
                status = task_info.get("status", "")
                if status == "RUNNING":
                    return TaskState.RUNNING
                elif status == "COMPLETED":
                    return TaskState.COMPLETED
                elif status == "FAILED":
                    return TaskState.FAILED
                elif status == "CANCELLED":
                    return TaskState.CANCELLED

        if target and self.is_task_running(target):
            return TaskState.RUNNING

        return TaskState.NOT_STARTED

    def get_user_visible_state(
        self,
        task_type: str,
        target: str,
        internal_stage: Optional[str] = None,
    ) -> str:
        """
        Masks internal pipeline steps (DISCOVERING_PROJECT, PROFILING_FRAMEWORK, etc.)
        behind natural user-visible descriptions.
        """
        target_clean = target.strip() if target else "Task"

        if task_type in ("RUN_PROJECT", "PROJECT_OPERATION"):
            return f"Starting {target_clean}."

        if task_type in ("OPEN_APP", "LAUNCH_APP"):
            return f"Opening {target_clean}."

        if task_type in ("CLOSE_APP", "QUIT_APP"):
            return f"Closing {target_clean}."

        return f"Working on {target_clean}."


# Global singleton instance
task_awareness_model = TaskAwarenessModel()
