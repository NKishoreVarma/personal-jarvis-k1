"""
Durable Task Contract for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Defines crash-resilient task representations tracking checkpoint versions, completed/pending steps,
and recovery state.
Enforces the principle: PERSISTED STATE IS A CHECKPOINT, NOT A SOURCE OF TRUTH.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DurableTaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING = "WAITING"
    VERIFYING = "VERIFYING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class DurableTaskContract:
    durable_task_id: str
    goal_id: str
    plan_id: str
    task_graph_id: str
    project_scope: str
    objective: str
    status: DurableTaskStatus = DurableTaskStatus.PENDING
    current_step: Optional[str] = None
    completed_steps: List[Dict[str, Any]] = field(default_factory=list)
    pending_steps: List[Dict[str, Any]] = field(default_factory=list)
    verification_state: str = "UNVERIFIED"
    checkpoint_version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_verified_at: Optional[float] = None
    recovery_attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = time.time()
        self.checkpoint_version += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "durable_task_id": self.durable_task_id,
            "goal_id": self.goal_id,
            "plan_id": self.plan_id,
            "task_graph_id": self.task_graph_id,
            "project_scope": self.project_scope,
            "objective": self.objective,
            "status": self.status.value if isinstance(self.status, DurableTaskStatus) else str(self.status),
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "verification_state": self.verification_state,
            "checkpoint_version": self.checkpoint_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_verified_at": self.last_verified_at,
            "recovery_attempts": self.recovery_attempts,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DurableTaskContract:
        status_val = data.get("status", "PENDING")
        try:
            status_enum = DurableTaskStatus(status_val)
        except ValueError:
            status_enum = DurableTaskStatus.PENDING

        return cls(
            durable_task_id=data.get("durable_task_id", f"dt_{uuid.uuid4().hex[:8]}"),
            goal_id=data.get("goal_id", ""),
            plan_id=data.get("plan_id", ""),
            task_graph_id=data.get("task_graph_id", ""),
            project_scope=data.get("project_scope", ""),
            objective=data.get("objective", ""),
            status=status_enum,
            current_step=data.get("current_step"),
            completed_steps=data.get("completed_steps", []),
            pending_steps=data.get("pending_steps", []),
            verification_state=data.get("verification_state", "UNVERIFIED"),
            checkpoint_version=data.get("checkpoint_version", 1),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            last_verified_at=data.get("last_verified_at"),
            recovery_attempts=data.get("recovery_attempts", 0),
            metadata=data.get("metadata", {}),
        )


def create_durable_task(
    goal_id: str,
    plan_id: str,
    task_graph_id: str,
    project_scope: str,
    objective: str,
    pending_steps: Optional[List[Dict[str, Any]]] = None,
) -> DurableTaskContract:
    now = time.time()
    return DurableTaskContract(
        durable_task_id=f"dt_{uuid.uuid4().hex[:8]}",
        goal_id=goal_id,
        plan_id=plan_id,
        task_graph_id=task_graph_id,
        project_scope=project_scope,
        objective=objective,
        status=DurableTaskStatus.PENDING,
        pending_steps=pending_steps or [],
        created_at=now,
        updated_at=now,
    )
