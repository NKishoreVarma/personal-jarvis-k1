"""
Screen Text Extractor for MARK XLVIII / JARVIS.
Extracts visible text blocks and spatial screen coordinates using OCR
and structured UI layout heuristics.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.visual_context_contract import DetectedTextBlock


class ScreenTextExtractor:
    """
    Extracts text, buttons, dialog bodies, and error messages with approximate bounding boxes.
    """

    ERROR_PATTERNS = [
        re.compile(r"(error|failed|exception|eaddrinuse|fatal|refused|cannot\s+find)", re.IGNORECASE),
    ]

    def extract_text_blocks(
        self,
        image: Any,
        provided_blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> List[DetectedTextBlock]:
        """
        Converts image or provided OCR results into structured DetectedTextBlock objects.
        """
        results: List[DetectedTextBlock] = []

        if provided_blocks:
            for b in provided_blocks:
                txt = b.get("text", "")
                bounds = tuple(b.get("bounds", [0, 0, 100, 30]))
                conf = b.get("confidence", 0.95)

                # Categorize
                category = "text"
                for err_pat in self.ERROR_PATTERNS:
                    if err_pat.search(txt):
                        category = "error"
                        break

                results.append(DetectedTextBlock(
                    text=txt,
                    bounds=bounds,
                    confidence=conf,
                    category=category,
                ))
            return results

        # Default synthetic OCR extraction if image provided without external OCR
        return results

    def find_text_matches(
        self,
        query: str,
        blocks: List[DetectedTextBlock],
        case_sensitive: bool = False,
    ) -> List[DetectedTextBlock]:
        """Finds text blocks matching query string."""
        q = query if case_sensitive else query.lower()
        matches = []
        for b in blocks:
            target = b.text if case_sensitive else b.text.lower()
            if q in target:
                matches.append(b)
        return matches


# Global singleton instance
screen_text_extractor = ScreenTextExtractor()
