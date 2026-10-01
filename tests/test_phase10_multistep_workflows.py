"""
Integration tests for Real-World Autonomous Multi-Step Workflows (Phase 10).
Verifies:
- WhatsApp message drafting with negative constraints ('but don't send')
- Multi-app project execution with browser dependency
- Immediate voice acknowledgement (< 50ms)
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from core.action_contract import ActionContract, ApprovalState, RiskLevel
from core.action_memory import action_memory
from core.approval_manager import ApprovalStore
from core.conversation_manager import conversation_manager
from core.execution_planner import execution_planner
from core.intent_router import router


class TestPhase10MultistepWorkflows(unittest.TestCase):
    def setUp(self):
        conversation_manager.reset_context()
        action_memory.clear()

    def test_01_whatsapp_draft_workflow_with_negative_constraint(self):
        cmd = "open WhatsApp, find John, write that I'll be late, but don't send it until I confirm"
        plan = execution_planner.plan_task(cmd)

        self.assertTrue(plan["is_multi_step"])
        self.assertTrue(plan["prohibit_send"])

        # Check step sequence
        steps = plan["steps"]
        self.assertEqual(steps[0]["tool"], "open_desktop_app")
        self.assertEqual(steps[1]["tool"], "open_whatsapp_chat")
        self.assertEqual(steps[2]["tool"], "execute_computer_action")
        self.assertTrue(steps[2].get("draft_only"))

        # Verify ActionContract creation for external send requirement
        contract = ActionContract(
            connector="whatsapp",
            operation="send_message",
            arguments={"recipient": "John", "message": "I'll be late"},
            risk_level=RiskLevel.HIGH_RISK,
        )
        self.assertEqual(contract.risk_level, RiskLevel.HIGH_RISK)
        self.assertTrue(contract.approval_required)
        self.assertEqual(contract.approval_state, ApprovalState.PENDING_APPROVAL)

    def test_02_multi_app_project_and_browser_workflow(self):
        cmd = "open FLOW from Desktop, run the server, and open it in Chrome when ready"
        plan = execution_planner.plan_task(cmd)

        self.assertTrue(plan["is_multi_step"])
        steps = plan["steps"]
        self.assertEqual(steps[0]["tool"], "run_project")
        self.assertEqual(steps[1]["tool"], "open_desktop_app")
        self.assertEqual(steps[0]["parameters"]["project_name"], "flow")

    def test_03_immediate_acknowledgement_latency(self):
        t0 = time.monotonic()
        res = router.route_and_execute("what did you just do")
        dt_ms = (time.monotonic() - t0) * 1000.0

        self.assertTrue(res["handled"])
        self.assertEqual(res["intent"], "WHAT_DID_YOU_DO")
        self.assertLess(dt_ms, 50.0)


if __name__ == "__main__":
    unittest.main()
