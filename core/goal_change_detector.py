"""
Goal Change Detector for MARK XLVIII / JARVIS.
Detects user mid-task goal pivots, contradictions, and explicit cancellations.
Coordinates invalidation of active plans, background tasks, and stale proactive suggestions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from core.cancellation_manager import cancellation_manager
from core.plan_contract import PlanContract, PlanStatus
from core.proactive_suggestion_manager import proactive_suggestion_manager


class GoalChangeDetector:
    """
    Detects goal shifts and cancellation utterances during active plan execution.
    """

    CANCEL_PATTERNS = [
        re.compile(r"^(stop|cancel|abort|never mind|terminate)$", re.IGNORECASE),
        re.compile(r"^(stop\s+(that|this|it|the\s+plan)|cancel\s+(the\s+plan|this))$", re.IGNORECASE),
    ]

    PIVOT_PATTERNS = [
        re.compile(r"^actually\s+(stop\s+([a-zA-Z0-9\._-]+)\s+and\s+)?(open|run|do)\s+([a-zA-Z0-9\._-]+)", re.IGNORECASE),
        re.compile(r"^instead(\s+of\s+that)?\s+(open|run|do)\s+([a-zA-Z0-9\._-]+)", re.IGNORECASE),
    ]

    def is_cancellation(self, utterance: str) -> bool:
        """Checks if utterance is an explicit cancellation request."""
        clean = utterance.strip()
        return any(p.search(clean) for p in self.CANCEL_PATTERNS)

    def detect_goal_pivot(
        self,
        utterance: str,
        active_plan: Optional[PlanContract] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Detects if utterance represents a pivot away from current active plan.
        Returns: (is_pivot, new_objective)
        """
        clean = utterance.strip()

        # Check explicit cancellation
        if self.is_cancellation(clean):
            return True, "CANCEL"

        # Check pivot regex
        for p in self.PIVOT_PATTERNS:
            match = p.search(clean)
            if match:
                return True, clean

        return False, None

    def handle_goal_change(
        self,
        new_objective: str,
        active_plan: Optional[PlanContract] = None,
    ) -> None:
        """
        Cancels active plan and purges stale suggestions and background work.
        """
        if active_plan:
            active_plan.status = PlanStatus.CANCELLED
            cancellation_manager.cancel_active_goal(active_plan.goal_id, reason=f"Goal changed to: {new_objective}")
            proj = active_plan.verification_criteria.get("project", "")
            if proj:
                proactive_suggestion_manager.invalidate_project_suggestions(proj)


# Global singleton instance
goal_change_detector = GoalChangeDetector()
