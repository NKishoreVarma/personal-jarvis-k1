"""
Temporal Trigger Engine for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Detects state transitions (SCHEDULED -> DUE, DUE -> OVERDUE, ACTIVE -> EXPIRED).
Enforces rule: TRIGGER != EXECUTION (Triggers emit temporal notifications, never unauthorized mutations).
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from core.temporal_contract import TemporalContract, TemporalState


class TemporalTriggerEngine:
    """
    Evaluates temporal contracts against active clock time to detect state transitions.
    """

    def evaluate_triggers(
        self,
        contracts: List[TemporalContract],
        current_time: Optional[float] = None,
    ) -> List[Tuple[TemporalContract, str]]:
        """
        Scans contracts and updates their lifecycle states.
        Returns list of (contract, event_description).
        """
        now = current_time if current_time is not None else time.time()
        triggered_events: List[Tuple[TemporalContract, str]] = []

        for c in contracts:
            if not c.is_active():
                continue

            # Check expiration first
            if c.is_expired(current_time=now):
                c.state = TemporalState.EXPIRED
                triggered_events.append((c, "TASK_EXPIRED"))
                continue

            # Check overdue
            if c.is_overdue(current_time=now) and c.state != TemporalState.OVERDUE:
                c.state = TemporalState.OVERDUE
                c.last_triggered_at = now
                triggered_events.append((c, "TASK_OVERDUE"))
                continue

            # Check due
            if c.is_due(current_time=now) and c.state not in [TemporalState.DUE, TemporalState.OVERDUE]:
                c.state = TemporalState.DUE
                c.last_triggered_at = now
                triggered_events.append((c, "TASK_DUE"))
                continue

        return triggered_events


# Global singleton instance
temporal_trigger_engine = TemporalTriggerEngine()
