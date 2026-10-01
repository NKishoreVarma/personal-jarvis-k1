"""
Unit & Integration Tests for WakeTurnManager & Intelligent Turn-Taking (Phase 12.3).
"""

import time
import unittest

from core.acknowledgement_policy import (
    AcknowledgementClass,
    AcknowledgementPolicy,
)
from core.command_completeness import (
    CommandCompletenessAnalyzer,
    CompletenessState,
)
from core.wake_turn_manager import (
    PreRollAudioBuffer,
    WakeConfidence,
    WakeTurnManager,
    WakeTurnState,
)


class TestWakeTurnManager(unittest.TestCase):
    def setUp(self):
        self.turn_mgr = WakeTurnManager(
            post_wake_timeout_sec=0.5,
            follow_up_timeout_sec=0.8,
            duplicate_window_sec=0.5,
        )
        self.completeness = CommandCompletenessAnalyzer()
        self.ack_policy = AcknowledgementPolicy()

    def test_01_single_utterance_wake_and_command(self):
        res = self.turn_mgr.extract_wake_command("Jarvis open Chrome")
        self.assertTrue(res.wake_detected)
        self.assertEqual(res.wake_phrase, "jarvis")
        self.assertEqual(res.command, "open Chrome")
        self.assertEqual(res.confidence, WakeConfidence.HIGH_CONFIDENCE)
        self.assertFalse(res.is_follow_up)
        self.assertEqual(self.turn_mgr.state, WakeTurnState.USER_SPEAKING)

    def test_02_wake_word_only(self):
        res = self.turn_mgr.extract_wake_command("Hey Jarvis")
        self.assertTrue(res.wake_detected)
        self.assertEqual(res.wake_phrase, "hey jarvis")
        self.assertIsNone(res.command)
        self.assertEqual(self.turn_mgr.state, WakeTurnState.LISTENING_FOR_COMMAND)

    def test_03_post_wake_command_capture(self):
        # 1. Wake word only
        self.turn_mgr.extract_wake_command("Jarvis")
        self.assertEqual(self.turn_mgr.state, WakeTurnState.LISTENING_FOR_COMMAND)

        # 2. Subsequent command within post-wake window
        res = self.turn_mgr.extract_wake_command("Open FLOW")
        self.assertTrue(res.wake_detected)
        self.assertEqual(res.command, "Open FLOW")
        self.assertTrue(res.is_follow_up)
        self.assertEqual(self.turn_mgr.state, WakeTurnState.USER_SPEAKING)

    def test_04_post_wake_timeout_expiration(self):
        self.turn_mgr.extract_wake_command("Jarvis")
        self.assertEqual(self.turn_mgr.state, WakeTurnState.LISTENING_FOR_COMMAND)

        # Wait for timeout (0.5s configured)
        time.sleep(0.6)
        self.turn_mgr.check_timeouts()
        self.assertEqual(self.turn_mgr.state, WakeTurnState.IDLE)

    def test_05_follow_up_window_command_capture(self):
        # Complete a turn and enter follow-up listening
        self.turn_mgr.on_command_completed(enable_follow_up=True)
        self.assertEqual(self.turn_mgr.state, WakeTurnState.FOLLOW_UP_LISTENING)

        # Follow-up command without wake word
        res = self.turn_mgr.extract_wake_command("Run it too")
        self.assertTrue(res.wake_detected)
        self.assertTrue(res.is_follow_up)
        self.assertEqual(res.command, "Run it too")

    def test_06_ambient_speech_rejected_when_idle(self):
        self.turn_mgr.reset()
        res = self.turn_mgr.extract_wake_command("Pass the salt please")
        self.assertFalse(res.wake_detected)
        self.assertIsNone(res.command)
        self.assertEqual(self.turn_mgr.state, WakeTurnState.IDLE)

    def test_07_duplicate_turn_protection(self):
        res1 = self.turn_mgr.extract_wake_command("Jarvis open Chrome")
        self.assertFalse(res1.is_duplicate)

        res2 = self.turn_mgr.extract_wake_command("Jarvis open Chrome")
        self.assertTrue(res2.is_duplicate)

    def test_08_preroll_audio_buffer(self):
        buf = PreRollAudioBuffer(max_chunks=5)
        for i in range(7):
            buf.append_chunk(f"chunk_{i}".encode("utf-8"))

        raw = buf.get_preroll_bytes().decode("utf-8")
        # Should retain only the last 5 chunks (2 through 6)
        self.assertNotIn("chunk_0", raw)
        self.assertNotIn("chunk_1", raw)
        self.assertIn("chunk_6", raw)

    def test_09_command_completeness_analysis(self):
        res_complete = self.completeness.analyze("open Chrome")
        self.assertEqual(res_complete["state"], CompletenessState.COMPLETE)

        res_incomplete = self.completeness.analyze("open FLOW and")
        self.assertEqual(res_incomplete["state"], CompletenessState.LIKELY_INCOMPLETE)
        self.assertGreater(res_incomplete["extra_grace_ms"], 0.0)

        res_verb = self.completeness.analyze("run")
        self.assertEqual(res_verb["state"], CompletenessState.LIKELY_INCOMPLETE)

    def test_10_acknowledgement_policy(self):
        ack_instant = self.ack_policy.get_acknowledgement(
            AcknowledgementClass.INSTANT_ACTION, target_name="Chrome"
        )
        self.assertIn("Chrome", ack_instant)

        ack_bg = self.ack_policy.get_acknowledgement(
            AcknowledgementClass.BACKGROUND_TASK, target_name="FLOW"
        )
        self.assertIn("FLOW", ack_bg)


if __name__ == "__main__":
    unittest.main()
