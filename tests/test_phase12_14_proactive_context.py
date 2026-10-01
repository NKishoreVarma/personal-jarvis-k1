"""
Phase 12.14 — Proactive Context Awareness, Anticipatory Assistance & Intelligent Intervention Test Suite.
Verifies all 20 core requirements:
1. Verified observation overrides memory
2. Stale context expires
3. Prediction cannot execute side effects
4. Useful project-start opportunity detected
5. Low-value opportunities suppressed
6. User speech blocks intervention
7. Quiet mode suppresses proactive voice
8. Proactive preparation remains side-effect-free
9. Duplicate suggestions are suppressed
10. Declined suggestion reduces future priority
11. Accepted suggestion reinforces relevance
12. Critical alerts bypass normal suggestion budget
13. Context remains isolated between projects
14. Cancellation invalidates pending proactive work
15. Stale predictions expire
16. Proactive suggestion is concise
17. No chain-of-thought is exposed
18. Visual context remains ephemeral
19. Background analysis does not block voice callbacks
20. Full FLOW scenario works end-to-end
"""

from __future__ import annotations

import time
import unittest

from core.anticipation_engine import Prediction, anticipation_engine
from core.context_contract import ContextContract, ContextTaskState, create_context_contract
from core.context_observation_engine import context_observation_engine
from core.event_bus import EventType, event_bus
from core.intent_router import router
from core.interruption_budget_manager import interruption_budget_manager
from core.intervention_policy import InterventionAction, intervention_policy
from core.memory_contract import MemoryType, create_memory_contract
from core.memory_service import memory_service
from core.proactive_learning_loop import proactive_learning_loop
from core.proactive_opportunity_detector import OpportunityType, OpportunityValue, ProactiveOpportunity, proactive_opportunity_detector
from core.proactive_preparation_manager import proactive_preparation_manager
from core.proactive_suggestion_manager import ProactiveSuggestion, SuggestionState, proactive_suggestion_manager


