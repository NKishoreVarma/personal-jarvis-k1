"""
Event Bus for MARK XLVIII / JARVIS.
Provides a lightweight, non-blocking, asynchronous local pub/sub event system
connecting background tasks, project monitors, system monitors, and notification managers.
"""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


class EventType:
    TASK_STARTED = "TASK_STARTED"
    TASK_PROGRESS = "TASK_PROGRESS"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_CANCELLED = "TASK_CANCELLED"
    PROJECT_READY = "PROJECT_READY"
    SERVER_CRASHED = "SERVER_CRASHED"
    APP_CLOSED = "APP_CLOSED"
    APP_OPENED = "APP_OPENED"
    DOWNLOAD_COMPLETED = "DOWNLOAD_COMPLETED"
    LONG_TASK_TIMEOUT = "LONG_TASK_TIMEOUT"
    SYSTEM_ALERT = "SYSTEM_ALERT"


@dataclass
class Event:
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    source: str = "system"


class EventBus:
    """
    Asynchronous and synchronous in-memory event dispatcher.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], Any]]] = {}
        self._global_subscribers: List[Callable[[Event], Any]] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], Any]) -> None:
        """Subscribes a callback to a specific event type (or '*' for all events)."""
        if event_type == "*":
            if handler not in self._global_subscribers:
                self._global_subscribers.append(handler)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Event], Any]) -> None:
        """Unsubscribes a callback."""
        if event_type == "*":
            if handler in self._global_subscribers:
                self._global_subscribers.remove(handler)
        elif event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(
        self,
        event_or_type: Any,
        payload: Optional[Dict[str, Any]] = None,
        source: str = "system",
    ) -> Event:
        """
        Dispatches an event non-blockingly to all registered subscribers.
        Supports passing either an Event instance or event_type string.
        """
        if isinstance(event_or_type, Event):
            event = event_or_type
            event_type = event.event_type
        else:
            event_type = str(event_or_type)
            event = Event(event_type=event_type, payload=payload or {}, source=source)

        handlers = list(self._subscribers.get(event_type, [])) + list(self._global_subscribers)

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        pass
                else:
                    handler(event)
            except Exception as e:
                print(f"[EVENT_BUS] Error in event handler for {event_type}: {e}")

        return event

    def clear(self) -> None:
        self._subscribers.clear()
        self._global_subscribers.clear()


# Global singleton event bus
event_bus = EventBus()
