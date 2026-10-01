"""
Mock GitHub Connector for MARK XLVIII / FLOW.
Simulates pull requests, reviews, safety checks, and controlled merges.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from connectors.mock.base import BaseMockConnector


class MockGitHubConnector(BaseMockConnector):
    def __init__(self):
        super().__init__("GitHub")
        self.prs: Dict[int, Dict[str, Any]] = {
            101: {
                "number": 101,
                "repo": "org/api-service",
                "title": "Fix memory leak in websocket listener",
                "state": "open",
                "ci_passed": True,
                "approved": True,
                "is_safe": True,
                "merged": False,
            },
            102: {
                "number": 102,
                "repo": "org/api-service",
                "title": "Refactor database migrations",
                "state": "open",
                "ci_passed": False,
                "approved": False,
                "is_safe": False,
                "merged": False,
            },
        }

    def list_prs(self, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        self._check_preconditions()
        return [pr for pr in self.prs.values() if pr.get("repo") == repo and pr.get("state") == state]

    def get_pr(self, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        self._check_preconditions()
        return self.prs.get(pr_number)

    def merge_pr(self, repo: str, pr_number: int, force: bool = False) -> Dict[str, Any]:
        self._check_preconditions()
        if pr_number not in self.prs:
            raise KeyError(f"Pull Request #{pr_number} does not exist in {repo}.")

        pr = self.prs[pr_number]
        if not force and not pr.get("is_safe", False):
            raise PermissionError(f"PR #{pr_number} cannot be automatically merged: CI failed or missing approvals.")

        if self.simulate_false_success:
            return {"success": True, "merged": False, "pr_number": pr_number}

        pr["state"] = "merged"
        pr["merged"] = True
        pr["merged_at"] = time.monotonic()
        return {"success": True, "merged": True, "pr_number": pr_number}

    def reset(self) -> None:
        super().reset()
        self.prs = {
            101: {
                "number": 101,
                "repo": "org/api-service",
                "title": "Fix memory leak in websocket listener",
                "state": "open",
                "ci_passed": True,
                "approved": True,
                "is_safe": True,
                "merged": False,
            },
            102: {
                "number": 102,
                "repo": "org/api-service",
                "title": "Refactor database migrations",
                "state": "open",
                "ci_passed": False,
                "approved": False,
                "is_safe": False,
                "merged": False,
            },
        }


mock_github = MockGitHubConnector()
