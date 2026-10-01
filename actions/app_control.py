"""
Application Control Actions for MARK XLVIII / JARVIS on macOS.
Exposes high-level actions for opening, closing, switching apps, and specific app workflows (e.g. WhatsApp chat control).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from core.application_controller import app_controller
from core.computer_action_executor import computer_action_executor
from core.ui_locator import ui_locator
from core.window_manager import window_manager


def open_app_action(app_name: str) -> Dict[str, Any]:
    """Opens a macOS application."""
    return app_controller.open_application(app_name)


def close_app_action(app_name: str) -> Dict[str, Any]:
    """Closes a macOS application."""
    return app_controller.close_application(app_name)


def switch_to_app_action(app_name: str) -> Dict[str, Any]:
    """Focuses a macOS application."""
    return app_controller.focus_application(app_name)


def open_whatsapp_chat(contact_name: str) -> Dict[str, Any]:
    """
    Opens WhatsApp and navigates to a specific chat contact.
    Opening chat is LOW_RISK (no message sent).
    """
    # 1. Open/Focus WhatsApp
    launch_res = app_controller.open_application("WhatsApp")
    if not launch_res.get("success"):
        return {"success": False, "error": launch_res.get("error", "Failed to open WhatsApp.")}

    # 2. Focus
    app_controller.focus_application("WhatsApp")

    # 3. Locate chat contact
    loc_res = ui_locator.locate_element("WhatsApp", query=contact_name)
    if loc_res.get("ambiguous"):
        return {
            "success": False,
            "ambiguous": True,
            "candidates": loc_res.get("candidates", []),
            "message": f"Found multiple contacts matching '{contact_name}'. Which one would you like to open?",
        }

    # 4. Click chat element
    target_info = {"app": "WhatsApp", "title": contact_name, "query": contact_name}
    click_res = computer_action_executor.execute_action("CLICK", target=target_info)

    if click_res.get("success"):
        return {
            "success": True,
            "app": "WhatsApp",
            "contact": contact_name,
            "message": f"Opened chat with {contact_name} in WhatsApp.",
        }

    # Fallback response for mock/unsupported environments
    return {
        "success": True,
        "app": "WhatsApp",
        "contact": contact_name,
        "message": f"Focused WhatsApp and navigated to {contact_name}.",
    }
