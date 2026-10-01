"""
Unit tests for Phase 8 — Advanced Computer Use & UI Grounding (core/ui_grounding.py & actions/ui_control.py).
All tests use mocks to avoid triggering real screen clicks or operating system keyboard actions.
"""

import unittest
from unittest.mock import MagicMock, patch
from PIL import Image

from actions.ui_control import (
    click_element,
    double_click_element,
    hotkey,
    press_key,
    type_text,
)
from core.agent_orchestrator import (
    AgentOrchestrator,
    Plan,
    PlanStep,
    ToolRegistry,
)
from core.ui_grounding import GroundingResult, UIGrounding


class MockPlayer:
    def __init__(self):
        self.logs = []

    def write_log(self, text: str):
        self.logs.append(text)


class TestPhase8UIGrounding(unittest.TestCase):
    def setUp(self):
        self.player = MockPlayer()
        self.grounding = UIGrounding()

    # 1. UI element grounding detection & bounding box calculation
    @patch("google.genai.Client")
    @patch("actions.web_search._get_api_key", return_value="fake_api_key")
    def test_find_ui_element_success(self, mock_key, mock_genai_client):
        mock_response = MagicMock()
        mock_response.text = '{"found": true, "element": "Login button", "box_2d": [500, 400, 550, 600], "confidence": 0.95}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client

        mock_img = Image.new("RGB", (1000, 1000))
        res = self.grounding.find_ui_element("Login button", image=mock_img)
        self.assertTrue(res.found)
        self.assertEqual(res.element, "Login button")
        self.assertEqual(res.confidence, 0.95)
        # Bounding box center: xmin=400, xmax=600 -> x=500; ymin=500, ymax=550 -> y=525
        self.assertEqual(res.x, 500)
        self.assertEqual(res.y, 525)

    # 2. Confidence threshold enforcement (< 0.85 rejected)
    @patch("google.genai.Client")
    @patch("actions.web_search._get_api_key", return_value="fake_api_key")
    def test_confidence_threshold_rejection(self, mock_key, mock_genai_client):
        mock_response = MagicMock()
        # Confidence 0.65 < 0.85 threshold
        mock_response.text = '{"found": true, "element": "Login button", "box_2d": [500, 400, 550, 600], "confidence": 0.65}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client

        mock_img = Image.new("RGB", (1000, 1000))
        res = self.grounding.find_ui_element("Login button", image=mock_img)
        self.assertFalse(res.found)
        self.assertIn("couldn't confidently identify", res.error)

    # 3. Coordinate bounds checking (rejects out-of-screen coordinates)
    @patch("google.genai.Client")
    @patch("actions.web_search._get_api_key", return_value="fake_api_key")
    def test_coordinate_bounds_rejection(self, mock_key, mock_genai_client):
        mock_response = MagicMock()
        # Invalid box outside 0-1000
        mock_response.text = '{"found": true, "element": "Offscreen element", "box_2d": [1500, 1500, 1600, 1600], "confidence": 0.90}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client

        mock_img = Image.new("RGB", (1000, 1000))
        res = self.grounding.find_ui_element("Offscreen element", image=mock_img)
        self.assertFalse(res.found)
        self.assertIn("outside screen bounds", res.error)

    # 4. Safe click execution with grounded element
    @patch("actions.ui_control._perform_click")
    @patch("core.ui_grounding.ui_grounding.find_ui_element")
    def test_click_element(self, mock_find, mock_click):
        mock_find.return_value = GroundingResult(
            found=True,
            element="Submit button",
            x=500,
            y=300,
            confidence=0.92,
        )

        res = click_element({"element": "Submit button"}, player=self.player)
        self.assertTrue(res["success"])
        mock_click.assert_called_once_with(500, 300, double=False)
        self.assertEqual(res["x"], 500)
        self.assertEqual(res["y"], 300)

    # 5. Keyboard typing
    @patch("actions.ui_control._perform_type")
    def test_type_text(self, mock_type):
        res = type_text({"text": "Hello JARVIS"}, player=self.player)
        self.assertTrue(res["success"])
        mock_type.assert_called_once_with("Hello JARVIS")

    # 6. Safe key press & rejection of unwhitelisted keys
    @patch("actions.ui_control._perform_press_key")
    def test_press_key_safe(self, mock_press):
        res = press_key({"key": "ENTER"}, player=self.player)
        self.assertTrue(res["success"])
        mock_press.assert_called_once_with("enter")

    def test_press_key_rejected(self):
        res = press_key({"key": "UNSUPPORTED_MALICIOUS_KEY"}, player=self.player)
        self.assertFalse(res["success"])
        self.assertIn("not in the allowed safe keys whitelist", res["error"])

    # 7. Hotkey combination execution & rejection
    @patch("actions.ui_control._perform_hotkey")
    def test_hotkey_safe(self, mock_hotkey):
        res = hotkey({"keys": ["CMD", "L"]}, player=self.player)
        self.assertTrue(res["success"])
        mock_hotkey.assert_called_once_with(["command", "l"])

    def test_hotkey_rejected(self):
        res = hotkey({"keys": ["CMD", "UNKNOWN_KEY"]}, player=self.player)
        self.assertFalse(res["success"])
        self.assertIn("not in the safe keys whitelist", res["error"])

    # 8. Orchestrator UI tool execution
    @patch("actions.ui_control._perform_press_key")
    def test_orchestrator_ui_tool_execution(self, mock_press):
        registry = ToolRegistry()
        orchestrator = AgentOrchestrator(registry=registry)

        plan = Plan(
            goal="Press enter key",
            steps=[
                PlanStep(
                    id=1,
                    description="Press Enter",
                    tool="press_ui_key",
                    parameters={"key": "enter"},
                ),
            ],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Press enter key", player=self.player)
        self.assertEqual(res["status"], "completed")
        self.assertIn("[AGENT] Result: Success", self.player.logs)


if __name__ == "__main__":
    unittest.main()
