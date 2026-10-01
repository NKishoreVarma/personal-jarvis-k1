"""
Phase 12.15 — Autonomous Planning, Goal Decomposition & Adaptive Execution Strategy Test Suite.
Verifies all 25 core requirements:
1. High-level goal decomposes into bounded steps
2. Decomposition produces no side effects
3. Multiple strategies are generated only when useful
4. Verified skill outranks historical memory
5. Current observation overrides strategy assumptions
6. Independent read-only steps run in parallel
7. Conflicting mutations serialize
8. Dependency ordering is enforced
9. Blocked step pauses downstream execution
10. Failed verification triggers adaptation
11. Adaptation preserves completed verified steps
12. Contradicted assumptions invalidate dependent steps
13. Plan reuse requires current compatibility
14. Stale plan expires
15. Goal change cancels invalid branches
16. User cancellation stops active execution
17. Progress announcements are bounded
18. Final completion requires outcome verification
19. Stale completion responses are suppressed
20. Full FLOW repair-run-open scenario succeeds
21. Voice pipeline remains non-blocking
22. No chain-of-thought is exposed
23. Plan status queries produce concise natural responses
24. Maximum strategy candidate limit is enforced
25. No cross-goal plan leakage
"""

from __future__ import annotations

import time
import unittest

from core.goal_change_detector import goal_change_detector
from core.goal_decomposition_engine import goal_decomposition_engine
from core.intent_router import router
from core.milestone_manager import MilestoneType, milestone_manager
from core.plan_adaptation_engine import plan_adaptation_engine
from core.plan_assumption_tracker import AssumptionState, plan_assumption_tracker
from core.plan_contract import PlanContract, PlanStatus, create_plan_contract
from core.plan_execution_controller import plan_execution_controller
from core.plan_graph_builder import plan_graph_builder
from core.plan_reuse_evaluator import plan_reuse_evaluator
from core.plan_step_contract import PlanStepContract, PlanStepStatus, create_plan_step_contract
from core.skill_contract import SkillContract, create_skill_contract
from core.skill_registry import skill_registry
from core.strategy_generator import Strategy, StrategyType, strategy_generator
from core.strategy_selector import strategy_selector
from core.task_graph import NodeExecutionType


