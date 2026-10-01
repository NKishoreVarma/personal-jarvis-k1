"""
Strategy Effectiveness Analyzer for MARK XLVIII / JARVIS.
Evaluates the efficiency and reliability of executed strategies relative to baseline alternatives.
Enforces invariant: COMPARATIVE UNCERTAINTY (Never claim unexecuted alternatives were definitely superior).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.outcome_evaluator import OutcomeEvaluation, OutcomeGrade


class StrategyEffectiveness(str, Enum):
    EFFECTIVE = "EFFECTIVE"
    INEFFICIENT = "INEFFICIENT"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


@dataclass
class EffectivenessAnalysis:
    analysis_id: str
    strategy_id: str
    effectiveness: StrategyEffectiveness
    rationale: str
    confidence: float = 0.85
    alternative_comparisons: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "strategy_id": self.strategy_id,
            "effectiveness": self.effectiveness.value,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "alternative_comparisons": self.alternative_comparisons,
        }


class StrategyEffectivenessAnalyzer:
    """
    Analyzes whether an executed strategy performed efficiently or showed signs of degradation.
    """

    def analyze_effectiveness(
        self,
        evaluation: OutcomeEvaluation,
        alternative_strategy_ids: Optional[List[str]] = None,
    ) -> EffectivenessAnalysis:
        """
        Grades effectiveness and compares with bounded estimates for alternatives.
        """
        alt_ids = alternative_strategy_ids or []

        if evaluation.was_cancelled or evaluation.grade == OutcomeGrade.CANCELLED:
            effectiveness = StrategyEffectiveness.UNKNOWN
            rationale = "Execution was cancelled before full verification."
            conf = 0.50
        elif not evaluation.success or evaluation.grade == OutcomeGrade.FAILED:
            effectiveness = StrategyEffectiveness.DEGRADED
            rationale = "Strategy failed to achieve verified outcome."
            conf = 0.95
        elif evaluation.grade in [OutcomeGrade.INEFFICIENT, OutcomeGrade.FRAGILE]:
            effectiveness = StrategyEffectiveness.INEFFICIENT
            rationale = f"Strategy succeeded but incurred {evaluation.retry_count} retries and {evaluation.repair_count} repairs."
            conf = 0.85
        else:
            effectiveness = StrategyEffectiveness.EFFECTIVE
            rationale = "Strategy completed cleanly with high verification strength."
            conf = 0.95

        # Bounded comparative estimates (never claiming certainty)
        comparisons: List[Dict[str, Any]] = []
        for alt in alt_ids:
            comparisons.append({
                "alternative_id": alt,
                "estimated_comparative_advantage": "uncertain",
                "note": "Alternative was not executed in this environment.",
            })

        return EffectivenessAnalysis(
            analysis_id=f"eff_{evaluation.eval_id[:8]}",
            strategy_id=evaluation.strategy_id,
            effectiveness=effectiveness,
            rationale=rationale,
            confidence=conf,
            alternative_comparisons=comparisons,
        )


# Global singleton instance
strategy_effectiveness_analyzer = StrategyEffectivenessAnalyzer()
