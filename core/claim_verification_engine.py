"""
Claim Verification Engine for Evidence-Grounded Decision Making in MARK XLVIII / JARVIS.
Validates external technical claims against the local project environment (e.g. package.json,
actual directory layout, dependency trees) before claims can influence repair planning.
Enforces rule: Only ENVIRONMENT_SUPPORTED or stronger evidence may influence autonomous repair plans.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.external_knowledge_contract import ExternalKnowledgeContract, VerificationState


class ClaimVerificationLevel(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
    MULTI_SOURCE_SUPPORTED = "MULTI_SOURCE_SUPPORTED"
    ENVIRONMENT_SUPPORTED = "ENVIRONMENT_SUPPORTED"
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"
    CONTRADICTED = "CONTRADICTED"


class ClaimVerificationEngine:
    """
    Validates retrieved claims against the physical filesystem and environment context.
    """

    def verify_claim_against_environment(
        self,
        item: ExternalKnowledgeContract,
        project_config: Optional[Dict[str, Any]] = None,
        local_files: Optional[List[str]] = None,
    ) -> Tuple[ClaimVerificationLevel, str]:
        """
        Validates whether the external claim matches the active local environment.
        """
        cfg = project_config or {}
        files = local_files or []

        for claim in item.claims:
            claim_lower = claim.lower()

            # 1. Version incompatibility check
            if "next.js 15" in claim_lower or "next 15" in claim_lower:
                local_ver = str(cfg.get("dependencies", {}).get("next", "")).lower()
                if "15" in local_ver:
                    item.verification_state = VerificationState.VERIFIED
                    return (
                        ClaimVerificationLevel.ENVIRONMENT_SUPPORTED,
                        "Claim matches local project Next.js 15 configuration.",
                    )
                elif "14" in local_ver or "13" in local_ver:
                    item.verification_state = VerificationState.CONTRADICTED
                    return (
                        ClaimVerificationLevel.CONTRADICTED,
                        f"Claim targets Next.js 15, but local project uses Next.js {local_ver}.",
                    )

            # 2. Config file check (e.g. next.config.mjs vs next.config.js)
            if "next.config.mjs" in claim_lower:
                if any("next.config.mjs" in f for f in files):
                    item.verification_state = VerificationState.VERIFIED
                    return (
                        ClaimVerificationLevel.ENVIRONMENT_SUPPORTED,
                        "Confirmed next.config.mjs exists in local project.",
                    )

        if item.verification_state == VerificationState.CORROBORATED:
            return ClaimVerificationLevel.MULTI_SOURCE_SUPPORTED, "Claim supported by multiple external sources but unverified locally."

        return ClaimVerificationLevel.SOURCE_SUPPORTED, "Claim is supported by external source only."


# Global singleton instance
claim_verification_engine = ClaimVerificationEngine()
