"""
Execution Planner for MARK XLVIII / JARVIS.
Classifies tasks by complexity (SIMPLE, MULTI_STEP, COMPLEX) and generates
deterministic or Gemini-structured execution plans with dependency and negative constraint enforcement.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from core.conversation_manager import conversation_manager
from core.task_decomposer import task_decomposer


class TaskComplexity(Enum):
    SIMPLE = "simple"
    MULTI_STEP = "multi_step"
    COMPLEX = "complex"


class ExecutionPlanner:
    """
    Coordinates task decomposition, pronoun resolution, complexity classification, and plan generation.
    """

    def __init__(self, decomposer=None, conv_mgr=None):
        self.decomposer = decomposer or task_decomposer
        self.conv_mgr = conv_mgr or conversation_manager

    def classify_complexity(self, text: str) -> TaskComplexity:
        """
        Determines whether a command is SIMPLE, MULTI_STEP, or COMPLEX.
        """
        cleaned = text.strip().lower()

        # Complex reasoning triggers
        complex_keywords = ["understand", "summarize", "analyze", "explain why", "inspect and tell me", "what do i need to reply"]
        if any(k in cleaned for k in complex_keywords):
            return TaskComplexity.COMPLEX

        # Decompose to check for multi-step triggers
        decomp = self.decomposer.decompose(text)
        if decomp.get("is_multi_step") or len(decomp.get("steps", [])) > 1:
            return TaskComplexity.MULTI_STEP

        return TaskComplexity.SIMPLE

    def plan_task(self, text: str) -> Dict[str, Any]:
        """
        Generates an executable structured plan for a user request.
        """
        # 1. Resolve pronouns using active conversation context
        resolved_text = self.conv_mgr.resolve_entity(text)

        # 2. Classify complexity
        complexity = self.classify_complexity(resolved_text)

        # 3. Decompose task
        decomp = self.decomposer.decompose(resolved_text)

        # 4. Record active goal in conversation manager
        self.conv_mgr.set_active_goal(resolved_text)

        return {
            "original_query": text,
            "resolved_query": resolved_text,
            "complexity": complexity.value,
            "is_multi_step": decomp.get("is_multi_step", False),
            "steps": decomp.get("steps", []),
            "constraints": decomp.get("constraints", []),
            "prohibit_send": decomp.get("prohibit_send", False),
        }


execution_planner = ExecutionPlanner()
