"""
Memory Context Builder for MARK XLVIII / JARVIS.
Constructs concise, bounded memory context blocks for autonomous problem solving
without polluting context or leaking unverified assumptions.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.memory_contract import MemoryContract
from core.memory_retriever import memory_retriever


class MemoryContextBuilder:
    """
    Constructs bounded memory summaries for the reasoning engine.
    """

    def build_reasoning_memory_context(
        self,
        project_name: str,
        issue_description: str = "",
        max_items: int = 3,
    ) -> Dict[str, Any]:
        """
        Retrieves and formats top relevant memories into a clean operational summary.
        """
        query = f"{project_name} {issue_description}".strip()
        memories = memory_retriever.retrieve_relevant(query=query, project_name=project_name, top_k=max_items)

        if not memories:
            return {
                "has_memory": False,
                "summary": "No prior experience or configuration recorded for this task.",
                "memories": [],
            }

        summaries: List[str] = []
        for m in memories:
            summaries.append(f"• [{m.memory_type.value}] {m.subject}: {m.content} (Confidence: {m.confidence:.2f}, State: {m.verification_state.value})")

        return {
            "has_memory": True,
            "summary": "\n".join(summaries),
            "memories": [m.to_dict() for m in memories],
            "top_memory": memories[0],
        }


# Global singleton instance
memory_context_builder = MemoryContextBuilder()
