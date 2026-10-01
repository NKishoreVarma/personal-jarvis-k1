"""
Resource Governor for MARK XLVIII / JARVIS.
Monitors CPU-sensitive workloads and protects real-time voice and audio pipelines
by throttling or deferring background worker activity during voice interactions.
"""

from __future__ import annotations

import time
from typing import Dict


class ResourceGovernor:
    """
    Protects voice pipeline latency by governing background worker concurrency.
    """

    def __init__(self, default_max_workers: int = 4):
        self.default_max_workers = default_max_workers
        self.is_user_speaking: bool = False
        self.is_audio_playing: bool = False
        self.last_voice_activity: float = 0.0

    def update_voice_state(self, user_speaking: bool, audio_playing: bool) -> None:
        self.is_user_speaking = user_speaking
        self.is_audio_playing = audio_playing
        if user_speaking or audio_playing:
            self.last_voice_activity = time.time()

    def should_defer_background_work(self) -> bool:
        """Returns True if user is actively speaking or audio is playing."""
        if self.is_user_speaking or self.is_audio_playing:
            return True
        # Cool-down window of 0.5s after speech
        if time.time() - self.last_voice_activity < 0.5:
            return True
        return False

    def get_max_allowed_workers(self) -> int:
        """Throttles concurrency when voice pipeline is active."""
        if self.should_defer_background_work():
            return 1
        return self.default_max_workers


# Global singleton instance
resource_governor = ResourceGovernor()