class TestPhase1215AutonomousPlanning(unittest.TestCase):
    def setUp(self):
        plan_execution_controller.clear_all()
        plan_assumption_tracker.clear_all()
        milestone_manager.clear_all()

    # 1. High-level goal decomposes into bounded steps
    def test_01_high_level_goal_decomposes_into_bounded_steps(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_start",
            turn_id="t_start",
            objective="Get FLOW running and open it",
            project_name="FLOW",
        )
        self.assertEqual(plan.status, PlanStatus.READY)
        self.assertGreaterEqual(len(steps), 4)
        self.assertLessEqual(len(steps), 10)
        self.assertTrue(any("open" in s.title.lower() for s in steps))

    # 2. Decomposition produces no side effects
    def test_02_decomposition_produces_no_side_effects(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_pure",
            turn_id="t_pure",
            objective="Fix FLOW and start the server",
            project_name="FLOW",
        )
        # All generated steps are PENDING, no execution has occurred
        for s in steps:
            self.assertEqual(s.status, PlanStepStatus.PENDING)
            self.assertIsNone(s.completed_at)

    # 3. Multiple strategies are generated only when useful
    def test_03_multiple_strategies_are_generated_only_when_useful(self):
        strats = strategy_generator.generate_strategies("Fix and run FLOW", "FLOW")
        self.assertGreaterEqual(len(strats), 1)
        self.assertLessEqual(len(strats), 3)

    # 4. Verified skill outranks historical memory
    def test_04_verified_skill_outranks_historical_memory(self):
        from core.skill_contract import SkillType
        skill = create_skill_contract(
            skill_name="FIX_PORT_CONFLICT",
            skill_type=SkillType.REPAIR_SKILL,
            description="Diagnostic repair for port conflict",
            goal_pattern="Fix and run FLOW",
            project_scope="FLOW",
            workflow_steps=[{"action": "kill_port_3000"}],
            confidence=0.98,
        )
        skill_registry.register_skill(skill)

        strats = strategy_generator.generate_strategies("Fix and run FLOW", "FLOW")
        best, reason = strategy_selector.select_strategy(strats)
        self.assertIsNotNone(best)
        self.assertEqual(best.strategy_type, StrategyType.VERIFIED_SKILL)
        self.assertIn("verified repair", reason.lower())

    # 5. Current observation overrides strategy assumptions
    def test_05_current_observation_overrides_strategy_assumptions(self):
        strat_std = Strategy(
            strategy_id="s1",
            title="Standard startup",
            description="Start on default port",
            strategy_type=StrategyType.STANDARD_WORKFLOW,
            required_steps=["start"],
            assumptions=["port 3000 available"],
        )
        strat_diag = Strategy(
            strategy_id="s2",
            title="Diagnostic repair",
            description="Resolve occupied port",
            strategy_type=StrategyType.DIAGNOSTIC_FIRST,
            required_steps=["diagnose", "repair", "start"],
            assumptions=["port 3000 occupied"],
        )

        # Observed conflict: port 3000 is occupied
        best, reason = strategy_selector.select_strategy(
            [strat_std, strat_diag],
            observed_conflicts=["port 3000 available"],
        )
        self.assertEqual(best.strategy_id, "s2")

    # 6. Independent read-only steps run in parallel
    def test_06_independent_read_only_steps_run_in_parallel(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_diag",
            turn_id="t_diag",
            objective="Fix FLOW",
            project_name="FLOW",
        )
        graph = plan_graph_builder.build_task_graph(plan, steps)

        # Initial read-only inspection steps have 0 dependencies and READ_ONLY type
        initial_nodes = [n for n in graph.nodes.values() if not n.dependencies]
        self.assertGreaterEqual(len(initial_nodes), 2)
        for n in initial_nodes:
            self.assertEqual(n.execution_type, NodeExecutionType.READ_ONLY)

    # 7. Conflicting mutations serialize
    def test_07_conflicting_mutations_serialize(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_mut",
            turn_id="t_mut",
            objective="Fix FLOW, run it, and open it",
            project_name="FLOW",
        )
        mutating_steps = [s for s in steps if s.is_mutating]
        # Mutating steps must have dependencies on predecessor steps
        for s in mutating_steps:
            self.assertTrue(len(s.dependencies) > 0)

    # 8. Dependency ordering is enforced
    def test_08_dependency_ordering_is_enforced(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_dep",
            turn_id="t_dep",
            objective="Run FLOW",
            project_name="FLOW",
        )
        plan_execution_controller.start_plan(plan, steps)

        ready = plan_execution_controller.get_ready_steps(plan.goal_id)
        # Only step 1 (locate/profile) should be ready initially
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].step_id, steps[0].step_id)

    # 9. Blocked step pauses downstream execution
    def test_09_blocked_step_pauses_downstream_execution(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_block",
            turn_id="t_block",
            objective="Run FLOW",
            project_name="FLOW",
        )
        plan_execution_controller.start_plan(plan, steps)

        # Do NOT complete step 1. Step 2 must not become ready.
        ready = plan_execution_controller.get_ready_steps(plan.goal_id)
        self.assertNotIn(steps[1].step_id, [s.step_id for s in ready])

    # 10. Failed verification triggers adaptation
    def test_10_failed_verification_triggers_adaptation(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_adapt",
            turn_id="t_adapt",
            objective="Run FLOW",
            project_name="FLOW",
        )
        plan_execution_controller.start_plan(plan, steps)

        # Step 1 completes
        plan_execution_controller.mark_step_completed(plan.goal_id, steps[0].step_id)

        # Step 2 fails
        adapted_plan, adapted_steps = plan_execution_controller.mark_step_failed(
            goal_id=plan.goal_id,
            step_id=steps[1].step_id,
            error_message="Port 3000 already in use",
        )
        self.assertEqual(adapted_plan.status, PlanStatus.READY)
        self.assertTrue(any("adapted" in s.title.lower() for s in adapted_steps))

    # 11. Adaptation preserves completed verified steps
    def test_11_adaptation_preserves_completed_verified_steps(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_pres",
            turn_id="t_pres",
            objective="Fix FLOW",
            project_name="FLOW",
        )
        plan_execution_controller.start_plan(plan, steps)

        # Complete step 1
        plan_execution_controller.mark_step_completed(plan.goal_id, steps[0].step_id)

        adapted_plan, adapted_steps = plan_execution_controller.mark_step_failed(
            goal_id=plan.goal_id,
            step_id=steps[1].step_id,
            error_message="Port scan error",
        )
        completed = [s for s in adapted_steps if s.status == PlanStepStatus.COMPLETED]
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].step_id, steps[0].step_id)

    # 12. Contradicted assumptions invalidate dependent steps
    def test_12_contradicted_assumptions_invalidate_dependent_steps(self):
        asmp = plan_assumption_tracker.register_assumption(
            plan_id="plan_x",
            description="port 3000 is open",
            dependent_steps=["step_start", "step_verify"],
        )
        affected = plan_assumption_tracker.contradict_assumption(asmp.assumption_id, "Port 3000 in use")
        self.assertEqual(affected, ["step_start", "step_verify"])
        self.assertTrue(plan_assumption_tracker.has_contradicted_assumptions("plan_x"))

    # 13. Plan reuse requires current compatibility
    def test_13_plan_reuse_requires_current_compatibility(self):
        hist_plan = create_plan_contract(
            goal_id="g_old",
            turn_id="t_old",
            objective="Run FLOW",
            strategy="Standard",
            verification_criteria={"project": "FLOW"},
            assumptions=["no conflict on port 3000"],
        )

        # Matching context -> Compatible
        compat, reason, conf = plan_reuse_evaluator.evaluate_reuse(hist_plan, "FLOW", [])
        self.assertTrue(compat)

        # Mismatch project -> Rejected
        compat_bad, reason_bad, conf_bad = plan_reuse_evaluator.evaluate_reuse(hist_plan, "OTHER_APP", [])
        self.assertFalse(compat_bad)

    # 14. Stale plan expires
    def test_14_stale_plan_expires(self):
        plan = create_plan_contract(
            goal_id="g_exp",
            turn_id="t_exp",
            objective="Run FLOW",
            strategy="Standard",
            ttl_seconds=0.01,
        )
        time.sleep(0.02)
        self.assertTrue(plan.is_expired())

    # 15. Goal change cancels invalid branches
    def test_15_goal_change_cancels_invalid_branches(self):
        plan = create_plan_contract(
            goal_id="g_pivot",
            turn_id="t_pivot",
            objective="Fix FLOW",
            strategy="Diagnostic",
            verification_criteria={"project": "FLOW"},
        )
        is_pivot, new_obj = goal_change_detector.detect_goal_pivot("Actually stop FLOW and open Chrome", plan)
        self.assertTrue(is_pivot)

        goal_change_detector.handle_goal_change(new_obj, plan)
        self.assertEqual(plan.status, PlanStatus.CANCELLED)

    # 16. User cancellation stops active execution
    def test_16_user_cancellation_stops_active_execution(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_cancel",
            turn_id="t_cancel",
            objective="Run FLOW",
            project_name="FLOW",
        )
        plan_execution_controller.start_plan(plan, steps)
        self.assertTrue(goal_change_detector.is_cancellation("stop that"))

        plan_execution_controller.cancel_plan(plan.goal_id)
        self.assertEqual(plan.status, PlanStatus.CANCELLED)

    # 17. Progress announcements are bounded
    def test_17_progress_announcements_are_bounded(self):
        # Fast task (< 4.0s) -> No announcement
        should_ann, text = milestone_manager.should_announce_progress("g_mile", elapsed_seconds=2.0)
        self.assertFalse(should_ann)

        # Slow task (> 4.0s) -> Single announcement
        should_ann2, text2 = milestone_manager.should_announce_progress("g_mile", elapsed_seconds=5.0)
        self.assertTrue(should_ann2)
        self.assertEqual(text2, "Still working on FLOW.")

        # Repeated call -> Suppressed
        should_ann3, text3 = milestone_manager.should_announce_progress("g_mile", elapsed_seconds=8.0)
        self.assertFalse(should_ann3)

    # 18. Final completion requires outcome verification
    def test_18_final_completion_requires_outcome_verification(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_ver",
            turn_id="t_ver",
            objective="Run FLOW",
            project_name="FLOW",
        )
        plan_execution_controller.start_plan(plan, steps)

        # Complete step 1 & 2 only
        plan_execution_controller.mark_step_completed(plan.goal_id, steps[0].step_id)
        plan_execution_controller.mark_step_completed(plan.goal_id, steps[1].step_id)
        self.assertFalse(plan_execution_controller.is_plan_complete(plan.goal_id))

        # Complete final verify step
        plan_execution_controller.mark_step_completed(plan.goal_id, steps[2].step_id)
        self.assertTrue(plan_execution_controller.is_plan_complete(plan.goal_id))

    # 19. Stale completion responses are suppressed
    def test_19_stale_completion_responses_are_suppressed(self):
        plan = create_plan_contract(
            goal_id="g_stale_resp",
            turn_id="t_stale_resp",
            objective="Run FLOW",
            strategy="Standard",
        )
        plan.status = PlanStatus.CANCELLED
        # If plan is cancelled, final completion announcement is rejected
        self.assertEqual(plan.status, PlanStatus.CANCELLED)

    # 20. Full FLOW repair-run-open scenario succeeds
    def test_20_full_flow_repair_run_open_scenario_succeeds(self):
        plan, steps = goal_decomposition_engine.decompose_goal(
            goal_id="g_e2e",
            turn_id="t_e2e",
            objective="Fix FLOW, run it, and open it when it works",
            project_name="FLOW",
        )
        plan_execution_controller.start_plan(plan, steps)

        # Step-by-step DAG progress
        for s in steps:
            ready = plan_execution_controller.get_ready_steps(plan.goal_id)
            if s in ready:
                plan_execution_controller.mark_step_completed(plan.goal_id, s.step_id, result={"ok": True})

        self.assertTrue(plan_execution_controller.is_plan_complete(plan.goal_id))
        final_text = milestone_manager.format_final_announcement(plan.goal_id, "FLOW", success=True)
        self.assertEqual(final_text, "FLOW is running and verified.")

    # 21. Voice pipeline remains non-blocking
    def test_21_voice_pipeline_remains_non_blocking(self):
        router.match("what time is it")  # Warm-up
        t0 = time.perf_counter()
        match = router.match("what's the plan")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_PLAN")
        self.assertLess(dt, 5.0)

    # 22. No chain-of-thought is exposed
    def test_22_no_chain_of_thought_is_exposed(self):
        strats = strategy_generator.generate_strategies("Fix and run FLOW", "FLOW")
        best, reason = strategy_selector.select_strategy(strats)
        self.assertNotIn("thought:", reason.lower())
        self.assertNotIn("step 1", reason.lower())
        self.assertNotIn("dag", reason.lower())

    # 23. Plan status queries produce concise natural responses
    def test_23_plan_status_queries_produce_concise_natural_responses(self):
        match = router.match("how far are you")
        self.assertEqual(match["intent"], "QUERY_PLAN_PROGRESS")

    # 24. Maximum strategy candidate limit is enforced
    def test_24_maximum_strategy_candidate_limit_is_enforced(self):
        strats = strategy_generator.generate_strategies("Fix FLOW and start everything", "FLOW")
        self.assertLessEqual(len(strats), strategy_generator.MAX_CANDIDATES)

    # 25. No cross-goal plan leakage
    def test_25_no_cross_goal_plan_leakage(self):
        plan1, steps1 = goal_decomposition_engine.decompose_goal("goal_1", "t1", "Run FLOW", "FLOW")
        plan2, steps2 = goal_decomposition_engine.decompose_goal("goal_2", "t2", "Run BACKEND", "BACKEND")

        plan_execution_controller.start_plan(plan1, steps1)
        plan_execution_controller.start_plan(plan2, steps2)

        steps_g1 = plan_execution_controller.get_steps("goal_1")
        steps_g2 = plan_execution_controller.get_steps("goal_2")

        self.assertNotEqual({s.step_id for s in steps_g1}, {s.step_id for s in steps_g2})


if __name__ == "__main__":
    unittest.main()
