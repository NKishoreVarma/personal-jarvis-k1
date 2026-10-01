"""
World Model Conflict Resolver for MARK XLVIII / JARVIS.
Resolves sensor disagreements, staleness conflicts, and multi-source observations using the evidence hierarchy:
    CURRENT VERIFIED OBSERVATION
                >
    CURRENT OBSERVATION
                >
    RECENT VERIFIED STATE
                >
    HISTORICAL STATE
                >
    INFERENCE / ASSUMPTION

Guarantees that stale information cannot override fresh verified evidence, and marks unresolved
conflicts as AMBIGUOUS rather than hallucinating or silently picking arbitrary states.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.perception_contract import FreshnessState, Observation


class FactSourceTier(int, Enum):
    CURRENT_VERIFIED_OBSERVATION = 5
    CURRENT_OBSERVATION = 4
    RECENT_VERIFIED_STATE = 3
    HISTORICAL_STATE = 2
    INFERENCE_OR_ASSUMPTION = 1


@dataclass
class GroundedFact:
    """
    A single fact stored in the World Model with rigorous provenance and freshness metadata.
    """
    key: str
    value: Any
    source: str
    tier: FactSourceTier
    confidence: float
    timestamp: float
    freshness: FreshnessState
    evidence_id: str
    is_ambiguous: bool = False
    competing_values: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "tier": self.tier.name,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "freshness": self.freshness.value,
            "evidence_id": self.evidence_id,
            "is_ambiguous": self.is_ambiguous,
            "competing_values": self.competing_values,
        }


class WorldModelResolver:
    """
    Evaluates incoming observations against existing world model facts.
    """

    SOURCE_RELIABILITY_SCORES: Dict[str, float] = {
        "system_observer": 0.98,
        "filesystem_observer": 0.95,
        "application_observer": 0.94,
        "screen_observer": 0.92,
        "browser_observer": 0.90,
        "ocr_observer": 0.88,
        "inference": 0.60,
    }

    def determine_source_tier(self, obs: Observation, is_verified: bool = False) -> FactSourceTier:
        """Assigns the evidence tier based on verification and freshness."""
        now = time.time()
        elapsed = now - obs.timestamp

        if is_verified or obs.is_verified:
            if elapsed <= obs.ttl_seconds * 0.5:
                return FactSourceTier.CURRENT_VERIFIED_OBSERVATION
            elif elapsed <= obs.ttl_seconds:
                return FactSourceTier.RECENT_VERIFIED_STATE
            else:
                return FactSourceTier.HISTORICAL_STATE

        if elapsed <= obs.ttl_seconds * 0.5:
            return FactSourceTier.CURRENT_OBSERVATION
        elif elapsed <= obs.ttl_seconds:
            return FactSourceTier.HISTORICAL_STATE
        else:
            return FactSourceTier.INFERENCE_OR_ASSUMPTION

    def resolve_fact(
        self,
        key: str,
        incoming_val: Any,
        incoming_obs: Observation,
        existing_fact: Optional[GroundedFact] = None,
    ) -> GroundedFact:
        """
        Applies conflict resolution rules between existing grounded facts and incoming observations.
        """
        incoming_tier = self.determine_source_tier(incoming_obs, incoming_obs.is_verified)
        incoming_conf = incoming_obs.confidence
        incoming_ts = incoming_obs.timestamp
        evidence_id = incoming_obs.observation_id

        # If no existing fact exists, accept incoming fact directly
        if existing_fact is None:
            return GroundedFact(
                key=key,
                value=incoming_val,
                source=incoming_obs.source,
                tier=incoming_tier,
                confidence=incoming_conf,
                timestamp=incoming_ts,
                freshness=incoming_obs.freshness,
                evidence_id=evidence_id,
            )

        # 1. Compare Evidence Tiers: Higher tier strictly wins
        if incoming_tier > existing_fact.tier:
            return GroundedFact(
                key=key,
                value=incoming_val,
                source=incoming_obs.source,
                tier=incoming_tier,
                confidence=incoming_conf,
                timestamp=incoming_ts,
                freshness=incoming_obs.freshness,
                evidence_id=evidence_id,
            )
        elif incoming_tier < existing_fact.tier:
            # Existing fact is higher tier (e.g. current verified probe vs later heuristic inference)
            return existing_fact

        # 2. Both are in the same tier: Check if values agree
        if incoming_val == existing_fact.value:
            # Reinforce confidence and update timestamp to newest
            new_conf = min(1.0, max(incoming_conf, existing_fact.confidence) + 0.02)
            return GroundedFact(
                key=key,
                value=incoming_val,
                source=incoming_obs.source,
                tier=incoming_tier,
                confidence=new_conf,
                timestamp=max(incoming_ts, existing_fact.timestamp),
                freshness=incoming_obs.freshness,
                evidence_id=evidence_id,
            )

        # 3. Values conflict at the same tier:
        # Check timestamps: if incoming observation is significantly newer, accept it
        if (incoming_ts - existing_fact.timestamp) > 3.0:
            return GroundedFact(
                key=key,
                value=incoming_val,
                source=incoming_obs.source,
                tier=incoming_tier,
                confidence=incoming_conf,
                timestamp=incoming_ts,
                freshness=incoming_obs.freshness,
                evidence_id=evidence_id,
            )

        # 4. Compare sensor reliability & confidence
        incoming_rel = self.SOURCE_RELIABILITY_SCORES.get(incoming_obs.source, 0.70) * incoming_conf
        existing_rel = self.SOURCE_RELIABILITY_SCORES.get(existing_fact.source, 0.70) * existing_fact.confidence

        if abs(incoming_rel - existing_rel) > 0.15:
            if incoming_rel > existing_rel:
                return GroundedFact(
                    key=key,
                    value=incoming_val,
                    source=incoming_obs.source,
                    tier=incoming_tier,
                    confidence=incoming_conf,
                    timestamp=incoming_ts,
                    freshness=incoming_obs.freshness,
                    evidence_id=evidence_id,
                )
            else:
                return existing_fact

        # 5. Unresolved Conflict: Mark as AMBIGUOUS
        competing = [
            {"value": existing_fact.value, "source": existing_fact.source, "confidence": existing_fact.confidence},
            {"value": incoming_val, "source": incoming_obs.source, "confidence": incoming_conf},
        ]
        return GroundedFact(
            key=key,
            value=incoming_val,  # Keep latest but mark ambiguity
            source=f"{existing_fact.source}+{incoming_obs.source}",
            tier=incoming_tier,
            confidence=0.50,  # Penalize confidence due to conflict
            timestamp=max(incoming_ts, existing_fact.timestamp),
            freshness=incoming_obs.freshness,
            evidence_id=f"{existing_fact.evidence_id},{evidence_id}",
            is_ambiguous=True,
            competing_values=competing,
        )


# Global singleton instance
world_model_resolver = WorldModelResolver()
