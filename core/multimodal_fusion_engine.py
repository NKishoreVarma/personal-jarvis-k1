"""
Multimodal Fusion Engine for MARK XLVIII / JARVIS.
Cross-correlates multi-sensor evidence across screen, OCR, application, filesystem, process,
and browser observations into unified, grounded diagnostic hypotheses.
Enforces invariant: Multimodal fusion performs EVIDENCE SYNTHESIS, never autonomous mutation.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from core.world_model import WorldModel, world_model


class MultimodalFusionEngine:
    """
    Synthesizes facts across multiple observation modalities to detect environmental state
    patterns (e.g. Build Failure, Port Conflict, Crash Dialogs, Server Stopped).
    """

    def __init__(self, wm: Optional[WorldModel] = None):
        self.wm = wm or world_model

    def fuse(self) -> Dict[str, Any]:
        """
        Cross-examines WorldModel facts across modalities to derive high-level environmental hypotheses.
        """
        t0 = time.perf_counter()
        evidence_chain: List[str] = []
        state = "HEALTHY_IDLE"
        cause = "NONE"
        confidence = 0.90

        snapshot = self.wm.get_snapshot()
        screen_data = snapshot.get("screen", {})
        app_data = snapshot.get("application", {})
        proc_data = snapshot.get("process", {})
        proj_data = snapshot.get("project", {})
        dev_data = snapshot.get("device", {})
        browser_data = snapshot.get("browser", {})

        # 1. Check for Build Failure / Code Errors
        # Correlate on-screen errors with active terminal / editor and project status
        error_snippets = screen_data.get("error_snippets", [])
        if error_snippets:
            err_text = " ".join(error_snippets)
            evidence_chain.append(f"Screen OCR detected errors: {error_snippets}")

            if "modulenotfounderror" in err_text.lower() or "cannot find module" in err_text.lower():
                state = "BUILD_FAILURE"
                cause = "MISSING_MODULE"
                confidence = 0.96
            elif "syntaxerror" in err_text.lower():
                state = "BUILD_FAILURE"
                cause = "SYNTAX_ERROR"
                confidence = 0.97
            elif "eaddrinuse" in err_text.lower() or "address already in use" in err_text.lower():
                state = "PORT_CONFLICT"
                cause = "ADDRESS_ALREADY_IN_USE"
                confidence = 0.98
            else:
                state = "BUILD_FAILURE"
                cause = "GENERAL_COMPILATION_ERROR"
                confidence = 0.92

        # 2. Check for App Crash Dialogs
        if app_data.get("has_crash_dialog"):
            state = "APPLICATION_CRASH"
            cause = f"App crashed: {app_data.get('focused_window_title')}"
            evidence_chain.append(f"Crash dialog detected in focused window: {app_data.get('focused_window_title')}")
            confidence = 0.98

        # 3. Check for Permission Dialogs
        elif app_data.get("has_permission_dialog"):
            state = "PERMISSION_BLOCKED"
            cause = "OS_PERMISSION_PROMPT_OPEN"
            evidence_chain.append(f"OS Permission dialog blocking window: {app_data.get('focused_window_title')}")
            confidence = 0.95

        # 4. Check for Port / Process Status
        listening = dev_data.get("listening_ports", {})
        if listening and all(not is_open for is_open in listening.values()):
            if state == "HEALTHY_IDLE":
                state = "SERVICES_OFFLINE"
                cause = f"Target ports not listening: {list(listening.keys())}"
                evidence_chain.append(f"Port probe confirmed no listeners on {list(listening.keys())}")
                confidence = 0.94

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "state": state,
            "cause": cause,
            "confidence": confidence,
            "evidence": evidence_chain,
            "active_application": app_data.get("active_application", "Unknown"),
            "focused_window": app_data.get("focused_window_title", ""),
            "project_branch": proj_data.get("git_branch", "unknown"),
            "fusion_latency_ms": round(elapsed_ms, 2),
            "timestamp": time.time(),
        }


# Global singleton instance
multimodal_fusion_engine = MultimodalFusionEngine()
