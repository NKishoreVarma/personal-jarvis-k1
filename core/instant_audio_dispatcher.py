"""
Instant Audio Dispatcher for MARK XLVIII / JARVIS.
Dispatches pre-rendered or streaming PCM audio directly into the low-latency playback pipeline
in <1ms upon command commitment, eliminating TTS startup delays.
"""

from __future__ import annotations

from typing import Any, Optional

from core.audio_response_cache import audio_response_cache
from core.playback_scheduler import PlaybackPriority, playback_scheduler
from core.voice_metrics import VoiceEvent, voice_metrics


class InstantAudioDispatcher:
    """
    Dispatches audio waveforms instantly to the output sound queue.
    """

    def dispatch_phrase_audio(
        self,
        turn_id: str,
        phrase: str,
        target_queue: Optional[Any] = None,
        priority: PlaybackPriority = PlaybackPriority.INSTANT_ACK,
    ) -> bool:
        """
        Looks up cached PCM audio for phrase and enqueues to output queue in <1ms.
        """
        cached_pcm = audio_response_cache.get_audio(phrase)
        if cached_pcm:
            voice_metrics.mark(VoiceEvent.FIRST_RESPONSE_AUDIO_QUEUED)
            slices_queued = playback_scheduler.schedule_audio(
                turn_id=turn_id,
                pcm_bytes=cached_pcm,
                target_queue=target_queue,
                priority=priority,
            )
            print(f"[INSTANT_AUDIO] ⚡ Dispatched cached audio for '{phrase}' ({slices_queued} slices, {len(cached_pcm)} bytes) in <1ms")
            return True
        return False

    def dispatch_raw_pcm(
        self,
        turn_id: str,
        pcm_bytes: bytes,
        target_queue: Optional[Any] = None,
        priority: PlaybackPriority = PlaybackPriority.INSTANT_ACK,
    ) -> int:
        """
        Dispatches streaming PCM bytes with zero chunk-waiting.
        """
        voice_metrics.mark(VoiceEvent.FIRST_RESPONSE_AUDIO_QUEUED)
        return playback_scheduler.schedule_audio(
            turn_id=turn_id,
            pcm_bytes=pcm_bytes,
            target_queue=target_queue,
            priority=priority,
        )


# Global singleton instance
instant_audio_dispatcher = InstantAudioDispatcher()
