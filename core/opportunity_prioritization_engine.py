"""
Opportunity Prioritization Engine for Proactive Task Orchestration in MARK XLVIII / JARVIS.
Ranks candidate proactive opportunities using explainable multi-factor scoring.
Enforces rule: Priority != Authorization (High priority does not authorize autonomous execution).
"""

from __future__ import annotations

from typing import List, Tuple

from core.action_contract import RiskLevel
from core.proactive_opportunity_contract import ProactiveOpportunityContract


class OpportunityPrioritizationEngine:
    """
    Ranks proactive opportunities according to importance, urgency, evidence confidence, and risk profile.
    """

    def calculate_priority_score(self, opp: ProactiveOpportunityContract) -> float:
        """
        Formula:
        PRIORITY = 0.25 * IMP + 0.20 * URG + 0.20 * CONF + 0.15 * VAL + 0.10 * ALIGN + 0.10 * RISK_RED - PENALTIES
        """
        goal_alignment = 0.90 if opp.source_goal_id else 0.50
        risk_reduction = 0.80 if opp.risk_level == RiskLevel.READ_ONLY else 0.30

        raw_score = (
            0.25 * opp.importance
            + 0.20 * opp.urgency
            + 0.20 * opp.confidence
            + 0.15 * opp.estimated_value
            + 0.10 * goal_alignment
            + 0.10 * risk_reduction
        )

        # Penalize low confidence (< 0.70)
        if opp.confidence < 0.70:
            raw_score -= 0.20

        # Penalize high risk
        if opp.risk_level in [RiskLevel.HIGH_RISK, RiskLevel.DESTRUCTIVE]:
            raw_score -= 0.15

        return max(0.0, min(1.0, raw_score))

    def rank_opportunities(
        self,
        opportunities: List[ProactiveOpportunityContract],
    ) -> List[Tuple[ProactiveOpportunityContract, float]]:
        """
        Returns sorted list of (opportunity, priority_score) in descending order.
        """
        scored = [(opp, self.calculate_priority_score(opp)) for opp in opportunities if opp.is_active()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# Global singleton instance
opportunity_prioritization_engine = OpportunityPrioritizationEngine()
