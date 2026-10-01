"""
Unit tests for TaskRegistry & Desktop Agent (Phase 8).
Verifies active task tracking, status querying ('what are you doing'), and clean task cancellation.
"""

import unittest
from core.desktop_agent import DesktopAgent
from core.task_registry import TaskRegistry


class TestDesktopAgent(unittest.TestCase):
    def setUp(self):
        self.reg = TaskRegistry()

    def tearDown(self):
        self.reg.clear()

    def test_task_registry_lifecycle(self):
        task_id = self.reg.register_task("Run FLOW server")
        self.assertIsNotNone(task_id)

        self.reg.update_progress(task_id, "Verifying localhost:3000")
        summary = self.reg.get_active_task_summary()
        self.assertIn("Verifying localhost:3000", summary)

        self.reg.complete_task(task_id, "FLOW is running on localhost:3000")
        self.assertEqual(self.reg.get_active_task_summary(), "I'm not currently running any background tasks.")

    def test_task_cancellation(self):
        task_id = self.reg.register_task("Run backend server")
        cancelled = self.reg.cancel_task(task_id)
        self.assertTrue(cancelled)
        record = self.reg._tasks[task_id]
        self.assertEqual(record.status, "CANCELLED")


if __name__ == "__main__":
    unittest.main()
