"""
Outcome Evaluator for MARK XLVIII / JARVIS.
Evaluates verified task outcomes across duration, retries, repairs, verification strength,
and user feedback to compute an objective OutcomeEvaluation record.
Enforces the principle: SUCCESS != GOOD STRATEGY (Inefficient or fragile success is penalized).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OutcomeGrade(str, Enum):
    OPTIMAL = "OPTIMAL"
    ACCEPTABLE = "ACCEPTABLE"
    INEFFICIENT = "INEFFICIENT"
    FRAGILE = "FRAGILE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class OutcomeEvaluation:
    eval_id: str
    goal_id: str
    plan_id: str
    strategy_id: str
    target_project: str
    success: bool
    duration_s: float
    retry_count: int = 0
    repair_count: int = 0
    verification_strength: float = 1.0
    was_cancelled: bool = False
    was_corrected: bool = False
    strategy_changed: bool = False
    cost_score: float = 0.1
    quality_score: float = 0.9
    grade: OutcomeGrade = OutcomeGrade.OPTIMAL
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "goal_id": self.goal_id,
            "plan_id": self.plan_id,
            "strategy_id": self.strategy_id,
            "target_project": self.target_project,
            "success": self.success,
            "duration_s": self.duration_s,
            "retry_count": self.retry_count,
            "repair_count": self.repair_count,
            "verification_strength": self.verification_strength,
            "was_cancelled": self.was_cancelled,
            "was_corrected": self.was_corrected,
            "strategy_changed": self.strategy_changed,
            "cost_score": self.cost_score,
            "quality_score": self.quality_score,
            "grade": self.grade.value,
            "created_at": self.created_at,
        }


class OutcomeEvaluator:
    """
    Evaluates completed execution traces and grades outcome efficiency and reliability.
    """

    def evaluate_outcome(
        self,
        goal_id: str,
        plan_id: str,
        strategy_id: str,
        target_project: str,
        success: bool,
        duration_s: float,
        retry_count: int = 0,
        repair_count: int = 0,
        verification_strength: float = 1.0,
        was_cancelled: bool = False,
        was_corrected: bool = False,
        strategy_changed: bool = False,
    ) -> OutcomeEvaluation:
        """
        Computes structured OutcomeEvaluation with quality and cost scoring.
        """
        # Base quality
        if was_cancelled:
            grade = OutcomeGrade.CANCELLED
            quality_score = 0.2
            cost_score = min(1.0, duration_s / 10.0)
        elif not success:
            grade = OutcomeGrade.FAILED
            quality_score = 0.0
            cost_score = min(1.0, duration_s / 10.0 + retry_count * 0.2)
        else:
            # Task succeeded: evaluate efficiency & fragility
            quality = 1.0
            quality -= retry_count * 0.15
            quality -= repair_count * 0.20
            if strategy_changed:
                quality -= 0.15
            if was_corrected:
                quality -= 0.25

            quality *= verification_strength
            quality_score = max(0.1, min(1.0, quality))

            # Duration cost normalized (e.g. 5s baseline)
            cost_score = max(0.05, min(1.0, duration_s / 15.0 + retry_count * 0.1))

            if quality_score >= 0.85 and duration_s <= 5.0 and retry_count == 0:
                grade = OutcomeGrade.OPTIMAL
            elif quality_score >= 0.70:
                grade = OutcomeGrade.ACCEPTABLE
            elif repair_count > 0 or strategy_changed:
                grade = OutcomeGrade.FRAGILE
            else:
                grade = OutcomeGrade.INEFFICIENT

        return OutcomeEvaluation(
            eval_id=f"eval_{uuid.uuid4().hex[:8]}",
            goal_id=goal_id,
            plan_id=plan_id,
            strategy_id=strategy_id,
            target_project=target_project,
            success=success,
            duration_s=round(duration_s, 3),
            retry_count=retry_count,
            repair_count=repair_count,
            verification_strength=round(verification_strength, 2),
            was_cancelled=was_cancelled,
            was_corrected=was_corrected,
            strategy_changed=strategy_changed,
            cost_score=round(cost_score, 3),
            quality_score=round(quality_score, 3),
            grade=grade,
        )


# Global singleton instance
outcome_evaluator = OutcomeEvaluator()
