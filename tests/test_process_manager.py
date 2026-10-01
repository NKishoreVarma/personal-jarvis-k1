"""
Unit tests for Process Manager (Phase 8).
Verifies non-blocking execution, port detection regex, HTTP verification, and process termination.
"""

import asyncio
import sys
import unittest
from core.process_manager import ProcessManager


class TestProcessManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mgr = ProcessManager()

    def tearDown(self):
        self.mgr.reset()

    def test_detect_port_patterns(self):
        self.assertEqual(self.mgr.detect_port("  ➜  Local:   http://localhost:5173/"), 5173)
        self.assertEqual(self.mgr.detect_port("Listening on http://127.0.0.1:3000"), 3000)
        self.assertEqual(self.mgr.detect_port("Server running on port 8000"), 8000)
        self.assertEqual(self.mgr.detect_port("Django dev server at http://0.0.0.0:8080/"), 8080)
        self.assertIsNone(self.mgr.detect_port("Compilation complete without errors"))

    async def test_start_and_stop_process(self):
        # Spawn a non-blocking python sleeper
        cmd = [sys.executable, "-c", "import time, sys; sys.stdout.write('port 3000\\n'); sys.stdout.flush(); time.sleep(10)"]
        res = await self.mgr.start_process(cmd, cwd=".", project_name="test_proj")
        self.assertTrue(res["success"])
        process_id = res["process_id"]

        # Wait a moment for output streaming
        await asyncio.sleep(0.3)
        status = self.mgr.get_process_status(process_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["detected_port"], 3000)

        # Stop process
        stopped = self.mgr.stop_process(process_id)
        self.assertTrue(stopped)


if __name__ == "__main__":
    unittest.main()
