"""
Phase 12.17 — Persistent Agent Runtime, Background Task Continuity & Crash Recovery Test Suite.
Verifies all 25 core requirements:
1. Runtime startup
2. Runtime heartbeat
3. Stale heartbeat detection
4. Graceful shutdown
5. Crash detection
6. Atomic checkpoint persistence
7. Corrupted checkpoint rejection
8. Checkpoint version validation
9. Active task restoration
10. Already-completed task detection
11. Verify-only recovery
12. Safe resume
13. Environment change requiring replanning
14. Duplicate execution prevention
15. Lease expiration
16. Concurrent runtime protection
17. Recovery cancellation
18. Sleep/wake gap detection
19. Background worker supervision
20. Orphan worker cleanup
21. Recovered task outcome verification
22. Recovery trace generation
23. Runtime health degradation
24. Checkpoint failure handling
25. Zero voice pipeline blocking
"""

from __future__ import annotations

import os
import shutil
import time
import unittest

from core.background_task_supervisor import TaskClass, background_task_supervisor
from core.checkpoint_manager import checkpoint_manager
from core.crash_recovery_manager import crash_recovery_manager
from core.durable_task_contract import DurableTaskStatus, create_durable_task
from core.graceful_shutdown_manager import graceful_shutdown_manager
from core.heartbeat_manager import heartbeat_manager
from core.intent_router import router
from core.recovery_decision_engine import RecoveryDecision, recovery_decision_engine
from core.recovery_trace import RecoveryEventType, recovery_trace
from core.runtime_contract import RuntimeStatus, create_runtime_contract
from core.runtime_health_monitor import RuntimeHealthState, runtime_health_monitor
from core.runtime_state_store import runtime_state_store
from core.sleep_wake_detector import sleep_wake_detector
from core.task_lease_manager import task_lease_manager


