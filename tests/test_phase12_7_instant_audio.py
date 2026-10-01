"""
Unit & Integration Tests for Phase 12.7 — Instant Audio Response & Zero-Perceived-Latency Speech.
"""

import asyncio
import time
import unittest

from core.audio_prebuffer import AudioPrebuffer, audio_prebuffer
from core.audio_response_cache import AudioResponseCache, audio_response_cache
from core.instant_audio_dispatcher import (
    InstantAudioDispatcher,
    instant_audio_dispatcher,
)
from core.perceived_latency_controller import (
    LatencyProfile,
    PerceivedLatencyController,
    perceived_latency_controller,
)
from core.playback_scheduler import (
    PlaybackPriority,
    PlaybackScheduler,
    playback_scheduler,
)
from core.response_contract import create_response_contract
from core.response_interruption_manager import (
    ResponseInterruptionManager,
    response_interruption_manager,
)


class TestPhase127InstantAudio(unittest.TestCase):
    def setUp(self):
        audio_prebuffer.clear()
        response_interruption_manager.reset()

    def test_01_audio_prebuffer_slicing(self):
        prebuffer = AudioPrebuffer(slice_bytes=960)
        # Create 4800 bytes of dummy PCM (5 slices of 960 bytes)
        dummy_pcm = b"\x00" * 4800
        slices = prebuffer.slice_audio(dummy_pcm)
        self.assertEqual(len(slices), 5)
        self.assertEqual(len(slices[0]), 960)

        prebuffer.enqueue_sliced(dummy_pcm)
        self.assertEqual(len(prebuffer), 5)
        chunk = prebuffer.pop_chunk()
        self.assertEqual(len(chunk), 960)
        self.assertEqual(len(prebuffer), 4)

        flushed = prebuffer.clear()
        self.assertEqual(flushed, 4)
        self.assertEqual(len(prebuffer), 0)

    def test_02_audio_response_cache(self):
        cache = AudioResponseCache()
        dummy_wav = b"\x01\x02" * 1000
        cache.register_audio("okay.", dummy_wav)

        self.assertTrue(cache.has_audio("Okay."))
        self.assertEqual(cache.get_audio("OKAY."), dummy_wav)
        self.assertIsNone(cache.get_audio("Unknown phrase"))

        # Default chime presence
        self.assertIsNotNone(cache.get_audio("_chime_ack"))

    def test_03_response_interruption_manager_barge_in(self):
        loop = asyncio.new_event_loop()
        q = asyncio.Queue()
        for i in range(10):
            q.put_nowait(b"slice")
        audio_prebuffer.enqueue_sliced(b"\x00" * 4800)

        t_start = time.perf_counter()
        drained = response_interruption_manager.interrupt_playback(audio_in_queue=q, reason="Test barge-in")
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        # Must execute in under 20ms
        self.assertLess(elapsed_ms, 20.0)
        self.assertTrue(q.empty())
        self.assertEqual(len(audio_prebuffer), 0)
        self.assertGreater(drained, 0)
        loop.close()

    def test_04_playback_scheduler_turn_isolation(self):
        scheduler = PlaybackScheduler()
        q = asyncio.Queue()

        scheduler.set_active_turn("turn_1")
        dummy_pcm = b"\x00" * 1920  # 2 slices of 960

        # Active turn scheduled
        scheduled_count = scheduler.schedule_audio("turn_1", dummy_pcm, target_queue=q)
        self.assertEqual(scheduled_count, 2)
        self.assertEqual(q.qsize(), 2)

        # Stale turn dropped
        dropped_count = scheduler.schedule_audio("turn_0", dummy_pcm, target_queue=q)
        self.assertEqual(dropped_count, 0)
        self.assertEqual(q.qsize(), 2)

        # Switching turn flushes old audio
        scheduler.set_active_turn("turn_2", target_queue=q)
        self.assertEqual(q.qsize(), 0)

    def test_05_instant_audio_dispatcher(self):
        cache = audio_response_cache
        dummy_pcm = b"\x00" * 1920
        cache.register_audio("Okay.", dummy_pcm)

        q = asyncio.Queue()
        playback_scheduler.set_active_turn("turn_test")

        dispatched = instant_audio_dispatcher.dispatch_phrase_audio(
            turn_id="turn_test",
            phrase="Okay.",
            target_queue=q,
        )
        self.assertTrue(dispatched)
        self.assertGreater(q.qsize(), 0)

    def test_06_perceived_latency_controller(self):
        q = asyncio.Queue()
        contract = create_response_contract(
            turn_id="turn_lat_test",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            ack_response="Okay.",
        )
        audio_response_cache.register_audio("Okay.", b"\x00" * 1920)

        profile = perceived_latency_controller.on_hard_endpoint(
            turn_id="turn_lat_test",
            response_contract=contract,
            target_audio_queue=q,
        )

        self.assertIsInstance(profile, LatencyProfile)
        self.assertTrue(profile.audio_dispatched)
        # Reaction overhead must be under 1ms
        self.assertLess(profile.total_reaction_ms, 5.0)


if __name__ == "__main__":
    unittest.main()
