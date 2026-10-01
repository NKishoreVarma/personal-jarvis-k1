"""
Decision Calibration Engine for System 1 Decision Evaluation in MARK XLVIII / JARVIS.
Computes Expected Calibration Error (ECE), Brier scores, confidence bucket distributions,
route-specific trust scores, recency-weighted statistics, and shadow recommendations.
Enforces rule: Do not compute misleading metrics or adapt policy when sample size is insufficient.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.decision_contract import DecisionCategory, DecisionType
from core.decision_outcome import (
    DecisionOutcomeRecord,
    OutcomeQuality,
    decision_outcome_store,
)

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceBucket:
    bin_lower: float
    bin_upper: float
    sample_count: int = 0
    correct_count: float = 0.0
    confidence_sum: float = 0.0

    @property
    def accuracy(self) -> float:
        if self.sample_count == 0:
            return 0.0
        return self.correct_count / self.sample_count

    @property
    def mean_confidence(self) -> float:
        if self.sample_count == 0:
            return 0.0
        return self.confidence_sum / self.sample_count

    @property
    def calibration_gap(self) -> float:
        return abs(self.accuracy - self.mean_confidence)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "range": f"[{self.bin_lower:.2f}, {self.bin_upper:.2f})",
            "sample_count": self.sample_count,
            "accuracy": round(self.accuracy, 4),
            "mean_confidence": round(self.mean_confidence, 4),
            "calibration_gap": round(self.calibration_gap, 4),
        }


@dataclass
class CalibrationReport:
    category: Optional[str]
    language: Optional[str]
    checkpoint: Optional[str]
    sample_count: int
    verified_sample_count: int
    accuracy: Optional[float]
    expected_calibration_error: Optional[float]
    max_calibration_error: Optional[float]
    brier_score: Optional[float]
    confidence_mean: Optional[float]
    confidence_variance: Optional[float]
    abstention_rate: float
    fallback_rate: float
    disagreement_rate: float
    system2_override_rate: float
    route_trust_score: float
    buckets: List[ConfidenceBucket]
    overconfident_bins: List[str]
    underconfident_bins: List[str]
    is_sufficient: bool
    recommended_threshold: Optional[float]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "language": self.language,
            "checkpoint": self.checkpoint,
            "sample_count": self.sample_count,
            "verified_sample_count": self.verified_sample_count,
            "accuracy": round(self.accuracy, 4) if self.accuracy is not None else None,
            "expected_calibration_error": (
                round(self.expected_calibration_error, 4)
                if self.expected_calibration_error is not None
                else None
            ),
            "max_calibration_error": (
                round(self.max_calibration_error, 4)
                if self.max_calibration_error is not None
                else None
            ),
            "brier_score": round(self.brier_score, 4) if self.brier_score is not None else None,
            "confidence_mean": round(self.confidence_mean, 4) if self.confidence_mean is not None else None,
            "confidence_variance": (
                round(self.confidence_variance, 6)
                if self.confidence_variance is not None
                else None
            ),
            "abstention_rate": round(self.abstention_rate, 4),
            "fallback_rate": round(self.fallback_rate, 4),
            "disagreement_rate": round(self.disagreement_rate, 4),
            "system2_override_rate": round(self.system2_override_rate, 4),
            "route_trust_score": round(self.route_trust_score, 4),
            "buckets": [b.to_dict() for b in self.buckets],
            "overconfident_bins": self.overconfident_bins,
            "underconfident_bins": self.underconfident_bins,
            "is_sufficient": self.is_sufficient,
            "recommended_threshold": (
                round(self.recommended_threshold, 4)
                if self.recommended_threshold is not None
                else None
            ),
            "timestamp": self.timestamp,
        }


class DecisionCalibrationEngine:
    """
    Evaluates confidence calibration, calculates Expected Calibration Error (ECE),
    detects over/underconfidence, and computes route-specific trust scores.
    """

    DEFAULT_MIN_SAMPLES = 10

    def __init__(
        self,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        target_accuracy: float = 0.85,
        num_buckets: int = 5,
    ):
        self.min_samples = min_samples
        self.target_accuracy = target_accuracy
        self.num_buckets = num_buckets

    def _create_buckets(self) -> List[ConfidenceBucket]:
        # Buckets spanning [0.50, 1.00] with standard interval 0.10
        # Plus an initial catch-all bucket for [0.0, 0.50) if predictions fall below 0.5
        buckets = [
            ConfidenceBucket(0.0, 0.50),
            ConfidenceBucket(0.50, 0.60),
            ConfidenceBucket(0.60, 0.70),
            ConfidenceBucket(0.70, 0.80),
            ConfidenceBucket(0.80, 0.90),
            ConfidenceBucket(0.90, 1.0001),
        ]
        return buckets

    def evaluate_records(
        self,
        records: List[DecisionOutcomeRecord],
        category: Optional[str] = None,
        language: Optional[str] = None,
        checkpoint: Optional[str] = None,
    ) -> CalibrationReport:
        """
        Computes calibration statistics across the provided records.
        """
        total_count = len(records)
        if total_count == 0:
            return CalibrationReport(
                category=category,
                language=language,
                checkpoint=checkpoint,
                sample_count=0,
                verified_sample_count=0,
                accuracy=None,
                expected_calibration_error=None,
                max_calibration_error=None,
                brier_score=None,
                confidence_mean=None,
                confidence_variance=None,
                abstention_rate=0.0,
                fallback_rate=0.0,
                disagreement_rate=0.0,
                system2_override_rate=0.0,
                route_trust_score=0.5,
                buckets=[],
                overconfident_bins=[],
                underconfident_bins=[],
                is_sufficient=False,
                recommended_threshold=None,
            )

        # Basic rates across all records
        abstained_count = sum(1 for r in records if r.abstained)
        fallback_count = sum(1 for r in records if r.fallback_used)
        disagreement_count = sum(
            1
            for r in records
            if r.predicted_option and r.final_decision and r.predicted_option != r.final_decision
        )
        system2_override_count = sum(
            1 for r in records if r.outcome_quality == OutcomeQuality.SYSTEM2_OVERRULED
        )

        abstention_rate = abstained_count / total_count
        fallback_rate = fallback_count / total_count
        disagreement_rate = disagreement_count / total_count
        system2_override_rate = system2_override_count / total_count

        # Filter for verified outcomes with established correctness
        verified_records: List[Tuple[DecisionOutcomeRecord, float]] = []
        for r in records:
            corr = r.is_correct()
            if corr is not None:
                # corr can be True, False, or 0.5 (partially correct)
                score_val = 1.0 if corr is True else (0.0 if corr is False else 0.5)
                verified_records.append((r, score_val))

        verified_sample_count = len(verified_records)
        is_sufficient = verified_sample_count >= self.min_samples

        if verified_sample_count == 0:
            return CalibrationReport(
                category=category,
                language=language,
                checkpoint=checkpoint,
                sample_count=total_count,
                verified_sample_count=0,
                accuracy=None,
                expected_calibration_error=None,
                max_calibration_error=None,
                brier_score=None,
                confidence_mean=None,
                confidence_variance=None,
                abstention_rate=abstention_rate,
                fallback_rate=fallback_rate,
                disagreement_rate=disagreement_rate,
                system2_override_rate=system2_override_rate,
                route_trust_score=0.5,
                buckets=[],
                overconfident_bins=[],
                underconfident_bins=[],
                is_sufficient=False,
                recommended_threshold=None,
            )

        # Accuracy
        total_correct = sum(score for _, score in verified_records)
        accuracy = total_correct / verified_sample_count

        # Confidence mean and variance
        confidences = [r.predicted_confidence for r, _ in verified_records]
        conf_mean = sum(confidences) / verified_sample_count
        conf_var = (
            sum((c - conf_mean) ** 2 for c in confidences) / verified_sample_count
            if verified_sample_count > 1
            else 0.0
        )

        # Brier score: 1/N * sum((p_i - y_i)^2)
        brier_score = (
            sum((r.predicted_confidence - y) ** 2 for r, y in verified_records)
            / verified_sample_count
        )

        # Bucketed Calibration (ECE and MCE)
        buckets = self._create_buckets()
        for r, score_val in verified_records:
            conf = max(0.0, min(1.0, r.predicted_confidence))
            for b in buckets:
                if b.bin_lower <= conf < b.bin_upper:
                    b.sample_count += 1
                    b.correct_count += score_val
                    b.confidence_sum += conf
                    break

        # Calculate ECE and MCE
        ece = 0.0
        mce = 0.0
        overconfident_bins: List[str] = []
        underconfident_bins: List[str] = []

        for b in buckets:
            if b.sample_count > 0:
                gap = b.calibration_gap
                ece += (b.sample_count / verified_sample_count) * gap
                if gap > mce:
                    mce = gap

                # Detect over/underconfidence (threshold 0.15 gap)
                diff = b.mean_confidence - b.accuracy
                if diff > 0.15:
                    overconfident_bins.append(f"{b.bin_lower:.2f}-{b.bin_upper:.2f}")
                elif diff < -0.15:
                    underconfident_bins.append(f"{b.bin_lower:.2f}-{b.bin_upper:.2f}")

        # Route Trust Score calculation
        # Blend of: accuracy (0.40), (1 - ECE) (0.25), (1 - disagreement) (0.15), (1 - fallback) (0.10), sample factor (0.10)
        sample_factor = min(1.0, verified_sample_count / (self.min_samples * 2))
        trust_score = (
            0.40 * accuracy
            + 0.25 * max(0.0, 1.0 - ece)
            + 0.15 * max(0.0, 1.0 - disagreement_rate)
            + 0.10 * max(0.0, 1.0 - fallback_rate)
            + 0.10 * sample_factor
        )
        trust_score = max(0.0, min(1.0, trust_score))

        # Shadow recommendation: find lowest bucket where accuracy >= target_accuracy
        recommended_threshold = None
        if is_sufficient:
            # Check buckets with at least 2 samples from highest to lowest
            valid_bins = [b for b in buckets if b.sample_count >= 2 and b.bin_lower >= 0.5]
            passing_bins = [b for b in valid_bins if b.accuracy >= self.target_accuracy]
            if passing_bins:
                # Find lowest passing bucket's lower bound, capped at min 0.75
                recommended_threshold = max(0.75, min(b.bin_lower for b in passing_bins))
            else:
                # If no bucket meets target accuracy, recommend higher threshold
                recommended_threshold = 0.90

        return CalibrationReport(
            category=category,
            language=language,
            checkpoint=checkpoint,
            sample_count=total_count,
            verified_sample_count=verified_sample_count,
            accuracy=accuracy,
            expected_calibration_error=ece,
            max_calibration_error=mce,
            brier_score=brier_score,
            confidence_mean=conf_mean,
            confidence_variance=conf_var,
            abstention_rate=abstention_rate,
            fallback_rate=fallback_rate,
            disagreement_rate=disagreement_rate,
            system2_override_rate=system2_override_rate,
            route_trust_score=trust_score,
            buckets=buckets,
            overconfident_bins=overconfident_bins,
            underconfident_bins=underconfident_bins,
            is_sufficient=is_sufficient,
            recommended_threshold=recommended_threshold,
        )

    def calibrate_category(
        self,
        category: DecisionCategory,
        recent_window_limit: Optional[int] = None,
    ) -> CalibrationReport:
        records = decision_outcome_store.query_records(
            route=category,
            limit=recent_window_limit,
        )
        cat_str = category.value if hasattr(category, "value") else str(category)
        return self.evaluate_records(records, category=cat_str)

    def calibrate_language(
        self,
        language: str,
        recent_window_limit: Optional[int] = None,
    ) -> CalibrationReport:
        records = decision_outcome_store.query_records(
            language=language,
            limit=recent_window_limit,
        )
        return self.evaluate_records(records, language=language)

    def calibrate_checkpoint(
        self,
        checkpoint: str,
        recent_window_limit: Optional[int] = None,
    ) -> CalibrationReport:
        records = decision_outcome_store.query_records(
            checkpoint=checkpoint,
            limit=recent_window_limit,
        )
        return self.evaluate_records(records, checkpoint=checkpoint)

    def calibrate_global(
        self,
        recent_window_limit: Optional[int] = None,
    ) -> CalibrationReport:
        records = decision_outcome_store.query_records(
            limit=recent_window_limit,
        )
        return self.evaluate_records(records)


# Global singleton instance
decision_calibration_engine = DecisionCalibrationEngine()
