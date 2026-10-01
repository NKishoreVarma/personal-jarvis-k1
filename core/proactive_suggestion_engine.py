"""
Proactive Suggestion Engine for Proactive Task Orchestration in MARK XLVIII / JARVIS.
Transforms prioritized opportunities into actionable, concise suggestions respecting user interaction style.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from core.interaction_style_manager import InteractionStyle, interaction_style_manager
from core.proactive_opportunity_contract import OpportunityState, ProactiveOpportunityContract
from core.proactive_safety_gate import proactive_safety_gate


class ProactiveSuggestionEngine:
    """
    Formulates natural language suggestions for top-ranked proactive opportunities.
    """

    def __init__(self):
        self.proactive_enabled: bool = True
        self._last_suggested_id: Optional[str] = None

    def set_proactive_enabled(self, enabled: bool) -> None:
        self.proactive_enabled = enabled

    def format_suggestion(
        self,
        opportunity: ProactiveOpportunityContract,
    ) -> Optional[str]:
        """
        Formats opportunity into a concise, polite suggestion.
        """
        if not self.proactive_enabled:
            return None

        is_safe, _ = proactive_safety_gate.validate_opportunity_for_suggestion(opportunity)
        if not is_safe:
            return None

        opportunity.state = OpportunityState.SUGGESTED
        self._last_suggested_id = opportunity.opportunity_id

        # Generate response respecting interaction style
        if interaction_style_manager.active_style == InteractionStyle.CONCISE:
            return f"Next recommended step: {opportunity.title}."
        elif interaction_style_manager.active_style == InteractionStyle.SILENT_BACKGROUND:
            return None

        return f"I noticed a high-priority opportunity: {opportunity.title}. {opportunity.description}"


# Global singleton instance
proactive_suggestion_engine = ProactiveSuggestionEngine()
