"""
Time Context Engine for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Evaluates current time, relative horizons, elapsed time, remaining durations, and overdue status.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from core.temporal_contract import TemporalContract, TemporalState


class TimeContextEngine:
    """
    Computes real-time dynamic temporal context for scheduled items and deadlines.
    """

    def get_temporal_context(
        self,
        contract: TemporalContract,
        current_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Computes elapsed duration, remaining duration, and active status for a temporal contract.
        """
        now = current_time if current_time is not None else time.time()
        elapsed_seconds = max(0.0, now - contract.created_at)

        remaining_seconds = None
        target_time = contract.due_at or contract.scheduled_at
        if target_time:
            remaining_seconds = target_time - now

        is_overdue = contract.due_at is not None and now > contract.due_at
        is_expired = contract.expires_at is not None and now > contract.expires_at

        return {
            "temporal_id": contract.temporal_id,
            "current_time": now,
            "elapsed_seconds": round(elapsed_seconds, 2),
            "remaining_seconds": round(remaining_seconds, 2) if remaining_seconds is not None else None,
            "is_due": contract.is_due(current_time=now),
            "is_overdue": is_overdue,
            "is_expired": is_expired,
            "human_remaining": self.format_duration(remaining_seconds) if remaining_seconds is not None else "No deadline set",
        }

    def format_duration(self, seconds: Optional[float]) -> str:
        if seconds is None:
            return "Indefinite"
        if seconds < 0:
            abs_sec = abs(seconds)
            if abs_sec < 60:
                return f"{int(abs_sec)} seconds overdue"
            elif abs_sec < 3600:
                return f"{int(abs_sec // 60)} minutes overdue"
            else:
                return f"{int(abs_sec // 3600)} hours overdue"

        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            return f"{int(seconds // 60)} minutes"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours} hours {minutes} minutes" if minutes > 0 else f"{hours} hours"
        else:
            days = int(seconds // 86400)
            return f"{days} days"


# Global singleton instance
time_context_engine = TimeContextEngine()
