"""
Window Manager for MARK XLVIII / JARVIS on macOS.
Provides deterministic window management: list windows, focus by title/app,
minimize, maximize, close, and switch window.
"""

from __future__ import annotations

import difflib
import subprocess
from typing import Any, Dict, List, Optional

from core.application_controller import app_controller


class WindowManager:
    """
    Manages application windows on macOS via System Events and Accessibility hooks.
    """

    def __init__(self, controller=None):
        self.controller = controller or app_controller

    def list_windows(self, app_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists all visible windows for a given application or across all running applications.
        """
        if app_name:
            canonical = self.controller.normalize_app_name(app_name) or app_name
            escaped = canonical.replace('"', '\\"')
            script = f'''
            tell application "System Events"
                if exists (process "{escaped}") then
                    tell process "{escaped}"
                        set winList to name of every window
                        return winList
                    end tell
                else
                    return ""
                end if
            end tell
            '''
        else:
            script = '''
            tell application "System Events"
                set output to {}
                repeat with p in (every process where background only is false)
                    set pName to name of p
                    repeat with w in (every window of p)
                        set wName to name of w
                        set end of output to pName & ":::" & wName
                    end repeat
                end repeat
                return output
            end tell
            '''

        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=4.0)
            if res.returncode != 0 or not res.stdout.strip():
                return []

            raw = res.stdout.strip()
            windows: List[Dict[str, Any]] = []

            if app_name:
                # Comma separated window titles
                titles = [t.strip() for t in raw.split(",") if t.strip()]
                for idx, t in enumerate(titles, 1):
                    windows.append({"app": canonical, "title": t, "index": idx})
            else:
                items = [it.strip() for it in raw.split(",") if it.strip()]
                for it in items:
                    if ":::" in it:
                        p_name, w_title = it.split(":::", 1)
                        windows.append({"app": p_name.strip(), "title": w_title.strip()})

            return windows
        except Exception:
            return []

    def focus_window(self, app_name: str, title_query: Optional[str] = None) -> Dict[str, Any]:
        """
        Focuses the window of `app_name` that best matches `title_query`.
        """
        canonical = self.controller.normalize_app_name(app_name) or app_name
        self.controller.focus_application(canonical)

        if not title_query:
            return {"success": True, "app": canonical, "message": f"Focused {canonical}."}

        windows = self.list_windows(canonical)
        if not windows:
            return {"success": True, "app": canonical, "message": f"Focused {canonical} (no windows found to filter)."}

        # Match title query
        q_lower = title_query.lower().strip()
        matched = None
        for w in windows:
            if q_lower in w["title"].lower():
                matched = w
                break

        if not matched:
            # Fuzzy match
            titles = [w["title"] for w in windows]
            close = difflib.get_close_matches(title_query, titles, n=1, cutoff=0.6)
            if close:
                matched = next((w for w in windows if w["title"] == close[0]), None)

        if matched:
            escaped_app = canonical.replace('"', '\\"')
            escaped_title = matched["title"].replace('"', '\\"')
            script = f'''
            tell application "System Events"
                tell process "{escaped_app}"
                    set frontmost to true
                    perform action "AXRaise" of (first window whose name is "{escaped_title}")
                end tell
            end tell
            '''
            try:
                subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3.0)
            except Exception:
                pass

            return {
                "success": True,
                "app": canonical,
                "window": matched["title"],
                "message": f"Focused '{matched['title']}' in {canonical}.",
            }

        return {
            "success": True,
            "app": canonical,
            "message": f"Focused {canonical}, but specific window matching '{title_query}' was not found.",
        }

    def close_window(self, app_name: str, window_index: int = 1) -> Dict[str, Any]:
        """Closes a specific window of an application."""
        canonical = self.controller.normalize_app_name(app_name) or app_name
        escaped_app = canonical.replace('"', '\\"')
        script = f'''
        tell application "System Events"
            tell process "{escaped_app}"
                click (button 1 of window {window_index})
            end tell
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                return {"success": True, "message": f"Closed window {window_index} of {canonical}."}
            return {"success": False, "error": res.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}


window_manager = WindowManager()
