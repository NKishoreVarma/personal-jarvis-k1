"""
Screen Observer for MARK XLVIII / JARVIS.
Integrates with existing screen capture infrastructure (actions/screen_capture.py, actions/screen_processor.py)
to provide event-driven, task-scoped screen perception without continuous background surveillance.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

from actions.screen_capture import screen_capture_service
from core.perception_contract import (
    Observation,
    ObservationType,
    PrivacyClassification,
    create_observation,
)


class ScreenObserver:
    """
    On-demand screen observer producing normalized Observation records.
    Never persists unrestricted raw screenshot histories.
    """

    def __init__(self):
        self._last_screen_hash: Optional[str] = None
        self._last_capture_time: float = 0.0

    def observe(
        self,
        bounds: Optional[Tuple[int, int, int, int]] = None,
        correlation_id: Optional[str] = None,
    ) -> Observation:
        """
        Captures on-demand screen or region and normalizes into an Observation contract.
        """
        t0 = time.perf_counter()

        try:
            if bounds:
                capture_res = screen_capture_service.capture_region(bounds)
                img = capture_res.get("image")
                w, h = img.size if img else (bounds[2] - bounds[0], bounds[3] - bounds[1])
                region_type = "region"
            else:
                capture_res = screen_capture_service.capture_full_screen()
                img = capture_res.get("image")
                w, h = img.size if img else (1920, 1080)
                region_type = "full_screen"

            # Compute lightweight perceptual hash to detect screen transitions
            screen_hash = "mock_hash"
            if img:
                try:
                    # Sample downscaled pixel bytes for instant hash
                    thumb = img.resize((32, 32))
                    screen_hash = hashlib.sha256(thumb.tobytes()).hexdigest()[:16]
                except Exception:
                    screen_hash = f"hash_{int(time.time())}"

            has_changed = (self._last_screen_hash is not None and self._last_screen_hash != screen_hash)
            self._last_screen_hash = screen_hash
            self._last_capture_time = time.time()
            elapsed_ms = (time.perf_counter() - t0) * 1000

            content = {
                "display_id": "main",
                "region_type": region_type,
                "width": w,
                "height": h,
                "bounds": list(bounds) if bounds else [0, 0, w, h],
                "screen_hash": screen_hash,
                "has_transitioned": has_changed,
                "capture_latency_ms": round(elapsed_ms, 2),
            }

            return create_observation(
                observation_type=ObservationType.SCREEN,
                source="screen_observer",
                content=content,
                confidence=0.98 if capture_res.get("success") else 0.50,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=15.0,
                correlation_id=correlation_id,
                is_verified=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return create_observation(
                observation_type=ObservationType.SCREEN,
                source="screen_observer",
                content={
                    "error": str(e),
                    "status": "CAPTURE_FAILED",
                    "capture_latency_ms": round(elapsed_ms, 2),
                },
                confidence=0.0,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=5.0,
                correlation_id=correlation_id,
                is_verified=False,
            )


# Global singleton instance
screen_observer = ScreenObserver()
