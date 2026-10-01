"""
Staleness Detector for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Identifies expired health observations, stale verifications, and outdated memories.
Enforces rule: CURRENT VERIFIED OBSERVATION > TEMPORAL HISTORY.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.temporal_contract import TemporalContract, TemporalType, create_temporal_contract


class StalenessDetector:
    """
    Evaluates timestamps on observations, knowledge records, and verifications to flag stale assumptions.
    """

    def check_staleness(
        self,
        item_id: str,
        last_verified_at: Optional[float],
        staleness_threshold_seconds: float = 86400.0,  # 24 hours default
        current_time: Optional[float] = None,
        project_id: str = "GLOBAL",
    ) -> Optional[TemporalContract]:
        """
        Creates a STALE_CHECK temporal contract if the item exceeds its staleness threshold.
        """
        now = current_time if current_time is not None else time.time()

        if last_verified_at is None or (now - last_verified_at) > staleness_threshold_seconds:
            contract, _ = create_temporal_contract(
                title=f"Stale Verification: {item_id}",
                description=f"Item {item_id} has not been verified within {int(staleness_threshold_seconds)}s.",
                temporal_type=TemporalType.STALE_CHECK,
                project_id=project_id,
                priority=0.75,
                required_authority="READ_ONLY",
            )
            return contract

        return None


# Global singleton instance
staleness_detector = StalenessDetector()
