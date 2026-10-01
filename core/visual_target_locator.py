"""
Visual Target Locator for MARK XLVIII / JARVIS.
Resolves natural language spatial and semantic target requests into precise screen coordinates
using fused UI elements, relative geometry, and spatial reasoning.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from core.visual_context_contract import UIElement, UIElementType


class VisualTargetLocator:
    """
    Locates interactive UI elements on screen given natural language instructions and spatial descriptors.
    """

    SPATIAL_KEYWORDS = {
        "left": lambda el, dim: el.center[0] < dim[0] // 2,
        "right": lambda el, dim: el.center[0] >= dim[0] // 2,
        "top": lambda el, dim: el.center[1] < dim[1] // 3,
        "bottom": lambda el, dim: el.center[1] >= (dim[1] * 2) // 3,
        "center": lambda el, dim: (dim[0] // 4 <= el.center[0] <= 3 * dim[0] // 4) and (dim[1] // 4 <= el.center[1] <= 3 * dim[1] // 4),
    }

    def locate_target(
        self,
        query: str,
        elements: List[UIElement],
        screen_dimensions: Tuple[int, int] = (1920, 1080),
    ) -> Dict[str, Any]:
        """
        Resolves query to candidate UIElement.
        Returns:
            - target: Optional[UIElement]
            - candidates: List[UIElement]
            - confidence: float
            - ambiguity: bool
            - disambiguation_prompt: Optional[str]
        """
        q = query.lower().strip()
        candidates: List[UIElement] = list(elements)

        # 1. Filter by specific element type if mentioned
        if "button" in q:
            btn_matches = [e for e in candidates if e.element_type in [UIElementType.BUTTON, UIElementType.CLOSE_BUTTON]]
            if btn_matches:
                candidates = btn_matches
        elif "popup" in q or "dialog" in q or "modal" in q:
            dialog_matches = [e for e in candidates if e.element_type in [UIElementType.DIALOG, UIElementType.CLOSE_BUTTON]]
            if dialog_matches:
                candidates = dialog_matches
        elif "error" in q:
            err_matches = [e for e in candidates if e.element_type == UIElementType.ERROR_BANNER or "error" in e.label.lower()]
            if err_matches:
                candidates = err_matches

        # 2. Filter by label / text match
        # Extract quoted text or words
        clean_words = [w for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", q) if w not in ["click", "press", "open", "close", "the", "button", "on", "to", "that", "this", "select", "next"]]
        
        label_filtered = []
        for word in clean_words:
            matched = [e for e in candidates if word in e.label.lower()]
            if matched:
                label_filtered.extend(matched)

        if label_filtered:
            # Deduplicate preserving order
            seen_ids = set()
            unique_filtered = []
            for e in label_filtered:
                if e.element_id not in seen_ids:
                    seen_ids.add(e.element_id)
                    unique_filtered.append(e)
            candidates = unique_filtered

        # 3. Spatial filtering (left, right, top, bottom, center)
        for keyword, pred in self.SPATIAL_KEYWORDS.items():
            if keyword in q:
                spat_filtered = [e for e in candidates if pred(e, screen_dimensions)]
                if spat_filtered:
                    candidates = spat_filtered

        # 4. Positional ordering (first, last)
        if "first" in q and candidates:
            # Sort top-to-bottom, left-to-right
            candidates = sorted(candidates, key=lambda e: (e.bounds[1], e.bounds[0]))
            candidates = [candidates[0]]
        elif "last" in q and candidates:
            candidates = sorted(candidates, key=lambda e: (e.bounds[1], e.bounds[0]))
            candidates = [candidates[-1]]

        # 5. Relative "next to <target>"
        if "next to" in q:
            match = re.search(r"next to\s+([a-zA-Z0-9_-]+)", q)
            if match:
                ref_label = match.group(1).lower()
                ref_elements = [e for e in elements if ref_label in e.label.lower()]
                if ref_elements:
                    ref_center = ref_elements[0].center
                    # Sort candidates by Euclidean distance to ref_center
                    candidates = [e for e in candidates if e.element_id != ref_elements[0].element_id]
                    candidates = sorted(candidates, key=lambda e: (e.center[0] - ref_center[0])**2 + (e.center[1] - ref_center[1])**2)

        # 6. Evaluation & Ambiguity Resolution
        if not candidates:
            return {
                "target": None,
                "candidates": [],
                "confidence": 0.0,
                "ambiguity": False,
                "disambiguation_prompt": f"I could not locate any matching visual target for '{query}'.",
            }

        if len(candidates) == 1:
            target = candidates[0]
            return {
                "target": target,
                "candidates": candidates,
                "confidence": target.confidence,
                "ambiguity": False,
                "disambiguation_prompt": None,
            }

        # Multiple candidates found
        # Check if identical confidence and ambiguous
        labels = [e.label or e.element_type.value for e in candidates[:3]]
        return {
            "target": candidates[0],  # Best candidate
            "candidates": candidates,
            "confidence": candidates[0].confidence * 0.8,  # Degrade slightly due to ambiguity
            "ambiguity": True,
            "disambiguation_prompt": f"I found multiple matching targets ({', '.join(labels)}). Which one would you like me to select?",
        }


# Global singleton instance
visual_target_locator = VisualTargetLocator()
