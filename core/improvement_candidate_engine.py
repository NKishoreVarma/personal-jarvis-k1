"""
Improvement Candidate Engine for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Transforms verified learning signals into candidate improvements while rejecting speculative optimizations.
Enforces rule: Candidates must cite supporting evidence references and cannot alter authority rules.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from core.action_contract import RiskLevel
from core.improvement_opportunity_contract import (
    ImprovementOpportunityContract,
    ImprovementState,
    ImprovementType,
    create_improvement_opportunity,
)
from core.learning_signal_detector import LearningSignal, LearningSignalType


class ImprovementCandidateEngine:
    """
    Generates structured, verifiable improvement candidate proposals from strong learning signals.
    """

    def __init__(self):
        self._existing_patterns: Set[str] = set()

    def generate_candidate_from_signal(
        self,
        signal: LearningSignal,
        baseline_metrics: Optional[Dict[str, float]] = None,
    ) -> Tuple[Optional[ImprovementOpportunityContract], str]:
        """
        Creates a bounded improvement proposal from a learning signal.
        """
        # 1. Reject speculative signals lacking evidence
        if not signal.evidence_references:
            return None, "Rejected: Learning signal lacks supporting evidence references."

        # 2. Prevent duplicate candidates for same pattern key
        if signal.pattern_key in self._existing_patterns:
            return None, f"Rejected: Candidate already exists for pattern '{signal.pattern_key}'."

        # 3. Determine improvement type and affected component
        if signal.signal_type == LearningSignalType.FAILURE_PATTERN:
            imp_type = ImprovementType.RELIABILITY_IMPROVEMENT
            title = f"Resolve Recurring Failure: {signal.pattern_key}"
            desc = f"Pre-emptively resolve failure pattern by adding pre-flight checks for '{signal.pattern_key}'."
            component = "workflow_diagnostics"
        elif signal.signal_type == LearningSignalType.EFFICIENCY_PATTERN:
            imp_type = ImprovementType.PERFORMANCE_IMPROVEMENT
            title = f"Optimize Execution Latency: {signal.pattern_key}"
            desc = f"Streamline workflow execution to eliminate slow steps in '{signal.pattern_key}'."
            component = "execution_pipeline"
        elif signal.signal_type == LearningSignalType.USER_CORRECTION_PATTERN:
            imp_type = ImprovementType.WORKFLOW_SIMPLIFICATION
            title = f"Incorporate User Correction: {signal.pattern_key}"
            desc = f"Align execution strategy with explicit user correction: '{signal.description}'."
            component = "preference_aligner"
        else:
            imp_type = ImprovementType.SKILL_IMPROVEMENT
            title = f"Strengthen Capability: {signal.pattern_key}"
            desc = f"Reinforce verified success workflow for '{signal.pattern_key}'."
            component = "capability_registry"

        candidate = create_improvement_opportunity(
            improvement_type=imp_type,
            title=title,
            description=desc,
            affected_component=component,
            source_signals=[signal.pattern_key],
            evidence_references=signal.evidence_references,
            expected_improvement="Reduce failure rate / improve execution efficiency without safety changes.",
            baseline_metrics=baseline_metrics or {"success_rate": 0.70, "avg_duration": 8.0},
            risk_level=RiskLevel.READ_ONLY,
        )

        self._existing_patterns.add(signal.pattern_key)
        return candidate, "Improvement candidate created successfully."

    def clear(self) -> None:
        self._existing_patterns.clear()


# Global singleton instance
improvement_candidate_engine = ImprovementCandidateEngine()
