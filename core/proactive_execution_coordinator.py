"""
Proactive Execution Coordinator for Anticipatory Task Orchestration in MARK XLVIII / JARVIS.
Coordinates end-to-end proactive loop: Detect -> Analyze -> Prioritize -> Safety Gate -> Suggest -> Await Approval -> Execute.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.collaboration_context_contract import CollaborationContextContract
from core.opportunity_detection_engine import opportunity_detection_engine
from core.opportunity_prioritization_engine import opportunity_prioritization_engine
from core.proactive_context_analyzer import proactive_context_analyzer
from core.proactive_opportunity_contract import ProactiveOpportunityContract
from core.proactive_safety_gate import proactive_safety_gate
from core.proactive_suggestion_engine import proactive_suggestion_engine


class ProactiveExecutionCoordinator:
    """
    Central orchestrator for proactive scanning, opportunity prioritization, and non-mutating suggestions.
    """

    def evaluate_proactive_pipeline(
        self,
        context: CollaborationContextContract,
        active_goals: Optional[List[Dict[str, Any]]] = None,
        runtime_health: Optional[Dict[str, Any]] = None,
        regression_signals: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Tuple[ProactiveOpportunityContract, str]]:
        """
        Executes proactive cycle and returns the top safety-cleared opportunity and its suggestion text.
        """
        # 1. Detect candidate opportunities
        raw_opps = opportunity_detection_engine.detect_opportunities(
            active_goals=active_goals,
            runtime_health=runtime_health,
            regression_signals=regression_signals,
            project_id=context.active_project or "GLOBAL",
        )
        if not raw_opps:
            return None

        # 2. Prioritize opportunities
        ranked = opportunity_prioritization_engine.rank_opportunities(raw_opps)
        if not ranked:
            return None

        top_opp, score = ranked[0]

        # 3. Safety gate check
        is_safe, reason = proactive_safety_gate.validate_opportunity_for_suggestion(top_opp)
        if not is_safe:
            return None

        # 4. Generate suggestion
        suggestion = proactive_suggestion_engine.format_suggestion(top_opp)
        if not suggestion:
            return None

        return top_opp, suggestion


# Global singleton instance
proactive_execution_coordinator = ProactiveExecutionCoordinator()
