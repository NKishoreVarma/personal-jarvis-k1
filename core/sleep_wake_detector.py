"""
Sleep / Wake Detector for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Detects macOS system sleep and wake events via heartbeat timestamp gaps.
Prevents false failure assumptions on wake and triggers live state re-observation.
"""

from __future__ import annotations

import time
from typing import Callable, List, Optional


class SleepWakeDetector:
    """
    Monitors monotonic timing continuity to detect OS suspension and trigger recovery checks.
    """

    SLEEP_GAP_THRESHOLD = 30.0  # seconds

    def __init__(self):
        self._last_tick: float = time.time()
        self._wake_listeners: List[Callable[[float], None]] = []

    def register_wake_listener(self, listener: Callable[[float], None]) -> None:
        self._wake_listeners.append(listener)

    def check_tick(self, current_time: Optional[float] = None) -> bool:
        """
        Evaluates elapsed interval since last tick. If gap exceeds threshold, notifies wake listeners.
        Returns True if a sleep/wake event was detected.
        """
        now = current_time if current_time is not None else time.time()
        elapsed = now - self._last_tick
        self._last_tick = now

        if elapsed > self.SLEEP_GAP_THRESHOLD:
            print(f"[SLEEP_WAKE] ☀️ System wake detected (gap: {elapsed:.1f}s). Triggering live state re-observation...")
            for listener in self._wake_listeners:
                try:
                    listener(elapsed)
                except Exception as e:
                    print(f"[SLEEP_WAKE] Warning in wake listener: {e}")
            return True

        return False

    def reset(self) -> None:
        self._last_tick = time.time()


# Global singleton instance
sleep_wake_detector = SleepWakeDetector()
