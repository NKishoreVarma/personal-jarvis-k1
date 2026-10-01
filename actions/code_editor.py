"""
Code Editor Tool Layer for MARK XLVIII / JARVIS.
Exposes controlled patch proposal, unified diff preview, confirmed patch application,
and rollback actions.
"""

from __future__ import annotations

from typing import Any, Dict
from core.patch_manager import patch_manager


def propose_patch(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Proposes a structured code patch, returning unified diff preview without applying changes.
    Parameters: {"file": str, "old_text": str, "new_text": str, "reason": str}
    """
    file_path = parameters.get("file", "")
    old_text = parameters.get("old_text", "")
    new_text = parameters.get("new_text", "")
    reason = parameters.get("reason", "Code update")

    preview = patch_manager.preview_patch(
        file_path=file_path,
        old_text=old_text,
        new_text=new_text,
        reason=reason,
    )

    if preview.get("success") and player and hasattr(player, "write_log"):
        player.write_log(f"[CODE PATCH PROPOSAL] File: {file_path}\n{preview.get('diff')}")

    return preview


def apply_patch(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Applies a confirmed code patch after validation and automatic snapshot creation.
    Parameters: {"file": str, "old_text": str, "new_text": str, "reason": str, "confirmed": bool}
    """
    confirmed = parameters.get("confirmed", True)
    if not confirmed:
        return {"success": False, "error": "User confirmation required before applying patch."}

    file_path = parameters.get("file", "")
    old_text = parameters.get("old_text", "")
    new_text = parameters.get("new_text", "")
    reason = parameters.get("reason", "Code update")

    res = patch_manager.apply_patch(
        file_path=file_path,
        old_text=old_text,
        new_text=new_text,
        reason=reason,
    )

    if res.get("success") and player and hasattr(player, "write_log"):
        player.write_log(f"[CODE PATCH APPLIED] File: {file_path} (Reason: {reason})")

    return res


def rollback_patch(parameters: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
    """
    Reverts the last patch applied to a file.
    Parameters: {"file": str}
    """
    file_path = parameters.get("file", "")
    res = patch_manager.rollback(file_path=file_path)

    if res.get("success") and player and hasattr(player, "write_log"):
        player.write_log(f"[CODE PATCH ROLLBACK] Restored: {file_path}")

    return res
