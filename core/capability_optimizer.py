"""
Capability Optimizer for MARK XLVIII / JARVIS.
Applies bounded strategy ranking modifiers, skill confidence calibration, and workflow tuning
from quality-gated feedback signals.
Enforces invariant: OPTIMIZATION != SELF-MODIFICATION (Source code, ActionContract, and ApprovalStore are immutable).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.capability_performance_tracker import CapabilityType, capability_performance_tracker
from core.learning_feedback_engine import FeedbackSignal, learning_feedback_engine
from core.learning_quality_gate import learning_quality_gate
from core.outcome_evaluator import OutcomeEvaluation
from core.skill_contract import SkillStatus
from core.skill_registry import skill_registry


class CapabilityOptimizer:
    """
    Optimizes capability rankings and skill weights within strict safety boundaries.
    """

    def __init__(self):
        self._ranking_modifiers: Dict[str, float] = {}  # capability_id -> modifier (-2.0 to +1.0)
        self.learning_enabled: bool = True

    def set_learning_enabled(self, enabled: bool) -> None:
        self.learning_enabled = enabled

    def optimize_capability(
        self,
        capability_id: str,
        evaluation: OutcomeEvaluation,
        capability_type: CapabilityType = CapabilityType.STRATEGY,
    ) -> Optional[FeedbackSignal]:
        """
        Processes an outcome evaluation through the quality gate and applies bounded score updates.
        """
        if not self.learning_enabled:
            return None

        # 1. Quality Gate
        admissible, reason = learning_quality_gate.validate_evaluation(evaluation)
        if not admissible:
            return None

        # 2. Performance Tracking
        capability_performance_tracker.record_performance(capability_id, evaluation, capability_type)

        # 3. Feedback Generation
        sig = learning_feedback_engine.generate_feedback_signal(capability_id, evaluation)

        # 4. Apply Ranking Modifier (Bounded between -2.0 and +1.0)
        current_mod = self._ranking_modifiers.get(capability_id, 0.0)
        new_mod = max(-2.0, min(1.0, current_mod + sig.ranking_modifier))
        self._ranking_modifiers[capability_id] = round(new_mod, 3)

        # 5. If capability is a registered Skill, update SkillContract
        if capability_type == CapabilityType.SKILL:
            skill = skill_registry.retrieve_skill(capability_id)
            if skill:
                if evaluation.success:
                    skill_registry.reinforce_skill(capability_id)
                else:
                    skill_registry.record_failure(capability_id, error="Evaluated outcome failure")
                if sig.requires_degradation:
                    skill.status = SkillStatus.DEGRADED

        return sig

    def get_ranking_modifier(self, capability_id: str) -> float:
        """Returns active ranking modifier for capability."""
        return self._ranking_modifiers.get(capability_id, 0.0)

    def reset_capability(self, capability_id: str) -> None:
        self._ranking_modifiers.pop(capability_id, None)
        capability_performance_tracker.reset_capability(capability_id)

    def clear_all(self) -> None:
        self._ranking_modifiers.clear()
        capability_performance_tracker.clear_all()


# Global singleton instance
capability_optimizer = CapabilityOptimizer()
