"""
Unit tests for Clarification Manager & Ambiguity Handling (Phase 10).
Verifies:
- Ambiguous contacts (John Smith vs John Doe) pause task and create PendingClarification.
- User choice resolves clarification and resumes blocked step.
"""

import unittest
from core.clarification_manager import ClarificationManager
from core.conversation_manager import ConversationManager


class TestPhase10Clarifications(unittest.TestCase):
    def setUp(self):
        self.conv_mgr = ConversationManager()
        self.clar_mgr = ClarificationManager(conv_mgr=self.conv_mgr)

    def test_create_and_resolve_clarification(self):
        # 1. Create clarification
        pending = self.clar_mgr.create_clarification(
            task_id="task_999",
            question="I found John Smith and John Doe. Which one do you mean?",
            options=["John Smith", "John Doe"],
            original_goal="Open chat with John",
            blocked_step_id=2,
            blocked_tool="open_whatsapp_chat",
        )

        self.assertIsNotNone(self.clar_mgr.get_pending_clarification())
        self.assertEqual(self.conv_mgr.context.pending_question, "I found John Smith and John Doe. Which one do you mean?")

        # 2. User selects "John Smith"
        res = self.clar_mgr.resolve_clarification("John Smith")
        self.assertTrue(res["resolved"])
        self.assertEqual(res["selected_option"], "John Smith")
        self.assertEqual(res["resumed_task_id"], "task_999")
        self.assertEqual(res["blocked_step_id"], 2)
        self.assertEqual(self.conv_mgr.context.last_contact, "John Smith")
        self.assertIsNone(self.clar_mgr.get_pending_clarification())


if __name__ == "__main__":
    unittest.main()
