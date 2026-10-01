"""
Proactive Opportunity Contract for Autonomous Planning & Opportunity Detection in MARK XLVIII / JARVIS.
Defines formal contracts for proactive next steps, blockers, risks, and follow-ups backed by verified evidence.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.action_contract import RiskLevel


class OpportunityType(str, Enum):
    NEXT_STEP = "NEXT_STEP"
    BLOCKER = "BLOCKER"
    RISK = "RISK"
    FOLLOW_UP = "FOLLOW_UP"
    OPTIMIZATION = "OPTIMIZATION"
    MAINTENANCE = "MAINTENANCE"
    DEADLINE = "DEADLINE"
    REGRESSION = "REGRESSION"
    KNOWLEDGE_GAP = "KNOWLEDGE_GAP"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"


class OpportunityState(str, Enum):
    DETECTED = "DETECTED"
    CANDIDATE = "CANDIDATE"
    SUGGESTED = "SUGGESTED"
    APPROVED = "APPROVED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"


@dataclass
class ProactiveOpportunityContract:
    opportunity_id: str
    opportunity_type: OpportunityType
    title: str
    description: str
    source_goal_id: str = ""
    project_id: str = "GLOBAL"
    session_id: str = "default_session"
    evidence_references: List[str] = field(default_factory=list)
    confidence: float = 0.85
    importance: float = 0.70
    urgency: float = 0.50
    estimated_value: float = 0.80
    estimated_cost: float = 0.20
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    required_authority: str = "READ_ONLY"
    approval_required: bool = False
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    superseded_by: Optional[str] = None
    state: OpportunityState = OpportunityState.DETECTED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.state in [OpportunityState.DETECTED, OpportunityState.CANDIDATE, OpportunityState.SUGGESTED]

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        if self.state in [OpportunityState.EXPIRED, OpportunityState.INVALIDATED, OpportunityState.DISMISSED]:
            return True
        if self.expires_at is not None:
            now = current_time if current_time is not None else time.time()
            return now > self.expires_at
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_type": self.opportunity_type.value,
            "title": self.title,
            "description": self.description,
            "source_goal_id": self.source_goal_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "evidence_references": self.evidence_references,
            "confidence": round(self.confidence, 3),
            "importance": round(self.importance, 3),
            "urgency": round(self.urgency, 3),
            "estimated_value": round(self.estimated_value, 3),
            "estimated_cost": round(self.estimated_cost, 3),
            "risk_level": self.risk_level.value,
            "required_authority": self.required_authority,
            "approval_required": self.approval_required,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "superseded_by": self.superseded_by,
            "state": self.state.value,
            "metadata": self.metadata,
        }


def create_proactive_opportunity(
    opportunity_type: OpportunityType,
    title: str,
    description: str,
    project_id: str = "GLOBAL",
    source_goal_id: str = "",
    evidence_references: Optional[List[str]] = None,
    confidence: float = 0.85,
    importance: float = 0.70,
    urgency: float = 0.50,
    estimated_value: float = 0.80,
    estimated_cost: float = 0.20,
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    required_authority: str = "READ_ONLY",
    approval_required: bool = False,
    ttl_seconds: Optional[float] = 3600.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> ProactiveOpportunityContract:
    now = time.time()
    expires_at = now + ttl_seconds if ttl_seconds else None
    return ProactiveOpportunityContract(
        opportunity_id=f"opp_{uuid.uuid4().hex[:8]}",
        opportunity_type=opportunity_type,
        title=title,
        description=description,
        source_goal_id=source_goal_id,
        project_id=project_id,
        evidence_references=evidence_references or [],
        confidence=confidence,
        importance=importance,
        urgency=urgency,
        estimated_value=estimated_value,
        estimated_cost=estimated_cost,
        risk_level=risk_level,
        required_authority=required_authority,
        approval_required=approval_required,
        created_at=now,
        expires_at=expires_at,
        state=OpportunityState.DETECTED,
        metadata=metadata or {},
    )
