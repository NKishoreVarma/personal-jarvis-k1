"""
Mock Gmail Connector for MARK XLVIII / FLOW.
Simulates thread search, draft preparation, and email dispatch.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from connectors.mock.base import BaseMockConnector


class MockGmailConnector(BaseMockConnector):
    def __init__(self):
        super().__init__("Gmail")
        self.sent_emails: List[Dict[str, Any]] = []
        self.drafts: List[Dict[str, Any]] = []

    def search_threads(self, query: str) -> List[Dict[str, Any]]:
        self._check_preconditions()
        q = query.lower()
        return [e for e in self.sent_emails if q in e.get("subject", "").lower() or q in e.get("to", "").lower()]

    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        self._check_preconditions()
        draft = {
            "draft_id": f"draft_{uuid.uuid4().hex[:8]}",
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": time.monotonic(),
        }
        self.drafts.append(draft)
        return {"success": True, "draft": draft}

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        self._check_preconditions()
        if self.simulate_false_success:
            return {"success": True, "message_id": "email_fake_999", "delivered": False}

        email = {
            "message_id": f"email_{uuid.uuid4().hex[:8]}",
            "to": to,
            "subject": subject,
            "body": body,
            "sent_at": time.monotonic(),
            "delivered": True,
        }
        self.sent_emails.append(email)
        return {"success": True, "message_id": email["message_id"], "delivered": True}

    def reset(self) -> None:
        super().reset()
        self.sent_emails.clear()
        self.drafts.clear()


mock_gmail = MockGmailConnector()
