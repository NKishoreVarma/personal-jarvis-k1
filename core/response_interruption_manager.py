"""
Response Interruption & Barge-In Manager for MARK XLVIII / JARVIS.
Enforces the invariant: BARGE_IN > CURRENT PLAYBACK and STALE AUDIO MUST BE DROPPED.
Drains all audio queues, halts speaker output, and transitions turn state in <20ms.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from core.audio_prebuffer import audio_prebuffer
from core.voice_metrics import VoiceEvent, voice_metrics


class ResponseInterruptionManager:
    """
    Sub-20ms audio playback cutoff and queue purging coordinator.
    """

    def __init__(self):
        self._is_interrupted: bool = False
        self._last_interrupted_at: float = 0.0

    def interrupt_playback(
        self,
        audio_in_queue: Optional[Any] = None,
        ui_instance: Optional[Any] = None,
        reason: str = "User barge-in",
    ) -> int:
        """
        Immediately purges active output audio queues and cuts off speech playback in <20ms.
        """
        now = time.monotonic()
        self._is_interrupted = True
        self._last_interrupted_at = now

        # Record metrics
        voice_metrics.mark(VoiceEvent.BARGE_IN_DETECTED)
        voice_metrics.mark(VoiceEvent.OUTPUT_INTERRUPTED)
        voice_metrics.set_metadata("interrupted_previous_response", True)

        drained_chunks = 0

        # 1. Drain raw asyncio / queue chunks
        if audio_in_queue is not None:
            while True:
                try:
                    audio_in_queue.get_nowait()
                    drained_chunks += 1
                except Exception:
                    break

        # 2. Drain fine-grained prebuffer
        drained_prebuffer = audio_prebuffer.clear()
        total_drained = drained_chunks + drained_prebuffer

        if total_drained > 0:
            print(f"[INTERRUPT] ✋ Cutoff active speech ({reason}) — {total_drained} audio slices discarded in {(time.monotonic() - now)*1000:.2f}ms")

        if ui_instance is not None:
            try:
                ui_instance.set_state("LISTENING")
            except Exception:
                pass

        return total_drained

    def reset(self) -> None:
        self._is_interrupted = False


# Global singleton instance
response_interruption_manager = ResponseInterruptionManager()
