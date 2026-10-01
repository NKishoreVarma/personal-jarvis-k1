"""
Long Horizon Goal Manager for Human Collaboration in MARK XLVIII / JARVIS.
Tracks multi-session overarching initiatives and milestone progression.
Enforces invariant: Active User Goal > Historical Long-Term Goal.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Milestone:
    milestone_id: str
    name: str
    completed: bool = False
    completed_at: Optional[float] = None


@dataclass
class LongHorizonGoal:
    goal_id: str
    title: str
    description: str
    milestones: List[Milestone] = field(default_factory=list)
    active: bool = True
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class LongHorizonGoalManager:
    """
    Manages long-horizon objectives spanning multiple user turns and sessions.
    """

    def __init__(self):
        self._goals: Dict[str, LongHorizonGoal] = {}

    def register_goal(self, title: str, description: str, milestone_names: List[str]) -> LongHorizonGoal:
        goal_id = f"lhg_{uuid.uuid4().hex[:8]}"
        milestones = [
            Milestone(milestone_id=f"m_{i}", name=name)
            for i, name in enumerate(milestone_names)
        ]
        goal = LongHorizonGoal(
            goal_id=goal_id,
            title=title,
            description=description,
            milestones=milestones,
        )
        self._goals[goal_id] = goal
        return goal

    def mark_milestone_completed(self, goal_id: str, milestone_name: str) -> bool:
        goal = self._goals.get(goal_id)
        if not goal:
            return False
        for m in goal.milestones:
            if m.name.lower() == milestone_name.lower():
                m.completed = True
                m.completed_at = time.time()
                return True
        return False

    def list_active_goals(self) -> List[LongHorizonGoal]:
        return [g for g in self._goals.values() if g.active]

    def clear(self) -> None:
        self._goals.clear()


# Global singleton instance
long_horizon_goal_manager = LongHorizonGoalManager()
