"""
Application Observer for MARK XLVIII / JARVIS.
Integrates with ApplicationController and WindowManager to observe active and running applications,
focused windows, application transitions, and system permission dialogs without requiring elevated privileges.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.application_controller import app_controller
from core.perception_contract import (
    Observation,
    ObservationType,
    PrivacyClassification,
    create_observation,
)
from core.window_manager import WindowManager


class ApplicationObserver:
    """
    Observes frontmost and background applications, open windows, and transitions.
    """

    def __init__(self, window_mgr: Optional[WindowManager] = None):
        self.window_mgr = window_mgr or WindowManager()
        self._last_active_app: Optional[str] = None
        self._last_active_window: Optional[str] = None

    def observe(
        self,
        app_name_filter: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Observation:
        """
        Samples the current application environment and builds an Observation record.
        """
        t0 = time.perf_counter()

        try:
            # 1. Frontmost application
            active_app = app_controller.get_active_application() or "Unknown"

            # 2. Window list
            windows = self.window_mgr.list_windows(app_name_filter)
            focused_window = windows[0].get("title", "") if windows else ""

            # 3. Detect transitions
            app_transitioned = (self._last_active_app is not None and self._last_active_app != active_app)
            win_transitioned = (self._last_active_window is not None and self._last_active_window != focused_window)

            self._last_active_app = active_app
            self._last_active_window = focused_window

            # 4. Check for common dialogs (permission dialogs, crash alerts)
            has_permission_dialog = any(
                "permission" in str(w.get("title", "")).lower() or "wants access" in str(w.get("title", "")).lower()
                for w in windows
            )
            has_crash_dialog = any(
                "quit unexpectedly" in str(w.get("title", "")).lower() or "problem report" in str(w.get("title", "")).lower()
                for w in windows
            )

            elapsed_ms = (time.perf_counter() - t0) * 1000

            content = {
                "active_application": active_app,
                "focused_window_title": focused_window,
                "open_window_count": len(windows),
                "windows": windows[:10],  # Bounded to top 10 windows
                "app_transitioned": app_transitioned,
                "window_transitioned": win_transitioned,
                "has_permission_dialog": has_permission_dialog,
                "has_crash_dialog": has_crash_dialog,
                "sampling_latency_ms": round(elapsed_ms, 2),
            }

            return create_observation(
                observation_type=ObservationType.APPLICATION,
                source="application_observer",
                content=content,
                confidence=0.96,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=30.0,
                correlation_id=correlation_id,
                is_verified=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return create_observation(
                observation_type=ObservationType.APPLICATION,
                source="application_observer",
                content={
                    "error": str(e),
                    "status": "SAMPLING_FAILED",
                    "sampling_latency_ms": round(elapsed_ms, 2),
                },
                confidence=0.0,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=5.0,
                correlation_id=correlation_id,
                is_verified=False,
            )


# Global singleton instance
application_observer = ApplicationObserver()
