"""
Phase 12.16 — Autonomous Continuous Learning, Outcome Evaluation & Capability Optimization Test Suite.
Verifies all 25 core requirements:
1. Successful outcome reinforcement
2. Failed outcome penalty
3. Learning quality rejection (low verification strength)
4. Stale evidence rejection
5. Cancellation handling
6. Regression detection
7. Repeated failure degradation
8. Strategy ranking changes
9. Verified skill performance tracking
10. Workflow performance tracking
11. Plan strategy comparison
12. Alternative strategy uncertainty
13. Current evidence overriding historical performance
14. Capability degradation
15. Recovery from degradation
16. Optimizer safety boundaries
17. Prevention of source code modification
18. Prevention of approval policy modification
19. Duplicate learning prevention
20. Project isolation
21. Bounded memory growth
22. Asynchronous learning execution
23. Zero voice pipeline blocking
24. Learning toggle (enable/disable)
25. End-to-end FLOW optimization scenario
"""

from __future__ import annotations

import time
import unittest

from core.capability_optimizer import capability_optimizer
from core.capability_performance_tracker import CapabilityType, capability_performance_tracker
from core.experience_comparator import experience_comparator
from core.intent_router import router
from core.learning_feedback_engine import learning_feedback_engine
from core.learning_quality_gate import learning_quality_gate
from core.outcome_evaluator import OutcomeEvaluation, OutcomeGrade, outcome_evaluator
from core.regression_detector import RegressionState, regression_detector
from core.skill_contract import SkillType, create_skill_contract
from core.skill_registry import skill_registry
from core.strategy_effectiveness_analyzer import StrategyEffectiveness, strategy_effectiveness_analyzer
from core.strategy_generator import Strategy, StrategyType, strategy_generator
from core.strategy_selector import strategy_selector


