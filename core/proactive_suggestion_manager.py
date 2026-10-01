"""
Proactive Suggestion Manager for MARK XLVIII / JARVIS.
Formulates concise, human-like voice suggestions from verified opportunities.
Enforces zero internal jargon, strict deduplication, and lifecycle tracking
(PREPARED -> SHOWN -> ACCEPTED / DECLINED / EXPIRED / INVALIDATED).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.proactive_opportunity_detector import OpportunityType, ProactiveOpportunity


class SuggestionState(str, Enum):
    PREPARED = "PREPARED"
    SHOWN = "SHOWN"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


@dataclass
class ProactiveSuggestion:
    suggestion_id: str
    opportunity_id: str
    project_name: str
    prompt_text: str
    suggested_action: str
    action_arguments: Dict[str, Any] = field(default_factory=dict)
    state: SuggestionState = SuggestionState.PREPARED
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 45.0)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "opportunity_id": self.opportunity_id,
            "project_name": self.project_name,
            "prompt_text": self.prompt_text,
            "suggested_action": self.suggested_action,
            "action_arguments": self.action_arguments,
            "state": self.state.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


class ProactiveSuggestionManager:
    """
    Manages active proactive suggestions, formatting, deduplication, and resolution tracking.
    """

    def __init__(self):
        self._suggestions: Dict[str, ProactiveSuggestion] = {}
        self._recent_prompts: List[Dict[str, Any]] = []

    def format_suggestion_text(self, opportunity: ProactiveOpportunity) -> str:
        """
        Formats opportunity into a concise, human-like voice prompt without chain-of-thought.
        """
        proj = opportunity.project_name
        op_type = opportunity.opportunity_type

        if op_type == OpportunityType.PROJECT_STARTED_OPEN_BROWSER:
            return f"{proj} is ready. Want me to open it?"

        elif op_type == OpportunityType.REPEATED_FAILURE_APPLY_SKILL:
            return f"I found the same issue on {proj} from before. I can try the previous fix."

        elif op_type == OpportunityType.MISSING_DEPENDENCY_REPAIR:
            return f"{proj} seems to be missing dependencies. Want me to install them?"

        elif op_type == OpportunityType.RELATED_TASK_SUGGESTION:
            return f"{proj} is running. Would you like me to test it?"

        return f"Would you like me to continue with {proj}?"

    def create_suggestion(self, opportunity: ProactiveOpportunity) -> Optional[ProactiveSuggestion]:
        """
        Creates suggestion, ensuring prompt is not duplicate or recently declined.
        """
        prompt = self.format_suggestion_text(opportunity)

        # Check for recent duplicate prompt within 30s
        now = time.time()
        for r in self._recent_prompts:
            if r.get("prompt") == prompt and now - r.get("time", 0) < 30.0:
                return None

        sug = ProactiveSuggestion(
            suggestion_id=f"sug_{uuid.uuid4().hex[:8]}",
            opportunity_id=opportunity.opportunity_id,
            project_name=opportunity.project_name,
            prompt_text=prompt,
            suggested_action=opportunity.suggested_action,
            action_arguments=opportunity.arguments,
        )

        self._suggestions[sug.suggestion_id] = sug
        self._recent_prompts.append({"prompt": prompt, "time": now, "id": sug.suggestion_id})
        # Keep recent prompts bounded
        if len(self._recent_prompts) > 20:
            self._recent_prompts.pop(0)

        return sug

    def get_suggestion(self, suggestion_id: str) -> Optional[ProactiveSuggestion]:
        return self._suggestions.get(suggestion_id)

    def mark_shown(self, suggestion_id: str) -> None:
        sug = self._suggestions.get(suggestion_id)
        if sug:
            sug.state = SuggestionState.SHOWN

    def mark_accepted(self, suggestion_id: str) -> None:
        sug = self._suggestions.get(suggestion_id)
        if sug:
            sug.state = SuggestionState.ACCEPTED

    def mark_declined(self, suggestion_id: str) -> None:
        sug = self._suggestions.get(suggestion_id)
        if sug:
            sug.state = SuggestionState.DECLINED

    def invalidate_project_suggestions(self, project_name: str) -> None:
        for sug in self._suggestions.values():
            if sug.project_name.lower() == project_name.lower() and sug.state in [SuggestionState.PREPARED, SuggestionState.SHOWN]:
                sug.state = SuggestionState.INVALIDATED

    def get_latest_active_suggestion(self) -> Optional[ProactiveSuggestion]:
        for sug in reversed(list(self._suggestions.values())):
            if sug.state in [SuggestionState.PREPARED, SuggestionState.SHOWN] and not sug.is_expired():
                return sug
        return None

    def clear_all(self) -> None:
        self._suggestions.clear()
        self._recent_prompts.clear()


# Global singleton instance
proactive_suggestion_manager = ProactiveSuggestionManager()
