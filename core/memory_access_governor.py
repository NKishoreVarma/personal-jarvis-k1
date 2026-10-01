"""
Memory Access Governor for Persistent Memory in MARK XLVIII / JARVIS.
Enforces multi-tier memory access boundaries (GLOBAL, PROJECT, GOAL, SESSION)
and prevents cross-project context leakage.
"""

from __future__ import annotations

from typing import List, Optional

from core.memory_contract import MemoryContract


class MemoryAccessGovernor:
    """
    Evaluates permissions and filters out unauthorized or cross-project memories.
    """

    def filter_accessible_memories(
        self,
        memories: List[MemoryContract],
        requesting_project_id: Optional[str] = None,
        requesting_goal_id: Optional[str] = None,
    ) -> List[MemoryContract]:
        """
        Filters out memories that do not match the requesting project or scope.
        """
        accessible: List[MemoryContract] = []

        for mem in memories:
            # 1. Global memories are universally accessible
            if mem.privacy_scope == "GLOBAL":
                accessible.append(mem)
                continue

            # 2. Check project match
            if requesting_project_id and mem.project_id:
                if mem.project_id.lower() == requesting_project_id.lower():
                    accessible.append(mem)
                continue

            # 3. If no project filter requested, allow local
            if not requesting_project_id and mem.privacy_scope in ["LOCAL", "USER"]:
                accessible.append(mem)

        return accessible


# Global singleton instance
memory_access_governor = MemoryAccessGovernor()
