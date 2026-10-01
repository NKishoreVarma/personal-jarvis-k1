"""
Agent Delegation Engine for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Decomposes complex goals into specialized subagents:
Observer -> (Research) -> Diagnostic -> Executor -> Verifier.
Enforces dependency ordering, resource limits, and role authority boundaries.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.agent_contract import (
    AgentContract,
    AgentRole,
    AuthorityLevel,
    create_agent_contract,
)
from core.agent_lifecycle_manager import agent_lifecycle_manager
from core.agent_resource_manager import agent_resource_manager


class AgentDelegationEngine:
    """
    Decomposes goals into specialized multi-agent delegation pipelines.
    """

    def __init__(self):
        self.delegation_enabled: bool = True

    def set_delegation_enabled(self, enabled: bool) -> None:
        self.delegation_enabled = enabled

    def create_delegation_plan(
        self,
        goal: str,
        project_id: str,
        turn_id: str = "t1",
        needs_research: bool = False,
    ) -> Tuple[List[AgentContract], str]:
        """
        Constructs a specialized multi-agent delegation plan for the goal.
        """
        if not self.delegation_enabled:
            return [], "Multi-agent delegation is disabled by user preference."

        goal_id = f"g_{uuid.uuid4().hex[:8]}"
        agents: List[AgentContract] = []

        # 1. Observer Agent (Inspects ports, processes, logs)
        can_spawn, reason = agent_resource_manager.can_spawn_agent(goal_id, spawn_depth=1)
        if not can_spawn:
            return [], reason

        observer = create_agent_contract(
            parent_goal_id=goal_id,
            turn_id=turn_id,
            role=AgentRole.OBSERVER,
            task_description=f"Inspect processes, open ports, and logs for {project_id}.",
            authority_scope=AuthorityLevel.READ_ONLY,
            allowed_operations=["inspect_port", "read_logs", "check_process"],
            priority=8,
            spawn_depth=1,
            metadata={"project_id": project_id},
        )
        agent_resource_manager.allocate_agent(goal_id)
        agent_lifecycle_manager.register_agent(observer)
        agents.append(observer)

        prev_deps = [observer.agent_id]

        # 2. Research Agent (Optional, if knowledge gap exists)
        if needs_research:
            researcher = create_agent_contract(
                parent_goal_id=goal_id,
                turn_id=turn_id,
                role=AgentRole.RESEARCHER,
                task_description=f"Retrieve official documentation for {project_id} configuration.",
                authority_scope=AuthorityLevel.READ_ONLY,
                allowed_operations=["search_documentation", "query_knowledge"],
                priority=6,
                spawn_depth=1,
                metadata={"project_id": project_id},
            )
            agent_resource_manager.allocate_agent(goal_id)
            agent_lifecycle_manager.register_agent(researcher)
            agents.append(researcher)
            prev_deps.append(researcher.agent_id)

        # 3. Diagnostic Agent (Determines root cause)
        diagnostic = create_agent_contract(
            parent_goal_id=goal_id,
            turn_id=turn_id,
            role=AgentRole.DIAGNOSTIC,
            task_description=f"Isolate root cause from observed evidence for {project_id}.",
            authority_scope=AuthorityLevel.READ_ONLY,
            allowed_operations=["analyze_error", "corroborate_evidence"],
            dependencies=list(prev_deps),
            priority=7,
            spawn_depth=1,
            metadata={"project_id": project_id},
        )
        agent_resource_manager.allocate_agent(goal_id)
        agent_lifecycle_manager.register_agent(diagnostic)
        agents.append(diagnostic)

        # 4. Executor Agent (Applies repair)
        executor = create_agent_contract(
            parent_goal_id=goal_id,
            turn_id=turn_id,
            role=AgentRole.EXECUTOR,
            task_description=f"Apply approved repair actions for {project_id}.",
            authority_scope=AuthorityLevel.EXECUTE_LOW_RISK,
            allowed_operations=["kill_process", "restart_service", "apply_patch"],
            dependencies=[diagnostic.agent_id],
            priority=9,
            spawn_depth=1,
            metadata={"project_id": project_id},
        )
        agent_resource_manager.allocate_agent(goal_id)
        agent_lifecycle_manager.register_agent(executor)
        agents.append(executor)

        # 5. Verifier Agent (Independently verifies live outcome)
        verifier = create_agent_contract(
            parent_goal_id=goal_id,
            turn_id=turn_id,
            role=AgentRole.VERIFIER,
            task_description=f"Independently probe live {project_id} service responsiveness.",
            authority_scope=AuthorityLevel.READ_ONLY,
            allowed_operations=["probe_http", "check_port_responsiveness"],
            dependencies=[executor.agent_id],
            priority=10,
            spawn_depth=1,
            metadata={"project_id": project_id},
        )
        agent_resource_manager.allocate_agent(goal_id)
        agent_lifecycle_manager.register_agent(verifier)
        agents.append(verifier)

        return agents, "Delegation plan generated successfully."


# Global singleton instance
agent_delegation_engine = AgentDelegationEngine()
