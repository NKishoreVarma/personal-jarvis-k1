"""
Application Controller for MARK XLVIII / JARVIS on macOS.
Provides normalized, structured, injection-safe application lifecycle management:
open, close, focus, list running, and active window detection.
"""

from __future__ import annotations

import difflib
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Set

APP_NAME_REGISTRY: Dict[str, str] = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "whatsapp": "WhatsApp",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "iterm2": "iTerm2",
    "finder": "Finder",
    "spotify": "Spotify",
    "slack": "Slack",
    "safari": "Safari",
    "notes": "Notes",
    "messages": "Messages",
    "calendar": "Calendar",
    "mail": "Mail",
    "settings": "System Settings",
    "system settings": "System Settings",
    "preview": "Preview",
    "calculator": "Calculator",
    "xcode": "Xcode",
    "activity monitor": "Activity Monitor",
}


class ApplicationController:
    """
    Safely controls macOS applications using structured system arguments and AppleScript templates.
    """

    def __init__(self, registry: Optional[Dict[str, str]] = None):
        self.registry: Dict[str, str] = registry or APP_NAME_REGISTRY.copy()

    def normalize_app_name(self, name: str) -> Optional[str]:
        """
        Resolves conversational app names to canonical macOS application bundle names.
        """
        if not name or not name.strip():
            return None

        clean = name.strip().lower()
        clean = re.sub(r"^(the|app|application)\s+", "", clean)
        clean = re.sub(r"\s+(app|application)$", "", clean)

        # 1. Exact canonical registry match
        if clean in self.registry:
            return self.registry[clean]

        # 2. Case-insensitive value match
        for k, canonical in self.registry.items():
            if clean == canonical.lower():
                return canonical

        # 3. Fuzzy match against registry keys
        matches = difflib.get_close_matches(clean, list(self.registry.keys()), n=1, cutoff=0.75)
        if matches:
            return self.registry[matches[0]]

        # If title-cased reasonable candidate name without shell characters
        if re.match(r"^[a-zA-Z0-9\s\.\-_]+$", name.strip()):
            return name.strip()

        return None

    def open_application(self, name: str) -> Dict[str, Any]:
        """
        Opens or launches a macOS application using structured subprocess arguments.
        """
        canonical = self.normalize_app_name(name)
        if not canonical:
            return {
                "success": False,
                "error": f"Unknown application '{name}'. Could not resolve canonical application name.",
            }

        cmd = ["open", "-a", canonical]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            if res.returncode == 0:
                return {
                    "success": True,
                    "app_name": canonical,
                    "message": f"Opened {canonical}.",
                }
            else:
                err = res.stderr.strip() or f"Failed to open application {canonical}"
                return {"success": False, "app_name": canonical, "error": err}
        except subprocess.TimeoutExpired:
            return {"success": False, "app_name": canonical, "error": "Application launch timed out."}
        except Exception as e:
            return {"success": False, "app_name": canonical, "error": str(e)}

    def close_application(self, name: str) -> Dict[str, Any]:
        """
        Quits an application gracefully via AppleScript.
        """
        canonical = self.normalize_app_name(name)
        if not canonical:
            return {"success": False, "error": f"Unknown application '{name}'."}

        # Safe AppleScript template with quoted canonical name
        escaped_name = canonical.replace('"', '\\"')
        script = f'tell application "{escaped_name}" to quit'
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5.0)
            if res.returncode == 0:
                return {"success": True, "app_name": canonical, "message": f"Closed {canonical}."}
            else:
                # Fallback to killall if AppleScript quit fails
                subprocess.run(["killall", canonical], capture_output=True, timeout=2.0)
                return {"success": True, "app_name": canonical, "message": f"Terminated {canonical}."}
        except Exception as e:
            return {"success": False, "app_name": canonical, "error": str(e)}

    def focus_application(self, name: str) -> Dict[str, Any]:
        """
        Brings an application to the foreground.
        """
        canonical = self.normalize_app_name(name)
        if not canonical:
            return {"success": False, "error": f"Unknown application '{name}'."}

        escaped_name = canonical.replace('"', '\\"')
        script = f'tell application "{escaped_name}" to activate'
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5.0)
            if res.returncode == 0:
                return {"success": True, "app_name": canonical, "message": f"Focused {canonical}."}
            return {"success": False, "app_name": canonical, "error": res.stderr.strip()}
        except Exception as e:
            return {"success": False, "app_name": canonical, "error": str(e)}

    def get_active_application(self) -> Optional[str]:
        """
        Returns the name of the currently frontmost application.
        """
        script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return None

    def is_application_running(self, name: str) -> bool:
        """
        Checks if an application process is currently running.
        """
        canonical = self.normalize_app_name(name)
        if not canonical:
            return False

        escaped_name = canonical.replace('"', '\\"')
        script = f'tell application "System Events" to return (exists (processes where name is "{escaped_name}"))'
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and "true" in res.stdout.lower():
                return True
        except Exception:
            pass
        return False


# Global singleton instance
app_controller = ApplicationController()
