"""
Skill Candidate Evaluator for Capability Evolution in MARK XLVIII / JARVIS.
Screens candidate skills across multi-factor reliability, safety, input stability, and verification criteria.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.evolved_skill_contract import EvolvedSkillContract, SkillStatus


class CandidateEvaluationOutcome(str, Enum):
    PROMOTE_TO_TESTING = "PROMOTE_TO_TESTING"
    RETAIN_AS_CANDIDATE = "RETAIN_AS_CANDIDATE"
    REJECT = "REJECT"


class SkillCandidateEvaluator:
    """
    Evaluates discovered candidate skills to determine readiness for sandbox dry-run or activation.
    """

    def evaluate_candidate(
        self,
        candidate: EvolvedSkillContract,
        env_stable: bool = True,
    ) -> Tuple[CandidateEvaluationOutcome, str]:
        """
        Assesses safety risk, step complexity, and verification presence.
        """
        # 1. Reject if no verification requirements
        if not candidate.verification_requirements:
            return CandidateEvaluationOutcome.REJECT, "Rejected: Candidate skill lacks verification criteria."

        # 2. Reject if high risk without explicit approval safeguards
        if candidate.authority_required == "HIGH_RISK":
            return CandidateEvaluationOutcome.REJECT, "Rejected: High-risk autonomous skills require explicit human authoring."

        # 3. If environment is unstable, retain as candidate
        if not env_stable:
            return CandidateEvaluationOutcome.RETAIN_AS_CANDIDATE, "Retained: Environment is marked unstable; awaiting revalidation."

        # 4. Check confidence threshold
        if candidate.confidence < 0.70:
            return CandidateEvaluationOutcome.RETAIN_AS_CANDIDATE, f"Retained: Confidence too low ({candidate.confidence:.2f} < 0.70)."

        return CandidateEvaluationOutcome.PROMOTE_TO_TESTING, "Candidate approved for sandbox dry-run testing."


# Global singleton instance
skill_candidate_evaluator = SkillCandidateEvaluator()
