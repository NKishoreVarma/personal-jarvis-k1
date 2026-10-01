"""
Unit tests for core.agent_orchestrator (JARVIS Agent Loop).
"""

import unittest
from core.agent_orchestrator import (
    AgentOrchestrator,
    AgentState,
    Plan,
    PlanSchema,
    PlanStep,
    StepSchema,
    StepStatus,
    Tool,
    ToolRegistry,
)


class MockPlayer:
    def __init__(self):
        self.logs = []

    def write_log(self, text: str):
        self.logs.append(text)


class TestAgentOrchestrator(unittest.TestCase):
    def setUp(self):
        self.player = MockPlayer()

    def test_structured_plan_dataclasses(self):
        step = PlanStep(
            id=1,
            description="Test Step",
            tool="open_app",
            parameters={"app_name": "Chrome"},
        )
        self.assertEqual(step.status, StepStatus.PENDING)
        step_dict = step.to_dict()
        self.assertEqual(step_dict["id"], 1)
        self.assertEqual(step_dict["status"], "pending")

        plan = Plan(goal="Open Chrome", steps=[step])
        plan_dict = plan.to_dict()
        self.assertEqual(plan_dict["goal"], "Open Chrome")
        self.assertEqual(len(plan_dict["steps"]), 1)

    def test_tool_registry_reuse(self):
        registry = ToolRegistry()
        tools = registry.list_tools()
        self.assertIn("open_app", tools)
        self.assertIn("browser_control", tools)
        self.assertIn("screen_process", tools)
        self.assertIn("web_search", tools)
        self.assertIn("computer_settings", tools)
        self.assertIn("save_memory", tools)

    def test_plan_schema_validation(self):
        registry = ToolRegistry()
        orchestrator = AgentOrchestrator(registry=registry)

        raw_plan = PlanSchema(
            goal="Test plan validation",
            steps=[
                StepSchema(id=1, description="Open Chrome", tool="open_app", parameters={"app_name": "Chrome"}),
                StepSchema(id=2, description="Unknown step", tool="invalid_unknown_tool", parameters={}),
                StepSchema(id=3, description="Search news", tool="web_search", parameters={"query": "news"}),
            ]
        )

        validated = orchestrator.validate_plan(raw_plan)
        # Should accept valid tools (open_app, web_search) and reject invalid_unknown_tool
        self.assertEqual(len(validated.steps), 2)
        self.assertEqual(validated.steps[0].tool, "open_app")
        self.assertEqual(validated.steps[1].tool, "web_search")
        self.assertEqual(validated.steps[0].id, 1)
        self.assertEqual(validated.steps[1].id, 2)

    def test_successful_goal_execution(self):
        registry = ToolRegistry()
        # Register a fast mock tool
        registry.register(Tool(
            name="mock_tool",
            description="Mock action",
            parameters={"query": "string"},
            execute=lambda params, player=None: "Mock result success",
            permission_level="normal",
        ))

        orchestrator = AgentOrchestrator(registry=registry)
        plan = Plan(
            goal="Mock goal",
            steps=[PlanStep(id=1, description="Run mock", tool="mock_tool", parameters={})],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Mock goal", player=self.player)
        self.assertEqual(res["status"], "completed")
        self.assertIn("[AGENT] Goal completed", self.player.logs)

    def test_failure_retry_limit(self):
        attempts = [0]

        def failing_tool(params, player=None):
            attempts[0] += 1
            return "Failed execution error"

        registry = ToolRegistry()
        registry.register(Tool(
            name="failing_tool",
            description="Failing action",
            parameters={},
            execute=failing_tool,
            permission_level="normal",
        ))

        orchestrator = AgentOrchestrator(registry=registry)
        plan = Plan(
            goal="Failing goal",
            steps=[PlanStep(id=1, description="Run fail", tool="failing_tool", parameters={})],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Failing goal", player=self.player)
        self.assertEqual(res["status"], "failed")
        # Should attempt initial execution (1) + 2 retries = 3 attempts total
        self.assertEqual(attempts[0], 3)

    def test_destructive_tool_no_auto_retry(self):
        attempts = [0]

        def destructive_failing_tool(params, player=None):
            attempts[0] += 1
            return "Failed destructive action"

        registry = ToolRegistry()
        registry.register(Tool(
            name="destructive_tool",
            description="Destructive action",
            parameters={},
            execute=destructive_failing_tool,
            permission_level="destructive",
        ))

        orchestrator = AgentOrchestrator(registry=registry)
        plan = Plan(
            goal="Destructive goal",
            steps=[PlanStep(id=1, description="Run destructive", tool="destructive_tool", parameters={})],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Destructive goal", player=self.player)
        self.assertEqual(res["status"], "failed")
        # Destructive action should fail on 1st attempt without automatic retries
        self.assertEqual(attempts[0], 1)

    def test_cancellation(self):
        registry = ToolRegistry()
        orchestrator = AgentOrchestrator(registry=registry)
        plan = Plan(
            goal="Long goal",
            steps=[
                PlanStep(id=1, description="Step 1", tool="open_app", parameters={"app_name": "Chrome"}),
                PlanStep(id=2, description="Step 2", tool="web_search", parameters={"query": "test"}),
            ],
        )
        orchestrator.create_plan = lambda goal: plan

        # Pre-request cancellation
        orchestrator.cancel()
        res = orchestrator.run_goal("Long goal", player=self.player)
        self.assertEqual(res["status"], "cancelled")
        self.assertEqual(orchestrator.state, AgentState.CANCELLED)


if __name__ == "__main__":
    unittest.main()
