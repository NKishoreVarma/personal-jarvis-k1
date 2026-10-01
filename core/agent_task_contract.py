"""
Agent Task Contract for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Defines formal atomic work assignments delegated to specialized agents.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.agent_contract import AgentRole


class AgentTaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"


@dataclass
class AgentTaskContract:
    task_id: str
    agent_id: str
    goal_id: str
    role: AgentRole
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_inputs: List[str] = field(default_factory=list)
    expected_output_type: str = "json"
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def mark_in_progress(self) -> None:
        self.status = AgentTaskStatus.IN_PROGRESS

    def mark_success(self, result: Dict[str, Any]) -> None:
        self.status = AgentTaskStatus.SUCCESS
        self.result = result
        self.completed_at = time.time()

    def mark_failure(self, error: str) -> None:
        self.status = AgentTaskStatus.FAILURE
        self.error = error
        self.completed_at = time.time()


def create_agent_task_contract(
    agent_id: str,
    goal_id: str,
    role: AgentRole,
    operation: str,
    parameters: Optional[Dict[str, Any]] = None,
    required_inputs: Optional[List[str]] = None,
    expected_output_type: str = "json",
) -> AgentTaskContract:
    return AgentTaskContract(
        task_id=f"atask_{uuid.uuid4().hex[:8]}",
        agent_id=agent_id,
        goal_id=goal_id,
        role=role,
        operation=operation,
        parameters=parameters or {},
        required_inputs=required_inputs or [],
        expected_output_type=expected_output_type,
    )
