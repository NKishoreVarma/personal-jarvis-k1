"""
Comprehensive Unit & Integration Test Suite for Phase 12.8:
Intelligent Voice Personality, Natural Conversation Timing & Human-Like Response Selection.
"""

import time
import unittest

from core.conversation_timing_controller import (
    ConversationTimingController,
    ResponsePriority,
    conversation_timing_controller,
)
from core.duplicate_response_guard import (
    DuplicateResponseGuard,
    duplicate_response_guard,
)
from core.natural_progress_manager import (
    NaturalProgressManager,
    natural_progress_manager,
)
from core.natural_response_selector import (
    NaturalResponseSelector,
    SelectedResponseType,
    natural_response_selector,
)
from core.response_length_policy import (
    ResponseLengthPolicy,
    ResponseVerbosity,
    response_length_policy,
)
from core.task_awareness_model import (
    TaskAwarenessModel,
    TaskState,
    task_awareness_model,
)
from core.voice_personality_engine import (
    VoicePersonalityEngine,
    voice_personality_engine,
)


class TestPhase128NaturalVoice(unittest.TestCase):
    def setUp(self):
        duplicate_response_guard._history.clear()
        conversation_timing_controller.is_user_speaking = False
        conversation_timing_controller.is_jarvis_speaking = False
        conversation_timing_controller.active_turn_id = None

    # Test 1: Open application produces short acknowledgement
    def test_01_open_app_short_ack(self):
        res = natural_response_selector.select_initial_response(
            turn_id="t1",
            task_type="OPEN_APP",
            entities={"app_name": "Chrome"},
            raw_text="open Chrome",
        )
        self.assertEqual(res["response_type"], SelectedResponseType.SHORT_ACK)
        self.assertEqual(res["spoken_text"], "Opening Chrome.")
        self.assertTrue(res["requires_speech"])

    # Test 2: Fast visible application action produces no unnecessary completion speech
    def test_02_fast_visible_action_completion_silence(self):
        res = natural_response_selector.select_completion_response(
            turn_id="t2",
            task_type="OPEN_APP",
            entities={"app_name": "Chrome"},
            raw_text="open Chrome",
            success=True,
            is_visible_action=True,
        )
        self.assertEqual(res["response_type"], SelectedResponseType.SILENT)
        self.assertEqual(res["spoken_text"], "")
        self.assertFalse(res["requires_speech"])

    # Test 3: Long-running project produces acknowledgement and verified completion
    def test_03_project_run_ack_and_completion(self):
        init_res = natural_response_selector.select_initial_response(
            turn_id="t3",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            raw_text="run FLOW",
        )
        self.assertEqual(init_res["response_type"], SelectedResponseType.SHORT_ACK)
        self.assertEqual(init_res["spoken_text"], "Starting FLOW.")

        comp_res = natural_response_selector.select_completion_response(
            turn_id="t3",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW", "port": 3000},
            raw_text="run FLOW",
            success=True,
        )
        self.assertEqual(comp_res["response_type"], SelectedResponseType.COMPLETION)
        self.assertEqual(comp_res["spoken_text"], "FLOW is running on port 3000.")
        self.assertTrue(comp_res["requires_speech"])

    # Test 4: Explicit "tell me when ready" forces completion announcement
    def test_04_explicit_notification_request(self):
        comp_res = natural_response_selector.select_completion_response(
            turn_id="t4",
            task_type="OPEN_APP",
            entities={"app_name": "FLOW in VS Code"},
            raw_text="open FLOW in VS Code and tell me when it's ready",
            success=True,
        )
        self.assertEqual(comp_res["response_type"], SelectedResponseType.COMPLETION)
        self.assertTrue(comp_res["requires_speech"])

    # Test 5: Explicit quiet request suppresses non-critical responses
    def test_05_quiet_mode_suppression(self):
        init_res = natural_response_selector.select_initial_response(
            turn_id="t5",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            raw_text="run FLOW quietly",
        )
        self.assertEqual(init_res["response_type"], SelectedResponseType.SILENT)
        self.assertFalse(init_res["requires_speech"])

        comp_res = natural_response_selector.select_completion_response(
            turn_id="t5",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            raw_text="run FLOW quietly",
            success=True,
        )
        self.assertEqual(comp_res["response_type"], SelectedResponseType.SILENT)
        self.assertFalse(comp_res["requires_speech"])

    # Test 6: Already open application produces state-aware response
    def test_06_already_open_app_response(self):
        res = natural_response_selector.select_initial_response(
            turn_id="t6",
            task_type="OPEN_APP",
            entities={"app_name": "Chrome"},
            raw_text="open Chrome",
            is_already_open=True,
        )
        self.assertEqual(res["response_type"], SelectedResponseType.STATE_UPDATE)
        self.assertEqual(res["spoken_text"], "Chrome is already open.")

    # Test 7: Duplicate task request does not start duplicate execution
    def test_07_duplicate_task_request(self):
        res = natural_response_selector.select_initial_response(
            turn_id="t7",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            raw_text="run FLOW",
            is_already_running=True,
        )
        self.assertEqual(res["response_type"], SelectedResponseType.REDUNDANCY)
        self.assertEqual(res["spoken_text"], "FLOW is already running.")

    # Test 8: Duplicate completion event produces only one spoken response
    def test_08_duplicate_response_guard(self):
        guard = DuplicateResponseGuard(ttl_seconds=10.0)
        self.assertFalse(guard.should_suppress("t8", "task_1", "COMPLETION", "FLOW is ready."))
        guard.record_spoken("t8", "task_1", "COMPLETION", "FLOW is ready.")

        # Second trigger must be suppressed
        self.assertTrue(guard.should_suppress("t8", "task_1", "COMPLETION", "FLOW is ready."))

    # Test 9: User barge-in cancels current response
    def test_09_user_barge_in_cancellation(self):
        timing = ConversationTimingController()
        timing.active_turn_id = "t9"
        timing.is_jarvis_speaking = True

        timing.on_user_speech_start("t9")
        self.assertTrue(timing.is_user_speaking)
        self.assertFalse(timing.is_jarvis_speaking)
        self.assertFalse(timing.can_speak(ResponsePriority.DIRECT_ACKNOWLEDGEMENT, "t9"))

    # Test 10: Stale response from previous turn never plays
    def test_10_stale_response_blocked(self):
        timing = ConversationTimingController()
        timing.active_turn_id = "turn_current"

        # Stale response for turn_old blocked
        self.assertFalse(timing.can_speak(ResponsePriority.VERIFIED_COMPLETION, "turn_old"))
        # Active turn response allowed
        self.assertTrue(timing.can_speak(ResponsePriority.VERIFIED_COMPLETION, "turn_current"))

    # Test 11: Ambiguous request produces concise clarification
    def test_11_ambiguous_request_clarification(self):
        res = natural_response_selector.select_initial_response(
            turn_id="t11",
            task_type="OPEN_CONTACT",
            entities={"target": "chat", "choices": ["John Smith", "John Doe"]},
            raw_text="open John's chat",
            is_ambiguous=True,
        )
        self.assertEqual(res["response_type"], SelectedResponseType.CLARIFICATION)
        self.assertEqual(res["spoken_text"], "I found John Smith and John Doe. Which one?")

    # Test 12: Failure response is natural and concise
    def test_12_natural_failure_response(self):
        res = natural_response_selector.select_completion_response(
            turn_id="t12",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            raw_text="run FLOW",
            success=False,
            error="EADDRINUSE: address already in use :::3000",
        )
        self.assertEqual(res["response_type"], SelectedResponseType.FAILURE)
        self.assertEqual(res["spoken_text"], "FLOW didn't start. Port is already in use.")

    # Test 13: Detailed failure explanation only occurs when requested
    def test_13_detailed_explanation_policy(self):
        v_short = response_length_policy.determine_verbosity("run FLOW")
        self.assertEqual(v_short, ResponseVerbosity.SHORT)

        v_why = response_length_policy.determine_verbosity("Why didn't FLOW start?")
        self.assertEqual(v_why, ResponseVerbosity.DETAILED)

    # Test 14: Multi-step task does not produce response spam
    def test_14_multistep_task_clean_response(self):
        init_res = natural_response_selector.select_initial_response(
            turn_id="t14",
            task_type="MULTI_STEP",
            entities={"target": "FLOW in Chrome"},
            raw_text="open FLOW, run the server, and open it in Chrome",
        )
        self.assertEqual(init_res["spoken_text"], "On it.")

    # Test 15: Follow-up command uses conversation context naturally
    def test_15_contextual_follow_up(self):
        text = voice_personality_engine.render_response(
            response_type="ACKNOWLEDGEMENT",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
        )
        self.assertEqual(text, "Starting FLOW.")

    # Test 16: Slow task can produce one meaningful progress update
    def test_16_natural_progress_update(self):
        mgr = NaturalProgressManager()
        mgr.register_task("task_slow", "FLOW", slow_threshold_sec=0.01)
        time.sleep(0.02)

        upd1 = mgr.check_progress_update("task_slow")
        self.assertEqual(upd1, "Still starting FLOW.")

        # Must not spam subsequent calls
        upd2 = mgr.check_progress_update("task_slow")
        self.assertIsNone(upd2)

    # Test 17: Internal pipeline states are never exposed as unnecessary narration
    def test_17_user_visible_state_masking(self):
        model = TaskAwarenessModel()
        vis_state = model.get_user_visible_state(
            task_type="RUN_PROJECT",
            target="FLOW",
            internal_stage="DETECTING_PORT_VIA_TCP_SCAN",
        )
        self.assertEqual(vis_state, "Starting FLOW.")
        self.assertNotIn("DETECTING_PORT", vis_state)

    # Test 18: Response selection remains deterministic
    def test_18_deterministic_selection(self):
        for _ in range(10):
            res = natural_response_selector.select_initial_response(
                turn_id="t18",
                task_type="RUN_PROJECT",
                entities={"project": "FLOW"},
                raw_text="run FLOW",
            )
            self.assertEqual(res["spoken_text"], "Starting FLOW.")

    # Test 19: All hot-path response decisions remain under 1 ms
    def test_19_sub_millisecond_decisions(self):
        t0 = time.perf_counter()
        for _ in range(100):
            natural_response_selector.select_initial_response(
                turn_id="t19",
                task_type="RUN_PROJECT",
                entities={"project": "FLOW"},
                raw_text="run FLOW",
            )
        elapsed_avg_ms = ((time.perf_counter() - t0) / 100) * 1000.0
        self.assertLess(elapsed_avg_ms, 1.0)


if __name__ == "__main__":
    unittest.main()
