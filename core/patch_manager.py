"""
Core Patch Manager for MARK XLVIII / JARVIS.
Handles safe, atomic code modification with unified diff preview, single-match verification,
secret protection, and automatic backup/rollback capabilities.
"""

from __future__ import annotations

import difflib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from actions.dev_tools import _validate_sandbox_path


class PatchManager:
    """
    Manages structured code patches for projects.
    Enforces sandbox constraints, single-occurrence match validation, and rollback safety.
    """

    def __init__(self):
        # Maps file path string to stack of historical snapshots
        self._backups: Dict[str, List[str]] = {}

    def validate_patch(self, file_path: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """
        Validates patch target, ensuring file exists, is inside workspace,
        and old_text occurs exactly once.
        """
        try:
            resolved = _validate_sandbox_path(file_path)
            if not resolved.exists() or not resolved.is_file():
                return {"valid": False, "error": f"Target file '{file_path}' does not exist or is not a file."}

            if not old_text:
                return {"valid": False, "error": "old_text snippet cannot be empty."}

            # Read existing file content
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            occurrences = content.count(old_text)
            if occurrences == 0:
                return {
                    "valid": False,
                    "error": f"Target snippet was not found in '{resolved.name}'. Patch rejected.",
                }
            elif occurrences > 1:
                return {
                    "valid": False,
                    "error": f"Target snippet is ambiguous ({occurrences} occurrences found in '{resolved.name}'). Patch rejected.",
                }

            return {
                "valid": True,
                "resolved_path": resolved,
                "content": content,
            }
        except PermissionError as pe:
            return {"valid": False, "error": f"Security violation: {pe}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def preview_patch(self, file_path: str, old_text: str, new_text: str, reason: str = "") -> Dict[str, Any]:
        """
        Generates a unified diff preview for the proposed change without modifying the file.
        """
        val = self.validate_patch(file_path, old_text, new_text)
        if not val["valid"]:
            return {"success": False, "error": val["error"]}

        resolved: Path = val["resolved_path"]
        content: str = val["content"]

        new_content = content.replace(old_text, new_text, 1)

        old_lines = content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{resolved.name}",
            tofile=f"b/{resolved.name}",
        ))

        diff_str = "".join(diff_lines)
        return {
            "success": True,
            "file": str(resolved),
            "reason": reason,
            "diff": diff_str or "No changes detected",
        }

    def apply_patch(self, file_path: str, old_text: str, new_text: str, reason: str = "") -> Dict[str, Any]:
        """
        Applies a validated patch, storing an automatic snapshot for rollback.
        """
        val = self.validate_patch(file_path, old_text, new_text)
        if not val["valid"]:
            return {"success": False, "error": val["error"]}

        resolved: Path = val["resolved_path"]
        content: str = val["content"]

        # Record snapshot in backup history
        key = str(resolved)
        if key not in self._backups:
            self._backups[key] = []
        self._backups[key].append(content)

        new_content = content.replace(old_text, new_text, 1)

        try:
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Verification: ensure file can be read back cleanly
            with open(resolved, "r", encoding="utf-8") as f:
                verified_content = f.read()

            if verified_content != new_content:
                # Rollback immediately on write mismatch
                self.rollback(file_path)
                return {"success": False, "error": "Post-write verification failed. Changes reverted."}

            return {
                "success": True,
                "file": str(resolved),
                "reason": reason,
                "timestamp": time.monotonic(),
            }
        except Exception as e:
            # Revert if write failed midway
            self.rollback(file_path)
            return {"success": False, "error": f"Failed to apply patch: {e}"}

    def rollback(self, file_path: str) -> Dict[str, Any]:
        """
        Reverts the last patch applied to a file using the backup history.
        """
        try:
            resolved = _validate_sandbox_path(file_path)
            key = str(resolved)
            if key not in self._backups or not self._backups[key]:
                return {"success": False, "error": f"No backup snapshot found for '{file_path}'."}

            previous_content = self._backups[key].pop()
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(previous_content)

            return {
                "success": True,
                "file": str(resolved),
                "restored": True,
            }
        except Exception as e:
            return {"success": False, "error": f"Rollback failed: {e}"}


# Global singleton instance
patch_manager = PatchManager()
