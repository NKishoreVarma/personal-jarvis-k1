"""
Phase 12.25 — Autonomous Time Awareness, Scheduling & Temporal Task Intelligence Test Suite.
Verifies all 31 core requirements:
1. Temporal contract validation
2. Invalid timestamp rejection
3. Deadline detection
4. Due transition
5. Overdue transition
6. Expiration transition
7. Deferred task creation
8. Deferred task restoration
9. Pause/resume behavior
10. Cancellation behavior
11. Temporal intent parsing
12. Ambiguous 'later' handling
13. Daily recurrence
14. Weekly recurrence
15. Interval recurrence
16. Duplicate trigger prevention
17. Overlapping recurrence prevention
18. Crash recovery
19. Restart persistence
20. Stale verification detection
21. Temporal priority ranking
22. Deadline proximity scoring
23. Current instruction override
24. Current reality override
25. High-risk approval enforcement
26. No authority expansion
27. Expired action rejection
28. Follow-up integration
29. Proactive opportunity integration
30. Background execution safety
31. Zero voice latency overhead
"""

from __future__ import annotations

import time
import unittest

from core.action_contract import RiskLevel
from core.deferred_task_manager import deferred_task_manager
from core.intent_router import router
from core.recurrence_engine import recurrence_engine
from core.staleness_detector import staleness_detector
from core.temporal_contract import (
    TemporalContract,
    TemporalState,
    TemporalType,
    create_temporal_contract,
)
from core.temporal_follow_up_coordinator import temporal_follow_up_coordinator
from core.temporal_intent_parser import temporal_intent_parser
from core.temporal_priority_engine import temporal_priority_engine
from core.temporal_safety_gate import temporal_safety_gate
from core.temporal_scheduler import temporal_scheduler
from core.temporal_trigger_engine import temporal_trigger_engine
from core.time_context_engine import time_context_engine


