"""
Screen Perception Manager for MARK XLVIII / JARVIS.
Central coordinator managing on-demand screenshot acquisition, OCR extraction,
visual element detection, UI perception fusion, and turn-bound lifecycle management.
Enforces Accessibility-First priority and expires stale visual observations.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from actions.screen_capture import screen_capture_service
from core.screen_change_detector import screen_change_detector
from core.screen_text_extractor import screen_text_extractor
from core.ui_perception_fusion import ui_perception_fusion
from core.visual_context_contract import (
    UIElement,
    VisualContextContract,
    VisualVerificationState,
    create_visual_context_contract,
)
from core.visual_element_detector import visual_element_detector
from core.visual_reasoning_engine import visual_reasoning_engine
from core.visual_target_locator import visual_target_locator


class PerceptionState(str, Enum):
    IDLE = "IDLE"
    CAPTURING = "CAPTURING"
    ANALYZING = "ANALYZING"
    VISUAL_CONTEXT_READY = "VISUAL_CONTEXT_READY"
    STALE = "STALE"
    FAILED = "FAILED"


class ScreenPerceptionManager:
    """
    Coordinates visual capture, perception fusion, and spatial targeting with strict turn isolation.
    """

    def __init__(self):
        self.state: PerceptionState = PerceptionState.IDLE
        self._active_contexts: Dict[str, VisualContextContract] = {}  # turn_id -> context
        self._last_image = None

    def get_context(self, turn_id: str) -> Optional[VisualContextContract]:
        """Retrieves active visual context if not expired."""
        ctx = self._active_contexts.get(turn_id)
        if ctx:
            if ctx.is_expired():
                ctx.verification_state = VisualVerificationState.STALE
                self.state = PerceptionState.STALE
                return None
            return ctx
        return None

    def clear_context(self, turn_id: str) -> None:
        """Cleans up turn visual context immediately."""
        self._active_contexts.pop(turn_id, None)
        self.state = PerceptionState.IDLE

    async def perceive_screen_async(
        self,
        turn_id: str,
        goal_id: str,
        accessibility_elements: Optional[List[Dict[str, Any]]] = None,
        provided_ocr_blocks: Optional[List[Dict[str, Any]]] = None,
        provided_visual_elements: Optional[List[Dict[str, Any]]] = None,
        force_fresh: bool = False,
    ) -> VisualContextContract:
        """
        Gathers visual context, running capture and fusion asynchronously.
        """
        # Check cache if not forcing fresh
        existing = self.get_context(turn_id)
        if existing and not force_fresh:
            return existing

        self.state = PerceptionState.CAPTURING
        # 1. Capture screen
        cap_res = screen_capture_service.capture_full_screen()
        img = cap_res.get("image")
        self._last_image = img

        self.state = PerceptionState.ANALYZING
        # 2. Extract OCR
        ocr_blocks = screen_text_extractor.extract_text_blocks(img, provided_blocks=provided_ocr_blocks)

        # 3. Detect visual elements
        vis_elements = visual_element_detector.detect_elements(img, text_blocks=ocr_blocks, provided_elements=provided_visual_elements)

        # 4. Perception Fusion
        fusion_res = ui_perception_fusion.fuse(
            accessibility_elements=accessibility_elements,
            ocr_blocks=ocr_blocks,
            visual_elements=vis_elements,
        )
        fused_elements: List[UIElement] = fusion_res["fused_elements"]

        # 5. Build Contract
        contract = create_visual_context_contract(
            turn_id=turn_id,
            goal_id=goal_id,
            source_window=cap_res.get("metadata", {}).get("active_window_title", "Desktop"),
            ui_elements=fused_elements,
            detected_text=ocr_blocks,
            ttl_seconds=15.0,
            screen_dimensions=(cap_res.get("metadata", {}).get("width", 1920), cap_res.get("metadata", {}).get("height", 1080)),
        )

        self._active_contexts[turn_id] = contract
        self.state = PerceptionState.VISUAL_CONTEXT_READY
        return contract

    def locate_visual_target(
        self,
        turn_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """Locates visual target within turn visual context."""
        ctx = self.get_context(turn_id)
        if not ctx:
            return {"target": None, "error": "Visual context not available or expired"}

        return visual_target_locator.locate_target(query, ctx.ui_elements, ctx.screen_dimensions)


# Global singleton instance
screen_perception_manager = ScreenPerceptionManager()
