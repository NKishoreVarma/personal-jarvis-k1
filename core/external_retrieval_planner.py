"""
External Retrieval Planner for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Formulates bounded, targeted search queries and source constraints from verified knowledge gaps.
Enforces limits: Max 5 sources per cycle, max 3 query variants, strict timeout, and no recursive loops.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.external_knowledge_contract import SourceCategory


@dataclass
class ExternalRetrievalPlan:
    query_objective: str
    search_queries: List[str]
    allowed_categories: List[SourceCategory]
    max_sources: int = 5
    freshness_requirements: str = "recent"
    project_relevance: str = "FLOW"
    timeout_s: float = 5.0
    stop_conditions: List[str] = field(default_factory=lambda: ["found_official_match", "timeout_exceeded"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_objective": self.query_objective,
            "search_queries": self.search_queries,
            "allowed_categories": [c.value for c in self.allowed_categories],
            "max_sources": self.max_sources,
            "freshness_requirements": self.freshness_requirements,
            "project_relevance": self.project_relevance,
            "timeout_s": self.timeout_s,
            "stop_conditions": self.stop_conditions,
        }


class ExternalRetrievalPlanner:
    """
    Constructs bounded retrieval plans with strict query constraints and source limits.
    """

    def create_retrieval_plan(
        self,
        query: str,
        project_scope: str = "FLOW",
        error_context: Optional[str] = None,
    ) -> ExternalRetrievalPlan:
        """
        Builds a bounded retrieval plan with at most 3 focused query variants.
        """
        clean_q = query.strip()
        variants: List[str] = [clean_q]

        # Add framework or project context variant
        if project_scope and project_scope.upper() not in clean_q.upper():
            variants.append(f"{clean_q} {project_scope}")

        # Add error context variant if present
        if error_context:
            err_snippet = error_context.split("\n")[0][:60].strip()
            variants.append(f"{clean_q} {err_snippet}")

        # Enforce maximum 3 query variants
        bounded_queries = variants[:3]

        # Prioritized categories
        categories = [
            SourceCategory.OFFICIAL_DOCUMENTATION,
            SourceCategory.PROJECT_REPOSITORY,
            SourceCategory.PACKAGE_DOCUMENTATION,
            SourceCategory.TECHNICAL_ARTICLE,
            SourceCategory.SEARCH_RESULT,
        ]

        return ExternalRetrievalPlan(
            query_objective=f"Resolve knowledge gap for '{clean_q}'",
            search_queries=bounded_queries,
            allowed_categories=categories,
            max_sources=5,  # Enforce max 5 sources
            freshness_requirements="recent",
            project_relevance=project_scope,
            timeout_s=5.0,
        )


# Global singleton instance
external_retrieval_planner = ExternalRetrievalPlanner()
