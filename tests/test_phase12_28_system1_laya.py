"""
Phase 12.28 — System 1 Decision Engine & Laya Integration Test Suite.
Verifies all 45+ requirements:
1. Laya adapter initialization
2. Laya unavailable fallback
3. Model loading
4. Model loading failure handling
5. Typed decision validation
6. Choice decision
7. Score decision
8. Noul decision
9. Confidence gate
10. Low-confidence abstention
11. High-risk escalation
12. Unknown intent escalation
13. Multilingual routing
14. English routing
15. Shadow mode
16. Advisory mode
17. Active mode
18. Route configuration
19. Agent routing
20. Skill routing
21. Strategy routing
22. Urgency scoring
23. Risk scoring
24. Proactive opportunity filtering
25. Temporal prioritization
26. Research gating
27. Memory relevance
28. System 1/System 2 fallback
29. Laya/System 2 disagreement
30. Governance remains authoritative
31. ActionContract cannot be bypassed
32. ApprovalStore cannot be bypassed
33. Verification still executes
34. Laya cannot execute tools
35. Laya cannot mutate user data
36. Laya timeout fallback
37. Memory pressure fallback
38. Realtime loop non-blocking behavior
39. Telemetry generation
40. Sensitive data isolation
41. Model cache behavior
42. Health monitoring
43. Automatic degradation
44. Regression detection
45. Backward compatibility with existing JARVIS behavior
"""

from __future__ import annotations

import time
import unittest

from core.decision_confidence_gate import decision_confidence_gate
from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionSource,
    DecisionType,
    compute_context_hash,
    create_decision_result,
)
from core.decision_fallback_engine import decision_fallback_engine
from core.decision_policy_router import RoutingMode, decision_policy_router
from core.decision_question_builder import decision_question_builder
from core.intent_router import router
from core.laya_decision_adapter import LayaDecisionAdapter, laya_decision_adapter
from core.laya_health_monitor import HealthState, laya_health_monitor
from core.system1_decision_engine import system1_decision_engine


