"""
Mock Slack Connector for MARK XLVIII / FLOW.
Simulates channels, DMs, drafts, message search, and message dispatch.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from connectors.mock.base import BaseMockConnector


class MockSlackConnector(BaseMockConnector):
    def __init__(self):
        super().__init__("Slack")
        self.messages: List[Dict[str, Any]] = []
        self.drafts: List[Dict[str, Any]] = []

    def search_messages(self, query: str) -> List[Dict[str, Any]]:
        self._check_preconditions()
        q = query.lower()
        return [m for m in self.messages if q in m.get("message", "").lower() or q in m.get("recipient", "").lower()]

    def create_draft(self, recipient: str, message: str) -> Dict[str, Any]:
        self._check_preconditions()
        draft = {
            "draft_id": f"draft_{uuid.uuid4().hex[:8]}",
            "recipient": recipient,
            "message": message,
            "created_at": time.monotonic(),
        }
        self.drafts.append(draft)
        return {"success": True, "draft": draft}

    def send_message(self, recipient: str, message: str) -> Dict[str, Any]:
        self._check_preconditions()
        if self.simulate_false_success:
            # Tool claims success but no message is recorded in state store
            return {"success": True, "message_id": "msg_fake_12345", "delivered": False}

        msg = {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "recipient": recipient,
            "message": message,
            "sent_at": time.monotonic(),
            "delivered": True,
        }
        self.messages.append(msg)
        return {"success": True, "message_id": msg["message_id"], "delivered": True}

    def reset(self) -> None:
        super().reset()
        self.messages.clear()
        self.drafts.clear()


mock_slack = MockSlackConnector()
