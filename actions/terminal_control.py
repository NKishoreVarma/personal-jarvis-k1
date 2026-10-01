"""
Terminal Control for MARK XLVIII / JARVIS on macOS.
Supports programmatic non-blocking process execution (preferred) and optional visible Terminal window spawning.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def open_terminal_window(cwd: str, command: Optional[str] = None) -> Dict[str, Any]:
    """
    Opens a visible macOS Terminal window in `cwd` and optionally runs `command`.
    Used only when visible terminal output is explicitly requested by the user.
    """
    path = Path(cwd).resolve()
    if not path.exists():
        return {"success": False, "error": f"Path '{cwd}' does not exist."}

    cmd_str = f"cd {path}"
    if command:
        cmd_str += f" && {command}"

    applescript = f'''
    tell application "Terminal"
        activate
        do script "{cmd_str}"
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", applescript], check=True, capture_output=True, timeout=5.0)
        return {"success": True, "message": f"Opened Terminal in {cwd}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
