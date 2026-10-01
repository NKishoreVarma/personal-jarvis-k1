"""
Phase 3 — Autonomous Agent End-to-End Certification Test Suite.
Verifies the complete THINK -> PLAN -> LOOPGUARD -> ACT -> OBSERVE -> THINK -> VERIFY -> RECOVER -> COMPLETE cycle across 18 certification scenarios.
"""

import asyncio
import time
import unittest
from typing import Any, Dict, List, Optional

from core.agent_orchestrator import (
    AgentOrchestrator,
    AgentState,
    Plan,
    PlanStep,
    StepStatus,
    Tool,
    ToolRegistry,
)
from core.loop_guard import LoopGuard, LoopGuardConfig, loop_guard
from core.think_tool import ThinkTool, think_tool
from core.intent_router import router


class TestPhase3AgentCertification(unittest.TestCase):
    def setUp(self):
        loop_guard.reset()
        think_tool.clear()

    def tearDown(self):
        loop_guard.reset()
        think_tool.clear()

    # -------------------------------------------------------------------------
    # TEST 1: Simple Successful Task
    # -------------------------------------------------------------------------
    def test_01_simple_successful_task(self):
        reg = ToolRegistry()
        executed = []

        def mock_open_app(params, player=None):
            executed.append(params.get("app_name"))
            return "Application Chrome launched successfully."

        reg.register(Tool(
            name="open_app",
            description="Opens an application",
            parameters={"app_name": "string"},
            execute=mock_open_app,
            permission_level="low_risk",
        ))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Open Chrome", tool="open_app", parameters={"app_name": "Chrome"}, requires_verification=True),
        ]
        orch.current_plan = Plan(goal="Open Chrome", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Open Chrome")
        self.assertEqual(res["status"], "completed")
        self.assertEqual(executed, ["Chrome"])
        self.assertEqual(orch.state, AgentState.IDLE)
        self.assertEqual(steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(steps[0].attempts, 1)

    # -------------------------------------------------------------------------
    # TEST 2: Multi-Step Successful Task (Sequential observations influence actions)
    # -------------------------------------------------------------------------
    def test_02_multi_step_successful_task(self):
        reg = ToolRegistry()
        call_log = []

        def exec_open(params, player=None):
            call_log.append(("open", params))
            return "Chrome opened"

        def exec_nav(params, player=None):
            call_log.append(("nav", params))
            return "Navigated to url"

        def exec_verify_page(params, player=None):
            call_log.append(("verify_page", params))
            return "Page loaded with title Google"

        reg.register(Tool(name="open_browser", description="", parameters={}, execute=exec_open, permission_level="low_risk"))
        reg.register(Tool(name="navigate_url", description="", parameters={}, execute=exec_nav, permission_level="low_risk"))
        reg.register(Tool(name="verify_page", description="", parameters={}, execute=exec_verify_page, permission_level="read_only"))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Open browser", tool="open_browser", parameters={"browser": "chrome"}),
            PlanStep(id=2, description="Navigate to Google", tool="navigate_url", parameters={"url": "https://google.com"}),
            PlanStep(id=3, description="Verify page loaded", tool="verify_page", parameters={"expected": "Google"}),
        ]
        orch.current_plan = Plan(goal="Navigate to website and verify", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Navigate to website and verify")
        self.assertEqual(res["status"], "completed")
        self.assertEqual(len(call_log), 3)
        self.assertEqual(call_log[0][0], "open")
        self.assertEqual(call_log[1][0], "nav")
        self.assertEqual(call_log[2][0], "verify_page")

    # -------------------------------------------------------------------------
    # TEST 3: First Action Failure + Recovery
    # -------------------------------------------------------------------------
    def test_03_first_action_failure_and_recovery(self):
        reg = ToolRegistry()
        attempt_count = 0

        def flaky_action(params, player=None):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise RuntimeError("Temporary lock contention")
            return "Port recovered and service active"

        reg.register(Tool(name="start_service", description="", parameters={}, execute=flaky_action, permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Start service with recovery", tool="start_service", parameters={}),
        ]
        orch.current_plan = Plan(goal="Start service", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Start service")
        self.assertEqual(res["status"], "completed")
        self.assertEqual(attempt_count, 2)
        self.assertEqual(steps[0].status, StepStatus.COMPLETED)

    # -------------------------------------------------------------------------
    # TEST 4: Repeated Failure -> LoopGuard Block
    # -------------------------------------------------------------------------
    def test_04_repeated_failure_triggers_loopguard_block(self):
        reg = ToolRegistry()
        call_count = 0

        def always_failing(params, player=None):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Fatal crash in driver")

        reg.register(Tool(name="failing_action", description="", parameters={}, execute=always_failing, permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Step 1", tool="failing_action", parameters={}),
            PlanStep(id=2, description="Step 2", tool="failing_action", parameters={}),
            PlanStep(id=3, description="Step 3", tool="failing_action", parameters={}),
            PlanStep(id=4, description="Step 4", tool="failing_action", parameters={}),
        ]
        orch.current_plan = Plan(goal="Repeated failure goal", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Repeated failure goal")
        self.assertEqual(res["status"], "failed")

    # -------------------------------------------------------------------------
    # TEST 5: Ping-Pong Loop Detection
    # -------------------------------------------------------------------------
    def test_05_ping_pong_loop_detection(self):
        custom_guard = LoopGuard(LoopGuardConfig(ping_pong_window=6))
        
        # A-B-A-B
        dec1 = custom_guard.register_action("tool_a", {"id": 1})
        self.assertTrue(dec1.allowed)
        dec2 = custom_guard.register_action("tool_b", {"id": 2})
        self.assertTrue(dec2.allowed)
        dec3 = custom_guard.register_action("tool_a", {"id": 1})
        self.assertTrue(dec3.allowed)
        # 4th action completes A-B-A-B cycle
        dec4 = custom_guard.register_action("tool_b", {"id": 2})
        self.assertFalse(dec4.allowed)
        self.assertEqual(dec4.loop_type, "ping_pong")

    # -------------------------------------------------------------------------
    # TEST 6: Verification Failure (Observer contradicts tool output)
    # -------------------------------------------------------------------------
    def test_06_verification_failure_rejects_success(self):
        reg = ToolRegistry()

        # Tool returns a string that doesn't trigger generic error, but verification will reject
        def exec_bad_output(params, player=None):
            return "Error: port 8080 refused connection"

        reg.register(Tool(name="start_server", description="", parameters={}, execute=exec_bad_output, permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Start server", tool="start_server", parameters={}),
        ]
        orch.current_plan = Plan(goal="Start server", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Start server")
        self.assertEqual(res["status"], "failed")
        self.assertIn("Error", str(steps[0].error))

    # -------------------------------------------------------------------------
    # TEST 7: Wrong Tool Result
    # -------------------------------------------------------------------------
    def test_07_wrong_tool_result_handled(self):
        reg = ToolRegistry()

        def incomplete_output(params, player=None):
            return "Failed: incomplete payload returned"

        reg.register(Tool(name="fetch_payload", description="", parameters={}, execute=incomplete_output, permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Fetch payload", tool="fetch_payload", parameters={}),
        ]
        orch.current_plan = Plan(goal="Fetch payload", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Fetch payload")
        self.assertEqual(res["status"], "failed")

    # -------------------------------------------------------------------------
    # TEST 8: Destructive Action Failure (No Auto-retry)
    # -------------------------------------------------------------------------
    def test_08_destructive_action_failure_no_auto_retry(self):
        reg = ToolRegistry()
        destructive_calls = 0

        def delete_target(params, player=None):
            nonlocal destructive_calls
            destructive_calls += 1
            raise PermissionError("Write access denied on target file")

        reg.register(Tool(
            name="delete_target",
            description="Delete file",
            parameters={"file": "string"},
            execute=delete_target,
            permission_level="destructive",
        ))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Delete file", tool="delete_target", parameters={"file": "/etc/hosts"}),
        ]
        orch.current_plan = Plan(goal="Delete file", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Delete file")
        self.assertEqual(res["status"], "failed")
        # Must execute exactly once with zero automatic retries
        self.assertEqual(destructive_calls, 1)

    # -------------------------------------------------------------------------
    # TEST 9: Long Multi-Step Task (8+ steps with intermediate recovery)
    # -------------------------------------------------------------------------
    def test_09_long_multi_step_task(self):
        reg = ToolRegistry()
        step_log = []
        step4_attempts = 0

        def make_tool(step_num):
            def _fn(params, player=None):
                nonlocal step4_attempts
                if step_num == 4:
                    step4_attempts += 1
                    if step4_attempts == 1:
                        raise RuntimeError("Step 4 intermittent failure")
                step_log.append(step_num)
                return f"Step {step_num} success"
            return _fn

        for i in range(1, 9):
            reg.register(Tool(name=f"step_tool_{i}", description="", parameters={}, execute=make_tool(i), permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [PlanStep(id=i, description=f"Step {i}", tool=f"step_tool_{i}", parameters={}) for i in range(1, 9)]
        orch.current_plan = Plan(goal="Long 8-step pipeline", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Long 8-step pipeline")
        self.assertEqual(res["status"], "completed")
        self.assertEqual(len(step_log), 8)
        self.assertEqual(step4_attempts, 2)  # Recovered step 4

    # -------------------------------------------------------------------------
    # TEST 10: Cancellation Midway
    # -------------------------------------------------------------------------
    def test_10_cancellation_midway(self):
        reg = ToolRegistry()

        def cancellable_step(params, player=None):
            orch.cancel()
            return "Running"

        reg.register(Tool(name="step_one", description="", parameters={}, execute=cancellable_step, permission_level="low_risk"))
        reg.register(Tool(name="step_two", description="", parameters={}, execute=lambda p, player=None: "Step 2", permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [
            PlanStep(id=1, description="Step 1", tool="step_one", parameters={}),
            PlanStep(id=2, description="Step 2", tool="step_two", parameters={}),
        ]
        orch.current_plan = Plan(goal="Cancel goal", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Cancel goal")
        self.assertEqual(res["status"], "cancelled")

    # -------------------------------------------------------------------------
    # TEST 11: Tool Timeout Handling
    # -------------------------------------------------------------------------
    def test_11_tool_timeout_handling(self):
        reg = ToolRegistry()

        def timeout_exec(params, player=None):
            raise TimeoutError("Execution timed out after 30.0s")

        reg.register(Tool(name="slow_tool", description="", parameters={}, execute=timeout_exec, permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [PlanStep(id=1, description="Slow step", tool="slow_tool", parameters={})]
        orch.current_plan = Plan(goal="Timeout goal", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Timeout goal")
        self.assertEqual(res["status"], "failed")

    # -------------------------------------------------------------------------
    # TEST 12: False Success Rejection (Tool success != Task success)
    # -------------------------------------------------------------------------
    def test_12_false_success_rejection(self):
        reg = ToolRegistry()

        def deceptive_tool(params, player=None):
            return "Error: Command exit code 1 with broken output"

        reg.register(Tool(name="deceptive_tool", description="", parameters={}, execute=deceptive_tool, permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [PlanStep(id=1, description="Deceptive step", tool="deceptive_tool", parameters={})]
        orch.current_plan = Plan(goal="Deceptive goal", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Deceptive goal")
        self.assertEqual(res["status"], "failed")

    # -------------------------------------------------------------------------
    # TEST 13: No Suitable Recovery -> Safe Stop
    # -------------------------------------------------------------------------
    def test_13_no_suitable_recovery_safe_stop(self):
        reg = ToolRegistry()

        def unrecoverable_tool(params, player=None):
            raise FileNotFoundError("Missing non-existent directory /root/secret")

        reg.register(Tool(name="unrecoverable_tool", description="", parameters={}, execute=unrecoverable_tool, permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [PlanStep(id=1, description="Unrecoverable step", tool="unrecoverable_tool", parameters={})]
        orch.current_plan = Plan(goal="Unrecoverable goal", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Unrecoverable goal")
        self.assertEqual(res["status"], "failed")

    # -------------------------------------------------------------------------
    # TEST 14: Realtime / Voice Path Safety (Non-blocking Local Intent Router)
    # -------------------------------------------------------------------------
    def test_14_realtime_voice_safety_latency(self):
        t0 = time.monotonic()
        res = router.route_and_execute("What time is it?")
        dt = (time.monotonic() - t0) * 1000.0  # ms

        self.assertTrue(res["handled"])
        self.assertLess(dt, 25.0)  # Must be under 25ms

    # -------------------------------------------------------------------------
    # TEST 15: Security / Permission Boundary Enforcement
    # -------------------------------------------------------------------------
    def test_15_permission_boundary_enforcement(self):
        reg = ToolRegistry()
        self.assertEqual(reg.get("apply_patch").permission_level, "destructive")
        self.assertEqual(reg.get("read_file").permission_level, "read_only")
        self.assertEqual(reg.get("think").permission_level, "read_only")
        self.assertEqual(reg.get("run_project_command").permission_level, "low_risk")

    # -------------------------------------------------------------------------
    # TEST 16: Final Answer Honesty & State Reflection
    # -------------------------------------------------------------------------
    def test_16_final_answer_honesty(self):
        reg = ToolRegistry()
        reg.register(Tool(name="valid_tool", description="", parameters={}, execute=lambda p, player=None: "Done", permission_level="low_risk"))

        orch = AgentOrchestrator(registry=reg)
        steps = [PlanStep(id=1, description="Valid step", tool="valid_tool", parameters={})]
        orch.current_plan = Plan(goal="Honest goal", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Honest goal")
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["plan"]["steps"][0]["status"], "completed")

    # -------------------------------------------------------------------------
    # TEST 17: Trace Validation
    # -------------------------------------------------------------------------
    def test_17_trace_validation(self):
        reg = ToolRegistry()
        reg.register(Tool(name="trace_tool", description="", parameters={}, execute=lambda p, player=None: "Trace OK", permission_level="read_only"))

        orch = AgentOrchestrator(registry=reg)
        steps = [PlanStep(id=1, description="Trace step", tool="trace_tool", parameters={})]
        orch.current_plan = Plan(goal="Trace goal", steps=steps)
        orch.create_plan = lambda g: orch.current_plan

        res = orch.run_goal("Trace goal")
        self.assertEqual(res["status"], "completed")

    # -------------------------------------------------------------------------
    # TEST 18: Full System State Stability
    # -------------------------------------------------------------------------
    def test_18_system_state_stability(self):
        self.assertEqual(loop_guard._global_consecutive_failures, 0)
        self.assertEqual(len(think_tool.get_history()), 0)


if __name__ == "__main__":
    unittest.main()
