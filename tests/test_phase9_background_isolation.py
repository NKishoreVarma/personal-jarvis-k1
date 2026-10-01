"""
Unit tests for Phase 1 Optimization — Realtime Voice Path & Background Task Isolation.
Tests core/background_task_manager.py, timeout enforcement, failure isolation, and non-blocking intent routing.
"""

import asyncio
import time
import unittest

from core.background_task_manager import (
    BackgroundTaskManager,
    TaskState,
    background_task_manager,
)
from core.intent_router import router


class TestPhase9BackgroundIsolation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mgr = BackgroundTaskManager()

    async def asyncTearDown(self):
        self.mgr.cancel_all()

    # 1. Background task submits and completes
    async def test_submit_and_complete(self):
        async def sample_task():
            await asyncio.sleep(0.05)
            return "ok"

        task = self.mgr.submit("sample", sample_task(), timeout=2.0)
        res = await task
        self.assertEqual(res, "ok")
        status = self.mgr.get_status("sample")
        self.assertEqual(status["status"], TaskState.COMPLETED.value)
        self.assertGreater(status["duration"], 0.0)

    # 2. Strict timeout enforcement
    async def test_timeout_enforcement(self):
        async def slow_task():
            await asyncio.sleep(1.0)
            return "done"

        task = self.mgr.submit("slow", slow_task(), timeout=0.05)
        await task
        status = self.mgr.get_status("slow")
        self.assertEqual(status["status"], TaskState.TIMEOUT.value)
        self.assertIn("timed out", status["error"])

    # 3. Failure isolation (error does not crash manager or event loop)
    async def test_error_isolation(self):
        async def error_task():
            raise RuntimeError("Database connection dropped")

        task = self.mgr.submit("failing", error_task(), timeout=1.0)
        await task
        status = self.mgr.get_status("failing")
        self.assertEqual(status["status"], TaskState.FAILED.value)
        self.assertIn("Database connection dropped", status["error"])

    # 4. Cancellation stops running background task
    async def test_cancel_task(self):
        async def forever_task():
            await asyncio.sleep(10.0)

        task = self.mgr.submit("forever", forever_task(), timeout=15.0)
        await asyncio.sleep(0.02)
        cancelled = self.mgr.cancel("forever")
        self.assertTrue(cancelled)
        status = self.mgr.get_status("forever")
        self.assertEqual(status["status"], TaskState.CANCELLED.value)

    # 5. Slow background operation does not delay local intent commands
    async def test_slow_search_does_not_block_local_intent(self):
        # Start a slow background task simulating background news fetch
        async def slow_background_fetch():
            await asyncio.sleep(0.2)
            return "news"

        self.mgr.submit("bg_news", slow_background_fetch(), timeout=2.0)

        # Immediate local intent command
        t0 = time.monotonic()
        res = router.route_and_execute("What time is it?")
        dt = time.monotonic() - t0

        self.assertTrue(res["handled"])
        self.assertIn("It is currently", res["response"])
        self.assertLess(dt, 0.05)  # Must complete in under 50ms despite background task running


if __name__ == "__main__":
    unittest.main()
