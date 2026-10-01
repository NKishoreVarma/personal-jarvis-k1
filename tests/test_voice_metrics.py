"""
Unit tests for Voice Latency Forensics & Instrumentation (Phase 12.1).
"""

import time
import unittest

from core.voice_metrics import VoiceEvent, VoiceMetrics


class TestVoiceMetrics(unittest.TestCase):
    def setUp(self):
        self.metrics = VoiceMetrics(max_history=10)

    def test_turn_lifecycle_and_events(self):
        t_id = self.metrics.start_turn()
        self.assertTrue(t_id.startswith("turn_"))

        self.metrics.mark(VoiceEvent.FIRST_AUDIO_FRAME)
        self.metrics.mark(VoiceEvent.SPEECH_STARTED)
        time.sleep(0.01)
        self.metrics.mark(VoiceEvent.LAST_SPEECH_FRAME)
        self.metrics.mark(VoiceEvent.ENDPOINT_DETECTED)
        self.metrics.mark(VoiceEvent.COMMAND_FINALIZED)
        self.metrics.mark(VoiceEvent.LOCAL_INTENT_MATCHED)
        self.metrics.mark(VoiceEvent.FIRST_AUDIO_PLAYBACK)

        self.metrics.set_metadata("route_type", "local_intent")
        self.metrics.increment_audio_frames()

        report = self.metrics.get_report()
        self.assertIsNotNone(report)
        self.assertEqual(report["turn_id"], t_id)
        self.assertEqual(report["metadata"]["route_type"], "local_intent")
        self.assertEqual(report["metadata"]["audio_frame_count"], 1)

        cumul = report["cumulative_ms"]
        self.assertIn(VoiceEvent.WAKE_DETECTED, cumul)
        self.assertIn(VoiceEvent.FIRST_AUDIO_PLAYBACK, cumul)

        deltas = report["stage_deltas_ms"]
        self.assertIn("user_stop_to_first_audio_ms", deltas)

        ended = self.metrics.end_turn()
        self.assertIsNotNone(ended)
        self.assertIsNone(self.metrics._current_turn)


if __name__ == "__main__":
    unittest.main()
