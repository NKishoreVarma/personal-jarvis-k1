"""
Learning Signal Detector for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Discovers recurrent behavioral patterns, failures, retries, and corrections.
Enforces rule: Single-instance anomalies are filtered out (Threshold >= 2 occurrences).
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.outcome_contract import OutcomeContract, OutcomeType


class LearningSignalType(str, Enum):
    SUCCESS_PATTERN = "SUCCESS_PATTERN"
    FAILURE_PATTERN = "FAILURE_PATTERN"
    EFFICIENCY_PATTERN = "EFFICIENCY_PATTERN"
    USER_CORRECTION_PATTERN = "USER_CORRECTION_PATTERN"
    REGRESSION_PATTERN = "REGRESSION_PATTERN"
    KNOWLEDGE_GAP_PATTERN = "KNOWLEDGE_GAP_PATTERN"
    VERIFICATION_GAP_PATTERN = "VERIFICATION_GAP_PATTERN"


@dataclass
class LearningSignal:
    signal_type: LearningSignalType
    pattern_key: str
    occurrence_count: int
    evidence_references: List[str]
    description: str
    detected_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningSignalDetector:
    """
    Scans outcome records and telemetry to detect robust learning signals.
    """

    def __init__(self, min_occurrence_threshold: int = 2):
        self.min_occurrence_threshold = min_occurrence_threshold
        self._history: List[OutcomeContract] = []
        self._user_corrections: Dict[str, int] = defaultdict(int)

    def record_outcome(self, outcome: OutcomeContract) -> None:
        self._history.append(outcome)

    def record_user_correction(self, topic_key: str) -> None:
        self._user_corrections[topic_key.lower().strip()] += 1

    def detect_signals(self) -> List[LearningSignal]:
        """
        Scans history and produces verified learning signals meeting the occurrence threshold.
        """
        signals: List[LearningSignal] = []

        # 1. Failure patterns
        failure_counts: Dict[str, List[OutcomeContract]] = defaultdict(list)
        success_counts: Dict[str, List[OutcomeContract]] = defaultdict(list)
        efficiency_counts: Dict[str, List[OutcomeContract]] = defaultdict(list)

        for out in self._history:
            if out.outcome_type == OutcomeType.FAILURE and out.failure_reason:
                failure_counts[out.failure_reason].append(out)
            elif out.outcome_type in [OutcomeType.SUCCESS, OutcomeType.VERIFIED_SUCCESS]:
                skill_or_goal = out.skill_id or out.goal_id or out.expected_outcome
                if skill_or_goal:
                    success_counts[skill_or_goal].append(out)

            if out.duration > 5.0:  # slow execution
                key = out.skill_id or out.goal_id or "slow_task"
                efficiency_counts[key].append(out)

        # Build failure signals
        for reason, outcomes in failure_counts.items():
            if len(outcomes) >= self.min_occurrence_threshold:
                ev_refs = [f"out:{o.outcome_id}" for o in outcomes]
                signals.append(
                    LearningSignal(
                        signal_type=LearningSignalType.FAILURE_PATTERN,
                        pattern_key=f"failure:{reason}",
                        occurrence_count=len(outcomes),
                        evidence_references=ev_refs,
                        description=f"Recurring failure signature detected: '{reason}'.",
                    )
                )

        # Build success patterns
        for key, outcomes in success_counts.items():
            if len(outcomes) >= self.min_occurrence_threshold:
                ev_refs = [f"out:{o.outcome_id}" for o in outcomes]
                signals.append(
                    LearningSignal(
                        signal_type=LearningSignalType.SUCCESS_PATTERN,
                        pattern_key=f"success:{key}",
                        occurrence_count=len(outcomes),
                        evidence_references=ev_refs,
                        description=f"Reliable success pattern confirmed for: '{key}'.",
                    )
                )

        # Build user correction patterns
        for topic, count in self._user_corrections.items():
            if count >= self.min_occurrence_threshold:
                signals.append(
                    LearningSignal(
                        signal_type=LearningSignalType.USER_CORRECTION_PATTERN,
                        pattern_key=f"correction:{topic}",
                        occurrence_count=count,
                        evidence_references=[f"correction:{topic}"],
                        description=f"Repeated user correction received on topic: '{topic}'.",
                    )
                )

        # Build efficiency patterns
        for key, outcomes in efficiency_counts.items():
            if len(outcomes) >= self.min_occurrence_threshold:
                ev_refs = [f"out:{o.outcome_id}" for o in outcomes]
                signals.append(
                    LearningSignal(
                        signal_type=LearningSignalType.EFFICIENCY_PATTERN,
                        pattern_key=f"efficiency:{key}",
                        occurrence_count=len(outcomes),
                        evidence_references=ev_refs,
                        description=f"Recurring latency inefficiency identified for: '{key}'.",
                    )
                )

        return signals

    def clear(self) -> None:
        self._history.clear()
        self._user_corrections.clear()


# Global singleton instance
learning_signal_detector = LearningSignalDetector()
