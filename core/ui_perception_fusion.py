"""
UI Perception Fusion Engine for MARK XLVIII / JARVIS.
Fuses Accessibility tree metadata, WindowManager geometry, OCR text, and Visual UI detections.
Enforces Accessibility-First priority, deduplicates overlapping targets, and flags visual contradictions.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.visual_context_contract import DetectedTextBlock, UIElement, UIElementType


def _boxes_overlap(b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int], threshold: float = 0.3) -> bool:
    """Calculates Intersection-over-Union (IoU) or spatial proximity."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter_area = inter_w * inter_h

    if inter_area == 0:
        return False

    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union_area = area1 + area2 - inter_area

    iou = inter_area / union_area if union_area > 0 else 0
    return iou >= threshold or inter_area / min(area1, area2) >= 0.5


class UIPerceptionFusion:
    """
    Combines accessibility, OCR, and vision into a unified, high-confidence perceptual map.
    """

    def fuse(
        self,
        accessibility_elements: Optional[List[Dict[str, Any]]] = None,
        window_metadata: Optional[Dict[str, Any]] = None,
        ocr_blocks: Optional[List[DetectedTextBlock]] = None,
        visual_elements: Optional[List[UIElement]] = None,
    ) -> Dict[str, Any]:
        """
        Executes hierarchical perception fusion.
        Returns:
            - fused_elements: List[UIElement]
            - contradictions: List[Dict[str, Any]]
            - primary_source: str
        """
        fused: List[UIElement] = []
        contradictions: List[Dict[str, Any]] = []

        # 1. Ingest Accessibility Elements (Priority #1)
        if accessibility_elements:
            for ax in accessibility_elements:
                lbl = ax.get("label") or ax.get("title") or ax.get("name") or ""
                role = ax.get("role", "button").upper()
                try:
                    el_type = UIElementType[role]
                except KeyError:
                    el_type = UIElementType.BUTTON if "button" in role.lower() else UIElementType.UNKNOWN

                bounds = tuple(ax.get("bounds", [0, 0, 100, 40]))
                conf = ax.get("confidence", 0.98)

                fused.append(UIElement(
                    element_id=f"ax_{uuid.uuid4().hex[:8]}",
                    element_type=el_type,
                    bounds=bounds,
                    label=lbl,
                    confidence=conf,
                    interaction_hint=ax.get("hint", "click"),
                    source="accessibility",
                    metadata=ax,
                ))

        # 2. Ingest Visual Elements (Priority #4) & Cross-Match
        if visual_elements:
            for vis in visual_elements:
                # Check for match / overlap with existing fused elements
                matched_ax = None
                for ax_el in fused:
                    if _boxes_overlap(vis.bounds, ax_el.bounds) or (vis.label and ax_el.label and vis.label.lower() == ax_el.label.lower()):
                        matched_ax = ax_el
                        break

                if matched_ax:
                    # Check for label contradiction
                    if vis.label and matched_ax.label and vis.label.lower() != matched_ax.label.lower():
                        contradictions.append({
                            "accessibility_label": matched_ax.label,
                            "visual_label": vis.label,
                            "bounds": matched_ax.bounds,
                            "resolution": "preferred_accessibility",
                        })
                    # Boost confidence when multiple sources agree
                    matched_ax.confidence = min(0.99, matched_ax.confidence + 0.05)
                    matched_ax.metadata["visual_corroborated"] = True
                else:
                    # Standalone visual element
                    fused.append(vis)

        # 3. Correlate with OCR Blocks (Priority #3)
        if ocr_blocks:
            for block in ocr_blocks:
                matched = False
                for el in fused:
                    if _boxes_overlap(block.bounds, el.bounds) or (el.label and block.text and block.text.lower() in el.label.lower()):
                        matched = True
                        if not el.label:
                            el.label = block.text
                        el.confidence = min(0.99, el.confidence + 0.02)
                        break
                if not matched and block.category in ["error", "button_label"]:
                    # Add as distinct element if not already represented
                    fused.append(UIElement(
                        element_id=f"ocr_{uuid.uuid4().hex[:8]}",
                        element_type=UIElementType.ERROR_BANNER if block.category == "error" else UIElementType.BUTTON,
                        bounds=block.bounds,
                        label=block.text,
                        confidence=block.confidence,
                        interaction_hint="inspect" if block.category == "error" else "click",
                        source="ocr",
                    ))

        return {
            "fused_elements": fused,
            "contradictions": contradictions,
            "element_count": len(fused),
            "window_metadata": window_metadata or {},
        }


# Global singleton instance
ui_perception_fusion = UIPerceptionFusion()
