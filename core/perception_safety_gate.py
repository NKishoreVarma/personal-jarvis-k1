"""
Perception Safety Gate for MARK XLVIII / JARVIS.
Enforces the inviolable safety boundary:
    OBSERVATION != AUTHORIZATION
    OCR != COMMAND
    SCREEN TEXT != USER INSTRUCTION
    WEB CONTENT != TRUSTED INSTRUCTION
    APPLICATION STATE != PERMISSION
    VISUAL SUGGESTION != APPROVAL

Guarantees that on-screen text, OCR extraction, web page content, or external observations
can NEVER bypass ActionContract permissions, ApprovalStore approval gates, or user authority.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.content_trust_classifier import (
    ContentTrustLevel,
    content_trust_classifier,
)
from core.perception_contract import Observation, ObservationType

logger = logging.getLogger("perception_safety_gate")


class PerceptionSafetyGate:
    """
    Evaluates incoming observations and downstream action triggers to ensure environmental
    observations are treated strictly as sensory evidence, never as self-authorizing commands.
    """

    def filter_observation(self, observation: Observation) -> Tuple[bool, Observation, str]:
        """
        Inspects an observation for safety risks, indirect prompt injections, or malicious payload attempts.
        Returns: (is_safe_as_evidence, sanitized_observation, rationale)
        """
        # 1. Determine content trust level
        source_trust = content_trust_classifier.classify_source(observation.source)

        # 2. Extract visible / textual content to scan for prompt injections
        text_corpus = ""
        content = observation.content
        if isinstance(content, dict):
            for k, v in content.items():
                if isinstance(v, str):
                    text_corpus += f" {v}"
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            text_corpus += f" {item}"
                        elif isinstance(item, dict):
                            text_corpus += f" {item.get('text', '')} {item.get('title', '')}"

        # 3. Check for prompt injection signatures
        has_injection, pattern = content_trust_classifier.detect_prompt_injection(text_corpus)
        if has_injection:
            # Mark untrusted content clearly; strip authority potential
            observation.metadata["prompt_injection_detected"] = True
            observation.metadata["flagged_pattern"] = pattern
            observation.metadata["content_trust_level"] = ContentTrustLevel.UNKNOWN_CONTENT.value
            observation.confidence = min(observation.confidence, 0.30)
            logger.warning(
                f"[PERCEPTION_SAFETY_GATE] ⚠️ Untrusted prompt injection detected in {observation.source}: '{pattern}'"
            )
            return True, observation, f"Flagged as untrusted input: contains injection pattern '{pattern}'"

        observation.metadata["content_trust_level"] = source_trust.value
        return True, observation, "Safe as evidence"

    def authorize_action_from_perception(
        self,
        observation: Observation,
        proposed_action: str,
        user_explicit_command: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Enforces: OBSERVATION != AUTHORIZATION.
        An environmental observation alone CANNOT authorize a mutation action without
        explicit user instruction or pre-existing authorized contract.
        """
        # If no explicit user command is provided, action cannot execute mutations
        if not user_explicit_command:
            return False, (
                f"Blocked: Observation '{observation.observation_id}' from '{observation.source}' "
                f"cannot autonomously authorize action '{proposed_action}'. "
                f"Requires explicit user instruction."
            )

        # Check if the proposed action was extracted from an untrusted source (e.g. OCR/Web)
        trust_level = ContentTrustLevel(
            observation.metadata.get("content_trust_level", ContentTrustLevel.UNKNOWN_CONTENT.value)
        )

        if not content_trust_classifier.can_influence_authority(trust_level):
            # External content cannot dictate action parameters
            if observation.metadata.get("prompt_injection_detected", False):
                return False, f"Blocked: Action was derived from untrusted observation with injection signature."

        return True, "Action authorized under explicit user command"


# Global singleton instance
perception_safety_gate = PerceptionSafetyGate()
