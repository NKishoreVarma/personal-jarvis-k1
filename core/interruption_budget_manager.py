"""
Interruption Budget Manager for MARK XLVIII / JARVIS.
Regulates the frequency and volume of proactive voice interventions to prevent user annoyance.
Tracks acceptance, decline, and silence rates to adaptively tune intervention thresholds.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class InterruptionBudgetManager:
    """
    Limits voice interruptions per goal and adapts proactive thresholds based on user feedback.
    """

    def __init__(self):
        self._goal_suggestion_counts: Dict[str, int] = {}  # goal_id -> count
        self._last_suggestion_time: float = 0.0
        self._min_interval_seconds: float = 15.0
        self._declined_patterns: Dict[str, float] = {}  # action_type -> last_declined_time
        self._accepted_count: int = 0
        self._declined_count: int = 0
        self.quiet_mode: bool = False

    def is_budget_available(self, goal_id: str, is_critical: bool = False) -> bool:
        """
        Evaluates whether an audible proactive suggestion is currently allowed.
        """
        if is_critical:
            return True

        if self.quiet_mode:
            return False

        # Check goal limit: max 1 proactive suggestion per goal
        count = self._goal_suggestion_counts.get(goal_id, 0)
        if count >= 1:
            return False

        # Check global time throttle
        if time.time() - self._last_suggestion_time < self._min_interval_seconds:
            return False

        return True

    def record_suggestion_issued(self, goal_id: str, action_type: str = "") -> None:
        """Records that a suggestion was made."""
        self._goal_suggestion_counts[goal_id] = self._goal_suggestion_counts.get(goal_id, 0) + 1
        self._last_suggestion_time = time.time()

    def record_outcome(self, action_type: str, accepted: bool) -> None:
        """Records user response to adapt future budgeting."""
        if accepted:
            self._accepted_count += 1
            self._declined_patterns.pop(action_type, None)
        else:
            self._declined_count += 1
            self._declined_patterns[action_type] = time.time()

    def is_action_suppressed(self, action_type: str, cooldown_seconds: float = 60.0) -> bool:
        """Checks if a specific action was recently declined."""
        last_declined = self._declined_patterns.get(action_type, 0.0)
        return (time.time() - last_declined) < cooldown_seconds

    def reset_goal_budget(self, goal_id: str) -> None:
        self._goal_suggestion_counts.pop(goal_id, None)

    def set_quiet_mode(self, enabled: bool) -> None:
        self.quiet_mode = enabled

    def clear_all(self) -> None:
        self._goal_suggestion_counts.clear()
        self._declined_patterns.clear()
        self._last_suggestion_time = 0.0
        self._accepted_count = 0
        self._declined_count = 0
        self.quiet_mode = False


# Global singleton instance
interruption_budget_manager = InterruptionBudgetManager()
