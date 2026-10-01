"""
ThinkTool — Reasoning Scratchpad for MARK XLVIII.
Enables structured, bounded chain-of-thought planning notes without external side effects.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ThinkResult:
    """Result of a ThinkTool reasoning step."""
    success: bool
    note: str
    category: str
    timestamp: float = field(default_factory=time.monotonic)


class ThinkTool:
    """
    In-memory reasoning scratchpad for active agent runs.
    Enforces maximum note length and history bounds, providing zero-latency scratchpad execution.
    """

    MAX_NOTE_LENGTH: int = 500
    MAX_HISTORY: int = 50
    ALLOWED_CATEGORIES: set[str] = {"planning", "observation", "recovery", "verification"}

    def __init__(self):
        self._history: List[ThinkResult] = []

    def think(self, note: str, category: str = "planning") -> ThinkResult:
        """
        Record a concise reasoning or planning note.
        Does not execute external actions.
        """
        clean_category = category.lower().strip()
        if clean_category not in self.ALLOWED_CATEGORIES:
            clean_category = "planning"

        # Enforce maximum note length
        clean_note = (note or "").strip()
        if len(clean_note) > self.MAX_NOTE_LENGTH:
            clean_note = clean_note[: self.MAX_NOTE_LENGTH] + "..."

        result = ThinkResult(
            success=True,
            note=clean_note,
            category=clean_category,
            timestamp=time.monotonic(),
        )

        self._history.append(result)
        if len(self._history) > self.MAX_HISTORY:
            self._history.pop(0)

        print(f"[THINK] [{clean_category.upper()}] {clean_note}")
        return result

    def get_history(self, category: Optional[str] = None) -> List[ThinkResult]:
        """Retrieve recent reasoning history, optionally filtered by category."""
        if category:
            cat = category.lower().strip()
            return [r for r in self._history if r.category == cat]
        return list(self._history)

    def get_latest(self) -> Optional[ThinkResult]:
        """Return the most recent reasoning note."""
        return self._history[-1] if self._history else None

    def clear(self) -> None:
        """Clear reasoning history for the active agent run."""
        self._history.clear()


# Global singleton instance for easy import
think_tool = ThinkTool()


def think(note: str, category: str = "planning", **kwargs: Any) -> Dict[str, Any]:
    """
    Tool function callable by the Agent Orchestrator ToolRegistry.
    """
    res = think_tool.think(note=note, category=category)
    return {
        "success": res.success,
        "note": res.note,
        "category": res.category,
        "timestamp": res.timestamp,
    }
