"""
Decision Policy Proposal, Governance & Versioning Engine for System 1 Decision Calibration in MARK XLVIII / JARVIS.
Manages versioned routing policies, shadow testing of threshold proposals, and deterministic rollback.
Enforces rule: System 1 cannot modify its own authority, relax high-risk thresholds, or bypass approval.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.decision_contract import DecisionCategory
from core.self_improvement_governor import GovernanceDecision, self_improvement_governor

logger = logging.getLogger(__name__)


class PolicyProposalStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SHADOW_TESTING = "SHADOW_TESTING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class DecisionPolicyProposal:
    proposal_id: str
    route: DecisionCategory
    current_policy: Dict[str, Any]
    proposed_policy: Dict[str, Any]
    reason: str
    supporting_sample_count: int
    calibration_metrics: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.85
    risk_level: str = "low"
    created_at: float = field(default_factory=time.time)
    status: PolicyProposalStatus = PolicyProposalStatus.PROPOSED
    rejection_reason: Optional[str] = None
    approved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "route": self.route.value if hasattr(self.route, "value") else str(self.route),
            "current_policy": self.current_policy,
            "proposed_policy": self.proposed_policy,
            "reason": self.reason,
            "supporting_sample_count": self.supporting_sample_count,
            "calibration_metrics": self.calibration_metrics,
            "confidence": round(self.confidence, 4),
            "risk_level": self.risk_level,
            "created_at": self.created_at,
            "status": self.status.value,
            "rejection_reason": self.rejection_reason,
            "approved_at": self.approved_at,
        }


@dataclass
class PolicyVersionRecord:
    version: str
    previous_version: Optional[str]
    route_thresholds: Dict[str, float]
    changes: Dict[str, Any]
    reason: str
    evidence_references: List[str]
    sample_count: int
    approved_by: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "previous_version": self.previous_version,
            "route_thresholds": {k: round(v, 4) for k, v in self.route_thresholds.items()},
            "changes": self.changes,
            "reason": self.reason,
            "evidence_references": self.evidence_references,
            "sample_count": self.sample_count,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }


class DecisionPolicyManager:
    """
    Governs policy updates, version progression, and deterministic rollback for System 1.
    """

    MIN_SAMPLES_FOR_PROPOSAL = 10
    ABSOLUTE_MIN_THRESHOLD = 0.75
    FORBIDDEN_AUTONOMOUS_ROUTES = {DecisionCategory.RISK}

    def __init__(self):
        self.current_version: str = "system1-policy-v1"
        self._version_counter: int = 1
        self._active_thresholds: Dict[str, float] = {
            DecisionCategory.INTENT.value: 0.75,
            DecisionCategory.AGENT_ROUTING.value: 0.75,
            DecisionCategory.SKILL_SELECTION.value: 0.75,
            DecisionCategory.STRATEGY_SELECTION.value: 0.75,
            DecisionCategory.URGENCY.value: 0.75,
            DecisionCategory.RISK.value: 0.95,
            DecisionCategory.PROACTIVE.value: 0.75,
            DecisionCategory.TEMPORAL.value: 0.75,
            DecisionCategory.RESEARCH.value: 0.80,
            DecisionCategory.MEMORY.value: 0.75,
        }
        self.proposals: Dict[str, DecisionPolicyProposal] = {}
        self.version_history: Dict[str, PolicyVersionRecord] = {
            "system1-policy-v1": PolicyVersionRecord(
                version="system1-policy-v1",
                previous_version=None,
                route_thresholds=dict(self._active_thresholds),
                changes={"initial": "Baseline verified thresholds"},
                reason="System 1 baseline initialization.",
                evidence_references=["PHASE_12_28_VERIFIED_BASELINE"],
                sample_count=0,
                approved_by="SYSTEM_DEFAULT",
            )
        }

    def get_threshold(self, category: DecisionCategory) -> float:
        cat_key = category.value if hasattr(category, "value") else str(category)
        return self._active_thresholds.get(cat_key, self.ABSOLUTE_MIN_THRESHOLD)

    def create_proposal(
        self,
        route: DecisionCategory,
        proposed_threshold: float,
        reason: str,
        supporting_sample_count: int,
        calibration_metrics: Optional[Dict[str, Any]] = None,
        confidence: float = 0.85,
    ) -> Tuple[Optional[DecisionPolicyProposal], str]:
        """
        Creates a policy proposal subject to safety boundaries and minimum sample counts.
        """
        # Invariant 1: Minimum sample size requirement
        if supporting_sample_count < self.MIN_SAMPLES_FOR_PROPOSAL:
            return None, f"Rejected: Supporting sample count ({supporting_sample_count}) is below minimum requirement ({self.MIN_SAMPLES_FOR_PROPOSAL})."

        # Invariant 2: High-risk or risk category cannot be relaxed
        if route in self.FORBIDDEN_AUTONOMOUS_ROUTES:
            return None, "Rejected: High-risk route policies cannot be altered autonomously."

        # Invariant 3: Threshold cannot be lowered below absolute baseline (0.75)
        if proposed_threshold < self.ABSOLUTE_MIN_THRESHOLD:
            return None, f"Rejected: Proposed threshold ({proposed_threshold:.2f}) is below absolute baseline ({self.ABSOLUTE_MIN_THRESHOLD:.2f})."

        cat_key = route.value if hasattr(route, "value") else str(route)
        current_threshold = self._active_thresholds.get(cat_key, self.ABSOLUTE_MIN_THRESHOLD)

        prop_id = f"prop_{uuid.uuid4().hex[:8]}"
        proposal = DecisionPolicyProposal(
            proposal_id=prop_id,
            route=route,
            current_policy={"threshold": current_threshold},
            proposed_policy={"threshold": round(proposed_threshold, 4)},
            reason=reason,
            supporting_sample_count=supporting_sample_count,
            calibration_metrics=calibration_metrics or {},
            confidence=confidence,
            risk_level="low",
            status=PolicyProposalStatus.PROPOSED,
        )
        self.proposals[prop_id] = proposal
        return proposal, "Proposal created successfully."

    def transition_to_shadow(self, proposal_id: str) -> Tuple[bool, str]:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False, f"Proposal '{proposal_id}' not found."
        if proposal.status != PolicyProposalStatus.PROPOSED:
            return False, f"Cannot transition proposal from {proposal.status.value} to SHADOW_TESTING."

        proposal.status = PolicyProposalStatus.SHADOW_TESTING
        return True, "Proposal transitioned to SHADOW_TESTING."

    def approve_and_activate(
        self,
        proposal_id: str,
        approved_by: str = "SELF_IMPROVEMENT_GOVERNOR",
    ) -> Tuple[bool, str]:
        """
        Approves and promotes a policy proposal into a new active policy version.
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False, f"Proposal '{proposal_id}' not found."

        if proposal.status not in [PolicyProposalStatus.PROPOSED, PolicyProposalStatus.SHADOW_TESTING]:
            return False, f"Cannot approve proposal in {proposal.status.value} status."

        # Verify against SelfImprovementGovernor if learning is enabled
        if not self_improvement_governor.learning_enabled:
            proposal.status = PolicyProposalStatus.REJECTED
            proposal.rejection_reason = "Continuous learning disabled by user governance."
            return False, "Continuous learning is disabled."

        # Build next version
        self._version_counter += 1
        new_version_id = f"system1-policy-v{self._version_counter}"
        prev_version = self.current_version

        cat_key = proposal.route.value if hasattr(proposal.route, "value") else str(proposal.route)
        new_threshold = proposal.proposed_policy["threshold"]

        # Apply change
        new_thresholds = dict(self._active_thresholds)
        new_thresholds[cat_key] = new_threshold

        # Record version history
        version_rec = PolicyVersionRecord(
            version=new_version_id,
            previous_version=prev_version,
            route_thresholds=new_thresholds,
            changes={cat_key: {"old": self._active_thresholds[cat_key], "new": new_threshold}},
            reason=proposal.reason,
            evidence_references=[f"proposal_{proposal_id}"],
            sample_count=proposal.supporting_sample_count,
            approved_by=approved_by,
        )

        self.version_history[new_version_id] = version_rec
        self._active_thresholds = new_thresholds
        self.current_version = new_version_id

        proposal.status = PolicyProposalStatus.APPROVED
        proposal.approved_at = time.time()

        return True, f"Policy proposal activated under version {new_version_id}."

    def reject_proposal(self, proposal_id: str, reason: str) -> Tuple[bool, str]:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False, f"Proposal '{proposal_id}' not found."

        proposal.status = PolicyProposalStatus.REJECTED
        proposal.rejection_reason = reason
        return True, f"Proposal rejected: {reason}"

    def rollback_policy(self, target_version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Deterministically rolls back active policy to target_version or previous version.
        """
        current_rec = self.version_history.get(self.current_version)
        if not current_rec:
            return False, "Current version record not found."

        target = target_version or current_rec.previous_version
        if not target:
            return False, "No previous policy version available for rollback."

        target_rec = self.version_history.get(target)
        if not target_rec:
            return False, f"Target rollback version '{target}' does not exist."

        # Revert thresholds
        self._active_thresholds = dict(target_rec.route_thresholds)

        # Mark any proposals approved under current version as ROLLED_BACK
        for p in self.proposals.values():
            if p.status == PolicyProposalStatus.APPROVED and p.approved_at and p.approved_at >= current_rec.timestamp:
                p.status = PolicyProposalStatus.ROLLED_BACK

        old_ver = self.current_version
        self.current_version = target

        return True, f"Successfully rolled back policy from {old_ver} to {target}."

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_policy_version": self.current_version,
            "active_thresholds": {k: round(v, 4) for k, v in self._active_thresholds.items()},
            "version_count": len(self.version_history),
            "proposal_count": len(self.proposals),
            "recent_versions": list(self.version_history.keys())[-5:],
        }


# Global singleton instance
decision_policy_manager = DecisionPolicyManager()
