"""
Agent Contract for Autonomous Multi-Agent Orchestration & Collaboration in MARK XLVIII / JARVIS.
Defines bounded authority scopes, specialized agent roles, execution contracts,
and strict operational permissions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(str, Enum):
    OBSERVER = "OBSERVER"
    RESEARCHER = "RESEARCHER"
    DIAGNOSTIC = "DIAGNOSTIC"
    EXECUTOR = "EXECUTOR"
    VERIFIER = "VERIFIER"
    COORDINATOR = "COORDINATOR"
    PLANNER = "PLANNER"


class AuthorityLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    PREPARE_ONLY = "PREPARE_ONLY"
    EXECUTE_LOW_RISK = "EXECUTE_LOW_RISK"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class AgentStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


@dataclass
class AgentContract:
    agent_id: str
    parent_goal_id: str
    turn_id: str
    role: AgentRole
    task_description: str
    authority_scope: AuthorityLevel = AuthorityLevel.READ_ONLY
    allowed_operations: List[str] = field(default_factory=list)
    forbidden_operations: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Agent IDs that must complete first
    timeout_seconds: float = 15.0
    priority: int = 1  # 1 (low) to 10 (high)
    status: AgentStatus = AgentStatus.PENDING
    input_context: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    spawn_depth: int = 1
    parent_agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + self.timeout_seconds

    def is_expired(self) -> bool:
        return time.time() > self.expires_at if self.expires_at else False

    def is_operation_permitted(self, operation_name: str) -> bool:
        """
        Validates whether a specific operation is permitted by authority scope and whitelist/blacklist.
        """
        op_norm = operation_name.strip().lower()
        # Check forbidden blacklist first
        for forbidden in self.forbidden_operations:
            if forbidden.strip().lower() == op_norm:
                return False

        # Read-only authority cannot mutate
        if self.authority_scope == AuthorityLevel.READ_ONLY:
            mutating_keywords = ["restart", "kill", "terminate", "delete", "write", "install", "modify", "patch"]
            if any(kw in op_norm for kw in mutating_keywords):
                return False

        # Check allowed whitelist if specified
        if self.allowed_operations:
            return any(allowed.strip().lower() == op_norm for allowed in self.allowed_operations)

        return True

    def mark_started(self) -> None:
        self.status = AgentStatus.RUNNING
        self.started_at = time.time()

    def mark_completed(self, result: Dict[str, Any]) -> None:
        self.status = AgentStatus.COMPLETED
        self.result_data = result
        self.completed_at = time.time()

    def mark_failed(self, error: str) -> None:
        self.status = AgentStatus.FAILED
        self.error_message = error
        self.completed_at = time.time()

    def mark_cancelled(self, reason: str = "Parent goal cancelled") -> None:
        self.status = AgentStatus.CANCELLED
        self.error_message = reason
        self.completed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "parent_goal_id": self.parent_goal_id,
            "turn_id": self.turn_id,
            "role": self.role.value,
            "task_description": self.task_description,
            "authority_scope": self.authority_scope.value,
            "allowed_operations": self.allowed_operations,
            "forbidden_operations": self.forbidden_operations,
            "dependencies": self.dependencies,
            "timeout_seconds": self.timeout_seconds,
            "priority": self.priority,
            "status": self.status.value,
            "input_context": self.input_context,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "spawn_depth": self.spawn_depth,
            "parent_agent_id": self.parent_agent_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


def create_agent_contract(
    parent_goal_id: str,
    turn_id: str,
    role: AgentRole,
    task_description: str,
    authority_scope: AuthorityLevel = AuthorityLevel.READ_ONLY,
    allowed_operations: Optional[List[str]] = None,
    forbidden_operations: Optional[List[str]] = None,
    dependencies: Optional[List[str]] = None,
    timeout_seconds: float = 15.0,
    priority: int = 5,
    input_context: Optional[Dict[str, Any]] = None,
    spawn_depth: int = 1,
    parent_agent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentContract:
    return AgentContract(
        agent_id=f"agent_{role.value.lower()}_{uuid.uuid4().hex[:6]}",
        parent_goal_id=parent_goal_id,
        turn_id=turn_id,
        role=role,
        task_description=task_description,
        authority_scope=authority_scope,
        allowed_operations=allowed_operations or [],
        forbidden_operations=forbidden_operations or [],
        dependencies=dependencies or [],
        timeout_seconds=timeout_seconds,
        priority=priority,
        input_context=input_context or {},
        spawn_depth=spawn_depth,
        parent_agent_id=parent_agent_id,
        metadata=metadata or {},
    )
