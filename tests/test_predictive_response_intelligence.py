"""
Unit & Integration Tests for Predictive Response Generation & Instant Completion Intelligence (Phase 12.6).
"""

import time
import unittest

from core.completion_response_cache import (
    CompletionResponseCache,
    completion_response_cache,
)
from core.execution_response_binder import (
    ExecutionResponseBinder,
    execution_response_binder,
)
from core.instant_completion_dispatcher import (
    InstantCompletionDispatcher,
    instant_completion_dispatcher,
)
from core.predictive_response_planner import (
    PredictiveResponsePlanner,
    predictive_response_planner,
)
from core.response_contract import (
    ResponseContract,
    ResponseStage,
    create_response_contract,
)
from core.streaming_intent_engine import StreamingIntent


class TestPredictiveResponseIntelligence(unittest.TestCase):
    def setUp(self):
        completion_response_cache.invalidate_turn("t_resp_test")

    def test_01_planner_project_run_response(self):
        intent = StreamingIntent(
            turn_id="t1",
            intent_type="RUN_PROJECT",
            confidence=0.98,
            entities={"project": "FLOW", "port": 3000},
            raw_text="open FLOW and run the server",
        )
        contract = predictive_response_planner.plan_response(intent)
        self.assertIn(contract.ack_response, ("Okay.", "Starting FLOW."))
        self.assertTrue(contract.requires_completion_announcement)
        self.assertIn("{project}", contract.success_template)
        self.assertIn("{port}", contract.success_template)

    def test_02_planner_app_open_intelligent_silence(self):
        intent = StreamingIntent(
            turn_id="t2",
            intent_type="OPEN_APP",
            confidence=0.95,
            entities={"app_name": "Chrome"},
            raw_text="open Chrome",
        )
        contract = predictive_response_planner.plan_response(intent)
        self.assertEqual(contract.ack_response, "Opening Chrome.")
        # Visual app launch should have intelligent silence by default
        self.assertFalse(contract.requires_completion_announcement)

    def test_03_planner_explicit_completion_requested(self):
        intent = StreamingIntent(
            turn_id="t3",
            intent_type="OPEN_APP",
            confidence=0.95,
            entities={"app_name": "Chrome"},
            raw_text="open Chrome and tell me when it's ready",
        )
        contract = predictive_response_planner.plan_response(intent)
        # Explicit request overrides default intelligent silence
        self.assertTrue(contract.requires_completion_announcement)

    def test_04_execution_binder_success(self):
        contract = create_response_contract(
            turn_id="t4",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            success_template="{project} is running successfully on port {port}.",
        )
        self.assertEqual(contract.stage, ResponseStage.INITIAL)

        # Bind verified execution data
        bound = execution_response_binder.bind_success(contract, {"project": "FLOW", "port": 3000})
        self.assertTrue(bound.is_success)
        self.assertEqual(bound.stage, ResponseStage.SUCCESS_RELEASED)
        self.assertEqual(bound.spoken_text, "FLOW is running successfully on port 3000.")

    def test_05_execution_binder_failure(self):
        contract = create_response_contract(
            turn_id="t5",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            failure_template="Failed to run {project}: {error}.",
        )
        bound = execution_response_binder.bind_failure(contract, error="Port 3000 already in use")
        self.assertFalse(bound.is_success)
        self.assertEqual(bound.stage, ResponseStage.FAILURE_RELEASED)
        self.assertIn("Port 3000 already in use", bound.spoken_text)

    def test_06_completion_response_cache_lifecycle(self):
        cache = CompletionResponseCache()
        contract = create_response_contract(turn_id="t6", task_type="RUN_PROJECT", entities={"project": "FLOW"})

        cache.store_contract(contract)
        retrieved = cache.get_contract("t6")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.contract_id, contract.contract_id)

        cache.invalidate_turn("t6")
        self.assertIsNone(cache.get_contract("t6"))

    def test_07_instant_completion_dispatcher(self):
        contract = create_response_contract(
            turn_id="t7",
            task_type="RUN_PROJECT",
            entities={"project": "FLOW"},
            success_template="{project} is running on port {port}.",
            requires_completion_announcement=True,
        )
        completion_response_cache.store_contract(contract)

        captured_messages = []

        def mock_ui(msg):
            captured_messages.append(msg)

        bound = instant_completion_dispatcher.dispatch_completion(
            turn_id="t7",
            success=True,
            verified_data={"project": "FLOW", "port": 3000},
            ui_callback=mock_ui,
        )

        self.assertIsNotNone(bound)
        self.assertEqual(bound.spoken_text, "FLOW is running on port 3000.")
        self.assertEqual(len(captured_messages), 1)
        self.assertEqual(captured_messages[0], "FLOW is running on port 3000.")

        # Duplicate dispatch should return None
        dup = instant_completion_dispatcher.dispatch_completion(
            turn_id="t7",
            success=True,
            verified_data={"project": "FLOW", "port": 3000},
        )
        self.assertIsNone(dup)


if __name__ == "__main__":
    unittest.main()
