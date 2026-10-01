"""
Interaction Style Manager for Human Collaboration in MARK XLVIII / JARVIS.
Dynamically adapts conversational verbosity, technical depth, and response tone.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class InteractionStyle(str, Enum):
    CONCISE = "CONCISE"
    STANDARD = "STANDARD"
    DETAILED = "DETAILED"
    TECHNICAL = "TECHNICAL"
    SILENT_BACKGROUND = "SILENT_BACKGROUND"


class InteractionStyleManager:
    """
    Manages active communication mode and applies formatting rules accordingly.
    """

    def __init__(self):
        self.active_style: InteractionStyle = InteractionStyle.STANDARD

    def set_style(self, style: InteractionStyle) -> None:
        self.active_style = style

    def format_response(self, text: str) -> str:
        if self.active_style == InteractionStyle.CONCISE:
            # Return first sentence or brief summary
            sentences = text.strip().split(". ")
            return sentences[0] if len(sentences) == 1 else f"{sentences[0]}."
        elif self.active_style == InteractionStyle.SILENT_BACKGROUND:
            return ""
        return text


# Global singleton instance
interaction_style_manager = InteractionStyleManager()
