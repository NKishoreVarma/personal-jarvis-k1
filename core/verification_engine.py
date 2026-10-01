"""
Verification Engine for MARK XLVIII / JARVIS.
Enforces multi-tiered verification:
1. ACTION_VERIFIED: Subprocess or tool returned exit code 0.
2. STATE_VERIFIED: Process is actively listed and running in OS process table.
3. OUTCOME_VERIFIED: Real HTTP health check responds and test suite passes.
Only OUTCOME_VERIFIED permits GoalContract completion.
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Dict, Optional

from core.process_manager import process_manager


class VerificationLevel(str, Enum):
    ACTION_VERIFIED = "ACTION_VERIFIED"
    STATE_VERIFIED = "STATE_VERIFIED"
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"


class VerificationEngine:
    """
    Independently verifies actual environmental outcomes before claiming success.
    """

    def verify_action_success(self, action_result: Dict[str, Any]) -> bool:
        """Confirms tool or subprocess completed without errors."""
        return bool(action_result.get("success", False))

    def verify_process_state(self, project_name: str) -> bool:
        """Confirms that a process for the project is actively in the RUNNING state."""
        procs = process_manager.list_processes()
        proj_norm = project_name.strip().lower()
        for p in procs:
            if p.get("project_name", "").lower() == proj_norm and p.get("status") == "RUNNING":
                return True
        return False

    def verify_outcome(
        self,
        project_name: str,
        target_port: int = 3000,
        verify_tests: bool = False,
        test_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end outcome verification.
        Requires active process + verified HTTP socket reachability (+ optional passing tests).
        """
        # 1. State verification
        state_ok = self.verify_process_state(project_name)

        # 2. HTTP reachability verification
        http_ok = process_manager.verify_http(target_port, path="/", timeout=1.0)

        # 3. Tests verification (if requested)
        tests_ok = True
        if verify_tests:
            tests_ok = bool(test_results and test_results.get("success", False))

        is_outcome_verified = state_ok and http_ok and tests_ok

        return {
            "level": VerificationLevel.OUTCOME_VERIFIED if is_outcome_verified else VerificationLevel.STATE_VERIFIED if state_ok else VerificationLevel.ACTION_VERIFIED,
            "outcome_verified": is_outcome_verified,
            "state_verified": state_ok,
            "http_responsive": http_ok,
            "tests_passed": tests_ok if verify_tests else None,
            "port": target_port,
            "project": project_name,
        }


# Global singleton instance
verification_engine = VerificationEngine()
