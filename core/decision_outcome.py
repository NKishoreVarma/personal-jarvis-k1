"""
Decision Outcome Contract and Store for System 1 Decision Calibration in MARK XLVIII / JARVIS.
Captures typed decision records, outcome verification states, and quality classifications.
Enforces rule: ACTION_COMPLETED != OUTCOME_VERIFIED, and OUTCOME_UNKNOWN != INCORRECT.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionType,
    compute_context_hash,
)

logger = logging.getLogger(__name__)


class OutcomeQuality(str, Enum):
    VERIFIED_CORRECT = "VERIFIED_CORRECT"
    VERIFIED_INCORRECT = "VERIFIED_INCORRECT"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
    USER_CORRECTED = "USER_CORRECTED"
    SYSTEM2_OVERRULED = "SYSTEM2_OVERRULED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    EXECUTION_SUCCEEDED = "EXECUTION_SUCCEEDED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


@dataclass
class DecisionOutcomeRecord:
    decision_id: str
    trace_id: str
    route: DecisionCategory
    decision_type: DecisionType
    model: str = "laya"
    checkpoint: str = "laya"
    language: str = "en"
    input_context_hash: str = ""
    predicted_option: Optional[str] = None
    predicted_confidence: float = 0.0
    alternatives: Dict[str, float] = field(default_factory=dict)
    system1_used: bool = True
    system2_used: bool = False
    fallback_used: bool = False
    abstained: bool = False
    governance_result: str = "PERMITTED"
    final_decision: Optional[str] = None
    actual_outcome: Optional[str] = None
    outcome_verified: bool = False
    outcome_quality: OutcomeQuality = OutcomeQuality.OUTCOME_UNKNOWN
    latency_ms: float = 0.0
    policy_version: str = "system1-policy-v1"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_correct(self) -> Optional[bool]:
        """
        Returns True if verified correct, False if verified incorrect / overruled / failed,
        or None if outcome is unknown or unverified.
        """
        if not self.outcome_verified or self.outcome_quality == OutcomeQuality.OUTCOME_UNKNOWN:
            return None
        if self.outcome_quality in [OutcomeQuality.VERIFIED_CORRECT, OutcomeQuality.EXECUTION_SUCCEEDED]:
            return True
        if self.outcome_quality in [
            OutcomeQuality.VERIFIED_INCORRECT,
            OutcomeQuality.USER_CORRECTED,
            OutcomeQuality.SYSTEM2_OVERRULED,
            OutcomeQuality.EXECUTION_FAILED,
        ]:
            return False
        if self.outcome_quality == OutcomeQuality.PARTIALLY_CORRECT:
            return 0.5  # type: ignore
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "trace_id": self.trace_id,
            "route": self.route.value if hasattr(self.route, "value") else str(self.route),
            "decision_type": self.decision_type.value if hasattr(self.decision_type, "value") else str(self.decision_type),
            "model": self.model,
            "checkpoint": self.checkpoint,
            "language": self.language,
            "input_context_hash": self.input_context_hash,
            "predicted_option": self.predicted_option,
            "predicted_confidence": round(self.predicted_confidence, 4),
            "alternatives": {k: round(v, 4) for k, v in self.alternatives.items()},
            "system1_used": self.system1_used,
            "system2_used": self.system2_used,
            "fallback_used": self.fallback_used,
            "abstained": self.abstained,
            "governance_result": self.governance_result,
            "final_decision": self.final_decision,
            "actual_outcome": self.actual_outcome,
            "outcome_verified": self.outcome_verified,
            "outcome_quality": self.outcome_quality.value if hasattr(self.outcome_quality, "value") else str(self.outcome_quality),
            "latency_ms": round(self.latency_ms, 3),
            "policy_version": self.policy_version,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


def create_decision_outcome_record(
    decision_result: DecisionResult,
    system1_used: bool = True,
    system2_used: bool = False,
    fallback_used: bool = False,
    governance_result: str = "PERMITTED",
    final_decision: Optional[str] = None,
    actual_outcome: Optional[str] = None,
    outcome_verified: bool = False,
    outcome_quality: OutcomeQuality = OutcomeQuality.OUTCOME_UNKNOWN,
    policy_version: str = "system1-policy-v1",
    metadata: Optional[Dict[str, Any]] = None,
) -> DecisionOutcomeRecord:
    """
    Creates a strongly typed DecisionOutcomeRecord from a DecisionResult.
    Guarantees no raw sensitive prompts are stored.
    """
    meta = dict(decision_result.metadata)
    if metadata:
        meta.update(metadata)

    return DecisionOutcomeRecord(
        decision_id=decision_result.decision_id,
        trace_id=decision_result.trace_id,
        route=decision_result.category,
        decision_type=decision_result.decision_type,
        model=decision_result.metadata.get("model", "laya"),
        checkpoint=decision_result.model_or_checkpoint,
        language=decision_result.language,
        input_context_hash=decision_result.input_context_hash,
        predicted_option=decision_result.selected_option,
        predicted_confidence=decision_result.confidence,
        alternatives=decision_result.alternatives,
        system1_used=system1_used,
        system2_used=system2_used,
        fallback_used=fallback_used,
        abstained=decision_result.abstained,
        governance_result=governance_result,
        final_decision=final_decision or decision_result.selected_option,
        actual_outcome=actual_outcome,
        outcome_verified=outcome_verified,
        outcome_quality=outcome_quality,
        latency_ms=decision_result.latency_ms,
        policy_version=policy_version,
        timestamp=decision_result.created_at,
        metadata=meta,
    )


class DecisionOutcomeStore:
    """
    In-memory bounded store for decision outcome records with persistence of lightweight summaries.
    Enforces maximum capacity and provides query and update capabilities.
    """

    def __init__(self, max_records: int = 5000):
        self.max_records = max_records
        self._records: Dict[str, DecisionOutcomeRecord] = {}
        self._ordered_ids: List[str] = []
        self._lock = threading.RLock()

    def add_record(self, record: DecisionOutcomeRecord) -> None:
        with self._lock:
            if record.decision_id in self._records:
                self._records[record.decision_id] = record
                return

            if len(self._ordered_ids) >= self.max_records:
                oldest_id = self._ordered_ids.pop(0)
                self._records.pop(oldest_id, None)

            self._ordered_ids.append(record.decision_id)
            self._records[record.decision_id] = record

    def get_record(self, decision_id: str) -> Optional[DecisionOutcomeRecord]:
        with self._lock:
            return self._records.get(decision_id)

    def update_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        outcome_quality: OutcomeQuality,
        outcome_verified: bool = True,
        final_decision: Optional[str] = None,
        governance_result: Optional[str] = None,
        metadata_update: Optional[Dict[str, Any]] = None,
    ) -> bool:
        with self._lock:
            record = self._records.get(decision_id)
            if not record:
                return False

            record.actual_outcome = actual_outcome
            record.outcome_quality = outcome_quality
            record.outcome_verified = outcome_verified
            if final_decision is not None:
                record.final_decision = final_decision
            if governance_result is not None:
                record.governance_result = governance_result
            if metadata_update:
                record.metadata.update(metadata_update)
            return True

    def query_records(
        self,
        route: Optional[DecisionCategory] = None,
        language: Optional[str] = None,
        checkpoint: Optional[str] = None,
        verified_only: bool = False,
        min_timestamp: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[DecisionOutcomeRecord]:
        with self._lock:
            results: List[DecisionOutcomeRecord] = []
            # iterate in reverse chronological order
            for dec_id in reversed(self._ordered_ids):
                rec = self._records[dec_id]
                if route and rec.route != route:
                    continue
                if language and rec.language != language:
                    continue
                if checkpoint and rec.checkpoint != checkpoint:
                    continue
                if verified_only and not rec.outcome_verified:
                    continue
                if min_timestamp and rec.timestamp < min_timestamp:
                    continue
                results.append(rec)
                if limit and len(results) >= limit:
                    break
            return results

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._records)
            verified_count = sum(1 for r in self._records.values() if r.outcome_verified)
            correct_count = sum(
                1 for r in self._records.values() if r.is_correct() is True
            )
            incorrect_count = sum(
                1 for r in self._records.values() if r.is_correct() is False
            )
            unknown_count = sum(
                1 for r in self._records.values() if r.outcome_quality == OutcomeQuality.OUTCOME_UNKNOWN
            )
            abstained_count = sum(1 for r in self._records.values() if r.abstained)
            fallback_count = sum(1 for r in self._records.values() if r.fallback_used)

            return {
                "total_records": total,
                "verified_outcomes": verified_count,
                "verified_correct": correct_count,
                "verified_incorrect": incorrect_count,
                "unknown_outcomes": unknown_count,
                "abstained_count": abstained_count,
                "fallback_count": fallback_count,
                "verified_accuracy": (
                    round(correct_count / verified_count, 4) if verified_count > 0 else None
                ),
            }

    def save_summary(self, path: str = "data/runtime/decision_outcomes_summary.json") -> bool:
        """
        Persists non-sensitive aggregate summary to disk.
        """
        try:
            summary = self.get_summary()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            return True
        except Exception as e:
            logger.warning(f"Failed to persist decision outcomes summary: {e}")
            return False

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._ordered_ids.clear()


# Global singleton instance
decision_outcome_store = DecisionOutcomeStore()
