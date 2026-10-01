"""
Mock Calendar Connector for MARK XLVIII / FLOW.
Simulates schedule checking, meeting proposals, event booking, and cancellation.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from connectors.mock.base import BaseMockConnector


class MockCalendarConnector(BaseMockConnector):
    def __init__(self):
        super().__init__("Calendar")
        self.events: List[Dict[str, Any]] = []

    def get_events(self, time_min: str = "", time_max: str = "") -> List[Dict[str, Any]]:
        self._check_preconditions()
        return list(self.events)

    def create_event(self, title: str, time_str: str, attendees: Optional[List[str]] = None) -> Dict[str, Any]:
        self._check_preconditions()
        if self.simulate_false_success:
            return {"success": True, "event_id": "evt_fake_555", "booked": False}

        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:8]}",
            "title": title,
            "time": time_str,
            "attendees": attendees or [],
            "created_at": time.monotonic(),
            "booked": True,
        }
        self.events.append(event)
        return {"success": True, "event_id": event["event_id"], "event": event, "booked": True}

    def cancel_event(self, event_id: str) -> Dict[str, Any]:
        self._check_preconditions()
        for idx, ev in enumerate(self.events):
            if ev.get("event_id") == event_id:
                self.events.pop(idx)
                return {"success": True, "event_id": event_id, "cancelled": True}
        raise KeyError(f"Calendar event '{event_id}' not found.")

    def reset(self) -> None:
        super().reset()
        self.events.clear()


mock_calendar = MockCalendarConnector()
