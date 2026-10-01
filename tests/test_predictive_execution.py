"""
Unit & Integration Tests for Predictive Execution & Safe Parallel Agent Preparation (Phase 12.4).
"""

import asyncio
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.predictive_execution import (
    PredictiveExecutionManager,
    PredictiveState,
)
from core.preparation_contract import (
    PreparationContract,
    PreparationRisk,
    create_preparation_contract,
)


class TestPredictiveExecution(unittest.TestCase):
    def setUp(self):
        self.manager = PredictiveExecutionManager()

    def test_01_preparation_contract_safety_enforcement(self):
        # Safe read-only contract
        c_safe = create_preparation_contract(
            turn_id="t1",
            operation="prefetch_project",
            arguments={"project_name": "FLOW"},
            side_effect_free=True,
        )
        self.assertTrue(c_safe.can_execute_predictively())
        self.assertEqual(c_safe.risk_level, PreparationRisk.READ_ONLY)

        # Prohibited mutating contract
        c_mutating = create_preparation_contract(
            turn_id="t1",
            operation="launch_server",
            arguments={"cmd": "npm start"},
            side_effect_free=False,
        )
        self.assertFalse(c_mutating.can_execute_predictively())
        self.assertEqual(c_mutating.risk_level, PreparationRisk.PROHIBITED_MUTATING)

    def test_02_partial_transcript_project_classification(self):
        pred = self.manager._classify_partial_intent("open FLOW from my Desktop")
        self.assertIsNotNone(pred)
        self.assertEqual(pred["task_type"], "PROJECT_OPERATION")
        self.assertEqual(pred["project_name"], "FLOW")
        self.assertEqual(pred["location_hint"], "Desktop")
        self.assertGreaterEqual(pred["confidence"], 0.80)

    def test_03_partial_transcript_app_classification(self):
        pred = self.manager._classify_partial_intent("open WhatsApp and")
        self.assertIsNotNone(pred)
        self.assertEqual(pred["task_type"], "APPLICATION_OPERATION")
        self.assertEqual(pred["app_name"], "WhatsApp")
        self.assertGreaterEqual(pred["confidence"], 0.85)

    def test_04_low_confidence_ignored(self):
        res = self.manager.on_partial_transcript("the", turn_id="t10")
        self.assertIsNone(res)

    @patch("core.project_discovery.project_discovery.find_project")
    @patch("core.project_profiler.project_profiler.profile_project")
    def test_05_project_execution_prefetch_caching(self, mock_profile, mock_find):
        mock_find.return_value = {"found": True, "path": Path("/Users/test/FLOW"), "exact": True}
        mock_profile.return_value = {
            "success": True,
            "project_path": "/Users/test/FLOW",
            "framework": "Next.js",
            "startup_command": ["npm", "run", "dev"],
            "port": 3000,
        }

        async def _run():
            pred = self.manager.on_partial_transcript("open FLOW from Desktop", turn_id="t101")
            self.assertIsNotNone(pred)

            # Wait for background task
            await asyncio.sleep(0.05)

            res = self.manager.get_prepared_result(
                operation="prefetch_project",
                turn_id="t101",
                arguments={"project_name": "FLOW"},
            )
            self.assertIsNotNone(res)
            self.assertTrue(res.get("found"))
            self.assertEqual(res.get("framework"), "Next.js")
            self.assertEqual(res.get("command"), ["npm", "run", "dev"])

        asyncio.run(_run())

    def test_06_prediction_invalidation_on_changed_meaning(self):
        # 1. First partial: "open FLOW" -> PROJECT_OPERATION
        self.manager.on_partial_transcript("open FLOW", turn_id="t102")
        prep_ids = list(self.manager._turn_contracts.get("t102", []))
        self.assertGreater(len(prep_ids), 0)

        # 2. Meaning changes: "open Chrome and" -> APPLICATION_OPERATION
        self.manager.on_partial_transcript("open Chrome and", turn_id="t102")

        # The project contract should now be marked invalid
        for pid in prep_ids:
            c = self.manager._contracts.get(pid)
            if c and c.operation == "prefetch_project":
                self.assertFalse(c.is_valid)

    @patch("core.project_discovery.project_discovery.find_project")
    @patch("core.project_profiler.project_profiler.profile_project")
    def test_07_turn_bound_isolation(self, mock_profile, mock_find):
        mock_find.return_value = {"found": True, "path": Path("/Users/test/FLOW"), "exact": True}
        mock_profile.return_value = {
            "success": True,
            "project_path": "/Users/test/FLOW",
            "framework": "Next.js",
            "startup_command": ["npm", "run", "dev"],
            "port": 3000,
        }

        async def _run():
            # Turn 1
            self.manager.on_partial_transcript("open FLOW", turn_id="turn_1")
            await asyncio.sleep(0.05)

            # Turn 1 should have result
            res1 = self.manager.get_prepared_result("prefetch_project", "turn_1", {"project_name": "FLOW"})
            self.assertIsNotNone(res1)

            # Turn 2 should NOT have Turn 1 result
            res2 = self.manager.get_prepared_result("prefetch_project", "turn_2", {"project_name": "FLOW"})
            self.assertIsNone(res2)

            # Invalidate Turn 1
            self.manager.invalidate_turn("turn_1")
            res1_after = self.manager.get_prepared_result("prefetch_project", "turn_1", {"project_name": "FLOW"})
            self.assertIsNone(res1_after)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
