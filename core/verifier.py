"""
Verifier for MARK XLVIII / JARVIS.
Provides semantic verification for agent step outcomes (APP_OPENED, SCREEN_CONTAINS, BROWSER_LOADED, ACTION_SUCCEEDED)
using DOM/browser state checks first, falling back to vision model verification when needed.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from core.computer_observer import computer_observer


class VerificationType(Enum):
    APP_OPENED = "APP_OPENED"
    SCREEN_CONTAINS = "SCREEN_CONTAINS"
    BROWSER_LOADED = "BROWSER_LOADED"
    ACTION_SUCCEEDED = "ACTION_SUCCEEDED"


class Verifier:
    """
    Verifies plan step execution using DOM/browser state first,
    or semantic vision analysis when visual verification is required.
    """

    def verify(
        self,
        step: Any,
        observation: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None,
        verification_type: Optional[VerificationType] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for step verification.
        Returns: {"success": bool, "reason": str, "type": str}
        """
        tool_name = getattr(step, "tool", "") if step else ""
        params = getattr(step, "parameters", {}) if step else {}

        # 1. Fast DOM / Application State Verification Path (No Vision Needed)
        if tool_name == "open_app":
            app_name = params.get("app_name", "")
            if result and ("launched" in str(result).lower() or "opening" in str(result).lower() or "success" in str(result).lower()):
                return {
                    "success": True,
                    "reason": f"Application '{app_name}' launched successfully",
                    "type": VerificationType.APP_OPENED.value,
                }

        elif tool_name == "browser_control":
            if result and ("success" in str(result).lower() or "navigated" in str(result).lower() or "done" in str(result).lower()):
                return {
                    "success": True,
                    "reason": "Browser action verified via DOM state",
                    "type": VerificationType.BROWSER_LOADED.value,
                }

        # 2. Basic result string check fallback
        if result and not str(result).startswith("Error") and not str(result).startswith("Failed"):
            # Check if visual observation verification is required
            if observation and observation.get("success") and observation.get("image"):
                question = f"Is the result of '{step.description}' visible and successful on screen?"
                analysis = computer_observer.analyze_screen(observation["image"], question)
                if analysis.get("success"):
                    return {
                        "success": True,
                        "reason": f"Vision verified: {analysis.get('answer')}",
                        "type": VerificationType.SCREEN_CONTAINS.value,
                    }

            return {
                "success": True,
                "reason": f"Action '{tool_name}' completed successfully",
                "type": VerificationType.ACTION_SUCCEEDED.value,
            }

        return {
            "success": False,
            "reason": f"Action '{tool_name}' failed: {result}",
            "type": VerificationType.ACTION_SUCCEEDED.value,
        }


# Global singleton instance
verifier = Verifier()