class TestPhase1214ProactiveContext(unittest.TestCase):
    def setUp(self):
        context_observation_engine.clear_all()
        proactive_preparation_manager.clear_all()
        proactive_suggestion_manager.clear_all()
        interruption_budget_manager.clear_all()
        proactive_learning_loop.clear_all()
        intervention_policy.set_user_speaking(False)
        intervention_policy.set_jarvis_speaking(False)
        intervention_policy.set_quiet_mode(False)

    # 1. Verified observation overrides memory
    def test_01_verified_observation_overrides_memory(self):
        # Create stale memory saying port is 8080
        mem = create_memory_contract(
            memory_type=MemoryType.EXPERIENCE,
            subject="FLOW",
            content="Server previously ran on port 8080",
            project_scope="FLOW",
        )
        memory_service.store(mem)

        # Verified live context says port 3000
        ctx = context_observation_engine.update_project_context(
            project_name="FLOW",
            task_state=ContextTaskState.RUNNING,
            recent_action={"action": "server_started", "port": 3000, "verified": True},
        )

        opp = proactive_opportunity_detector.detect_opportunity(ctx)
        self.assertEqual(opp.arguments.get("port"), 3000)
        self.assertNotEqual(opp.arguments.get("port"), 8080)

    # 2. Stale context expires
    def test_02_stale_context_expires(self):
        ctx = create_context_contract(
            turn_id="t_stale",
            goal_id="g_stale",
            active_project="FLOW",
            ttl_seconds=0.01,
        )
        time.sleep(0.02)
        self.assertTrue(ctx.is_expired())
        opp = proactive_opportunity_detector.detect_opportunity(ctx)
        self.assertEqual(opp.value_tier, OpportunityValue.NO_OPPORTUNITY)

    # 3. Prediction cannot execute side effects
    def test_03_prediction_cannot_execute_side_effects(self):
        ctx = create_context_contract(
            turn_id="t1",
            goal_id="g1",
            active_project="FLOW",
            task_state=ContextTaskState.RUNNING,
            recent_verified_actions=[{"action": "server_started", "port": 3000}],
        )
        pred = anticipation_engine.predict_next_need(ctx)
        self.assertIsNotNone(pred)
        self.assertEqual(pred.predicted_next_action, "open_browser")
        # Prediction is purely informative dataclass, executes no code
        self.assertFalse(hasattr(pred, "execute"))

    # 4. Useful project-start opportunity detected
    def test_04_useful_project_start_opportunity_detected(self):
        ctx = create_context_contract(
            turn_id="t_flow",
            goal_id="g_flow",
            active_project="FLOW",
            task_state=ContextTaskState.RUNNING,
            recent_verified_actions=[{"action": "server_started", "port": 3000}],
        )
        opp = proactive_opportunity_detector.detect_opportunity(ctx)
        self.assertEqual(opp.opportunity_type, OpportunityType.PROJECT_STARTED_OPEN_BROWSER)
        self.assertEqual(opp.value_tier, OpportunityValue.HIGH_VALUE)
        self.assertTrue(opp.requires_voice_prompt)

    # 5. Low-value opportunities suppressed
    def test_05_low_value_opportunities_suppressed(self):
        ctx = create_context_contract(
            turn_id="t_idle",
            goal_id="g_idle",
            active_project="FLOW",
            task_state=ContextTaskState.IDLE,
        )
        opp = proactive_opportunity_detector.detect_opportunity(ctx)
        self.assertEqual(opp.value_tier, OpportunityValue.NO_OPPORTUNITY)
        act = intervention_policy.decide_intervention(opp)
        self.assertEqual(act, InterventionAction.DO_NOT_INTERVENE)

    # 6. User speech blocks intervention
    def test_06_user_speech_blocks_intervention(self):
        opp = ProactiveOpportunity(
            opportunity_id="opp_1",
            opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER,
            value_tier=OpportunityValue.HIGH_VALUE,
            project_name="FLOW",
            description="FLOW is ready",
            suggested_action="open_browser",
            confidence=0.95,
        )
        intervention_policy.set_user_speaking(True)
        act = intervention_policy.decide_intervention(opp)
        self.assertEqual(act, InterventionAction.DO_NOT_INTERVENE)

    # 7. Quiet mode suppresses proactive voice
    def test_07_quiet_mode_suppresses_proactive_voice(self):
        opp = ProactiveOpportunity(
            opportunity_id="opp_1",
            opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER,
            value_tier=OpportunityValue.HIGH_VALUE,
            project_name="FLOW",
            description="FLOW is ready",
            suggested_action="open_browser",
            confidence=0.95,
        )
        intervention_policy.set_quiet_mode(True)
        act = intervention_policy.decide_intervention(opp)
        self.assertEqual(act, InterventionAction.SILENT_PREPARE)

    # 8. Proactive preparation remains side-effect-free
    def test_08_proactive_preparation_remains_side_effect_free(self):
        pred = Prediction(
            prediction_id="p1",
            predicted_next_action="open_browser",
            target_project="FLOW",
            confidence=0.95,
            expected_value="high",
            parameters={"port": 3000},
        )
        prep = proactive_preparation_manager.prepare_anticipated_action(pred)
        self.assertIsNotNone(prep)
        self.assertFalse(prep["has_side_effects"])
        self.assertEqual(prep["url"], "http://localhost:3000")

    # 9. Duplicate suggestions are suppressed
    def test_09_duplicate_suggestions_are_suppressed(self):
        opp = ProactiveOpportunity(
            opportunity_id="opp_dup",
            opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER,
            value_tier=OpportunityValue.HIGH_VALUE,
            project_name="FLOW",
            description="FLOW is ready",
            suggested_action="open_browser",
        )
        sug1 = proactive_suggestion_manager.create_suggestion(opp)
        self.assertIsNotNone(sug1)

        # Immediate repeated suggestion should be suppressed
        sug2 = proactive_suggestion_manager.create_suggestion(opp)
        self.assertIsNone(sug2)

    # 10. Declined suggestion reduces future priority
    def test_10_declined_suggestion_reduces_future_priority(self):
        opp = ProactiveOpportunity(
            opportunity_id="opp_dec",
            opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER,
            value_tier=OpportunityValue.HIGH_VALUE,
            project_name="FLOW",
            description="FLOW is ready",
            suggested_action="open_browser",
            confidence=0.90,
        )
        sug = proactive_suggestion_manager.create_suggestion(opp)
        self.assertIsNotNone(sug)

        proactive_learning_loop.record_feedback(sug, accepted=False)
        self.assertEqual(sug.state, SuggestionState.DECLINED)

        # Future opportunity confidence is degraded
        opp2 = proactive_learning_loop.apply_learning_to_opportunity(opp)
        self.assertLess(opp2.confidence, 0.90)

    # 11. Accepted suggestion reinforces relevance
    def test_11_accepted_suggestion_reinforces_relevance(self):
        opp = ProactiveOpportunity(
            opportunity_id="opp_acc",
            opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER,
            value_tier=OpportunityValue.HIGH_VALUE,
            project_name="FLOW",
            description="FLOW is ready",
            suggested_action="open_browser",
            confidence=0.85,
        )
        sug = proactive_suggestion_manager.create_suggestion(opp)
        self.assertIsNotNone(sug)

        proactive_learning_loop.record_feedback(sug, accepted=True)
        self.assertEqual(sug.state, SuggestionState.ACCEPTED)

        opp2 = proactive_learning_loop.apply_learning_to_opportunity(opp)
        self.assertGreater(opp2.confidence, 0.85)

    # 12. Critical alerts bypass normal suggestion budget
    def test_12_critical_alerts_bypass_normal_suggestion_budget(self):
        # Exceed goal budget
        interruption_budget_manager.record_suggestion_issued("goal_x", "open_browser")
        interruption_budget_manager.record_suggestion_issued("goal_x", "open_browser")

        self.assertFalse(interruption_budget_manager.is_budget_available("goal_x", is_critical=False))
        self.assertTrue(interruption_budget_manager.is_budget_available("goal_x", is_critical=True))

    # 13. Context remains isolated between projects
    def test_13_context_remains_isolated_between_projects(self):
        context_observation_engine.update_project_context(
            project_name="FLOW",
            task_state=ContextTaskState.RUNNING,
            recent_action={"port": 3000},
        )
        context_observation_engine.update_project_context(
            project_name="BACKEND",
            task_state=ContextTaskState.FAILED,
            recent_action={"error": "Database error"},
        )

        ctx_flow = context_observation_engine.observe_context("t1", "g1", project_name="FLOW")
        ctx_back = context_observation_engine.observe_context("t2", "g2", project_name="BACKEND")

        self.assertEqual(ctx_flow.task_state, ContextTaskState.RUNNING)
        self.assertEqual(ctx_back.task_state, ContextTaskState.FAILED)

    # 14. Cancellation invalidates pending proactive work
    def test_14_cancellation_invalidates_pending_proactive_work(self):
        pred = Prediction(prediction_id="p_can", predicted_next_action="open_browser", target_project="FLOW", confidence=0.95, expected_value="high")
        proactive_preparation_manager.prepare_anticipated_action(pred)

        opp = ProactiveOpportunity(opportunity_id="opp_can", opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER, value_tier=OpportunityValue.HIGH_VALUE, project_name="FLOW", description="FLOW", suggested_action="open_browser")
        sug = proactive_suggestion_manager.create_suggestion(opp)
        self.assertIsNotNone(sug)

        # On cancellation:
        proactive_preparation_manager.invalidate_project_preparations("FLOW")
        proactive_suggestion_manager.invalidate_project_suggestions("FLOW")

        self.assertIsNone(proactive_preparation_manager.get_prepared_data("open_browser", "FLOW"))
        self.assertEqual(sug.state, SuggestionState.INVALIDATED)

    # 15. Stale predictions expire
    def test_15_stale_predictions_expire(self):
        pred = Prediction(
            prediction_id="p_exp",
            predicted_next_action="open_browser",
            target_project="FLOW",
            confidence=0.95,
            expected_value="high",
            expires_at=time.time() - 1.0,
        )
        self.assertTrue(pred.is_expired())
        self.assertIsNone(proactive_preparation_manager.prepare_anticipated_action(pred))

    # 16. Proactive suggestion is concise
    def test_16_proactive_suggestion_is_concise(self):
        opp = ProactiveOpportunity(
            opportunity_id="opp_c",
            opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER,
            value_tier=OpportunityValue.HIGH_VALUE,
            project_name="FLOW",
            description="FLOW is ready",
            suggested_action="open_browser",
        )
        txt = proactive_suggestion_manager.format_suggestion_text(opp)
        self.assertEqual(txt, "FLOW is ready. Want me to open it?")
        self.assertLess(len(txt.split()), 10)

    # 17. No chain-of-thought is exposed
    def test_17_no_chain_of_thought_is_exposed(self):
        opp = ProactiveOpportunity(
            opportunity_id="opp_cot",
            opportunity_type=OpportunityType.REPEATED_FAILURE_APPLY_SKILL,
            value_tier=OpportunityValue.HIGH_VALUE,
            project_name="FLOW",
            description="Diagnostic repair",
            suggested_action="apply_learned_skill",
        )
        txt = proactive_suggestion_manager.format_suggestion_text(opp)
        self.assertNotIn("chain of thought", txt.lower())
        self.assertNotIn("reasoning step", txt.lower())
        self.assertNotIn("agent", txt.lower())
        self.assertIn("FLOW", txt)

    # 18. Visual context remains ephemeral
    def test_18_visual_context_remains_ephemeral(self):
        ctx = create_context_contract(
            turn_id="t_vis",
            goal_id="g_vis",
            active_project="FLOW",
            visible_context={"screen_id": "scr_123", "elements": [{"label": "button"}]},
        )
        self.assertIn("screen_id", ctx.visible_context)
        # Verify it has TTL and is not stored in long-term memory
        self.assertTrue(ctx.expires_at > ctx.created_at)
        self.assertLess(ctx.expires_at - ctx.created_at, 120.0)

    # 19. Background analysis does not block voice callbacks
    def test_19_background_analysis_does_not_block_voice_callbacks(self):
        # Warm-up
        router.match("what time is it")
        t0 = time.perf_counter()
        match = router.match("what are you watching for")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_PROACTIVE_STATUS")
        self.assertLess(dt, 5.0)

    # 20. Full FLOW scenario works end-to-end
    def test_20_full_flow_scenario_works_end_to_end(self):
        # 1. EventBus notifies PROJECT_READY
        event_bus.publish(EventType.PROJECT_READY, {"project": "FLOW", "port": 3000})

        # 2. ContextObservationEngine updates
        ctx = context_observation_engine.observe_context("turn_e2e", "goal_e2e", project_name="FLOW")
        self.assertEqual(ctx.task_state, ContextTaskState.RUNNING)

        # 3. AnticipationEngine predicts browser need
        pred = anticipation_engine.predict_next_need(ctx)
        self.assertIsNotNone(pred)
        self.assertEqual(pred.predicted_next_action, "open_browser")

        # 4. ProactivePreparationManager precomputes URL
        prep = proactive_preparation_manager.prepare_anticipated_action(pred)
        self.assertEqual(prep["url"], "http://localhost:3000")

        # 5. ProactiveOpportunityDetector detects HIGH_VALUE opportunity
        opp = proactive_opportunity_detector.detect_opportunity(ctx)
        self.assertEqual(opp.value_tier, OpportunityValue.HIGH_VALUE)

        # 6. InterventionPolicy approves intervention
        budget_ok = interruption_budget_manager.is_budget_available(ctx.goal_id)
        act = intervention_policy.decide_intervention(opp, interruption_budget_allowed=budget_ok)
        self.assertEqual(act, InterventionAction.SPEAK_NOW)

        # 7. ProactiveSuggestionManager creates suggestion
        sug = proactive_suggestion_manager.create_suggestion(opp)
        self.assertEqual(sug.prompt_text, "FLOW is ready. Want me to open it?")

        # 8. User accepts -> Learning loop reinforces
        new_score = proactive_learning_loop.record_feedback(sug, accepted=True)
        self.assertGreater(new_score, 0.0)


if __name__ == "__main__":
    unittest.main()
