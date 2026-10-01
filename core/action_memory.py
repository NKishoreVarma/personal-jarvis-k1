"""
Short-Term Action Memory for MARK XLVIII / JARVIS.
Maintains bounded execution history (MAX_ACTION_HISTORY = 50) for natural queries:
'What did you just do?', 'Undo that', 'Try again', and 'Continue'.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ActionRecord:
    action_id: str
    task_id: str
    tool: str
    arguments: Dict[str, Any]
    status: str = "RUNNING"  # RUNNING | SUCCESS | FAILED
    is_reversible: bool = False
    undo_handler: Optional[Callable[..., Any]] = None
    started_at: float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None
    result_summary: Optional[str] = None


class ActionMemory:
    """
    In-memory, bounded short-term action memory store.
    """

    MAX_ACTION_HISTORY = 50

    def __init__(self):
        self._history: List[ActionRecord] = []

    def record_action(
        self,
        task_id: str,
        tool: str,
        arguments: Dict[str, Any],
        is_reversible: bool = False,
        undo_handler: Optional[Callable[..., Any]] = None,
    ) -> ActionRecord:
        """Records the beginning of a tool execution."""
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        record = ActionRecord(
            action_id=action_id,
            task_id=task_id,
            tool=tool,
            arguments=arguments,
            status="RUNNING",
            is_reversible=is_reversible,
            undo_handler=undo_handler,
        )
        self._history.append(record)
        if len(self._history) > self.MAX_ACTION_HISTORY:
            self._history.pop(0)

        print(f"[ACTION_MEMORY] Recorded {tool} (id={action_id})")
        return record

    def update_action(self, action_id: str, status: str, result_summary: Optional[str] = None) -> None:
        """Updates action outcome and completion timestamp."""
        for rec in reversed(self._history):
            if rec.action_id == action_id:
                rec.status = status
                rec.completed_at = time.monotonic()
                rec.result_summary = result_summary
                print(f"[ACTION_MEMORY] Action {action_id} -> {status}")
                break

    def get_recent_actions(self, limit: int = 5) -> List[ActionRecord]:
        return list(reversed(self._history[-limit:]))

    def find_last_successful_action(self) -> Optional[ActionRecord]:
        for rec in reversed(self._history):
            if rec.status == "SUCCESS":
                return rec
        return None

    def find_last_failed_action(self) -> Optional[ActionRecord]:
        for rec in reversed(self._history):
            if rec.status == "FAILED":
                return rec
        return None

    def undo_last_action(self) -> Dict[str, Any]:
        """
        Attempts to undo the most recent successful reversible action.
        """
        last_action = self.find_last_successful_action()
        if not last_action:
            return {"success": False, "message": "There are no recent actions to undo."}

        if not last_action.is_reversible or not last_action.undo_handler:
            return {
                "success": False,
                "message": f"Action '{last_action.tool}' cannot be safely undone automatically.",
            }

        try:
            undo_res = last_action.undo_handler(last_action.arguments)
            last_action.status = "UNDONE"
            print(f"[ACTION_MEMORY] Successfully undid action {last_action.action_id} ({last_action.tool})")
            return {
                "success": True,
                "action": last_action.tool,
                "message": f"Undid last action ({last_action.tool}).",
                "result": undo_res,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to undo action: {e}",
                "message": f"Undo failed for {last_action.tool}.",
            }

    def get_last_action_summary(self) -> str:
        """Produces natural language response for 'What did you just do?'."""
        last_action = self.find_last_successful_action()
        if not last_action:
            return "I haven't performed any actions yet."
        summary = last_action.result_summary or f"executed {last_action.tool}"
        return f"I just {summary}."

    def clear(self) -> None:
        self._history.clear()


action_memory = ActionMemory()
