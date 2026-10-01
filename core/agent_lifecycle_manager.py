"""
Agent Lifecycle Manager for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Tracks formal lifecycle states and transition telemetry for specialized subagents.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from core.agent_contract import AgentContract, AgentStatus


class AgentLifecycleManager:
    """
    Manages state transitions and historical lifecycles for multi-agent workflows.
    """

    def __init__(self):
        self._active_agents: Dict[str, AgentContract] = {}
        self._history: Dict[str, List[AgentContract]] = {}

    def register_agent(self, agent: AgentContract) -> None:
        self._active_agents[agent.agent_id] = agent
        self._history.setdefault(agent.parent_goal_id, []).append(agent)

    def transition_state(self, agent_id: str, new_status: AgentStatus) -> bool:
        agent = self._active_agents.get(agent_id)
        if not agent:
            return False
        agent.status = new_status
        if new_status == AgentStatus.RUNNING and not agent.started_at:
            agent.started_at = time.time()
        elif new_status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED, AgentStatus.TIMEOUT]:
            agent.completed_at = time.time()
        return True

    def get_agent(self, agent_id: str) -> Optional[AgentContract]:
        return self._active_agents.get(agent_id)

    def get_agents_for_goal(self, goal_id: str) -> List[AgentContract]:
        return self._history.get(goal_id, [])

    def clear(self) -> None:
        self._active_agents.clear()
        self._history.clear()


# Global singleton instance
agent_lifecycle_manager = AgentLifecycleManager()
