"""
Follow-Up Tracker for Proactive Task Orchestration in MARK XLVIII / JARVIS.
Maintains an intelligent queue of pending verifications, approvals, and recovery follow-ups without spamming.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FollowUpItem:
    follow_up_id: str
    title: str
    trigger_condition: str
    project_id: str = "GLOBAL"
    check_interval_seconds: float = 60.0
    last_checked: float = field(default_factory=time.time)
    next_eligible_check: float = 0.0
    suppressed: bool = False
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.next_eligible_check == 0.0:
            self.next_eligible_check = self.created_at + self.check_interval_seconds


class FollowUpTracker:
    """
    Manages rate-limited follow-up checks for background tasks and pending actions.
    """

    def __init__(self):
        self._follow_ups: Dict[str, FollowUpItem] = {}

    def register_follow_up(
        self,
        title: str,
        trigger_condition: str,
        project_id: str = "GLOBAL",
        check_interval_seconds: float = 60.0,
        ttl_seconds: float = 3600.0,
    ) -> FollowUpItem:
        now = time.time()
        item = FollowUpItem(
            follow_up_id=f"fu_{uuid.uuid4().hex[:8]}",
            title=title,
            trigger_condition=trigger_condition,
            project_id=project_id,
            check_interval_seconds=check_interval_seconds,
            expires_at=now + ttl_seconds,
        )
        self._follow_ups[item.follow_up_id] = item
        return item

    def get_pending_follow_ups(self, current_time: Optional[float] = None) -> List[FollowUpItem]:
        now = current_time if current_time is not None else time.time()
        ready = []
        for fu in list(self._follow_ups.values()):
            if not fu.suppressed:
                if fu.expires_at and now > fu.expires_at:
                    self._follow_ups.pop(fu.follow_up_id, None)
                    continue
                if now >= fu.next_eligible_check:
                    ready.append(fu)
                    fu.last_checked = now
                    fu.next_eligible_check = now + fu.check_interval_seconds
        return ready

    def clear(self) -> None:
        self._follow_ups.clear()


# Global singleton instance
follow_up_tracker = FollowUpTracker()
