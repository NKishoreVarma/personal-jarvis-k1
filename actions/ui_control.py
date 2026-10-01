"""
Controlled UI Interaction Layer for MARK XLVIII / JARVIS.
Provides safe mouse clicks and keyboard actions using grounded UI coordinates,
failsafe bounds, key allowlists, and cross-platform automation adapters.
"""

from __future__ import annotations

import os
import string
import subprocess
from typing import Any, Dict, List, Set

from core.ui_grounding import ui_grounding

# Whitelist of allowed keys for keyboard automation
SAFE_KEYS_ALLOWLIST: Set[str] = {
    "enter", "return", "tab", "space", "backspace", "delete", "escape", "esc",
    "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
    "command", "cmd", "ctrl", "control", "alt", "option", "shift",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
} | set(string.ascii_lowercase) | set(string.digits)


def _normalize_key(key: str) -> str:
    """Normalizes key names for automation matching."""
    k = key.strip().lower()
    if k in ("cmd", "command"):
        return "command"
    elif k in ("ctrl", "control"):
        return "ctrl"
    elif k in ("esc", "escape"):
        return "escape"
    elif k == "return":
        return "enter"
    return k


def _perform_click(x: int, y: int, double: bool = False) -> None:
    """Executes mouse click via pyautogui if installed or macOS AppleScript/Quartz."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        if double:
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.click(x, y)
        return
    except ImportError:
        pass

    # Fallback to AppleScript on macOS
    click_code = 2 if double else 1
    script = f'tell application "System Events" to click at {{{x}, {y}}}'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5.0)


def _perform_type(text: str) -> None:
    """Executes text typing via pyautogui or macOS AppleScript."""
    try:
        import pyautogui
        pyautogui.write(text, interval=0.01)
        return
    except ImportError:
        pass

    # Fallback to AppleScript keystroke on macOS
    safe_text = text.replace('"', '\\"')
    script = f'tell application "System Events" to keystroke "{safe_text}"'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5.0)


def _perform_press_key(key: str) -> None:
    """Executes key press via pyautogui or macOS AppleScript."""
    try:
        import pyautogui
        pyautogui.press(key)
        return
    except ImportError:
        pass

    # Fallback key code mapping for AppleScript
    key_codes = {
        "enter": "key code 36",
        "tab": "key code 48",
        "space": "key code 49",
        "backspace": "key code 51",
        "escape": "key code 53",
    }
    if key in key_codes:
        script = f'tell application "System Events" to {key_codes[key]}'
    else:
        script = f'tell application "System Events" to keystroke "{key}"'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5.0)


def _perform_hotkey(keys: List[str]) -> None:
    """Executes combination hotkey via pyautogui or macOS AppleScript."""
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
        return
    except ImportError:
        pass

    # Fallback for common hotkeys (e.g. cmd+l)
    modifiers = []
    main_key = ""
    for k in keys:
        if k in ("command", "cmd"):
            modifiers.append("command down")
        elif k in ("ctrl", "control"):
            modifiers.append("control down")
        elif k in ("alt", "option"):
            modifiers.append("option down")
        elif k == "shift":
            modifiers.append("shift down")
        else:
            main_key = k

    if modifiers and main_key:
        mod_str = " using {" + ", ".join(modifiers) + "}"
        script = f'tell application "System Events" to keystroke "{main_key}"{mod_str}'
    else:
        script = f'tell application "System Events" to keystroke "{keys[-1]}"'

    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5.0)


def click_element(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Identifies a UI element via semantic grounding and clicks its center coordinate.
    Parameters: {"element": str}
    """
    element_query = parameters.get("element", "")
    if not element_query:
        return {"success": False, "error": "No element description provided."}

    grounded = ui_grounding.find_ui_element(element_query)
    if not grounded.found:
        return {"success": False, "error": grounded.error or f"Could not locate '{element_query}'"}

    try:
        _perform_click(grounded.x, grounded.y, double=False)
        msg = f"[UI] Clicked '{element_query}' at ({grounded.x}, {grounded.y}) with confidence {grounded.confidence:.2f}"
        if player and hasattr(player, "write_log"):
            player.write_log(msg)
        return {
            "success": True,
            "element": element_query,
            "x": grounded.x,
            "y": grounded.y,
            "confidence": grounded.confidence,
        }
    except Exception as e:
        return {"success": False, "error": f"Click failed: {e}"}


