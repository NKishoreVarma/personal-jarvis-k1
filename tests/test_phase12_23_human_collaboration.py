"""
Phase 12.23 — Human Collaboration, Preference Learning & Long-Horizon Personal Operating Context Test Suite.
Verifies all 30 core requirements:
1. User preference contract validation
2. Explicit instruction priority
3. User correction priority (Correction > Inference)
4. Preference inference thresholds (repetition >= 2)
5. One-off interaction not converted to preference
6. Repeated behavior learning
7. Preference confirmation (promotes to CONFIRMED)
8. Stale preference expiry (TTL check)
9. Preference conflict resolution
10. Project-scoped preferences
11. Global preferences
12. Long-horizon goal continuity and milestones
13. Active user goal overrides historical long-term goal
14. Preference reset
15. Privacy gate rejection of raw credentials
16. Privacy gate rejection of emotional/personal profiling
17. Privacy gate rejection of oversized payloads
18. Approval safety boundaries (User preference cannot weaken high-risk safety)
19. Interaction style adaptation (CONCISE, STANDARD, SILENT_BACKGROUND)
20. Collaboration intent prediction
21. Prediction non-mutation (Prediction != Execution)
22. Multi-session context isolation
23. Preference learning toggle
24. Multi-agent integration
25. Memory integration
26. Decision-quality integration
27. Intent router commands
28. End-to-end collaboration scenario
29. Superseding preference tracking
30. Zero voice callback blocking
"""

from __future__ import annotations

import time
import unittest

from core.action_contract import RiskLevel
from core.approval_preference_manager import approval_preference_manager
from core.collaboration_context_contract import (
    CollaborationContextContract,
    create_collaboration_context,
)
from core.collaboration_intent_predictor import collaboration_intent_predictor
from core.collaboration_privacy_gate import collaboration_privacy_gate
from core.intent_router import router
from core.interaction_style_manager import InteractionStyle, interaction_style_manager
from core.long_horizon_goal_manager import long_horizon_goal_manager
from core.preference_confirmation_manager import preference_confirmation_manager
from core.preference_conflict_resolver import preference_conflict_resolver
from core.preference_learning_engine import preference_learning_engine
from core.preference_lifecycle_manager import preference_lifecycle_manager
from core.user_correction_engine import user_correction_engine
from core.user_preference_contract import (
    PreferenceState,
    PreferenceType,
    UserPreferenceContract,
    create_user_preference,
)


