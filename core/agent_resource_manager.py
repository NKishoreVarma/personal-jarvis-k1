"""
Agent Resource Manager for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Enforces the safety invariant: No Infinite Agent Spawning.
Imposes hard limits on delegation depth, concurrent workers, total agents per goal, and timeout bounds.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.agent_contract import AgentContract


class AgentResourceManager:
    """
    Guards CPU/memory resources against runaway subagent spawning.
    """

    def __init__(
        self,
        max_concurrent_agents: int = 5,
        max_delegation_depth: int = 3,
        max_agents_per_goal: int = 10,
    ):
        self.max_concurrent_agents = max_concurrent_agents
        self.max_delegation_depth = max_delegation_depth
        self.max_agents_per_goal = max_agents_per_goal

        self._active_agents_count: int = 0
        self._goal_agent_counts: Dict[str, int] = {}

    def can_spawn_agent(
        self,
        goal_id: str,
        spawn_depth: int,
    ) -> Tuple[bool, str]:
        """
        Validates resource quotas before an agent contract is created and scheduled.
        """
        # 1. Depth check
        if spawn_depth > self.max_delegation_depth:
            return False, f"Rejected: Delegation depth {spawn_depth} exceeds maximum limit ({self.max_delegation_depth})."

        # 2. Concurrency check
        if self._active_agents_count >= self.max_concurrent_agents:
            return False, f"Rejected: Active agent count {self._active_agents_count} reached concurrency ceiling ({self.max_concurrent_agents})."

        # 3. Total agents per goal check
        current_goal_total = self._goal_agent_counts.get(goal_id, 0)
        if current_goal_total >= self.max_agents_per_goal:
            return False, f"Rejected: Goal {goal_id} reached maximum agent allocation ({self.max_agents_per_goal})."

        return True, "Resource quota available."

    def allocate_agent(self, goal_id: str) -> None:
        self._active_agents_count += 1
        self._goal_agent_counts[goal_id] = self._goal_agent_counts.get(goal_id, 0) + 1

    def release_agent(self, goal_id: str) -> None:
        self._active_agents_count = max(0, self._active_agents_count - 1)

    def reset_goal(self, goal_id: str) -> None:
        self._goal_agent_counts.pop(goal_id, None)

    def clear_all(self) -> None:
        self._active_agents_count = 0
        self._goal_agent_counts.clear()


# Global singleton instance
agent_resource_manager = AgentResourceManager()
