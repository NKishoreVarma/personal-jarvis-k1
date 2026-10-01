"""
Duplicate Response Guard for MARK XLVIII / JARVIS.
Guarantees that verified task completions, acknowledgements, and progress notices
are never spoken twice due to duplicate events, retries, or reconnects.
"""

from __future__ import annotations

import hashlib
import time
from typing import Dict, Optional


class DuplicateResponseGuard:
    """
    In-memory bounded guard with TTL-based expiration for spoken message fingerprints.
    """

    def __init__(self, ttl_seconds: float = 60.0, max_entries: int = 200):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._history: Dict[str, float] = {}

    def _generate_fingerprint(
        self,
        turn_id: str,
        task_id: str,
        response_type: str,
        text: str,
    ) -> str:
        """Computes a deterministic hash for the response event."""
        norm_text = " ".join(text.strip().lower().split())
        raw = f"{turn_id}:{task_id}:{response_type}:{norm_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def should_suppress(
        self,
        turn_id: str,
        task_id: str,
        response_type: str,
        text: str,
    ) -> bool:
        """
        Returns True if this exact response has already been emitted within the TTL window.
        Decision completes in < 1ms.
        """
        self.cleanup_expired()
        fp = self._generate_fingerprint(turn_id, task_id, response_type, text)
        return fp in self._history

    def record_spoken(
        self,
        turn_id: str,
        task_id: str,
        response_type: str,
        text: str,
    ) -> str:
        """
        Records that a response was spoken so subsequent duplicate events are ignored.
        """
        if len(self._history) >= self.max_entries:
            self.cleanup_expired()
            if len(self._history) >= self.max_entries:
                # Evict oldest entry
                oldest_key = min(self._history, key=self._history.get)
                self._history.pop(oldest_key, None)

        fp = self._generate_fingerprint(turn_id, task_id, response_type, text)
        self._history[fp] = time.monotonic()
        return fp

    def clear_turn(self, turn_id: str) -> None:
        """Cleans up fingerprints tied to a specific turn if needed."""
        pass  # Preserved in history up to TTL to guard against late re-delivery

    def cleanup_expired(self) -> None:
        """Purges entries older than TTL."""
        now = time.monotonic()
        cutoff = now - self.ttl_seconds
        expired_keys = [k for k, ts in self._history.items() if ts < cutoff]
        for k in expired_keys:
            self._history.pop(k, None)


# Global singleton instance
duplicate_response_guard = DuplicateResponseGuard()
