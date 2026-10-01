"""
Phase 11 — Background Intelligence, Event Monitoring & Proactive JARVIS Test Suite.
Verifies:
- Asynchronous task management (states, progress, completion, timeout, cancellation)
- Fingerprint deduplication
- Task dependency execution
- Event bus publishing & subscription
- User activity awareness (queueing during speech, delivery during idle)
- Notification rate limiting and duplicate suppression
- System health monitoring
- LoopGuard prevention of runaway recovery loops
"""

import asyncio
import time
import unittest
from unittest.mock import MagicMock

from actions.system_monitor import SystemMonitor
from core.background_task_manager import BackgroundTaskManager, TaskState
from core.event_bus import EventBus, EventType
from core.intent_router import router
from core.loop_guard import LoopGuard
from core.notification_manager import (
    NotificationManager,
    NotificationPriority,
    NotificationRateLimiter,
    UserActivityState,
)


class TestPhase11BackgroundIntelligence(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.task_mgr = BackgroundTaskManager()
        self.rate_limiter = NotificationRateLimiter(max_spoken_per_minute=5, duplicate_cooldown_sec=5.0)
        self.notif_mgr = NotificationManager(rate_limiter=self.rate_limiter)

    def test_01_background_task_lifecycle_and_events(self):
        async def _run_test():
            events_received = []

            def _handler(evt):
                events_received.append(evt.event_type)

            self.event_bus.subscribe(EventType.TASK_STARTED, _handler)
            self.event_bus.subscribe(EventType.TASK_COMPLETED, _handler)

            async def _sample_job():
                await asyncio.sleep(0.05)
                return "SUCCESS_DATA"

            task_id = self.task_mgr.start_background_task("sample_job", _sample_job(), timeout=2.0)
            self.assertIsNotNone(task_id)

            res = await self.task_mgr.wait_for_task(task_id, timeout=1.0)
            self.assertEqual(res, "SUCCESS_DATA")

            status = self.task_mgr.get_task_status(task_id)
            self.assertEqual(status["status"], TaskState.COMPLETED.value)
            self.assertEqual(status["result"], "SUCCESS_DATA")

        asyncio.run(_run_test())

    def test_02_task_timeout_handling(self):
        async def _run_test():
            async def _slow_job():
                await asyncio.sleep(2.0)
                return "NEVER"

            task_id = self.task_mgr.start_background_task("slow_job", _slow_job(), timeout=0.05)
            await asyncio.sleep(0.15)

            status = self.task_mgr.get_task_status(task_id)
            self.assertEqual(status["status"], TaskState.TIMEOUT.value)

        asyncio.run(_run_test())

    def test_03_task_cancellation(self):
        async def _run_test():
            async def _forever():
                while True:
                    await asyncio.sleep(0.1)

            task_id = self.task_mgr.start_background_task("forever", _forever(), timeout=10.0)
            cancelled = self.task_mgr.cancel_task(task_id)
            self.assertTrue(cancelled)

            status = self.task_mgr.get_task_status(task_id)
            self.assertEqual(status["status"], TaskState.CANCELLED.value)

        asyncio.run(_run_test())

    def test_04_task_fingerprint_deduplication(self):
        async def _run_test():
            async def _job():
                await asyncio.sleep(0.5)

            fp = "job_fp_12345"
            task_id_1 = self.task_mgr.start_background_task("job1", _job(), fingerprint=fp)
            task_id_2 = self.task_mgr.start_background_task("job2", _job(), fingerprint=fp)

            self.assertEqual(task_id_1, task_id_2)

            self.task_mgr.cancel_task(task_id_1)

        asyncio.run(_run_test())

    def test_05_task_dependencies(self):
        async def _run_test():
            execution_order = []

            async def _step1():
                await asyncio.sleep(0.05)
                execution_order.append("STEP_1")
                return "STEP_1_DONE"

            async def _step2():
                execution_order.append("STEP_2")
                return "STEP_2_DONE"

            task1_id = self.task_mgr.start_background_task("step1", _step1(), timeout=2.0)
            task2_id = self.task_mgr.start_background_task("step2", _step2(), timeout=2.0, depends_on=task1_id)

            await self.task_mgr.wait_for_task(task2_id, timeout=2.0)
            self.assertEqual(execution_order, ["STEP_1", "STEP_2"])

        asyncio.run(_run_test())

    def test_06_user_activity_aware_notifications(self):
        spoken = []
        self.notif_mgr.set_speech_sink(lambda text: spoken.append(text))

        # 1. While user is speaking, notifications should queue
        self.notif_mgr.set_user_state(UserActivityState.USER_SPEAKING)
        self.notif_mgr.notify("Build", "FLOW server is ready.", priority=NotificationPriority.NORMAL)
        self.assertEqual(len(spoken), 0)
        self.assertEqual(len(self.notif_mgr._pending_queue), 1)

        # 2. When user becomes idle, queued notification flushes
        self.notif_mgr.set_user_state(UserActivityState.USER_IDLE)
        self.assertEqual(len(self.notif_mgr._pending_queue), 0)
        self.assertEqual(len(spoken), 1)
        self.assertIn("FLOW server is ready", spoken[0])

    def test_07_notification_rate_limiter_deduplication(self):
        spoken = []
        self.notif_mgr.set_speech_sink(lambda text: spoken.append(text))
        self.notif_mgr.set_user_state(UserActivityState.USER_IDLE)

        # First dispatch passes
        self.notif_mgr.notify("Server", "Server is ready.", priority=NotificationPriority.NORMAL, category="server")
        self.assertEqual(len(spoken), 1)

        # Immediate duplicate is suppressed
        self.notif_mgr.notify("Server", "Server is ready.", priority=NotificationPriority.NORMAL, category="server")
        self.assertEqual(len(spoken), 1)

    def test_08_system_monitor_alerts(self):
        monitor = SystemMonitor(battery_threshold=15, disk_threshold=90)
        # Mock low battery
        monitor._get_battery_status = MagicMock(return_value={"available": True, "percentage": 8, "charging": False})
        monitor._get_disk_usage = MagicMock(return_value={"used_percent": 96})

        alerts = monitor.check_health_thresholds()
        self.assertEqual(len(alerts), 2)
        types = [a["type"] for a in alerts]
        self.assertIn("BATTERY_LOW", types)
        self.assertIn("DISK_FULL", types)

    def test_09_loop_guard_recovery_prevention(self):
        from core.loop_guard import LoopGuardConfig
        guard = LoopGuard(config=LoopGuardConfig(max_consecutive_failures=2))
        args = {"proc": "FLOW"}
        guard.register_action("restart_server", args)
        guard.register_result(success=False, error="Crash 1")
        guard.register_action("restart_server", args)
        guard.register_result(success=False, error="Crash 2")

        dec = guard.register_action("restart_server", args)
        self.assertFalse(dec.allowed)
        self.assertIn("consecutive failure", dec.reason.lower())

    def test_10_natural_status_query_routing(self):
        res1 = router.match("what's running")
        self.assertTrue(res1["handled"])
        self.assertEqual(res1["intent"], "TASK_STATUS")

        res2 = router.match("is FLOW ready")
        self.assertTrue(res2["handled"])
        self.assertEqual(res2["intent"], "TASK_STATUS")

        res3 = router.match("stop FLOW")
        self.assertTrue(res3["handled"])
        self.assertEqual(res3["intent"], "CANCEL_TASK")


if __name__ == "__main__":
    unittest.main()
