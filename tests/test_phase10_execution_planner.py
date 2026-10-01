"""
Unit tests for Execution Planner (Phase 10).
Verifies complexity classification (SIMPLE, MULTI_STEP, COMPLEX) and plan construction.
"""

import unittest
from core.execution_planner import ExecutionPlanner, TaskComplexity


class TestPhase10ExecutionPlanner(unittest.TestCase):
    def setUp(self):
        self.planner = ExecutionPlanner()

    def test_classify_simple_commands(self):
        self.assertEqual(self.planner.classify_complexity("open Chrome"), TaskComplexity.SIMPLE)
        self.assertEqual(self.planner.classify_complexity("what time is it"), TaskComplexity.SIMPLE)

    def test_classify_multi_step_commands(self):
        cmd = "open WhatsApp, find John, and write hello"
        self.assertEqual(self.planner.classify_complexity(cmd), TaskComplexity.MULTI_STEP)

    def test_classify_complex_reasoning_commands(self):
        cmd = "check John's recent messages and explain why the build failed"
        self.assertEqual(self.planner.classify_complexity(cmd), TaskComplexity.COMPLEX)

    def test_plan_task_preserves_constraints(self):
        cmd = "open WhatsApp, find John, type I'll join soon, without sending it"
        plan = self.planner.plan_task(cmd)

        self.assertTrue(plan["is_multi_step"])
        self.assertTrue(plan["prohibit_send"])
        self.assertGreaterEqual(len(plan["steps"]), 3)


if __name__ == "__main__":
    unittest.main()
