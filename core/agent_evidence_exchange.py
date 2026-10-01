"""
Agent Evidence Exchange for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Enforces the safety invariant: Shared Evidence != Shared Memory.
Exchanges bounded, structured observation payloads and measurements without leaking private worker context.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceType(str, Enum):
    PORT_STATE = "PORT_STATE"
    PROCESS_METRIC = "PROCESS_METRIC"
    LOG_SIGNATURE = "LOG_SIGNATURE"
    DOCUMENTATION_FACT = "DOCUMENTATION_FACT"
    DIAGNOSTIC_HYPOTHESIS = "DIAGNOSTIC_HYPOTHESIS"
    VERIFICATION_PROBE = "VERIFICATION_PROBE"
    ENVIRONMENTAL_OBSERVATION = "ENVIRONMENTAL_OBSERVATION"


@dataclass
class StructuredEvidence:
    evidence_id: str
    goal_id: str
    source_agent_id: str
    evidence_type: EvidenceType
    content: Dict[str, Any]
    confidence: float = 0.90
    timestamp: float = field(default_factory=time.time)


class AgentEvidenceExchange:
    """
    Exchange repository for verified observations between specialized agents.
    """

    def __init__(self):
        self._evidence_by_goal: Dict[str, List[StructuredEvidence]] = {}

    def submit_evidence(
        self,
        goal_id: str,
        source_agent_id: str,
        evidence_type: EvidenceType,
        content: Dict[str, Any],
        confidence: float = 0.90,
    ) -> StructuredEvidence:
        """
        Submits structured evidence, rejecting unstructured prompt dumping.
        """
        ev = StructuredEvidence(
            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
            goal_id=goal_id,
            source_agent_id=source_agent_id,
            evidence_type=evidence_type,
            content=content,
            confidence=confidence,
        )
        self._evidence_by_goal.setdefault(goal_id, []).append(ev)
        return ev

    def submit_observation(
        self,
        goal_id: str,
        source_agent_id: str,
        observation: Any,
    ) -> StructuredEvidence:
        """Publishes a structured perception observation to the multi-agent evidence exchange."""
        content = observation.to_dict() if hasattr(observation, "to_dict") else dict(observation)
        return self.submit_evidence(
            goal_id=goal_id,
            source_agent_id=source_agent_id,
            evidence_type=EvidenceType.ENVIRONMENTAL_OBSERVATION,
            content=content,
            confidence=getattr(observation, "confidence", 0.90),
        )

    def get_evidence(self, goal_id: str, evidence_type: Optional[EvidenceType] = None) -> List[StructuredEvidence]:
        items = self._evidence_by_goal.get(goal_id, [])
        if evidence_type:
            return [e for e in items if e.evidence_type == evidence_type]
        return list(items)

    def clear(self) -> None:
        self._evidence_by_goal.clear()


# Global singleton instance
agent_evidence_exchange = AgentEvidenceExchange()
