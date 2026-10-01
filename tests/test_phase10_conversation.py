"""
Unit tests for Conversation Manager (Phase 10).
Verifies in-memory conversation context, entity setting, pronoun resolution, and state snapshots.
"""

import unittest
from core.conversation_manager import ConversationManager


class TestPhase10Conversation(unittest.TestCase):
    def setUp(self):
        self.mgr = ConversationManager()

    def test_set_and_get_active_goal(self):
        self.mgr.set_active_goal("Open WhatsApp and message John", task_id="task_123")
        self.assertEqual(self.mgr.get_active_goal(), "Open WhatsApp and message John")
        self.assertEqual(self.mgr.context.active_task_id, "task_123")

    def test_set_entities(self):
        self.mgr.set_entity("app", "WhatsApp")
        self.mgr.set_entity("contact", "John")
        self.mgr.set_entity("project", "FLOW")

        self.assertEqual(self.mgr.context.last_application, "WhatsApp")
        self.assertEqual(self.mgr.context.last_contact, "John")
        self.assertEqual(self.mgr.context.last_project, "FLOW")
        self.assertIn("WhatsApp", self.mgr.context.recent_entities)
        self.assertIn("FLOW", self.mgr.context.recent_entities)

    def test_resolve_entity_pronouns(self):
        self.mgr.set_entity("project", "FLOW")
        self.assertEqual(self.mgr.resolve_entity("run it"), "run FLOW")
        self.assertEqual(self.mgr.resolve_entity("start that"), "start FLOW")

        self.mgr.set_entity("contact", "John Doe")
        self.assertEqual(self.mgr.resolve_entity("message him"), "message John Doe")

    def test_pending_question_lifecycle(self):
        self.mgr.set_pending_question("Which John?", ["John Smith", "John Doe"])
        self.assertEqual(self.mgr.context.pending_question, "Which John?")
        self.assertEqual(len(self.mgr.context.pending_options), 2)

        self.mgr.clear_pending_question()
        self.assertIsNone(self.mgr.context.pending_question)
        self.assertEqual(len(self.mgr.context.pending_options), 0)

    def test_context_snapshot_and_reset(self):
        self.mgr.set_entity("app", "Spotify")
        snapshot = self.mgr.get_context_snapshot()
        self.assertEqual(snapshot["last_application"], "Spotify")

        self.mgr.reset_context()
        self.assertIsNone(self.mgr.context.last_application)


if __name__ == "__main__":
    unittest.main()
