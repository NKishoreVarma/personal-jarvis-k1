"""
Improvement Opportunity Contract for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Defines candidate improvements, verification telemetry, baseline metrics, and lifecycle states.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.action_contract import RiskLevel


class ImprovementType(str, Enum):
    RELIABILITY_IMPROVEMENT = "RELIABILITY_IMPROVEMENT"
    PERFORMANCE_IMPROVEMENT = "PERFORMANCE_IMPROVEMENT"
    SAFETY_IMPROVEMENT = "SAFETY_IMPROVEMENT"
    VERIFICATION_IMPROVEMENT = "VERIFICATION_IMPROVEMENT"
    PLANNING_IMPROVEMENT = "PLANNING_IMPROVEMENT"
    SKILL_IMPROVEMENT = "SKILL_IMPROVEMENT"
    RETRIEVAL_IMPROVEMENT = "RETRIEVAL_IMPROVEMENT"
    MEMORY_IMPROVEMENT = "MEMORY_IMPROVEMENT"
    WORKFLOW_SIMPLIFICATION = "WORKFLOW_SIMPLIFICATION"


class ImprovementState(str, Enum):
    DETECTED = "DETECTED"
    CANDIDATE = "CANDIDATE"
    TESTING = "TESTING"
    VERIFIED = "VERIFIED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    EXPIRED = "EXPIRED"


@dataclass
class ImprovementOpportunityContract:
    opportunity_id: str
    improvement_type: ImprovementType
    title: str
    description: str
    affected_component: str
    source_signals: List[str] = field(default_factory=list)
    evidence_references: List[str] = field(default_factory=list)
    expected_improvement: str = ""
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    candidate_metrics: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.85
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    state: ImprovementState = ImprovementState.DETECTED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "improvement_type": self.improvement_type.value,
            "title": self.title,
            "description": self.description,
            "affected_component": self.affected_component,
            "source_signals": self.source_signals,
            "evidence_references": self.evidence_references,
            "expected_improvement": self.expected_improvement,
            "baseline_metrics": self.baseline_metrics,
            "candidate_metrics": self.candidate_metrics,
            "confidence": round(self.confidence, 3),
            "risk_level": self.risk_level.value,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


def create_improvement_opportunity(
    improvement_type: ImprovementType,
    title: str,
    description: str,
    affected_component: str,
    source_signals: Optional[List[str]] = None,
    evidence_references: Optional[List[str]] = None,
    expected_improvement: str = "",
    baseline_metrics: Optional[Dict[str, float]] = None,
    confidence: float = 0.85,
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    metadata: Optional[Dict[str, Any]] = None,
) -> ImprovementOpportunityContract:
    now = time.time()
    return ImprovementOpportunityContract(
        opportunity_id=f"imp_{uuid.uuid4().hex[:8]}",
        improvement_type=improvement_type,
        title=title,
        description=description,
        affected_component=affected_component,
        source_signals=source_signals or [],
        evidence_references=evidence_references or [],
        expected_improvement=expected_improvement,
        baseline_metrics=baseline_metrics or {},
        confidence=confidence,
        risk_level=risk_level,
        state=ImprovementState.CANDIDATE,
        created_at=now,
        updated_at=now,
        metadata=metadata or {},
    )
