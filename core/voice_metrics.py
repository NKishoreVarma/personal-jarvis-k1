"""
Voice Latency Forensics & Instrumentation Metrics for MARK XLVIII / JARVIS.
Provides high-resolution, non-blocking, in-memory timestamp metrics using time.perf_counter().
Zero I/O and zero print calls inside high-frequency audio callbacks.
"""

from __future__ import annotations

import collections
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class VoiceEvent:
    WAKE_DETECTED = "WAKE_DETECTED"
    FIRST_AUDIO_FRAME = "FIRST_AUDIO_FRAME"
    SPEECH_STARTED = "SPEECH_STARTED"
    LAST_SPEECH_FRAME = "LAST_SPEECH_FRAME"
    SOFT_ENDPOINT_DETECTED = "SOFT_ENDPOINT_DETECTED"
    HARD_ENDPOINT_DETECTED = "HARD_ENDPOINT_DETECTED"
    ENDPOINT_DETECTED = "HARD_ENDPOINT_DETECTED"  # Alias for backward compatibility
    BARGE_IN_DETECTED = "BARGE_IN_DETECTED"
    OUTPUT_INTERRUPTED = "OUTPUT_INTERRUPTED"
    COMMAND_FINALIZED = "COMMAND_FINALIZED"
    LOCAL_INTENT_MATCHED = "LOCAL_INTENT_MATCHED"
    GEMINI_SEND_STARTED = "GEMINI_SEND_STARTED"
    GEMINI_FIRST_RESPONSE = "GEMINI_FIRST_RESPONSE"
    FIRST_RESPONSE_AUDIO_QUEUED = "FIRST_RESPONSE_AUDIO_QUEUED"
    FIRST_AUDIO_PLAYBACK = "FIRST_AUDIO_PLAYBACK"
    TURN_COMPLETED = "TURN_COMPLETED"

    # Phase 12.5 Streaming Intent & Zero-Wait Handoff Events
    STREAMING_INTENT_UPDATED = "STREAMING_INTENT_UPDATED"
    INTENT_STABILIZED = "INTENT_STABILIZED"
    PREDICTIVE_PREPARATION_STARTED = "PREDICTIVE_PREPARATION_STARTED"
    PREDICTIVE_PREPARATION_COMPLETED = "PREDICTIVE_PREPARATION_COMPLETED"
    COMMAND_COMMITTED = "COMMAND_COMMITTED"
    HANDOFF_CLAIMED = "HANDOFF_CLAIMED"
    HANDOFF_FALLBACK = "HANDOFF_FALLBACK"
    EXECUTION_STARTED = "EXECUTION_STARTED"


