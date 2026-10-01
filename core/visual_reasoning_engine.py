"""
Visual Reasoning Engine for MARK XLVIII / JARVIS.
Provides multimodal reasoning fallback for custom/canvas interfaces, dynamic errors,
or unlabeled controls when deterministic accessibility and OCR are insufficient.
Enforces strict confidence tiers and never blindly executes low-confidence visual guesses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.visual_context_contract import UIElement, UIElementType


class VisualReasoningEngine:
    """
    Multimodal reasoning fallback applying strict confidence thresholds.
    """

    CONFIDENCE_EXECUTE_THRESHOLD = 0.90
    CONFIDENCE_VERIFY_THRESHOLD = 0.70

    def reason_about_screen(
        self,
        query: str,
        fused_elements: List[UIElement],
        screen_metadata: Optional[Dict[str, Any]] = None,
        mock_reasoning_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes visual reasoning interpretation and assigns confidence tiers.
        """
        if mock_reasoning_result:
            conf = mock_reasoning_result.get("confidence", 0.85)
            tier = "EXECUTE" if conf >= self.CONFIDENCE_EXECUTE_THRESHOLD else ("VERIFY" if conf >= self.CONFIDENCE_VERIFY_THRESHOLD else "CLARIFY")
            return {
                "interpretation": mock_reasoning_result.get("interpretation", "Screen analyzed"),
                "candidate_targets": mock_reasoning_result.get("candidate_targets", []),
                "confidence": conf,
                "uncertainty": 1.0 - conf,
                "confidence_tier": tier,
                "recommended_action": mock_reasoning_result.get("recommended_action", "observe"),
                "can_auto_execute": conf >= self.CONFIDENCE_EXECUTE_THRESHOLD,
            }

        # Dynamic fallback analysis
        q_lower = query.lower()
        matching = [e for e in fused_elements if any(word in e.label.lower() for word in q_lower.split() if len(word) > 2)]
        
        if matching:
            top_el = matching[0]
            conf = top_el.confidence
            tier = "EXECUTE" if conf >= self.CONFIDENCE_EXECUTE_THRESHOLD else ("VERIFY" if conf >= self.CONFIDENCE_VERIFY_THRESHOLD else "CLARIFY")
            return {
                "interpretation": f"Found matching element '{top_el.label}' ({top_el.element_type.value})",
                "candidate_targets": [top_el.to_dict()],
                "confidence": conf,
                "uncertainty": 1.0 - conf,
                "confidence_tier": tier,
                "recommended_action": top_el.interaction_hint,
                "can_auto_execute": conf >= self.CONFIDENCE_EXECUTE_THRESHOLD,
            }

        return {
            "interpretation": f"No definitive visual element identified for '{query}'",
            "candidate_targets": [],
            "confidence": 0.50,
            "uncertainty": 0.50,
            "confidence_tier": "CLARIFY",
            "recommended_action": "clarify",
            "can_auto_execute": False,
        }


# Global singleton instance
visual_reasoning_engine = VisualReasoningEngine()
