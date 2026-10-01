"""
Perceived Latency Controller for MARK XLVIII / JARVIS.
Orchestrates the critical end-to-end voice timeline from speech termination to first audio emission,
ensuring zero-perceived-latency verbal responses.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.instant_audio_dispatcher import instant_audio_dispatcher
from core.playback_scheduler import PlaybackPriority, playback_scheduler
from core.response_contract import ResponseContract
from core.voice_metrics import VoiceEvent, voice_metrics


@dataclass
class LatencyProfile:
    turn_id: str
    endpoint_to_ack_ms: float
    ack_to_audio_queued_ms: float
    total_reaction_ms: float
    audio_dispatched: bool


class PerceivedLatencyController:
    """
    Coordinates sub-millisecond audio handoff upon hard endpoint detection.
    """

    def on_hard_endpoint(
        self,
        turn_id: str,
        response_contract: Optional[ResponseContract] = None,
        target_audio_queue: Optional[Any] = None,
    ) -> LatencyProfile:
        """
        Executes immediate audio dispatch upon hard endpoint confirmation.
        """
        t_start = time.perf_counter()
        playback_scheduler.set_active_turn(turn_id, target_queue=target_audio_queue)

        dispatched = False
        t_ack = time.perf_counter()

        if response_contract and response_contract.ack_response:
            # Attempt instant pre-cached audio dispatch
            dispatched = instant_audio_dispatcher.dispatch_phrase_audio(
                turn_id=turn_id,
                phrase=response_contract.ack_response,
                target_queue=target_audio_queue,
                priority=PlaybackPriority.INSTANT_ACK,
            )

        t_queued = time.perf_counter()

        endpoint_to_ack_ms = (t_ack - t_start) * 1000.0
        ack_to_audio_queued_ms = (t_queued - t_ack) * 1000.0
        total_reaction_ms = (t_queued - t_start) * 1000.0

        return LatencyProfile(
            turn_id=turn_id,
            endpoint_to_ack_ms=round(endpoint_to_ack_ms, 3),
            ack_to_audio_queued_ms=round(ack_to_audio_queued_ms, 3),
            total_reaction_ms=round(total_reaction_ms, 3),
            audio_dispatched=dispatched,
        )


# Global singleton instance
perceived_latency_controller = PerceivedLatencyController()
