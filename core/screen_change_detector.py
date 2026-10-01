"""
Screen Change Detector for MARK XLVIII / JARVIS.
Detects meaningful visual and structural screen changes (dialog appearance,
window transitions, loading state resolution, error popups) while suppressing redundant re-analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageChops, ImageStat

from core.visual_context_contract import UIElement, UIElementType


class ScreenChangeDetector:
    """
    Computes visual delta metrics between successive screen frames and identifies semantic UI transitions.
    """

    def compute_difference_score(self, prev_image: Optional[Image.Image], curr_image: Optional[Image.Image]) -> float:
        """
        Calculates pixel difference ratio between 0.0 (identical) and 1.0 (completely distinct).
        """
        if prev_image is None or curr_image is None:
            return 1.0

        if prev_image.size != curr_image.size:
            return 1.0

        try:
            # Downsample for fast comparison
            small_prev = prev_image.resize((128, 72)).convert("L")
            small_curr = curr_image.resize((128, 72)).convert("L")

            diff = ImageChops.difference(small_prev, small_curr)
            stat = ImageStat.Stat(diff)
            # Average pixel difference normalized to 0..1
            avg_diff = stat.mean[0] / 255.0
            return avg_diff
        except Exception:
            return 0.5

    def has_changed(
        self,
        prev_image: Optional[Image.Image],
        curr_image: Optional[Image.Image],
        threshold: float = 0.02,
    ) -> bool:
        """Returns True if visual difference exceeds threshold."""
        return self.compute_difference_score(prev_image, curr_image) >= threshold

    def detect_semantic_change(
        self,
        prev_elements: List[UIElement],
        curr_elements: List[UIElement],
    ) -> Dict[str, Any]:
        """
        Detects specific UI event transitions between element lists.
        """
        prev_labels = {e.label.lower() for e in prev_elements if e.label}
        curr_labels = {e.label.lower() for e in curr_elements if e.label}

        new_labels = curr_labels - prev_labels
        removed_labels = prev_labels - curr_labels

        new_types = {e.element_type for e in curr_elements} - {e.element_type for e in prev_elements}

        change_type = "NO_CHANGE"
        if UIElementType.DIALOG in new_types or any("popup" in l or "modal" in l for l in new_labels):
            change_type = "DIALOG_APPEARED"
        elif UIElementType.ERROR_BANNER in new_types or any("error" in l or "fail" in l for l in new_labels):
            change_type = "ERROR_APPEARED"
        elif UIElementType.LOADING_INDICATOR in {e.element_type for e in prev_elements} and UIElementType.LOADING_INDICATOR not in {e.element_type for e in curr_elements}:
            change_type = "LOADING_FINISHED"
        elif len(new_labels) > 0 or len(removed_labels) > 0:
            change_type = "CONTENT_UPDATED"

        return {
            "has_changed": change_type != "NO_CHANGE",
            "change_type": change_type,
            "new_labels": list(new_labels),
            "removed_labels": list(removed_labels),
        }


# Global singleton instance
screen_change_detector = ScreenChangeDetector()
