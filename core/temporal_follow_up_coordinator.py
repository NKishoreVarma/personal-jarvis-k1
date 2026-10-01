"""
Temporal Follow-Up Coordinator for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Integrates temporal triggers with proactive opportunity detection and follow-up management.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from core.opportunity_detection_engine import opportunity_detection_engine
from core.proactive_opportunity_contract import (
    OpportunityType,
    ProactiveOpportunityContract,
    create_proactive_opportunity,
)
from core.temporal_contract import TemporalContract, TemporalState
from core.temporal_safety_gate import temporal_safety_gate
from core.temporal_scheduler import temporal_scheduler


class TemporalFollowUpCoordinator:
    """
    Coordinates clock-driven triggers, staleness re-checks, and opportunity formulation.
    """

    def process_due_temporal_events(
        self,
        current_time: Optional[float] = None,
    ) -> List[Tuple[TemporalContract, Optional[ProactiveOpportunityContract]]]:
        """
        Polls scheduler and formulates proactive follow-ups for due items.
        """
        now = current_time if current_time is not None else time.time()
        due_events = temporal_scheduler.poll_due_tasks(current_time=now)
        processed: List[Tuple[TemporalContract, Optional[ProactiveOpportunityContract]]] = []

        for contract, event_type in due_events:
            opp = None
            if event_type in ["TASK_DUE", "TASK_OVERDUE"]:
                opp = create_proactive_opportunity(
                    opportunity_type=OpportunityType.FOLLOW_UP,
                    title=f"Temporal Follow-Up: {contract.title}",
                    description=contract.description,
                    project_id=contract.project_id,
                    evidence_references=[f"temp:{contract.temporal_id}"],
                    confidence=0.95,
                    importance=contract.priority,
                    urgency=0.85 if event_type == "TASK_OVERDUE" else 0.65,
                )
            processed.append((contract, opp))

        return processed


# Global singleton instance
temporal_follow_up_coordinator = TemporalFollowUpCoordinator()
