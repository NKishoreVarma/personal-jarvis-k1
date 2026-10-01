"""
Parallel Worker Manager for MARK XLVIII / JARVIS.
Coordinates bounded parallel worker execution, priority scheduling, worker timeout enforcement,
and cooperative cancellation propagation.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional

from core.agent_contract import AgentContract, AgentStatus


class ParallelWorkerManager:
    """
    Manages bounded worker execution pools and cancellation lifecycles.
    """

    def __init__(self, max_parallel_workers: int = 4):
        self.max_parallel_workers = max_parallel_workers
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._worker_contracts: Dict[str, AgentContract] = {}
        self._cancellation_events: Dict[str, asyncio.Event] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_parallel_workers)
        return self._semaphore

    async def run_worker_async(
        self,
        contract: AgentContract,
        worker_coro: Coroutine[Any, Any, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Executes a worker coroutine under concurrency bounds and timeout limits.
        """
        sem = self._get_semaphore()
        cancel_evt = asyncio.Event()
        self._cancellation_events[contract.agent_id] = cancel_evt
        self._worker_contracts[contract.agent_id] = contract

        contract.mark_started()

        try:
            async with sem:
                # Check if already cancelled
                if cancel_evt.is_set() or contract.status == AgentStatus.CANCELLED:
                    return {"success": False, "error": "Worker cancelled prior to launch", "agent_id": contract.agent_id}

                # Run with timeout enforcement
                result = await asyncio.wait_for(worker_coro, timeout=contract.timeout_seconds)
                contract.mark_completed(result)
                return result

        except asyncio.TimeoutError:
            contract.status = AgentStatus.TIMEOUT
            contract.error_message = f"Worker timed out after {contract.timeout_seconds}s"
            return {"success": False, "error": contract.error_message, "agent_id": contract.agent_id}
        except asyncio.CancelledError:
            contract.mark_cancelled("Worker task cancelled")
            return {"success": False, "error": "Worker cancelled", "agent_id": contract.agent_id}
        except Exception as e:
            contract.mark_failed(str(e))
            return {"success": False, "error": str(e), "agent_id": contract.agent_id}
        finally:
            self._cancellation_events.pop(contract.agent_id, None)
            self._active_tasks.pop(contract.agent_id, None)

    def cancel_worker(self, agent_id: str, reason: str = "Worker cancelled") -> bool:
        """Signals cancellation to an active worker."""
        evt = self._cancellation_events.get(agent_id)
        if evt:
            evt.set()

        task = self._active_tasks.get(agent_id)
        if task and not task.done():
            task.cancel()

        contract = self._worker_contracts.get(agent_id)
        if contract and contract.status in (AgentStatus.PENDING, AgentStatus.RUNNING, AgentStatus.WAITING):
            contract.mark_cancelled(reason)
            return True
        return False

    def cancel_all_for_goal(self, goal_id: str, reason: str = "Parent goal cancelled") -> List[str]:
        """Cancels all active workers associated with a parent goal."""
        cancelled = []
        for aid, contract in list(self._worker_contracts.items()):
            if contract.parent_goal_id == goal_id:
                if self.cancel_worker(aid, reason=reason):
                    cancelled.append(aid)
        return cancelled

    def get_active_worker_count(self) -> int:
        return len(self._cancellation_events)

    def clear(self) -> None:
        self._active_tasks.clear()
        self._worker_contracts.clear()
        self._cancellation_events.clear()


# Global singleton instance
parallel_worker_manager = ParallelWorkerManager()
