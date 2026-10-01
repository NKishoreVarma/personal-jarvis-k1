"""
Playback Scheduler for MARK XLVIII / JARVIS.
Coordinates output audio streams with turn-bound validation, priority queuing,
and automatic dropping of stale packets from prior interaction turns.
"""

from __future__ import annotations

import asyncio
from enum import IntEnum
from typing import Any, Dict, Optional

from core.audio_prebuffer import audio_prebuffer
from core.response_interruption_manager import response_interruption_manager


class PlaybackPriority(IntEnum):
    CRITICAL_ALERT = 1
    INSTANT_ACK = 2
    COMPLETION = 3
    PROGRESS = 4


class PlaybackScheduler:
    """
    Schedules audio playback slices while enforcing turn isolation and dropping stale audio.
    """

    def __init__(self):
        self.active_turn_id: Optional[str] = None
        self._playback_lock = asyncio.Lock()

    def set_active_turn(self, turn_id: str, target_queue: Optional[Any] = None) -> None:
        """Transitions active turn and immediately flushes stale audio from prior turns."""
        if self.active_turn_id != turn_id:
            old_turn = self.active_turn_id
            self.active_turn_id = turn_id
            if old_turn is not None and target_queue is not None:
                # Flush stale audio from old turn
                response_interruption_manager.interrupt_playback(
                    audio_in_queue=target_queue,
                    reason=f"Turn switched: {old_turn} -> {turn_id}",
                )

    def schedule_audio(
        self,
        turn_id: str,
        pcm_bytes: bytes,
        target_queue: Optional[Any] = None,
        priority: PlaybackPriority = PlaybackPriority.INSTANT_ACK,
    ) -> int:
        """
        Slices and enqueues PCM audio into output queue if turn matches active turn.
        Drops audio if turn is stale.
        """
        if self.active_turn_id is not None and turn_id != self.active_turn_id:
            print(f"[PLAYBACK_SCHEDULER] ⚠️ Dropped stale audio for turn '{turn_id}' (active turn is '{self.active_turn_id}')")
            return 0

        slices = audio_prebuffer.slice_audio(pcm_bytes)
        if target_queue is not None:
            for s in slices:
                try:
                    target_queue.put_nowait(s)
                except Exception as e:
                    print(f"[PLAYBACK_SCHEDULER] Queue put error: {e}")
                    break

        return len(slices)

    def clear(self, target_queue: Optional[Any] = None) -> None:
        """Flushes all queued audio slices."""
        response_interruption_manager.interrupt_playback(audio_in_queue=target_queue)


# Global singleton instance
playback_scheduler = PlaybackScheduler()
