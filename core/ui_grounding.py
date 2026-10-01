"""
Semantic UI Grounding Layer for MARK XLVIII / JARVIS.
Detects visible UI elements on screen, computes display coordinates,
and enforces a strict confidence threshold (0.85) to prevent misclicks.
"""

from __future__ import annotations

import io
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from PIL import Image
from pydantic import BaseModel, Field

from core.computer_observer import computer_observer

UI_GROUNDING_MIN_CONFIDENCE: float = 0.85


class GroundingElementSchema(BaseModel):
    found: bool = Field(description="Whether the requested element was identified on screen")
    element: str = Field(description="Description of the element")
    box_2d: Optional[List[int]] = Field(
        default=None,
        description="Normalized bounding box [ymin, xmin, ymax, xmax] scaled 0 to 1000",
    )
    confidence: float = Field(default=0.0, description="Detection confidence score from 0.0 to 1.0")


@dataclass
class GroundingResult:
    found: bool
    element: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "element": self.element,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "error": self.error,
        }


class UIGrounding:
    """
    Identifies UI elements from screen captures and converts normalized bounding boxes
    to validated pixel coordinates.
    """

    def find_ui_element(self, element_description: str, image: Any = None) -> GroundingResult:
        """
        Locates a requested UI element on screen using Gemini Vision.
        Enforces UI_GROUNDING_MIN_CONFIDENCE (0.85) and screen coordinate bounds checking.
        """
        # 1. Capture screen if no image provided
        screen_w, screen_h = 1920, 1080
        if image is None:
            obs = computer_observer.observe_screen()
            if not obs.get("success") or not obs.get("image"):
                return GroundingResult(
                    found=False,
                    element=element_description,
                    error="Failed to capture screen for UI grounding.",
                )
            image = obs["image"]
            screen_w = obs["metadata"]["width"]
            screen_h = obs["metadata"]["height"]
        elif isinstance(image, Image.Image):
            screen_w, screen_h = image.size

        # 2. Query Gemini Vision with Grounding Schema
        try:
            from actions.web_search import _get_api_key
            api_key = _get_api_key()
            if not api_key:
                return GroundingResult(
                    found=False,
                    element=element_description,
                    error="API key unavailable for UI grounding.",
                )

            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            if isinstance(image, Image.Image):
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                img_bytes = buf.getvalue()
            elif isinstance(image, bytes):
                img_bytes = image
            else:
                img_bytes = str(image).encode()

            prompt = (
                f"You are the JARVIS UI Grounding Engine.\n"
                f"Target UI Element: '{element_description}'\n\n"
                f"Detect the target element on screen. Provide normalized bounding box [ymin, xmin, ymax, xmax] "
                f"scaled 0-1000 and a confidence score between 0.0 and 1.0."
            )

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GroundingElementSchema,
                ),
            )

            if not response or not response.text:
                return GroundingResult(
                    found=False,
                    element=element_description,
                    error="Empty response from vision grounding model.",
                )

            data = json.loads(response.text)
            parsed = GroundingElementSchema(**data)

            if not parsed.found or not parsed.box_2d or len(parsed.box_2d) != 4:
                return GroundingResult(
                    found=False,
                    element=element_description,
                    confidence=parsed.confidence,
                    error=f"Element '{element_description}' was not found on screen.",
                )

            # 3. Confidence Threshold Check
            if parsed.confidence < UI_GROUNDING_MIN_CONFIDENCE:
                return GroundingResult(
                    found=False,
                    element=element_description,
                    confidence=parsed.confidence,
                    error=(
                        f"I couldn't confidently identify '{element_description}' "
                        f"(confidence {parsed.confidence:.2f} < {UI_GROUNDING_MIN_CONFIDENCE})."
                    ),
                )

            # 4. Convert 0-1000 normalized coordinates to screen pixel coordinates
            ymin, xmin, ymax, xmax = parsed.box_2d
            px_xmin = int((xmin / 1000.0) * screen_w)
            px_xmax = int((xmax / 1000.0) * screen_w)
            px_ymin = int((ymin / 1000.0) * screen_h)
            px_ymax = int((ymax / 1000.0) * screen_h)

            center_x = (px_xmin + px_xmax) // 2
            center_y = (px_ymin + px_ymax) // 2
            elem_w = max(1, px_xmax - px_xmin)
            elem_h = max(1, px_ymax - px_ymin)

            # 5. Screen Bounds Check
            if not (0 <= center_x <= screen_w and 0 <= center_y <= screen_h):
                return GroundingResult(
                    found=False,
                    element=element_description,
                    confidence=parsed.confidence,
                    error=f"Computed coordinates ({center_x}, {center_y}) outside screen bounds ({screen_w}x{screen_h}).",
                )

            return GroundingResult(
                found=True,
                element=element_description,
                x=center_x,
                y=center_y,
                width=elem_w,
                height=elem_h,
                confidence=parsed.confidence,
            )

        except Exception as e:
            return GroundingResult(
                found=False,
                element=element_description,
                error=f"Grounding error: {e}",
            )


# Global singleton instance
ui_grounding = UIGrounding()
