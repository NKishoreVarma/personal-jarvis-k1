"""
Streaming Intent Engine for MARK XLVIII / JARVIS.
Incrementally extracts intents, entities, locations, and operations from partial transcripts
in real-time without blocking the audio loop or calling cloud LLMs.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StreamingIntent:
    turn_id: str
    intent_type: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    stable: bool = False
    raw_text: str = ""
    updated_at: float = field(default_factory=time.monotonic)


class StreamingIntentEngine:
    """
    Fast, deterministic streaming intent classifier and entity extractor.
    """

    KNOWN_APPS = {
        "chrome", "safari", "whatsapp", "slack", "spotify", "vscode",
        "visual studio code", "finder", "notes", "terminal", "iterm",
        "calculator", "messages", "settings", "system settings",
    }

    LOCATION_KEYWORDS = {"desktop", "projects", "developer", "workspace", "downloads", "documents"}

    def __init__(self):
        self._turn_history: Dict[str, List[StreamingIntent]] = {}

    def process_partial(self, turn_id: str, partial_text: str) -> StreamingIntent:
        """
        Consumes streaming transcript fragment and produces an updated StreamingIntent.
        """
        clean = partial_text.strip().lower()
        now = time.monotonic()

        if not clean:
            intent = StreamingIntent(
                turn_id=turn_id,
                intent_type="UNKNOWN",
                confidence=0.0,
                entities={},
                stable=False,
                raw_text=partial_text,
                updated_at=now,
            )
            self._record_intent(turn_id, intent)
            return intent

        # 1. Deterministic Local Utility Commands
        if any(w in clean for w in ["what time", "current time", "what's the time", "tell me the time"]):
            intent = StreamingIntent(
                turn_id=turn_id,
                intent_type="GET_TIME",
                confidence=0.95,
                entities={},
                stable=True,
                raw_text=partial_text,
                updated_at=now,
            )
            self._record_intent(turn_id, intent)
            return intent

        if any(w in clean for w in ["what date", "today's date", "what is today", "what day"]):
            intent = StreamingIntent(
                turn_id=turn_id,
                intent_type="GET_DATE",
                confidence=0.95,
                entities={},
                stable=True,
                raw_text=partial_text,
                updated_at=now,
            )
            self._record_intent(turn_id, intent)
            return intent

        if clean in ("mute", "unmute", "stop", "cancel"):
            intent = StreamingIntent(
                turn_id=turn_id,
                intent_type="CONTROL_COMMAND",
                confidence=0.98,
                entities={"action": clean},
                stable=True,
                raw_text=partial_text,
                updated_at=now,
            )
            self._record_intent(turn_id, intent)
            return intent

        # 2. Project Operations (e.g. "open FLOW from my Desktop and run the server")
        m_proj = re.search(
            r"(?:open|run|start)\s+(?:the\s+)?(?:project\s+)?([a-zA-Z0-9\._-]+)(?:\s+from\s+(?:my\s+)?([a-zA-Z0-9\._-]+))?",
            clean,
        )
        if m_proj:
            cand = m_proj.group(1)
            loc = m_proj.group(2)
            if cand and cand not in self.KNOWN_APPS:
                # Check for explicit server run trigger
                is_run_server = any(w in clean for w in ["run the server", "start the server", "run server", "start server", "run dev"])
                entities = {"project": cand}
                if loc:
                    entities["location"] = loc

                if is_run_server:
                    entities["action"] = "run_server"
                    intent_type = "RUN_PROJECT"
                    conf = 0.98 if loc else 0.90
                else:
                    intent_type = "PROJECT_OPERATION"
                    conf = 0.92 if loc else 0.80

                intent = StreamingIntent(
                    turn_id=turn_id,
                    intent_type=intent_type,
                    confidence=conf,
                    entities=entities,
                    stable=(conf >= 0.90),
                    raw_text=partial_text,
                    updated_at=now,
                )
                self._record_intent(turn_id, intent)
                return intent

        # 3. Application Operations (e.g. "open WhatsApp", "switch to Chrome")
        m_app = re.search(r"(?:open|launch|switch\s+to|start|close|quit)\s+([a-zA-Z0-9\._-]+)", clean)
        if m_app:
            app_cand = m_app.group(1)
            if app_cand in self.KNOWN_APPS:
                is_close = any(clean.startswith(w) for w in ["close", "quit", "exit"])
                intent_type = "CLOSE_APP" if is_close else "OPEN_APP"
                entities = {"app_name": app_cand}

                # Sub-target extraction (e.g. "open WhatsApp and message John")
                m_sub = re.search(r"(?:and\s+)?(?:open\s+(?:my\s+)?chat\s+with|search\s+for|find)\s+(.+)", clean)
                if m_sub:
                    entities["target"] = m_sub.group(1).strip()

                conf = 0.95 if "target" in entities else 0.88
                intent = StreamingIntent(
                    turn_id=turn_id,
                    intent_type=intent_type,
                    confidence=conf,
                    entities=entities,
                    stable=True,
                    raw_text=partial_text,
                    updated_at=now,
                )
                self._record_intent(turn_id, intent)
                return intent

        # 4. Fallback / Complex Information Search
        tokens = clean.split()
        if len(tokens) == 1 and tokens[0] in ("open", "run", "start", "find", "search"):
            conf = 0.30
        else:
            conf = min(0.70, 0.30 + len(tokens) * 0.08)

        intent = StreamingIntent(
            turn_id=turn_id,
            intent_type="COMPLEX_QUERY",
            confidence=conf,
            entities={"raw_query": clean},
            stable=False,
            raw_text=partial_text,
            updated_at=now,
        )
        self._record_intent(turn_id, intent)
        return intent

    def _record_intent(self, turn_id: str, intent: StreamingIntent) -> None:
        if turn_id not in self._turn_history:
            self._turn_history[turn_id] = []
        self._turn_history[turn_id].append(intent)

    def get_turn_history(self, turn_id: str) -> List[StreamingIntent]:
        return list(self._turn_history.get(turn_id, []))

    def clear_turn(self, turn_id: str) -> None:
        self._turn_history.pop(turn_id, None)


# Global singleton instance
streaming_intent_engine = StreamingIntentEngine()
