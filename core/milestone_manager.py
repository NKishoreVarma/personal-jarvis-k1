"""
Milestone Manager for MARK XLVIII / JARVIS.
Tracks key execution milestones and formats human-like progress announcements
while enforcing strict silence budgets (no micro-step narration).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MilestoneType(str, Enum):
    PROJECT_FOUND = "PROJECT_FOUND"
    DIAGNOSIS_COMPLETE = "DIAGNOSIS_COMPLETE"
    REPAIR_APPLIED = "REPAIR_APPLIED"
    SERVER_STARTED = "SERVER_STARTED"
    SERVER_REACHABLE = "SERVER_REACHABLE"
    APPLICATION_OPENED = "APPLICATION_OPENED"
    GOAL_COMPLETED = "GOAL_COMPLETED"
    GOAL_FAILED = "GOAL_FAILED"


@dataclass
class Milestone:
    milestone_id: str
    goal_id: str
    milestone_type: MilestoneType
    description: str
    timestamp: float = field(default_factory=time.time)
    announced: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "goal_id": self.goal_id,
            "milestone_type": self.milestone_type.value,
            "description": self.description,
            "timestamp": self.timestamp,
            "announced": self.announced,
        }


class MilestoneManager:
    """
    Manages goal milestones and applies bounded voice announcement policies.
    """

    def __init__(self):
        self._milestones: Dict[str, List[Milestone]] = {}  # goal_id -> list of Milestones
        self._progress_announced_count: Dict[str, int] = {}  # goal_id -> count

    def record_milestone(
        self,
        goal_id: str,
        milestone_type: MilestoneType,
        description: str,
    ) -> Milestone:
        """Records a meaningful operational milestone."""
        m = Milestone(
            milestone_id=f"mile_{uuid.uuid4().hex[:6]}",
            goal_id=goal_id,
            milestone_type=milestone_type,
            description=description,
        )
        if goal_id not in self._milestones:
            self._milestones[goal_id] = []
        self._milestones[goal_id].append(m)
        return m

    def should_announce_progress(self, goal_id: str, elapsed_seconds: float) -> Tuple[bool, Optional[str]]:
        """
        Determines if an intermediate progress update is allowed (max 1 per long-running goal).
        """
        count = self._progress_announced_count.get(goal_id, 0)
        if count >= 1:
            return False, None

        # Only announce if task runs longer than 4.0s
        if elapsed_seconds > 4.0:
            self._progress_announced_count[goal_id] = count + 1
            return True, "Still working on FLOW."

        return False, None

    def get_latest_milestone(self, goal_id: str) -> Optional[Milestone]:
        ms = self._milestones.get(goal_id, [])
        return ms[-1] if ms else None

    def format_final_announcement(self, goal_id: str, project_name: str = "FLOW", success: bool = True) -> str:
        """Formats the concise final verified voice outcome."""
        if success:
            return f"{project_name} is running and verified."
        return f"Could not complete {project_name}."

    def clear_goal(self, goal_id: str) -> None:
        self._milestones.pop(goal_id, None)
        self._progress_announced_count.pop(goal_id, None)

    def clear_all(self) -> None:
        self._milestones.clear()
        self._progress_announced_count.clear()


# Global singleton instance
milestone_manager = MilestoneManager()
