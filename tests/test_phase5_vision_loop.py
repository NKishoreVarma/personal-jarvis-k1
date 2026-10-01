"""
Unit tests for Phase 5 — JARVIS Computer Vision + Observe/Act/Verify Loop.
All tests use mocks to avoid real network, Gemini, or screen/browser operations.
"""

import time
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image

from core.agent_orchestrator import (
    AgentOrchestrator,
    AgentState,
    Plan,
    PlanStep,
    StepStatus,
    Tool,
    ToolRegistry,
)
from core.computer_observer import ComputerObserver
from core.verifier import VerificationType, Verifier


class MockPlayer:
    def __init__(self):
        self.logs = []

    def write_log(self, text: str):
        self.logs.append(text)


class TestPhase5VisionLoop(unittest.TestCase):
    def setUp(self):
        self.player = MockPlayer()
        self.observer = ComputerObserver()
        self.verifier = Verifier()

    # 1. Observe screen test
    @patch("actions.screen_processor._capture_screen")
    def test_observe_screen(self, mock_capture):
        mock_img = Image.new("RGB", (100, 100))
        mock_capture.return_value = mock_img

        obs = self.observer.observe_screen()
        self.assertTrue(obs["success"])
        self.assertEqual(obs["type"], "screen")
        self.assertEqual(obs["metadata"]["width"], 100)
        self.assertEqual(obs["metadata"]["height"], 100)

    # 2. Analyze screen test
    @patch("google.genai.Client")
    @patch("actions.web_search._get_api_key", return_value="fake_key")
    def test_analyze_screen(self, mock_key, mock_genai_client):
        mock_response = MagicMock()
        mock_response.text = "Google Chrome is open on the desktop"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client

        mock_img = Image.new("RGB", (100, 100))
        res = self.observer.analyze_screen(mock_img, "Is Chrome open?")
        self.assertTrue(res["success"])
        self.assertIn("Chrome is open", res["answer"])

    # 3. Open app → verify app
    def test_verify_open_app(self):
        step = PlanStep(
            id=1,
            description="Open Chrome",
            tool="open_app",
            parameters={"app_name": "Chrome"},
            requires_verification=True,
        )
        res = self.verifier.verify(step=step, result="Chrome launched successfully")
        self.assertTrue(res["success"])
        self.assertEqual(res["type"], VerificationType.APP_OPENED.value)

    # 4. Browser navigate → verify page
    def test_verify_browser_navigate(self):
        step = PlanStep(
            id=1,
            description="Go to Google",
            tool="browser_control",
            parameters={"action": "navigate", "url": "https://google.com"},
            requires_verification=True,
        )
        res = self.verifier.verify(step=step, result="Navigated to https://google.com successfully")
        self.assertTrue(res["success"])
        self.assertEqual(res["type"], VerificationType.BROWSER_LOADED.value)

    # 5. Verification failure → recovery loop
    def test_verification_failure_recovery(self):
        attempts = [0]

        def failing_exec(params, player=None):
            attempts[0] += 1
            return "Failed result"

        registry = ToolRegistry()
        registry.register(Tool(
            name="test_tool",
            description="Test action",
            parameters={},
            execute=failing_exec,
            permission_level="low_risk",
        ))

        orchestrator = AgentOrchestrator(registry=registry)
        plan = Plan(
            goal="Verification fail test",
            steps=[PlanStep(id=1, description="Step 1", tool="test_tool", parameters={}, requires_verification=True)],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Verification fail test", player=self.player)
        self.assertEqual(res["status"], "failed")
        # Should attempt execution (1) + 2 recovery retries = 3 attempts total
        self.assertEqual(attempts[0], 3)

    # 6. Observation timeout / failure
    @patch("actions.screen_processor._capture_screen", side_effect=TimeoutError("Screen capture timed out"))
    def test_observation_timeout(self, mock_capture):
        obs = self.observer.observe_screen()
        self.assertFalse(obs["success"])
        self.assertIn("timed out", obs["error"])

    # 7. Vision API failure
    @patch("google.genai.Client", side_effect=Exception("Vision API 500 Server Error"))
    @patch("actions.web_search._get_api_key", return_value="fake_key")
    def test_vision_api_failure(self, mock_key, mock_genai_client):
        mock_img = Image.new("RGB", (100, 100))
        res = self.observer.analyze_screen(mock_img, "Is Chrome open?")
        self.assertFalse(res["success"])
        self.assertIn("Vision API 500", res["answer"])

    # 8. Agent step limit (MAX_STEPS = 10)
    def test_agent_step_limit(self):
        registry = ToolRegistry()
        orchestrator = AgentOrchestrator(registry=registry)
        steps = [
            PlanStep(id=i, description=f"Step {i}", tool="web_search", parameters={"query": f"test {i}"})
            for i in range(1, 15)
        ]
        plan = Plan(goal="Step limit test", steps=steps)
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Step limit test", player=self.player)
        self.assertEqual(res["status"], "failed")
        self.assertEqual(res["reason"], "Step limit exceeded")

    # 9. Agent runtime limit (MAX_AGENT_RUNTIME = 120s)
    @patch("time.monotonic")
    def test_agent_runtime_limit(self, mock_time):
        mock_time.side_effect = [100.0, 300.0, 301.0, 302.0]  # Simulate 200s elapsed
        registry = ToolRegistry()
        orchestrator = AgentOrchestrator(registry=registry)

        plan = Plan(
            goal="Runtime limit test",
            steps=[PlanStep(id=1, description="Step 1", tool="open_app", parameters={"app_name": "Chrome"})],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Runtime limit test", player=self.player)
        self.assertEqual(res["status"], "failed")
        self.assertEqual(res["reason"], "Runtime limit exceeded")

    # 10. Cancellation during observation
    @patch("core.computer_observer.computer_observer.observe_screen")
    def test_cancellation_during_observation(self, mock_observe):
        registry = ToolRegistry()
        orchestrator = AgentOrchestrator(registry=registry)

        def _cancel_side_effect():
            orchestrator.cancel()
            return {"success": True, "type": "screen", "image": None, "metadata": {}}

        mock_observe.side_effect = _cancel_side_effect

        plan = Plan(
            goal="Cancel during observation test",
            steps=[PlanStep(id=1, description="Step 1", tool="open_app", parameters={"app_name": "Chrome"}, requires_observation=True)],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Cancel during observation test", player=self.player)
        self.assertEqual(res["status"], "cancelled")
        self.assertEqual(orchestrator.state, AgentState.CANCELLED)


if __name__ == "__main__":
    unittest.main()
