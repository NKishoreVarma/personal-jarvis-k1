"""
Background Task Supervisor for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Supervises background worker lifecycles, classifies tasks into durability tiers
(EPHEMERAL, RECOVERABLE, PERSISTENT, NON_RECOVERABLE), and manages orphan cleanup.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class TaskClass(str, Enum):
    EPHEMERAL = "EPHEMERAL"
    RECOVERABLE = "RECOVERABLE"
    PERSISTENT = "PERSISTENT"
    NON_RECOVERABLE = "NON_RECOVERABLE"


@dataclass
class SupervisedTask:
    task_id: str
    name: str
    task_class: TaskClass
    owner_runtime_id: str
    target_project: str
    started_at: float = field(default_factory=time.time)
    last_pulse_at: float = field(default_factory=time.time)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_class": self.task_class.value,
            "owner_runtime_id": self.owner_runtime_id,
            "target_project": self.target_project,
            "started_at": self.started_at,
            "last_pulse_at": self.last_pulse_at,
            "is_active": self.is_active,
        }


class BackgroundTaskSupervisor:
    """
    Supervises background async workers and orchestrates safe post-crash reconnects.
    """

    def __init__(self):
        self._tasks: Dict[str, SupervisedTask] = {}  # task_id -> SupervisedTask

    def register_task(
        self,
        name: str,
        task_class: TaskClass,
        owner_runtime_id: str,
        target_project: str = "FLOW",
    ) -> SupervisedTask:
        """Registers a newly spawned background worker."""
        task_id = f"bg_{uuid.uuid4().hex[:8]}"
        task = SupervisedTask(
            task_id=task_id,
            name=name,
            task_class=task_class,
            owner_runtime_id=owner_runtime_id,
            target_project=target_project,
        )
        self._tasks[task_id] = task
        return task

    def pulse_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.last_pulse_at = time.time()

    def complete_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.is_active = False

    def list_recoverable_tasks(self) -> List[SupervisedTask]:
        """Returns tasks eligible for post-crash reconnect or resumption."""
        return [
            t for t in self._tasks.values()
            if t.is_active and t.task_class in [TaskClass.RECOVERABLE, TaskClass.PERSISTENT]
        ]

    def cleanup_orphaned_tasks(self, active_runtime_id: str) -> int:
        """Marks orphaned tasks from dead runtimes as inactive."""
        count = 0
        for task in self._tasks.values():
            if task.is_active and task.owner_runtime_id != active_runtime_id:
                if task.task_class == TaskClass.EPHEMERAL:
                    task.is_active = False
                    count += 1
        return count

    def clear_all(self) -> None:
        self._tasks.clear()


# Global singleton instance
background_task_supervisor = BackgroundTaskSupervisor()
