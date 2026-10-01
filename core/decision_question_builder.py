"""
Decision Question Builder for System 1 Decision Engine (Laya Integration) in MARK XLVIII / JARVIS.
Builds typed decision prompts and option sets across all 10 System 1 operational categories.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from core.decision_contract import DecisionCategory, DecisionType

CATEGORY_OPTIONS: Dict[DecisionCategory, List[str]] = {
    DecisionCategory.INTENT: [
        "informational",
        "conversational",
        "task",
        "coding",
        "research",
        "planning",
        "automation",
        "system_control",
        "memory",
        "scheduling",
        "proactive",
        "multi_agent",
        "high_risk",
    ],
    DecisionCategory.AGENT_ROUTING: [
        "planner",
        "researcher",
        "coder",
        "browser",
        "memory",
        "vision",
        "scheduler",
        "executor",
        "verifier",
        "general_reasoner",
    ],
    DecisionCategory.SKILL_SELECTION: [
        "choose_existing_skill",
        "create_new_plan",
        "invoke_general_reasoning",
        "ask_clarification",
        "abstain",
    ],
    DecisionCategory.STRATEGY_SELECTION: [
        "direct_answer",
        "retrieve_then_answer",
        "plan_then_execute",
        "research_then_synthesize",
        "delegate_to_agent",
        "ask_user",
        "defer",
        "abstain",
    ],
    DecisionCategory.RISK: [
        "low",
        "medium",
        "high",
        "unknown",
    ],
    DecisionCategory.PROACTIVE: [
        "irrelevant",
        "potentially_useful",
        "actionable",
        "urgent",
    ],
    DecisionCategory.RESEARCH: [
        "no_research_needed",
        "local_memory_sufficient",
        "external_research_useful",
        "external_research_required",
        "uncertain",
    ],
    DecisionCategory.MEMORY: [
        "new",
        "likely_memory_relevant",
        "likely_related_to_prior_context",
        "ambiguous",
    ],
}


class DecisionQuestionBuilder:
    """
    Constructs formatted questions and valid candidate option lists for Laya decisions.
    """

    def build_question(
        self,
        category: DecisionCategory,
        context: str,
        custom_options: List[str] | None = None,
    ) -> Tuple[DecisionType, str, List[str]]:
        """
        Returns (decision_type, question_text, options).
        """
        if category == DecisionCategory.URGENCY:
            return (
                DecisionType.SCORE,
                f"Rate the urgency of this context on a scale from 0.0 (no urgency) to 1.0 (immediate critical urgency): '{context}'",
                [],
            )

        if category == DecisionCategory.TEMPORAL:
            options = custom_options or ["immediate", "scheduled_future", "recurring", "deferred_later", "expired"]
            return (
                DecisionType.CHOICE,
                f"Classify the temporal scheduling requirement for: '{context}'",
                options,
            )

        options = custom_options or CATEGORY_OPTIONS.get(category, ["default", "abstain"])
        return (
            DecisionType.CHOICE,
            f"Classify the {category.value} for the following context: '{context}'",
            options,
        )


# Global singleton instance
decision_question_builder = DecisionQuestionBuilder()
