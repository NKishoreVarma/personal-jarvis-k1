"""
Runtime Health Monitor for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Tracks runtime health status (HEALTHY, WATCH, DEGRADED, CRITICAL), checkpoint write errors,
worker failures, and recovery integrity.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.heartbeat_manager import heartbeat_manager
from core.runtime_contract import RuntimeStatus


class RuntimeHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class RuntimeHealthMonitor:
    """
    Evaluates real-time operational health of the agent runtime.
    """

    def __init__(self):
        self._checkpoint_errors: int = 0
        self._worker_errors: int = 0
        self._recovery_failures: int = 0

    def record_checkpoint_error(self) -> None:
        self._checkpoint_errors += 1

    def record_worker_error(self) -> None:
        self._worker_errors += 1

    def record_recovery_failure(self) -> None:
        self._recovery_failures += 1

    def evaluate_health(self) -> Tuple[RuntimeHealthState, str]:
        """
        Computes health rating and explanation.
        """
        # Critical if persistent storage / checkpointing has repeated failures
        if self._checkpoint_errors >= 3:
            return (
                RuntimeHealthState.CRITICAL,
                "Checkpoint storage is failing. Tasks may not survive restarts.",
            )

        if self._recovery_failures >= 2:
            return (
                RuntimeHealthState.DEGRADED,
                "Multiple recovery failures observed on startup.",
            )

        rt = heartbeat_manager.current_runtime
        if rt and rt.is_heartbeat_stale(15.0):
            return (
                RuntimeHealthState.DEGRADED,
                "Heartbeat is delayed or stalled.",
            )

        if self._checkpoint_errors > 0 or self._worker_errors > 0:
            return (
                RuntimeHealthState.WATCH,
                f"Operating with minor errors (checkpoints: {self._checkpoint_errors}, workers: {self._worker_errors}).",
            )

        return RuntimeHealthState.HEALTHY, "Runtime is healthy. No tasks need recovery."

    def clear_all(self) -> None:
        self._checkpoint_errors = 0
        self._worker_errors = 0
        self._recovery_failures = 0


# Global singleton instance
runtime_health_monitor = RuntimeHealthMonitor()
