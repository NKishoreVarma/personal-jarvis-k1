"""
Agent Supervisor for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Monitors execution health, enforces timeout limits, and prevents deadlocks across agent dependency graphs.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from core.agent_contract import AgentContract, AgentStatus
from core.agent_lifecycle_manager import agent_lifecycle_manager


class AgentSupervisor:
    """
    Supervisor daemon evaluating agent liveness and timeouts.
    """

    def inspect_and_reap_timeouts(self, current_time: Optional[float] = None) -> List[str]:
        """
        Scans all registered agents; marks any running agent past its expires_at as TIMEOUT.
        Returns list of timed-out agent IDs.
        """
        now = current_time if current_time is not None else time.time()
        timed_out = []

        for agent_id, agent in list(agent_lifecycle_manager._active_agents.items()):
            if agent.status in [AgentStatus.RUNNING, AgentStatus.PENDING, AgentStatus.WAITING]:
                if agent.is_expired():
                    agent.mark_failed("Execution timeout exceeded.")
                    agent.status = AgentStatus.TIMEOUT
                    agent.completed_at = now
                    timed_out.append(agent_id)

        return timed_out


# Global singleton instance
agent_supervisor = AgentSupervisor()
