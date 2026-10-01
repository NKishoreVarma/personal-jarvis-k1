"""
Capability Graph for Autonomous Capability Evolution in MARK XLVIII / JARVIS.
Maintains directed acyclic graphs of skills, child compositions, and dependencies,
strictly preventing recursive cycles (A -> B -> C -> A).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


class CapabilityGraph:
    """
    Directed Acyclic Graph (DAG) for skill dependencies and compositions.
    """

    def __init__(self):
        self._adj: Dict[str, Set[str]] = {}  # parent -> set of children

    def add_node(self, skill_id: str) -> None:
        if skill_id not in self._adj:
            self._adj[skill_id] = set()

    def add_dependency(self, parent_id: str, child_id: str) -> Tuple[bool, str]:
        """
        Adds dependency parent -> child. Rejects if a cycle would be introduced.
        """
        self.add_node(parent_id)
        self.add_node(child_id)

        if parent_id == child_id:
            return False, "Rejected: Self-referential dependency creates cycle."

        # Check if adding parent -> child introduces a cycle (i.e. child can already reach parent)
        if self._has_path(child_id, parent_id):
            return False, f"Rejected: Cycle detected ({parent_id} -> {child_id} -> ... -> {parent_id})."

        self._adj[parent_id].add(child_id)
        return True, "Dependency added successfully."

    def _has_path(self, start: str, target: str, visited: Optional[Set[str]] = None) -> bool:
        if start == target:
            return True
        if visited is None:
            visited = set()
        visited.add(start)

        for neighbor in self._adj.get(start, set()):
            if neighbor not in visited:
                if self._has_path(neighbor, target, visited):
                    return True
        return False

    def get_dependencies(self, skill_id: str) -> List[str]:
        return list(self._adj.get(skill_id, set()))

    def clear_all(self) -> None:
        self._adj.clear()


# Global singleton instance
capability_graph = CapabilityGraph()
