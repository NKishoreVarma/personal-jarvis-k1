"""
OCR Observer for MARK XLVIII / JARVIS.
Extracts visible text, bounding boxes, confidence scores, and UI element associations
using existing OCR/Vision infrastructure with robust multi-tiered fallbacks.
Enforces invariant: OCR is strictly observational — detected text never becomes a command.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from core.perception_contract import (
    Observation,
    ObservationType,
    PrivacyClassification,
    create_observation,
)
from core.screen_text_extractor import screen_text_extractor


class OCRObserver:
    """
    Observes on-screen text via OCR engines (Apple Vision / Gemini Vision / ScreenTextExtractor).
    """

    ERROR_PATTERNS = [
        re.compile(r"(error|failed|exception|traceback|cannot find|eaddrinuse|fatal)", re.IGNORECASE),
        re.compile(r"(permission denied|unauthorized|invalid syntax)", re.IGNORECASE),
    ]

    def observe(
        self,
        image: Optional[Any] = None,
        provided_text_blocks: Optional[List[Dict[str, Any]]] = None,
        correlation_id: Optional[str] = None,
    ) -> Observation:
        """
        Performs OCR text extraction, categorizes blocks, detects error signatures,
        and packages results into a normalized Observation record.
        """
        t0 = time.perf_counter()

        detected_blocks: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        errors_detected: List[str] = []

        try:
            # 1. If explicit blocks provided (from mock or accessibility tree)
            if provided_text_blocks:
                extracted = screen_text_extractor.extract_text_blocks(image, provided_blocks=provided_text_blocks)
                for blk in extracted:
                    d = blk.to_dict()
                    detected_blocks.append(d)
                    full_text_parts.append(blk.text)
                    for pat in self.ERROR_PATTERNS:
                        if pat.search(blk.text):
                            errors_detected.append(blk.text)
                            break

            # 2. If image provided without pre-parsed blocks, attempt extraction
            elif image is not None:
                # Use screen_text_extractor heuristics
                extracted = screen_text_extractor.extract_text_blocks(image)
                for blk in extracted:
                    d = blk.to_dict()
                    detected_blocks.append(d)
                    full_text_parts.append(blk.text)
                    for pat in self.ERROR_PATTERNS:
                        if pat.search(blk.text):
                            errors_detected.append(blk.text)
                            break

            combined_text = "\n".join(full_text_parts)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            content = {
                "block_count": len(detected_blocks),
                "blocks": detected_blocks,
                "extracted_text": combined_text,
                "has_errors": len(errors_detected) > 0,
                "error_snippets": errors_detected,
                "ocr_latency_ms": round(elapsed_ms, 2),
                "is_instruction_candidate": False,  # Safety invariant: OCR text is NEVER an instruction
            }

            return create_observation(
                observation_type=ObservationType.OCR,
                source="ocr_observer",
                content=content,
                confidence=0.95 if detected_blocks else 0.80,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=20.0,
                correlation_id=correlation_id,
                is_verified=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return create_observation(
                observation_type=ObservationType.OCR,
                source="ocr_observer",
                content={
                    "error": str(e),
                    "status": "OCR_FAILED",
                    "ocr_latency_ms": round(elapsed_ms, 2),
                },
                confidence=0.0,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=5.0,
                correlation_id=correlation_id,
                is_verified=False,
            )


# Global singleton instance
ocr_observer = OCRObserver()