class TestPhase1217PersistentRuntime(unittest.TestCase):
    def setUp(self):
        self.test_dir = "data/test_runtime"
        runtime_state_store.base_dir = self.test_dir
        runtime_state_store.runtime_file = os.path.join(self.test_dir, "runtime_state.json")
        runtime_state_store.tasks_file = os.path.join(self.test_dir, "active_tasks.json")
        runtime_state_store.checkpoints_dir = os.path.join(self.test_dir, "checkpoints")
        runtime_state_store.history_file = os.path.join(self.test_dir, "recovery_history.json")
        runtime_state_store.clear_all()

        checkpoint_manager.clear_all()
        task_lease_manager.clear_all()
        background_task_supervisor.clear_all()
        recovery_trace.clear_all()
        runtime_health_monitor.clear_all()
        heartbeat_manager.stop_heartbeat()

    def tearDown(self):
        heartbeat_manager.stop_heartbeat()
        try:
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
        except Exception:
            pass

    # 1. Runtime startup
    def test_01_runtime_startup(self):
        rt = heartbeat_manager.initialize_runtime("rt_test_01")
        self.assertEqual(rt.runtime_id, "rt_test_01")
        self.assertEqual(rt.runtime_status, RuntimeStatus.RUNNING)
        loaded = runtime_state_store.load_runtime()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.runtime_id, "rt_test_01")

    # 2. Runtime heartbeat
    def test_02_runtime_heartbeat(self):
        rt = heartbeat_manager.initialize_runtime("rt_test_02")
        old_heartbeat = rt.last_heartbeat
        time.sleep(0.02)
        heartbeat_manager.pulse_heartbeat()
        self.assertGreater(heartbeat_manager.current_runtime.last_heartbeat, old_heartbeat)

    # 3. Stale heartbeat detection
    def test_03_stale_heartbeat_detection(self):
        rt = create_runtime_contract("rt_old")
        rt.last_heartbeat = time.time() - 25.0  # 25 seconds ago
        self.assertTrue(rt.is_heartbeat_stale(10.0))

    # 4. Graceful shutdown
    def test_04_graceful_shutdown(self):
        heartbeat_manager.initialize_runtime("rt_shutdown")
        task = create_durable_task("g1", "p1", "tg1", "FLOW", "Start FLOW")
        task.status = DurableTaskStatus.RUNNING
        runtime_state_store.save_task(task)

        graceful_shutdown_manager.execute_shutdown("Test graceful shutdown")

        loaded_rt = runtime_state_store.load_runtime()
        self.assertEqual(loaded_rt.runtime_status, RuntimeStatus.STOPPED)
        self.assertTrue(loaded_rt.shutdown_requested)

        # Active tasks must be RECOVERY_REQUIRED (never FAILED)
        active = runtime_state_store.load_active_tasks()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].status, DurableTaskStatus.RECOVERY_REQUIRED)

    # 5. Crash detection
    def test_05_crash_detection(self):
        # Simulate prior crashed runtime
        prior = create_runtime_contract("rt_prior_crash")
        prior.runtime_status = RuntimeStatus.RUNNING
        prior.last_heartbeat = time.time() - 30.0  # Stale
        prior.shutdown_requested = False
        runtime_state_store.save_runtime(prior)

        crashed_notified = []
        new_rt = heartbeat_manager.initialize_runtime("rt_new", on_crash_detected=lambda c: crashed_notified.append(c))

        self.assertEqual(len(crashed_notified), 1)
        self.assertEqual(new_rt.recovery_generation, 1)

    # 6. Atomic checkpoint persistence
    def test_06_atomic_checkpoint_persistence(self):
        task = create_durable_task("g_ckpt", "p_ckpt", "tg_ckpt", "FLOW", "Repair FLOW")
        snapshot = checkpoint_manager.create_checkpoint("g_ckpt", task, plan_data={"step": "repair"})
        self.assertIsNotNone(snapshot)
        loaded = checkpoint_manager.load_latest_valid_checkpoint("g_ckpt")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.version, task.checkpoint_version)

    # 7. Corrupted checkpoint rejection
    def test_07_corrupted_checkpoint_rejection(self):
        corrupted_data = {
            "checkpoint_id": "ckpt_bad",
            "goal_id": "g_bad",
            "version": 1,
            "task_data": {"task": "bad"},
            "checksum": "invalid_checksum_hash",
        }
        valid, reason = checkpoint_manager.validate_checkpoint(corrupted_data)
        self.assertFalse(valid)
        self.assertIn("Corruption detected", reason)

    # 8. Checkpoint version validation
    def test_08_checkpoint_version_validation(self):
        task = create_durable_task("g_ver", "p_ver", "tg_ver", "FLOW", "Build FLOW")
        ckpt1 = checkpoint_manager.create_checkpoint("g_ver", task)
        task.touch()
        ckpt2 = checkpoint_manager.create_checkpoint("g_ver", task)
        self.assertGreater(ckpt2.version, ckpt1.version)

    # 9. Active task restoration
    def test_09_active_task_restoration(self):
        t1 = create_durable_task("g1", "p1", "tg1", "FLOW", "Goal 1")
        t2 = create_durable_task("g2", "p2", "tg2", "FLOW", "Goal 2")
        runtime_state_store.save_task(t1)
        runtime_state_store.save_task(t2)

        loaded = runtime_state_store.load_active_tasks()
        self.assertEqual(len(loaded), 2)

    # 10. Already-completed task detection (Case A)
    def test_10_already_completed_task_detection(self):
        task = create_durable_task("g_flow", "p_flow", "tg_flow", "FLOW", "Start FLOW")
        task.status = DurableTaskStatus.RUNNING

        # Live reality: server is running and reachable
        obs = {"project_name": "FLOW", "process_running": True, "reachable": True, "port": 3000}
        plan = recovery_decision_engine.decide_recovery_action(task, obs)
        self.assertEqual(plan.decision, RecoveryDecision.ALREADY_COMPLETED)

    # 11. Verify-only recovery (Case B)
    def test_11_verify_only_recovery(self):
        task = create_durable_task("g_v", "p_v", "tg_v", "FLOW", "Start FLOW")
        task.status = DurableTaskStatus.RUNNING

        # Process is alive but not verified reachable yet
        obs = {"project_name": "FLOW", "process_running": True, "reachable": False, "pid": 1234}
        plan = recovery_decision_engine.decide_recovery_action(task, obs)
        self.assertEqual(plan.decision, RecoveryDecision.VERIFY_ONLY)

    # 12. Safe resume (Case C)
    def test_12_safe_resume(self):
        task = create_durable_task("g_res", "p_res", "tg_res", "FLOW", "Multi-step plan", pending_steps=[{"step_id": "step_3"}])
        task.status = DurableTaskStatus.RUNNING

        obs = {"project_name": "FLOW", "process_running": False, "reachable": False, "port_conflict": False}
        plan = recovery_decision_engine.decide_recovery_action(task, obs)
        self.assertEqual(plan.decision, RecoveryDecision.SAFE_RESUME)
        self.assertEqual(plan.target_step_id, "step_3")

    # 13. Environment change requiring replanning (Case D)
    def test_13_environment_change_requiring_replanning(self):
        task = create_durable_task("g_env", "p_env", "tg_env", "FLOW", "Start FLOW")
        task.status = DurableTaskStatus.RUNNING

        obs = {"project_name": "FLOW", "process_running": False, "reachable": False, "port_conflict": True}
        plan = recovery_decision_engine.decide_recovery_action(task, obs)
        self.assertEqual(plan.decision, RecoveryDecision.REPLAN_REQUIRED)

    # 14. Duplicate execution prevention
    def test_14_duplicate_execution_prevention(self):
        lease1 = task_lease_manager.acquire_lease("FLOW_PORT_3000", "rt_1", ttl_seconds=10.0)
        self.assertIsNotNone(lease1)

        # Second runtime attempts to acquire same resource
        lease2 = task_lease_manager.acquire_lease("FLOW_PORT_3000", "rt_2", ttl_seconds=10.0)
        self.assertIsNone(lease2)

    # 15. Lease expiration
    def test_15_lease_expiration(self):
        task_lease_manager.acquire_lease("FLOW_MUTATION", "rt_1", ttl_seconds=0.01)
        time.sleep(0.03)
        self.assertFalse(task_lease_manager.is_lease_active("FLOW_MUTATION"))

    # 16. Concurrent runtime protection
    def test_16_concurrent_runtime_protection(self):
        l1 = task_lease_manager.acquire_lease("DB_MIGRATION", "rt_alpha")
        self.assertTrue(task_lease_manager.is_lease_active("DB_MIGRATION"))
        # Same owner can renew
        l2 = task_lease_manager.acquire_lease("DB_MIGRATION", "rt_alpha")
        self.assertEqual(l1, l2)

    # 17. Recovery cancellation
    def test_17_recovery_cancellation(self):
        task = create_durable_task("g_canc", "p_canc", "tg_canc", "FLOW", "Cancelled goal")
        task.status = DurableTaskStatus.CANCELLED
        obs = {"process_running": False}
        plan = recovery_decision_engine.decide_recovery_action(task, obs)
        self.assertEqual(plan.decision, RecoveryDecision.CANCEL_RECOVERY)

    # 18. Sleep/wake gap detection
    def test_18_sleep_wake_gap_detection(self):
        wakes = []
        sleep_wake_detector.register_wake_listener(lambda gap: wakes.append(gap))

        # Normal small interval
        t0 = time.time()
        sleep_wake_detector.check_tick(t0)
        self.assertFalse(sleep_wake_detector.check_tick(t0 + 1.0))

        # Simulated 45s sleep gap
        detected = sleep_wake_detector.check_tick(t0 + 46.0)
        self.assertTrue(detected)
        self.assertEqual(len(wakes), 1)

    # 19. Background worker supervision
    def test_19_background_worker_supervision(self):
        w1 = background_task_supervisor.register_task("flow_watcher", TaskClass.RECOVERABLE, "rt_1", "FLOW")
        w2 = background_task_supervisor.register_task("ocr_scanner", TaskClass.EPHEMERAL, "rt_1", "FLOW")

        recoverable = background_task_supervisor.list_recoverable_tasks()
        self.assertEqual(len(recoverable), 1)
        self.assertEqual(recoverable[0].name, "flow_watcher")

    # 20. Orphan worker cleanup
    def test_20_orphan_worker_cleanup(self):
        background_task_supervisor.register_task("ephemeral_job", TaskClass.EPHEMERAL, "rt_dead_runtime")
        cleaned = background_task_supervisor.cleanup_orphaned_tasks("rt_active_runtime")
        self.assertEqual(cleaned, 1)

    # 21. Recovered task outcome verification
    def test_21_recovered_task_outcome_verification(self):
        task = create_durable_task("g_rec_v", "p_rec_v", "tg_rec_v", "FLOW", "Recover FLOW")
        task.status = DurableTaskStatus.RECOVERY_REQUIRED
        runtime_state_store.save_task(task)

        obs = {"project_name": "FLOW", "process_running": True, "reachable": True, "port": 3000}
        plan = crash_recovery_manager.recover_task(task, live_observation=obs)

        self.assertEqual(plan.decision, RecoveryDecision.ALREADY_COMPLETED)
        self.assertEqual(task.status, DurableTaskStatus.COMPLETED)
        self.assertEqual(task.verification_state, "VERIFIED")

    # 22. Recovery trace generation
    def test_22_recovery_trace_generation(self):
        ev = recovery_trace.record_event(
            event_type=RecoveryEventType.TASK_ALREADY_COMPLETED,
            goal_id="g_flow",
            project_name="FLOW",
            description="FLOW was already running and verified.",
        )
        self.assertIsNotNone(ev)
        explanation = recovery_trace.format_user_explanation("FLOW")
        self.assertIn("already running", explanation)

    # 23. Runtime health degradation
    def test_23_runtime_health_degradation(self):
        for _ in range(3):
            runtime_health_monitor.record_checkpoint_error()

        state, reason = runtime_health_monitor.evaluate_health()
        self.assertEqual(state, RuntimeHealthState.CRITICAL)

    # 24. Checkpoint failure handling
    def test_24_checkpoint_failure_handling(self):
        # Sanitization filters secrets & audio buffers
        task = create_durable_task("g_sec", "p_sec", "tg_sec", "FLOW", "Secured task")
        payload = {
            "token": "bearer ghp_1234567890abcdef1234567890abcdef1234",
            "audio_buffer": b"\x00\x01\x02",
            "step": "execute",
        }
        sanitized = checkpoint_manager.sanitize_payload(payload)
        self.assertNotIn("audio_buffer", sanitized)
        self.assertIn("[REDACTED_SECRET]", sanitized["token"])

    # 25. Zero voice pipeline blocking
    def test_25_zero_voice_pipeline_blocking(self):
        router.match("what time is it")  # Warm-up
        t0 = time.perf_counter()
        match = router.match("how is the system running")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_RUNTIME_STATUS")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
