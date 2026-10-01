"""
Window Control Actions for MARK XLVIII / JARVIS on macOS.
Exposes tools for focusing, listing, and switching application windows.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from core.window_manager import window_manager


def focus_window_action(app_name: str, title_query: Optional[str] = None) -> Dict[str, Any]:
    """Focuses a specific window matching a title query."""
    return window_manager.focus_window(app_name, title_query=title_query)


def list_windows_action(app_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists visible application windows."""
    return window_manager.list_windows(app_name=app_name)


def close_window_action(app_name: str, window_index: int = 1) -> Dict[str, Any]:
    """Closes a specific window."""
    return window_manager.close_window(app_name=app_name, window_index=window_index)
