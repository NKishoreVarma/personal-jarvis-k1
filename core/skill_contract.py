"""
Skill Contract for Autonomous Skill Learning & Reusable Workflows in MARK XLVIII / JARVIS.
Defines formal schema for learned skills, parameterized workflows, verification requirements,
and strict lifecycle states.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SkillType(str, Enum):
    PROJECT_WORKFLOW = "PROJECT_WORKFLOW"
    DIAGNOSTIC_SKILL = "DIAGNOSTIC_SKILL"
    REPAIR_SKILL = "REPAIR_SKILL"
    APPLICATION_WORKFLOW = "APPLICATION_WORKFLOW"
    UI_WORKFLOW = "UI_WORKFLOW"
    SYSTEM_WORKFLOW = "SYSTEM_WORKFLOW"
    USER_DEFINED_SKILL = "USER_DEFINED_SKILL"


class SkillStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    RETIRED = "RETIRED"
    FORGOTTEN = "FORGOTTEN"


class SkillMatchLevel(str, Enum):
    NO_MATCH = "NO_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    STRONG_MATCH = "STRONG_MATCH"


@dataclass
class SkillContract:
    skill_id: str
    skill_name: str
    skill_type: SkillType
    description: str
    goal_pattern: str
    problem_pattern: Optional[str] = None
    project_scope: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_preconditions: List[str] = field(default_factory=list)
    workflow_steps: List[Dict[str, Any]] = field(default_factory=list)
    expected_outcome: str = ""
    verification_requirements: List[str] = field(default_factory=list)
    risk_level: str = "LOW"  # READ_ONLY, LOW, REVERSIBLE, HIGH, DESTRUCTIVE
    confidence: float = 0.85
    success_count: int = 1
    failure_count: int = 0
    reuse_count: int = 0
    adaptation_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    last_verified_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    status: SkillStatus = SkillStatus.ACTIVE
    source_experience_ids: List[str] = field(default_factory=list)
    version: int = 1
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is not None and time.time() > self.expires_at:
            return True
        return False

    def is_executable(self) -> bool:
        return self.status == SkillStatus.ACTIVE and not self.is_expired()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_type": self.skill_type.value,
            "description": self.description,
            "goal_pattern": self.goal_pattern,
            "problem_pattern": self.problem_pattern,
            "project_scope": self.project_scope,
            "parameters": self.parameters,
            "required_preconditions": self.required_preconditions,
            "workflow_steps": self.workflow_steps,
            "expected_outcome": self.expected_outcome,
            "verification_requirements": self.verification_requirements,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "reuse_count": self.reuse_count,
            "adaptation_count": self.adaptation_count,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "last_verified_at": self.last_verified_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "source_experience_ids": self.source_experience_ids,
            "version": self.version,
            "evolution_history": self.evolution_history,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillContract:
        return cls(
            skill_id=data.get("skill_id", f"skill_{uuid.uuid4().hex[:8]}"),
            skill_name=data.get("skill_name", "unnamed_skill"),
            skill_type=SkillType(data.get("skill_type", "PROJECT_WORKFLOW")),
            description=data.get("description", ""),
            goal_pattern=data.get("goal_pattern", ""),
            problem_pattern=data.get("problem_pattern"),
            project_scope=data.get("project_scope"),
            parameters=data.get("parameters", {}),
            required_preconditions=data.get("required_preconditions", []),
            workflow_steps=data.get("workflow_steps", []),
            expected_outcome=data.get("expected_outcome", ""),
            verification_requirements=data.get("verification_requirements", []),
            risk_level=data.get("risk_level", "LOW"),
            confidence=data.get("confidence", 0.85),
            success_count=data.get("success_count", 1),
            failure_count=data.get("failure_count", 0),
            reuse_count=data.get("reuse_count", 0),
            adaptation_count=data.get("adaptation_count", 0),
            created_at=data.get("created_at", time.time()),
            last_used_at=data.get("last_used_at", time.time()),
            last_verified_at=data.get("last_verified_at", time.time()),
            expires_at=data.get("expires_at"),
            status=SkillStatus(data.get("status", "ACTIVE")),
            source_experience_ids=data.get("source_experience_ids", []),
            version=data.get("version", 1),
            evolution_history=data.get("evolution_history", []),
            metadata=data.get("metadata", {}),
        )


def create_skill_contract(
    skill_name: str,
    skill_type: SkillType,
    description: str,
    goal_pattern: str,
    workflow_steps: List[Dict[str, Any]],
    parameters: Optional[Dict[str, Any]] = None,
    problem_pattern: Optional[str] = None,
    project_scope: Optional[str] = None,
    required_preconditions: Optional[List[str]] = None,
    expected_outcome: str = "",
    verification_requirements: Optional[List[str]] = None,
    risk_level: str = "LOW",
    confidence: float = 0.85,
    source_experience_ids: Optional[List[str]] = None,
    version: int = 1,
) -> SkillContract:
    now = time.time()
    return SkillContract(
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        skill_name=skill_name,
        skill_type=skill_type,
        description=description,
        goal_pattern=goal_pattern,
        problem_pattern=problem_pattern,
        project_scope=project_scope,
        parameters=parameters or {},
        required_preconditions=required_preconditions or ["project_exists"],
        workflow_steps=workflow_steps,
        expected_outcome=expected_outcome or "Project operational and verified",
        verification_requirements=verification_requirements or ["outcome_verified", "http_responsive"],
        risk_level=risk_level,
        confidence=confidence,
        created_at=now,
        last_used_at=now,
        last_verified_at=now,
        status=SkillStatus.ACTIVE,
        source_experience_ids=source_experience_ids or [],
        version=version,
    )
