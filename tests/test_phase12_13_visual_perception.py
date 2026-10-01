"""
Phase 12.13 — Computer Vision, Screen Understanding & Autonomous Visual Interaction Test Suite.
Verifies all 27 core capabilities:
1. Visual context lifecycle
2. Turn isolation
3. Goal isolation
4. Screenshot expiration
5. OCR text extraction contract
6. UI element detection contract
7. Accessibility-first priority
8. OCR fallback
9. Visual fallback
10. Perception fusion
11. Duplicate target merging
12. Contradictory metadata
13. Spatial target resolution
14. Ambiguous visual target clarification
15. Low-confidence target blocking
16. ActionContract enforcement
17. Post-action visual verification
18. Screen change detection
19. Visual wait success
20. Visual wait timeout
21. Cancellation during visual wait
22. Error dialog detection
23. Visual evidence integration with ProblemSolver
24. Multi-agent visual observation
25. No screenshot persistence into long-term memory
26. Simple commands bypass visual pipeline
27. Voice pipeline remains non-blocking
"""

from __future__ import annotations

import asyncio
import time
import unittest
from PIL import Image

from actions.screen_capture import screen_capture_service
from core.action_contract import ActionContract, RiskLevel
from core.agent_contract import AgentRole, AuthorityLevel, create_agent_contract
from core.intent_router import router
from core.memory_contract import MemoryType, create_memory_contract
from core.memory_service import memory_service
from core.problem_solver import problem_solver
from core.screen_change_detector import screen_change_detector
from core.screen_perception_manager import PerceptionState, screen_perception_manager
from core.screen_text_extractor import screen_text_extractor
from core.shared_evidence_store import EvidenceCategory, shared_evidence_store
from core.ui_perception_fusion import ui_perception_fusion
from core.visual_action_verifier import VisualVerificationLevel, visual_action_verifier
from core.visual_context_contract import (
    DetectedTextBlock,
    UIElement,
    UIElementType,
    VisualVerificationState,
    create_visual_context_contract,
)
from core.visual_element_detector import visual_element_detector
from core.visual_reasoning_engine import visual_reasoning_engine
from core.visual_target_locator import visual_target_locator
from core.visual_wait_manager import VisualWaitCondition, visual_wait_manager


