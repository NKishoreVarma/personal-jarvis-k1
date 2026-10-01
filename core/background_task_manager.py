"""
Background Task Manager for MARK XLVIII / JARVIS.
Provides asynchronous, non-blocking background task management, bounded timeouts,
fingerprint deduplication, task dependencies, state transitions, and event bus publishing.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.event_bus import EventType, event_bus


class TaskState(str, Enum):
    PENDING = "PENDING"
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    TIMED_OUT = "TIMED_OUT"


@dataclass
class BackgroundTask:
    task_id: str
    name: str
    description: str = ""
    status: TaskState = TaskState.PENDING
    timeout: float = 15.0
    progress: float = 0.0
    created_at: float = field(default_factory=time.monotonic)
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None
    duration: float = 0.0
    error: Optional[str] = None
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    fingerprint: Optional[str] = None
    depends_on: Optional[str] = None
    dependency_condition: str = "SUCCESS"
    asyncio_task: Optional[asyncio.Task] = None


class BackgroundTaskManager:
    """
    Authoritative background task executor for MARK XLVIII / JARVIS.
    """

    MAX_HISTORY = 50

    def __init__(self):
        self._tasks: Dict[str, BackgroundTask] = {}
        self._name_to_id: Dict[str, str] = {}
        self._fingerprints: Dict[str, str] = {}  # fingerprint -> task_id

    def start_background_task(
        self,
        name: str,
        coro: Any,
        timeout: float = 15.0,
        description: str = "",
        fingerprint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        depends_on: Optional[str] = None,
        condition: str = "SUCCESS",
        on_complete: Optional[Callable[[Any], Any]] = None,
        on_error: Optional[Callable[[Exception], Any]] = None,
    ) -> str:
        """
        Starts an asynchronous background task with deduplication, dependencies, and timeout protection.
        Returns the unique task_id.
        """
        # 1. Deduplication via fingerprint
        if fingerprint:
            existing_id = self._fingerprints.get(fingerprint)
            if existing_id and existing_id in self._tasks:
                existing = self._tasks[existing_id]
                if existing.status in (TaskState.PENDING, TaskState.WAITING, TaskState.RUNNING):
                    print(f"[BACKGROUND] Reusing existing duplicate task {existing_id} (fp={fingerprint})")
                    return existing_id

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        bg_task = BackgroundTask(
            task_id=task_id,
            name=name,
            description=description,
            timeout=timeout,
            fingerprint=fingerprint,
            metadata=metadata or {},
            depends_on=depends_on,
            dependency_condition=condition,
            status=TaskState.WAITING if depends_on else TaskState.PENDING,
        )

        self._tasks[task_id] = bg_task
        self._name_to_id[name] = task_id
        if fingerprint:
            self._fingerprints[fingerprint] = task_id

        async def _runner():
            # Handle dependency wait if configured
            if bg_task.depends_on:
                dep_task_id = bg_task.depends_on
                print(f"[BACKGROUND] Task {task_id} WAITING on dependency {dep_task_id} ({condition})")
                while True:
                    dep = self._tasks.get(dep_task_id)
                    if not dep:
                        break
                    if dep.status in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMEOUT, TaskState.TIMED_OUT):
                        if condition == "SUCCESS" and dep.status != TaskState.COMPLETED:
                            bg_task.status = TaskState.FAILED
                            bg_task.error = f"Dependency task {dep_task_id} did not complete successfully."
                            event_bus.publish(EventType.TASK_FAILED, {"task_id": task_id, "name": name, "error": bg_task.error})
                            return None
                        break
                    await asyncio.sleep(0.05)

            bg_task.status = TaskState.RUNNING
            bg_task.start_time = time.monotonic()
            print(f"[BACKGROUND] START {name} (id={task_id}, timeout={timeout}s)")
            event_bus.publish(EventType.TASK_STARTED, {"task_id": task_id, "name": name, "metadata": bg_task.metadata})

            try:
                res = await asyncio.wait_for(coro, timeout=timeout)
                bg_task.end_time = time.monotonic()
                bg_task.duration = bg_task.end_time - bg_task.start_time
                bg_task.status = TaskState.COMPLETED
                bg_task.result = res
                bg_task.progress = 1.0
                print(f"[BACKGROUND] COMPLETE {name} {bg_task.duration:.2f}s")
                event_bus.publish(EventType.TASK_COMPLETED, {"task_id": task_id, "name": name, "result": res, "duration": bg_task.duration})

                if on_complete:
                    try:
                        if asyncio.iscoroutinefunction(on_complete):
                            await on_complete(res)
                        else:
                            on_complete(res)
                    except Exception as cb_err:
                        print(f"[BACKGROUND] on_complete callback error for {name}: {cb_err}")
                return res

            except asyncio.TimeoutError:
                bg_task.end_time = time.monotonic()
                bg_task.duration = bg_task.end_time - bg_task.start_time
                bg_task.status = TaskState.TIMEOUT
                bg_task.error = f"Operation timed out after {timeout}s"
                print(f"[BACKGROUND] TIMEOUT {name} (exceeded {timeout}s)")
                event_bus.publish(EventType.LONG_TASK_TIMEOUT, {"task_id": task_id, "name": name, "timeout": timeout})
                if on_error:
                    try:
                        err = TimeoutError(f"Task '{name}' exceeded timeout of {timeout}s")
                        if asyncio.iscoroutinefunction(on_error):
                            await on_error(err)
                        else:
                            on_error(err)
                    except Exception:
                        pass

            except asyncio.CancelledError:
                bg_task.end_time = time.monotonic()
                bg_task.duration = bg_task.end_time - bg_task.start_time
                bg_task.status = TaskState.CANCELLED
                print(f"[BACKGROUND] CANCELLED {name}")
                event_bus.publish(EventType.TASK_CANCELLED, {"task_id": task_id, "name": name})
                raise

            except Exception as e:
                bg_task.end_time = time.monotonic()
                bg_task.duration = bg_task.end_time - bg_task.start_time
                bg_task.status = TaskState.FAILED
                bg_task.error = str(e)
                print(f"[BACKGROUND] FAILED {name} error: {e}")
                event_bus.publish(EventType.TASK_FAILED, {"task_id": task_id, "name": name, "error": str(e)})
                if on_error:
                    try:
                        if asyncio.iscoroutinefunction(on_error):
                            await on_error(e)
                        else:
                            on_error(e)
                    except Exception:
                        pass

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(_runner())
            bg_task.asyncio_task = task
        except RuntimeError:
            pass

        self.cleanup_completed_tasks()
        return task_id

    # Backward compatibility with Phase 8 submit()
    def submit(
        self,
        name: str,
        coro: Any,
        timeout: float = 15.0,
        on_complete: Optional[Callable[[Any], Any]] = None,
        on_error: Optional[Callable[[Exception], Any]] = None,
    ) -> asyncio.Task:
        task_id = self.start_background_task(
            name=name,
            coro=coro,
            timeout=timeout,
            on_complete=on_complete,
            on_error=on_error,
        )
        bg_task = self._tasks.get(task_id)
        if bg_task and bg_task.asyncio_task:
            return bg_task.asyncio_task
        # If no loop was active
        return asyncio.create_task(asyncio.sleep(0))

    def update_task_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> None:
        """Updates numeric progress (0.0 to 1.0) and publishes progress event."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskState.RUNNING:
            task.progress = min(max(progress, 0.0), 1.0)
            event_bus.publish(EventType.TASK_PROGRESS, {"task_id": task_id, "progress": task.progress, "message": message})

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Returns structured dictionary of task status."""
        task = self._tasks.get(task_id)
        if not task:
            # Fallback by name lookup
            task_id_by_name = self._name_to_id.get(task_id)
            if task_id_by_name:
                task = self._tasks.get(task_id_by_name)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value,
            "progress": task.progress,
            "duration": task.duration,
            "error": task.error,
            "result": task.result,
            "metadata": task.metadata,
        }

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """Returns all currently running or waiting tasks."""
        active = []
        for t in self._tasks.values():
            if t.status in (TaskState.PENDING, TaskState.WAITING, TaskState.RUNNING):
                active.append({
                    "task_id": t.task_id,
                    "name": t.name,
                    "status": t.status.value,
                    "progress": t.progress,
                    "description": t.description,
                })
        return active

    def cancel_task(self, task_id: str) -> bool:
        """Cancels a specific task by task_id or name."""
        task = self._tasks.get(task_id)
        if not task:
            task_id_by_name = self._name_to_id.get(task_id)
            if task_id_by_name:
                task = self._tasks.get(task_id_by_name)

        if task and task.asyncio_task and not task.asyncio_task.done():
            task.asyncio_task.cancel()
            task.status = TaskState.CANCELLED
            return True
        return False

    def cancel(self, name: str) -> bool:
        return self.cancel_task(name)

    def cancel_all(self) -> int:
        count = 0
        for task_id in list(self._tasks.keys()):
            if self.cancel_task(task_id):
                count += 1
        return count

    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Asynchronously awaits task completion."""
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found")
        if task.asyncio_task:
            return await asyncio.wait_for(task.asyncio_task, timeout=timeout)
        return task.result

    def cleanup_completed_tasks(self, max_history: int = 50) -> int:
        """Maintains bounded completed task history."""
        completed_ids = [
            k for k, t in self._tasks.items()
            if t.status in (TaskState.COMPLETED, TaskState.FAILED, TaskState.TIMEOUT, TaskState.TIMED_OUT, TaskState.CANCELLED)
        ]
        excess = len(completed_ids) - max_history
        removed = 0
        if excess > 0:
            for k in completed_ids[:excess]:
                if self._tasks[k].fingerprint:
                    self._fingerprints.pop(self._tasks[k].fingerprint, None)
                del self._tasks[k]
                removed += 1
        return removed

    def get_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Backward-compatible status dictionary."""
        if name:
            st = self.get_task_status(name)
            return st or {}
        return {k: self.get_task_status(k) for k in self._tasks}

    def cleanup_finished(self) -> int:
        return self.cleanup_completed_tasks(max_history=0)


# Global singleton instance
background_task_manager = BackgroundTaskManager()
