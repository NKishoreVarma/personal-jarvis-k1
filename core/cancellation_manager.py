"""
Cancellation Manager for MARK XLVIII / JARVIS.
Coordinates top-down cancellation from user commands through parent goals, task graphs,
worker tasks, background execution, and audio queues.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from core.event_bus import EventType, event_bus
from core.parallel_worker_manager import parallel_worker_manager
from core.task_graph import TaskGraph


class CancellationManager:
    """
    Manages active goal cancellation and cascading worker termination.
    """

    def __init__(self):
        self._active_graphs: Dict[str, TaskGraph] = {}
        self._cancelled_goals: set[str] = set()

    def register_active_goal(self, goal_id: str, graph: TaskGraph) -> None:
        self._active_graphs[goal_id] = graph

    def unregister_goal(self, goal_id: str) -> None:
        self._active_graphs.pop(goal_id, None)

    def is_cancelled(self, goal_id: str) -> bool:
        return goal_id in self._cancelled_goals

    def cancel_active_goal(self, goal_id: Optional[str] = None, reason: str = "User cancelled") -> int:
        """
        Cascades cancellation to target goal or all active goals.
        Returns count of cancelled goals.
        """
        targets = [goal_id] if goal_id else list(self._active_graphs.keys())
        cancelled_count = 0

        for gid in targets:
            if not gid:
                continue
            self._cancelled_goals.add(gid)

            # 1. Cancel graph nodes
            graph = self._active_graphs.get(gid)
            if graph:
                graph.propagate_cancellation(reason=reason)

            # 2. Cancel active parallel workers
            parallel_worker_manager.cancel_all_for_goal(gid, reason=reason)

            # 3. Publish cancellation event to suppress audio/completion
            event_bus.publish(EventType.TASK_CANCELLED, {"goal_id": gid, "reason": reason})
            cancelled_count += 1
            print(f"[CANCELLATION_MANAGER] 🛑 Goal '{gid}' cancelled ({reason}).")

        return cancelled_count

    def clear(self) -> None:
        self._active_graphs.clear()
        self._cancelled_goals.clear()


# Global singleton instance
cancellation_manager = CancellationManager()
