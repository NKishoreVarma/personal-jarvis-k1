"""
Response Length Policy for MARK XLVIII / JARVIS.
Controls the verbosity and conciseness of spoken feedback across the system.
Enforces the principle: "Do not speak just because you can speak. Speak only when the information helps the user."
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ResponseVerbosity(str, Enum):
    MINIMAL = "MINIMAL"    # 1-3 words: "Okay.", "On it.", "Done."
    SHORT = "SHORT"        # 1 concise sentence: "FLOW is running.", "Opening Chrome."
    NORMAL = "NORMAL"      # 1-2 concise sentences: "FLOW didn't start because port 3000 is in use."
    DETAILED = "DETAILED"  # Multi-sentence: Only when explicitly requested ("Why?", "Explain", etc.)


class ResponseLengthPolicy:
    """
    Evaluates context to determine the appropriate response verbosity level.
    """

    WHY_KEYWORDS = {"why", "how come", "what happened", "explain", "details", "elaborate", "reason"}

    def determine_verbosity(
        self,
        raw_user_text: str,
        is_failure: bool = False,
        is_clarification: bool = False,
        debug_mode: bool = False,
    ) -> ResponseVerbosity:
        """
        Determines the appropriate verbosity level in < 1ms.
        """
        text_lower = raw_user_text.strip().lower()

        # 1. User explicitly requested detailed explanation
        if any(kw in text_lower for kw in self.WHY_KEYWORDS) or debug_mode:
            return ResponseVerbosity.DETAILED

        # 2. Clarification requires concise explanation of ambiguous choices
        if is_clarification:
            return ResponseVerbosity.SHORT

        # 3. Failures provide a short actionable reason by default (NORMAL), but never raw stack traces
        if is_failure:
            return ResponseVerbosity.NORMAL

        # 4. Standard default is SHORT
        return ResponseVerbosity.SHORT

    def truncate_to_verbosity(self, text: str, verbosity: ResponseVerbosity) -> str:
        """
        Ensures a spoken string conforms strictly to the target verbosity.
        """
        text = text.strip()
        if not text:
            return ""

        if verbosity == ResponseVerbosity.MINIMAL:
            # First 3-4 words or first short sentence
            sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
            if sentences:
                words = sentences[0].split()
                if len(words) <= 4:
                    return f"{sentences[0]}."
                return " ".join(words[:3]) + "."
            return "Okay."

        if verbosity == ResponseVerbosity.SHORT:
            # First sentence only
            for delim in [".", "!", "?"]:
                if delim in text:
                    return text.split(delim)[0].strip() + "."
            return text

        if verbosity == ResponseVerbosity.NORMAL:
            # At most two sentences
            sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
            if len(sentences) > 2:
                return f"{sentences[0]}. {sentences[1]}."
            return text

        # DETAILED: Return full formatted text
        return text


# Global singleton instance
response_length_policy = ResponseLengthPolicy()
