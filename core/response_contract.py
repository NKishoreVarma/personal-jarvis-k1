"""
Response Contract for Predictive Response Generation in MARK XLVIII / JARVIS.
Defines the structure for speculative response templates, verified completion bindings,
and strict safety enforcement (PREPARED RESPONSE != PERMISSION TO CLAIM SUCCESS).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ResponseStage(str, Enum):
    INITIAL = "INITIAL"
    ACK_RELEASED = "ACK_RELEASED"
    PROGRESS_RELEASED = "PROGRESS_RELEASED"
    SUCCESS_RELEASED = "SUCCESS_RELEASED"
    FAILURE_RELEASED = "FAILURE_RELEASED"
    INVALIDATED = "INVALIDATED"


@dataclass
class ResponseContract:
    contract_id: str
    turn_id: str
    task_type: str
    entities: Dict[str, Any] = field(default_factory=dict)
    ack_response: Optional[str] = "Okay."
    success_template: str = "{target} completed successfully."
    failure_template: str = "Unable to complete {target}: {error}."
    progress_template: Optional[str] = None
    requires_completion_announcement: bool = True
    stage: ResponseStage = ResponseStage.INITIAL
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = field(default_factory=lambda: time.monotonic() + 30.0)
    verified_result: Optional[Dict[str, Any]] = None

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at

    def format_success(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Renders the success response using verified execution data."""
        data = {**self.entities, **(context or {})}
        try:
            return self.success_template.format(**data)
        except KeyError:
            # Fallback if any placeholder is missing
            target = data.get("project") or data.get("app_name") or data.get("target") or "Task"
            return f"{target} is ready."

    def format_failure(self, error: str = "Unknown error", context: Optional[Dict[str, Any]] = None) -> str:
        """Renders the failure response with verified error details."""
        data = {**self.entities, "error": error, **(context or {})}
        try:
            return self.failure_template.format(**data)
        except KeyError:
            target = data.get("project") or data.get("app_name") or data.get("target") or "Task"
            return f"Failed to complete {target}: {error}."


def create_response_contract(
    turn_id: str,
    task_type: str,
    entities: Dict[str, Any],
    ack_response: Optional[str] = "Okay.",
    success_template: str = "{target} is ready.",
    failure_template: str = "Failed to complete {target}: {error}.",
    progress_template: Optional[str] = None,
    requires_completion_announcement: bool = True,
    ttl_sec: float = 30.0,
) -> ResponseContract:
    return ResponseContract(
        contract_id=f"resp_{uuid.uuid4().hex[:8]}",
        turn_id=turn_id,
        task_type=task_type,
        entities=entities,
        ack_response=ack_response,
        success_template=success_template,
        failure_template=failure_template,
        progress_template=progress_template,
        requires_completion_announcement=requires_completion_announcement,
        expires_at=time.monotonic() + ttl_sec,
    )
