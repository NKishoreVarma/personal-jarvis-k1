"""
Desktop Control for MARK XLVIII / JARVIS on macOS.
Provides controlled macOS desktop interactions: opening Finder directories, VS Code workspaces, etc.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def open_folder_in_finder(folder_path: str) -> Dict[str, Any]:
    """Opens a folder in macOS Finder."""
    path = Path(folder_path).resolve()
    if not path.exists():
        return {"success": False, "error": f"Path '{folder_path}' does not exist."}

    try:
        subprocess.run(["open", str(path)], check=True, timeout=5.0)
        return {"success": True, "message": f"Opened '{path.name}' in Finder."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def open_in_vscode(folder_path: str) -> Dict[str, Any]:
    """Opens a project folder in Visual Studio Code."""
    path = Path(folder_path).resolve()
    if not path.exists():
        return {"success": False, "error": f"Path '{folder_path}' does not exist."}

    try:
        subprocess.run(["code", str(path)], check=True, timeout=5.0)
        return {"success": True, "message": f"Opened '{path.name}' in VS Code."}
    except Exception as e:
        return {"success": False, "error": str(e)}