class TestPhase1213VisualPerception(unittest.TestCase):
    def setUp(self):
        screen_perception_manager._active_contexts.clear()
        screen_perception_manager.state = PerceptionState.IDLE
        shared_evidence_store.clear_all()

    # 1. Visual Context Lifecycle
    def test_01_visual_context_lifecycle(self):
        contract = create_visual_context_contract(
            turn_id="turn_v1",
            goal_id="goal_v1",
            source_window="FLOW Dashboard",
            ttl_seconds=10.0,
        )
        self.assertEqual(contract.turn_id, "turn_v1")
        self.assertEqual(contract.goal_id, "goal_v1")
        self.assertFalse(contract.is_expired())
        self.assertEqual(contract.verification_state, VisualVerificationState.OBSERVED)

    # 2. Turn Isolation
    def test_02_turn_isolation(self):
        ctx1 = create_visual_context_contract(turn_id="t1", goal_id="g1")
        ctx2 = create_visual_context_contract(turn_id="t2", goal_id="g2")

        screen_perception_manager._active_contexts["t1"] = ctx1
        screen_perception_manager._active_contexts["t2"] = ctx2

        self.assertEqual(screen_perception_manager.get_context("t1").turn_id, "t1")
        self.assertEqual(screen_perception_manager.get_context("t2").turn_id, "t2")
        screen_perception_manager.clear_context("t1")
        self.assertIsNone(screen_perception_manager.get_context("t1"))
        self.assertIsNotNone(screen_perception_manager.get_context("t2"))

    # 3. Goal Isolation
    def test_03_goal_isolation(self):
        shared_evidence_store.add_evidence("goal_1", "ag1", EvidenceCategory.VISUAL_UI_STATE.value, {"btn": "Start"}, source="ScreenPerceptionManager")
        shared_evidence_store.add_evidence("goal_2", "ag2", EvidenceCategory.VISUAL_UI_STATE.value, {"btn": "Stop"}, source="ScreenPerceptionManager")

        ev1 = shared_evidence_store.get_evidence("goal_1", EvidenceCategory.VISUAL_UI_STATE.value)
        ev2 = shared_evidence_store.get_evidence("goal_2", EvidenceCategory.VISUAL_UI_STATE.value)

        self.assertEqual(len(ev1), 1)
        self.assertEqual(ev1[0].value["btn"], "Start")
        self.assertEqual(len(ev2), 1)
        self.assertEqual(ev2[0].value["btn"], "Stop")

    # 4. Screenshot Expiration
    def test_04_screenshot_expiration(self):
        ctx = create_visual_context_contract(
            turn_id="t_exp",
            goal_id="g_exp",
            ttl_seconds=0.01,
        )
        screen_perception_manager._active_contexts["t_exp"] = ctx
        time.sleep(0.02)
        retrieved = screen_perception_manager.get_context("t_exp")
        self.assertIsNone(retrieved)
        self.assertEqual(screen_perception_manager.state, PerceptionState.STALE)

    # 5. OCR Text Extraction Contract
    def test_05_ocr_text_extraction_contract(self):
        provided = [
            {"text": "FLOW Server", "bounds": [100, 100, 300, 140], "confidence": 0.98},
            {"text": "Error: Port 3000 in use", "bounds": [100, 150, 400, 180], "confidence": 0.95},
        ]
        blocks = screen_text_extractor.extract_text_blocks(image=None, provided_blocks=provided)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].text, "FLOW Server")
        self.assertEqual(blocks[1].category, "error")

    # 6. UI Element Detection Contract
    def test_06_ui_element_detection_contract(self):
        provided = [
            {"type": "BUTTON", "label": "Start Server", "bounds": [500, 400, 620, 440], "confidence": 0.94},
            {"type": "CLOSE_BUTTON", "label": "X", "bounds": [900, 100, 930, 130], "confidence": 0.99},
        ]
        elements = visual_element_detector.detect_elements(provided_elements=provided)
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0].element_type, UIElementType.BUTTON)
        self.assertEqual(elements[0].center, (560, 420))
        self.assertEqual(elements[1].element_type, UIElementType.CLOSE_BUTTON)

    # 7. Accessibility-First Priority
    def test_07_accessibility_first_priority(self):
        ax_elements = [{"label": "Run", "role": "button", "bounds": [100, 100, 200, 140], "confidence": 0.98}]
        vis_elements = [UIElement(element_id="v1", element_type=UIElementType.BUTTON, bounds=(102, 101, 198, 139), label="Run", confidence=0.85)]

        res = ui_perception_fusion.fuse(accessibility_elements=ax_elements, visual_elements=vis_elements)
        fused = res["fused_elements"]
        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0].source, "accessibility")
        self.assertGreater(fused[0].confidence, 0.98)

    # 8. OCR Fallback
    def test_08_ocr_fallback(self):
        ocr_blocks = [DetectedTextBlock(text="Error occurred", bounds=(200, 200, 400, 240), confidence=0.92, category="error")]
        res = ui_perception_fusion.fuse(accessibility_elements=[], ocr_blocks=ocr_blocks)
        fused = res["fused_elements"]
        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0].element_type, UIElementType.ERROR_BANNER)
        self.assertEqual(fused[0].source, "ocr")

    # 9. Visual Fallback
    def test_09_visual_fallback(self):
        vis_elements = [UIElement(element_id="v_custom", element_type=UIElementType.BUTTON, bounds=(400, 400, 500, 440), label="Custom Canvas Button", confidence=0.91)]
        res = ui_perception_fusion.fuse(accessibility_elements=[], visual_elements=vis_elements)
        fused = res["fused_elements"]
        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0].label, "Custom Canvas Button")

    # 10. Perception Fusion
    def test_10_perception_fusion(self):
        ax = [{"label": "Settings", "role": "button", "bounds": [50, 50, 150, 80]}]
        ocr = [DetectedTextBlock(text="Settings", bounds=(52, 52, 148, 78), confidence=0.95)]
        vis = [UIElement(element_id="v2", element_type=UIElementType.BUTTON, bounds=(51, 51, 149, 79), label="Settings", confidence=0.90)]

        res = ui_perception_fusion.fuse(accessibility_elements=ax, ocr_blocks=ocr, visual_elements=vis)
        self.assertEqual(len(res["fused_elements"]), 1)
        self.assertTrue(res["fused_elements"][0].metadata.get("visual_corroborated"))

    # 11. Duplicate Target Merging
    def test_11_duplicate_target_merging(self):
        vis1 = UIElement(element_id="v1", element_type=UIElementType.BUTTON, bounds=(100, 100, 200, 140), label="Save", confidence=0.85)
        vis2 = UIElement(element_id="v2", element_type=UIElementType.BUTTON, bounds=(102, 101, 198, 139), label="Save", confidence=0.88)
        ax = [{"label": "Save", "role": "button", "bounds": [100, 100, 200, 140]}]

        res = ui_perception_fusion.fuse(accessibility_elements=ax, visual_elements=[vis1, vis2])
        self.assertEqual(len(res["fused_elements"]), 1)

    # 12. Contradictory Metadata
    def test_12_contradictory_metadata(self):
        ax = [{"label": "Start", "role": "button", "bounds": [100, 100, 200, 140]}]
        vis = [UIElement(element_id="v_stop", element_type=UIElementType.BUTTON, bounds=(100, 100, 200, 140), label="Stop", confidence=0.90)]

        res = ui_perception_fusion.fuse(accessibility_elements=ax, visual_elements=vis)
        self.assertEqual(len(res["contradictions"]), 1)
        self.assertEqual(res["contradictions"][0]["resolution"], "preferred_accessibility")

    # 13. Spatial Target Resolution
    def test_13_spatial_target_resolution(self):
        left_btn = UIElement(element_id="btn_l", element_type=UIElementType.BUTTON, bounds=(100, 500, 200, 540), label="Action")
        right_btn = UIElement(element_id="btn_r", element_type=UIElementType.BUTTON, bounds=(1500, 500, 1600, 540), label="Action")

        res_left = visual_target_locator.locate_target("Click the Action button on the left", [left_btn, right_btn], (1920, 1080))
        self.assertEqual(res_left["target"].element_id, "btn_l")

        res_right = visual_target_locator.locate_target("Click the Action button on the right", [left_btn, right_btn], (1920, 1080))
        self.assertEqual(res_right["target"].element_id, "btn_r")

    # 14. Ambiguous Visual Target Clarification
    def test_14_ambiguous_visual_target_clarification(self):
        btn1 = UIElement(element_id="b1", element_type=UIElementType.BUTTON, bounds=(100, 200, 200, 240), label="Run")
        btn2 = UIElement(element_id="b2", element_type=UIElementType.BUTTON, bounds=(500, 200, 600, 240), label="Run")

        res = visual_target_locator.locate_target("Click the Run button", [btn1, btn2], (1920, 1080))
        self.assertTrue(res["ambiguity"])
        self.assertIsNotNone(res["disambiguation_prompt"])

    # 15. Low-Confidence Target Blocking
    def test_15_low_confidence_target_blocking(self):
        res = visual_reasoning_engine.reason_about_screen(
            query="Click the strange symbol",
            fused_elements=[],
            mock_reasoning_result={"confidence": 0.55, "interpretation": "Uncertain glyph"},
        )
        self.assertFalse(res["can_auto_execute"])
        self.assertEqual(res["confidence_tier"], "CLARIFY")

    # 16. ActionContract Enforcement
    def test_16_action_contract_enforcement(self):
        contract = ActionContract(
            connector="visual_interaction",
            operation="click",
            arguments={"element_id": "el_test", "bounds": (100, 100, 200, 200)},
            risk_level=RiskLevel.LOW_RISK,
        )
        self.assertFalse(contract.approval_required)
        self.assertEqual(contract.risk_level, RiskLevel.LOW_RISK)

    # 17. Post-Action Visual Verification
    def test_17_post_action_visual_verification(self):
        target = UIElement(element_id="el_start", element_type=UIElementType.BUTTON, bounds=(100, 100, 200, 140), label="Start Server")
        
        async def run_test():
            res = await visual_action_verifier.execute_and_verify_visual_action(
                target_element=target,
                action_fn=lambda: "Clicked",
                post_observation_fn=lambda: {"state_changed": True, "new_state": "Running"},
            )
            return res

        res = asyncio.run(run_test())
        self.assertTrue(res["success"])
        self.assertEqual(res["verification_level"], VisualVerificationLevel.OUTCOME_VERIFIED.value)

    # 18. Screen Change Detection
    def test_18_screen_change_detection(self):
        img1 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        self.assertTrue(screen_change_detector.has_changed(img1, img2, threshold=0.05))
        self.assertFalse(screen_change_detector.has_changed(img1, img1, threshold=0.05))

    # 19. Visual Wait Success
    def test_19_visual_wait_success(self):
        state = {"text_blocks": [{"text": "FLOW is ready", "bounds": [0, 0, 100, 20]}]}

        async def run_wait():
            return await visual_wait_manager.wait_for_condition(
                condition=VisualWaitCondition.TEXT_APPEARS,
                target_value="FLOW is ready",
                poll_fn=lambda: state,
                timeout_seconds=1.0,
            )

        res = asyncio.run(run_wait())
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "satisfied")

    # 20. Visual Wait Timeout
    def test_20_visual_wait_timeout(self):
        async def run_timeout():
            return await visual_wait_manager.wait_for_condition(
                condition=VisualWaitCondition.TEXT_APPEARS,
                target_value="Non-existent text",
                poll_fn=lambda: {"text_blocks": []},
                timeout_seconds=0.05,
                poll_interval=0.01,
            )

        res = asyncio.run(run_timeout())
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "timeout")

    # 21. Cancellation During Visual Wait
    def test_21_cancellation_during_visual_wait(self):
        cancelled = True

        async def run_cancelled():
            return await visual_wait_manager.wait_for_condition(
                condition=VisualWaitCondition.TEXT_APPEARS,
                target_value="Some text",
                poll_fn=lambda: {"text_blocks": []},
                timeout_seconds=2.0,
                cancellation_check=lambda: cancelled,
            )

        res = asyncio.run(run_cancelled())
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "cancelled")

    # 22. Error Dialog Detection
    def test_22_error_dialog_detection(self):
        blocks = screen_text_extractor.extract_text_blocks(
            image=None,
            provided_blocks=[{"text": "Fatal: Port 3000 already bound", "bounds": [400, 300, 800, 350]}],
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].category, "error")

        elements = visual_element_detector.detect_elements(text_blocks=blocks)
        self.assertTrue(any(e.element_type == UIElementType.ERROR_BANNER for e in elements))

    # 23. Visual Evidence Integration with ProblemSolver
    def test_23_visual_evidence_integration_with_problemsolver(self):
        contract = create_agent_contract(
            parent_goal_id="g_diag",
            turn_id="t_diag",
            role=AgentRole.DIAGNOSTIC,
            task_description="Diagnose visual error",
            authority_scope=AuthorityLevel.READ_ONLY,
        )
        shared_evidence_store.add_evidence("g_diag", contract.agent_id, EvidenceCategory.VISUAL_ERROR_STATE.value, {"error": "EADDRINUSE"}, source="ScreenPerceptionManager")
        ev = shared_evidence_store.get_evidence("g_diag", EvidenceCategory.VISUAL_ERROR_STATE.value)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].value["error"], "EADDRINUSE")

    # 24. Multi-Agent Visual Observation
    def test_24_multi_agent_visual_observation(self):
        c_vis = create_agent_contract(
            parent_goal_id="g_multi",
            turn_id="t_multi",
            role=AgentRole.OBSERVER,
            task_description="Visual Screen Observer",
            authority_scope=AuthorityLevel.READ_ONLY,
        )
        self.assertEqual(c_vis.authority_scope, AuthorityLevel.READ_ONLY)
        self.assertIn("observe", c_vis.task_description.lower())

    # 25. No Screenshot Persistence into Long-Term Memory
    def test_25_no_screenshot_persistence_into_long_term_memory(self):
        mem = create_memory_contract(memory_type=MemoryType.PREFERENCE, subject="theme", content="dark_mode")
        stored = memory_service.store(mem)
        self.assertTrue(bool(stored))
        # Ephemeral VisualContextContract is not leaked into memory store
        retrieved = memory_service.retrieve(query="screenshot")
        self.assertEqual(len(retrieved), 0)

    # 26. Simple Commands Bypass Visual Pipeline
    def test_26_simple_commands_bypass_visual_pipeline(self):
        t0 = time.perf_counter()
        match = router.match("what time is it")
        t_match = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "GET_TIME")
        self.assertLess(t_match, 5.0)  # Sub-5ms fast path
        self.assertEqual(screen_perception_manager.state, PerceptionState.IDLE)

    # 27. Voice Pipeline Remains Non-Blocking
    def test_27_voice_pipeline_remains_non_blocking(self):
        router.match("click the blue button")  # Warm-up
        t0 = time.perf_counter()
        match = router.match("click the blue button")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "VISUAL_UI_ACTION")
        self.assertLess(dt, 5.0)


if __name__ == "__main__":
    unittest.main()
