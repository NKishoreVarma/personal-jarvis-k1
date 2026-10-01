"""
Ultra-Fast Wake, Command Detection & Intelligent Turn-Taking Manager for MARK XLVIII / JARVIS.
Owns turn lifecycle, single-utterance wake+command extraction, post-wake command window,
follow-up conversation window, pre-roll audio buffering, false-wake protection, and duplicate turn deduplication.
"""

from __future__ import annotations

import collections
import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from core.command_completeness import CompletenessState, command_completeness


class WakeTurnState(str, Enum):
    IDLE = "IDLE"
    WAKE_DETECTED = "WAKE_DETECTED"
    LISTENING_FOR_COMMAND = "LISTENING_FOR_COMMAND"
    USER_SPEAKING = "USER_SPEAKING"
    SOFT_ENDPOINT = "SOFT_ENDPOINT"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"
    FOLLOW_UP_LISTENING = "FOLLOW_UP_LISTENING"


class WakeConfidence(str, Enum):
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


@dataclass
class TurnExtractionResult:
    wake_detected: bool
    wake_phrase: Optional[str]
    command: Optional[str]
    confidence: WakeConfidence
    is_follow_up: bool = False
    is_duplicate: bool = False


class PreRollAudioBuffer:
    """
    Lock-free, bounded in-memory ring buffer holding recent audio chunks to prevent clipping.
    """

    def __init__(self, max_chunks: int = 10):  # 10 x 50ms = 500ms pre-roll
        self.max_chunks = max_chunks
        self._buffer: collections.deque = collections.deque(maxlen=max_chunks)

    def append_chunk(self, data: bytes) -> None:
        """Appends an audio chunk in non-blocking O(1) time."""
        self._buffer.append(data)

    def get_preroll_bytes(self) -> bytes:
        """Returns concatenated pre-roll audio bytes."""
        return b"".join(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()


class WakeTurnManager:
    """
    Authoritative coordinator for wake word activation, command extraction, and conversation turn state.
    """

    WAKE_ALIASES: List[str] = [
        "hey jarvis",
        "okay jarvis",
        "ok jarvis",
        "hi jarvis",
        "jarvis",
    ]

    def __init__(
        self,
        post_wake_timeout_sec: float = 4.0,
        follow_up_timeout_sec: float = 7.0,
        duplicate_window_sec: float = 2.0,
    ):
        self.post_wake_timeout_sec = post_wake_timeout_sec
        self.follow_up_timeout_sec = follow_up_timeout_sec
        self.duplicate_window_sec = duplicate_window_sec

        self.state: WakeTurnState = WakeTurnState.IDLE
        self.state_changed_at: float = time.monotonic()
        self.preroll_buffer = PreRollAudioBuffer(max_chunks=10)

        self._recent_turns: Dict[str, float] = {}  # fp -> timestamp
        self._current_command: Optional[str] = None
        self._turn_id: int = 0

    def set_state(self, new_state: WakeTurnState) -> None:
        """Transitions state and records timestamp."""
        prev = self.state
        self.state = new_state
        self.state_changed_at = time.monotonic()
        print(f"[TURN_MANAGER] State: {prev.value} -> {new_state.value}")

    def extract_wake_command(self, raw_text: str) -> TurnExtractionResult:
        """
        Extracts wake phrase and command from a spoken transcript.
        Handles:
        1. Wake word only ("Jarvis")
        2. Wake word + command in single utterance ("Jarvis open Chrome")
        3. Follow-up commands without wake word ("Run it") when in FOLLOW_UP_LISTENING
        """
        clean = raw_text.strip()
        lower = clean.lower()
        now = time.monotonic()

        # Check follow-up window expiration
        if self.state == WakeTurnState.FOLLOW_UP_LISTENING:
            if (now - self.state_changed_at) > self.follow_up_timeout_sec:
                self.set_state(WakeTurnState.IDLE)

        # 1. Match wake aliases
        wake_match = None
        matched_alias = None

        for alias in self.WAKE_ALIASES:
            pattern = r"^(?:" + re.escape(alias) + r")[\s,:\.!\?-]*(.*)$"
            m = re.match(pattern, clean, re.IGNORECASE)
            if m:
                matched_alias = alias
                rest = m.group(1).strip()
                wake_match = rest if rest else None
                break

        # Case A: Wake word found
        if matched_alias is not None:
            self._turn_id += 1
            cmd = wake_match if (wake_match and len(wake_match) > 0) else None

            # Duplicate check
            is_dup = False
            if cmd:
                fp = hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:12]
                last_time = self._recent_turns.get(fp, 0.0)
                if (now - last_time) < self.duplicate_window_sec:
                    is_dup = True
                else:
                    self._recent_turns[fp] = now

            if cmd:
                self.set_state(WakeTurnState.USER_SPEAKING)
            else:
                self.set_state(WakeTurnState.LISTENING_FOR_COMMAND)

            return TurnExtractionResult(
                wake_detected=True,
                wake_phrase=matched_alias,
                command=cmd,
                confidence=WakeConfidence.HIGH_CONFIDENCE,
                is_follow_up=False,
                is_duplicate=is_dup,
            )

        # Case B: Follow-up window active (command without wake word)
        if self.state in (WakeTurnState.FOLLOW_UP_LISTENING, WakeTurnState.LISTENING_FOR_COMMAND):
            # Evaluate post-wake timeout
            if self.state == WakeTurnState.LISTENING_FOR_COMMAND and (now - self.state_changed_at) > self.post_wake_timeout_sec:
                self.set_state(WakeTurnState.IDLE)
                return TurnExtractionResult(
                    wake_detected=False,
                    wake_phrase=None,
                    command=None,
                    confidence=WakeConfidence.LOW_CONFIDENCE,
                )

            # Valid follow-up command
            cmd = clean if clean else None
            is_dup = False
            if cmd:
                fp = hashlib.sha256(cmd.lower().encode("utf-8")).hexdigest()[:12]
                last_time = self._recent_turns.get(fp, 0.0)
                if (now - last_time) < self.duplicate_window_sec:
                    is_dup = True
                else:
                    self._recent_turns[fp] = now

            if cmd:
                self.set_state(WakeTurnState.USER_SPEAKING)

            return TurnExtractionResult(
                wake_detected=True,
                wake_phrase=None,
                command=cmd,
                confidence=WakeConfidence.HIGH_CONFIDENCE,
                is_follow_up=True,
                is_duplicate=is_dup,
            )

        # Case C: Random ambient speech without wake word -> Ignore
        return TurnExtractionResult(
            wake_detected=False,
            wake_phrase=None,
            command=None,
            confidence=WakeConfidence.LOW_CONFIDENCE,
        )

    def on_command_completed(self, enable_follow_up: bool = True) -> None:
        """Called when JARVIS finishes processing and speaking a response."""
        if enable_follow_up:
            self.set_state(WakeTurnState.FOLLOW_UP_LISTENING)
        else:
            self.set_state(WakeTurnState.IDLE)

    def check_timeouts(self) -> None:
        """Housekeeping check for post-wake or follow-up expirations."""
        now = time.monotonic()
        if self.state == WakeTurnState.LISTENING_FOR_COMMAND:
            if (now - self.state_changed_at) > self.post_wake_timeout_sec:
                print("[TURN_MANAGER] Post-wake timeout expired -> IDLE")
                self.set_state(WakeTurnState.IDLE)
        elif self.state == WakeTurnState.FOLLOW_UP_LISTENING:
            if (now - self.state_changed_at) > self.follow_up_timeout_sec:
                print("[TURN_MANAGER] Follow-up window expired -> IDLE")
                self.set_state(WakeTurnState.IDLE)

        # Prune old turn fingerprints
        for fp, ts in list(self._recent_turns.items()):
            if (now - ts) > (self.duplicate_window_sec * 3):
                self._recent_turns.pop(fp, None)

    def reset(self) -> None:
        self.state = WakeTurnState.IDLE
        self.state_changed_at = time.monotonic()
        self.preroll_buffer.clear()
        self._current_command = None


# Global singleton
wake_turn_manager = WakeTurnManager()
