"""
Temporal Priority Engine for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Ranks time-sensitive tasks based on urgency, deadline proximity, and goal alignment.
Enforces rule: Priority != Execution Authorization.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from core.temporal_contract import TemporalContract, TemporalState


class TemporalPriorityEngine:
    """
    Evaluates temporal priorities dynamically based on clock progress and deadline proximity.
    """

    def calculate_priority(
        self,
        contract: TemporalContract,
        current_time: Optional[float] = None,
    ) -> float:
        """
        Calculates dynamic temporal priority score [0.0 - 1.0].
        """
        now = current_time if current_time is not None else time.time()

        if contract.state in [TemporalState.COMPLETED, TemporalState.CANCELLED, TemporalState.PAUSED, TemporalState.EXPIRED]:
            return 0.0

        urgency = 0.50
        proximity = 0.50

        if contract.due_at:
            time_left = contract.due_at - now
            if time_left < 0:
                # Overdue! Maximize urgency
                urgency = 1.0
                proximity = 1.0
            elif time_left < 3600:  # < 1 hour
                urgency = 0.90
                proximity = 0.90
            elif time_left < 86400:  # < 1 day
                urgency = 0.70
                proximity = 0.70
            else:
                urgency = 0.40
                proximity = 0.30

        goal_alignment = 0.90 if contract.source_goal_id else 0.50

        raw_score = (
            0.30 * urgency
            + 0.20 * contract.priority
            + 0.15 * proximity
            + 0.15 * goal_alignment
            + 0.10 * 0.50  # Risk buffer
            + 0.10 * 0.90  # Evidence confidence
        )
        return max(0.0, min(1.0, raw_score))

    def rank_temporal_contracts(
        self,
        contracts: List[TemporalContract],
        current_time: Optional[float] = None,
    ) -> List[Tuple[TemporalContract, float]]:
        scored = [(c, self.calculate_priority(c, current_time=current_time)) for c in contracts if c.is_active()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# Global singleton instance
temporal_priority_engine = TemporalPriorityEngine()
