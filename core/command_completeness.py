"""
Command Completeness Analyzer for MARK XLVIII / JARVIS.
Provides fast, lightweight, non-blocking linguistic heuristics to evaluate whether
a spoken voice command is complete or likely incomplete (trailing connector, hanging preposition).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, Set


class CompletenessState(str, Enum):
    COMPLETE = "COMPLETE"
    LIKELY_INCOMPLETE = "LIKELY_INCOMPLETE"
    AMBIGUOUS = "AMBIGUOUS"


class CommandCompletenessAnalyzer:
    """
    Evaluates whether an utterance represents a finished command or requires continuation grace.
    """

    TRAILING_CONNECTORS: Set[str] = {
        "and", "then", "after", "once", "when", "but", "also",
        "with", "to", "in", "on", "from", "for", "at", "about",
        "into", "or", "because", "so", "until", "while", "as",
    }

    ACTION_VERBS: Set[str] = {
        "open", "run", "start", "stop", "close", "show", "switch",
        "find", "search", "create", "delete", "send", "write", "type",
    }

    def analyze(self, text: str) -> Dict[str, any]:
        """
        Analyzes text and returns completeness state and suggested extra grace in milliseconds.
        """
        clean = text.strip().lower()
        if not clean:
            return {"state": CompletenessState.AMBIGUOUS, "extra_grace_ms": 0.0, "reason": "empty"}

        tokens = re.findall(r"\b\w+\b", clean)
        if not tokens:
            return {"state": CompletenessState.AMBIGUOUS, "extra_grace_ms": 0.0, "reason": "no_tokens"}

        last_word = tokens[-1]

        # 1. Trailing connector check: "open flow and", "run server then"
        if last_word in self.TRAILING_CONNECTORS:
            return {
                "state": CompletenessState.LIKELY_INCOMPLETE,
                "extra_grace_ms": 200.0,
                "reason": f"trailing_connector_{last_word}",
            }

        # 2. Bare action verb check: "open", "run", "send"
        if len(tokens) == 1 and tokens[0] in self.ACTION_VERBS:
            return {
                "state": CompletenessState.LIKELY_INCOMPLETE,
                "extra_grace_ms": 250.0,
                "reason": f"bare_action_verb_{tokens[0]}",
            }

        # 3. Known single-word standalone commands: "mute", "unmute", "stop", "cancel", "time"
        if len(tokens) == 1 and tokens[0] in {"mute", "unmute", "stop", "cancel", "time", "help", "pause", "resume"}:
            return {
                "state": CompletenessState.COMPLETE,
                "extra_grace_ms": 0.0,
                "reason": "standalone_keyword",
            }

        # 4. Standard complete phrase
        return {
            "state": CompletenessState.COMPLETE,
            "extra_grace_ms": 0.0,
            "reason": "complete_clause",
        }


# Global singleton
command_completeness = CommandCompletenessAnalyzer()
