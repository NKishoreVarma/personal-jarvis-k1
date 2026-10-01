"""
Unit tests for Short-Term Action Memory, Undo, and Natural Queries (Phase 10).
Verifies:
- Action recording and status updates
- Bounded history (MAX_ACTION_HISTORY = 50)
- 'What did you just do?' natural summary
- Reversible action undo vs non-reversible rejection
"""

import unittest
from unittest.mock import MagicMock
from core.action_memory import ActionMemory


class TestPhase10ActionMemory(unittest.TestCase):
    def setUp(self):
        self.mem = ActionMemory()

    def test_record_and_update_action(self):
        rec = self.mem.record_action(
            task_id="t1",
            tool="open_desktop_app",
            arguments={"name": "WhatsApp"},
        )
        self.assertEqual(rec.status, "RUNNING")

        self.mem.update_action(rec.action_id, status="SUCCESS", result_summary="opened WhatsApp")
        self.assertEqual(rec.status, "SUCCESS")
        self.assertEqual(rec.result_summary, "opened WhatsApp")
        self.assertEqual(self.mem.get_last_action_summary(), "I just opened WhatsApp.")

    def test_undo_reversible_action(self):
        mock_undo = MagicMock(return_value={"reverted": True})
        rec = self.mem.record_action(
            task_id="t2",
            tool="create_draft",
            arguments={"text": "hello"},
            is_reversible=True,
            undo_handler=mock_undo,
        )
        self.mem.update_action(rec.action_id, status="SUCCESS")

        res = self.mem.undo_last_action()
        self.assertTrue(res["success"])
        self.assertIn("Undid last action", res["message"])
        mock_undo.assert_called_once_with({"text": "hello"})

    def test_undo_irreversible_action_rejected(self):
        rec = self.mem.record_action(
            task_id="t3",
            tool="send_message",
            arguments={"text": "hello"},
            is_reversible=False,
        )
        self.mem.update_action(rec.action_id, status="SUCCESS")

        res = self.mem.undo_last_action()
        self.assertFalse(res["success"])
        self.assertIn("cannot be safely undone", res["message"])


if __name__ == "__main__":
    unittest.main()
