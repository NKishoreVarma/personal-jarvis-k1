"""
Notification Manager & Rate Limiter for MARK XLVIII / JARVIS.
Provides activity-aware, priority-gated notifications:
- Prioritizes LOW, NORMAL, HIGH, CRITICAL notifications.
- Queues notifications while USER_SPEAKING or JARVIS_PROCESSING.
- Dispatches cleanly when USER_IDLE.
- Rate-limits duplicate and frequent background alerts.
"""

from __future__ import annotations

import collections
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.event_bus import Event, EventType, event_bus


class NotificationPriority(str, Enum):
    LOW = "LOW"            # UI only (no speech)
    NORMAL = "NORMAL"      # UI + optional voice when idle
    HIGH = "HIGH"          # Spoken proactively when user is idle
    CRITICAL = "CRITICAL"  # Spoken immediately regardless of state


class UserActivityState(str, Enum):
    USER_IDLE = "USER_IDLE"
    USER_SPEAKING = "USER_SPEAKING"
    JARVIS_PROCESSING = "JARVIS_PROCESSING"
    JARVIS_SPEAKING = "JARVIS_SPEAKING"


@dataclass
class Notification:
    notification_id: str
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: str = "general"
    created_at: float = field(default_factory=time.monotonic)
    spoken: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationRateLimiter:
    """
    Prevents notification spam through cooldowns, duplicate suppression, and frequency caps.
    """

    def __init__(self, max_spoken_per_minute: int = 6, duplicate_cooldown_sec: float = 15.0):
        self.max_spoken_per_minute = max_spoken_per_minute
        self.duplicate_cooldown_sec = duplicate_cooldown_sec
        self._spoken_timestamps: collections.deque = collections.deque()
        self._last_event_timestamps: Dict[str, float] = {}

    def should_allow_speech(self, category: str, message: str) -> bool:
        now = time.monotonic()

        # 1. Clean old timestamps (> 60s)
        while self._spoken_timestamps and (now - self._spoken_timestamps[0]) > 60.0:
            self._spoken_timestamps.popleft()

        # 2. Check maximum spoken rate
        if len(self._spoken_timestamps) >= self.max_spoken_per_minute:
            print(f"[NOTIFICATION_LIMITER] Suppressing spoken notification (rate limit {self.max_spoken_per_minute}/min reached)")
            return False

        # 3. Duplicate suppression
        msg_key = f"{category}::{message.strip().lower()}"
        last_time = self._last_event_timestamps.get(msg_key, 0.0)
        if (now - last_time) < self.duplicate_cooldown_sec:
            print(f"[NOTIFICATION_LIMITER] Suppressing duplicate notification within {self.duplicate_cooldown_sec}s: '{message}'")
            return False

        # Register speech
        self._spoken_timestamps.append(now)
        self._last_event_timestamps[msg_key] = now
        return True


class NotificationManager:
    """
    Coordinates UI and proactive spoken notifications for JARVIS.
    """

    def __init__(self, rate_limiter: Optional[NotificationRateLimiter] = None):
        self.user_state = UserActivityState.USER_IDLE
        self.rate_limiter = rate_limiter or NotificationRateLimiter()
        self._pending_queue: List[Notification] = []
        self._history: List[Notification] = []
        self._speech_sink: Optional[Callable[[str], Any]] = None

        # Wire event bus handlers
        self._subscribe_to_events()

    def set_speech_sink(self, sink: Callable[[str], Any]) -> None:
        """Sets the audio playback / TTS callback for spoken notifications."""
        self._speech_sink = sink

    def set_user_state(self, state: UserActivityState) -> None:
        """Updates the current activity state and flushes pending queue if idle."""
        prev = self.user_state
        self.user_state = state
        print(f"[NOTIFICATION_MANAGER] User state: {prev.value} -> {state.value}")

        if state == UserActivityState.USER_IDLE and self._pending_queue:
            self.flush_pending_notifications()

    def notify(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Dispatches or queues a notification based on user activity state and priority.
        """
        notif = Notification(
            notification_id=f"notif_{uuid.uuid4().hex[:8]}",
            title=title,
            message=message,
            priority=priority,
            category=category,
            metadata=metadata or {},
        )
        self._history.append(notif)
        if len(self._history) > 50:
            self._history.pop(0)

        # 1. CRITICAL: Speak immediately
        if priority == NotificationPriority.CRITICAL:
            self._speak(notif)
            return notif

        # 2. LOW: UI notification only
        if priority == NotificationPriority.LOW:
            print(f"[NOTIFICATION_UI] [{title}] {message}")
            return notif

        # 3. NORMAL / HIGH: If user is speaking or JARVIS processing, queue
        if self.user_state in (UserActivityState.USER_SPEAKING, UserActivityState.JARVIS_PROCESSING):
            print(f"[NOTIFICATION_MANAGER] Queued ({priority.value}) while user active: '{message}'")
            self._pending_queue.append(notif)
            return notif

        # 4. If idle, deliver
        self._speak(notif)
        return notif

    def flush_pending_notifications(self) -> List[Notification]:
        """Delivers queued notifications when the user becomes idle."""
        flushed = []
        while self._pending_queue:
            notif = self._pending_queue.pop(0)
            prefix = "By the way, " if not notif.message.lower().startswith("by the way") else ""
            notif.message = f"{prefix}{notif.message}"
            self._speak(notif)
            flushed.append(notif)
        return flushed

    def _speak(self, notif: Notification) -> None:
        """Delivers notification through speech sink if rate limiter permits."""
        print(f"[NOTIFICATION_MANAGER] [{notif.priority.value}] {notif.title}: {notif.message}")
        if self.rate_limiter.should_allow_speech(notif.category, notif.message):
            notif.spoken = True
            if self._speech_sink:
                try:
                    self._speech_sink(notif.message)
                except Exception as e:
                    print(f"[NOTIFICATION_MANAGER] Speech sink error: {e}")

    def _subscribe_to_events(self) -> None:
        """Listens to background task and system events."""
        event_bus.subscribe(EventType.PROJECT_READY, self._on_project_ready)
        event_bus.subscribe(EventType.SERVER_CRASHED, self._on_server_crashed)
        event_bus.subscribe(EventType.SYSTEM_ALERT, self._on_system_alert)

    def _on_project_ready(self, event: Event) -> None:
        proj = event.payload.get("project", "Project")
        url = event.payload.get("url", "localhost")
        self.notify(
            title="Project Ready",
            message=f"{proj} is ready on {url}.",
            priority=NotificationPriority.NORMAL,
            category="project",
        )

    def _on_server_crashed(self, event: Event) -> None:
        proj = event.payload.get("project", "Server")
        code = event.payload.get("exit_code", 1)
        self.notify(
            title="Server Stopped",
            message=f"{proj} stopped unexpectedly with code {code}.",
            priority=NotificationPriority.HIGH,
            category="server_crash",
        )

    def _on_system_alert(self, event: Event) -> None:
        msg = event.payload.get("message", "System Alert")
        crit = event.payload.get("critical", False)
        self.notify(
            title="System Alert",
            message=msg,
            priority=NotificationPriority.CRITICAL if crit else NotificationPriority.NORMAL,
            category="system",
        )


notification_manager = NotificationManager()
