"""
Clarification Manager for MARK XLVIII / JARVIS.
Handles ambiguous targets (e.g. 'John Smith' vs 'John Doe'), pauses execution cleanly,
and resumes the task from the exact blocked step once clarified by the user.
"""

from __future__ import annotations

import difflib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.conversation_manager import conversation_manager


@dataclass
class PendingClarification:
    clarification_id: str
    task_id: str
    question: str
    options: List[str]
    original_goal: str
    blocked_step_id: int = 1
    blocked_tool: str = ""
    context_params: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)


class ClarificationManager:
    """
    Manages pending disambiguation prompts and task resumption.
    """

    def __init__(self, conv_mgr=None):
        self._pending: Optional[PendingClarification] = None
        self.conv_mgr = conv_mgr or conversation_manager

    def create_clarification(
        self,
        task_id: str,
        question: str,
        options: List[str],
        original_goal: str,
        blocked_step_id: int = 1,
        blocked_tool: str = "",
        context_params: Optional[Dict[str, Any]] = None,
    ) -> PendingClarification:
        """Registers a clarification prompt and updates conversational state."""
        clarification_id = f"clar_{uuid.uuid4().hex[:8]}"
        self._pending = PendingClarification(
            clarification_id=clarification_id,
            task_id=task_id,
            question=question,
            options=options,
            original_goal=original_goal,
            blocked_step_id=blocked_step_id,
            blocked_tool=blocked_tool,
            context_params=context_params or {},
        )
        self.conv_mgr.set_pending_question(question, options)
        print(f"[CLARIFICATION] Task {task_id} paused for clarification: '{question}' (options: {options})")
        return self._pending

    def get_pending_clarification(self) -> Optional[PendingClarification]:
        return self._pending

    def resolve_clarification(self, user_choice: str) -> Dict[str, Any]:
        """
        Resolves the pending clarification using the user's choice and prepares task resumption.
        """
        if not self._pending:
            return {"resolved": False, "error": "No clarification is currently pending."}

        target = user_choice.strip().lower()
        matched_option = None

        # 1. Exact / Substring match against options
        for opt in self._pending.options:
            if target == opt.lower() or target in opt.lower() or opt.lower() in target:
                matched_option = opt
                break

        # 2. Fuzzy match
        if not matched_option:
            matches = difflib.get_close_matches(user_choice, self._pending.options, n=1, cutoff=0.6)
            if matches:
                matched_option = matches[0]

        if not matched_option:
            return {
                "resolved": False,
                "error": f"Choice '{user_choice}' does not match any of the available options: {self._pending.options}",
            }

        task_id = self._pending.task_id
        blocked_step = self._pending.blocked_step_id
        blocked_tool = self._pending.blocked_tool
        orig_goal = self._pending.original_goal

        # Update entity context with user choice
        self.conv_mgr.set_entity("contact", matched_option)
        self.conv_mgr.clear_pending_question()
        self._pending = None

        print(f"[CLARIFICATION] Resolved to '{matched_option}'. Resuming task {task_id} at step {blocked_step}.")
        return {
            "resolved": True,
            "selected_option": matched_option,
            "resumed_task_id": task_id,
            "blocked_step_id": blocked_step,
            "blocked_tool": blocked_tool,
            "original_goal": orig_goal,
            "message": f"Continuing with {matched_option}.",
        }

    def clear(self) -> None:
        self._pending = None
        self.conv_mgr.clear_pending_question()


clarification_manager = ClarificationManager()
