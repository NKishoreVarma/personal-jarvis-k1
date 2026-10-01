"""
Natural Progress Manager for MARK XLVIII / JARVIS.
Enforces extremely conservative progress notification rules:
- NEVER narrates internal pipeline steps (discovery, profiling, port sniffing).
- Emits at most ONE progress update if a task exceeds expected duration (>6.0s).
- Zero voice spam.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class MonitoredTask:
    task_id: str
    target_name: str
    started_at: float
    slow_threshold_sec: float
    progress_reported: bool = False


class NaturalProgressManager:
    """
    Monitors long-running tasks and triggers single, non-spammy progress updates if needed.
    """

    def __init__(self):
        self._tasks: Dict[str, MonitoredTask] = {}

    def register_task(
        self,
        task_id: str,
        target_name: str,
        slow_threshold_sec: float = 6.0,
    ) -> None:
        """Begins tracking a background task."""
        self._tasks[task_id] = MonitoredTask(
            task_id=task_id,
            target_name=target_name,
            started_at=time.monotonic(),
            slow_threshold_sec=slow_threshold_sec,
            progress_reported=False,
        )

    def check_progress_update(self, task_id: str) -> Optional[str]:
        """
        Returns a progress message if the task is taking longer than expected and hasn't yet reported progress.
        """
        task = self._tasks.get(task_id)
        if not task or task.progress_reported:
            return None

        elapsed = time.monotonic() - task.started_at
        if elapsed >= task.slow_threshold_sec:
            task.progress_reported = True
            return f"Still starting {task.target_name}."

        return None

    def mark_completed(self, task_id: str) -> None:
        """Removes task from monitoring."""
        self._tasks.pop(task_id, None)


# Global singleton instance
natural_progress_manager = NaturalProgressManager()
