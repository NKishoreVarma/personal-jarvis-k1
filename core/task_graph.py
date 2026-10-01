"""
Task Graph for Autonomous Multi-Agent Orchestration in MARK XLVIII / JARVIS.
Represents directed task dependencies, parallel and sequential execution branches,
failure propagation, and cooperative cancellation trees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from core.agent_contract import AgentRole, AgentStatus


class NodeExecutionType(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATING = "MUTATING"


@dataclass
class TaskNode:
    node_id: str
    name: str
    agent_role: AgentRole
    operation: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    execution_type: NodeExecutionType = NodeExecutionType.READ_ONLY
    status: AgentStatus = AgentStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # Predecessor node IDs
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def is_mutating(self) -> bool:
        return self.execution_type == NodeExecutionType.MUTATING


@dataclass
class TaskEdge:
    from_node: str
    to_node: str
    condition: str = "ON_SUCCESS"  # ON_SUCCESS, ON_FAILURE, ALWAYS


class TaskGraph:
    """
    Directed Acyclic Graph (DAG) for multi-agent task execution and dependency tracking.
    """

    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        self.nodes: Dict[str, TaskNode] = {}
        self.edges: List[TaskEdge] = []

    def add_node(self, node: TaskNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, from_node: str, to_node: str, condition: str = "ON_SUCCESS") -> None:
        self.edges.append(TaskEdge(from_node=from_node, to_node=to_node, condition=condition))
        if to_node in self.nodes and from_node not in self.nodes[to_node].dependencies:
            self.nodes[to_node].dependencies.append(from_node)

    def get_ready_nodes(self) -> List[TaskNode]:
        """
        Returns all PENDING nodes whose prerequisite dependencies have COMPLETED successfully.
        """
        ready: List[TaskNode] = []
        for node in self.nodes.values():
            if node.status != AgentStatus.PENDING:
                continue

            # Check if all dependencies are satisfied
            deps_satisfied = True
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status != AgentStatus.COMPLETED:
                    deps_satisfied = False
                    break

            if deps_satisfied:
                ready.append(node)

        return ready

    def propagate_failure(self, failed_node_id: str, reason: str = "") -> List[str]:
        """
        Recursively marks downstream dependent nodes as FAILED or CANCELLED.
        """
        if failed_node_id in self.nodes:
            self.nodes[failed_node_id].status = AgentStatus.FAILED
            self.nodes[failed_node_id].error = reason

        affected: List[str] = [failed_node_id]
        queue = [failed_node_id]

        while queue:
            curr = queue.pop(0)
            for edge in self.edges:
                if edge.from_node == curr:
                    child = self.nodes.get(edge.to_node)
                    if child and child.status in (AgentStatus.PENDING, AgentStatus.WAITING):
                        child.status = AgentStatus.FAILED
                        child.error = f"Prerequisite {curr} failed: {reason}"
                        affected.append(child.node_id)
                        queue.append(child.node_id)

        return affected

    def propagate_cancellation(self, reason: str = "Parent goal cancelled") -> List[str]:
        """
        Cancels all pending, running, or waiting nodes in the graph.
        """
        cancelled_nodes: List[str] = []
        for node in self.nodes.values():
            if node.status in (AgentStatus.PENDING, AgentStatus.WAITING, AgentStatus.RUNNING, AgentStatus.READY):
                node.status = AgentStatus.CANCELLED
                node.error = reason
                cancelled_nodes.append(node.node_id)
        return cancelled_nodes

    def is_completed(self) -> bool:
        """Returns True if all nodes are in terminal states (COMPLETED, FAILED, CANCELLED)."""
        terminal_states = {AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED, AgentStatus.TIMEOUT}
        return all(node.status in terminal_states for node in self.nodes.values())

    def has_failures(self) -> bool:
        return any(node.status in (AgentStatus.FAILED, AgentStatus.CANCELLED, AgentStatus.TIMEOUT) for node in self.nodes.values())
