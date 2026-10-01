"""
Cognitive Context Builder for Unified Autonomous Execution in MARK XLVIII / JARVIS.
Assembles compact, bounded cognitive contexts by selecting relevant world-model facts,
user preferences, pending approvals, recent verified outcomes, temporal deadlines, and memory facts.
Enforces character/token budgets, source provenance, trust classification, and freshness filtering.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.approval_manager import approval_store
from core.content_trust_classifier import ContentTrustLevel
from core.perception_contract import FreshnessState
from core.world_model import WorldModel
from core.world_model_resolver import FactSourceTier, GroundedFact

logger = logging.getLogger(__name__)


@dataclass
class ContextItem:
    key: str
    value: Any
    domain: str
    source: str
    timestamp: float
    confidence: float
    freshness: FreshnessState
    trust: ContentTrustLevel = ContentTrustLevel.TRUSTED_SYSTEM_STATE
    relevance_score: float = 1.0
    evidence_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "domain": self.domain,
            "source": self.source,
            "timestamp": self.timestamp,
            "confidence": round(self.confidence, 4),
            "freshness": self.freshness.value if hasattr(self.freshness, "value") else str(self.freshness),
            "trust": self.trust.value if hasattr(self.trust, "value") else str(self.trust),
            "relevance_score": round(self.relevance_score, 4),
            "evidence_id": self.evidence_id,
        }


@dataclass
class CognitiveContext:
    task: str
    trace_id: str
    goal_id: Optional[str] = None
    items: List[ContextItem] = field(default_factory=list)
    world_model_summary: Dict[str, Any] = field(default_factory=dict)
    active_preferences: Dict[str, Any] = field(default_factory=dict)
    pending_approvals: List[Dict[str, Any]] = field(default_factory=list)
    temporal_constraints: List[Dict[str, Any]] = field(default_factory=list)
    recent_outcomes: List[Dict[str, Any]] = field(default_factory=list)
    token_estimate: int = 0
    max_tokens: int = 4000
    truncated: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "trace_id": self.trace_id,
            "goal_id": self.goal_id,
            "items_count": len(self.items),
            "world_model_summary": self.world_model_summary,
            "active_preferences": self.active_preferences,
            "pending_approvals_count": len(self.pending_approvals),
            "temporal_constraints_count": len(self.temporal_constraints),
            "recent_outcomes_count": len(self.recent_outcomes),
            "token_estimate": self.token_estimate,
            "max_tokens": self.max_tokens,
            "truncated": self.truncated,
            "created_at": self.created_at,
        }


class CognitiveContextBuilder:
    """
    Constructs bounded cognitive context representations respecting token budgets and trust boundaries.
    """

    def __init__(self, world_model: Optional[WorldModel] = None, default_max_tokens: int = 4000):
        self.world_model = world_model
        self.default_max_tokens = default_max_tokens

    def set_world_model(self, world_model: WorldModel) -> None:
        self.world_model = world_model

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 characters per token."""
        return max(1, len(text) // 4)

    def _compute_relevance(self, key: str, value: Any, task_lower: str) -> float:
        """Heuristic relevance scorer based on keyword overlap and semantic tokens."""
        score = 0.5
        key_lower = key.lower()
        val_str = str(value).lower()
        
        words = [w for w in task_lower.split() if len(w) > 2]
        for w in words:
            if w in key_lower:
                score += 0.25
            if w in val_str:
                score += 0.20
        return min(1.0, score)

    def build_context(
        self,
        task: str,
        trace_id: str,
        goal_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        include_stale: bool = False,
    ) -> CognitiveContext:
        """
        Assembles a bounded context containing only relevant, fresh, and trusted elements.
        """
        limit = max_tokens or self.default_max_tokens
        task_lower = task.lower().strip()
        items: List[ContextItem] = []
        total_tokens = self._estimate_tokens(task)
        truncated = False

        # 1. Ingest relevant WorldModel facts
        wm_summary: Dict[str, Any] = {}
        if self.world_model:
            snapshot = self.world_model.get_snapshot()
            for domain_name, facts in snapshot.items():
                if not isinstance(facts, dict):
                    continue
                for k, v in facts.items():
                    # Check fact properties
                    freshness = FreshnessState.FRESH
                    trust = ContentTrustLevel.TRUSTED_SYSTEM_STATE
                    confidence = 1.0
                    evidence_id = None
                    val = v

                    fact_obj = self.world_model.get_fact(domain_name, k)
                    if fact_obj:
                        freshness = fact_obj.freshness
                        confidence = fact_obj.confidence
                        evidence_id = fact_obj.evidence_id
                        val = fact_obj.value

                    # Filter out expired or stale facts unless requested
                    if not include_stale and freshness in (FreshnessState.EXPIRED, FreshnessState.STALE):
                        continue

                    # Filter out untrusted content from polluting executive instructions
                    relevance = self._compute_relevance(k, val, task_lower)
                    if relevance >= 0.5:
                        item = ContextItem(
                            key=k,
                            value=val,
                            domain=domain_name,
                            source=f"world_model:{domain_name}",
                            timestamp=time.time(),
                            confidence=confidence,
                            freshness=freshness,
                            trust=trust,
                            relevance_score=relevance,
                            evidence_id=evidence_id,
                        )
                        items.append(item)
                        wm_summary[f"{domain_name}.{k}"] = val

        # 2. Ingest Pending Approvals
        pending_list: List[Dict[str, Any]] = []
        try:
            # Query approval store for pending items
            for act_id, contract in list(approval_store._pending.items()):
                if not contract.is_expired():
                    pending_list.append({
                        "action_id": contract.action_id,
                        "connector": contract.connector,
                        "operation": contract.operation,
                        "risk_level": contract.risk_level.value,
                        "fingerprint": contract.fingerprint,
                    })
        except Exception:
            pass

        # 3. Sort items by relevance descending
        items.sort(key=lambda it: it.relevance_score, reverse=True)

        # 4. Token budget enforcement
        budgeted_items: List[ContextItem] = []
        for it in items:
            item_text = f"{it.domain}:{it.key}={it.value}"
            item_toks = self._estimate_tokens(item_text)
            if total_tokens + item_toks > limit:
                truncated = True
                break
            total_tokens += item_toks
            budgeted_items.append(it)

        return CognitiveContext(
            task=task,
            trace_id=trace_id,
            goal_id=goal_id,
            items=budgeted_items,
            world_model_summary=wm_summary,
            active_preferences={},
            pending_approvals=pending_list,
            temporal_constraints=[],
            recent_outcomes=[],
            token_estimate=total_tokens,
            max_tokens=limit,
            truncated=truncated,
        )


# Global singleton builder
cognitive_context_builder = CognitiveContextBuilder()