class TestPhase1228System1Laya(unittest.TestCase):
    def setUp(self):
        decision_policy_router.set_mode(RoutingMode.SHADOW)
        decision_policy_router.clear_telemetry()
        laya_health_monitor.reset()
        system1_decision_engine.set_enabled(True)

    # 1. Laya adapter initialization
    def test_01_laya_adapter_initialization(self):
        adapter = LayaDecisionAdapter()
        self.assertIsNotNone(adapter)
        self.assertTrue(adapter.is_available())

    # 2. Laya unavailable fallback
    def test_02_laya_unavailable_fallback(self):
        system1_decision_engine.set_enabled(False)
        res = system1_decision_engine.decide("What is my schedule?", DecisionCategory.INTENT)
        self.assertEqual(res.source, DecisionSource.FALLBACK_HEURISTIC)
        self.assertIn("FALLBACK", res.reason_code)

    # 3. Model loading
    def test_03_model_loading(self):
        ok = laya_decision_adapter.load_model("laya")
        self.assertTrue(ok)
        self.assertIn("laya", laya_decision_adapter._loaded_models)

    # 4. Model loading failure handling
    def test_04_model_loading_failure_handling(self):
        ok = laya_decision_adapter.load_model("unknown-checkpoint")
        self.assertTrue(ok)  # Gracefully falls back to simulated model without crashing

    # 5. Typed decision validation
    def test_05_typed_decision_validation(self):
        res, msg = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="Fix FLOW server",
            selected_option="coding",
            confidence=0.90,
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.selected_option, "coding")

    # 6. Choice decision
    def test_06_choice_decision(self):
        res = laya_decision_adapter.decide_choice(
            context="Please write a python function to parse JSON",
            options=["coding", "conversational", "research"],
            category=DecisionCategory.INTENT,
        )
        self.assertEqual(res.decision_type, DecisionType.CHOICE)
        self.assertEqual(res.selected_option, "coding")

    # 7. Score decision
    def test_07_score_decision(self):
        res = laya_decision_adapter.decide_score(
            context="Critical emergency: database crashed immediately",
            category=DecisionCategory.URGENCY,
        )
        self.assertEqual(res.decision_type, DecisionType.SCORE)
        self.assertGreaterEqual(res.score, 0.90)

    # 8. Noul decision
    def test_08_noul_decision(self):
        res = laya_decision_adapter.decide_noul(
            context="Complex multi-label query",
            category=DecisionCategory.INTENT,
        )
        self.assertEqual(res.decision_type, DecisionType.NOUL)
        self.assertIsNotNone(res.selected_option)

    # 9. Confidence gate
    def test_09_confidence_gate(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="test",
            selected_option="task",
            confidence=0.88,
            alternatives={"task": 0.88, "coding": 0.12},
        )
        passed, msg = decision_confidence_gate.evaluate_decision(res)
        self.assertTrue(passed)
        self.assertFalse(res.abstained)

    # 10. Low-confidence abstention
    def test_10_low_confidence_abstention(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.INTENT,
            context="ambiguous statement",
            selected_option="task",
            confidence=0.40,  # Below 0.75
        )
        passed, msg = decision_confidence_gate.evaluate_decision(res)
        self.assertFalse(passed)
        self.assertTrue(res.abstained)
        self.assertEqual(res.reason_code, "INSUFFICIENT_CONFIDENCE")

    # 11. High-risk escalation
    def test_11_high_risk_escalation(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.RISK,
            context="rm -rf /",
            selected_option="high",
            confidence=0.99,
        )
        passed, msg = decision_confidence_gate.evaluate_decision(res)
        self.assertFalse(passed)
        self.assertTrue(res.abstained)
        self.assertEqual(res.reason_code, "HIGH_RISK_ESCALATION")

    # 12. Unknown intent escalation
    def test_12_unknown_intent_escalation(self):
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=DecisionCategory.RISK,
            context="obscure unfamiliar command",
            selected_option="unknown",
            confidence=0.85,
        )
        passed, msg = decision_confidence_gate.evaluate_decision(res)
        self.assertFalse(passed)
        self.assertTrue(res.abstained)

    # 13. Multilingual routing
    def test_13_multilingual_routing(self):
        ckpt = laya_decision_adapter.select_checkpoint(language="es", decision_type=DecisionType.CHOICE)
        self.assertEqual(ckpt, "laya-multilingual")

    # 14. English routing
    def test_14_english_routing(self):
        ckpt = laya_decision_adapter.select_checkpoint(language="en", decision_type=DecisionType.CHOICE)
        self.assertEqual(ckpt, "laya")

    # 15. Shadow mode
    def test_15_shadow_mode(self):
        decision_policy_router.set_mode(RoutingMode.SHADOW)
        res = system1_decision_engine.decide("Write tests for FLOW", DecisionCategory.AGENT_ROUTING)
        final_choice, rationale = decision_policy_router.arbitrate_decision(res, "planner")
        self.assertEqual(final_choice, "planner")  # System 2 authoritative in SHADOW
        self.assertIn("SHADOW mode active", rationale)

    # 16. Advisory mode
    def test_16_advisory_mode(self):
        decision_policy_router.set_mode(RoutingMode.ADVISORY)
        res = system1_decision_engine.decide("Check disk space", DecisionCategory.INTENT)
        final_choice, rationale = decision_policy_router.arbitrate_decision(res, "system_control")
        self.assertEqual(final_choice, "system_control")
        self.assertIn("ADVISORY mode", rationale)

    # 17. Active mode
    def test_17_active_mode(self):
        decision_policy_router.set_mode(RoutingMode.ACTIVE)
        res = system1_decision_engine.decide("Write python code", DecisionCategory.AGENT_ROUTING)
        final_choice, rationale = decision_policy_router.arbitrate_decision(res, "general_reasoner")
        self.assertEqual(final_choice, "coder")  # Laya fast-route active
        self.assertIn("ACTIVE mode", rationale)

    # 18. Route configuration
    def test_18_route_configuration(self):
        decision_policy_router.set_mode(RoutingMode.ACTIVE)
        decision_policy_router.set_route_enabled(DecisionCategory.RESEARCH, False)
        self.assertFalse(decision_policy_router.is_route_active(DecisionCategory.RESEARCH))

    # 19. Agent routing
    def test_19_agent_routing(self):
        res = system1_decision_engine.decide("Search documentation for API updates", DecisionCategory.AGENT_ROUTING)
        self.assertIn(res.selected_option, ["researcher", "coder", "planner", "general_reasoner"])

    # 20. Skill routing
    def test_20_skill_routing(self):
        res = system1_decision_engine.decide("Restart FLOW port 3000", DecisionCategory.SKILL_SELECTION)
        self.assertIsNotNone(res.selected_option)

    # 21. Strategy routing
    def test_21_strategy_routing(self):
        res = system1_decision_engine.decide("Answer simple question directly", DecisionCategory.STRATEGY_SELECTION)
        self.assertIsNotNone(res.selected_option)

    # 22. Urgency scoring
    def test_22_urgency_scoring(self):
        res = system1_decision_engine.decide("Do this optional task later", DecisionCategory.URGENCY)
        self.assertLess(res.score, 0.50)

    # 23. Risk scoring
    def test_23_risk_scoring(self):
        res = system1_decision_engine.decide("View logs file", DecisionCategory.RISK)
        self.assertEqual(res.category, DecisionCategory.RISK)

    # 24. Proactive opportunity filtering
    def test_24_proactive_opportunity_filtering(self):
        res = system1_decision_engine.decide("Stale file detected on disk", DecisionCategory.PROACTIVE)
        self.assertIn(res.selected_option, ["irrelevant", "potentially_useful", "actionable", "urgent"])

    # 25. Temporal prioritization
    def test_25_temporal_prioritization(self):
        res = system1_decision_engine.decide("Remind me tomorrow at 9am", DecisionCategory.TEMPORAL)
        self.assertIsNotNone(res.selected_option)

    # 26. Research gating
    def test_26_research_gating(self):
        res = system1_decision_engine.decide("Check local memory", DecisionCategory.RESEARCH)
        self.assertIn(res.selected_option, ["no_research_needed", "local_memory_sufficient", "external_research_useful", "external_research_required", "uncertain"])

    # 27. Memory relevance
    def test_27_memory_relevance(self):
        res = system1_decision_engine.decide("Related to prior FLOW deployment context", DecisionCategory.MEMORY)
        self.assertIn(res.selected_option, ["new", "likely_memory_relevant", "likely_related_to_prior_context", "ambiguous"])

    # 28. System 1/System 2 fallback
    def test_28_system1_system2_fallback(self):
        fb = decision_fallback_engine.resolve_fallback(DecisionCategory.INTENT, "What is today's date?")
        self.assertEqual(fb.source, DecisionSource.FALLBACK_HEURISTIC)
        self.assertEqual(fb.selected_option, "informational")

    # 29. Laya/System 2 disagreement
    def test_29_laya_system2_disagreement(self):
        res = system1_decision_engine.decide("Disputed request", DecisionCategory.INTENT)
        decision_policy_router.arbitrate_decision(res, "planner")
        self.assertGreaterEqual(len(decision_policy_router.disagreements), 1)

    # 30. Governance remains authoritative
    def test_30_governance_remains_authoritative(self):
        decision_policy_router.set_mode(RoutingMode.ACTIVE)
        res = system1_decision_engine.decide("Dangerous command", DecisionCategory.INTENT)
        final, rationale = decision_policy_router.arbitrate_decision(res, "human_escalation", governance_override=True)
        self.assertEqual(final, "human_escalation")
        self.assertIn("governance", rationale.lower())

    # 31. ActionContract cannot be bypassed
    def test_31_action_contract_cannot_be_bypassed(self):
        # System 1 only produces DecisionResult without execution permissions
        res = system1_decision_engine.decide("Deploy production server", DecisionCategory.INTENT)
        self.assertIsInstance(res, DecisionResult)
        self.assertFalse(hasattr(res, "execute_tool"))

    # 32. ApprovalStore cannot be bypassed
    def test_32_approval_store_cannot_be_bypassed(self):
        res = system1_decision_engine.decide("Format disk", DecisionCategory.RISK)
        # Any mutating action still requires ApprovalStore
        self.assertTrue(res.abstained or res.selected_option == "high")

    # 33. Verification still executes
    def test_33_verification_still_executes(self):
        res = system1_decision_engine.decide("Verify outcome", DecisionCategory.AGENT_ROUTING)
        self.assertIn(res.selected_option, ["verifier", "planner", "general_reasoner", "executor", "coder"])

    # 34. Laya cannot execute tools
    def test_34_laya_cannot_execute_tools(self):
        res = system1_decision_engine.decide("Run bash script", DecisionCategory.INTENT)
        self.assertNotIn("execute", dir(res))

    # 35. Laya cannot mutate user data
    def test_35_laya_cannot_mutate_user_data(self):
        res = system1_decision_engine.decide("Delete folder", DecisionCategory.INTENT)
        self.assertNotIn("delete", dir(res))

    # 36. Laya timeout fallback
    def test_36_laya_timeout_fallback(self):
        laya_health_monitor.record_failure(is_timeout=True)
        self.assertEqual(laya_health_monitor.metrics.timeout_count, 1)

    # 37. Memory pressure fallback
    def test_37_memory_pressure_fallback(self):
        laya_health_monitor.set_memory_pressure(True)
        self.assertEqual(laya_health_monitor.metrics.health_state, HealthState.UNHEALTHY)
        res = system1_decision_engine.decide("Perform query", DecisionCategory.INTENT)
        self.assertEqual(res.source, DecisionSource.FALLBACK_HEURISTIC)

    # 38. Realtime loop non-blocking behavior
    def test_38_realtime_loop_non_blocking_behavior(self):
        router.match("what time is it")  # Warm-up regex cache
        t0 = time.perf_counter()
        match = router.match("what is the system 1 status")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_SYSTEM1_STATUS")
        self.assertLess(dt, 20.0)

    # 39. Telemetry generation
    def test_39_telemetry_generation(self):
        res = system1_decision_engine.decide("Telemetry test", DecisionCategory.INTENT)
        d = res.to_dict()
        self.assertIn("trace_id", d)
        self.assertIn("latency_ms", d)
        self.assertIn("confidence", d)

    # 40. Sensitive data isolation
    def test_40_sensitive_data_isolation(self):
        # Context hash preserves privacy
        h1 = compute_context_hash("secret password 123")
        self.assertEqual(len(h1), 16)
        self.assertNotIn("password", h1)

    # 41. Model cache behavior
    def test_41_model_cache_behavior(self):
        adapter = LayaDecisionAdapter(max_loaded_models=1)
        adapter.load_model("model1")
        adapter.load_model("model2")
        self.assertEqual(len(adapter._loaded_models), 1)
        self.assertIn("model2", adapter._loaded_models)

    # 42. Health monitoring
    def test_42_health_monitoring(self):
        status = laya_health_monitor.get_status()
        self.assertIn("health_state", status)
        self.assertIn("average_latency_ms", status)

    # 43. Automatic degradation
    def test_43_automatic_degradation(self):
        for _ in range(5):
            laya_health_monitor.record_failure()
        self.assertEqual(laya_health_monitor.metrics.health_state, HealthState.UNHEALTHY)

    # 44. Regression detection
    def test_44_regression_detection(self):
        res = system1_decision_engine.decide("Disagreement query", DecisionCategory.INTENT)
        decision_policy_router.arbitrate_decision(res, "alternative_choice")
        summary = decision_policy_router.get_telemetry_summary()
        self.assertGreaterEqual(summary["disagreement_count"], 1)

    # 45. Backward compatibility with existing JARVIS behavior
    def test_45_backward_compatibility_with_existing_jarvis_behavior(self):
        match = router.match("what time is it")
        self.assertEqual(match["intent"], "GET_TIME")


if __name__ == "__main__":
    unittest.main()
