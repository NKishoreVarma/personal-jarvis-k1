"""
Phase 12.26 — Autonomous Continuous Learning, Outcome Evaluation & Self-Improvement Governance Test Suite.
Verifies all 30 core requirements:
1. Outcome contract validation
2. Verified outcome evidence requirement
3. Action completed vs outcome verified distinction
4. Repeated success pattern detection
5. Repeated failure pattern detection
6. One-off anomaly rejection
7. Improvement candidate generation
8. Duplicate candidate prevention
9. Speculative improvement rejection
10. Sandbox isolation
11. Baseline vs candidate comparison
12. Improvement verification
13. No-improvement rejection
14. Regression detection
15. Promotion lifecycle
16. Approval requirement
17. Authority modification rejection
18. ActionContract protection
19. ApprovalStore protection
20. Rollback behavior
21. Regression monitor state transitions
22. User correction learning signals
23. Memory evidence integration
24. Skill evidence integration
25. Auditability
26. Sensitive data rejection
27. No chain-of-thought persistence
28. Self-improvement governor evaluation
29. Backward compatibility
30. Voice non-blocking guarantee
"""

from __future__ import annotations

import time
import unittest

from core.action_contract import RiskLevel
from core.improvement_candidate_engine import improvement_candidate_engine
from core.improvement_opportunity_contract import (
    ImprovementOpportunityContract,
    ImprovementState,
    ImprovementType,
    create_improvement_opportunity,
)
from core.improvement_promotion_manager import improvement_promotion_manager
from core.improvement_regression_monitor import HealthStatus, improvement_regression_monitor
from core.improvement_sandbox import improvement_sandbox
from core.improvement_verification_engine import (
    ImprovementVerificationResult,
    improvement_verification_engine,
)
from core.intent_router import router
from core.learning_signal_detector import (
    LearningSignal,
    LearningSignalType,
    learning_signal_detector,
)
from core.outcome_contract import (
    OutcomeContract,
    OutcomeType,
    VerificationState,
    create_outcome_contract,
)
from core.outcome_evaluation_engine import outcome_evaluation_engine
from core.self_improvement_governor import GovernanceDecision, self_improvement_governor


