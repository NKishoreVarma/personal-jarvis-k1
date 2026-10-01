"""
Unit tests for Task Decomposer (Phase 10).
Verifies sequential dependency parsing ('then', 'after', 'once') and negative constraint preservation ('but don't send').
"""

import unittest
from core.task_decomposer import TaskDecomposer


class TestPhase10TaskDecomposition(unittest.TestCase):
    def setUp(self):
        self.decomposer = TaskDecomposer()

    def test_decompose_simple_single_step(self):
        res = self.decomposer.decompose("open Chrome")
        self.assertFalse(res["is_multi_step"])
        self.assertEqual(len(res["steps"]), 1)
        self.assertEqual(res["steps"][0]["tool"], "open_desktop_app")

    def test_decompose_whatsapp_multi_step_with_negative_constraint(self):
        cmd = "open WhatsApp, find John, write that I'll be late, but don't send it until I confirm"
        res = self.decomposer.decompose(cmd)

        self.assertTrue(res["is_multi_step"])
        self.assertTrue(res["prohibit_send"])
        self.assertIn("PROHIBIT_AUTO_SEND", res["constraints"])
        self.assertGreaterEqual(len(res["steps"]), 3)

        tools = [s["tool"] for s in res["steps"]]
        self.assertIn("open_desktop_app", tools)
        self.assertIn("open_whatsapp_chat", tools)
        self.assertIn("execute_computer_action", tools)

    def test_decompose_project_and_browser_dependency(self):
        cmd = "open FLOW from Desktop, run the server, and open it in Chrome when ready"
        res = self.decomposer.decompose(cmd)

        self.assertTrue(res["is_multi_step"])
        self.assertGreaterEqual(len(res["steps"]), 2)
        tools = [s["tool"] for s in res["steps"]]
        self.assertIn("run_project", tools)
        self.assertIn("open_desktop_app", tools)


if __name__ == "__main__":
    unittest.main()