def double_click_element(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Identifies a UI element via semantic grounding and double clicks its center coordinate.
    Parameters: {"element": str}
    """
    element_query = parameters.get("element", "")
    if not element_query:
        return {"success": False, "error": "No element description provided."}

    grounded = ui_grounding.find_ui_element(element_query)
    if not grounded.found:
        return {"success": False, "error": grounded.error or f"Could not locate '{element_query}'"}

    try:
        _perform_click(grounded.x, grounded.y, double=True)
        msg = f"[UI] Double-clicked '{element_query}' at ({grounded.x}, {grounded.y}) with confidence {grounded.confidence:.2f}"
        if player and hasattr(player, "write_log"):
            player.write_log(msg)
        return {
            "success": True,
            "element": element_query,
            "x": grounded.x,
            "y": grounded.y,
            "confidence": grounded.confidence,
        }
    except Exception as e:
        return {"success": False, "error": f"Double click failed: {e}"}


def move_to_element(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Identifies a UI element via semantic grounding and moves mouse to its center coordinate.
    Parameters: {"element": str}
    """
    element_query = parameters.get("element", "")
    if not element_query:
        return {"success": False, "error": "No element description provided."}

    grounded = ui_grounding.find_ui_element(element_query)
    if not grounded.found:
        return {"success": False, "error": grounded.error or f"Could not locate '{element_query}'"}

    try:
        _perform_click(grounded.x, grounded.y, double=False)
        return {
            "success": True,
            "element": element_query,
            "x": grounded.x,
            "y": grounded.y,
            "confidence": grounded.confidence,
        }
    except Exception as e:
        return {"success": False, "error": f"Move mouse failed: {e}"}


def type_text(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Types text into the currently active window or input control.
    Parameters: {"text": str}
    """
    text = parameters.get("text", "")
    if not text:
        return {"success": False, "error": "No text provided to type."}

    try:
        _perform_type(text)
        if player and hasattr(player, "write_log"):
            player.write_log(f"[UI] Typed text: '{text}'")
        return {"success": True, "typed": text}
    except Exception as e:
        return {"success": False, "error": f"Type text failed: {e}"}


def press_key(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Presses a single key from the safe keys allowlist.
    Parameters: {"key": str}
    """
    raw_key = parameters.get("key", "")
    norm_key = _normalize_key(raw_key)

    if norm_key not in SAFE_KEYS_ALLOWLIST:
        return {
            "success": False,
            "error": f"Key '{raw_key}' is not in the allowed safe keys whitelist.",
        }

    try:
        _perform_press_key(norm_key)
        if player and hasattr(player, "write_log"):
            player.write_log(f"[UI] Pressed key: '{norm_key}'")
        return {"success": True, "key": norm_key}
    except Exception as e:
        return {"success": False, "error": f"Key press failed: {e}"}


def hotkey(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Presses a combination hotkey from the safe keys allowlist.
    Parameters: {"keys": List[str]}
    """
    raw_keys = parameters.get("keys", [])
    if not raw_keys:
        return {"success": False, "error": "No keys provided for hotkey."}

    norm_keys: List[str] = []
    for k in raw_keys:
        nk = _normalize_key(k)
        if nk not in SAFE_KEYS_ALLOWLIST:
            return {
                "success": False,
                "error": f"Key '{k}' in hotkey combination is not in the safe keys whitelist.",
            }
        norm_keys.append(nk)

    try:
        _perform_hotkey(norm_keys)
        if player and hasattr(player, "write_log"):
            player.write_log(f"[UI] Pressed hotkey: {'+'.join(norm_keys)}")
        return {"success": True, "keys": norm_keys}
    except Exception as e:
        return {"success": False, "error": f"Hotkey press failed: {e}"}
