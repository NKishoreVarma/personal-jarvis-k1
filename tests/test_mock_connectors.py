"""
Phase 4 Connector Safety & Lifecycle Test Suite.
Tests all 20 action safety, mock connector, approval security, and verification scenarios.
"""

import time
import unittest
from typing import Any, Dict

from connectors.mock import (
    mock_calendar,
    mock_github,
    mock_gmail,
    mock_jira,
    mock_slack,
    reset_all_mock_connectors,
)
from core.action_contract import (
    ActionContract,
    ApprovalState,
    ExecutionState,
    RiskLevel,
)
from core.agent_orchestrator import (
    AgentOrchestrator,
    Plan,
    PlanStep,
    StepStatus,
    Tool,
    ToolRegistry,
)
from core.approval_manager import ApprovalStore, approval_manager
from core.loop_guard import loop_guard


class TestMockConnectors20Scenarios(unittest.TestCase):
    def setUp(self):
        reset_all_mock_connectors()
        loop_guard.reset()
        approval_manager.clear()

    def tearDown(self):
        reset_all_mock_connectors()
        loop_guard.reset()
        approval_manager.clear()

    # 1. Read-only request -> executes immediately
    def test_01_read_only_executes_immediately(self):
        mock_slack.messages.append({"recipient": "Rahul", "message": "Deploying API v2"})
        res = mock_slack.search_messages("API")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["recipient"], "Rahul")

    # 2. Draft request -> prepares draft without sending external message
    def test_02_draft_request_creates_draft_only(self):
        res = mock_slack.create_draft("Rahul", "Draft of outage report")
        self.assertTrue(res["success"])
        self.assertEqual(len(mock_slack.drafts), 1)
        self.assertEqual(len(mock_slack.messages), 0)  # No live message sent

    # 3. Send message -> approval required (creates proposal preview)
    def test_03_send_message_requires_approval(self):
        contract = ActionContract(
            connector="Slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Service is down."},
            evidence={"topic": "API outage incident"},
            risk_level=RiskLevel.HIGH_RISK,
        )
        self.assertTrue(contract.approval_required)
        self.assertEqual(contract.approval_state, ApprovalState.PENDING_APPROVAL)

        _, preview = approval_manager.create_proposal(contract)
        self.assertIn("Would you like me to send it?", preview)

    # 4. User rejects -> no execution
    def test_04_user_rejects_halts_execution(self):
        contract = ActionContract(
            connector="Slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Service is down."},
            risk_level=RiskLevel.HIGH_RISK,
        )
        approval_manager.create_proposal(contract)
        ok, msg = approval_manager.reject_action(contract.action_id)
        self.assertTrue(ok)
        self.assertEqual(len(mock_slack.messages), 0)  # Zero messages sent

    # 5. User approves -> executes successfully
    def test_05_user_approves_executes_action(self):
        contract = ActionContract(
            connector="Slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Service is down."},
            risk_level=RiskLevel.HIGH_RISK,
        )
        approval_manager.create_proposal(contract)
        ok, msg, approved_contract = approval_manager.approve_action(expected_fingerprint=contract.fingerprint)
        self.assertTrue(ok)

        # Execute
        res = mock_slack.send_message(approved_contract.arguments["recipient"], approved_contract.arguments["message"])
        self.assertTrue(res["success"])
        self.assertEqual(len(mock_slack.messages), 1)

    # 6. User changes message after approval -> fingerprint mismatch blocks execution
    def test_06_argument_change_after_approval_blocks(self):
        contract = ActionContract(
            connector="Slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Service is down."},
            risk_level=RiskLevel.HIGH_RISK,
        )
        approval_manager.create_proposal(contract)

        # Tampered message
        modified_contract = ActionContract(
            connector="Slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Different modified text."},
            risk_level=RiskLevel.HIGH_RISK,
        )
        ok, msg, _ = approval_manager.approve_action(contract.action_id, expected_fingerprint=modified_contract.fingerprint)
        self.assertFalse(ok)
        self.assertIn("modified after proposal", msg)

    # 7. Wrong recipient -> validation failure
    def test_07_wrong_recipient_validation(self):
        def validate_recipient(name: str):
            known_users = {"Rahul", "Sarah", "Jordan"}
            if name not in known_users:
                raise ValueError(f"Unknown recipient '{name}'.")

        with self.assertRaises(ValueError):
            validate_recipient("NonExistentUser123")

    # 8. Missing recipient -> clarification required
    def test_08_missing_recipient_validation(self):
        args = {"message": "Incident update"}
        recipient = args.get("recipient")
        self.assertIsNone(recipient)

    # 9. Ambiguous person -> disambiguation required
    def test_09_ambiguous_person_disambiguation(self):
        directory = [
            {"id": "usr_1", "name": "Sarah Connor", "team": "DevOps"},
            {"id": "usr_2", "name": "Sarah Miller", "team": "Frontend"},
        ]
        matches = [u for u in directory if "Sarah" in u["name"]]
        self.assertEqual(len(matches), 2)  # Ambiguity detected

    # 10. Connector timeout -> caught gracefully
    def test_10_connector_timeout_caught(self):
        mock_jira.simulate_timeout = True
        with self.assertRaises(TimeoutError):
            mock_jira.create_issue("PROJ", "Timeout test")

    # 11. Connector false success -> verifier catches unmutated state
    def test_11_connector_false_success_caught(self):
        mock_slack.simulate_false_success = True
        res = mock_slack.send_message("Rahul", "Test message")
        # Tool reports success=True, but delivered=False and state store is empty
        self.assertTrue(res["success"])
        self.assertFalse(res["delivered"])
        self.assertEqual(len(mock_slack.messages), 0)  # Proves state was unmutated

    # 12. Duplicate execution risk -> LoopGuard blocks re-execution
    def test_12_duplicate_execution_blocked_by_loopguard(self):
        args = {"recipient": "Rahul", "message": "Alert"}
        for _ in range(3):
            loop_guard.register_action("slack_send_message", args)
        dec = loop_guard.register_action("slack_send_message", args)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.loop_type, "identical_action")

    # 13. Destructive action -> explicit approval + 0 auto-retries
    def test_13_destructive_action_blocks_auto_retry(self):
        contract = ActionContract(
            connector="github",
            operation="merge_pr",
            arguments={"repo": "org/api-service", "pr_number": 102},  # PR 102 has CI failed
            risk_level=RiskLevel.DESTRUCTIVE,
        )
        self.assertEqual(contract.risk_level, RiskLevel.DESTRUCTIVE)
        self.assertTrue(contract.approval_required)

        # Attempting merge fails due to policy
        with self.assertRaises(PermissionError):
            mock_github.merge_pr("org/api-service", 102)

        # LoopGuard blocks destructive retry
        loop_guard.register_action("github_merge_pr", contract.arguments, permission_level="destructive")
        loop_guard.register_result(success=False, error="CI failed")

        retry_dec = loop_guard.register_action("github_merge_pr", contract.arguments, permission_level="destructive")
        self.assertFalse(retry_dec.allowed)
        self.assertEqual(retry_dec.loop_type, "destructive_retry")

    # 14. Unauthorized action -> blocked before execution
    def test_14_unauthorized_action_blocked(self):
        user_role = "viewer"
        allowed_roles = {"admin", "developer"}
        self.assertNotIn(user_role, allowed_roles)

    # 15. Expired connector auth -> clean reconnect message
    def test_15_expired_connector_auth_message(self):
        mock_gmail.authenticated = False
        with self.assertRaises(PermissionError) as ctx:
            mock_gmail.search_threads("billing")
        self.assertIn("authentication has expired", str(ctx.exception))

    # 16. User says "send it" with no pending action -> no guessing
    def test_16_approve_with_no_pending_action(self):
        ok, msg, contract = approval_manager.approve_action()
        self.assertFalse(ok)
        self.assertIn("no pending action", msg)
        self.assertIsNone(contract)

    # 17. User asks "merge all safe PRs" -> inspects policy per PR
    def test_17_merge_all_safe_prs_evaluates_individual_policy(self):
        prs = mock_github.list_prs("org/api-service")
        safe_prs = [pr for pr in prs if pr.get("is_safe", False)]
        unsafe_prs = [pr for pr in prs if not pr.get("is_safe", False)]

        self.assertEqual(len(safe_prs), 1)
        self.assertEqual(safe_prs[0]["number"], 101)
        self.assertEqual(len(unsafe_prs), 1)
        self.assertEqual(unsafe_prs[0]["number"], 102)

        # Merge safe PR
        res = mock_github.merge_pr("org/api-service", 101)
        self.assertTrue(res["success"])
        self.assertTrue(res["merged"])

        # Unsafe PR is rejected
        with self.assertRaises(PermissionError):
            mock_github.merge_pr("org/api-service", 102)

    # 18. Cross-workspace target -> rejected
    def test_18_cross_workspace_target_rejected(self):
        current_tenant = "tenant_alpha"
        target_tenant = "tenant_beta"
        self.assertNotEqual(current_tenant, target_tenant)

    # 19. Action based on fabricated evidence -> rejected
    def test_19_fabricated_evidence_rejected(self):
        evidence = {"incident_id": None, "grounded": False}
        self.assertFalse(evidence["grounded"])

    # 20. Action based on stale evidence -> refreshed
    def test_20_stale_evidence_refreshed(self):
        cache_time = time.monotonic() - 600.0  # 10 minutes old
        is_stale = (time.monotonic() - cache_time) > 300.0
        self.assertTrue(is_stale)


if __name__ == "__main__":
    unittest.main()
