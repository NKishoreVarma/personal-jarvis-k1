"""
Skill Verification Engine for Capability Evolution in MARK XLVIII / JARVIS.
Verifies post-execution state transitions and enforces the distinction between
merely completing an action vs confirming a verified operational outcome.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.evolved_skill_contract import EvolvedSkillContract, SkillStatus


class SkillVerificationOutcome(str, Enum):
    ACTION_COMPLETED = "ACTION_COMPLETED"
    OUTPUT_VERIFIED = "OUTPUT_VERIFIED"
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"
    FAILED = "FAILED"


class SkillVerificationEngine:
    """
    Evaluates execution outcomes against skill verification criteria.
    """

    def verify_execution(
        self,
        skill: EvolvedSkillContract,
        step_results: List[Dict[str, Any]],
        observed_outcome: Dict[str, Any],
    ) -> Tuple[SkillVerificationOutcome, str]:
        """
        Determines verification strength of executed skill run.
        """
        if not step_results:
            return SkillVerificationOutcome.FAILED, "Execution recorded 0 completed steps."

        # Check if all steps succeeded
        all_steps_ok = all(r.get("success", False) for r in step_results)
        if not all_steps_ok:
            return SkillVerificationOutcome.FAILED, "One or more execution steps reported failure."

        # Check outcome confirmation
        is_responsive = observed_outcome.get("is_responsive") or observed_outcome.get("reachable") or observed_outcome.get("verified_outcome")
        if is_responsive:
            return SkillVerificationOutcome.OUTCOME_VERIFIED, "Outcome independently confirmed and verified."

        if observed_outcome.get("output_present"):
            return SkillVerificationOutcome.OUTPUT_VERIFIED, "Step outputs confirmed, but live outcome unverified."

        return SkillVerificationOutcome.ACTION_COMPLETED, "Actions finished with basic completion only."


# Global singleton instance
skill_verification_engine = SkillVerificationEngine()
