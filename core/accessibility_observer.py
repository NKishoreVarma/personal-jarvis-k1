"""
Accessibility Observer for MARK XLVIII / JARVIS on macOS.
Inspects native macOS Accessibility elements (AXButtons, AXTextFields, AXRows, AXMenuItems)
without dumping giant unfiltered trees.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional

from core.application_controller import app_controller


class AccessibilityObserver:
    """
    Observes and inspects macOS UI Accessibility tree elements.
    """

    def __init__(self, controller=None):
        self.controller = controller or app_controller

    def get_active_app(self) -> Optional[str]:
        """Returns the currently active frontmost application."""
        return self.controller.get_active_application()

    def get_focused_window(self, app_name: Optional[str] = None) -> Dict[str, Any]:
        """Returns metadata for the frontmost/focused window of an app."""
        canonical = self.controller.normalize_app_name(app_name) if app_name else self.get_active_app()
        if not canonical:
            return {"found": False, "error": "No active application."}

        escaped = canonical.replace('"', '\\"')
        script = f'''
        tell application "System Events"
            if exists (process "{escaped}") then
                tell process "{escaped}"
                    if exists (window 1) then
                        set wTitle to name of window 1
                        set wPos to position of window 1
                        set wSize to size of window 1
                        return wTitle & ":::" & (item 1 of wPos) & "," & (item 2 of wPos) & ":::" & (item 1 of wSize) & "," & (item 2 of wSize)
                    end if
                end tell
            end if
            return ""
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split(":::")
                if len(parts) >= 3:
                    title = parts[0]
                    pos = [int(p) for p in parts[1].split(",") if p.isdigit()]
                    size = [int(s) for s in parts[2].split(",") if s.isdigit()]
                    return {
                        "found": True,
                        "app": canonical,
                        "title": title,
                        "position": pos,
                        "size": size,
                    }
        except Exception:
            pass

        return {"found": False, "app": canonical}

    def get_ui_elements(self, app_name: Optional[str] = None, max_elements: int = 30) -> List[Dict[str, Any]]:
        """
        Extracts high-level interactive UI elements (buttons, text fields, lists, rows) for an application.
        """
        canonical = self.controller.normalize_app_name(app_name) if app_name else self.get_active_app()
        if not canonical:
            return []

        escaped = canonical.replace('"', '\\"')
        # Query primary interactive elements: buttons, text fields, static texts
        script = f'''
        tell application "System Events"
            if exists (process "{escaped}") then
                tell process "{escaped}"
                    set outList to {{}}
                    if exists (window 1) then
                        tell window 1
                            -- Buttons
                            repeat with b in (every button)
                                set bName to name of b
                                if bName is not missing value and bName is not "" then
                                    set end of outList to "AXButton:::" & bName & ":::" & (enabled of b)
                                end if
                            end repeat
                            -- Text fields
                            repeat with tf in (every text field)
                                set tfName to name of tf
                                if tfName is not missing value and tfName is not "" then
                                    set end of outList to "AXTextField:::" & tfName & ":::" & (enabled of tf)
                                end if
                            end repeat
                            -- Static text labels
                            repeat with st in (every static text)
                                set stVal to value of st
                                if stVal is not missing value and stVal is not "" then
                                    set end of outList to "AXStaticText:::" & stVal & ":::true"
                                end if
                            end repeat
                        end tell
                    end if
                    return outList
                end tell
            end if
            return {{}}
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=4.0)
            if res.returncode != 0 or not res.stdout.strip():
                return []

            items = [it.strip() for it in res.stdout.strip().split(",") if it.strip()]
            elements: List[Dict[str, Any]] = []

            for it in items[:max_elements]:
                if ":::" in it:
                    parts = it.split(":::")
                    role = parts[0] if len(parts) > 0 else "AXElement"
                    title = parts[1] if len(parts) > 1 else ""
                    enabled = (parts[2].lower() == "true") if len(parts) > 2 else True

                    elements.append({
                        "role": role,
                        "title": title,
                        "label": title,
                        "enabled": enabled,
                        "visible": True,
                        "app": canonical,
                    })

            return elements
        except Exception:
            return []

    def find_elements(
        self,
        app_name: str,
        role: Optional[str] = None,
        title: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Searches for elements matching criteria."""
        elements = self.get_ui_elements(app_name=app_name)
        results: List[Dict[str, Any]] = []

        q = (query or title or "").lower().strip()

        for el in elements:
            if role and el.get("role", "").lower() != role.lower():
                continue
            if q:
                el_title = el.get("title", "").lower()
                el_label = el.get("label", "").lower()
                if q in el_title or q in el_label:
                    results.append(el)
            else:
                results.append(el)

        return results


accessibility_observer = AccessibilityObserver()
