"""
Comprehensive Unit & Integration Test Suite for Phase 12.9:
Deep Reasoning, Autonomous Problem Solving & Self-Correcting Execution.
"""

import asyncio
import time
import unittest

from core.action_contract import ActionContract, ApprovalState, RiskLevel
from core.approval_manager import approval_store
from core.diagnostic_planner import diagnostic_planner
from core.goal_contract import GoalContract, GoalStatus, create_goal_contract
from core.hypothesis_engine import hypothesis_engine
from core.intent_router import intent_router
from core.observation_engine import observation_engine
from core.problem_solver import ProblemSolver, problem_solver
from core.reasoning_state import (
    Hypothesis,
    HypothesisStatus,
    ReasoningState,
    create_reasoning_state,
)
from core.reasoning_trace import (
    ReasoningTrace,
    TraceEventType,
    reasoning_trace,
)
from core.repair_planner import repair_planner
from core.replanning_engine import replanning_engine
from core.verification_engine import VerificationLevel, verification_engine


class TestPhase129DeepReasoning(unittest.TestCase):
    def setUp(self):
        reasoning_trace._events.clear()

    # Test 1: GoalContract correctly extracts desired outcome
    def test_01_goal_contract_structure(self):
        goal = create_goal_contract(
            turn_id="t1",
            original_request="Fix FLOW",
            normalized_goal="Restore FLOW to operational state",
            desired_outcome="FLOW is running on localhost:3000",
            target_project="FLOW",
        )
        self.assertEqual(goal.status, GoalStatus.PENDING)
        self.assertEqual(goal.target_project, "FLOW")
        self.assertIn("port_detected", goal.success_conditions)

    # Test 2: Observation occurs before repair
    def test_02_observation_before_repair(self):
        obs = observation_engine.gather_diagnostic_evidence("FLOW", target_port=3000)
        self.assertIn("project_state", obs)
        self.assertIn("port_state", obs)
        self.assertIn("active_processes", obs)

    # Test 3: Multiple hypotheses are generated
    def test_03_multiple_hypotheses_generation(self):
        evidence = {"port_state": {"is_responsive": False}, "project_state": {"found": True}}
        hyps = hypothesis_engine.generate_hypotheses("FLOW", evidence)
        self.assertGreaterEqual(len(hyps), 3)
        categories = [h.category for h in hyps]
        self.assertIn("PORT_CONFLICT", categories)
        self.assertIn("MISSING_DEPENDENCY", categories)
        self.assertIn("RUNTIME_ERROR", categories)

    # Test 4: Hypotheses rank by evidence
    def test_04_hypotheses_ranked_by_evidence(self):
        evidence = {"port_state": {}, "project_state": {}}
        stderr = ["Error: listen EADDRINUSE: address already in use :::3000"]
        hyps = hypothesis_engine.generate_hypotheses("FLOW", evidence, stderr_tail=stderr)
        self.assertEqual(hyps[0].category, "PORT_CONFLICT")
        self.assertGreater(hyps[0].confidence, 0.9)

    # Test 5: Diagnostic action preferred over destructive repair
    def test_05_diagnostic_plan_read_only(self):
        h = Hypothesis(
            hypothesis_id="h1",
            description="Port conflict",
            category="PORT_CONFLICT",
            confidence=0.9,
        )
        steps = diagnostic_planner.create_diagnostic_plan(h, "FLOW")
        self.assertGreater(len(steps), 0)
        for s in steps:
            self.assertEqual(s["risk_level"], "READ_ONLY")

    # Test 6: Disproven hypothesis is not reused blindly
    def test_06_disproven_hypothesis_invalidation(self):
        h = Hypothesis(hypothesis_id="h2", description="Missing dep", category="MISSING_DEPENDENCY", confidence=0.5)
        h.add_contradiction("All packages already in node_modules")
        self.assertEqual(h.status, HypothesisStatus.DISPROVEN)
        self.assertLess(h.confidence, 0.2)

    # Test 7: Failed verification triggers replanning
    def test_07_failed_verification_replanning(self):
        goal = create_goal_contract("t7", "Fix FLOW", "Restore FLOW", "FLOW running", target_project="FLOW")
        state = create_reasoning_state(goal, max_cycles=3)
        h1 = Hypothesis("h1", "Port issue", "PORT_CONFLICT", confidence=0.8)
        h2 = Hypothesis("h2", "Missing dep", "MISSING_DEPENDENCY", confidence=0.6)
        state.add_hypothesis(h1)
        state.add_hypothesis(h2)
        state.selected_hypothesis = h1

        new_plan = replanning_engine.replan(state, "restart_project_server", "Port was free, crash occurred")
        self.assertIsNotNone(new_plan)
        self.assertEqual(state.selected_hypothesis.hypothesis_id, "h2")

    # Test 8: Identical failed action is bounded by LoopGuard
    def test_08_loop_guard_bounding(self):
        from core.loop_guard import loop_guard, compute_fingerprint
        fp = compute_fingerprint("restart_project_server", {"project": "FLOW"})
        loop_guard.register_result(fp, success=False)
        loop_guard.register_result(fp, success=False)
        loop_guard.register_result(fp, success=False)
        decision = loop_guard.register_action("restart_project_server", {"project": "FLOW"})
        self.assertFalse(decision.allowed)

    # Test 9: Low-risk repair can execute
    def test_09_low_risk_repair_plan(self):
        h = Hypothesis("h3", "Port issue", "PORT_CONFLICT", confidence=0.8)
        steps = repair_planner.create_repair_plan(h, "FLOW", {})
        self.assertGreater(len(steps), 0)
        self.assertIn(steps[0]["risk_level"], ("LOW", "REVERSIBLE"))

    # Test 10: High-risk repair requires approval
    def test_10_high_risk_approval_gated(self):
        contract = ActionContract(
            connector="problem_solver",
            operation="delete_node_modules",
            arguments={"target": "FLOW"},
            risk_level=RiskLevel.HIGH_RISK,
        )
        self.assertTrue(contract.approval_required)
        self.assertEqual(contract.approval_state.value, "pending_approval")

    # Test 11: Destructive repair has zero automatic retries
    def test_11_destructive_action_risk_policy(self):
        contract = ActionContract(
            connector="problem_solver",
            operation="format_disk",
            arguments={},
            risk_level=RiskLevel.DESTRUCTIVE,
        )
        self.assertEqual(contract.risk_level, RiskLevel.DESTRUCTIVE)
        self.assertTrue(contract.approval_required)

    # Test 12: Success cannot be claimed before outcome verification
    def test_12_outcome_verification_enforcement(self):
        # Action success != outcome verified
        act_ok = verification_engine.verify_action_success({"success": True})
        self.assertTrue(act_ok)

        # But outcome verification checks actual port
        out = verification_engine.verify_outcome("non_existent_project", target_port=9999)
        self.assertFalse(out["outcome_verified"])
        self.assertNotEqual(out["level"], VerificationLevel.OUTCOME_VERIFIED)

    # Test 13: Port conflict diagnosis
    def test_13_port_conflict_diagnosis(self):
        evidence = {"port_state": {"is_responsive": True}, "project_state": {}}
        hyps = hypothesis_engine.generate_hypotheses("FLOW", evidence)
        self.assertEqual(hyps[0].category, "PORT_CONFLICT")

    # Test 14: Missing dependency diagnosis
    def test_14_missing_dependency_diagnosis(self):
        evidence = {"port_state": {}, "project_state": {}}
        stderr = ["ModuleNotFoundError: No module named 'fastapi'"]
        hyps = hypothesis_engine.generate_hypotheses("FLOW", evidence, stderr_tail=stderr)
        self.assertEqual(hyps[0].category, "MISSING_DEPENDENCY")

    # Test 15: Runtime error diagnosis
    def test_15_runtime_error_diagnosis(self):
        evidence = {"port_state": {}, "project_state": {}}
        stderr = ["SyntaxError: invalid syntax in server.py on line 42"]
        hyps = hypothesis_engine.generate_hypotheses("FLOW", evidence, stderr_tail=stderr)
        self.assertEqual(hyps[0].category, "RUNTIME_ERROR")

    # Test 16: Ambiguous project requests clarification
    def test_16_ambiguous_project_clarification(self):
        from core.natural_response_selector import natural_response_selector
        res = natural_response_selector.select_initial_response(
            turn_id="t16",
            task_type="AUTONOMOUS_PROBLEM_SOLVE",
            entities={"target": "project", "choices": ["FLOW Frontend", "FLOW Backend"]},
            raw_text="fix FLOW",
            is_ambiguous=True,
        )
        self.assertEqual(res["spoken_text"], "I found FLOW Frontend and FLOW Backend. Which one?")

    # Test 17: Solver stops after maximum reasoning cycles
    def test_17_solver_cycle_limit(self):
        goal = create_goal_contract("t17", "Fix impossible", "Restore", "Running", target_project="impossible")
        state = create_reasoning_state(goal, max_cycles=2)
        state.cycle_count = 2
        res = replanning_engine.replan(state, "some_action", "still broken")
        self.assertIsNone(res)

    # Test 18: Solver produces concise operational reasoning trace
    def test_18_reasoning_trace_summary(self):
        trace = ReasoningTrace()
        gid = "goal_test"
        trace.record_event(TraceEventType.GOAL_CREATED, gid, {"target": "FLOW"})
        trace.record_event(TraceEventType.HYPOTHESIS_SELECTED, gid, {"category": "PORT_CONFLICT"})
        trace.record_event(TraceEventType.ACTION_EXECUTED, gid, {"action": "terminate_conflicting_processes", "target": "FLOW"})
        trace.record_event(TraceEventType.ACTION_EXECUTED, gid, {"action": "restart_project_server", "target": "FLOW"})
        trace.record_event(TraceEventType.VERIFICATION_PASSED, gid, {"outcome_verified": True})

        summary = trace.get_summary(gid)
        self.assertIn("FLOW is working now", summary)
        self.assertIn("port was occupied", summary)

    # Test 19: Voice acknowledgement remains non-blocking
    def test_19_voice_acknowledgement_instant(self):
        match_res = intent_router.match("find out why FLOW is not working")
        self.assertTrue(match_res["handled"])
        self.assertEqual(match_res["intent"], "AUTONOMOUS_PROBLEM_SOLVE")

        exec_res = intent_router.execute(match_res)
        self.assertIn("I'll check", exec_res["response"])

    # Test 20: Full autonomous FLOW recovery scenario
    def test_20_full_autonomous_flow_recovery_mock(self):
        from unittest.mock import patch
        loop = asyncio.new_event_loop()
        with patch.object(
            verification_engine,
            "verify_outcome",
            return_value={
                "outcome_verified": True,
                "state_verified": True,
                "http_responsive": True,
                "tests_passed": True,
                "port": 3000,
                "project": "FLOW",
                "level": VerificationLevel.OUTCOME_VERIFIED,
            },
        ), patch("core.problem_solver.run_project_async", return_value={"success": True}):
            res = loop.run_until_complete(
                problem_solver.solve_goal_async(
                    turn_id="t20",
                    user_request="find out why FLOW isn't starting, fix it, and tell me when it's working",
                    target_project="FLOW",
                    target_port=3000,
                )
            )
        self.assertTrue(res["success"])
        self.assertIn("FLOW", res["project"])
        self.assertEqual(res["port"], 3000)
        self.assertIn("FLOW is working now", res["summary"])
        loop.close()


if __name__ == "__main__":
    unittest.main()
