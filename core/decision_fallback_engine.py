"""
Decision Fallback Engine for System 1 in MARK XLVIII / JARVIS.
Provides deterministic fallback resolution and structured System 2 escalations when System 1 is unavailable or abstains.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionSource,
    DecisionType,
    create_decision_result,
)


class DecisionFallbackEngine:
    """
    Executes fallback heuristic routing or constructs System 2 escalation payloads.
    """

    def resolve_fallback(
        self,
        category: DecisionCategory,
        context: str,
        options: Optional[List[str]] = None,
        reason: str = "SYSTEM1_UNAVAILABLE",
        trace_id: Optional[str] = None,
    ) -> DecisionResult:
        """
        Computes a safe deterministic fallback decision.
        """
        t0 = time.perf_counter()
        ctx_lower = context.lower()

        selected: Optional[str] = None
        score: Optional[float] = None
        decision_type = DecisionType.CHOICE

        if category == DecisionCategory.URGENCY:
            decision_type = DecisionType.SCORE
            score = 0.50
            if any(w in ctx_lower for w in ["emergency", "critical", "urgent"]):
                score = 0.90
            elif any(w in ctx_lower for w in ["low", "later"]):
                score = 0.20

        elif category == DecisionCategory.RISK:
            selected = "medium"
            if any(w in ctx_lower for w in ["delete", "drop", "destroy", "format", "rm -rf"]):
                selected = "high"
            elif any(w in ctx_lower for w in ["read", "view", "check", "status", "list"]):
                selected = "low"

        elif category == DecisionCategory.AGENT_ROUTING:
            selected = "general_reasoner"
            if any(w in ctx_lower for w in ["code", "bug", "syntax", "refactor", "function"]):
                selected = "coder"
            elif any(w in ctx_lower for w in ["search", "look up", "docs", "documentation"]):
                selected = "researcher"
            elif any(w in ctx_lower for w in ["schedule", "remind", "later", "tomorrow"]):
                selected = "scheduler"
            elif any(w in ctx_lower for w in ["see", "screen", "window", "image", "ui"]):
                selected = "vision"

        elif category == DecisionCategory.INTENT:
            selected = "task"
            if any(w in ctx_lower for w in ["what", "who", "why", "how", "tell me"]):
                selected = "informational"
            elif any(w in ctx_lower for w in ["hi", "hello", "thanks", "good morning"]):
                selected = "conversational"

        else:
            selected = options[0] if options else "default"

        dt = (time.perf_counter() - t0) * 1000
        res, _ = create_decision_result(
            decision_type=decision_type,
            category=category,
            context=context,
            selected_option=selected,
            score=score,
            confidence=0.80,
            abstained=False,
            model_or_checkpoint="fallback_heuristics",
            language="en",
            latency_ms=dt,
            evidence=[f"Fallback heuristic applied due to: {reason}"],
            reason_code=f"FALLBACK_{reason}",
            source=DecisionSource.FALLBACK_HEURISTIC,
            trace_id=trace_id,
        )
        return res  # type: ignore


# Global singleton instance
decision_fallback_engine = DecisionFallbackEngine()
