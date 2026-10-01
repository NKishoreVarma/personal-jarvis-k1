"""
Deferred Task Manager for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Stores and restores postponed tasks and their associated goal contexts, evidence, and approval state.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from core.temporal_contract import (
    TemporalContract,
    TemporalState,
    TemporalType,
    create_temporal_contract,
)


class DeferredTaskManager:
    """
    Coordinates deferred work items and restores full operational context upon user request.
    """

    def __init__(self):
        self._deferred_tasks: Dict[str, TemporalContract] = {}

    def defer_task(
        self,
        title: str,
        description: str,
        source_goal_id: str = "",
        project_id: str = "GLOBAL",
        metadata: Optional[Dict] = None,
    ) -> Optional[TemporalContract]:
        contract, _ = create_temporal_contract(
            title=title,
            description=description,
            temporal_type=TemporalType.DEFERRED,
            source_goal_id=source_goal_id,
            project_id=project_id,
            metadata=metadata or {},
        )
        if contract:
            self._deferred_tasks[contract.temporal_id] = contract
        return contract

    def resume_task(self, temporal_id: str) -> Optional[TemporalContract]:
        contract = self._deferred_tasks.get(temporal_id)
        if contract and contract.state == TemporalState.DEFERRED:
            contract.state = TemporalState.ACTIVE
            return contract
        return None

    def get_latest_deferred(self, project_id: Optional[str] = None) -> Optional[TemporalContract]:
        active_deferred = [
            t for t in self._deferred_tasks.values()
            if t.state == TemporalState.DEFERRED and (not project_id or t.project_id.lower() == project_id.lower())
        ]
        if active_deferred:
            # Sort by created_at descending
            active_deferred.sort(key=lambda x: x.created_at, reverse=True)
            return active_deferred[0]
        return None

    def cancel_task(self, temporal_id: str) -> bool:
        contract = self._deferred_tasks.get(temporal_id)
        if contract:
            contract.state = TemporalState.CANCELLED
            return True
        return False

    def clear(self) -> None:
        self._deferred_tasks.clear()


# Global singleton instance
deferred_task_manager = DeferredTaskManager()
