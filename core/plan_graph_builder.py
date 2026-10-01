"""
Plan Graph Builder for MARK XLVIII / JARVIS.
Translates PlanStepContracts into an executable TaskGraph DAG,
mapping roles, isolating independent read-only tasks, and serializing mutating actions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.agent_contract import AgentRole, AgentStatus
from core.plan_contract import PlanContract
from core.plan_step_contract import PlanStepContract, PlanStepStatus
from core.task_graph import NodeExecutionType, TaskGraph, TaskNode


class PlanGraphBuilder:
    """
    Constructs a validated TaskGraph from a PlanContract and its PlanStepContracts.
    """

    def build_task_graph(
        self,
        plan: PlanContract,
        steps: List[PlanStepContract],
    ) -> TaskGraph:
        """
        Creates a TaskGraph preserving step dependencies, mutability flags, and agent roles.
        """
        graph = TaskGraph(graph_id=plan.goal_id)

        for step in steps:
            # Map action type to AgentRole & NodeExecutionType
            if step.action_type == "verify":
                role = AgentRole.VERIFIER
                exec_type = NodeExecutionType.READ_ONLY
            elif step.is_mutating:
                role = AgentRole.EXECUTOR
                exec_type = NodeExecutionType.MUTATING
            else:
                role = AgentRole.OBSERVER
                exec_type = NodeExecutionType.READ_ONLY

            node = TaskNode(
                node_id=step.step_id,
                name=step.title,
                agent_role=role,
                operation=step.objective,
                arguments=step.parameters,
                execution_type=exec_type,
                status=AgentStatus.PENDING,
                dependencies=list(step.dependencies),
            )
            graph.add_node(node)

        # Build edges from dependencies
        for step in steps:
            for dep_id in step.dependencies:
                graph.add_edge(from_node=dep_id, to_node=step.step_id, condition="ON_SUCCESS")

        return graph


# Global singleton instance
plan_graph_builder = PlanGraphBuilder()
