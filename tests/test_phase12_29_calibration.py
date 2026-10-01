"""
Phase 12.29 — Autonomous Decision Calibration & Adaptive System-1 Governance Test Suite.
Verifies all 35+ requirements:
1. Outcome record creation
2. Verified outcome handling
3. Unknown outcome handling (does not count as incorrect)
4. Confidence calibration
5. Bucket calibration
6. Accuracy calculation
7. Brier score calculation
8. Route-specific calibration
9. Language-specific calibration
10. Checkpoint-specific calibration
11. Minimum sample enforcement
12. Policy proposal creation
13. Shadow policy proposal
14. Policy versioning
15. Policy rollback
16. Drift detection
17. Stable state
18. Warning state
19. Degraded state
20. Automatic System 2 escalation
21. Recovery
22. Recency weighting
23. System 1 vs System 2 disagreement tracking
24. High-risk threshold cannot be weakened
25. Approval requirements cannot be weakened
26. Verification cannot be bypassed
27. Laya cannot modify its own policy directly
28. Unknown outcomes do not count as incorrect
29. Small sample cannot trigger adaptation
30. Multilingual calibration isolation
31. Checkpoint comparison
32. Latency telemetry
33. Policy version attached to decisions
34. Phase 12.26 continuous learning bridge
35. Developer status commands via intent router
"""

from __future__ import annotations

import time
import unittest

from core.decision_calibration_engine import (
    ConfidenceBucket,
    DecisionCalibrationEngine,
    decision_calibration_engine,
)
from core.decision_confidence_gate import decision_confidence_gate
from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionSource,
    DecisionType,
    create_decision_result,
)
from core.decision_drift_detector import (
    DriftState,
    decision_drift_detector,
)
from core.decision_outcome import (
    DecisionOutcomeRecord,
    OutcomeQuality,
    create_decision_outcome_record,
    decision_outcome_store,
)
from core.decision_policy_proposal import (
    DecisionPolicyManager,
    PolicyProposalStatus,
    decision_policy_manager,
)
from core.decision_policy_router import (
    RoutingMode,
    decision_policy_router,
)
from core.intent_router import router
from core.outcome_contract import OutcomeType, VerificationState, create_outcome_contract
from core.outcome_evaluation_engine import outcome_evaluation_engine
from core.self_improvement_governor import self_improvement_governor
from core.system1_decision_engine import system1_decision_engine