@dataclass
class VoiceTurnRecord:
    turn_id: str
    start_perf: float
    timestamps: Dict[str, float] = field(default_factory=dict)
    event_order: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VoiceMetrics:
    """
    Lightweight, thread-safe, non-blocking voice latency instrumentation collector.
    """

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._current_turn: Optional[VoiceTurnRecord] = None
        self._history: collections.deque = collections.deque(maxlen=max_history)

    def start_turn(self, turn_id: Optional[str] = None) -> str:
        """Starts timing a new voice interaction turn."""
        t_id = turn_id or f"turn_{uuid.uuid4().hex[:8]}"
        now = time.perf_counter()
        self._current_turn = VoiceTurnRecord(
            turn_id=t_id,
            start_perf=now,
            timestamps={VoiceEvent.WAKE_DETECTED: now},
            event_order=[VoiceEvent.WAKE_DETECTED],
            metadata={
                "audio_frame_count": 0,
                "route_type": "unknown",
                "interrupted_previous_response": False,
                "handoff_claimed": False,
            },
        )
        return t_id

    def mark(self, event_name: str) -> None:
        """
        Records a timestamp for a named event in the active turn.
        Zero allocation, non-blocking, safe in audio callbacks.
        """
        if self._current_turn is not None:
            now = time.perf_counter()
            self._current_turn.timestamps[event_name] = now
            self._current_turn.event_order.append(event_name)

    def increment_audio_frames(self) -> None:
        """Increments audio frame counter without locks or I/O."""
        if self._current_turn is not None:
            self._current_turn.metadata["audio_frame_count"] += 1

    def set_metadata(self, key: str, value: Any) -> None:
        """Sets metadata attribute on current turn."""
        if self._current_turn is not None:
            self._current_turn.metadata[key] = value

    def end_turn(self) -> Optional[Dict[str, Any]]:
        """Completes active turn and saves record to bounded history."""
        if self._current_turn is None:
            return None

        self.mark(VoiceEvent.TURN_COMPLETED)
        report = self.get_report()
        self._history.append(self._current_turn)
        self._current_turn = None
        return report

    def get_report(self) -> Optional[Dict[str, Any]]:
        """
        Calculates delta latencies (in milliseconds and seconds) across all stages.
        """
        if self._current_turn is None and not self._history:
            return None

        turn = self._current_turn or self._history[-1]
        ts = turn.timestamps
        t_start = turn.start_perf

        # Calculate stage deltas
        deltas_ms: Dict[str, float] = {}
        cumulative_ms: Dict[str, float] = {}

        for evt in turn.event_order:
            if evt in ts:
                cumulative_ms[evt] = round((ts[evt] - t_start) * 1000.0, 2)

        # Stage specific deltas
        def _delta(e1: str, e2: str) -> Optional[float]:
            if e1 in ts and e2 in ts:
                return round((ts[e2] - ts[e1]) * 1000.0, 2)
            return None

        soft_endpoint_ms = _delta(VoiceEvent.LAST_SPEECH_FRAME, VoiceEvent.SOFT_ENDPOINT_DETECTED)
        hard_endpoint_ms = _delta(VoiceEvent.LAST_SPEECH_FRAME, VoiceEvent.HARD_ENDPOINT_DETECTED)
        commit_delay_ms = _delta(VoiceEvent.HARD_ENDPOINT_DETECTED, VoiceEvent.COMMAND_COMMITTED)
        handoff_delay_ms = _delta(VoiceEvent.COMMAND_COMMITTED, VoiceEvent.HANDOFF_CLAIMED)
        exec_start_delay_ms = _delta(VoiceEvent.COMMAND_COMMITTED, VoiceEvent.EXECUTION_STARTED)
        route_decision_ms = _delta(VoiceEvent.HARD_ENDPOINT_DETECTED, VoiceEvent.COMMAND_FINALIZED)
        gemini_ttft_ms = _delta(VoiceEvent.GEMINI_SEND_STARTED, VoiceEvent.GEMINI_FIRST_RESPONSE)
        first_audio_ms = _delta(VoiceEvent.GEMINI_FIRST_RESPONSE, VoiceEvent.FIRST_AUDIO_PLAYBACK)
        total_latency_from_speech_end = _delta(VoiceEvent.LAST_SPEECH_FRAME, VoiceEvent.FIRST_AUDIO_PLAYBACK)

        return {
            "turn_id": turn.turn_id,
            "metadata": dict(turn.metadata),
            "cumulative_ms": cumulative_ms,
            "stage_deltas_ms": {
                "soft_endpoint_delay_ms": soft_endpoint_ms,
                "hard_endpoint_delay_ms": hard_endpoint_ms,
                "commit_delay_ms": commit_delay_ms,
                "handoff_delay_ms": handoff_delay_ms,
                "exec_start_delay_ms": exec_start_delay_ms,
                "route_decision_ms": route_decision_ms,
                "gemini_ttft_ms": gemini_ttft_ms,
                "playback_queue_to_audio_ms": first_audio_ms,
                "user_stop_to_first_audio_ms": total_latency_from_speech_end,
            },
            "timestamps_perf": dict(ts),
        }

    def reset(self) -> None:
        self._current_turn = None
        self._history.clear()


# Global singleton instance
voice_metrics = VoiceMetrics()
