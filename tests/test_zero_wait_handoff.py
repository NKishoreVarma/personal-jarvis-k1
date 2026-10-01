"""
Unit & Integration Tests for Streaming Intent Engine & Zero-Wait Execution Handoff (Phase 12.5).
"""

import asyncio
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.command_commit_gate import (
    CommandCommitGate,
    CommitStatus,
    command_commit_gate,
)
from core.intent_stability_manager import (
    IntentStabilityManager,
    StabilityState,
    intent_stability_manager,
)
from core.predictive_execution import (
    PredictiveExecutionManager,
    predictive_manager,
)
from core.response_scheduler import (
    ResponseMode,
    ResponseScheduler,
    response_scheduler,
)
from core.streaming_intent_engine import (
    StreamingIntent,
    StreamingIntentEngine,
    streaming_intent_engine,
)
from core.zero_wait_handoff import (
    HandoffResult,
    HandoffStatus,
    ZeroWaitHandoff,
    zero_wait_handoff,
)


class TestZeroWaitHandoff(unittest.TestCase):
    def setUp(self):
        streaming_intent_engine.clear_turn("t_test")
        intent_stability_manager.clear_turn("t_test")
        predictive_manager.invalidate_turn("t_test")

    def test_01_streaming_intent_evolution(self):
        engine = StreamingIntentEngine()

        # Step 1: "open"
        i1 = engine.process_partial("t1", "open")
        self.assertEqual(i1.intent_type, "COMPLEX_QUERY")
        self.assertFalse(i1.stable)

        # Step 2: "open FLOW"
        i2 = engine.process_partial("t1", "open FLOW")
        self.assertEqual(i2.intent_type, "PROJECT_OPERATION")
        self.assertEqual(i2.entities.get("project"), "flow")

        # Step 3: "open FLOW from Desktop"
        i3 = engine.process_partial("t1", "open FLOW from Desktop")
        self.assertEqual(i3.entities.get("location"), "desktop")
        self.assertGreaterEqual(i3.confidence, 0.90)

        # Step 4: "open FLOW from Desktop and run the server"
        i4 = engine.process_partial("t1", "open FLOW from Desktop and run the server")
        self.assertEqual(i4.intent_type, "RUN_PROJECT")
        self.assertEqual(i4.entities.get("action"), "run_server")
        self.assertTrue(i4.stable)

    def test_02_intent_stability_and_contradiction(self):
        stability_mgr = IntentStabilityManager()

        # Consistent stream
        i1 = StreamingIntent(turn_id="t2", intent_type="RUN_PROJECT", confidence=0.88, entities={"project": "flow"})
        s1 = stability_mgr.evaluate_stability(i1)

        i2 = StreamingIntent(turn_id="t2", intent_type="RUN_PROJECT", confidence=0.96, entities={"project": "flow"})
        s2 = stability_mgr.evaluate_stability(i2)
        self.assertEqual(s2, StabilityState.STABLE)
        self.assertTrue(stability_mgr.is_stable("t2"))

        # Contradiction: Switch to Chrome
        i_pivot = StreamingIntent(turn_id="t2", intent_type="OPEN_APP", confidence=0.92, entities={"app_name": "chrome"})
        s_pivot = stability_mgr.evaluate_stability(i_pivot)
        self.assertEqual(s_pivot, StabilityState.CHANGED)

    def test_03_command_commit_gate_validation(self):
        gate = CommandCommitGate()

        # Valid finalized command
        intent = StreamingIntent(turn_id="t3", intent_type="RUN_PROJECT", confidence=0.95, entities={"project": "flow"})
        dec_valid = gate.evaluate_commit(
            turn_id="t3",
            final_command="open FLOW from Desktop and run the server",
            intent=intent,
            is_finalized=True,
        )
        self.assertTrue(dec_valid.is_committed)
        self.assertEqual(dec_valid.status, CommitStatus.COMMITTED)

        # Unfinalized command rejected
        dec_unfin = gate.evaluate_commit(
            turn_id="t3",
            final_command="open FLOW",
            intent=intent,
            is_finalized=False,
        )
        self.assertFalse(dec_unfin.is_committed)
        self.assertEqual(dec_unfin.status, CommitStatus.REJECTED_UNFINALIZED)

    @patch("core.project_discovery.project_discovery.find_project")
    @patch("core.project_profiler.project_profiler.profile_project")
    def test_04_zero_wait_handoff_project_claim(self, mock_profile, mock_find):
        mock_find.return_value = {"found": True, "path": Path("/Users/test/FLOW"), "exact": True}
        mock_profile.return_value = {
            "success": True,
            "project_path": "/Users/test/FLOW",
            "framework": "Next.js",
            "startup_command": ["npm", "run", "dev"],
            "port": 3000,
        }

        async def _run():
            turn_id = "t_handoff_proj"
            # 1. Stream partial transcript
            intent = streaming_intent_engine.process_partial(turn_id, "open FLOW from Desktop and run the server")
            intent_stability_manager.evaluate_stability(intent)
            predictive_manager.on_partial_transcript("open FLOW from Desktop", turn_id=turn_id)

            await asyncio.sleep(0.05)

            # 2. Finalize & Claim
            handoff = zero_wait_handoff.claim(turn_id, "open FLOW from Desktop and run the server")
            self.assertEqual(handoff.status, HandoffStatus.READY)
            self.assertIn("project_discovery", handoff.reused_components)
            self.assertIn("project_profiler", handoff.reused_components)
            self.assertEqual(handoff.execution_context.get("framework"), "Next.js")
            self.assertEqual(handoff.execution_context.get("command"), ["npm", "run", "dev"])

        asyncio.run(_run())

    def test_05_zero_wait_handoff_safe_fallback(self):
        # Empty / non-prepared turn claims safely without errors
        handoff = zero_wait_handoff.claim("t_empty", "unprepared random command")
        self.assertEqual(handoff.status, HandoffStatus.NO_PREPARATION)
        self.assertIsNone(handoff.execution_context)

    def test_06_response_scheduler(self):
        sched = ResponseScheduler()

        # App action
        resp_app = sched.schedule_response(task_type="OPEN_APP", target_name="Chrome")
        self.assertEqual(resp_app.mode, ResponseMode.INSTANT_ACK)
        self.assertTrue(resp_app.should_speak)
        self.assertIn("Chrome", resp_app.spoken_text)

        # Background project action with ready handoff
        ready_handoff = HandoffResult(status=HandoffStatus.READY, turn_id="t1")
        resp_proj = sched.schedule_response(task_type="RUN_PROJECT", handoff=ready_handoff, target_name="FLOW")
        self.assertEqual(resp_proj.mode, ResponseMode.INSTANT_ACK)
        self.assertEqual(resp_proj.spoken_text, "Okay.")

        # Utility command silent response
        resp_util = sched.schedule_response(task_type="GET_TIME")
        self.assertEqual(resp_util.mode, ResponseMode.SILENT)
        self.assertFalse(resp_util.should_speak)


if __name__ == "__main__":
    unittest.main()
