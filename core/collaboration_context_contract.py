"""
Collaboration Context Contract for Human Collaboration in MARK XLVIII / JARVIS.
Tracks active project focus, current long-horizon goals, open decisions, and recent corrections.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CollaborationContextContract:
    context_id: str
    user_id: str = "default_user"
    active_goal: str = ""
    active_project: str = ""
    current_workflow: str = ""
    user_preference_set: Dict[str, Any] = field(default_factory=dict)
    open_decisions: List[str] = field(default_factory=list)
    pending_approvals: List[str] = field(default_factory=list)
    recent_corrections: List[Dict[str, Any]] = field(default_factory=list)
    last_updated_at: float = field(default_factory=time.time)

    def record_correction(self, original: str, corrected: str) -> None:
        self.recent_corrections.append({
            "original": original,
            "corrected": corrected,
            "timestamp": time.time(),
        })
        self.last_updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "user_id": self.user_id,
            "active_goal": self.active_goal,
            "active_project": self.active_project,
            "current_workflow": self.current_workflow,
            "user_preference_set": self.user_preference_set,
            "open_decisions": self.open_decisions,
            "pending_approvals": self.pending_approvals,
            "recent_corrections": self.recent_corrections,
            "last_updated_at": self.last_updated_at,
        }


def create_collaboration_context(
    active_goal: str = "",
    active_project: str = "",
    current_workflow: str = "",
    user_id: str = "default_user",
) -> CollaborationContextContract:
    return CollaborationContextContract(
        context_id=f"ctx_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        active_goal=active_goal,
        active_project=active_project,
        current_workflow=current_workflow,
    )
