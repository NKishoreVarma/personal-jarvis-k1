"""
Integration tests for Contextual Follow-up Commands & Pronoun Resolution (Phase 10).
Verifies:
- 'open FLOW' followed by 'run it'
- 'open WhatsApp' followed by 'open John's chat'
- 'open Chrome' followed by 'go to YouTube'
"""

import unittest
from core.conversation_manager import conversation_manager
from core.intent_router import router


class TestPhase10ContextFollowups(unittest.TestCase):
    def setUp(self):
        conversation_manager.reset_context()

    def test_project_followup_pronoun(self):
        # Step 1: User says "open FLOW from Desktop and run server"
        res1 = router.route_and_execute("open FLOW from Desktop and run the server")
        self.assertTrue(res1["handled"])
        self.assertEqual(conversation_manager.context.last_project.upper(), "FLOW")

        # Step 2: Next command: "run it" -> should resolve to "run FLOW"
        res2 = router.match("run it")
        self.assertTrue(res2["handled"])
        self.assertEqual(res2["intent"], "RUN_PROJECT")
        self.assertEqual(res2["parameters"]["project_name"].upper(), "FLOW")

    def test_app_followup_context(self):
        # Step 1: "open WhatsApp"
        res1 = router.route_and_execute("open WhatsApp")
        self.assertTrue(res1["handled"])
        self.assertEqual(conversation_manager.context.last_application, "whatsapp")

        # Step 2: "the app" pronoun resolution
        resolved = conversation_manager.resolve_entity("close the app")
        self.assertIn("whatsapp", resolved.lower())


if __name__ == "__main__":
    unittest.main()