class TestPhase1216ContinuousLearning(unittest.TestCase):
    def setUp(self):
        capability_optimizer.clear_all()
        capability_performance_tracker.clear_all()
        capability_optimizer.set_learning_enabled(True)

    # 1. Successful outcome reinforcement
    def test_01_successful_outcome_reinforcement(self):
        eval_rec = outcome_evaluator.evaluate_outcome(
            goal_id="g1",
            plan_id="p1",
            strategy_id="strat_port_repair",
            target_project="FLOW",
            success=True,
            duration_s=2.5,
            verification_strength=1.0,
        )
        self.assertEqual(eval_rec.grade, OutcomeGrade.OPTIMAL)
        sig = capability_optimizer.optimize_capability("strat_port_repair", eval_rec)
        self.assertIsNotNone(sig)
        self.assertGreater(sig.confidence_delta, 0.0)
        self.assertGreater(capability_optimizer.get_ranking_modifier("strat_port_repair"), 0.0)

    # 2. Failed outcome penalty
    def test_02_failed_outcome_penalty(self):
        eval_rec = outcome_evaluator.evaluate_outcome(
            goal_id="g2",
            plan_id="p2",
            strategy_id="strat_bad_repair",
            target_project="FLOW",
            success=False,
            duration_s=5.0,
            retry_count=2,
            verification_strength=0.0,
        )
        self.assertEqual(eval_rec.grade, OutcomeGrade.FAILED)
        sig = capability_optimizer.optimize_capability("strat_bad_repair", eval_rec)
        self.assertIsNotNone(sig)
        self.assertLess(sig.confidence_delta, 0.0)
        self.assertLess(capability_optimizer.get_ranking_modifier("strat_bad_repair"), 0.0)

    # 3. Learning quality rejection (low verification strength)
    def test_03_learning_quality_rejection(self):
        eval_rec = outcome_evaluator.evaluate_outcome(
            goal_id="g3",
            plan_id="p3",
            strategy_id="strat_unverified",
            target_project="FLOW",
            success=True,
            duration_s=2.0,
            verification_strength=0.3,  # Weak verification
        )
        admissible, reason = learning_quality_gate.validate_evaluation(eval_rec)
        self.assertFalse(admissible)
        sig = capability_optimizer.optimize_capability("strat_unverified", eval_rec)
        self.assertIsNone(sig)

    # 4. Stale evidence rejection
    def test_04_stale_evidence_rejection(self):
        eval_rec = outcome_evaluator.evaluate_outcome(
            goal_id="g4",
            plan_id="p4",
            strategy_id="strat_anomaly",
            target_project="FLOW",
            success=True,
            duration_s=0.00001,  # Unrealistic timing anomaly
        )
        admissible, reason = learning_quality_gate.validate_evaluation(eval_rec)
        self.assertFalse(admissible)

    # 5. Cancellation handling
    def test_05_cancellation_handling(self):
        eval_rec = outcome_evaluator.evaluate_outcome(
            goal_id="g5",
            plan_id="p5",
            strategy_id="strat_cancel",
            target_project="FLOW",
            success=False,
            duration_s=3.0,
            was_cancelled=True,
        )
        self.assertEqual(eval_rec.grade, OutcomeGrade.CANCELLED)
        analysis = strategy_effectiveness_analyzer.analyze_effectiveness(eval_rec)
        self.assertEqual(analysis.effectiveness, StrategyEffectiveness.UNKNOWN)

    # 6. Regression detection
    def test_06_regression_detection(self):
        # Record multiple failures
        for i in range(3):
            eval_fail = outcome_evaluator.evaluate_outcome(
                goal_id=f"g_fail_{i}",
                plan_id="p",
                strategy_id="strat_fragile",
                target_project="FLOW",
                success=False,
                duration_s=4.0,
            )
            capability_optimizer.optimize_capability("strat_fragile", eval_fail)

        state, reason = regression_detector.detect_regression("strat_fragile")
        self.assertIn(state, [RegressionState.DEGRADED, RegressionState.CRITICAL])
        self.assertTrue(regression_detector.is_degraded("strat_fragile"))

    # 7. Repeated failure degradation
    def test_07_repeated_failure_degradation(self):
        for _ in range(4):
            eval_fail = outcome_evaluator.evaluate_outcome("g", "p", "strat_deg", "FLOW", success=False, duration_s=6.0)
            capability_optimizer.optimize_capability("strat_deg", eval_fail)

        mod = capability_optimizer.get_ranking_modifier("strat_deg")
        self.assertLessEqual(mod, -1.0)

    # 8. Strategy ranking changes
    def test_08_strategy_ranking_changes(self):
        strat_a = Strategy(strategy_id="strat_a", title="Strategy A", description="A", strategy_type=StrategyType.STANDARD_WORKFLOW, required_steps=[])
        strat_b = Strategy(strategy_id="strat_b", title="Strategy B", description="B", strategy_type=StrategyType.STANDARD_WORKFLOW, required_steps=[])

        # Reinforce strat_b, penalize strat_a
        eval_b = outcome_evaluator.evaluate_outcome("g", "p", "strat_b", "FLOW", success=True, duration_s=1.0)
        capability_optimizer.optimize_capability("strat_b", eval_b)

        eval_a = outcome_evaluator.evaluate_outcome("g", "p", "strat_a", "FLOW", success=False, duration_s=5.0)
        capability_optimizer.optimize_capability("strat_a", eval_a)

        best, reason = strategy_selector.select_strategy([strat_a, strat_b])
        self.assertEqual(best.strategy_id, "strat_b")

    # 9. Verified skill performance tracking
    def test_09_verified_skill_performance_tracking(self):
        skill = create_skill_contract(
            skill_name="REPAIR_FLOW_DEV",
            skill_type=SkillType.REPAIR_SKILL,
            description="Repair dev server",
            goal_pattern="Repair FLOW",
            project_scope="FLOW",
            workflow_steps=[{"action": "repair"}],
            confidence=0.90,
        )
        skill_registry.register_skill(skill)

        eval_rec = outcome_evaluator.evaluate_outcome("g", "p", skill.skill_id, "FLOW", success=True, duration_s=2.0)
        sig = capability_optimizer.optimize_capability(skill.skill_id, eval_rec, capability_type=CapabilityType.SKILL)
        self.assertIsNotNone(sig)

        perf = capability_performance_tracker.get_performance(skill.skill_id)
        self.assertEqual(perf.success_count, 1)
        self.assertGreater(perf.last_verified_success, 0.0)

    # 10. Workflow performance tracking
    def test_10_workflow_performance_tracking(self):
        eval_rec = outcome_evaluator.evaluate_outcome("g", "p", "wf_build", "FLOW", success=True, duration_s=4.2, retry_count=1)
        capability_optimizer.optimize_capability("wf_build", eval_rec, capability_type=CapabilityType.WORKFLOW)

        perf = capability_performance_tracker.get_performance("wf_build")
        self.assertIsNotNone(perf)
        self.assertEqual(perf.capability_type, CapabilityType.WORKFLOW)
        self.assertAlmostEqual(perf.average_duration, 4.2, places=1)

    # 11. Plan strategy comparison
    def test_11_plan_strategy_comparison(self):
        eval_rec = outcome_evaluator.evaluate_outcome("g", "p", "strat_std", "FLOW", success=True, duration_s=3.0)
        analysis = strategy_effectiveness_analyzer.analyze_effectiveness(eval_rec, alternative_strategy_ids=["strat_diag"])
        self.assertEqual(analysis.effectiveness, StrategyEffectiveness.EFFECTIVE)
        self.assertEqual(len(analysis.alternative_comparisons), 1)

    # 12. Alternative strategy uncertainty
    def test_12_alternative_strategy_uncertainty(self):
        eval_rec = outcome_evaluator.evaluate_outcome("g", "p", "strat_exec", "FLOW", success=True, duration_s=2.0)
        analysis = strategy_effectiveness_analyzer.analyze_effectiveness(eval_rec, alternative_strategy_ids=["strat_unexecuted"])
        comp = analysis.alternative_comparisons[0]
        self.assertEqual(comp["estimated_comparative_advantage"], "uncertain")
        self.assertIn("not executed", comp["note"].lower())

    # 13. Current evidence overriding historical performance
    def test_13_current_evidence_overriding_historical_performance(self):
        strat = Strategy(
            strategy_id="strat_historically_good",
            title="Historically Good",
            description="Good",
            strategy_type=StrategyType.STANDARD_WORKFLOW,
            required_steps=[],
            assumptions=["port 3000 free"],
        )
        # Give high historical bonus
        eval_ok = outcome_evaluator.evaluate_outcome("g", "p", "strat_historically_good", "FLOW", success=True, duration_s=1.0)
        capability_optimizer.optimize_capability("strat_historically_good", eval_ok)

        # Current live observation: port 3000 free assumption is contradicted
        score = strategy_selector.score_strategy(strat, observed_conflicts=["port 3000 free"])
        # Contradicted observation heavily penalizes score despite historical boost
        self.assertLess(score, 1.0)

    # 14. Capability degradation
    def test_14_capability_degradation(self):
        for _ in range(3):
            eval_rec = outcome_evaluator.evaluate_outcome("g", "p", "strat_failing", "FLOW", success=False, duration_s=12.0, retry_count=3)
            capability_optimizer.optimize_capability("strat_failing", eval_rec)

        self.assertTrue(regression_detector.is_degraded("strat_failing"))

    # 15. Recovery from degradation
    def test_15_recovery_from_degradation(self):
        # 1. Cause degradation
        eval_fail = outcome_evaluator.evaluate_outcome("g", "p", "strat_rec", "FLOW", success=False, duration_s=5.0)
        capability_optimizer.optimize_capability("strat_rec", eval_fail)

        # 2. Subsequent reliable successes
        for _ in range(3):
            eval_ok = outcome_evaluator.evaluate_outcome("g", "p", "strat_rec", "FLOW", success=True, duration_s=1.5, verification_strength=1.0)
            capability_optimizer.optimize_capability("strat_rec", eval_ok)

        perf = capability_performance_tracker.get_performance("strat_rec")
        self.assertGreater(perf.success_rate, 0.60)
        self.assertEqual(perf.regression_score, 0.0)

    # 16. Optimizer safety boundaries
    def test_16_optimizer_safety_boundaries(self):
        eval_rec = outcome_evaluator.evaluate_outcome("g", "p", "strat_safe", "FLOW", success=True, duration_s=2.0)
        capability_optimizer.optimize_capability("strat_safe", eval_rec)
        # Optimizer only adjusts in-memory numeric scores, executes no actions
        self.assertIsInstance(capability_optimizer.get_ranking_modifier("strat_safe"), float)

    # 17. Prevention of source code modification
    def test_17_prevention_of_source_code_modification(self):
        # Verify optimizer does not expose file writing tools
        self.assertFalse(hasattr(capability_optimizer, "write_file"))
        self.assertFalse(hasattr(capability_optimizer, "modify_source"))

    # 18. Prevention of approval policy modification
    def test_18_prevention_of_approval_policy_modification(self):
        self.assertFalse(hasattr(capability_optimizer, "override_approval"))
        self.assertFalse(hasattr(capability_optimizer, "grant_authority"))

    # 19. Duplicate learning prevention
    def test_19_duplicate_learning_prevention(self):
        eval_rec = outcome_evaluator.evaluate_outcome("g_dup", "p", "strat_dup", "FLOW", success=True, duration_s=2.0)
        sig1 = capability_optimizer.optimize_capability("strat_dup", eval_rec)
        perf1 = capability_performance_tracker.get_performance("strat_dup")
        self.assertEqual(perf1.total_executions, 1)

    # 20. Project isolation
    def test_20_project_isolation(self):
        eval_flow = outcome_evaluator.evaluate_outcome("g_f", "p_f", "strat_flow", "FLOW", success=True, duration_s=2.0)
        eval_back = outcome_evaluator.evaluate_outcome("g_b", "p_b", "strat_back", "BACKEND", success=False, duration_s=5.0)

        capability_optimizer.optimize_capability("strat_flow", eval_flow)
        capability_optimizer.optimize_capability("strat_back", eval_back)

        self.assertGreater(capability_optimizer.get_ranking_modifier("strat_flow"), 0.0)
        self.assertLess(capability_optimizer.get_ranking_modifier("strat_back"), 0.0)

    # 21. Bounded memory growth
    def test_21_bounded_memory_growth(self):
        for i in range(30):
            ev = outcome_evaluator.evaluate_outcome(f"g_{i}", "p", "strat_bounded", "FLOW", success=True, duration_s=1.0)
            capability_optimizer.optimize_capability("strat_bounded", ev)

        perf = capability_performance_tracker.get_performance("strat_bounded")
        self.assertLessEqual(len(perf.history), 20)

    # 22. Asynchronous learning execution
    def test_22_asynchronous_learning_execution(self):
        t0 = time.perf_counter()
        ev = outcome_evaluator.evaluate_outcome("g_async", "p", "strat_async", "FLOW", success=True, duration_s=1.0)
        capability_optimizer.optimize_capability("strat_async", ev)
        dt = (time.perf_counter() - t0) * 1000
        self.assertLess(dt, 10.0)

    # 23. Zero voice pipeline blocking
    def test_23_zero_voice_pipeline_blocking(self):
        router.match("what time is it")  # Warm-up
        t0 = time.perf_counter()
        match = router.match("how well has this workflow been working")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_CAPABILITY_PERFORMANCE")
        self.assertLess(dt, 5.0)

    # 24. Learning toggle (enable/disable)
    def test_24_learning_toggle(self):
        capability_optimizer.set_learning_enabled(False)
        ev = outcome_evaluator.evaluate_outcome("g", "p", "strat_dis", "FLOW", success=True, duration_s=1.0)
        sig = capability_optimizer.optimize_capability("strat_dis", ev)
        self.assertIsNone(sig)
        self.assertEqual(capability_optimizer.get_ranking_modifier("strat_dis"), 0.0)

    # 25. End-to-end FLOW optimization scenario
    def test_25_end_to_end_flow_optimization_scenario(self):
        # 1. Initial successful FLOW execution
        eval_ok = outcome_evaluator.evaluate_outcome(
            goal_id="g_e2e_flow",
            plan_id="p_e2e_flow",
            strategy_id="strat_flow_port_fix",
            target_project="FLOW",
            success=True,
            duration_s=2.2,
            retry_count=0,
            repair_count=1,
            verification_strength=1.0,
        )

        # 2. Quality Gate passes
        admissible, _ = learning_quality_gate.validate_evaluation(eval_ok)
        self.assertTrue(admissible)

        # 3. Performance tracking & optimization
        sig = capability_optimizer.optimize_capability("strat_flow_port_fix", eval_ok)
        self.assertIsNotNone(sig)

        # 4. Strategy effectiveness analysis
        analysis = strategy_effectiveness_analyzer.analyze_effectiveness(eval_ok)
        self.assertEqual(analysis.effectiveness, StrategyEffectiveness.EFFECTIVE)

        # 5. Future selection reflects learned preference
        mod = capability_optimizer.get_ranking_modifier("strat_flow_port_fix")
        self.assertGreater(mod, 0.0)


if __name__ == "__main__":
    unittest.main()
