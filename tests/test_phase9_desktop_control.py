"""
Phase 9 Application & UI Control Integration Test Suite.
Tests high-level application lifecycle, window management, fast voice acknowledgement,
and WhatsApp chat interaction workflows.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from actions.app_control import open_whatsapp_chat
from core.application_controller import app_controller
from core.intent_router import router


class TestPhase9DesktopControl(unittest.TestCase):
    def test_01_voice_acknowledgement_for_apps(self):
        t0 = time.monotonic()
        res = router.route_and_execute("open WhatsApp")
        dt_ms = (time.monotonic() - t0) * 1000.0

        self.assertTrue(res["handled"])
        self.assertEqual(res["intent"], "OPEN_APP")
        self.assertIn("whatsapp", res["response"].lower())
        self.assertLess(dt_ms, 50.0)

    @patch("actions.app_control.app_controller")
    @patch("actions.app_control.ui_locator")
    @patch("actions.app_control.computer_action_executor")
    def test_02_open_whatsapp_chat_success(self, mock_exec, mock_locator, mock_ctrl):
        mock_ctrl.open_application.return_value = {"success": True}
        mock_locator.locate_element.return_value = {
            "found": True,
            "element": {"role": "AXStaticText", "title": "John"},
        }
        mock_exec.execute_action.return_value = {"success": True}

        res = open_whatsapp_chat("John")
        self.assertTrue(res["success"])
        self.assertEqual(res["app"], "WhatsApp")
        self.assertEqual(res["contact"], "John")

    @patch("actions.app_control.app_controller")
    @patch("actions.app_control.ui_locator")
    def test_03_open_whatsapp_chat_ambiguous_contact(self, mock_locator, mock_ctrl):
        mock_ctrl.open_application.return_value = {"success": True}
        mock_locator.locate_element.return_value = {
            "found": False,
            "ambiguous": True,
            "candidates": ["John Doe", "John Smith"],
        }

        res = open_whatsapp_chat("John")
        self.assertFalse(res["success"])
        self.assertTrue(res["ambiguous"])
        self.assertEqual(len(res["candidates"]), 2)
        self.assertIn("Which one would you like to open?", res["message"])


if __name__ == "__main__":
    unittest.main()
