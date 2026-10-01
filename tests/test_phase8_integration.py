"""
Phase 8 End-to-End Integration Test Suite.
Tests the complete project execution pipeline:
User says: 'open FLOW from my Desktop and run the server'
-> Immediate 'Okay.' acknowledgement (< 500ms)
-> Asynchronous Discover -> Profile -> Start Process -> Detect Port -> Verify -> Complete.
"""

import asyncio
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from actions.project_runner import run_project_async
from core.intent_router import router
from core.process_manager import process_manager
from core.project_discovery import ProjectDiscovery
from core.task_registry import task_registry


class TestPhase8Integration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.desktop_dir = self.temp_dir / "Desktop"
        self.desktop_dir.mkdir()

        # Create mock FLOW project
        self.flow_dir = self.desktop_dir / "FLOW"
        self.flow_dir.mkdir()

        # Create mock script that outputs port and sleeps
        runner_script = self.flow_dir / "dev_server.py"
        with open(runner_script, "w") as f:
            f.write(
                "import sys, http.server\n"
                "sys.stdout.write('  ▲ Next.js 14.0.0\\n')\n"
                "sys.stdout.write('  - Local:        http://localhost:3000\\n')\n"
                "sys.stdout.flush()\n"
                "server = http.server.HTTPServer(('127.0.0.1', 3000), http.server.SimpleHTTPRequestHandler)\n"
                "server.serve_forever()\n"
            )

        pkg_json = {
            "name": "flow",
            "scripts": {"dev": f"{sys.executable} dev_server.py"},
            "dependencies": {"next": "14.0.0"},
        }
        with open(self.flow_dir / "package.json", "w") as f:
            json.dump(pkg_json, f)

        # Inject custom discovery root
        self.custom_discovery = ProjectDiscovery(custom_roots=[self.desktop_dir])
        import actions.project_runner
        self.orig_discovery = actions.project_runner.project_discovery
        actions.project_runner.project_discovery = self.custom_discovery

        task_registry.clear()
        process_manager.reset()

    def tearDown(self):
        import actions.project_runner
        actions.project_runner.project_discovery = self.orig_discovery
        process_manager.reset()
        task_registry.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_01_end_to_end_project_run(self):
        task_id = task_registry.register_task("Run FLOW server")
        res = await run_project_async("FLOW", location_hint="desktop", task_id=task_id, startup_wait_seconds=4.0)

        self.assertTrue(res["success"])
        self.assertEqual(res["project"], "FLOW")
        self.assertEqual(res["port"], 3000)
        self.assertIn("FLOW is running successfully on localhost:3000", res["message"])

        # Check task registry reflects completed state
        task_record = task_registry._tasks[task_id]
        self.assertEqual(task_record.status, "COMPLETED")

    def test_02_voice_acknowledgement_intent_and_latency(self):
        t0 = time.monotonic()
        res = router.route_and_execute("open FLOW from my Desktop and run the server")
        dt_ms = (time.monotonic() - t0) * 1000.0

        self.assertTrue(res["handled"])
        self.assertEqual(res["intent"], "RUN_PROJECT")
        self.assertEqual(res["response"], "Okay.")
        self.assertEqual(res["parameters"]["project_name"].upper(), "FLOW")
        self.assertEqual(res["parameters"]["location_hint"].lower(), "desktop")
        self.assertLess(dt_ms, 50.0)  # Immediate local acknowledgement under 50ms


if __name__ == "__main__":
    unittest.main()
