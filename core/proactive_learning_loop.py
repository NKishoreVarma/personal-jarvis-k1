"""
Proactive Learning Loop for MARK XLVIII / JARVIS.
Reinforces high-value proactive suggestions and suppresses declined patterns
through feedback collection and bounded score adaptation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.interruption_budget_manager import interruption_budget_manager
from core.proactive_opportunity_detector import ProactiveOpportunity
from core.proactive_suggestion_manager import ProactiveSuggestion, proactive_suggestion_manager


class ProactiveLearningLoop:
    """
    Collects user responses to suggestions and dynamically adapts opportunity weights.
    """

    def __init__(self):
        # Map: (project_name, action_type) -> score_modifier (-0.5 to +0.3)
        self._learned_preferences: Dict[str, float] = {}

    def _get_key(self, project: str, action: str) -> str:
        return f"{project.lower().strip()}::{action.lower().strip()}"

    def record_feedback(
        self,
        suggestion: ProactiveSuggestion,
        accepted: bool,
        resulted_in_success: bool = True,
    ) -> float:
        """
        Adapts score modifier for the given project & action pattern.
        """
        key = self._get_key(suggestion.project_name, suggestion.suggested_action)
        current = self._learned_preferences.get(key, 0.0)

        if accepted:
            proactive_suggestion_manager.mark_accepted(suggestion.suggestion_id)
            interruption_budget_manager.record_outcome(suggestion.suggested_action, accepted=True)
            new_val = min(0.30, current + 0.10)
        else:
            proactive_suggestion_manager.mark_declined(suggestion.suggestion_id)
            interruption_budget_manager.record_outcome(suggestion.suggested_action, accepted=False)
            new_val = max(-0.50, current - 0.20)

        self._learned_preferences[key] = new_val
        return new_val

    def get_score_modifier(self, project: str, action: str) -> float:
        """Returns learned confidence modifier for project action."""
        key = self._get_key(project, action)
        return self._learned_preferences.get(key, 0.0)

    def apply_learning_to_opportunity(self, opportunity: ProactiveOpportunity) -> ProactiveOpportunity:
        """Adjusts confidence based on prior learned feedback."""
        mod = self.get_score_modifier(opportunity.project_name, opportunity.suggested_action)
        opportunity.confidence = max(0.10, min(0.99, opportunity.confidence + mod))
        return opportunity

    def clear_all(self) -> None:
        self._learned_preferences.clear()


# Global singleton instance
proactive_learning_loop = ProactiveLearningLoop()
