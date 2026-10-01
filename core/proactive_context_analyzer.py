"""
Proactive Context Analyzer for Proactive Task Orchestration in MARK XLVIII / JARVIS.
Synthesizes active collaboration context, multi-session goal progress, and recent project completions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.collaboration_context_contract import CollaborationContextContract
from core.long_horizon_goal_manager import long_horizon_goal_manager


class ProactiveContextAnalyzer:
    """
    Analyzes active execution trajectory and determines what logically follows next.
    """

    def analyze_operational_context(
        self,
        context: CollaborationContextContract,
    ) -> Dict[str, Any]:
        """
        Determines current focus, latest completed milestone, and recommended next action.
        """
        active_goals = long_horizon_goal_manager.list_active_goals()
        next_milestone = None
        for g in active_goals:
            for m in g.milestones:
                if not m.completed:
                    next_milestone = m.name
                    break
            if next_milestone:
                break

        return {
            "active_project": context.active_project or "JARVIS",
            "active_goal": context.active_goal,
            "next_logical_milestone": next_milestone,
            "has_open_decisions": len(context.open_decisions) > 0,
            "has_pending_approvals": len(context.pending_approvals) > 0,
        }


# Global singleton instance
proactive_context_analyzer = ProactiveContextAnalyzer()