class TestPhase1229Calibration(unittest.TestCase):
    def setUp(self):
        decision_outcome_store.clear()
        decision_drift_detector.reset()
        decision_policy_router.clear_telemetry()
        decision_policy_router.set_mode(RoutingMode.SHADOW)
        system1_decision_engine.set_enabled(True)

    # 1. Outcome record creation
    def test_01_outcome_record_creation(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Please refund my bill",
            selected_option="billing_refund",
            confidence=0.92,
        )
        rec = create_decision_outcome_record(
            decision_result=res,
            system1_used=True,
            policy_version="system1-policy-v1",
        )
        self.assertEqual(rec.decision_id, res.decision_id)
        self.assertEqual(rec.route, DecisionCategory.INTENT)
        self.assertEqual(rec.predicted_option, "billing_refund")
        self.assertEqual(rec.outcome_quality, OutcomeQuality.OUTCOME_UNKNOWN)
        self.assertFalse(rec.outcome_verified)

    # 2. Verified outcome handling
    def test_02_verified_outcome_handling(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Refund my subscription",
            selected_option="billing_refund",
            confidence=0.88,
        )
        rec = create_decision_outcome_record(res)
        decision_outcome_store.add_record(rec)

        updated = decision_outcome_store.update_outcome(
            decision_id=res.decision_id,
            actual_outcome="billing_refund",
            outcome_quality=OutcomeQuality.VERIFIED_CORRECT,
            outcome_verified=True,
            final_decision="billing_refund",
        )
        self.assertTrue(updated)
        stored = decision_outcome_store.get_record(res.decision_id)
        self.assertTrue(stored.outcome_verified)
        self.assertEqual(stored.is_correct(), True)

    # 3. Unknown outcome handling (does not count as incorrect)
    def test_03_unknown_outcome_handling(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Ambiguous query",
            selected_option="general_inquiry",
            confidence=0.80,
        )
        rec = create_decision_outcome_record(res)
        decision_outcome_store.add_record(rec)

        stored = decision_outcome_store.get_record(res.decision_id)
        self.assertIsNone(stored.is_correct())
        self.assertFalse(stored.outcome_verified)

    # 4. Confidence calibration
    def test_04_confidence_calibration(self):
        records = []
        for i in range(12):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Intent query {i}",
                selected_option="opt_a",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT if i < 10 else OutcomeQuality.VERIFIED_INCORRECT
            records.append(rec)

        engine = DecisionCalibrationEngine(min_samples=10)
        report = engine.evaluate_records(records)
        self.assertTrue(report.is_sufficient)
        self.assertAlmostEqual(report.accuracy, 10 / 12, places=3)
        self.assertIsNotNone(report.expected_calibration_error)

    # 5. Bucket calibration
    def test_05_bucket_calibration(self):
        b = ConfidenceBucket(0.80, 0.90)
        b.sample_count = 10
        b.correct_count = 8.0
        b.confidence_sum = 8.5
        self.assertAlmostEqual(b.accuracy, 0.80)
        self.assertAlmostEqual(b.mean_confidence, 0.85)
        self.assertAlmostEqual(b.calibration_gap, 0.05)

    # 6. Accuracy calculation
    def test_06_accuracy_calculation(self):
        records = []
        for i in range(10):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Query {i}",
                selected_option="opt_a",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT if i < 7 else OutcomeQuality.VERIFIED_INCORRECT
            records.append(rec)

        report = decision_calibration_engine.evaluate_records(records)
        self.assertEqual(report.accuracy, 0.70)

    # 7. Brier score calculation
    def test_07_brier_score_calculation(self):
        # Perfect predictions: confidence 1.0, outcome 1.0 -> Brier score = 0.0
        records = []
        for i in range(10):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Query {i}",
                selected_option="opt_a",
                confidence=1.0,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            records.append(rec)

        report = decision_calibration_engine.evaluate_records(records)
        self.assertAlmostEqual(report.brier_score, 0.0, places=4)

    # 8. Route-specific calibration
    def test_08_route_specific_calibration(self):
        for i in range(10):
            res_intent, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Intent {i}",
                selected_option="opt_a",
                confidence=0.90,
            )
            rec1 = create_decision_outcome_record(res_intent)
            rec1.outcome_verified = True
            rec1.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec1)

            res_research, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.RESEARCH,
                context=f"Research {i}",
                selected_option="opt_b",
                confidence=0.75,
            )
            rec2 = create_decision_outcome_record(res_research)
            rec2.outcome_verified = True
            rec2.outcome_quality = OutcomeQuality.VERIFIED_INCORRECT
            decision_outcome_store.add_record(rec2)

        report_intent = decision_calibration_engine.calibrate_category(DecisionCategory.INTENT)
        report_research = decision_calibration_engine.calibrate_category(DecisionCategory.RESEARCH)

        self.assertEqual(report_intent.accuracy, 1.0)
        self.assertEqual(report_research.accuracy, 0.0)
        self.assertGreater(report_intent.route_trust_score, report_research.route_trust_score)

    # 9. Language-specific calibration
    def test_09_language_specific_calibration(self):
        for i in range(10):
            res_es, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Context {i}",
                selected_option="opt_es",
                confidence=0.88,
                language="es",
            )
            rec = create_decision_outcome_record(res_es)
            rec.language = "es"
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec)

        report_es = decision_calibration_engine.calibrate_language("es")
        self.assertEqual(report_es.language, "es")
        self.assertEqual(report_es.accuracy, 1.0)

    # 10. Checkpoint-specific calibration
    def test_10_checkpoint_specific_calibration(self):
        for i in range(10):
            res_cp, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Context {i}",
                selected_option="opt_cp",
                confidence=0.86,
                model_or_checkpoint="convaiinnovations/laya",
            )
            rec = create_decision_outcome_record(res_cp)
            rec.checkpoint = "convaiinnovations/laya"
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec)

        report_cp = decision_calibration_engine.calibrate_checkpoint("convaiinnovations/laya")
        self.assertEqual(report_cp.checkpoint, "convaiinnovations/laya")
        self.assertEqual(report_cp.verified_sample_count, 10)

    # 11. Minimum sample enforcement
    def test_11_minimum_sample_enforcement(self):
        # 3 samples < MIN_SAMPLES (10)
        records = []
        for i in range(3):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Sample {i}",
                selected_option="opt_a",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            records.append(rec)

        report = decision_calibration_engine.evaluate_records(records)
        self.assertFalse(report.is_sufficient)
        self.assertIsNone(report.recommended_threshold)

    # 12. Policy proposal creation
    def test_12_policy_proposal_creation(self):
        proposal, msg = decision_policy_manager.create_proposal(
            route=DecisionCategory.INTENT,
            proposed_threshold=0.82,
            reason="High calibration accuracy observed at 0.82.",
            supporting_sample_count=25,
        )
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.status, PolicyProposalStatus.PROPOSED)
        self.assertEqual(proposal.proposed_policy["threshold"], 0.82)

    # 13. Shadow policy proposal
    def test_13_shadow_policy_proposal(self):
        proposal, _ = decision_policy_manager.create_proposal(
            route=DecisionCategory.AGENT_ROUTING,
            proposed_threshold=0.80,
            reason="Agent routing calibration suggestion.",
            supporting_sample_count=20,
        )
        ok, msg = decision_policy_manager.transition_to_shadow(proposal.proposal_id)
        self.assertTrue(ok)
        self.assertEqual(proposal.status, PolicyProposalStatus.SHADOW_TESTING)
        # Verify active threshold remains unchanged during shadow testing
        self.assertEqual(decision_policy_manager.get_threshold(DecisionCategory.AGENT_ROUTING), 0.75)

    # 14. Policy versioning
    def test_14_policy_versioning(self):
        proposal, _ = decision_policy_manager.create_proposal(
            route=DecisionCategory.SKILL_SELECTION,
            proposed_threshold=0.81,
            reason="Optimized skill threshold.",
            supporting_sample_count=30,
        )
        initial_ver = decision_policy_manager.current_version
        ok, msg = decision_policy_manager.approve_and_activate(proposal.proposal_id)
        self.assertTrue(ok)
        self.assertNotEqual(decision_policy_manager.current_version, initial_ver)
        self.assertEqual(decision_policy_manager.get_threshold(DecisionCategory.SKILL_SELECTION), 0.81)

    # 15. Policy rollback
    def test_15_policy_rollback(self):
        # Create and activate proposal
        proposal, _ = decision_policy_manager.create_proposal(
            route=DecisionCategory.INTENT,
            proposed_threshold=0.83,
            reason="Temporary intent update.",
            supporting_sample_count=15,
        )
        v1 = decision_policy_manager.current_version
        decision_policy_manager.approve_and_activate(proposal.proposal_id)
        v2 = decision_policy_manager.current_version

        # Rollback to v1
        ok, msg = decision_policy_manager.rollback_policy(v1)
        self.assertTrue(ok)
        self.assertEqual(decision_policy_manager.current_version, v1)
        self.assertEqual(decision_policy_manager.get_threshold(DecisionCategory.INTENT), 0.75)

    # 16. Drift detection
    def test_16_drift_detection(self):
        # Initially empty -> STABLE
        assessment = decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(assessment.state, DriftState.STABLE)

    # 17. Stable state
    def test_17_stable_state(self):
        for i in range(15):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Query {i}",
                selected_option="opt_a",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec)

        decision_drift_detector.set_baseline_accuracy("intent", 0.85)
        assessment = decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(assessment.state, DriftState.STABLE)
        self.assertEqual(assessment.threshold_penalty, 0.0)

    # 18. Warning state
    def test_18_warning_state(self):
        # 15 samples with 70% accuracy (drop of 15% from 85% baseline -> WARNING)
        for i in range(15):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Warning test {i}",
                selected_option="opt_a",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT if i < 10 else OutcomeQuality.VERIFIED_INCORRECT
            decision_outcome_store.add_record(rec)

        decision_drift_detector.set_baseline_accuracy("intent", 0.85)
        assessment = decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(assessment.state, DriftState.WARNING)
        self.assertGreater(assessment.threshold_penalty, 0.0)

    # 19. Degraded state
    def test_19_degraded_state(self):
        # 15 samples with 30% accuracy (below critical 65% -> DEGRADED)
        for i in range(15):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Degraded test {i}",
                selected_option="opt_a",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT if i < 4 else OutcomeQuality.VERIFIED_INCORRECT
            decision_outcome_store.add_record(rec)

        decision_drift_detector.set_baseline_accuracy("intent", 0.85)
        assessment = decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(assessment.state, DriftState.DEGRADED)
        self.assertTrue(assessment.force_system2)

    # 20. Automatic System 2 escalation
    def test_20_automatic_system2_escalation(self):
        # Put category into DEGRADED state
        self.test_19_degraded_state()

        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="High confidence in degraded route",
            selected_option="billing_refund",
            confidence=0.95,
        )
        passed, rationale = decision_confidence_gate.evaluate_decision(res)
        self.assertFalse(passed)
        self.assertTrue(res.abstained)
        self.assertEqual(res.reason_code, "CONSERVATIVE_DRIFT_DEGRADATION")

    # 21. Recovery
    def test_21_recovery(self):
        # First degrade
        self.test_19_degraded_state()
        self.assertEqual(decision_drift_detector.get_state(DecisionCategory.INTENT), DriftState.DEGRADED)

        # Clear and inject 15 consecutive 100% correct samples
        decision_outcome_store.clear()
        for i in range(15):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Recovery sample {i}",
                selected_option="opt_a",
                confidence=0.88,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec)

        # First evaluation after healthy samples transitions from DEGRADED to WARNING
        assessment1 = decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(assessment1.state, DriftState.WARNING)

        # Second evaluation transitions from WARNING to STABLE
        assessment2 = decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(assessment2.state, DriftState.STABLE)

    # 22. Recency weighting
    def test_22_recency_weighting(self):
        # Add 30 old records (poor accuracy)
        for i in range(30):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Old {i}",
                selected_option="opt_a",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_INCORRECT
            decision_outcome_store.add_record(rec)

        # Add 10 recent records (100% accuracy)
        for i in range(10):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Recent {i}",
                selected_option="opt_a",
                confidence=0.90,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec)

        # Query full vs recent window
        all_rep = decision_calibration_engine.calibrate_category(DecisionCategory.INTENT)
        recent_rep = decision_calibration_engine.calibrate_category(DecisionCategory.INTENT, recent_window_limit=10)

        self.assertAlmostEqual(all_rep.accuracy, 10 / 40)
        self.assertEqual(recent_rep.accuracy, 1.0)

    # 23. System 1 vs System 2 disagreement tracking
    def test_23_disagreement_tracking(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Disagreement context",
            selected_option="laya_choice",
            confidence=0.85,
        )
        decision_policy_router.set_mode(RoutingMode.ACTIVE)
        final_opt, _ = decision_policy_router.arbitrate_decision(res, system2_decision_option="system2_choice")
        self.assertEqual(final_opt, "laya_choice")
        self.assertEqual(len(decision_policy_router.disagreements), 1)

        # Record verified ground truth showing Laya was correct
        updated = decision_policy_router.update_disagreement_outcome(
            decision_id=res.decision_id,
            actual_outcome="laya_choice",
            verified_correct_choice="laya_choice",
        )
        self.assertTrue(updated)
        analysis = decision_policy_router.get_disagreement_analysis()
        self.assertEqual(analysis["system1_correct"], 1)
        self.assertEqual(analysis["system2_correct"], 0)

    # 24. High-risk threshold cannot be weakened
    def test_24_high_risk_threshold_cannot_be_weakened(self):
        proposal, msg = decision_policy_manager.create_proposal(
            route=DecisionCategory.RISK,
            proposed_threshold=0.70,
            reason="Try to weaken risk threshold",
            supporting_sample_count=50,
        )
        self.assertIsNone(proposal)
        self.assertIn("Rejected", msg)

    # 25. Approval requirements cannot be weakened
    def test_25_approval_cannot_be_bypassed(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.RISK,
            context="Delete database partition",
            selected_option="high",
            confidence=0.99,
        )
        passed, rationale = decision_confidence_gate.evaluate_decision(res)
        self.assertFalse(passed)
        self.assertTrue(res.abstained)
        self.assertEqual(res.reason_code, "HIGH_RISK_ESCALATION")

    # 26. Verification cannot be bypassed
    def test_26_verification_cannot_be_bypassed(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Unverified task completion",
            selected_option="done",
            confidence=0.90,
        )
        rec = create_decision_outcome_record(res)
        self.assertFalse(rec.outcome_verified)
        self.assertEqual(rec.outcome_quality, OutcomeQuality.OUTCOME_UNKNOWN)
        # Cannot establish correctness without verification
        self.assertIsNone(rec.is_correct())

    # 27. Laya cannot modify its own policy directly
    def test_27_laya_cannot_modify_policy_directly(self):
        # Decision results cannot alter manager thresholds
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Intent",
            selected_option="opt",
            confidence=0.99,
        )
        self.assertEqual(decision_policy_manager.get_threshold(DecisionCategory.INTENT), 0.75)
        # Attempting to lower threshold below 0.75 is rejected
        proposal, msg = decision_policy_manager.create_proposal(
            route=DecisionCategory.INTENT,
            proposed_threshold=0.60,
            reason="Too low",
            supporting_sample_count=20,
        )
        self.assertIsNone(proposal)
        self.assertIn("below absolute baseline", msg)

    # 28. Unknown outcomes do not count as incorrect
    def test_28_unknown_outcomes_do_not_count_as_incorrect(self):
        records = []
        for i in range(10):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Query {i}",
                selected_option="opt",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(res)
            if i < 5:
                rec.outcome_verified = True
                rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            else:
                # 5 unverified outcomes
                rec.outcome_verified = False
                rec.outcome_quality = OutcomeQuality.OUTCOME_UNKNOWN
            records.append(rec)

        report = decision_calibration_engine.evaluate_records(records)
        # Accuracy must be calculated ONLY over the 5 verified records (5/5 = 100%)
        # It must NOT count the 5 unknown records as incorrect!
        self.assertEqual(report.verified_sample_count, 5)
        self.assertEqual(report.accuracy, 1.0)

    # 29. Small sample cannot trigger adaptation
    def test_29_small_sample_cannot_trigger_adaptation(self):
        proposal, msg = decision_policy_manager.create_proposal(
            route=DecisionCategory.INTENT,
            proposed_threshold=0.80,
            reason="Few samples",
            supporting_sample_count=4,  # below MIN 10
        )
        self.assertIsNone(proposal)
        self.assertIn("below minimum requirement", msg)

    # 30. Multilingual calibration isolation
    def test_30_multilingual_calibration_isolation(self):
        # 10 English samples (100% correct)
        for i in range(10):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"English query {i}",
                selected_option="opt_en",
                confidence=0.90,
                language="en",
            )
            rec = create_decision_outcome_record(res)
            rec.language = "en"
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec)

        # 2 Spanish samples (insufficient)
        for i in range(2):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"Spanish query {i}",
                selected_option="opt_es",
                confidence=0.80,
                language="es",
            )
            rec = create_decision_outcome_record(res)
            rec.language = "es"
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
            decision_outcome_store.add_record(rec)

        rep_en = decision_calibration_engine.calibrate_language("en")
        rep_es = decision_calibration_engine.calibrate_language("es")

        self.assertTrue(rep_en.is_sufficient)
        self.assertFalse(rep_es.is_sufficient)

    # 31. Checkpoint comparison
    def test_31_checkpoint_comparison(self):
        res1, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="C1",
            selected_option="a",
            confidence=0.90,
            model_or_checkpoint="checkpoint_a",
        )
        rec1 = create_decision_outcome_record(res1)
        rec1.checkpoint = "checkpoint_a"
        rec1.outcome_verified = True
        rec1.outcome_quality = OutcomeQuality.VERIFIED_CORRECT
        decision_outcome_store.add_record(rec1)

        res2, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="C2",
            selected_option="b",
            confidence=0.80,
            model_or_checkpoint="checkpoint_b",
        )
        rec2 = create_decision_outcome_record(res2)
        rec2.checkpoint = "checkpoint_b"
        rec2.outcome_verified = True
        rec2.outcome_quality = OutcomeQuality.VERIFIED_INCORRECT
        decision_outcome_store.add_record(rec2)

        q_a = decision_outcome_store.query_records(checkpoint="checkpoint_a")
        q_b = decision_outcome_store.query_records(checkpoint="checkpoint_b")
        self.assertEqual(len(q_a), 1)
        self.assertEqual(len(q_b), 1)

    # 32. Latency telemetry
    def test_32_latency_telemetry(self):
        res = system1_decision_engine.decide("Benchmark latency", DecisionCategory.INTENT)
        rec = decision_outcome_store.get_record(res.decision_id)
        self.assertIsNotNone(rec)
        self.assertGreaterEqual(rec.latency_ms, 0.0)

    # 33. Policy version attached to decisions
    def test_33_policy_version_attached_to_decisions(self):
        res = system1_decision_engine.decide("Policy version stamping", DecisionCategory.INTENT)
        self.assertIn("policy_version", res.metadata)
        self.assertEqual(res.metadata["policy_version"], decision_policy_router.policy_version)

    # 34. Phase 12.26 continuous learning bridge
    def test_34_phase12_26_learning_bridge(self):
        # Create decision
        dec = system1_decision_engine.decide("Repair flow port", DecisionCategory.SKILL_SELECTION)

        # Create task outcome contract referencing decision_id
        outcome, _ = create_outcome_contract(
            expected_outcome="Port 3000 released",
            actual_outcome="Port 3000 released successfully",
            outcome_type=OutcomeType.VERIFIED_SUCCESS,
            verification_state=VerificationState.VERIFIED,
            evidence_references=["ps_port_verified"],
            metadata={"decision_id": dec.decision_id},
        )

        # Evaluate outcome via Phase 12.26 OutcomeEvaluationEngine
        eval_result = outcome_evaluation_engine.evaluate_outcome(outcome)
        self.assertTrue(eval_result["outcome_verified"])

        # Check that DecisionOutcomeStore was automatically bridged and updated
        rec = decision_outcome_store.get_record(dec.decision_id)
        self.assertIsNotNone(rec)
        self.assertTrue(rec.outcome_verified)
        self.assertEqual(rec.outcome_quality, OutcomeQuality.VERIFIED_CORRECT)

    # 35. Developer status commands via intent router
    def test_35_developer_status_commands(self):
        m1 = router.match("show system 1 calibration")
        self.assertEqual(m1["intent"], "QUERY_SYSTEM1_CALIBRATION")
        r1 = router.execute(m1)
        resp1 = r1.get("response", "") if isinstance(r1, dict) else str(r1)
        self.assertIn("System 1 calibration", resp1)

        m2 = router.match("how accurate is system 1")
        self.assertEqual(m2["intent"], "QUERY_SYSTEM1_ACCURACY")
        r2 = router.execute(m2)
        resp2 = r2.get("response", "") if isinstance(r2, dict) else str(r2)
        self.assertTrue("verified" in resp2.lower() or "accuracy" in resp2.lower())

        m3 = router.match("show system 1 drift")
        self.assertEqual(m3["intent"], "QUERY_SYSTEM1_DRIFT")
        r3 = router.execute(m3)
        resp3 = r3.get("response", "") if isinstance(r3, dict) else str(r3)
        self.assertIn("drift state", resp3.lower())

        m4 = router.match("why did system 1 abstain")
        self.assertEqual(m4["intent"], "QUERY_SYSTEM1_ABSTENTION_REASON")
        r4 = router.execute(m4)
        resp4 = r4.get("response", "") if isinstance(r4, dict) else str(r4)
        self.assertIn("abstains", resp4.lower())

        m5 = router.match("show system 1 policy version")
        self.assertEqual(m5["intent"], "QUERY_SYSTEM1_POLICY_VERSION")
        r5 = router.execute(m5)
        resp5 = r5.get("response", "") if isinstance(r5, dict) else str(r5)
        self.assertIn("policy version", resp5.lower())

        m6 = router.match("show system 1 route reliability")
        self.assertEqual(m6["intent"], "QUERY_SYSTEM1_ROUTE_RELIABILITY")
        r6 = router.execute(m6)
        resp6 = r6.get("response", "") if isinstance(r6, dict) else str(r6)
        self.assertIn("trust score", resp6.lower())

        m7 = router.match("rollback system 1 policy")
        self.assertEqual(m7["intent"], "ROLLBACK_SYSTEM1_POLICY")
        r7 = router.execute(m7)
        resp7 = r7.get("response", "") if isinstance(r7, dict) else str(r7)
        self.assertIn("policy rollback", resp7.lower())


if __name__ == "__main__":
    unittest.main()
