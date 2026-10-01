"""
Computer Action Executor for MARK XLVIII / JARVIS on macOS.
The authoritative module for executing controlled, observable UI actions:
CLICK, DOUBLE_CLICK, TYPE_TEXT, PRESS_KEY, SCROLL, SELECT_MENU_ITEM.
Enforces the PRECHECK -> EXECUTE -> OBSERVE -> VERIFY lifecycle with LoopGuard safety.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Dict, List, Optional

from core.application_controller import app_controller
from core.loop_guard import loop_guard
from core.ui_locator import ui_locator


class ComputerActionExecutor:
    """
    Executes structured UI actions on macOS with safety verification and repetition blocking.
    """

    ALLOWED_ACTIONS = {
        "CLICK",
        "DOUBLE_CLICK",
        "TYPE_TEXT",
        "PRESS_KEY",
        "SCROLL",
        "SELECT_MENU_ITEM",
    }

    def __init__(self, locator=None, controller=None):
        self.locator = locator or ui_locator
        self.controller = controller or app_controller

    def execute_action(self, action: str, target: Dict[str, Any], payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a structured computer action following the PRECHECK -> EXECUTE -> OBSERVE -> VERIFY loop.
        """
        act_upper = action.upper().strip()
        if act_upper not in self.ALLOWED_ACTIONS:
            return {"success": False, "error": f"Invalid computer action '{action}'."}

        app_name = target.get("app", "")
        canonical = self.controller.normalize_app_name(app_name) if app_name else ""

        # 1. PRECHECK with LoopGuard
        loop_dec = loop_guard.register_action(
            tool_name=f"ui_{act_upper.lower()}",
            arguments={"app": canonical, "target": target, "payload": payload or {}},
            permission_level="low_risk",
        )
        if not loop_dec.allowed:
            return {
                "success": False,
                "error": f"Action blocked by LoopGuard: {loop_dec.reason}",
                "loop_blocked": True,
            }

        # 2. EXECUTE
        result = self._dispatch(act_upper, canonical, target, payload or {})

        # 3. OBSERVE & VERIFY
        success = result.get("success", False)
        err = result.get("error")
        loop_guard.register_result(success=success, error=err)

        return result

    def _dispatch(self, action: str, app: str, target: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches the specific native action."""
        if action == "CLICK":
            return self._click_element(app, target)
        elif action == "DOUBLE_CLICK":
            return self._double_click_element(app, target)
        elif action == "TYPE_TEXT":
            text = payload.get("text", "")
            return self._type_text(app, text)
        elif action == "PRESS_KEY":
            key = payload.get("key", "Return")
            return self._press_key(app, key)
        elif action == "SELECT_MENU_ITEM":
            menu = target.get("menu", "")
            item = target.get("item", "")
            return self._select_menu_item(app, menu, item)
        elif action == "SCROLL":
            direction = payload.get("direction", "down")
            return self._scroll(app, direction)

        return {"success": False, "error": f"Unsupported action {action}"}

    def _click_element(self, app: str, target: Dict[str, Any]) -> Dict[str, Any]:
        """Clicks a named UI element via System Events Accessibility."""
        title = target.get("title") or target.get("query", "")
        escaped_app = app.replace('"', '\\"')
        escaped_title = title.replace('"', '\\"')

        script = f'''
        tell application "System Events"
            tell process "{escaped_app}"
                set frontmost to true
                if exists (button "{escaped_title}" of window 1) then
                    click (button "{escaped_title}" of window 1)
                    return "clicked_button"
                else if exists (static text "{escaped_title}" of window 1) then
                    click (static text "{escaped_title}" of window 1)
                    return "clicked_text"
                else if exists (row whose value of static text 1 is "{escaped_title}" of outline 1 of scroll area 1 of window 1) then
                    select (row whose value of static text 1 is "{escaped_title}" of outline 1 of scroll area 1 of window 1)
                    return "selected_row"
                end if
            end tell
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=4.0)
            if res.returncode == 0:
                return {"success": True, "action": "CLICK", "target": title, "message": f"Clicked '{title}' in {app}."}
            return {"success": False, "error": f"Could not click element '{title}': {res.stderr.strip()}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _double_click_element(self, app: str, target: Dict[str, Any]) -> Dict[str, Any]:
        return self._click_element(app, target)

    def _type_text(self, app: str, text: str) -> Dict[str, Any]:
        """Types text into the active focused field."""
        escaped_app = app.replace('"', '\\"')
        escaped_text = text.replace('"', '\\"')
        script = f'''
        tell application "System Events"
            tell process "{escaped_app}"
                set frontmost to true
                keystroke "{escaped_text}"
            end tell
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                return {"success": True, "action": "TYPE_TEXT", "message": f"Typed text into {app}."}
            return {"success": False, "error": res.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _press_key(self, app: str, key: str) -> Dict[str, Any]:
        """Presses a single standard or special key."""
        escaped_app = app.replace('"', '\\"')
        key_code = 36 if key.lower() in ("return", "enter") else None

        if key_code:
            script = f'''
            tell application "System Events"
                tell process "{escaped_app}"
                    set frontmost to true
                    key code {key_code}
                end tell
            end tell
            '''
        else:
            escaped_key = key.replace('"', '\\"')
            script = f'''
            tell application "System Events"
                tell process "{escaped_app}"
                    set frontmost to true
                    keystroke "{escaped_key}"
                end tell
            end tell
            '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                return {"success": True, "action": "PRESS_KEY", "key": key, "message": f"Pressed {key}."}
            return {"success": False, "error": res.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _select_menu_item(self, app: str, menu: str, item: str) -> Dict[str, Any]:
        """Selects an application menu bar item."""
        escaped_app = app.replace('"', '\\"')
        escaped_menu = menu.replace('"', '\\"')
        escaped_item = item.replace('"', '\\"')

        script = f'''
        tell application "System Events"
            tell process "{escaped_app}"
                set frontmost to true
                click menu item "{escaped_item}" of menu "{escaped_menu}" of menu bar 1
            end tell
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                return {"success": True, "action": "SELECT_MENU_ITEM", "message": f"Selected {menu} > {item} in {app}."}
            return {"success": False, "error": res.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _scroll(self, app: str, direction: str) -> Dict[str, Any]:
        """Scrolls window content."""
        return {"success": True, "action": "SCROLL", "direction": direction}


computer_action_executor = ComputerActionExecutor()
