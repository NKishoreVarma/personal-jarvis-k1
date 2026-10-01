"""
Strategy Selector for MARK XLVIII / JARVIS.
Ranks candidate strategies using multi-factor objective scoring and selects the safest,
most verified strategy under the hierarchy:
CURRENT VERIFIED EVIDENCE > VERIFIED SKILL > HISTORICAL EXPERIENCE > GENERAL FALLBACK.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.strategy_generator import Strategy, StrategyType


class StrategySelector:
    """
    Evaluates, scores, and selects optimal execution strategy without exposing chain-of-thought.
    """

    def score_strategy(
        self,
        strategy: Strategy,
        current_evidence: Optional[List[Dict[str, Any]]] = None,
        observed_conflicts: Optional[List[str]] = None,
    ) -> float:
        """
        Calculates multi-factor score for a candidate strategy.
        """
        # Base confidence
        score = strategy.confidence * 2.0  # up to 2.0

        # Strategy type weighting (Hierarchy: EVIDENCE / VERIFIED SKILL > STANDARD > DIAGNOSTIC)
        if strategy.strategy_type == StrategyType.VERIFIED_SKILL:
            score += 1.5
        elif strategy.strategy_type == StrategyType.STANDARD_WORKFLOW:
            score += 1.0
        elif strategy.strategy_type == StrategyType.DIAGNOSTIC_FIRST:
            score += 0.8

        # Reversibility bonus
        if strategy.reversibility:
            score += 0.5

        # Risk penalty
        if strategy.estimated_risk == "low":
            score += 0.5
        elif strategy.estimated_risk == "high":
            score -= 1.0

        # Cost penalty
        if strategy.estimated_cost == "low":
            score += 0.3
        elif strategy.estimated_cost == "high":
            score -= 0.5

        # Assumption risk penalty if conflicts observed
        if observed_conflicts:
            for assump in strategy.assumptions:
                for conf in observed_conflicts:
                    if conf.lower() in assump.lower() or assump.lower() in conf.lower():
                        score -= 5.0  # heavy penalty for contradicted assumption

        # Continuous learning ranking modifier
        try:
            from core.capability_optimizer import capability_optimizer
            score += capability_optimizer.get_ranking_modifier(strategy.strategy_id)
            if strategy.skill_id:
                score += capability_optimizer.get_ranking_modifier(strategy.skill_id)
        except Exception:
            pass

        return round(score, 3)

    def select_strategy(
        self,
        strategies: List[Strategy],
        current_evidence: Optional[List[Dict[str, Any]]] = None,
        observed_conflicts: Optional[List[str]] = None,
    ) -> Tuple[Optional[Strategy], str]:
        """
        Selects the top-scoring strategy and provides a concise user-facing rationale.
        """
        if not strategies:
            return None, "No viable strategy found."

        scored: List[Tuple[Strategy, float]] = []
        for s in strategies:
            sc = self.score_strategy(s, current_evidence, observed_conflicts)
            scored.append((s, sc))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_strat, best_score = scored[0]

        # Generate concise explanation
        if best_strat.strategy_type == StrategyType.VERIFIED_SKILL:
            reason = "Using verified repair workflow matching current issue."
        elif best_strat.strategy_type == StrategyType.STANDARD_WORKFLOW:
            reason = "Using standard project startup based on verified configuration."
        elif best_strat.strategy_type == StrategyType.DIAGNOSTIC_FIRST:
            reason = "Gathering diagnostics first to resolve failure safely."
        else:
            reason = "Executing direct plan."

        return best_strat, reason


# Global singleton instance
strategy_selector = StrategySelector()