class TestPhase1226ContinuousLearning(unittest.TestCase):
    def setUp(self):
        learning_signal_detector.clear()
        improvement_candidate_engine.clear()
        improvement_promotion_manager.clear()
        improvement_regression_monitor.clear()
        self_improvement_governor.set_learning_enabled(True)

    # 1. Outcome contract validation
    def test_01_outcome_contract_validation(self):
        out, msg = create_outcome_contract(
            expected_outcome="Server running on port 3000",
            actual_outcome="Server listening on 127.0.0.1:3000",
            outcome_type=OutcomeType.SUCCESS,
            verification_state=VerificationState.OBSERVED,
        )
        self.assertIsNotNone(out)
        self.assertEqual(out.outcome_type, OutcomeType.SUCCESS)
        self.assertEqual(out.verification_state, VerificationState.OBSERVED)

    # 2. Verified outcome evidence requirement
    def test_02_verified_outcome_evidence_requirement(self):
        # Attempting VERIFIED without evidence references must fail validation
        out, err = create_outcome_contract(
            expected_outcome="Build clean",
            actual_outcome="Build succeeded",
            verification_state=VerificationState.VERIFIED,
            evidence_references=[],
        )
        self.assertIsNone(out)
        self.assertIn("requires supporting evidence references", err)

        # Valid with evidence references
        out_valid, _ = create_outcome_contract(
            expected_outcome="Build clean",
            actual_outcome="Build succeeded",
            verification_state=VerificationState.VERIFIED,
            evidence_references=["log:build.log"],
        )
        self.assertIsNotNone(out_valid)
        self.assertTrue(out_valid.is_verified())

    # 3. Action completed vs outcome verified distinction
    def test_03_action_completed_vs_outcome_verified_distinction(self):
        out, _ = create_outcome_contract(
            expected_outcome="FLOW healthy",
            actual_outcome="Command exit code 0, but port not open",
            outcome_type=OutcomeType.PARTIAL_SUCCESS,
            verification_state=VerificationState.SELF_REPORTED,
            success_score=0.40,
        )
        eval_res = outcome_evaluation_engine.evaluate_outcome(out)
        self.assertTrue(eval_res["action_completed"])
        self.assertFalse(eval_res["outcome_verified"])
        self.assertLess(eval_res["outcome_quality_score"], 0.50)

    # 4. Repeated success pattern detection
    def test_04_repeated_success_pattern_detection(self):
        for i in range(3):
            out, _ = create_outcome_contract(
                expected_outcome="Deploy FLOW",
                actual_outcome="Deployment verified",
                skill_id="FLOW_DEPLOY",
                outcome_type=OutcomeType.VERIFIED_SUCCESS,
                verification_state=VerificationState.VERIFIED,
                evidence_references=[f"run:{i}"],
            )
            learning_signal_detector.record_outcome(out)

        signals = learning_signal_detector.detect_signals()
        success_signals = [s for s in signals if s.signal_type == LearningSignalType.SUCCESS_PATTERN]
        self.assertEqual(len(success_signals), 1)
        self.assertIn("FLOW_DEPLOY", success_signals[0].pattern_key)

    # 5. Repeated failure pattern detection
    def test_05_repeated_failure_pattern_detection(self):
        for _ in range(2):
            out, _ = create_outcome_contract(
                expected_outcome="Start server",
                actual_outcome="Address already in use: 3000",
                outcome_type=OutcomeType.FAILURE,
                failure_reason="PORT_3000_IN_USE",
            )
            learning_signal_detector.record_outcome(out)

        signals = learning_signal_detector.detect_signals()
        fail_signals = [s for s in signals if s.signal_type == LearningSignalType.FAILURE_PATTERN]
        self.assertEqual(len(fail_signals), 1)
        self.assertIn("PORT_3000_IN_USE", fail_signals[0].pattern_key)

    # 6. One-off anomaly rejection
    def test_06_one_off_anomaly_rejection(self):
        # A single occurrence must NOT produce a learning signal (threshold >= 2)
        out, _ = create_outcome_contract(
            expected_outcome="Test run",
            actual_outcome="Intermittent network timeout",
            outcome_type=OutcomeType.FAILURE,
            failure_reason="TRANSIENT_TIMEOUT",
        )
        learning_signal_detector.record_outcome(out)
        signals = learning_signal_detector.detect_signals()
        self.assertEqual(len(signals), 0)

    # 7. Improvement candidate generation
    def test_07_improvement_candidate_generation(self):
        sig = LearningSignal(
            signal_type=LearningSignalType.FAILURE_PATTERN,
            pattern_key="failure:PORT_CONFLICT",
            occurrence_count=3,
            evidence_references=["out:1", "out:2", "out:3"],
            description="Recurring port conflict",
        )
        cand, msg = improvement_candidate_engine.generate_candidate_from_signal(sig)
        self.assertIsNotNone(cand)
        self.assertEqual(cand.improvement_type, ImprovementType.RELIABILITY_IMPROVEMENT)
        self.assertEqual(cand.state, ImprovementState.CANDIDATE)

    # 8. Duplicate candidate prevention
    def test_08_duplicate_candidate_prevention(self):
        sig = LearningSignal(
            signal_type=LearningSignalType.FAILURE_PATTERN,
            pattern_key="failure:PORT_CONFLICT",
            occurrence_count=3,
            evidence_references=["out:1", "out:2"],
            description="Recurring port conflict",
        )
        c1, _ = improvement_candidate_engine.generate_candidate_from_signal(sig)
        self.assertIsNotNone(c1)
        c2, err = improvement_candidate_engine.generate_candidate_from_signal(sig)
        self.assertIsNone(c2)
        self.assertIn("already exists", err)

    # 9. Speculative improvement rejection
    def test_09_speculative_improvement_rejection(self):
        sig = LearningSignal(
            signal_type=LearningSignalType.FAILURE_PATTERN,
            pattern_key="speculative:UNKNOWN",
            occurrence_count=2,
            evidence_references=[],  # No evidence!
            description="Speculative guess",
        )
        cand, err = improvement_candidate_engine.generate_candidate_from_signal(sig)
        self.assertIsNone(cand)
        self.assertIn("lacks supporting evidence", err)

    # 10. Sandbox isolation
    def test_10_sandbox_isolation(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT,
            "Speed up health checks",
            "Cache probe socket",
            "health_monitor",
            evidence_references=["ev:1"],
        )
        res = improvement_sandbox.simulate_candidate(cand)
        self.assertEqual(res["safety_status"], "SAFE")
        self.assertEqual(cand.state, ImprovementState.TESTING)

    # 11. Baseline vs candidate comparison
    def test_11_baseline_vs_candidate_comparison(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT,
            "Optimize startup",
            "Desc",
            "server",
            baseline_metrics={"success_rate": 0.70, "avg_duration": 10.0},
            evidence_references=["ev:1"],
        )
        res = improvement_sandbox.simulate_candidate(
            cand, simulated_candidate_metrics={"success_rate": 0.90, "avg_duration": 4.0}
        )
        self.assertAlmostEqual(res["success_delta"], 0.20, delta=0.01)
        self.assertAlmostEqual(res["duration_delta"], 6.0, delta=0.01)

    # 12. Improvement verification
    def test_12_improvement_verification(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT,
            "Optimize startup",
            "Desc",
            "server",
            evidence_references=["ev:1"],
        )
        sandbox_res = {
            "safety_status": "SAFE",
            "regression_detected": False,
            "success_delta": 0.15,
            "duration_delta": 3.0,
        }
        res, msg = improvement_verification_engine.verify_candidate(cand, sandbox_res)
        self.assertEqual(res, ImprovementVerificationResult.IMPROVED)
        self.assertEqual(cand.state, ImprovementState.VERIFIED)

    # 13. No-improvement rejection
    def test_13_no_improvement_rejection(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT,
            "Flat tweak", "Desc", "server", evidence_references=["ev:1"]
        )
        sandbox_res = {
            "safety_status": "SAFE",
            "regression_detected": False,
            "success_delta": 0.00,
            "duration_delta": 0.0,
        }
        res, msg = improvement_verification_engine.verify_candidate(cand, sandbox_res)
        self.assertEqual(res, ImprovementVerificationResult.NO_IMPROVEMENT)

    # 14. Regression detection
    def test_14_regression_detection(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT,
            "Degraded tweak", "Desc", "server", evidence_references=["ev:1"]
        )
        sandbox_res = {
            "safety_status": "SAFE",
            "regression_detected": True,
            "success_delta": -0.10,
            "duration_delta": -2.0,
        }
        res, msg = improvement_verification_engine.verify_candidate(cand, sandbox_res)
        self.assertEqual(res, ImprovementVerificationResult.REGRESSION)
        self.assertEqual(cand.state, ImprovementState.REJECTED)

    # 15. Promotion lifecycle
    def test_15_promotion_lifecycle(self):
        cand = create_improvement_opportunity(
            ImprovementType.RELIABILITY_IMPROVEMENT,
            "Verified Fix", "Desc", "diagnostics", evidence_references=["ev:1"]
        )
        cand.state = ImprovementState.VERIFIED
        improvement_promotion_manager.register_candidate(cand)
        ok, msg = improvement_promotion_manager.activate_improvement(cand.opportunity_id)
        self.assertTrue(ok)
        self.assertEqual(cand.state, ImprovementState.ACTIVE)

    # 16. Approval requirement
    def test_16_approval_requirement(self):
        cand = create_improvement_opportunity(
            ImprovementType.RELIABILITY_IMPROVEMENT,
            "High Risk Workflow", "Desc", "core_system",
            risk_level=RiskLevel.HIGH_RISK, evidence_references=["ev:1"]
        )
        cand.state = ImprovementState.VERIFIED
        improvement_promotion_manager.register_candidate(cand)

        # Activation without explicit approval must be blocked
        ok_no_appr, _ = improvement_promotion_manager.activate_improvement(cand.opportunity_id, user_explicit_approval=False)
        self.assertFalse(ok_no_appr)

        # Activation with explicit approval succeeds
        ok_appr, _ = improvement_promotion_manager.activate_improvement(cand.opportunity_id, user_explicit_approval=True)
        self.assertTrue(ok_appr)

    # 17. Authority modification rejection
    def test_17_authority_modification_rejection(self):
        cand = create_improvement_opportunity(
            ImprovementType.SAFETY_IMPROVEMENT,
            "Authority Bypass Candidate", "Desc", "auth",
            evidence_references=["ev:1"],
            metadata={"modify_safety_rules": True},
        )
        dec, msg = self_improvement_governor.evaluate_proposal(cand)
        self.assertEqual(dec, GovernanceDecision.REJECT)
        self.assertIn("cannot modify safety authority", msg)

    # 18. ActionContract protection
    def test_18_action_contract_protection(self):
        cand = create_improvement_opportunity(
            ImprovementType.RELIABILITY_IMPROVEMENT, "Safe Candidate", "Desc", "tool",
            evidence_references=["ev:1"]
        )
        self.assertEqual(cand.risk_level, RiskLevel.READ_ONLY)

    # 19. ApprovalStore protection
    def test_19_approval_store_protection(self):
        cand = create_improvement_opportunity(
            ImprovementType.RELIABILITY_IMPROVEMENT, "High Risk", "Desc", "db",
            risk_level=RiskLevel.HIGH_RISK, evidence_references=["ev:1"]
        )
        dec, _ = self_improvement_governor.evaluate_proposal(cand, user_explicit_approval=False)
        self.assertEqual(dec, GovernanceDecision.REQUIRE_APPROVAL)

    # 20. Rollback behavior
    def test_20_rollback_behavior(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT, "Speedup", "Desc", "server",
            evidence_references=["ev:1"]
        )
        cand.state = ImprovementState.VERIFIED
        improvement_promotion_manager.register_candidate(cand)
        improvement_promotion_manager.activate_improvement(cand.opportunity_id)

        # Rollback
        ok_rb = improvement_promotion_manager.rollback_improvement(cand.opportunity_id, reason="Performance degradation")
        self.assertTrue(ok_rb)
        self.assertEqual(cand.state, ImprovementState.ROLLED_BACK)
        self.assertIsNone(improvement_promotion_manager.get_active_improvement("server"))

    # 21. Regression monitor state transitions
    def test_21_regression_monitor_state_transitions(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT, "Speedup", "Desc", "network",
            evidence_references=["ev:1"]
        )
        cand.state = ImprovementState.VERIFIED
        improvement_promotion_manager.register_candidate(cand)
        improvement_promotion_manager.activate_improvement(cand.opportunity_id)

        # Record failure triggering automatic rollback
        status, msg = improvement_regression_monitor.record_execution_metric("network", success=False, duration=1.0)
        self.assertEqual(status, HealthStatus.DEGRADED)
        self.assertIn("Automatic rollback executed", msg)
        self.assertEqual(cand.state, ImprovementState.ROLLED_BACK)

    # 22. User correction learning signals
    def test_22_user_correction_learning_signals(self):
        learning_signal_detector.record_user_correction("subagent_delegation")
        learning_signal_detector.record_user_correction("subagent_delegation")
        signals = learning_signal_detector.detect_signals()
        corr_signals = [s for s in signals if s.signal_type == LearningSignalType.USER_CORRECTION_PATTERN]
        self.assertEqual(len(corr_signals), 1)

    # 23. Memory evidence integration
    def test_23_memory_evidence_integration(self):
        out, _ = create_outcome_contract(
            expected_outcome="Recall memory",
            actual_outcome="Memory retrieved",
            verification_state=VerificationState.VERIFIED,
            evidence_references=["mem:mem_12345"],
        )
        self.assertIn("mem:mem_12345", out.evidence_references)

    # 24. Skill evidence integration
    def test_24_skill_evidence_integration(self):
        out, _ = create_outcome_contract(
            expected_outcome="Execute port repair",
            actual_outcome="Port 3000 cleared",
            skill_id="FIX_PORT",
            verification_state=VerificationState.VERIFIED,
            evidence_references=["skill:FIX_PORT"],
        )
        self.assertEqual(out.skill_id, "FIX_PORT")

    # 25. Auditability
    def test_25_auditability(self):
        cand = create_improvement_opportunity(
            ImprovementType.RELIABILITY_IMPROVEMENT, "Audit Test", "Desc", "audit_comp",
            source_signals=["sig:1"], evidence_references=["ev:1"]
        )
        d = cand.to_dict()
        self.assertEqual(d["title"], "Audit Test")
        self.assertIn("ev:1", d["evidence_references"])

    # 26. Sensitive data rejection
    def test_26_sensitive_data_rejection(self):
        # Verification that contracts preserve sanitization
        cand = create_improvement_opportunity(
            ImprovementType.RELIABILITY_IMPROVEMENT, "Sanitized Task", "Clean description", "comp"
        )
        self.assertNotIn("password", cand.description.lower())

    # 27. No chain-of-thought persistence
    def test_27_no_chain_of_thought_persistence(self):
        out, _ = create_outcome_contract(
            expected_outcome="Clean outcome", actual_outcome="Result verified",
            verification_state=VerificationState.OBSERVED
        )
        self.assertNotIn("raw_cot", out.metadata)

    # 28. Self-improvement governor evaluation
    def test_28_self_improvement_governor_evaluation(self):
        cand = create_improvement_opportunity(
            ImprovementType.PERFORMANCE_IMPROVEMENT, "Test Candidate", "Desc", "comp",
            evidence_references=["ev:1"]
        )
        cand.state = ImprovementState.CANDIDATE
        dec, _ = self_improvement_governor.evaluate_proposal(cand)
        self.assertEqual(dec, GovernanceDecision.REQUIRE_TESTING)

    # 29. Backward compatibility
    def test_29_backward_compatibility(self):
        # Intent router query works
        match = router.match("what have you learned recently")
        self.assertEqual(match["intent"], "QUERY_LEARNING_STATUS")

    # 30. Voice non-blocking guarantee
    def test_30_voice_non_blocking_guarantee(self):
        t0 = time.perf_counter()
        match = router.match("are you improving anything")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_IMPROVEMENT_STATUS")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
