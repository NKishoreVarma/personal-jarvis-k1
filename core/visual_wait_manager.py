"""
Visual Wait Manager for MARK XLVIII / JARVIS.
Provides non-blocking, event-driven async condition waiting for visual screen changes
(text appearance, dialog resolution, loading completion) with strict timeout enforcement
and cancellation support.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional


class VisualWaitCondition(str, Enum):
    TEXT_APPEARS = "TEXT_APPEARS"
    TEXT_DISAPPEARS = "TEXT_DISAPPEARS"
    DIALOG_APPEARS = "DIALOG_APPEARS"
    DIALOG_DISAPPEARS = "DIALOG_DISAPPEARS"
    ELEMENT_APPEARS = "ELEMENT_APPEARS"
    ELEMENT_DISAPPEARS = "ELEMENT_DISAPPEARS"
    SCREEN_CHANGED = "SCREEN_CHANGED"
    WINDOW_CHANGED = "WINDOW_CHANGED"
    LOADING_FINISHED = "LOADING_FINISHED"


class VisualWaitManager:
    """
    Coordinates asynchronous polling and condition checking for visual UI states.
    """

    async def wait_for_condition(
        self,
        condition: VisualWaitCondition,
        target_value: str = "",
        poll_fn: Optional[Callable[[], Dict[str, Any]]] = None,
        timeout_seconds: float = 5.0,
        poll_interval: float = 0.05,
        cancellation_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Polls periodically until condition is satisfied or timeout expires.
        """
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout_seconds:
            if cancellation_check and cancellation_check():
                return {
                    "success": False,
                    "condition": condition.value,
                    "target": target_value,
                    "status": "cancelled",
                    "elapsed_seconds": time.monotonic() - start_time,
                }

            if poll_fn:
                state = poll_fn()
                elements = state.get("elements", [])
                text_blocks = state.get("text_blocks", [])

                # Evaluate condition
                satisfied = False

                if condition == VisualWaitCondition.TEXT_APPEARS:
                    matched = any(target_value.lower() in b.get("text", "").lower() for b in text_blocks)
                    if not matched:
                        matched = any(target_value.lower() in getattr(e, "label", "").lower() for e in elements)
                    satisfied = matched

                elif condition == VisualWaitCondition.TEXT_DISAPPEARS:
                    matched = any(target_value.lower() in b.get("text", "").lower() for b in text_blocks)
                    satisfied = not matched

                elif condition == VisualWaitCondition.DIALOG_APPEARS:
                    satisfied = any(getattr(e, "element_type", "").value == "DIALOG" or "dialog" in getattr(e, "label", "").lower() for e in elements)

                elif condition == VisualWaitCondition.LOADING_FINISHED:
                    loading_active = any(getattr(e, "element_type", "").value == "LOADING_INDICATOR" or "loading" in getattr(e, "label", "").lower() for e in elements)
                    satisfied = not loading_active

                elif condition == VisualWaitCondition.SCREEN_CHANGED:
                    satisfied = state.get("has_changed", True)

                if satisfied:
                    return {
                        "success": True,
                        "condition": condition.value,
                        "target": target_value,
                        "status": "satisfied",
                        "elapsed_seconds": time.monotonic() - start_time,
                    }

            await asyncio.sleep(poll_interval)

        return {
            "success": False,
            "condition": condition.value,
            "target": target_value,
            "status": "timeout",
            "elapsed_seconds": time.monotonic() - start_time,
        }


# Global singleton instance
visual_wait_manager = VisualWaitManager()
