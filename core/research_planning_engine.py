"""
Research Planning Engine for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Decomposes high-level knowledge gaps into targeted, bounded sub-questions and builds research execution plans.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from core.knowledge_gap_contract import KnowledgeGapContract, KnowledgeGapState, KnowledgeGapType
from core.research_task_contract import (
    ResearchTaskContract,
    create_research_task,
)


class ResearchPlanningEngine:
    """
    Formulates bounded research task plans from detected knowledge gaps.
    """

    def plan_research(
        self,
        gap: KnowledgeGapContract,
    ) -> Tuple[Optional[ResearchTaskContract], str]:
        """
        Decomposes the gap question into sub-questions and configures source constraints.
        """
        sub_questions: List[str] = []
        q_lower = gap.question.lower()

        if gap.gap_type == KnowledgeGapType.DEPENDENCY_GAP or "dependency" in q_lower or "version" in q_lower:
            sub_questions = [
                f"What changed in the dependency version referenced in '{gap.question}'?",
                "Are there documented breaking changes or compatibility deprecations?",
                "Does the local project stack trace match the documented failure signature?",
            ]
        elif gap.gap_type == KnowledgeGapType.DOCUMENTATION_GAP or "docs" in q_lower or "api" in q_lower:
            sub_questions = [
                f"What is the official API specification for '{gap.question}'?",
                "What are the required parameters and expected return types?",
            ]
        elif gap.gap_type == KnowledgeGapType.SOURCE_CONFLICT:
            sub_questions = [
                f"What are the exact conflicting claims regarding '{gap.question}'?",
                "Which primary source has the highest authority and recency?",
                "Can local environment inspection directly corroborate one of the claims?",
            ]
        else:
            sub_questions = [
                f"What are the primary facts explaining '{gap.question}'?",
                "Is there direct empirical evidence available in the local repository?",
            ]

        task, msg = create_research_task(
            gap_id=gap.gap_id,
            question=gap.question,
            sub_questions=sub_questions,
            scope=gap.project_id,
            project_id=gap.project_id,
            goal_id=gap.goal_id,
            max_sources=5,
            max_depth=2,
            time_budget_seconds=30.0,
        )

        if task:
            gap.state = KnowledgeGapState.RESEARCH_PLANNED

        return task, msg


# Global singleton instance
research_planning_engine = ResearchPlanningEngine()
