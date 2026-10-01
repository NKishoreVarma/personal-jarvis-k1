"""
Unit tests for Phase 2 Agent Safety — LoopGuard.
Tests action fingerprinting, identical repeat limits, ping-pong cycle detection, failure tracking, and destructive action guards.
"""

import unittest
from core.loop_guard import (
    LoopGuard,
    LoopGuardConfig,
    compute_fingerprint,
)
from core.agent_orchestrator import AgentOrchestrator, PlanStep, Plan, Tool, ToolRegistry


class TestPhase2LoopGuard(unittest.TestCase):
    def setUp(self):
        self.guard = LoopGuard(LoopGuardConfig(
            max_identical_actions=3,
            ping_pong_window=6,
            max_consecutive_failures=3,
            max_global_consecutive_failures=5,
        ))

    # 1. Single action is allowed
    def test_single_action_allowed(self):
        dec = self.guard.register_action("open_app", {"app_name": "Chrome"})
        self.assertTrue(dec.allowed)
        self.assertEqual(dec.action_count, 1)

    # 2. Repeated action below threshold is allowed
    def test_repeat_below_threshold(self):
        for i in range(1, 4):
            dec = self.guard.register_action("open_app", {"app_name": "Chrome"})
            self.assertTrue(dec.allowed)
            self.assertEqual(dec.action_count, i)

    # 3. Excessive identical action is blocked
    def test_excessive_identical_blocked(self):
        for _ in range(3):
            self.guard.register_action("open_app", {"app_name": "Chrome"})
        
        # 4th execution must be blocked
        dec = self.guard.register_action("open_app", {"app_name": "Chrome"})
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.loop_type, "identical_action")
        self.assertIn("exceeded maximum identical execution threshold", dec.reason)

    # 4. Dictionary key order produces identical fingerprint
    def test_key_order_same_fingerprint(self):
        fp1 = compute_fingerprint("test_tool", {"a": 1, "b": "hello", "c": True})
        fp2 = compute_fingerprint("test_tool", {"c": True, "a": 1, "b": "hello"})
        self.assertEqual(fp1, fp2)

    # 5. Different arguments produce different fingerprints
    def test_different_arguments_different_fingerprints(self):
        fp1 = compute_fingerprint("open_app", {"app_name": "Chrome"})
        fp2 = compute_fingerprint("open_app", {"app_name": "Safari"})
        self.assertNotEqual(fp1, fp2)

    # 6. Failure tracking works correctly
    def test_failure_tracking(self):
        fp = compute_fingerprint("failing_tool", {})
        self.guard.register_action("failing_tool", {})
        self.guard.register_result(fp, success=False, error="Test error")
        self.assertEqual(self.guard._failure_counts[fp], 1)

        # Success resets failure count
        self.guard.register_result(fp, success=True)
        self.assertEqual(self.guard._failure_counts[fp], 0)

    # 7. Repeated failure triggers block
    def test_repeated_failure_triggers_block(self):
        fp = compute_fingerprint("failing_tool", {})
        for _ in range(3):
            self.guard.register_action("failing_tool", {})
            self.guard.register_result(fp, success=False, error="Crash")

        # 4th attempt blocked by max failures
        dec = self.guard.register_action("failing_tool", {})
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.loop_type, "max_failures")

    # 8. A-B-A-B Ping-pong pattern detected
    def test_ping_pong_abab_detected(self):
        # A
        self.guard.register_action("open_browser", {"url": "https://google.com"})
        # B
        self.guard.register_action("verify_browser", {"status": "check"})
        # A
        self.guard.register_action("open_browser", {"url": "https://google.com"})
        # B (projected 4th action makes A-B-A-B cycle)
        dec = self.guard.register_action("verify_browser", {"status": "check"})
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.loop_type, "ping_pong")

    # 9. A-B-C-A-B-C Cycle detected
    def test_ping_pong_abcabc_detected(self):
        # A, B, C
        self.guard.register_action("tool_a", {})
        self.guard.register_action("tool_b", {})
        self.guard.register_action("tool_c", {})
        # A, B
        self.guard.register_action("tool_a", {})
        self.guard.register_action("tool_b", {})
        # C (projected 6th action makes A-B-C-A-B-C cycle)
        dec = self.guard.register_action("tool_c", {})
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.loop_type, "ping_pong")

    # 10. Destructive action does not auto-repeat after failure
    def test_destructive_no_auto_repeat(self):
        fp = compute_fingerprint("delete_database", {"target": "prod"})
        self.guard.register_action("delete_database", {"target": "prod"}, permission_level="destructive")
        self.guard.register_result(fp, success=False, error="Permission denied")

        # Second attempt must be blocked
        dec = self.guard.register_action("delete_database", {"target": "prod"}, permission_level="destructive")
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.loop_type, "destructive_retry")

    # 11. Reset clears state
    def test_reset_clears_state(self):
        for _ in range(3):
            self.guard.register_action("open_app", {"app_name": "Chrome"})
        
        self.guard.reset()
        dec = self.guard.register_action("open_app", {"app_name": "Chrome"})
        self.assertTrue(dec.allowed)
        self.assertEqual(dec.action_count, 1)

    # 12. Orchestrator integration terminates safely on loop block
    def test_orchestrator_loopguard_integration(self):
        reg = ToolRegistry()
        call_count = 0

        def failing_exec(params, player=None):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Repeated fatal failure")

        reg.register(Tool(
            name="looping_failing_tool",
            description="Tool that always fails",
            parameters={},
            execute=failing_exec,
            permission_level="low_risk",
        ))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Try 1", tool="looping_failing_tool"),
            PlanStep(id=2, description="Try 2", tool="looping_failing_tool"),
            PlanStep(id=3, description="Try 3", tool="looping_failing_tool"),
            PlanStep(id=4, description="Try 4", tool="looping_failing_tool"),
        ]
        orch.current_plan = Plan(goal="Looping test", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Looping test")
        self.assertEqual(res["status"], "failed")
        self.assertIn("plan", res)


if __name__ == "__main__":
    unittest.main()