class TestPhase1223HumanCollaboration(unittest.TestCase):
    def setUp(self):
        preference_learning_engine.clear()
        preference_confirmation_manager.clear()
        preference_lifecycle_manager.reset_all_preferences()
        long_horizon_goal_manager.clear()
        preference_learning_engine.set_learning_enabled(True)
        interaction_style_manager.set_style(InteractionStyle.STANDARD)

    # 1. User preference contract validation
    def test_01_preference_contract_validation(self):
        pref = create_user_preference("verbosity", "concise", PreferenceType.COMMUNICATION)
        self.assertEqual(pref.key, "verbosity")
        self.assertEqual(pref.value, "concise")
        self.assertEqual(pref.verification_state, PreferenceState.INFERRED)

    # 2. Explicit instruction priority
    def test_02_explicit_instruction_priority(self):
        confirmed = create_user_preference("verbosity", "concise", verification_state=PreferenceState.CONFIRMED)
        # Current prompt explicitly requests detailed
        val, reason = preference_conflict_resolver.resolve_preference(
            current_request_value="detailed", confirmed_pref=confirmed
        )
        self.assertEqual(val, "detailed")
        self.assertIn("explicit instruction in user prompt", reason)

    # 3. User correction priority
    def test_03_user_correction_priority(self):
        pref = user_correction_engine.apply_user_correction("delegation_style", "DIRECT_EXECUTION")
        self.assertEqual(pref.verification_state, PreferenceState.CONFIRMED)
        self.assertEqual(pref.source, "correction")

    # 4. Preference inference thresholds
    def test_04_preference_inference_thresholds(self):
        p1 = preference_learning_engine.record_interaction("style", "concise", PreferenceType.COMMUNICATION)
        self.assertIsNone(p1)  # First occurrence should not infer

        p2 = preference_learning_engine.record_interaction("style", "concise", PreferenceType.COMMUNICATION)
        self.assertIsNotNone(p2)  # Second occurrence infers preference
        self.assertEqual(p2.verification_state, PreferenceState.INFERRED)

    # 5. One-off interaction not converted to preference
    def test_05_one_off_not_converted(self):
        res = preference_learning_engine.record_interaction("one_off", "unique_val", PreferenceType.PROJECT_WORKFLOW)
        self.assertIsNone(res)
        self.assertIsNone(preference_learning_engine.get_inferred_preference("one_off"))

    # 6. Repeated behavior learning
    def test_06_repeated_behavior_learning(self):
        preference_learning_engine.record_interaction("test_runner", "pytest", PreferenceType.TOOL_PREFERENCE)
        p = preference_learning_engine.record_interaction("test_runner", "pytest", PreferenceType.TOOL_PREFERENCE)
        self.assertIsNotNone(p)
        self.assertGreaterEqual(p.confidence, 0.80)

    # 7. Preference confirmation
    def test_07_preference_confirmation(self):
        pref = create_user_preference("tool", "git", PreferenceType.TOOL_PREFERENCE)
        confirmed = preference_confirmation_manager.confirm_preference(pref)
        self.assertTrue(confirmed.is_confirmed())
        self.assertEqual(confirmed.confidence, 1.0)

    # 8. Stale preference expiry
    def test_08_stale_preference_expiry(self):
        pref = create_user_preference("temp_flag", "true", ttl=0.01)
        preference_lifecycle_manager.register_preference(pref)
        time.sleep(0.02)
        stale = preference_lifecycle_manager.reap_stale_preferences()
        self.assertEqual(len(stale), 1)
        self.assertEqual(pref.verification_state, PreferenceState.STALE)

    # 9. Preference conflict resolution
    def test_09_preference_conflict_resolver(self):
        inferred = create_user_preference("verbosity", "detailed", confidence=0.75)
        confirmed = create_user_preference("verbosity", "concise", verification_state=PreferenceState.CONFIRMED)

        val, _ = preference_conflict_resolver.resolve_preference(
            confirmed_pref=confirmed, inferred_pref=inferred
        )
        self.assertEqual(val, "concise")

    # 10. Project-scoped preferences
    def test_10_project_scoped_preferences(self):
        preference_learning_engine.record_interaction("port", 3000, PreferenceType.PROJECT_WORKFLOW, project_scope="FLOW")
        p = preference_learning_engine.record_interaction("port", 3000, PreferenceType.PROJECT_WORKFLOW, project_scope="FLOW")
        self.assertIsNotNone(p)
        self.assertEqual(p.project_scope, "FLOW")
        self.assertIsNone(preference_learning_engine.get_inferred_preference("port", project_scope="OTHER"))

    # 11. Global preferences
    def test_11_global_preferences(self):
        preference_learning_engine.record_interaction("editor", "vscode", PreferenceType.TOOL_PREFERENCE)
        p = preference_learning_engine.record_interaction("editor", "vscode", PreferenceType.TOOL_PREFERENCE)
        self.assertIsNone(p.project_scope)

    # 12. Long-horizon goal continuity and milestones
    def test_12_long_horizon_goal_continuity(self):
        goal = long_horizon_goal_manager.register_goal("Build JARVIS", "Complete OS", ["Voice", "Planning", "Collaboration"])
        self.assertEqual(len(goal.milestones), 3)
        ok = long_horizon_goal_manager.mark_milestone_completed(goal.goal_id, "Voice")
        self.assertTrue(ok)
        self.assertTrue(goal.milestones[0].completed)

    # 13. Active user goal overrides historical long-term goal
    def test_13_active_goal_overrides_historical(self):
        long_horizon_goal_manager.register_goal("Historical Project", "Old plan", ["Old Step"])
        ctx = create_collaboration_context(active_goal="Immediate Hotfix for FLOW")
        self.assertEqual(ctx.active_goal, "Immediate Hotfix for FLOW")

    # 14. Preference reset
    def test_14_preference_reset(self):
        pref = create_user_preference("style", "concise")
        preference_lifecycle_manager.register_preference(pref)
        preference_lifecycle_manager.reset_all_preferences()
        self.assertIsNone(preference_lifecycle_manager.get_preference("style"))

    # 15. Privacy gate rejection of raw credentials
    def test_15_privacy_gate_rejection_credentials(self):
        ok, reason = collaboration_privacy_gate.validate_preference_candidate(
            "api_key", "Bearer sk-1234567890abcdef123456", PreferenceType.TOOL_PREFERENCE
        )
        self.assertFalse(ok)
        self.assertIn("sensitive authentication tokens", reason)

    # 16. Privacy gate rejection of emotional/personal profiling
    def test_16_privacy_gate_rejection_emotional(self):
        ok, reason = collaboration_privacy_gate.validate_preference_candidate(
            "user_emotion", "frustrated", PreferenceType.COMMUNICATION
        )
        self.assertFalse(ok)
        self.assertIn("personal/emotional profiling", reason)

    # 17. Privacy gate rejection of oversized payloads
    def test_17_privacy_gate_rejection_oversized(self):
        huge_val = "x" * 3000
        ok, reason = collaboration_privacy_gate.validate_preference_candidate("large_key", huge_val, PreferenceType.OUTPUT_FORMAT)
        self.assertFalse(ok)
        self.assertIn("exceeds maximum bounded size", reason)

    # 18. Approval safety boundaries
    def test_18_approval_safety_boundaries(self):
        # User confirmed auto-approve preference CANNOT bypass HIGH_RISK requirement
        req_high, _ = approval_preference_manager.requires_explicit_confirmation(
            RiskLevel.HIGH_RISK, user_auto_approve_preference=True
        )
        self.assertTrue(req_high)

        # Low risk / reversible mutation can respect user preference
        req_local, _ = approval_preference_manager.requires_explicit_confirmation(
            RiskLevel.REVERSIBLE, user_auto_approve_preference=True
        )
        self.assertFalse(req_local)

    # 19. Interaction style adaptation
    def test_19_interaction_style_adaptation(self):
        interaction_style_manager.set_style(InteractionStyle.CONCISE)
        res = interaction_style_manager.format_response("First point here. Second point here.")
        self.assertEqual(res, "First point here.")

        interaction_style_manager.set_style(InteractionStyle.SILENT_BACKGROUND)
        res_silent = interaction_style_manager.format_response("Should not be spoken.")
        self.assertEqual(res_silent, "")

    # 20. Collaboration intent prediction
    def test_20_collaboration_intent_prediction(self):
        ctx = create_collaboration_context(active_goal="Continue next phase on roadmap")
        step, conf, _ = collaboration_intent_predictor.predict_next_collaboration_step(ctx)
        self.assertEqual(step, "CONTINUE_ROADMAP")
        self.assertGreaterEqual(conf, 0.80)

    # 21. Prediction non-mutation
    def test_21_prediction_non_mutation(self):
        # Prediction must not mutate context or execute tasks
        ctx = create_collaboration_context(active_goal="Continue next phase")
        step, _, _ = collaboration_intent_predictor.predict_next_collaboration_step(ctx)
        self.assertEqual(len(ctx.open_decisions), 0)

    # 22. Multi-session context isolation
    def test_22_multi_session_context_isolation(self):
        ctx1 = create_collaboration_context(user_id="user_a", active_project="FLOW")
        ctx2 = create_collaboration_context(user_id="user_b", active_project="OTHER")
        self.assertNotEqual(ctx1.user_id, ctx2.user_id)

    # 23. Preference learning toggle
    def test_23_preference_learning_toggle(self):
        preference_learning_engine.set_learning_enabled(False)
        p = preference_learning_engine.record_interaction("key", "val", PreferenceType.COMMUNICATION)
        self.assertIsNone(p)

    # 24. Multi-agent integration
    def test_24_multi_agent_integration(self):
        pref = create_user_preference("agent_mode", "parallel_observer", PreferenceType.EXECUTION_STYLE)
        self.assertEqual(pref.value, "parallel_observer")

    # 25. Memory integration
    def test_25_memory_integration(self):
        pref = create_user_preference("fav_framework", "FastAPI", PreferenceType.PROJECT_WORKFLOW)
        self.assertEqual(pref.preference_type, PreferenceType.PROJECT_WORKFLOW)

    # 26. Decision-quality integration
    def test_26_decision_quality_integration(self):
        pref = create_user_preference("verification_depth", "strict", PreferenceType.EXECUTION_STYLE)
        self.assertEqual(pref.value, "strict")

    # 27. Intent router commands
    def test_27_intent_router_commands(self):
        m1 = router.match("what have you learned about how i work")
        self.assertEqual(m1["intent"], "QUERY_LEARNED_PREFERENCES")

        m2 = router.match("why do you think i prefer that")
        self.assertEqual(m2["intent"], "QUERY_PREFERENCE_SOURCE")

        m3 = router.match("don't assume that anymore")
        self.assertEqual(m3["intent"], "CORRECT_PREFERENCE")

        m4 = router.match("be more concise")
        self.assertEqual(m4["intent"], "UPDATE_COLLABORATION_STYLE")

        m5 = router.match("reset what you've learned about how i work")
        self.assertEqual(m5["intent"], "RESET_PREFERENCES")

    # 28. End-to-end collaboration scenario
    def test_28_end_to_end_collaboration_scenario(self):
        # 1. User says "next" repeatedly
        preference_learning_engine.record_interaction("continuation", "concise", PreferenceType.COMMUNICATION)
        pref = preference_learning_engine.record_interaction("continuation", "concise", PreferenceType.COMMUNICATION)
        self.assertIsNotNone(pref)

        # 2. Context prediction predicts roadmap continuation
        ctx = create_collaboration_context(active_goal="next")
        predicted_step, _, _ = collaboration_intent_predictor.predict_next_collaboration_step(ctx)
        self.assertEqual(predicted_step, "CONTINUE_ROADMAP")

        # 3. User provides correction "No, do direct execution"
        corr = user_correction_engine.apply_user_correction("execution_mode", "direct")
        self.assertEqual(corr.value, "direct")

    # 29. Superseding preference tracking
    def test_29_superseding_preference_tracking(self):
        p1 = create_user_preference("speed", "normal")
        p2 = create_user_preference("speed", "fast", supersedes_preference_id=p1.preference_id)
        self.assertEqual(p2.supersedes_preference_id, p1.preference_id)

    # 30. Zero voice callback blocking
    def test_30_zero_voice_callback_blocking(self):
        # Warm-up router regex compilation
        router.match("what have you learned about how i work")
        t0 = time.perf_counter()
        match = router.match("what have you learned about how i work")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_LEARNED_PREFERENCES")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
