"""
Smoke & Integration Tests for Real Laya Neural Model Integration in MARK XLVIII / JARVIS.
Verifies:
1. import laya succeeds
2. Real checkpoint loading into LayaModelHandle
3. Real neural inference execution
4. Real probability distribution and calibrated confidence
5. Source identification as DecisionSource.REAL_LAYA
6. Direct Laya API vs JARVIS LayaDecisionAdapter correspondence
7. Real inference latency measurement
8. Confidence gate validation with real neural output
9. Inviolable governance preservation
"""

from __future__ import annotations

import time
import unittest

from core.decision_confidence_gate import decision_confidence_gate
from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionSource,
    DecisionType,
)
from core.decision_policy_router import RoutingMode, decision_policy_router
from core.laya_decision_adapter import LayaDecisionAdapter, laya_decision_adapter
from core.system1_decision_engine import system1_decision_engine


class TestRealLayaSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import laya

            cls.laya_installed = True
        except ImportError:
            cls.laya_installed = False

    def test_01_import_laya_succeeds(self):
        self.assertTrue(self.laya_installed, "laya package must be installed in the virtual environment.")
        import laya

        self.assertTrue(hasattr(laya, "load"))
        self.assertTrue(hasattr(laya, "Router"))

    def test_02_real_checkpoint_loading(self):
        if not self.laya_installed:
            self.skipTest("laya package not installed")

        adapter = LayaDecisionAdapter(device="cpu")
        ok = adapter.load_model("laya")
        self.assertTrue(ok)
        handle = adapter._loaded_models.get("laya")
        self.assertIsNotNone(handle)
        self.assertTrue(handle.is_real)
        self.assertEqual(handle.backend, "real_laya")
        self.assertIsNotNone(handle.model)

    def test_03_real_neural_choice_inference(self):
        if not self.laya_installed:
            self.skipTest("laya package not installed")

        state = {"request": "Please refund my duplicate payment"}
        options = ["billing_refund", "technical_support", "general_inquiry"]

        res = laya_decision_adapter.decide_choice(
            context=state["request"],
            options=options,
            category=DecisionCategory.INTENT,
        )

        self.assertIsInstance(res, DecisionResult)
        self.assertEqual(res.source, DecisionSource.REAL_LAYA)
        self.assertTrue(res.metadata.get("is_real"))
        self.assertEqual(res.metadata.get("backend"), "real_laya")
        self.assertIn(res.selected_option, options)
        self.assertGreater(res.confidence, 0.0)
        self.assertGreater(res.latency_ms, 0.0)
        self.assertIn("billing_refund", res.alternatives)

    def test_04_direct_laya_vs_jarvis_adapter_correspondence(self):
        if not self.laya_installed:
            self.skipTest("laya package not installed")

        import laya

        agent = laya.load("convaiinnovations/laya", device="cpu")

        state = {"request": "Please refund my duplicate payment"}
        options = ["billing_refund", "technical_support", "general_inquiry"]
        questions = {
            "intent": {
                "type": "choice",
                "instructions": "Classify the intent for the request.",
                "criteria": {opt: opt.replace("_", " ") for opt in options},
            }
        }

        # Direct Laya execution
        direct_pred = agent.predict(state, questions)
        direct_choice = direct_pred["answers"]["intent"]["choice"]
        direct_conf = direct_pred["answers"]["intent"]["confidence"]

        # JARVIS Adapter execution
        adapter_res = laya_decision_adapter.decide_choice(
            context=state["request"],
            options=["billing_refund", "technical_support", "general_inquiry"],
            category=DecisionCategory.INTENT,
        )

        # Verify output correspondence
        self.assertEqual(adapter_res.selected_option, direct_choice)
        self.assertAlmostEqual(adapter_res.confidence, direct_conf, places=2)
        self.assertEqual(adapter_res.source, DecisionSource.REAL_LAYA)

    def test_05_confidence_gate_with_real_neural_output(self):
        if not self.laya_installed:
            self.skipTest("laya package not installed")

        res = laya_decision_adapter.decide_choice(
            context="Please refund my duplicate payment",
            options=["billing_refund", "technical_support", "general_inquiry"],
            category=DecisionCategory.INTENT,
        )

        passed, rationale = decision_confidence_gate.evaluate_decision(res)
        self.assertTrue(passed)
        self.assertFalse(res.abstained)

    def test_06_governance_and_shadow_mode_preservation(self):
        if not self.laya_installed:
            self.skipTest("laya package not installed")

        decision_policy_router.set_mode(RoutingMode.SHADOW)
        res = system1_decision_engine.decide(
            "Please refund my duplicate payment",
            category=DecisionCategory.INTENT,
            options=["billing_refund", "technical_support", "general_inquiry"],
        )

        # Real Laya executes and records prediction
        self.assertEqual(res.source, DecisionSource.REAL_LAYA)

        # In SHADOW mode, System 2 baseline remains authoritative
        final_choice, rationale = decision_policy_router.arbitrate_decision(res, "system2_baseline")
        self.assertEqual(final_choice, "system2_baseline")
        self.assertIn("SHADOW", rationale)


if __name__ == "__main__":
    unittest.main()
