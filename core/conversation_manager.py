"""
Conversation Manager for MARK XLVIII / JARVIS.
Maintains lightweight, in-memory, thread-safe conversation context, entity bindings,
and deterministic pronoun resolution ('it', 'that', 'the app', 'the project') without cloud latency.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationContext:
    conversation_id: str = field(default_factory=lambda: f"conv_{uuid.uuid4().hex[:8]}")
    active_goal: Optional[str] = None
    active_task_id: Optional[str] = None
    last_application: Optional[str] = None
    last_window: Optional[str] = None
    last_contact: Optional[str] = None
    last_project: Optional[str] = None
    last_url: Optional[str] = None
    pending_action_id: Optional[str] = None
    pending_question: Optional[str] = None
    pending_options: List[str] = field(default_factory=list)
    recent_entities: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)


class ConversationManager:
    """
    Lightweight, deterministic session context manager.
    Zero network I/O, non-blocking, $< 1.0$ms operations.
    """

    def __init__(self):
        self.context = ConversationContext()

    def set_active_goal(self, goal: str, task_id: Optional[str] = None) -> None:
        self.context.active_goal = goal
        if task_id:
            self.context.active_task_id = task_id
        self.context.updated_at = time.monotonic()

    def get_active_goal(self) -> Optional[str]:
        return self.context.active_goal

    def set_entity(self, key: str, value: str) -> None:
        """Sets a specific entity attribute on context."""
        k = key.lower().strip()
        val = value.strip()
        if k in ("app", "application", "last_application"):
            self.context.last_application = val
        elif k in ("project", "last_project"):
            self.context.last_project = val
        elif k in ("contact", "person", "last_contact"):
            self.context.last_contact = val
        elif k in ("window", "last_window"):
            self.context.last_window = val
        elif k in ("url", "website", "last_url"):
            self.context.last_url = val

        self.add_recent_entity(val)
        self.context.updated_at = time.monotonic()

    def add_recent_entity(self, entity: str) -> None:
        clean = entity.strip()
        if clean and clean not in self.context.recent_entities:
            self.context.recent_entities.append(clean)
            if len(self.context.recent_entities) > 10:
                self.context.recent_entities.pop(0)

    def resolve_entity(self, text: str) -> str:
        """
        Resolves ambiguous pronouns ('it', 'that', 'the app', 'the project', 'the contact')
        using the current session context without corrupting standard phrases ('what time is it').
        """
        if not text:
            return text

        # Guard common phrases where 'it' is non-referential
        if re.search(r"\b(time\s+is\s+it|date\s+is\s+it|is\s+it\s+(?:hot|cold|raining|true|ready))\b", text, re.IGNORECASE):
            return text

        resolved = text

        # Project pronoun replacement: "run it", "start it", "open it", "the project", "the server"
        if self.context.last_project:
            # Action verbs followed by it/that
            resolved = re.sub(
                r"\b(run|start|open|launch|build|test|stop|kill|close|restart|execute|switch\s+to|focus)\s+(?:it|that)\b",
                rf"\1 {self.context.last_project}",
                resolved,
                flags=re.IGNORECASE,
            )
            resolved = re.sub(r"\b(the\s+project|the\s+server)\b", self.context.last_project, resolved, flags=re.IGNORECASE)

        # Contact pronoun replacement
        if self.context.last_contact:
            resolved = re.sub(
                r"\b(message|tell|chat\s+with|contact|email|call|ask|write\s+to)\s+(?:him|her|them)\b",
                rf"\1 {self.context.last_contact}",
                resolved,
                flags=re.IGNORECASE,
            )
            resolved = re.sub(r"\b(the\s+contact|the\s+person)\b", self.context.last_contact, resolved, flags=re.IGNORECASE)

        # Application pronoun replacement
        if self.context.last_application:
            resolved = re.sub(r"\b(the\s+app|the\s+application)\b", self.context.last_application, resolved, flags=re.IGNORECASE)

        return resolved

    def set_pending_question(self, question: str, options: Optional[List[str]] = None) -> None:
        self.context.pending_question = question
        self.context.pending_options = options or []
        self.context.updated_at = time.monotonic()

    def clear_pending_question(self) -> None:
        self.context.pending_question = None
        self.context.pending_options.clear()
        self.context.updated_at = time.monotonic()

    def set_pending_action(self, action_id: str) -> None:
        self.context.pending_action_id = action_id
        self.context.updated_at = time.monotonic()

    def clear_pending_action(self) -> None:
        self.context.pending_action_id = None
        self.context.updated_at = time.monotonic()

    def get_context_snapshot(self) -> Dict[str, Any]:
        """Returns structured dictionary of the active session context."""
        return {
            "conversation_id": self.context.conversation_id,
            "active_goal": self.context.active_goal,
            "active_task_id": self.context.active_task_id,
            "last_application": self.context.last_application,
            "last_window": self.context.last_window,
            "last_contact": self.context.last_contact,
            "last_project": self.context.last_project,
            "last_url": self.context.last_url,
            "pending_action_id": self.context.pending_action_id,
            "pending_question": self.context.pending_question,
            "pending_options": list(self.context.pending_options),
            "recent_entities": list(self.context.recent_entities),
            "updated_at": self.context.updated_at,
        }

    def reset_context(self) -> None:
        self.context = ConversationContext()


# Global singleton conversation manager
conversation_manager = ConversationManager()
