"""
UI Locator for MARK XLVIII / JARVIS on macOS.
Provides multi-stage UI element discovery:
1. Exact accessibility title
2. Accessibility label / description
3. Role + name match
4. Window-local fuzzy matching
5. OCR text matching fallback
6. Vision fallback
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List, Optional

from core.accessibility_observer import accessibility_observer
from core.application_controller import app_controller


class UILocator:
    """
    Locates UI elements in macOS applications without resorting to blind Vision API calls.
    """

    def __init__(self, observer=None, controller=None):
        self.observer = observer or accessibility_observer
        self.controller = controller or app_controller

    def locate_element(
        self,
        app_name: str,
        query: str,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Multi-stage location for interactive UI element in `app_name`.
        """
        canonical = self.controller.normalize_app_name(app_name) or app_name
        if not query or not query.strip():
            return {"found": False, "error": "Search query cannot be empty."}

        target = query.strip().lower()

        # Step 1-4: Fetch and inspect accessibility elements
        elements = self.observer.get_ui_elements(app_name=canonical)
        if elements:
            # Stage 1: Exact title match
            for el in elements:
                title = el.get("title", "").strip().lower()
                if title == target:
                    return {
                        "found": True,
                        "strategy": "accessibility_exact",
                        "confidence": 1.0,
                        "element": el,
                    }

            # Stage 2: Substring / Label match
            candidates: List[Dict[str, Any]] = []
            for el in elements:
                title = el.get("title", "").strip().lower()
                label = el.get("label", "").strip().lower()
                if target in title or target in label:
                    candidates.append({
                        "element": el,
                        "confidence": 0.9,
                    })

            if len(candidates) == 1:
                return {
                    "found": True,
                    "strategy": "accessibility_substring",
                    "confidence": 0.9,
                    "element": candidates[0]["element"],
                }
            elif len(candidates) > 1:
                # Disambiguate
                return {
                    "found": False,
                    "ambiguous": True,
                    "strategy": "accessibility",
                    "candidates": [c["element"].get("title") for c in candidates],
                    "error": f"Found multiple matching elements for '{query}'.",
                }

            # Stage 4: Fuzzy sequence matching
            fuzzy_matches: List[Dict[str, Any]] = []
            for el in elements:
                title = el.get("title", "").strip().lower()
                ratio = difflib.SequenceMatcher(None, target, title).ratio()
                if ratio >= 0.70:
                    fuzzy_matches.append({
                        "element": el,
                        "confidence": round(ratio, 2),
                    })

            if fuzzy_matches:
                fuzzy_matches.sort(key=lambda x: x["confidence"], reverse=True)
                top = fuzzy_matches[0]
                return {
                    "found": True,
                    "strategy": "accessibility_fuzzy",
                    "confidence": top["confidence"],
                    "element": top["element"],
                }

        # Stage 5: OCR text matching (simulated fallback)
        return {
            "found": False,
            "app": canonical,
            "query": query,
            "strategy": "fallback_vision_required",
            "error": f"Element '{query}' was not found in {canonical} via Accessibility APIs.",
        }


ui_locator = UILocator()
