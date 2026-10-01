"""
Visual UI Element Detector for MARK XLVIII / JARVIS.
Detects interactive controls, buttons, text fields, dialogs, close buttons,
error banners, and loading indicators from screen buffers.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.visual_context_contract import DetectedTextBlock, UIElement, UIElementType


class VisualElementDetector:
    """
    Detects UI elements and pairs visual geometry with detected text labels.
    """

    def detect_elements(
        self,
        image: Any = None,
        text_blocks: Optional[List[DetectedTextBlock]] = None,
        provided_elements: Optional[List[Dict[str, Any]]] = None,
    ) -> List[UIElement]:
        """
        Extracts UI elements from visual geometry and OCR text.
        """
        elements: List[UIElement] = []

        # 1. Ingest provided/detected elements
        if provided_elements:
            for item in provided_elements:
                raw_type = item.get("type", "UNKNOWN").upper()
                try:
                    el_type = UIElementType[raw_type]
                except KeyError:
                    el_type = UIElementType.UNKNOWN

                bounds = tuple(item.get("bounds", [0, 0, 100, 40]))
                lbl = item.get("label", "")
                conf = item.get("confidence", 0.90)
                hint = item.get("interaction_hint", "click")

                elements.append(UIElement(
                    element_id=f"el_{uuid.uuid4().hex[:8]}",
                    element_type=el_type,
                    bounds=bounds,
                    label=lbl,
                    confidence=conf,
                    interaction_hint=hint,
                    source="visual_detector",
                    metadata=item.get("metadata", {}),
                ))

        # 2. Correlate with text blocks (e.g. create button elements for prominent button labels)
        if text_blocks:
            for block in text_blocks:
                # If block looks like a button label and isn't already covered
                if block.category == "button_label" or any(w in block.text.lower() for w in ["start", "run", "stop", "close", "ok", "cancel", "submit", "save"]):
                    # Check if already in elements
                    exists = any(e.label.lower() == block.text.lower() for e in elements)
                    if not exists:
                        elements.append(UIElement(
                            element_id=f"el_{uuid.uuid4().hex[:8]}",
                            element_type=UIElementType.BUTTON,
                            bounds=block.bounds,
                            label=block.text,
                            confidence=block.confidence,
                            interaction_hint="click",
                            source="ocr_derived",
                        ))
                elif block.category == "error":
                    elements.append(UIElement(
                        element_id=f"el_{uuid.uuid4().hex[:8]}",
                        element_type=UIElementType.ERROR_BANNER,
                        bounds=block.bounds,
                        label=block.text,
                        confidence=block.confidence,
                        interaction_hint="inspect",
                        source="ocr_derived",
                    ))

        return elements


# Global singleton instance
visual_element_detector = VisualElementDetector()
