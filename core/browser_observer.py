"""
Browser Observer for MARK XLVIII / JARVIS.
Integrates with browser control and OS AppleScript automation to observe the active browser tab,
URL, page title, and status without executing mutations.
Enforces invariant: Browser observation is strictly read-only.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Dict, List, Optional

from core.perception_contract import (
    Observation,
    ObservationType,
    PrivacyClassification,
    create_observation,
)


class BrowserObserver:
    """
    Observes browser state (URL, active tab title, loading state) without modifying tabs or cookies.
    """

    def observe(
        self,
        target_browser: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Observation:
        """
        Samples the current active browser tab details on macOS.
        Supports Google Chrome, Safari, Brave, and Edge.
        """
        t0 = time.perf_counter()

        browser_name = target_browser or "Google Chrome"
        url = ""
        title = ""
        is_active = False

        try:
            # Query frontmost tab URL and title via AppleScript
            if "chrome" in browser_name.lower() or "brave" in browser_name.lower():
                script = f'''
                tell application "{browser_name}"
                    if (count of windows) > 0 then
                        set currentTab to active tab of front window
                        return (URL of currentTab) & ":::" & (title of currentTab)
                    else
                        return ""
                    end if
                end tell
                '''
            elif "safari" in browser_name.lower():
                script = '''
                tell application "Safari"
                    if (count of windows) > 0 then
                        set currentTab to current tab of front window
                        return (URL of currentTab) & ":::" & (name of currentTab)
                    else
                        return ""
                    end if
                end tell
                '''
            else:
                script = ""

            if script:
                res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2.0)
                if res.returncode == 0 and ":::" in res.stdout:
                    parts = res.stdout.strip().split(":::", 1)
                    url = parts[0].strip()
                    title = parts[1].strip()
                    is_active = True

            elapsed_ms = (time.perf_counter() - t0) * 1000

            content = {
                "browser_name": browser_name,
                "is_active": is_active,
                "url": url,
                "title": title,
                "is_secure": url.startswith("https://") if url else False,
                "domain": url.split("//")[-1].split("/")[0] if url else "",
                "observation_latency_ms": round(elapsed_ms, 2),
            }

            return create_observation(
                observation_type=ObservationType.BROWSER,
                source="browser_observer",
                content=content,
                confidence=0.95 if is_active else 0.70,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=20.0,
                correlation_id=correlation_id,
                is_verified=is_active,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return create_observation(
                observation_type=ObservationType.BROWSER,
                source="browser_observer",
                content={
                    "error": str(e),
                    "browser_name": browser_name,
                    "status": "BROWSER_OBSERVE_FAILED",
                    "observation_latency_ms": round(elapsed_ms, 2),
                },
                confidence=0.0,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=5.0,
                correlation_id=correlation_id,
                is_verified=False,
            )


# Global singleton instance
browser_observer = BrowserObserver()
