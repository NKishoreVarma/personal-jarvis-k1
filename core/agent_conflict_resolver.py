"""
Agent Conflict Resolver for MARK XLVIII / JARVIS.
Detects concurrent mutating operations, dependency collisions, and resource contention,
resolving them via serialization, priority preemption, or replanning.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Tuple

from core.task_graph import TaskNode


class ConflictResolutionAction(str, Enum):
    SERIALIZE = "SERIALIZE"
    CANCEL_LOWER_PRIORITY = "CANCEL_LOWER_PRIORITY"
    REQUIRE_REPLAN = "REQUIRE_REPLAN"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    ALLOW = "ALLOW"


class AgentConflictResolver:
    """
    Evaluates and arbitrates multi-agent operational conflicts.
    """

    def detect_conflicts(self, ready_nodes: List[TaskNode]) -> List[Dict[str, Any]]:
        """
        Detects if multiple ready nodes intend to perform concurrent mutations on identical targets.
        """
        conflicts: List[Dict[str, Any]] = []
        mutating_nodes = [n for n in ready_nodes if n.is_mutating]

        if len(mutating_nodes) <= 1:
            return conflicts

        # Group by target
        target_map: Dict[str, List[TaskNode]] = {}
        for n in mutating_nodes:
            target = n.arguments.get("target") or n.arguments.get("project") or "global"
            target_map.setdefault(str(target).lower(), []).append(n)

        for target, nodes in target_map.items():
            if len(nodes) > 1:
                conflicts.append({
                    "target": target,
                    "nodes": nodes,
                    "reason": f"Multiple concurrent mutating operations on target '{target}'.",
                })

        return conflicts

    def resolve_mutating_conflict(self, conflict: Dict[str, Any]) -> Tuple[ConflictResolutionAction, List[TaskNode]]:
        """
        Resolves mutating collision by enforcing strict serialization.
        Returns (action, ordered_nodes).
        """
        nodes: List[TaskNode] = conflict.get("nodes", [])
        # Sort by priority (higher first)
        ordered = sorted(nodes, key=lambda x: getattr(x, "priority", 5), reverse=True)
        return ConflictResolutionAction.SERIALIZE, ordered


# Global singleton instance
agent_conflict_resolver = AgentConflictResolver()
