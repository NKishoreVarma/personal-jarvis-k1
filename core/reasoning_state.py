"""
Bounded Structured Reasoning State for MARK XLVIII / JARVIS.
Maintains operational belief state, hypotheses, diagnostic results, and repair plans without unbounded memory growth.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.goal_contract import GoalContract


class HypothesisStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPPORTED = "SUPPORTED"
    DISPROVEN = "DISPROVEN"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"


@dataclass
class Hypothesis:
    hypothesis_id: str
    description: str
    category: str
    confidence: float = 0.5
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    suggested_diagnostic: Optional[str] = None
    suggested_repair: Optional[str] = None
    diagnostic_cost: float = 1.0  # 1.0 = low (read-only), 5.0 = high

    def add_support(self, evidence: str, boost: float = 0.2) -> None:
        self.supporting_evidence.append(evidence)
        self.confidence = min(1.0, self.confidence + boost)
        self.status = HypothesisStatus.SUPPORTED

    def add_contradiction(self, evidence: str, penalty: float = 0.4) -> None:
        self.contradicting_evidence.append(evidence)
        self.confidence = max(0.0, self.confidence - penalty)
        if self.confidence < 0.2:
            self.status = HypothesisStatus.DISPROVEN


@dataclass
class ReasoningState:
    goal: GoalContract
    observations: List[Dict[str, Any]] = field(default_factory=list)
    hypotheses: List[Hypothesis] = field(default_factory=list)
    selected_hypothesis: Optional[Hypothesis] = None
    plan: List[Dict[str, Any]] = field(default_factory=list)
    completed_steps: List[Dict[str, Any]] = field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = field(default_factory=list)
    verification_results: Dict[str, Any] = field(default_factory=dict)
    cycle_count: int = 0
    max_cycles: int = 5
    created_at: float = field(default_factory=time.monotonic)

    def add_observation(self, observation: Dict[str, Any], max_entries: int = 25) -> None:
        if len(self.observations) >= max_entries:
            self.observations.pop(0)
        self.observations.append(observation)

    def add_hypothesis(self, hypothesis: Hypothesis, max_entries: int = 10) -> None:
        if len(self.hypotheses) >= max_entries:
            # Evict oldest disproven or lowest confidence hypothesis
            self.hypotheses.sort(key=lambda h: (h.status != HypothesisStatus.DISPROVEN, h.confidence))
            self.hypotheses.pop(0)
        self.hypotheses.append(hypothesis)

    def get_active_hypotheses(self) -> List[Hypothesis]:
        return [h for h in self.hypotheses if h.status in (HypothesisStatus.ACTIVE, HypothesisStatus.SUPPORTED)]

    def select_best_hypothesis(self) -> Optional[Hypothesis]:
        active = self.get_active_hypotheses()
        if not active:
            return None
        # Sort by confidence descending, then by lower diagnostic cost
        active.sort(key=lambda h: (h.confidence, -h.diagnostic_cost), reverse=True)
        self.selected_hypothesis = active[0]
        return self.selected_hypothesis


def create_reasoning_state(goal: GoalContract, max_cycles: int = 5) -> ReasoningState:
    return ReasoningState(goal=goal, max_cycles=max_cycles)
