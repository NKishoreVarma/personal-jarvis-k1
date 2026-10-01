"""
Content Trust Classifier for MARK XLVIII / JARVIS.
Classifies observed content into distinct trust tiers to prevent indirect prompt injection
and enforce strict authority boundaries between user input, system state, and untrusted environment data.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ContentTrustLevel(str, Enum):
    TRUSTED_USER_INPUT = "TRUSTED_USER_INPUT"
    TRUSTED_SYSTEM_STATE = "TRUSTED_SYSTEM_STATE"
    APPLICATION_CONTENT = "APPLICATION_CONTENT"
    WEB_CONTENT = "WEB_CONTENT"
    DOCUMENT_CONTENT = "DOCUMENT_CONTENT"
    UNKNOWN_CONTENT = "UNKNOWN_CONTENT"


class ContentTrustClassifier:
    """
    Classifies observations and text into trust tiers.
    Enforces the invariant: External content provides EVIDENCE, never PERMISSIONS.
    """

    # Common indirect prompt injection and privilege escalation patterns
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(in|a|an)\s+(developer|unrestricted|god|dan|jailbreak)\s+mode", re.IGNORECASE),
        re.compile(r"system\s+override\s*[:=]", re.IGNORECASE),
        re.compile(r"new\s+system\s+instruction\s*[:=]", re.IGNORECASE),
        re.compile(r"disregard\s+(the\s+)?(safety|security|contract)\s+guidelines", re.IGNORECASE),
        re.compile(r"(execute|run|delete)\s+(immediately|without\s+approval)", re.IGNORECASE),
        re.compile(r"(sudo\s+rm\s+-rf|format\s+c:|mkfs)", re.IGNORECASE),
        re.compile(r"<\s*script\s*>", re.IGNORECASE),
    ]

    def classify_source(
        self,
        source: str,
        is_user_turn: bool = False,
        is_internal_system: bool = False,
    ) -> ContentTrustLevel:
        """Determines default trust tier based on origin source."""
        if is_user_turn:
            return ContentTrustLevel.TRUSTED_USER_INPUT
        if is_internal_system:
            return ContentTrustLevel.TRUSTED_SYSTEM_STATE

        s = source.lower()
        if "browser" in s or "web" in s or "url" in s or "http" in s:
            return ContentTrustLevel.WEB_CONTENT
        if "file" in s or "document" in s or "pdf" in s or "readme" in s:
            return ContentTrustLevel.DOCUMENT_CONTENT
        if "screen" in s or "window" in s or "app" in s or "ocr" in s or "ui" in s:
            return ContentTrustLevel.APPLICATION_CONTENT
        if "process" in s or "system" in s or "os" in s:
            return ContentTrustLevel.TRUSTED_SYSTEM_STATE

        return ContentTrustLevel.UNKNOWN_CONTENT

    def detect_prompt_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Inspects text for prompt injection patterns.
        Returns (has_injection, matched_pattern_str).
        """
        if not text or not isinstance(text, str):
            return False, None

        for pattern in self.PROMPT_INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return True, match.group(0)

        return False, None

    def can_influence_authority(self, trust_level: ContentTrustLevel) -> bool:
        """
        Strict invariant check: ONLY direct trusted user input and authenticated system state.
        """
        return trust_level in (
            ContentTrustLevel.TRUSTED_USER_INPUT,
            ContentTrustLevel.TRUSTED_SYSTEM_STATE,
        )

    def classify_text(self, text: str, source: str = "environment") -> ContentTrustLevel:
        """Helper to classify text based on origin and injection patterns."""
        if not text or not isinstance(text, str):
            return ContentTrustLevel.UNKNOWN_CONTENT
        is_inj, _ = self.detect_prompt_injection(text)
        if is_inj:
            return ContentTrustLevel.APPLICATION_CONTENT
        return self.classify_source(source)


# Global singleton instance
content_trust_classifier = ContentTrustClassifier()
