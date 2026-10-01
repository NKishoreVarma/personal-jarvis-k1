"""
Unit tests for Phase 7 — Controlled Code Modification (core/patch_manager.py & actions/code_editor.py).
"""

import unittest
from pathlib import Path

from actions.code_editor import apply_patch, propose_patch, rollback_patch
from core.agent_orchestrator import (
    AgentOrchestrator,
    Plan,
    PlanStep,
    ToolRegistry,
)
from core.patch_manager import patch_manager


class MockPlayer:
    def __init__(self):
        self.logs = []

    def write_log(self, text: str):
        self.logs.append(text)


class TestPhase7CodeEditor(unittest.TestCase):
    def setUp(self):
        self.player = MockPlayer()
        self.test_dir = Path(__file__).resolve().parent / "tmp_patch_test"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        self.test_file = self.test_dir / "math_utils.py"
        self.test_file.write_text(
            "def add(a, b):\n"
            "    # Old addition function\n"
            "    return a + b\n\n"
            "def multiply(a, b):\n"
            "    return a * b\n"
        )

        self.ambiguous_file = self.test_dir / "ambiguous.py"
        self.ambiguous_file.write_text(
            "x = 1\n"
            "x = 1\n"
            "x = 1\n"
        )

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()
        if self.ambiguous_file.exists():
            self.ambiguous_file.unlink()
        if self.test_dir.exists():
            try:
                self.test_dir.rmdir()
            except Exception:
                pass

    # 1. Diff preview generation
    def test_preview_patch_diff(self):
        res = propose_patch(
            {
                "file": str(self.test_file),
                "old_text": "# Old addition function",
                "new_text": "# New improved addition function",
                "reason": "Update comment",
            },
            player=self.player,
        )
        self.assertTrue(res["success"])
        self.assertIn("--- a/math_utils.py", res["diff"])
        self.assertIn("+++ b/math_utils.py", res["diff"])
        self.assertIn("-    # Old addition function", res["diff"])
        self.assertIn("+    # New improved addition function", res["diff"])

    # 2. Successful single-match patch application
    def test_apply_patch_success(self):
        res = apply_patch(
            {
                "file": str(self.test_file),
                "old_text": "return a + b",
                "new_text": "return int(a) + int(b)",
                "reason": "Typecast inputs",
                "confirmed": True,
            },
            player=self.player,
        )
        self.assertTrue(res["success"])
        # Check actual file contents
        content = self.test_file.read_text()
        self.assertIn("return int(a) + int(b)", content)
        self.assertNotIn("return a + b\n\ndef multiply", content)

    # 3. Rejection when old_text not found
    def test_apply_patch_not_found(self):
        res = apply_patch(
            {
                "file": str(self.test_file),
                "old_text": "def non_existent_function():",
                "new_text": "def new_function():",
                "reason": "Replace non-existent",
                "confirmed": True,
            },
            player=self.player,
        )
        self.assertFalse(res["success"])
        self.assertIn("was not found", res["error"])

    # 4. Rejection when old_text is ambiguous
    def test_apply_patch_ambiguous(self):
        res = apply_patch(
            {
                "file": str(self.ambiguous_file),
                "old_text": "x = 1",
                "new_text": "x = 2",
                "reason": "Ambiguous replacement",
                "confirmed": True,
            },
            player=self.player,
        )
        self.assertFalse(res["success"])
        self.assertIn("is ambiguous", res["error"])

    # 5. Rejection of sensitive paths or paths outside workspace
    def test_apply_patch_security_rejection(self):
        res = apply_patch(
            {
                "file": "/etc/hosts",
                "old_text": "127.0.0.1",
                "new_text": "127.0.0.2",
                "reason": "Illegal system edit",
                "confirmed": True,
            },
            player=self.player,
        )
        self.assertFalse(res["success"])
        self.assertIn("Security violation", res["error"])

    # 6. Automatic backup creation and rollback restoration
    def test_patch_rollback(self):
        original_content = self.test_file.read_text()

        # Apply a patch
        apply_res = apply_patch(
            {
                "file": str(self.test_file),
                "old_text": "return a * b",
                "new_text": "return float(a) * float(b)",
                "reason": "Float multiply",
                "confirmed": True,
            },
            player=self.player,
        )
        self.assertTrue(apply_res["success"])
        self.assertIn("float(a)", self.test_file.read_text())

        # Rollback
        rb_res = rollback_patch({"file": str(self.test_file)}, player=self.player)
        self.assertTrue(rb_res["success"])
        self.assertEqual(self.test_file.read_text(), original_content)

    # 7. Orchestrator tool registry integration
    def test_orchestrator_patch_tool_execution(self):
        registry = ToolRegistry()
        orchestrator = AgentOrchestrator(registry=registry)

        plan = Plan(
            goal="Refactor add function",
            steps=[
                PlanStep(
                    id=1,
                    description="Propose patch",
                    tool="propose_patch",
                    parameters={
                        "file": str(self.test_file),
                        "old_text": "# Old addition function",
                        "new_text": "# Verified addition",
                    },
                ),
            ],
        )
        orchestrator.create_plan = lambda goal: plan

        res = orchestrator.run_goal("Refactor add function", player=self.player)
        self.assertEqual(res["status"], "completed")
        self.assertIn("[AGENT] Result: Success", self.player.logs)


if __name__ == "__main__":
    unittest.main()
