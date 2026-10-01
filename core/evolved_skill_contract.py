"""
Evolved Skill Contract for Autonomous Skill Discovery & Capability Evolution in MARK XLVIII / JARVIS.
Defines versioned, verified, scoped, and authority-governed executable skill contracts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SkillType(str, Enum):
    ATOMIC = "ATOMIC"
    COMPOSITE = "COMPOSITE"
    DIAGNOSTIC = "DIAGNOSTIC"
    REPAIR = "REPAIR"
    VERIFICATION = "VERIFICATION"
    WORKFLOW = "WORKFLOW"
    ADAPTIVE = "ADAPTIVE"


class SkillStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    TESTING = "TESTING"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"
    DEPRECATED = "DEPRECATED"
    REJECTED = "REJECTED"


class SkillScope(str, Enum):
    GLOBAL = "GLOBAL"
    PROJECT = "PROJECT"
    ENVIRONMENT = "ENVIRONMENT"


@dataclass
class EvolvedSkillContract:
    skill_id: str
    skill_name: str
    description: str
    skill_type: SkillType
    version: str = "1.0.0"
    scope: SkillScope = SkillScope.PROJECT
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    authority_required: str = "READ_ONLY"  # READ_ONLY, DIAGNOSTIC, LOCAL_MUTATION, HIGH_RISK
    verification_requirements: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    confidence: float = 0.80
    reliability_score: float = 0.80
    verification_rate: float = 1.0
    average_duration: float = 0.0
    retry_rate: float = 0.0
    usage_count: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_verified_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deprecated_at: Optional[float] = None
    status: SkillStatus = SkillStatus.CANDIDATE
    provenance: str = "discovery"
    parent_skill_ids: List[str] = field(default_factory=list)
    composition_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.status in [SkillStatus.VERIFIED, SkillStatus.ACTIVE]

    def is_degraded(self) -> bool:
        return self.status in [SkillStatus.DEGRADED, SkillStatus.SUSPENDED, SkillStatus.REJECTED]

    def record_run(self, success: bool, duration_s: float, verified: bool) -> None:
        self.usage_count += 1
        if success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1

        # Exponential moving average for duration
        if self.average_duration == 0.0:
            self.average_duration = duration_s
        else:
            self.average_duration = (self.average_duration * 0.8) + (duration_s * 0.2)

        # Success rate & reliability
        if self.usage_count > 0:
            self.reliability_score = self.successful_runs / self.usage_count

        if verified and success:
            self.last_verified_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "description": self.description,
            "skill_type": self.skill_type.value,
            "version": self.version,
            "scope": self.scope.value,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "preconditions": self.preconditions,
            "execution_steps": self.execution_steps,
            "required_tools": self.required_tools,
            "authority_required": self.authority_required,
            "verification_requirements": self.verification_requirements,
            "success_criteria": self.success_criteria,
            "failure_conditions": self.failure_conditions,
            "confidence": round(self.confidence, 3),
            "reliability_score": round(self.reliability_score, 3),
            "verification_rate": round(self.verification_rate, 3),
            "average_duration": round(self.average_duration, 3),
            "retry_rate": round(self.retry_rate, 3),
            "usage_count": self.usage_count,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "last_verified_at": self.last_verified_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deprecated_at": self.deprecated_at,
            "status": self.status.value,
            "provenance": self.provenance,
            "parent_skill_ids": self.parent_skill_ids,
            "composition_id": self.composition_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvolvedSkillContract:
        type_val = data.get("skill_type", "WORKFLOW")
        try:
            skill_type = SkillType(type_val)
        except ValueError:
            skill_type = SkillType.WORKFLOW

        status_val = data.get("status", "CANDIDATE")
        try:
            status = SkillStatus(status_val)
        except ValueError:
            status = SkillStatus.CANDIDATE

        scope_val = data.get("scope", "PROJECT")
        try:
            scope = SkillScope(scope_val)
        except ValueError:
            scope = SkillScope.PROJECT

        return cls(
            skill_id=data.get("skill_id", f"skill_{uuid.uuid4().hex[:8]}"),
            skill_name=data.get("skill_name", ""),
            description=data.get("description", ""),
            skill_type=skill_type,
            version=data.get("version", "1.0.0"),
            scope=scope,
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            preconditions=data.get("preconditions", []),
            execution_steps=data.get("execution_steps", []),
            required_tools=data.get("required_tools", []),
            authority_required=data.get("authority_required", "READ_ONLY"),
            verification_requirements=data.get("verification_requirements", []),
            success_criteria=data.get("success_criteria", []),
            failure_conditions=data.get("failure_conditions", []),
            confidence=data.get("confidence", 0.80),
            reliability_score=data.get("reliability_score", 0.80),
            verification_rate=data.get("verification_rate", 1.0),
            average_duration=data.get("average_duration", 0.0),
            retry_rate=data.get("retry_rate", 0.0),
            usage_count=data.get("usage_count", 0),
            successful_runs=data.get("successful_runs", 0),
            failed_runs=data.get("failed_runs", 0),
            last_verified_at=data.get("last_verified_at"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            deprecated_at=data.get("deprecated_at"),
            status=status,
            provenance=data.get("provenance", "discovery"),
            parent_skill_ids=data.get("parent_skill_ids", []),
            composition_id=data.get("composition_id"),
            metadata=data.get("metadata", {}),
        )


def create_evolved_skill_contract(
    skill_name: str,
    description: str,
    skill_type: SkillType = SkillType.WORKFLOW,
    scope: SkillScope = SkillScope.PROJECT,
    execution_steps: Optional[List[Dict[str, Any]]] = None,
    required_tools: Optional[List[str]] = None,
    authority_required: str = "READ_ONLY",
    verification_requirements: Optional[List[str]] = None,
    provenance: str = "discovery",
    metadata: Optional[Dict[str, Any]] = None,
) -> EvolvedSkillContract:
    now = time.time()
    return EvolvedSkillContract(
        skill_id=f"eskill_{uuid.uuid4().hex[:8]}",
        skill_name=skill_name,
        description=description,
        skill_type=skill_type,
        scope=scope,
        execution_steps=execution_steps or [],
        required_tools=required_tools or [],
        authority_required=authority_required,
        verification_requirements=verification_requirements or [],
        created_at=now,
        updated_at=now,
        status=SkillStatus.CANDIDATE,
        provenance=provenance,
        metadata=metadata or {},
    )
