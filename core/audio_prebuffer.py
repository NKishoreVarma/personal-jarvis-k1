"""
Low-Latency Audio Slicer and Pre-buffer for MARK XLVIII / JARVIS.
Slices PCM audio into ultra-fine streaming frames (10-25ms) to prevent chunk-waiting
and enable sub-20ms instant playback interruption and cancellation.
"""

from __future__ import annotations

import collections
from typing import Iterator, List, Optional


class AudioPrebuffer:
    """
    Slices raw PCM audio bytes into fine-grained streaming slices without heap churn.
    Default slice size: 960 bytes (20ms at 24,000 Hz, 16-bit mono).
    """

    DEFAULT_SLICE_BYTES = 960  # 24000 Hz * 2 bytes/sample * 0.020s

    def __init__(self, slice_bytes: int = DEFAULT_SLICE_BYTES):
        self.slice_bytes = slice_bytes
        self._queue: collections.deque = collections.deque()

    def slice_audio(self, pcm_bytes: bytes) -> List[bytes]:
        """Slices PCM byte stream into fine-grained chunks."""
        if not pcm_bytes:
            return []
        slices = []
        for i in range(0, len(pcm_bytes), self.slice_bytes):
            slices.append(pcm_bytes[i : i + self.slice_bytes])
        return slices

    def enqueue_sliced(self, pcm_bytes: bytes) -> int:
        """Slices and enqueues chunks in O(1) amortized time."""
        chunks = self.slice_audio(pcm_bytes)
        for chunk in chunks:
            self._queue.append(chunk)
        return len(chunks)

    def pop_chunk(self) -> Optional[bytes]:
        """Pops the next fine-grained slice for the output audio stream."""
        if self._queue:
            return self._queue.popleft()
        return None

    def clear(self) -> int:
        """Flushes all queued slices immediately (sub-millisecond purge)."""
        count = len(self._queue)
        self._queue.clear()
        return count

    def __len__(self) -> int:
        return len(self._queue)


# Global singleton instance
audio_prebuffer = AudioPrebuffer()
