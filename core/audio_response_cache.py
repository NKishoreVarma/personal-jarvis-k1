"""
Audio Response Cache for MARK XLVIII / JARVIS.
Stores pre-synthesized in-memory PCM audio waveforms for frequent spoken acknowledgements,
enabling instant (<1ms) audio dispatch without waiting for cloud TTS generation.
"""

from __future__ import annotations

import math
import struct
from typing import Dict, List, Optional


class AudioResponseCache:
    """
    In-memory cache of pre-rendered 24kHz 16-bit mono PCM audio for common responses.
    """

    SAMPLE_RATE = 24000
    CHANNELS = 1
    SAMPLE_WIDTH = 2  # 16-bit

    def __init__(self):
        self._cache: Dict[str, bytes] = {}
        self._initialize_default_tones()

    def _initialize_default_tones(self) -> None:
        """
        Generates lightweight, natural audio chimes/tones for instant audio cues.
        """
        # Subtle 440Hz warm chime for instant feedback (120ms duration)
        self._cache["_chime_ready"] = self._synthesize_sine_wave(frequency=523.25, duration_sec=0.10, volume=0.25)
        self._cache["_chime_ack"] = self._synthesize_sine_wave(frequency=659.25, duration_sec=0.08, volume=0.20)

    def _synthesize_sine_wave(self, frequency: float, duration_sec: float, volume: float = 0.3) -> bytes:
        """Synthesizes smooth sine tone in raw 16-bit PCM format."""
        num_samples = int(self.SAMPLE_RATE * duration_sec)
        pcm_data = bytearray()
        for i in range(num_samples):
            t = float(i) / self.SAMPLE_RATE
            # Smooth attack and decay envelope
            envelope = math.sin(math.pi * (i / num_samples))
            sample_val = int(volume * envelope * 32767.0 * math.sin(2.0 * math.pi * frequency * t))
            sample_val = max(-32768, min(32767, sample_val))
            pcm_data.extend(struct.pack("<h", sample_val))
        return bytes(pcm_data)

    def register_audio(self, phrase: str, pcm_bytes: bytes) -> None:
        """Caches pre-synthesized PCM bytes for a specific phrase."""
        norm = phrase.strip().lower()
        self._cache[norm] = pcm_bytes

    def get_audio(self, phrase: str) -> Optional[bytes]:
        """Retrieves cached PCM audio for a phrase if available."""
        norm = phrase.strip().lower()
        return self._cache.get(norm)

    def has_audio(self, phrase: str) -> bool:
        return phrase.strip().lower() in self._cache

    def clear(self) -> None:
        self._cache.clear()
        self._initialize_default_tones()


# Global singleton instance
audio_response_cache = AudioResponseCache()
