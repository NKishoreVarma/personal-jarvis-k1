"""
Recurrence Engine for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Computes next scheduled executions for recurring tasks and prevents runaway recursion loops.
"""

from __future__ import annotations

import re
import time
from typing import Optional

from core.temporal_contract import TemporalContract, TemporalState


class RecurrenceEngine:
    """
    Evaluates recurrence rules and computes the next eligible trigger timestamp.
    """

    def compute_next_recurrence(
        self,
        contract: TemporalContract,
        current_time: Optional[float] = None,
    ) -> Optional[float]:
        """
        Calculates next trigger timestamp based on contract.recurrence_rule.
        """
        if not contract.recurrence_rule:
            return None

        now = current_time if current_time is not None else time.time()
        rule = contract.recurrence_rule.strip().lower()

        # 1. interval:SECONDS
        if rule.startswith("interval:"):
            try:
                seconds = float(rule.split(":")[1])
                # Ensure minimum interval >= 10.0s to prevent runaway storms
                seconds = max(10.0, seconds)
                return now + seconds
            except Exception:
                return now + 3600.0

        # 2. daily -> +86400s
        if rule == "daily":
            return now + 86400.0

        # 3. weekly -> +604800s
        if rule == "weekly":
            return now + 604800.0

        # 4. monthly -> +2592000s (30 days)
        if rule == "monthly":
            return now + 2592000.0

        return now + 3600.0

    def advance_recurrence(
        self,
        contract: TemporalContract,
        current_time: Optional[float] = None,
    ) -> bool:
        """
        Advances the contract to its next scheduled cycle.
        """
        next_ts = self.compute_next_recurrence(contract, current_time=current_time)
        if next_ts:
            contract.scheduled_at = next_ts
            contract.next_trigger_at = next_ts
            contract.state = TemporalState.SCHEDULED
            contract.last_triggered_at = current_time if current_time is not None else time.time()
            return True
        return False


# Global singleton instance
recurrence_engine = RecurrenceEngine()
