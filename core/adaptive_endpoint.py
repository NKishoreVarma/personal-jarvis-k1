"""
Adaptive Ultra-Low-Latency Voice Endpoint Controller for MARK XLVIII / JARVIS.
Dynamically chooses silence thresholds based on speech duration, energy, cadence,
and linguistic continuation cues, using a two-stage soft/hard endpoint model.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EndpointState(str, Enum):
    IDLE = "IDLE"
    SPEECH_ACTIVE = "SPEECH_ACTIVE"
    SOFT_ENDPOINT = "SOFT_ENDPOINT"
    HARD_ENDPOINT = "HARD_ENDPOINT"


class EndpointDecisionType(str, Enum):
    NONE = "NONE"
    SOFT_ENDPOINT = "SOFT_ENDPOINT"
    HARD_ENDPOINT = "HARD_ENDPOINT"
    BARGE_IN = "BARGE_IN"


@dataclass
class EndpointDecision:
    decision: EndpointDecisionType
    state: EndpointState
    silence_duration_ms: float
    target_threshold_ms: float
    is_continuation_suspected: bool = False
    reason: str = ""


class AdaptiveEndpointController:
    """
    Non-blocking, adaptive end-of-speech detector.
    """

    MIN_ENDPOINT_MS = 120.0
    MAX_ENDPOINT_MS = 450.0
    SHORT_COMMAND_SPEECH_MS = 1500.0
    CONTINUATION_GRACE_MS = 150.0
    DEFAULT_SOFT_GRACE_MS = 60.0

    # Trailing connectors indicating that the user is about to say more
    CONTINUATION_TRAILING_WORDS = {
        "and", "then", "after", "once", "but", "or", "because", "so",
        "in", "on", "from", "with", "to", "for", "at", "about", "into",
    }

    def __init__(
        self,
        min_endpoint_ms: float = 120.0,
        max_endpoint_ms: float = 450.0,
        continuation_grace_ms: float = 150.0,
        soft_grace_ms: float = 60.0,
    ):
        self.min_endpoint_ms = min_endpoint_ms
        self.max_endpoint_ms = max_endpoint_ms
        self.continuation_grace_ms = continuation_grace_ms
        self.soft_grace_ms = soft_grace_ms

        self.state = EndpointState.IDLE
        self.speech_started_at: Optional[float] = None
        self.last_speech_at: Optional[float] = None
        self.silence_started_at: Optional[float] = None
        self.soft_endpoint_at: Optional[float] = None

        self.voice_frame_count: int = 0
        self.silence_frame_count: int = 0
        self.partial_transcript: str = ""
        self.is_continuation_suspected: bool = False

    def reset(self) -> None:
        """Resets state for a new interaction turn."""
        self.state = EndpointState.IDLE
        self.speech_started_at = None
        self.last_speech_at = None
        self.silence_started_at = None
        self.soft_endpoint_at = None
        self.voice_frame_count = 0
        self.silence_frame_count = 0
        self.partial_transcript = ""
        self.is_continuation_suspected = False

    def on_voice_frame(self, energy: float = 1.0) -> EndpointDecision:
        """
        Called when voice activity is detected in a frame.
        Handles speech initiation and barge-in / resumption from soft endpoint.
        """
        now = time.perf_counter()
        self.voice_frame_count += 1
        self.last_speech_at = now
        self.silence_started_at = None

        # 1. Resumption from Soft Endpoint -> Cancel Soft Endpoint and resume speech
        if self.state == EndpointState.SOFT_ENDPOINT:
            self.state = EndpointState.SPEECH_ACTIVE
            self.soft_endpoint_at = None
            return EndpointDecision(
                decision=EndpointDecisionType.NONE,
                state=self.state,
                silence_duration_ms=0.0,
                target_threshold_ms=self.calculate_target_threshold_ms(),
                reason="Speech resumed during soft endpoint grace window",
            )

        # 2. First speech frame in IDLE
        if self.state in (EndpointState.IDLE, EndpointState.HARD_ENDPOINT):
            self.state = EndpointState.SPEECH_ACTIVE
            self.speech_started_at = now
            self.soft_endpoint_at = None
            return EndpointDecision(
                decision=EndpointDecisionType.NONE,
                state=self.state,
                silence_duration_ms=0.0,
                target_threshold_ms=self.calculate_target_threshold_ms(),
                reason="Speech started",
            )

        return EndpointDecision(
            decision=EndpointDecisionType.NONE,
            state=self.state,
            silence_duration_ms=0.0,
            target_threshold_ms=self.calculate_target_threshold_ms(),
            reason="Speech continuing",
        )

    def on_silence_frame(self, energy: float = 0.0) -> EndpointDecision:
        """
        Called when silence is detected in a frame.
        Evaluates two-stage soft and hard endpoint conditions.
        """
        now = time.perf_counter()
        self.silence_frame_count += 1

        if self.state == EndpointState.IDLE:
            return EndpointDecision(
                decision=EndpointDecisionType.NONE,
                state=self.state,
                silence_duration_ms=0.0,
                target_threshold_ms=self.min_endpoint_ms,
            )

        if self.silence_started_at is None:
            self.silence_started_at = self.last_speech_at or now

        silence_ms = (now - self.silence_started_at) * 1000.0
        target_hard_ms = self.calculate_target_threshold_ms()
        target_soft_ms = max(self.min_endpoint_ms, target_hard_ms - self.soft_grace_ms)

        # 1. Evaluate Hard Endpoint
        if silence_ms >= target_hard_ms:
            self.state = EndpointState.HARD_ENDPOINT
            return EndpointDecision(
                decision=EndpointDecisionType.HARD_ENDPOINT,
                state=self.state,
                silence_duration_ms=silence_ms,
                target_threshold_ms=target_hard_ms,
                is_continuation_suspected=self.is_continuation_suspected,
                reason=f"Hard endpoint reached ({silence_ms:.1f}ms >= {target_hard_ms:.1f}ms)",
            )

        # 2. Evaluate Soft Endpoint
        if silence_ms >= target_soft_ms and self.state == EndpointState.SPEECH_ACTIVE:
            self.state = EndpointState.SOFT_ENDPOINT
            self.soft_endpoint_at = now
            return EndpointDecision(
                decision=EndpointDecisionType.SOFT_ENDPOINT,
                state=self.state,
                silence_duration_ms=silence_ms,
                target_threshold_ms=target_hard_ms,
                is_continuation_suspected=self.is_continuation_suspected,
                reason=f"Soft endpoint entered ({silence_ms:.1f}ms >= {target_soft_ms:.1f}ms)",
            )

        return EndpointDecision(
            decision=EndpointDecisionType.NONE,
            state=self.state,
            silence_duration_ms=silence_ms,
            target_threshold_ms=target_hard_ms,
            is_continuation_suspected=self.is_continuation_suspected,
        )

    def on_partial_transcript(self, text: str) -> None:
        """
        Ingests incoming transcription fragments to detect trailing continuation cues via CommandCompletenessAnalyzer.
        """
        from core.command_completeness import CompletenessState, command_completeness
        self.partial_transcript = text.strip()
        analysis = command_completeness.analyze(self.partial_transcript)
        if analysis["state"] == CompletenessState.LIKELY_INCOMPLETE:
            self.is_continuation_suspected = True
            self.continuation_grace_ms = analysis.get("extra_grace_ms", 150.0)
        else:
            self.is_continuation_suspected = False

    def calculate_target_threshold_ms(self) -> float:
        """
        Dynamically calculates the optimal hard endpoint threshold in milliseconds.
        """
        now = time.perf_counter()
        speech_dur_ms = 0.0
        if self.speech_started_at:
            ref_end = self.last_speech_at or now
            speech_dur_ms = max(0.0, (ref_end - self.speech_started_at) * 1000.0)

        # Base category based on speech length
        if speech_dur_ms < 600.0:
            # Very short command: "Mute", "Stop", "Time" -> 160ms
            base_threshold = 160.0
        elif speech_dur_ms < self.SHORT_COMMAND_SPEECH_MS:
            # Short command: "Open Chrome", "What time is it" -> 210ms
            base_threshold = 210.0
        elif speech_dur_ms < 3500.0:
            # Normal command: "Open FLOW and run the server" -> 260ms
            base_threshold = 260.0
        else:
            # Long / complex speech -> 340ms
            base_threshold = 340.0

        # Add continuation grace if connector word detected
        if self.is_continuation_suspected:
            base_threshold += self.continuation_grace_ms

        # Clamp between MIN and MAX
        return min(max(base_threshold, self.min_endpoint_ms), self.max_endpoint_ms)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns non-blocking snapshot of current endpointing telemetry."""
        now = time.perf_counter()
        silence_ms = 0.0
        if self.silence_started_at:
            silence_ms = max(0.0, (now - self.silence_started_at) * 1000.0)

        speech_ms = 0.0
        if self.speech_started_at:
            ref_end = self.last_speech_at or now
            speech_ms = max(0.0, (ref_end - self.speech_started_at) * 1000.0)

        return {
            "state": self.state.value,
            "speech_duration_ms": round(speech_ms, 2),
            "silence_duration_ms": round(silence_ms, 2),
            "target_threshold_ms": round(self.calculate_target_threshold_ms(), 2),
            "is_continuation_suspected": self.is_continuation_suspected,
            "voice_frame_count": self.voice_frame_count,
            "silence_frame_count": self.silence_frame_count,
        }


# Global singleton instance
adaptive_endpoint = AdaptiveEndpointController()
