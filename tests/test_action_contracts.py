"""
Unit tests for Action Contract & Approval Manager in MARK XLVIII / FLOW.
Verifies contract data model, fingerprint binding, expiration, approval lifecycle, and human previews.
"""

import time
import unittest
from core.action_contract import ActionContract, ApprovalState, ExecutionState, RiskLevel
from core.approval_manager import ApprovalStore, approval_manager


class TestActionContracts(unittest.TestCase):
    def setUp(self):
        self.store = ApprovalStore()

    def tearDown(self):
        self.store.clear()

    # 1. Fingerprint is invariant to dictionary key order
    def test_fingerprint_invariance(self):
        c1 = ActionContract(
            connector="Slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "API outage"},
            risk_level=RiskLevel.HIGH_RISK,
        )
        c2 = ActionContract(
            connector="slack",
            operation="send_message",
            arguments={"message": "API outage", "recipient": "Rahul"},
            risk_level=RiskLevel.HIGH_RISK,
        )
        self.assertEqual(c1.fingerprint, c2.fingerprint)

    # 2. Risk level automatically triggers approval requirement for high_risk & destructive
    def test_risk_level_approval_trigger(self):
        c_read = ActionContract(connector="slack", operation="search", arguments={}, risk_level=RiskLevel.READ_ONLY)
        self.assertFalse(c_read.approval_required)
        self.assertEqual(c_read.approval_state, ApprovalState.NOT_REQUIRED)

        c_high = ActionContract(connector="slack", operation="send", arguments={}, risk_level=RiskLevel.HIGH_RISK)
        self.assertTrue(c_high.approval_required)
        self.assertEqual(c_high.approval_state, ApprovalState.PENDING_APPROVAL)

        c_dest = ActionContract(connector="github", operation="merge", arguments={}, risk_level=RiskLevel.DESTRUCTIVE)
        self.assertTrue(c_dest.approval_required)
        self.assertEqual(c_dest.approval_state, ApprovalState.PENDING_APPROVAL)

    # 3. Contract expiration
    def test_contract_expiration(self):
        contract = ActionContract(
            connector="slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Hello"},
            risk_level=RiskLevel.HIGH_RISK,
            expires_at=time.monotonic() - 1.0,  # in the past
        )
        self.assertTrue(contract.is_expired())
        self.assertEqual(contract.approval_state, ApprovalState.EXPIRED)

    # 4. ApprovalStore creates natural proposal preview
    def test_approval_store_create_proposal(self):
        contract = ActionContract(
            connector="slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Incident resolved."},
            evidence={"topic": "API outage incident"},
            risk_level=RiskLevel.HIGH_RISK,
        )
        saved_contract, preview = self.store.create_proposal(contract)
        self.assertIn("Rahul", preview)
        self.assertIn("Incident resolved", preview)
        self.assertIn("Would you like me to send it?", preview)

    # 5. ApprovalStore approves matching fingerprint
    def test_approval_store_approve_success(self):
        contract = ActionContract(
            connector="slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Deploying fix."},
            risk_level=RiskLevel.HIGH_RISK,
        )
        self.store.create_proposal(contract)
        
        ok, msg, approved_contract = self.store.approve_action(expected_fingerprint=contract.fingerprint)
        self.assertTrue(ok)
        self.assertEqual(approved_contract.approval_state, ApprovalState.APPROVED)

    # 6. ApprovalStore rejects argument changes after proposal
    def test_approval_store_fingerprint_mismatch_blocks(self):
        contract = ActionContract(
            connector="slack",
            operation="send_message",
            arguments={"recipient": "Rahul", "message": "Deploying fix."},
            risk_level=RiskLevel.HIGH_RISK,
        )
        self.store.create_proposal(contract)

        # User attempts to approve with a modified payload fingerprint
        tampered_fp = "different_hash_123"
        ok, msg, _ = self.store.approve_action(expected_fingerprint=tampered_fp)
        self.assertFalse(ok)
        self.assertIn("modified after proposal", msg)

    # 7. ApprovalStore rejects proposal cleanly
    def test_approval_store_reject(self):
        contract = ActionContract(
            connector="jira",
            operation="delete_issue",
            arguments={"issue_key": "PROJ-101"},
            risk_level=RiskLevel.DESTRUCTIVE,
        )
        self.store.create_proposal(contract)
        ok, msg = self.store.reject_action()
        self.assertTrue(ok)
        self.assertIn("rejected", msg)
        self.assertIsNone(self.store.get_pending_action())

    # 8. User approves with no pending action
    def test_approval_store_no_pending_action(self):
        ok, msg, _ = self.store.approve_action()
        self.assertFalse(ok)
        self.assertIn("no pending action", msg)


if __name__ == "__main__":
    unittest.main()
