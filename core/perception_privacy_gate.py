"""
Perception Privacy Gate for MARK XLVIII / JARVIS.
Detects, redacts, and strips sensitive credentials, API keys, passwords, bearer tokens,
private keys, and authentication cookies from environmental observations before ingestion into the World Model.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from core.perception_contract import Observation, PrivacyClassification


class PerceptionPrivacyGate:
    """
    Sanitizes observations to prevent credential leakage into persistent world models or prompts.
    """

    SECRET_PATTERNS = [
        # API Keys, secrets, tokens
        re.compile(r'(?i)(api[_-]?key|secret|token|password|auth|bearer|access[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?'),
        # Private Keys
        re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----.*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----', re.DOTALL),
        # GitHub / AWS / Generic API Tokens
        re.compile(r'\b(?:ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|AKIA[0-9A-Z]{16})\b'),
        # Bearer tokens in headers
        re.compile(r'(?i)bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*'),
        # Authentication Cookies
        re.compile(r'(?i)(sessionid|connect\.sid|remember_token)=([a-zA-Z0-9_\-\.]{12,})'),
    ]

    def redact_text(self, text: str) -> Tuple[str, bool]:
        """
        Redacts sensitive tokens from string content.
        Returns: (sanitized_text, was_redacted)
        """
        if not text or not isinstance(text, str):
            return text, False

        redacted = False
        result = text

        for pattern in self.SECRET_PATTERNS:
            if pattern.search(result):
                redacted = True
                result = pattern.sub(r'***REDACTED_CREDENTIAL***', result)

        return result, redacted

    def sanitize_dict(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Recursively sanitizes dictionary keys and values."""
        clean = {}
        any_redacted = False

        for k, v in data.items():
            # Check key name itself for sensitive keywords
            if any(s in str(k).lower() for s in ("password", "secret", "private_key", "token", "auth")):
                clean[k] = "***REDACTED_CREDENTIAL***"
                any_redacted = True
                continue

            if isinstance(v, str):
                s_val, was_r = self.redact_text(v)
                clean[k] = s_val
                if was_r:
                    any_redacted = True
            elif isinstance(v, dict):
                sub_clean, was_r = self.sanitize_dict(v)
                clean[k] = sub_clean
                if was_r:
                    any_redacted = True
            elif isinstance(v, list):
                sub_list = []
                for item in v:
                    if isinstance(item, str):
                        s_item, was_r = self.redact_text(item)
                        sub_list.append(s_item)
                        if was_r:
                            any_redacted = True
                    elif isinstance(item, dict):
                        sub_d, was_r = self.sanitize_dict(item)
                        sub_list.append(sub_d)
                        if was_r:
                            any_redacted = True
                    else:
                        sub_list.append(item)
                clean[k] = sub_list
            else:
                clean[k] = v

        return clean, any_redacted

    def filter_observation(self, observation: Observation) -> Observation:
        """
        Filters observation content and metadata through credential redaction,
        upgrading privacy classification if sensitive data is found.
        """
        # Sanitize content
        clean_content, redacted_c = self.sanitize_dict(observation.content)
        observation.content = clean_content

        # Sanitize metadata
        clean_metadata, redacted_m = self.sanitize_dict(observation.metadata)
        observation.metadata = clean_metadata

        if redacted_c or redacted_m:
            observation.privacy_classification = PrivacyClassification.RESTRICTED
            observation.metadata["credential_redacted"] = True

        return observation

    def redact_observation(self, observation: Observation) -> Tuple[Observation, int]:
        """
        Sanitizes observation and returns (cleaned_observation, redacted_count).
        """
        clean_content, redacted_c = self.sanitize_dict(observation.content)
        clean_metadata, redacted_m = self.sanitize_dict(observation.metadata)
        count = (1 if redacted_c else 0) + (1 if redacted_m else 0)
        observation.content = clean_content
        observation.metadata = clean_metadata
        if count > 0:
            observation.privacy_classification = PrivacyClassification.RESTRICTED
            observation.metadata["credential_redacted"] = True
        return observation, count


# Global singleton instance
perception_privacy_gate = PerceptionPrivacyGate()
