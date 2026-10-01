"""
Unit tests for Phase 2 Reasoning Core — ThinkTool.
Tests scratchpad note creation, category validation, note length limits, history bounding, and ToolRegistry integration.
"""

import unittest
from core.think_tool import ThinkTool, think_tool, think
from core.agent_orchestrator import ToolRegistry


class TestPhase2ThinkTool(unittest.TestCase):
    def setUp(self):
        self.tt = ThinkTool()

    # 1. Planning note creation
    def test_planning_note_creation(self):
        res = self.tt.think("Analyze project structure and package.json", category="planning")
        self.assertTrue(res.success)
        self.assertEqual(res.category, "planning")
        self.assertEqual(res.note, "Analyze project structure and package.json")

    # 2. Observation note creation
    def test_observation_note_creation(self):
        res = self.tt.think("Screen capture shows terminal active on port 3000", category="observation")
        self.assertTrue(res.success)
        self.assertEqual(res.category, "observation")

    # 3. Recovery note creation
    def test_recovery_note_creation(self):
        res = self.tt.think("Port already in use; inspect next available port", category="recovery")
        self.assertTrue(res.success)
        self.assertEqual(res.category, "recovery")

    # 4. Verification note creation
    def test_verification_note_creation(self):
        res = self.tt.think("HTTP 200 OK received from localhost", category="verification")
        self.assertTrue(res.success)
        self.assertEqual(res.category, "verification")

    # 5. Invalid category defaults to planning
    def test_invalid_category_defaults_to_planning(self):
        res = self.tt.think("Custom thought", category="arbitrary_unknown")
        self.assertEqual(res.category, "planning")

    # 6. Maximum note length enforced
    def test_max_note_length_enforced(self):
        long_note = "A" * 700
        res = self.tt.think(long_note, category="planning")
        self.assertLessEqual(len(res.note), self.tt.MAX_NOTE_LENGTH + 3)
        self.assertTrue(res.note.endswith("..."))

    # 7. Maximum history capacity enforced
    def test_max_history_enforced(self):
        for i in range(70):
            self.tt.think(f"Thought note {i}", category="planning")
        history = self.tt.get_history()
        self.assertEqual(len(history), self.tt.MAX_HISTORY)
        self.assertEqual(history[-1].note, "Thought note 69")

    # 8. History filtering by category
    def test_history_filtering_by_category(self):
        self.tt.think("Plan 1", category="planning")
        self.tt.think("Obs 1", category="observation")
        self.tt.think("Plan 2", category="planning")
        self.tt.think("Rec 1", category="recovery")

        plans = self.tt.get_history(category="planning")
        self.assertEqual(len(plans), 2)
        obs = self.tt.get_history(category="observation")
        self.assertEqual(len(obs), 1)

    # 9. Clear resets history
    def test_clear_resets_history(self):
        self.tt.think("Note 1")
        self.tt.think("Note 2")
        self.assertEqual(len(self.tt.get_history()), 2)
        self.tt.clear()
        self.assertEqual(len(self.tt.get_history()), 0)

    # 10. ToolRegistry integration executes without side effects
    def test_tool_registry_think_execution(self):
        reg = ToolRegistry()
        think_tool_obj = reg.get("think")
        self.assertIsNotNone(think_tool_obj)
        self.assertEqual(think_tool_obj.permission_level, "read_only")

        res = think_tool_obj.execute({"note": "Orchestrator reasoning step", "category": "planning"})
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("note"), "Orchestrator reasoning step")


if __name__ == "__main__":
    unittest.main()
