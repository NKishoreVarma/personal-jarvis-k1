"""
Intervention Policy for MARK XLVIII / JARVIS.
Decides when and how JARVIS may intervene proactively without annoying the user or interrupting speech.
Enforces the strict hierarchy:
USER_SPEECH > CRITICAL_ALERT > USER_REQUEST > CLARIFICATION > TASK_FAILURE > HIGH_VALUE_PROACTIVE_INTERVENTION > VERIFIED_COMPLETION > LOW_VALUE_SUGGESTION.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from core.proactive_opportunity_detector import OpportunityValue, ProactiveOpportunity


class InterventionAction(str, Enum):
    SPEAK_NOW = "SPEAK_NOW"
    SPEAK_LATER = "SPEAK_LATER"
    VISUAL_SUGGESTION = "VISUAL_SUGGESTION"
    SILENT_PREPARE = "SILENT_PREPARE"
    SILENT_MONITOR = "SILENT_MONITOR"
    DO_NOT_INTERVENE = "DO_NOT_INTERVENE"


class InterventionPolicy:
    """
    Evaluates timing, user voice state, quiet mode, and opportunity value to decide intervention mode.
    """

    def __init__(self):
        self.quiet_mode: bool = False
        self.user_speaking: bool = False
        self.jarvis_speaking: bool = False

    def set_user_speaking(self, speaking: bool) -> None:
        self.user_speaking = speaking

    def set_jarvis_speaking(self, speaking: bool) -> None:
        self.jarvis_speaking = speaking

    def set_quiet_mode(self, enabled: bool) -> None:
        self.quiet_mode = enabled

    def decide_intervention(
        self,
        opportunity: ProactiveOpportunity,
        interruption_budget_allowed: bool = True,
    ) -> InterventionAction:
        """
        Determines the appropriate intervention action based on strict priority rules.
        """
        # Invariant 1: USER_SPEECH overrides all proactive interventions
        if self.user_speaking:
            return InterventionAction.DO_NOT_INTERVENE

        # Invariant 2: Quiet mode suppresses audible speech unless critical
        if self.quiet_mode:
            if opportunity.value_tier == OpportunityValue.CRITICAL:
                return InterventionAction.SPEAK_NOW
            elif opportunity.value_tier in [OpportunityValue.HIGH_VALUE, OpportunityValue.USEFUL]:
                return InterventionAction.SILENT_PREPARE
            return InterventionAction.DO_NOT_INTERVENE

        # Invariant 3: If JARVIS is currently speaking, defer proactive speech
        if self.jarvis_speaking:
            if opportunity.value_tier in [OpportunityValue.HIGH_VALUE, OpportunityValue.CRITICAL]:
                return InterventionAction.SPEAK_LATER
            return InterventionAction.DO_NOT_INTERVENE

        # Invariant 4: Check interruption budget
        if not interruption_budget_allowed and opportunity.value_tier != OpportunityValue.CRITICAL:
            if opportunity.value_tier == OpportunityValue.HIGH_VALUE:
                return InterventionAction.SILENT_PREPARE
            return InterventionAction.DO_NOT_INTERVENE

        # Evaluate by Value Tier
        if opportunity.value_tier == OpportunityValue.CRITICAL:
            return InterventionAction.SPEAK_NOW

        elif opportunity.value_tier == OpportunityValue.HIGH_VALUE:
            if opportunity.confidence >= 0.90 and opportunity.requires_voice_prompt:
                return InterventionAction.SPEAK_NOW
            return InterventionAction.SILENT_PREPARE

        elif opportunity.value_tier == OpportunityValue.USEFUL:
            if opportunity.requires_voice_prompt:
                return InterventionAction.SPEAK_NOW
            return InterventionAction.SILENT_MONITOR

        elif opportunity.value_tier == OpportunityValue.LOW_VALUE:
            return InterventionAction.DO_NOT_INTERVENE

        return InterventionAction.DO_NOT_INTERVENE


# Global singleton instance
intervention_policy = InterventionPolicy()
