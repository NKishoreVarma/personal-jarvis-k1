"""
Unit & Integration Tests for Adaptive Ultra-Low-Latency Voice Endpointing (Phase 12.2).
"""

import time
import unittest

from core.adaptive_endpoint import (
    AdaptiveEndpointController,
    EndpointDecisionType,
    EndpointState,
)
from core.voice_metrics import VoiceEvent, voice_metrics


class TestAdaptiveEndpoint(unittest.TestCase):
    def setUp(self):
        self.controller = AdaptiveEndpointController(
            min_endpoint_ms=120.0,
            max_endpoint_ms=450.0,
            continuation_grace_ms=150.0,
            soft_grace_ms=60.0,
        )
        voice_metrics.reset()

    def test_01_short_command_threshold(self):
        # Short speech (< 600ms)
        self.controller.on_voice_frame()
        self.controller.on_partial_transcript("Mute")
        thresh = self.controller.calculate_target_threshold_ms()
        self.assertLessEqual(thresh, 220.0)
        self.assertGreaterEqual(thresh, 120.0)

    def test_02_normal_command_threshold(self):
        # Normal speech (simulate 2000ms duration)
        now = time.perf_counter()
        self.controller.speech_started_at = now - 2.0
        self.controller.last_speech_at = now
        self.controller.on_partial_transcript("Open FLOW and run the server")
        thresh = self.controller.calculate_target_threshold_ms()
        self.assertGreaterEqual(thresh, 240.0)
        self.assertLessEqual(thresh, 300.0)

    def test_03_long_speech_threshold(self):
        # Long speech (> 4000ms duration)
        now = time.perf_counter()
        self.controller.speech_started_at = now - 4.5
        self.controller.last_speech_at = now
        thresh = self.controller.calculate_target_threshold_ms()
        self.assertGreaterEqual(thresh, 320.0)
        self.assertLessEqual(thresh, 450.0)

    def test_04_trailing_and_delays_endpoint(self):
        self.controller.on_voice_frame()
        self.controller.on_partial_transcript("open chrome and")
        self.assertTrue(self.controller.is_continuation_suspected)
        thresh = self.controller.calculate_target_threshold_ms()
        # Should include continuation grace
        self.assertGreaterEqual(thresh, 300.0)

    def test_05_trailing_then_delays_endpoint(self):
        self.controller.on_voice_frame()
        self.controller.on_partial_transcript("build the project then")
        self.assertTrue(self.controller.is_continuation_suspected)

    def test_06_speech_resumption_cancels_soft_endpoint(self):
        self.controller.on_voice_frame()
        self.controller.state = EndpointState.SOFT_ENDPOINT
        dec = self.controller.on_voice_frame()
        self.assertEqual(self.controller.state, EndpointState.SPEECH_ACTIVE)
        self.assertEqual(dec.decision, EndpointDecisionType.NONE)

    def test_07_hard_endpoint_finalizes_correctly(self):
        now = time.perf_counter()
        self.controller.state = EndpointState.SPEECH_ACTIVE
        self.controller.speech_started_at = now - 0.5
        self.controller.last_speech_at = now - 0.25
        self.controller.silence_started_at = now - 0.25  # 250ms silence

        dec = self.controller.on_silence_frame()
        self.assertEqual(dec.decision, EndpointDecisionType.HARD_ENDPOINT)
        self.assertEqual(self.controller.state, EndpointState.HARD_ENDPOINT)

    def test_08_silence_below_threshold_does_not_finalize(self):
        now = time.perf_counter()
        self.controller.state = EndpointState.SPEECH_ACTIVE
        self.controller.speech_started_at = now - 1.0
        self.controller.last_speech_at = now - 0.05
        self.controller.silence_started_at = now - 0.05  # 50ms silence

        dec = self.controller.on_silence_frame()
        self.assertEqual(dec.decision, EndpointDecisionType.NONE)

    def test_09_silence_above_threshold_finalizes(self):
        now = time.perf_counter()
        self.controller.state = EndpointState.SPEECH_ACTIVE
        self.controller.speech_started_at = now - 1.0
        self.controller.last_speech_at = now - 0.3
        self.controller.silence_started_at = now - 0.3  # 300ms silence

        dec = self.controller.on_silence_frame()
        self.assertEqual(dec.decision, EndpointDecisionType.HARD_ENDPOINT)

    def test_10_controller_reset_works(self):
        self.controller.on_voice_frame()
        self.controller.on_partial_transcript("testing")
        self.controller.reset()
        self.assertEqual(self.controller.state, EndpointState.IDLE)
        self.assertEqual(self.controller.voice_frame_count, 0)
        self.assertEqual(self.controller.partial_transcript, "")

    def test_11_min_threshold_respected(self):
        self.controller.min_endpoint_ms = 120.0
        self.controller.speech_started_at = time.perf_counter()
        thresh = self.controller.calculate_target_threshold_ms()
        self.assertGreaterEqual(thresh, 120.0)

    def test_12_max_threshold_respected(self):
        self.controller.max_endpoint_ms = 450.0
        self.controller.speech_started_at = time.perf_counter() - 100.0
        self.controller.is_continuation_suspected = True
        thresh = self.controller.calculate_target_threshold_ms()
        self.assertLessEqual(thresh, 450.0)

    def test_13_no_negative_timing_values(self):
        metrics = self.controller.get_metrics()
        self.assertGreaterEqual(metrics["speech_duration_ms"], 0.0)
        self.assertGreaterEqual(metrics["silence_duration_ms"], 0.0)
        self.assertGreaterEqual(metrics["target_threshold_ms"], 0.0)

    def test_14_voice_metrics_receives_endpoint_events(self):
        voice_metrics.start_turn()
        voice_metrics.mark(VoiceEvent.SPEECH_STARTED)
        time.sleep(0.01)
        voice_metrics.mark(VoiceEvent.LAST_SPEECH_FRAME)
        voice_metrics.mark(VoiceEvent.SOFT_ENDPOINT_DETECTED)
        voice_metrics.mark(VoiceEvent.HARD_ENDPOINT_DETECTED)
        voice_metrics.mark(VoiceEvent.FIRST_AUDIO_PLAYBACK)

        report = voice_metrics.get_report()
        self.assertIsNotNone(report)
        deltas = report["stage_deltas_ms"]
        self.assertIn("soft_endpoint_delay_ms", deltas)
        self.assertIn("hard_endpoint_delay_ms", deltas)


if __name__ == "__main__":
    unittest.main()
