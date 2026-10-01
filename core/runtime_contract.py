"""
Runtime Contract for Persistent Agent Runtime & Crash Recovery in MARK XLVIII / JARVIS.
Defines formal schemas for runtime instances, lifecycle states, process ownership,
heartbeat tracking, and recovery generations.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RuntimeStatus(str, Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"
    CRASHED = "CRASHED"


@dataclass
class RuntimeContract:
    runtime_id: str
    runtime_status: RuntimeStatus = RuntimeStatus.STARTING
    started_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    process_id: int = field(default_factory=os.getpid)
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:8]}")
    recovery_generation: int = 0
    shutdown_requested: bool = False
    crash_detected: bool = False
    last_checkpoint_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_heartbeat_stale(self, threshold_seconds: float = 10.0) -> bool:
        """Checks if heartbeat has expired beyond stale threshold."""
        return (time.time() - self.last_heartbeat) > threshold_seconds

    def touch_heartbeat(self) -> None:
        self.last_heartbeat = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "runtime_status": self.runtime_status.value if isinstance(self.runtime_status, RuntimeStatus) else str(self.runtime_status),
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "process_id": self.process_id,
            "session_id": self.session_id,
            "recovery_generation": self.recovery_generation,
            "shutdown_requested": self.shutdown_requested,
            "crash_detected": self.crash_detected,
            "last_checkpoint_at": self.last_checkpoint_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RuntimeContract:
        status_val = data.get("runtime_status", "STARTING")
        try:
            status_enum = RuntimeStatus(status_val)
        except ValueError:
            status_enum = RuntimeStatus.STARTING

        return cls(
            runtime_id=data.get("runtime_id", f"rt_{uuid.uuid4().hex[:8]}"),
            runtime_status=status_enum,
            started_at=data.get("started_at", time.time()),
            last_heartbeat=data.get("last_heartbeat", time.time()),
            process_id=data.get("process_id", os.getpid()),
            session_id=data.get("session_id", f"sess_{uuid.uuid4().hex[:8]}"),
            recovery_generation=data.get("recovery_generation", 0),
            shutdown_requested=data.get("shutdown_requested", False),
            crash_detected=data.get("crash_detected", False),
            last_checkpoint_at=data.get("last_checkpoint_at"),
            metadata=data.get("metadata", {}),
        )


def create_runtime_contract(
    runtime_id: Optional[str] = None,
    recovery_generation: int = 0,
) -> RuntimeContract:
    now = time.time()
    return RuntimeContract(
        runtime_id=runtime_id or f"rt_{uuid.uuid4().hex[:8]}",
        runtime_status=RuntimeStatus.STARTING,
        started_at=now,
        last_heartbeat=now,
        process_id=os.getpid(),
        session_id=f"sess_{uuid.uuid4().hex[:8]}",
        recovery_generation=recovery_generation,
    )