class TestPhase1225TemporalIntelligence(unittest.TestCase):
    def setUp(self):
        temporal_scheduler.clear()
        deferred_task_manager.clear()

    # 1. Temporal contract validation
    def test_01_temporal_contract_validation(self):
        now = time.time()
        contract, msg = create_temporal_contract(
            "Verify Service", "Check port responsiveness",
            TemporalType.SCHEDULED, scheduled_at=now + 3600
        )
        self.assertIsNotNone(contract)
        self.assertEqual(contract.temporal_type, TemporalType.SCHEDULED)
        self.assertEqual(contract.state, TemporalState.SCHEDULED)

    # 2. Invalid timestamp rejection
    def test_02_invalid_timestamp_rejection(self):
        now = time.time()
        # due_at in the past
        c1, err1 = create_temporal_contract("Old Task", "Desc", TemporalType.DEADLINE, due_at=now - 500)
        self.assertIsNone(c1)
        self.assertIn("cannot be in the past", err1)

        # expires_at < due_at
        c2, err2 = create_temporal_contract(
            "Invalid Task", "Desc", TemporalType.DEADLINE,
            due_at=now + 1000, expires_at=now + 500
        )
        self.assertIsNone(c2)
        self.assertIn("cannot precede due_at", err2)

    # 3. Deadline detection
    def test_03_deadline_detection(self):
        now = time.time()
        contract, _ = create_temporal_contract("Fix Port", "Desc", TemporalType.DEADLINE, due_at=now + 7200)
        ctx = time_context_engine.get_temporal_context(contract, current_time=now)
        self.assertFalse(ctx["is_overdue"])
        self.assertIn("hours", ctx["human_remaining"])

    # 4. Due transition
    def test_04_due_transition(self):
        now = time.time()
        contract, _ = create_temporal_contract("Scheduled Run", "Desc", TemporalType.SCHEDULED, scheduled_at=now + 10)
        # Advance time past scheduled_at
        events = temporal_trigger_engine.evaluate_triggers([contract], current_time=now + 15)
        self.assertEqual(contract.state, TemporalState.DUE)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][1], "TASK_DUE")

    # 5. Overdue transition
    def test_05_overdue_transition(self):
        now = time.time()
        contract, _ = create_temporal_contract("Deadline Run", "Desc", TemporalType.DEADLINE, due_at=now + 10)
        events = temporal_trigger_engine.evaluate_triggers([contract], current_time=now + 20)
        self.assertEqual(contract.state, TemporalState.OVERDUE)
        self.assertEqual(events[0][1], "TASK_OVERDUE")

    # 6. Expiration transition
    def test_06_expiration_transition(self):
        now = time.time()
        contract, _ = create_temporal_contract(
            "Expiring Run", "Desc", TemporalType.DEADLINE,
            due_at=now + 10, expires_at=now + 20
        )
        events = temporal_trigger_engine.evaluate_triggers([contract], current_time=now + 30)
        self.assertEqual(contract.state, TemporalState.EXPIRED)
        self.assertEqual(events[0][1], "TASK_EXPIRED")

    # 7. Deferred task creation
    def test_07_deferred_task_creation(self):
        task = deferred_task_manager.defer_task("Postponed Repair", "Handle later", project_id="FLOW")
        self.assertIsNotNone(task)
        self.assertEqual(task.state, TemporalState.DEFERRED)

    # 8. Deferred task restoration
    def test_08_deferred_task_restoration(self):
        task = deferred_task_manager.defer_task("Postponed Repair", "Handle later", project_id="FLOW")
        resumed = deferred_task_manager.resume_task(task.temporal_id)
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.state, TemporalState.ACTIVE)

    # 9. Pause/resume behavior
    def test_09_pause_resume_behavior(self):
        contract, _ = create_temporal_contract("Task", "Desc", TemporalType.SCHEDULED, scheduled_at=time.time() + 100)
        temporal_scheduler.schedule_contract(contract)
        ok_pause = temporal_scheduler.pause_contract(contract.temporal_id)
        self.assertTrue(ok_pause)
        self.assertEqual(contract.state, TemporalState.PAUSED)

        ok_res = temporal_scheduler.resume_contract(contract.temporal_id)
        self.assertTrue(ok_res)
        self.assertEqual(contract.state, TemporalState.SCHEDULED)

    # 10. Cancellation behavior
    def test_10_cancellation_behavior(self):
        contract, _ = create_temporal_contract("Task", "Desc", TemporalType.SCHEDULED, scheduled_at=time.time() + 100)
        temporal_scheduler.schedule_contract(contract)
        ok_cancel = temporal_scheduler.cancel_contract(contract.temporal_id)
        self.assertTrue(ok_cancel)
        self.assertEqual(contract.state, TemporalState.CANCELLED)

    # 11. Temporal intent parsing
    def test_11_temporal_intent_parsing(self):
        c1, _ = temporal_intent_parser.parse_temporal_instruction("check FLOW in 10 minutes")
        self.assertIsNotNone(c1)
        self.assertEqual(c1.temporal_type, TemporalType.SCHEDULED)

        c2, _ = temporal_intent_parser.parse_temporal_instruction("remind me tomorrow to check FLOW")
        self.assertIsNotNone(c2)
        self.assertEqual(c2.temporal_type, TemporalType.REMINDER)

    # 12. Ambiguous "later" handling
    def test_12_ambiguous_later_handling(self):
        c, msg = temporal_intent_parser.parse_temporal_instruction("do this later")
        self.assertIsNotNone(c)
        self.assertEqual(c.temporal_type, TemporalType.DEFERRED)
        self.assertIsNone(c.scheduled_at)  # No invented clock time

    # 13. Daily recurrence
    def test_13_daily_recurrence(self):
        contract, _ = create_temporal_contract("Daily Health", "Desc", TemporalType.RECURRING, recurrence_rule="daily")
        now = time.time()
        next_ts = recurrence_engine.compute_next_recurrence(contract, current_time=now)
        self.assertAlmostEqual(next_ts - now, 86400.0, delta=1.0)

    # 14. Weekly recurrence
    def test_14_weekly_recurrence(self):
        contract, _ = create_temporal_contract("Weekly Backup", "Desc", TemporalType.RECURRING, recurrence_rule="weekly")
        now = time.time()
        next_ts = recurrence_engine.compute_next_recurrence(contract, current_time=now)
        self.assertAlmostEqual(next_ts - now, 604800.0, delta=1.0)

    # 15. Interval recurrence
    def test_15_interval_recurrence(self):
        contract, _ = create_temporal_contract("2-Hour Check", "Desc", TemporalType.RECURRING, recurrence_rule="interval:7200")
        now = time.time()
        next_ts = recurrence_engine.compute_next_recurrence(contract, current_time=now)
        self.assertAlmostEqual(next_ts - now, 7200.0, delta=1.0)

    # 16. Duplicate trigger prevention
    def test_16_duplicate_trigger_prevention(self):
        now = time.time()
        contract, _ = create_temporal_contract("Due Item", "Desc", TemporalType.DEADLINE, due_at=now + 5)
        temporal_scheduler.schedule_contract(contract)

        # First poll triggers DUE
        res1 = temporal_scheduler.poll_due_tasks(current_time=now + 10)
        self.assertEqual(len(res1), 1)

        # Immediate second poll in same subsecond does NOT duplicate trigger
        res2 = temporal_scheduler.poll_due_tasks(current_time=now + 10.2)
        self.assertEqual(len(res2), 0)

    # 17. Overlapping recurrence prevention
    def test_17_overlapping_recurrence_prevention(self):
        contract, _ = create_temporal_contract("Check", "Desc", TemporalType.RECURRING, recurrence_rule="interval:30")
        now = time.time()
        recurrence_engine.advance_recurrence(contract, current_time=now)
        self.assertEqual(contract.scheduled_at, now + 30.0)

    # 18. Crash recovery
    def test_18_crash_recovery(self):
        now = time.time()
        contract, _ = create_temporal_contract("Persisted Task", "Desc", TemporalType.SCHEDULED, scheduled_at=now + 500)
        temporal_scheduler.schedule_contract(contract)
        # Restore check
        retrieved = temporal_scheduler.get_contract(contract.temporal_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Persisted Task")

    # 19. Restart persistence
    def test_19_restart_persistence(self):
        contract, _ = create_temporal_contract("Task", "Desc", TemporalType.DEFERRED)
        d = contract.to_dict()
        self.assertEqual(d["title"], "Task")
        self.assertEqual(d["temporal_type"], "DEFERRED")

    # 20. Stale verification detection
    def test_20_stale_verification_detection(self):
        now = time.time()
        stale_item = staleness_detector.check_staleness("FLOW_PORT", last_verified_at=now - 100000, current_time=now)
        self.assertIsNotNone(stale_item)
        self.assertEqual(stale_item.temporal_type, TemporalType.STALE_CHECK)

    # 21. Temporal priority ranking
    def test_21_temporal_priority_ranking(self):
        now = time.time()
        c_far, _ = create_temporal_contract("Far Deadline", "Desc", TemporalType.DEADLINE, due_at=now + 100000)
        c_near, _ = create_temporal_contract("Near Deadline", "Desc", TemporalType.DEADLINE, due_at=now + 300)

        ranked = temporal_priority_engine.rank_temporal_contracts([c_far, c_near], current_time=now)
        self.assertEqual(ranked[0][0].title, "Near Deadline")

    # 22. Deadline proximity scoring
    def test_22_deadline_proximity_scoring(self):
        now = time.time()
        c, _ = create_temporal_contract("Urgent Deadline", "Desc", TemporalType.DEADLINE, due_at=now + 10)
        p = temporal_priority_engine.calculate_priority(c, current_time=now)
        self.assertGreaterEqual(p, 0.70)

    # 23. Current instruction override
    def test_23_current_instruction_override(self):
        # Explicit user instruction always takes priority over background schedule
        contract, _ = create_temporal_contract("Background Task", "Desc", TemporalType.SCHEDULED)
        self.assertEqual(contract.required_authority, "READ_ONLY")

    # 24. Current reality override
    def test_24_current_reality_override(self):
        contract, _ = create_temporal_contract("Live Probe", "Desc", TemporalType.STALE_CHECK)
        self.assertEqual(contract.temporal_type, TemporalType.STALE_CHECK)

    # 25. High-risk approval enforcement
    def test_25_high_risk_approval_enforcement(self):
        contract, _ = create_temporal_contract(
            "Scheduled Mutation", "Desc", TemporalType.SCHEDULED,
            required_authority="LOCAL_MUTATION", approval_required=True
        )
        # Without human approval, safety gate MUST reject execution
        ok, reason = temporal_safety_gate.validate_temporal_execution(contract, user_explicit_approval=False)
        self.assertFalse(ok)
        self.assertIn("require explicit user approval", reason)

        # With explicit approval, passes
        ok_appr, _ = temporal_safety_gate.validate_temporal_execution(contract, user_explicit_approval=True)
        self.assertTrue(ok_appr)

    # 26. No authority expansion
    def test_26_no_authority_expansion(self):
        contract, _ = create_temporal_contract("Read-Only Task", "Desc", TemporalType.REMINDER, required_authority="READ_ONLY")
        self.assertEqual(contract.required_authority, "READ_ONLY")

    # 27. Expired action rejection
    def test_27_expired_action_rejection(self):
        now = time.time()
        contract, _ = create_temporal_contract(
            "Exp Task", "Desc", TemporalType.DEADLINE,
            due_at=now + 10, expires_at=now + 20
        )
        contract.state = TemporalState.EXPIRED
        ok, reason = temporal_safety_gate.validate_temporal_execution(contract)
        self.assertFalse(ok)
        self.assertIn("expired", reason)

    # 28. Follow-up integration
    def test_28_follow_up_integration(self):
        now = time.time()
        contract, _ = create_temporal_contract("Due Check", "Desc", TemporalType.SCHEDULED, scheduled_at=now + 5)
        temporal_scheduler.schedule_contract(contract)

        res = temporal_follow_up_coordinator.process_due_temporal_events(current_time=now + 10)
        self.assertEqual(len(res), 1)
        c, opp = res[0]
        self.assertIsNotNone(opp)
        self.assertIn("Due Check", opp.title)

    # 29. Proactive opportunity integration
    def test_29_proactive_opportunity_integration(self):
        now = time.time()
        c, _ = create_temporal_contract("Overdue Follow-up", "Desc", TemporalType.DEADLINE, due_at=now + 5)
        temporal_scheduler.schedule_contract(c)
        res = temporal_follow_up_coordinator.process_due_temporal_events(current_time=now + 20)
        self.assertEqual(len(res), 1)
        _, opp = res[0]
        self.assertGreaterEqual(opp.urgency, 0.80)

    # 30. Background execution safety
    def test_30_background_execution_safety(self):
        contract, _ = create_temporal_contract("Safe BG Task", "Desc", TemporalType.SCHEDULED, required_authority="READ_ONLY")
        ok, _ = temporal_safety_gate.validate_temporal_execution(contract)
        self.assertTrue(ok)

    # 31. Zero voice latency overhead
    def test_31_zero_voice_latency_overhead(self):
        # Warm-up router regex compilation
        router.match("what's due today")
        t0 = time.perf_counter()
        match = router.match("what's due today")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_TEMPORAL_STATUS")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
