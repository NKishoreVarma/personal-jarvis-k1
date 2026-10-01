"""
Visual Context Contract for MARK XLVIII / JARVIS.
Defines formal schemas for visual screen observations, detected UI elements,
OCR text blocks, spatial bounding boxes, confidence scores, and strict verification lifecycles.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class VisualVerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    OBSERVED = "OBSERVED"
    CONFIRMED = "CONFIRMED"
    STALE = "STALE"
    CONTRADICTED = "CONTRADICTED"


class UIElementType(str, Enum):
    BUTTON = "BUTTON"
    TEXT_FIELD = "TEXT_FIELD"
    CHECKBOX = "CHECKBOX"
    DROPDOWN = "DROPDOWN"
    MENU = "MENU"
    TAB = "TAB"
    DIALOG = "DIALOG"
    ICON = "ICON"
    CLOSE_BUTTON = "CLOSE_BUTTON"
    ERROR_BANNER = "ERROR_BANNER"
    LOADING_INDICATOR = "LOADING_INDICATOR"
    LABEL = "LABEL"
    UNKNOWN = "UNKNOWN"


@dataclass
class UIElement:
    element_id: str
    element_type: UIElementType
    bounds: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    label: str = ""
    confidence: float = 0.90
    interaction_hint: str = "click"
    source: str = "visual_detector"  # accessibility, ocr, visual_detector, fusion
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "element_type": self.element_type.value,
            "bounds": list(self.bounds),
            "center": list(self.center),
            "label": self.label,
            "confidence": self.confidence,
            "interaction_hint": self.interaction_hint,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class DetectedTextBlock:
    text: str
    bounds: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float = 0.90
    category: str = "text"  # text, title, error, button_label, dialog_body

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bounds": list(self.bounds),
            "confidence": self.confidence,
            "category": self.category,
        }


@dataclass
class VisualContextContract:
    context_id: str
    turn_id: str
    goal_id: str
    screenshot_id: str
    source_window: str = ""
    captured_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 15.0)  # 15s TTL
    ui_elements: List[UIElement] = field(default_factory=list)
    detected_text: List[DetectedTextBlock] = field(default_factory=list)
    active_dialogs: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.95
    verification_state: VisualVerificationState = VisualVerificationState.OBSERVED
    screen_dimensions: Tuple[int, int] = (1920, 1080)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "turn_id": self.turn_id,
            "goal_id": self.goal_id,
            "screenshot_id": self.screenshot_id,
            "source_window": self.source_window,
            "captured_at": self.captured_at,
            "expires_at": self.expires_at,
            "ui_elements": [e.to_dict() for e in self.ui_elements],
            "detected_text": [t.to_dict() for t in self.detected_text],
            "active_dialogs": self.active_dialogs,
            "confidence": self.confidence,
            "verification_state": self.verification_state.value,
            "screen_dimensions": list(self.screen_dimensions),
            "is_expired": self.is_expired(),
        }


def create_visual_context_contract(
    turn_id: str,
    goal_id: str,
    source_window: str = "",
    ui_elements: Optional[List[UIElement]] = None,
    detected_text: Optional[List[DetectedTextBlock]] = None,
    ttl_seconds: float = 15.0,
    screen_dimensions: Tuple[int, int] = (1920, 1080),
) -> VisualContextContract:
    now = time.time()
    return VisualContextContract(
        context_id=f"vis_ctx_{uuid.uuid4().hex[:8]}",
        turn_id=turn_id,
        goal_id=goal_id,
        screenshot_id=f"scr_{uuid.uuid4().hex[:8]}",
        source_window=source_window,
        captured_at=now,
        expires_at=now + ttl_seconds,
        ui_elements=ui_elements or [],
        detected_text=detected_text or [],
        screen_dimensions=screen_dimensions,
    )
