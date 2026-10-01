"""
Dependency Scheduler for MARK XLVIII / JARVIS.
Traverses TaskGraphs, scheduling independent read-only operations concurrently
while serializing mutating operations and enforcing prerequisite dependencies.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional

from core.agent_conflict_resolver import ConflictResolutionAction, agent_conflict_resolver
from core.agent_contract import AgentStatus
from core.task_graph import NodeExecutionType, TaskGraph, TaskNode


class DependencyScheduler:
    """
    Executes a TaskGraph respecting concurrency boundaries and prerequisite contracts.
    """

    async def execute_graph_async(
        self,
        graph: TaskGraph,
        node_executor: Callable[[TaskNode], Coroutine[Any, Any, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Runs the DAG to completion or failure.
        """
        while not graph.is_completed():
            ready_nodes = graph.get_ready_nodes()
            if not ready_nodes:
                # If no ready nodes and graph is not completed, we might have a dead end or active running nodes
                running_nodes = [n for n in graph.nodes.values() if n.status == AgentStatus.RUNNING]
                if not running_nodes:
                    # Stalled DAG
                    break
                await asyncio.sleep(0.05)
                continue

            # Separate read-only vs mutating nodes
            read_only_nodes = [n for n in ready_nodes if not n.is_mutating]
            mutating_nodes = [n for n in ready_nodes if n.is_mutating]

            # 1. Dispatch all ready read-only nodes concurrently
            tasks = []
            for r_node in read_only_nodes:
                r_node.status = AgentStatus.RUNNING
                tasks.append(self._run_node_wrapper(graph, r_node, node_executor))

            # 2. Check for conflicts on mutating nodes and serialize them
            if mutating_nodes:
                conflicts = agent_conflict_resolver.detect_conflicts(mutating_nodes)
                if conflicts:
                    _, ordered_mutating = agent_conflict_resolver.resolve_mutating_conflict(conflicts[0])
                    # Run the first mutating node only (serialize)
                    target_node = ordered_mutating[0]
                    target_node.status = AgentStatus.RUNNING
                    tasks.append(self._run_node_wrapper(graph, target_node, node_executor))
                else:
                    for m_node in mutating_nodes:
                        m_node.status = AgentStatus.RUNNING
                        tasks.append(self._run_node_wrapper(graph, m_node, node_executor))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            await asyncio.sleep(0.02)

        return {
            "completed": graph.is_completed(),
            "has_failures": graph.has_failures(),
            "graph_id": graph.graph_id,
        }

    async def _run_node_wrapper(
        self,
        graph: TaskGraph,
        node: TaskNode,
        node_executor: Callable[[TaskNode], Coroutine[Any, Any, Dict[str, Any]]],
    ) -> None:
        try:
            res = await node_executor(node)
            if res.get("success", False):
                node.status = AgentStatus.COMPLETED
                node.result = res
            else:
                node.status = AgentStatus.FAILED
                node.error = res.get("error", "Unknown execution error")
                graph.propagate_failure(node.node_id, reason=node.error)
        except Exception as e:
            node.status = AgentStatus.FAILED
            node.error = str(e)
            graph.propagate_failure(node.node_id, reason=str(e))


# Global singleton instance
dependency_scheduler = DependencyScheduler()
