"""
Phase 12.30 — Autonomous Decision Arbitration Test Suite.
Verifies all 32+ operational requirements:
1. High-confidence, low-risk, simple task -> System 1
2. Low-confidence -> System 2 (LOW_CONFIDENCE)
3. Low route reliability -> System 2 (LOW_ROUTE_RELIABILITY)
4. Insufficient calibration samples -> System 2 (INSUFFICIENT_SAMPLES)
5. Drift warning -> stricter threshold routing
6. Drift degraded -> System 2 (DRIFT_DETECTED)
7. High risk -> System 2 (HIGH_RISK)
8. Unknown risk -> System 2 (UNKNOWN_RISK)
9. Novel task -> System 2 (NOVEL_TASK)
10. Complex task -> System 2 (HIGH_COMPLEXITY)
11. Weak evidence -> System 2 (WEAK_EVIDENCE)
12. Research required -> System 2 (RESEARCH_REQUIRED)
13. System 1 / System 2 agreement
14. System 1 / System 2 disagreement arbitration
15. Hybrid mode execution
16. Human escalation integration with ApprovalStore
17. Memory conflict escalation
18. Current observation overrides memory
19. Cost-aware routing
20. Temporal urgency integration
21. Proactive arbitration
22. Laya unavailable fallback
23. System 2 unavailable fallback
24. Both engines unavailable fallback
25. Structured arbitration explanations
26. Arbitration telemetry generation
27. Policy version propagation
28. Calibration integration
29. Drift integration
30. Developer status commands via intent router
31. Phase 12.28 regression compatibility
32. Phase 12.29 regression compatibility
"""

from __future__ import annotations

import time
import unittest

from core.decision_arbitration import (
    ArbitrationContext,
    DecisionArbitrator,
    DecisionEngine,
    DisagreementType,
    EscalationReason,
    EvidenceQuality,
    TaskComplexity,
    TaskNovelty,
    TemporalPressure,
    decision_arbitrator,
)
from core.decision_calibration_engine import decision_calibration_engine
from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionSource,
    DecisionType,
    create_decision_result,
)
from core.decision_drift_detector import DriftState, decision_drift_detector
from core.decision_outcome import (
    DecisionOutcomeRecord,
    OutcomeQuality,
    create_decision_outcome_record,
    decision_outcome_store,
)
from core.decision_policy_proposal import decision_policy_manager
from core.decision_policy_router import RoutingMode, decision_policy_router
from core.intent_router import router
from core.system1_decision_engine import system1_decision_engine


