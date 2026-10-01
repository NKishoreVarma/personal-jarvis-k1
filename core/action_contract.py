"""
Action Contract — Formal contract and safety lifecycle for real-world operations in MARK XLVIII / FLOW.
Defines risk levels, approval states, evidence binding, and execution contracts.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(Enum):
    READ_ONLY = "read_only"
    LOW_RISK = "low_risk"
    REVERSIBLE = "reversible"
    HIGH_RISK = "high_risk"
    DESTRUCTIVE = "destructive"


class ApprovalState(Enum):
    NOT_REQUIRED = "not_required"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionState(Enum):
    IDLE = "idle"
    PREPARED = "prepared"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _canonicalize(val: Any) -> Any:
    if isinstance(val, dict):
        return {str(k).strip().lower(): _canonicalize(v) for k, v in sorted(val.items())}
    elif isinstance(val, (list, tuple)):
        return [_canonicalize(x) for x in val]
    elif isinstance(val, str):
        return val.strip()
    return val


@dataclass
class ActionContract:
    """
    Formal, evidence-grounded action contract binding tool operation,
    arguments, risk profile, and approval lifecycle.
    """
    connector: str
    operation: str
    arguments: Dict[str, Any]
    risk_level: RiskLevel = RiskLevel.LOW_RISK
    permission_required: str = "low_risk"
    evidence: Dict[str, Any] = field(default_factory=dict)
    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:10]}")
    approval_required: bool = False
    approval_state: ApprovalState = ApprovalState.NOT_REQUIRED
    execution_state: ExecutionState = ExecutionState.IDLE
    verification_state: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.monotonic)
    expires_at: Optional[float] = None
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = self.compute_fingerprint()
        if self.risk_level in (RiskLevel.HIGH_RISK, RiskLevel.DESTRUCTIVE):
            self.approval_required = True
            if self.approval_state == ApprovalState.NOT_REQUIRED:
                self.approval_state = ApprovalState.PENDING_APPROVAL
        if self.expires_at is None:
            self.expires_at = self.created_at + 300.0  # 5-minute proposal validity

    def compute_fingerprint(self) -> str:
        """
        Generate a deterministic SHA-256 fingerprint binding the connector,
        operation, and canonical arguments.
        """
        payload = {
            "connector": self.connector.strip().lower(),
            "operation": self.operation.strip().lower(),
            "arguments": _canonicalize(self.arguments),
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]

    def is_expired(self) -> bool:
        if self.expires_at is not None and time.monotonic() > self.expires_at:
            if self.approval_state == ApprovalState.PENDING_APPROVAL:
                self.approval_state = ApprovalState.EXPIRED
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "connector": self.connector,
            "operation": self.operation,
            "risk_level": self.risk_level.value,
            "permission_required": self.permission_required,
            "arguments": self.arguments,
            "evidence": self.evidence,
            "approval_required": self.approval_required,
            "approval_state": self.approval_state.value,
            "execution_state": self.execution_state.value,
            "verification_state": self.verification_state,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "fingerprint": self.fingerprint,
        }
