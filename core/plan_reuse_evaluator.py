"""
Plan Reuse Evaluator for MARK XLVIII / JARVIS.
Assesses whether a historical plan or verified skill template can be safely reused
under current real-time environmental observations.
Enforces invariant: CURRENT REALITY > HISTORICAL PLAN.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.plan_contract import PlanContract
from core.skill_contract import SkillContract


class PlanReuseEvaluator:
    """
    Evaluates compatibility of historical plans against live environment observations.
    """

    def evaluate_reuse(
        self,
        historical_plan: PlanContract,
        current_project: str,
        current_evidence: List[Dict[str, Any]],
    ) -> Tuple[bool, str, float]:
        """
        Determines if historical plan is valid for immediate reuse.
        Returns: (is_compatible, reason, confidence)
        """
        # 1. Project match
        plan_proj = historical_plan.verification_criteria.get("project", "")
        if plan_proj.lower() != current_project.lower():
            return False, f"Project mismatch: {plan_proj} != {current_project}", 0.0

        # 2. Plan expiration
        if historical_plan.is_expired():
            return False, "Historical plan expired", 0.0

        # 3. Check for contradiction against current evidence
        evidence_texts = [str(e) for e in current_evidence]
        for assump in historical_plan.assumptions:
            for ev in evidence_texts:
                if "error" in ev.lower() and "conflict" in ev.lower() and "no conflict" in assump.lower():
                    return False, f"Assumption '{assump}' contradicted by current evidence '{ev}'", 0.30

        return True, "Historical plan compatible with current verified state", 0.94


# Global singleton instance
plan_reuse_evaluator = PlanReuseEvaluator()