class TestPhase1230Arbitration(unittest.TestCase):
    def setUp(self):
        decision_outcome_store.clear()
        decision_drift_detector.reset()
        decision_policy_router.clear_telemetry()
        decision_arbitrator.telemetry_store.clear()
        decision_policy_router.set_mode(RoutingMode.ACTIVE)
        system1_decision_engine.set_enabled(True)

    def tearDown(self):
        decision_drift_detector.degraded_accuracy_threshold = 0.65

    def _seed_sufficient_calibration(self, category: DecisionCategory, accuracy: float = 1.0):
        """Helper to seed minimum calibration samples so route reliability is verified."""
        for i in range(12):
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=category,
                context=f"Seed sample {i}",
                selected_option="opt_a",
                confidence=0.88,
            )
            rec = create_decision_outcome_record(res)
            rec.outcome_verified = True
            rec.outcome_quality = (
                OutcomeQuality.VERIFIED_CORRECT
                if (i / 12) < accuracy
                else OutcomeQuality.VERIFIED_INCORRECT
            )
            decision_outcome_store.add_record(rec)

    # 1. High-confidence, low-risk, simple task -> System 1
    def test_01_high_confidence_low_risk_simple_task(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT, accuracy=1.0)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Simple what time is it",
            selected_option="get_time",
            confidence=0.92,
        )
        ctx = ArbitrationContext(
            context_text="what time is it",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="get_time",
            novelty=TaskNovelty.FAMILIAR,
            complexity=TaskComplexity.SIMPLE,
            risk_level="low",
            evidence_quality=EvidenceQuality.STRONG,
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM1)
        self.assertFalse(arb.system2_required)
        self.assertEqual(arb.system2_reason, EscalationReason.NONE)

    # 2. Low-confidence -> System 2 (LOW_CONFIDENCE)
    def test_02_low_confidence_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Unclear request",
            selected_option="general_inquiry",
            confidence=0.55,  # below 0.75 threshold
        )
        ctx = ArbitrationContext(
            context_text="Unclear request",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="clarification",
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertTrue(arb.system2_required)
        self.assertEqual(arb.system2_reason, EscalationReason.LOW_CONFIDENCE)

    # 3. Low route reliability -> System 2 (LOW_ROUTE_RELIABILITY)
    def test_03_low_route_reliability_escalation(self):
        # Set degraded threshold to 0.35 and baseline to 0.45 so 40% accuracy does not trigger DRIFT_DETECTED
        decision_drift_detector.degraded_accuracy_threshold = 0.35
        decision_drift_detector.set_baseline_accuracy("research", 0.45)
        self._seed_sufficient_calibration(DecisionCategory.RESEARCH, accuracy=0.40)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.RESEARCH,
            context="Research question",
            selected_option="local_lookup",
            confidence=0.88,
        )
        ctx = ArbitrationContext(
            context_text="Research question",
            category=DecisionCategory.RESEARCH,
            laya_decision=res,
            system2_option="local_lookup",
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.LOW_ROUTE_RELIABILITY)

    # 4. Insufficient calibration samples -> System 2 (INSUFFICIENT_SAMPLES)
    def test_04_insufficient_samples_escalation(self):
        # 0 samples seeded
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.SKILL_SELECTION,
            context="Skill selection without data",
            selected_option="port_fix",
            confidence=0.88,
        )
        ctx = ArbitrationContext(
            context_text="Skill selection",
            category=DecisionCategory.SKILL_SELECTION,
            laya_decision=res,
            system2_option="port_fix",
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.INSUFFICIENT_SAMPLES)

    # 5. Drift warning -> stricter threshold routing
    def test_05_drift_warning_stricter_routing(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        # Induce WARNING drift state
        for i in range(15):
            r, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"W {i}",
                selected_option="opt",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(r)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT if i < 10 else OutcomeQuality.VERIFIED_INCORRECT
            decision_outcome_store.add_record(rec)

        decision_drift_detector.set_baseline_accuracy("intent", 0.85)
        decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(decision_drift_detector.get_state(DecisionCategory.INTENT), DriftState.WARNING)

        # Confidence of 0.77 would pass baseline (0.75), but fails under WARNING penalty (+0.05 -> 0.80)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Borderline confidence under drift warning",
            selected_option="opt",
            confidence=0.77,
        )
        ctx = ArbitrationContext(
            context_text="Borderline confidence",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="opt",
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.LOW_CONFIDENCE)

    # 6. Drift degraded -> System 2 (DRIFT_DETECTED)
    def test_06_drift_degraded_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        # Induce DEGRADED drift state
        for i in range(15):
            r, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.INTENT,
                context=f"D {i}",
                selected_option="opt",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(r)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT if i < 3 else OutcomeQuality.VERIFIED_INCORRECT
            decision_outcome_store.add_record(rec)

        decision_drift_detector.set_baseline_accuracy("intent", 0.85)
        decision_drift_detector.assess_route(DecisionCategory.INTENT)
        self.assertEqual(decision_drift_detector.get_state(DecisionCategory.INTENT), DriftState.DEGRADED)

        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="High confidence in degraded route",
            selected_option="opt",
            confidence=0.99,
        )
        ctx = ArbitrationContext(
            context_text="High confidence",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="opt",
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.DRIFT_DETECTED)

    # 7. High risk -> System 2 (HIGH_RISK)
    def test_07_high_risk_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.RISK)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.RISK,
            context="Delete database partition",
            selected_option="delete_db",
            confidence=0.98,
        )
        ctx = ArbitrationContext(
            context_text="Delete database",
            category=DecisionCategory.RISK,
            laya_decision=res,
            system2_option="delete_db",
            risk_level="high",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.HIGH_RISK)

    # 8. Unknown risk -> System 2 (UNKNOWN_RISK)
    def test_08_unknown_risk_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Execute obscure binary",
            selected_option="exec_bin",
            confidence=0.90,
        )
        ctx = ArbitrationContext(
            context_text="Execute obscure binary",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="exec_bin",
            risk_level="unknown",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.UNKNOWN_RISK)

    # 9. Novel task -> System 2 (NOVEL_TASK)
    def test_09_novel_task_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Brand new unfamiliar domain instruction",
            selected_option="opt_novel",
            confidence=0.91,
        )
        ctx = ArbitrationContext(
            context_text="Unfamiliar domain",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="opt_novel",
            novelty=TaskNovelty.NOVEL,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.NOVEL_TASK)

    # 10. Complex task -> System 2 (HIGH_COMPLEXITY)
    def test_10_complex_task_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.AGENT_ROUTING)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.AGENT_ROUTING,
            context="Refactor distributed microservice architecture",
            selected_option="coder",
            confidence=0.90,
        )
        ctx = ArbitrationContext(
            context_text="Refactor distributed architecture",
            category=DecisionCategory.AGENT_ROUTING,
            laya_decision=res,
            system2_option="multi_agent_team",
            complexity=TaskComplexity.COMPLEX,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.HIGH_COMPLEXITY)

    # 11. Weak evidence -> System 2 (WEAK_EVIDENCE)
    def test_11_weak_evidence_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Context with weak grounding",
            selected_option="guess_opt",
            confidence=0.88,
        )
        ctx = ArbitrationContext(
            context_text="Context with weak grounding",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="guess_opt",
            evidence_quality=EvidenceQuality.WEAK,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.WEAK_EVIDENCE)

    # 12. Research required -> System 2 (RESEARCH_REQUIRED)
    def test_12_research_required_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.RESEARCH)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.RESEARCH,
            context="What are Next.js 16 canary features",
            selected_option="hallucinate_features",
            confidence=0.92,
        )
        ctx = ArbitrationContext(
            context_text="What are Next.js 16 canary features",
            category=DecisionCategory.RESEARCH,
            laya_decision=res,
            system2_option="search_web",
            requires_research=True,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.RESEARCH_REQUIRED)

    # 13. System 1 / System 2 agreement
    def test_13_system1_system2_agreement(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Open settings",
            selected_option="open_settings",
            confidence=0.89,
        )
        ctx = ArbitrationContext(
            context_text="Open settings",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="open_settings",
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.disagreement, DisagreementType.AGREEMENT)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM1)

    # 14. System 1 / System 2 disagreement arbitration
    def test_14_system1_system2_disagreement(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Ambiguous intent query",
            selected_option="option_laya",
            confidence=0.85,
        )
        # Moderate risk + partial evidence forces System 2 to arbitrate
        ctx = ArbitrationContext(
            context_text="Ambiguous intent",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="option_system2",
            evidence_quality=EvidenceQuality.PARTIAL,
            risk_level="medium",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.disagreement, DisagreementType.DISAGREEMENT)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.final_decision_option, "option_system2")

    # 15. Hybrid mode execution
    def test_15_hybrid_mode_execution(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Moderate multi-part query",
            selected_option="candidate_strategy",
            confidence=0.86,
        )
        ctx = ArbitrationContext(
            context_text="Moderate multi-part query",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="candidate_strategy",
            complexity=TaskComplexity.MODERATE,
            evidence_quality=EvidenceQuality.STRONG,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.HYBRID)
        self.assertTrue(arb.system2_required)
        self.assertEqual(arb.final_decision_option, "candidate_strategy")

    # 16. Human escalation integration with ApprovalStore
    def test_16_human_escalation_approval(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Format production server disk",
            selected_option="format_disk",
            confidence=0.99,
        )
        ctx = ArbitrationContext(
            context_text="Format production server disk",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="format_disk",
            risk_level="destructive",
            user_preference="require_confirmation",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.HUMAN)
        self.assertEqual(arb.system2_reason, EscalationReason.EXECUTION_CONSEQUENCE)

    # 17. Memory conflict escalation
    def test_17_memory_conflict_escalation(self):
        self._seed_sufficient_calibration(DecisionCategory.MEMORY)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.MEMORY,
            context="Recall server port configuration",
            selected_option="port_8080",
            confidence=0.88,
        )
        ctx = ArbitrationContext(
            context_text="Recall server port",
            category=DecisionCategory.MEMORY,
            laya_decision=res,
            system2_option="port_3000",
            memory_conflict=True,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.MEMORY_CONFLICT)

    # 18. Current observation overrides memory
    def test_18_observation_overrides_memory(self):
        self._seed_sufficient_calibration(DecisionCategory.MEMORY)
        # Memory says port 8080, but live observation says port 3000 -> memory_conflict flagged
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.MEMORY,
            context="Port discrepancy",
            selected_option="port_8080",
            confidence=0.85,
        )
        ctx = ArbitrationContext(
            context_text="Live reality observation shows port 3000 active",
            category=DecisionCategory.MEMORY,
            laya_decision=res,
            system2_option="port_3000",
            memory_conflict=True,
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.final_decision_option, "port_3000")

    # 19. Cost-aware routing
    def test_19_cost_aware_routing(self):
        # Verify that for simple low-risk tasks, System 1 is chosen to conserve compute
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Mute volume",
            selected_option="mute",
            confidence=0.95,
        )
        ctx = ArbitrationContext(
            context_text="Mute volume",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="mute",
            complexity=TaskComplexity.SIMPLE,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM1)

    # 20. Temporal urgency integration
    def test_20_temporal_urgency_integration(self):
        self._seed_sufficient_calibration(DecisionCategory.TEMPORAL)
        # Urgent + simple + low-risk -> fast System 1
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.TEMPORAL,
            context="Urgent alarm cancel",
            selected_option="cancel_alarm",
            confidence=0.92,
        )
        ctx = ArbitrationContext(
            context_text="Urgent alarm cancel",
            category=DecisionCategory.TEMPORAL,
            laya_decision=res,
            system2_option="cancel_alarm",
            temporal_pressure=TemporalPressure.URGENT,
            complexity=TaskComplexity.SIMPLE,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM1)

    # 21. Proactive arbitration
    def test_21_proactive_arbitration(self):
        self._seed_sufficient_calibration(DecisionCategory.PROACTIVE)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.PROACTIVE,
            context="Prefetch project context",
            selected_option="prefetch_flow",
            confidence=0.88,
        )
        ctx = ArbitrationContext(
            context_text="Prefetch project context",
            category=DecisionCategory.PROACTIVE,
            laya_decision=res,
            system2_option="prefetch_flow",
            complexity=TaskComplexity.SIMPLE,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM1)

    # 22. Laya unavailable fallback
    def test_22_laya_unavailable_fallback(self):
        ctx = ArbitrationContext(
            context_text="Laya model unavailable",
            category=DecisionCategory.INTENT,
            laya_decision=None,
            system2_option="fallback_option",
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.final_decision_option, "fallback_option")

    # 23. System 2 unavailable fallback
    def test_23_system2_unavailable_fallback(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="System 2 down",
            selected_option="local_opt",
            confidence=0.90,
        )
        ctx = ArbitrationContext(
            context_text="System 2 down",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option=None,
            risk_level="low",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM1)
        self.assertEqual(arb.final_decision_option, "local_opt")

    # 24. Both engines unavailable fallback
    def test_24_both_engines_unavailable(self):
        ctx = ArbitrationContext(
            context_text="Both engines missing",
            category=DecisionCategory.INTENT,
            laya_decision=None,
            system2_option=None,
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.ABSTAIN)
        self.assertIsNone(arb.final_decision_option)

    # 25. Structured arbitration explanations
    def test_25_arbitration_explanations(self):
        self._seed_sufficient_calibration(DecisionCategory.INTENT)
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Complex multi-step task",
            selected_option="opt",
            confidence=0.90,
        )
        ctx = ArbitrationContext(
            context_text="Complex task",
            category=DecisionCategory.INTENT,
            laya_decision=res,
            system2_option="opt",
            complexity=TaskComplexity.COMPLEX,
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertGreater(len(arb.explanations), 0)
        self.assertTrue(any("complexity" in exp.lower() for exp in arb.explanations))

    # 26. Arbitration telemetry generation
    def test_26_arbitration_telemetry(self):
        ctx = ArbitrationContext(
            context_text="Telemetry test",
            category=DecisionCategory.INTENT,
            system2_option="sys2_opt",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        d = arb.to_dict()
        self.assertIn("arbitration_id", d)
        self.assertIn("selected_engine", d)
        self.assertIn("latency_ms", d)
        self.assertIn("explanations", d)

    # 27. Policy version propagation
    def test_27_policy_version_propagation(self):
        ctx = ArbitrationContext(
            context_text="Policy version test",
            category=DecisionCategory.INTENT,
            system2_option="opt",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.policy_version, decision_policy_manager.current_version)

    # 28. Calibration integration
    def test_28_calibration_integration(self):
        # Route with 0 samples seeded -> INSUFFICIENT_SAMPLES
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.STRATEGY_SELECTION,
            context="Strategy context",
            selected_option="strat_a",
            confidence=0.90,
        )
        ctx = ArbitrationContext(
            context_text="Strategy context",
            category=DecisionCategory.STRATEGY_SELECTION,
            laya_decision=res,
            system2_option="strat_a",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.system2_reason, EscalationReason.INSUFFICIENT_SAMPLES)

    # 29. Drift integration
    def test_29_drift_integration(self):
        # Seed 15 samples with low accuracy to trigger genuine DEGRADED drift state
        for i in range(15):
            r, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=DecisionCategory.URGENCY,
                context=f"Urgency drift {i}",
                selected_option="high",
                confidence=0.85,
            )
            rec = create_decision_outcome_record(r)
            rec.outcome_verified = True
            rec.outcome_quality = OutcomeQuality.VERIFIED_CORRECT if i < 3 else OutcomeQuality.VERIFIED_INCORRECT
            decision_outcome_store.add_record(rec)

        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.URGENCY,
            context="Urgency check",
            selected_option="high",
            confidence=0.95,
        )
        ctx = ArbitrationContext(
            context_text="Urgency check",
            category=DecisionCategory.URGENCY,
            laya_decision=res,
            system2_option="high",
        )
        arb = decision_arbitrator.arbitrate(ctx)
        self.assertEqual(arb.selected_engine, DecisionEngine.SYSTEM2)
        self.assertEqual(arb.system2_reason, EscalationReason.DRIFT_DETECTED)

    # 30. Developer status commands via intent router
    def test_30_developer_status_commands(self):
        m1 = router.match("show decision arbitration")
        self.assertEqual(m1["intent"], "QUERY_DECISION_ARBITRATION")
        r1 = router.execute(m1)
        resp1 = r1.get("response", "") if isinstance(r1, dict) else str(r1)
        self.assertIn("arbitration", resp1.lower())

        m2 = router.match("why did jarvis use system 2")
        self.assertEqual(m2["intent"], "QUERY_SYSTEM2_ESCALATION_REASON")
        r2 = router.execute(m2)
        resp2 = r2.get("response", "") if isinstance(r2, dict) else str(r2)
        self.assertIn("system 2", resp2.lower())

        m3 = router.match("why did jarvis use system 1")
        self.assertEqual(m3["intent"], "QUERY_SYSTEM1_SELECTION_REASON")
        r3 = router.execute(m3)
        resp3 = r3.get("response", "") if isinstance(r3, dict) else str(r3)
        self.assertIn("system 1", resp3.lower())

        m4 = router.match("show system 1 vs system 2")
        self.assertEqual(m4["intent"], "QUERY_SYSTEM1_VS_SYSTEM2")
        r4 = router.execute(m4)
        resp4 = r4.get("response", "") if isinstance(r4, dict) else str(r4)
        self.assertIn("disagreements", resp4.lower())

        m5 = router.match("show arbitration reliability")
        self.assertEqual(m5["intent"], "QUERY_ARBITRATION_RELIABILITY")
        r5 = router.execute(m5)
        resp5 = r5.get("response", "") if isinstance(r5, dict) else str(r5)
        self.assertTrue("reliability" in resp5.lower() or "escalation" in resp5.lower())

    # 31. Phase 12.28 regression compatibility
    def test_31_phase12_28_regression_compatibility(self):
        res = system1_decision_engine.decide("What is current time", DecisionCategory.INTENT)
        self.assertIsNotNone(res.decision_id)
        self.assertIn("policy_version", res.metadata)

    # 32. Phase 12.29 regression compatibility
    def test_32_phase12_29_regression_compatibility(self):
        report = decision_calibration_engine.calibrate_global()
        self.assertIsNotNone(report)
        self.assertEqual(report.verified_sample_count, 0)
        self.assertFalse(report.is_sufficient)


if __name__ == "__main__":
    unittest.main()
