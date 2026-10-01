"""
Mock Jira Connector for MARK XLVIII / FLOW.
Simulates issues, project workspaces, custom fields, and ticket operations.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from connectors.mock.base import BaseMockConnector


class MockJiraConnector(BaseMockConnector):
    def __init__(self):
        super().__init__("Jira")
        self.issues: Dict[str, Dict[str, Any]] = {}
        self._next_id: int = 101

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        self._check_preconditions()
        return self.issues.get(issue_key)

    def create_issue(self, project: str, summary: str, description: str = "", issue_type: str = "Bug") -> Dict[str, Any]:
        self._check_preconditions()
        key = f"{project.upper()}-{self._next_id}"
        self._next_id += 1

        if self.simulate_false_success:
            return {"success": True, "issue_key": key, "persisted": False}

        issue = {
            "key": key,
            "project": project.upper(),
            "summary": summary,
            "description": description,
            "type": issue_type,
            "status": "Open",
            "created_at": time.monotonic(),
        }
        self.issues[key] = issue
        return {"success": True, "issue_key": key, "issue": issue, "persisted": True}

    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        self._check_preconditions()
        if issue_key not in self.issues:
            raise KeyError(f"Jira issue '{issue_key}' does not exist.")
        self.issues[issue_key].update(fields)
        return {"success": True, "issue_key": issue_key, "updated_fields": fields}

    def delete_issue(self, issue_key: str) -> Dict[str, Any]:
        self._check_preconditions()
        if issue_key not in self.issues:
            raise KeyError(f"Jira issue '{issue_key}' does not exist.")
        self.issues.pop(issue_key)
        return {"success": True, "issue_key": issue_key, "deleted": True}

    def reset(self) -> None:
        super().reset()
        self.issues.clear()
        self._next_id = 101


mock_jira = MockJiraConnector()
