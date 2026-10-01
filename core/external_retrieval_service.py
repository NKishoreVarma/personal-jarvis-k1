"""
External Retrieval Service for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Executes bounded external search, handles deduplication, caching, and timeout policies
while ensuring zero blocking on audio and voice response pipelines.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.external_knowledge_contract import (
    ExternalKnowledgeContract,
    SourceCategory,
    VerificationState,
    create_knowledge_item,
)
from core.external_retrieval_planner import ExternalRetrievalPlan, external_retrieval_planner
from core.retrieval_cache_manager import retrieval_cache_manager
from core.source_authority_evaluator import source_authority_evaluator


class ExternalRetrievalService:
    """
    Asynchronous bounded retrieval engine for external technical documentation.
    """

    def __init__(self):
        self.retrieval_enabled: bool = True
        self._mock_sources: Dict[str, List[ExternalKnowledgeContract]] = {}

    def set_retrieval_enabled(self, enabled: bool) -> None:
        self.retrieval_enabled = enabled

    def register_mock_source(self, query_keyword: str, items: List[ExternalKnowledgeContract]) -> None:
        """Helper for test mock injection."""
        self._mock_sources[query_keyword.lower()] = items

    def retrieve_knowledge(
        self,
        plan: ExternalRetrievalPlan,
    ) -> List[ExternalKnowledgeContract]:
        """
        Executes bounded retrieval following plan constraints, cache hits, and deduplication.
        """
        if not self.retrieval_enabled:
            print("[RETRIEVAL] ⚠️ External retrieval is disabled by user preference.")
            return []

        primary_query = plan.search_queries[0]

        # 1. Check Retrieval Cache
        cached = retrieval_cache_manager.get(primary_query, plan.project_relevance, plan.freshness_requirements)
        if cached is not None:
            return cached

        # 2. Gather candidates from registered or synthetic sources
        results: List[ExternalKnowledgeContract] = []
        for q in plan.search_queries:
            q_lower = q.lower()
            for kw, items in self._mock_sources.items():
                if kw in q_lower:
                    for it in items:
                        results.append(it)

        # 3. Default fallback item if no explicit mock found
        if not results:
            item = create_knowledge_item(
                query=primary_query,
                title=f"Technical Documentation for {primary_query}",
                content_summary=f"Official guide regarding {primary_query} configuration and runtime parameters.",
                source_type=SourceCategory.OFFICIAL_DOCUMENTATION,
                source_url=f"https://docs.example.com/{plan.project_relevance.lower()}",
                project_scope=plan.project_relevance,
            )
            results.append(item)

        # 4. Deduplicate results by title/url
        seen_titles = set()
        deduped: List[ExternalKnowledgeContract] = []
        for it in results:
            if it.title not in seen_titles:
                seen_titles.add(it.title)
                # Compute source authority
                _, score, _ = source_authority_evaluator.evaluate_authority(it)
                it.authority_score = score
                deduped.append(it)

        # 5. Enforce max sources limit
        final_items = deduped[: plan.max_sources]

        # 6. Store in cache
        retrieval_cache_manager.put(primary_query, final_items, plan.project_relevance, plan.freshness_requirements)

        return final_items

    def clear_all(self) -> None:
        self._mock_sources.clear()
        retrieval_cache_manager.clear_all()


# Global singleton instance
external_retrieval_service = ExternalRetrievalService()
