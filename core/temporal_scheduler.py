"""
Temporal Scheduler for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Maintains persistent scheduled task state, prevents duplicate triggers, and manages crash recovery transitions.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

from core.temporal_contract import TemporalContract, TemporalState
from core.temporal_trigger_engine import temporal_trigger_engine


class TemporalScheduler:
    """
    Asynchronous coordinator for scheduled items and recurring obligations.
    """

    def __init__(self):
        self._schedules: Dict[str, TemporalContract] = {}
        self._triggered_history: Dict[str, List[float]] = {}

    def schedule_contract(self, contract: TemporalContract) -> None:
        self._schedules[contract.temporal_id] = contract

    def cancel_contract(self, temporal_id: str) -> bool:
        contract = self._schedules.get(temporal_id)
        if contract:
            contract.state = TemporalState.CANCELLED
            return True
        return False

    def pause_contract(self, temporal_id: str) -> bool:
        contract = self._schedules.get(temporal_id)
        if contract:
            contract.state = TemporalState.PAUSED
            return True
        return False

    def resume_contract(self, temporal_id: str) -> bool:
        contract = self._schedules.get(temporal_id)
        if contract:
            contract.state = TemporalState.SCHEDULED if contract.scheduled_at else TemporalState.PENDING
            return True
        return False

    def poll_due_tasks(self, current_time: Optional[float] = None) -> List[Tuple[TemporalContract, str]]:
        """
        Polls for due items while preventing duplicate triggers in the same second window.
        """
        now = current_time if current_time is not None else time.time()
        active_list = list(self._schedules.values())
        events = temporal_trigger_engine.evaluate_triggers(active_list, current_time=now)

        filtered_events = []
        for contract, event_name in events:
            # Check duplicate trigger prevention
            history = self._triggered_history.setdefault(contract.temporal_id, [])
            if not history or (now - history[-1] >= 1.0):
                history.append(now)
                filtered_events.append((contract, event_name))

        return filtered_events

    def get_contract(self, temporal_id: str) -> Optional[TemporalContract]:
        return self._schedules.get(temporal_id)

    def list_all(self) -> List[TemporalContract]:
        return list(self._schedules.values())

    def clear(self) -> None:
        self._schedules.clear()
        self._triggered_history.clear()


# Global singleton instance
temporal_scheduler = TemporalScheduler()
