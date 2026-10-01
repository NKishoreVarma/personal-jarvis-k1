"""
Unified World Model for MARK XLVIII / JARVIS.
Maintains the centralized, normalized, grounded representation of the system's external environment,
active applications, open windows, screen state, project metadata, processes, browser tabs, and tasks.
Enforces the invariant: Every fact has source provenance, timestamp, confidence, and freshness.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from core.perception_contract import FreshnessState, Observation, ObservationType
from core.world_model_resolver import FactSourceTier, GroundedFact, world_model_resolver


class WorldModel:
    """
    Thread-safe, normalized environmental state repository.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._environment: Dict[str, GroundedFact] = {}
        self._application: Dict[str, GroundedFact] = {}
        self._window: Dict[str, GroundedFact] = {}
        self._screen: Dict[str, GroundedFact] = {}
        self._project: Dict[str, GroundedFact] = {}
        self._process: Dict[str, GroundedFact] = {}
        self._browser: Dict[str, GroundedFact] = {}
        self._device: Dict[str, GroundedFact] = {}
        self._task: Dict[str, GroundedFact] = {}
        self._temporal: Dict[str, GroundedFact] = {}
        self._user_interaction: Dict[str, GroundedFact] = {}
        self._last_update_time: float = 0.0

    def clear(self) -> None:
        """Resets all world model facts."""
        with self._lock:
            self._environment.clear()
            self._application.clear()
            self._window.clear()
            self._screen.clear()
            self._project.clear()
            self._process.clear()
            self._browser.clear()
            self._device.clear()
            self._task.clear()
            self._temporal.clear()
            self._user_interaction.clear()
            self._last_update_time = 0.0

    def _select_domain(self, obs_type: ObservationType) -> Dict[str, GroundedFact]:
        if obs_type in (ObservationType.SCREEN, ObservationType.USER_INTERFACE):
            return self._screen
        elif obs_type == ObservationType.WINDOW:
            return self._window
        elif obs_type == ObservationType.APPLICATION:
            return self._application
        elif obs_type == ObservationType.PROCESS:
            return self._process
        elif obs_type == ObservationType.BROWSER:
            return self._browser
        elif obs_type == ObservationType.FILESYSTEM:
            return self._project
        elif obs_type == ObservationType.SYSTEM:
            return self._device
        elif obs_type in (ObservationType.ENVIRONMENT, ObservationType.NETWORK):
            return self._environment
        elif obs_type == ObservationType.OCR:
            return self._screen
        return self._environment

    def update_observation(self, observation: Observation) -> None:
        """
        Ingests a normalized Observation and resolves conflicts across matching domain facts.
        """
        with self._lock:
            domain = self._select_domain(observation.observation_type)
            content = observation.content
            if not isinstance(content, dict):
                return

            for key, val in content.items():
                existing = domain.get(key)
                resolved = world_model_resolver.resolve_fact(
                    key=key,
                    incoming_val=val,
                    incoming_obs=observation,
                    existing_fact=existing,
                )
                domain[key] = resolved

            self._last_update_time = time.time()

    def set_task_state(self, key: str, value: Any, source: str = "task_registry", confidence: float = 1.0) -> None:
        """Manually sets active task state attributes."""
        with self._lock:
            self._task[key] = GroundedFact(
                key=key,
                value=value,
                source=source,
                tier=FactSourceTier.CURRENT_VERIFIED_OBSERVATION,
                confidence=confidence,
                timestamp=time.time(),
                freshness=FreshnessState.FRESH,
                evidence_id="task_internal",
            )

    def set_user_request(self, text: str, source: str = "voice_turn") -> None:
        """Stores active user request in user interaction domain."""
        with self._lock:
            self._user_interaction["active_request"] = GroundedFact(
                key="active_request",
                value=text,
                source=source,
                tier=FactSourceTier.CURRENT_VERIFIED_OBSERVATION,
                confidence=1.0,
                timestamp=time.time(),
                freshness=FreshnessState.FRESH,
                evidence_id="user_input",
            )

    def get_fact(self, domain_name: str, key: str) -> Optional[GroundedFact]:
        """Retrieves a specific grounded fact from a domain."""
        with self._lock:
            domains = {
                "environment": self._environment,
                "application": self._application,
                "window": self._window,
                "screen": self._screen,
                "project": self._project,
                "process": self._process,
                "browser": self._browser,
                "device": self._device,
                "task": self._task,
                "temporal": self._temporal,
                "user_interaction": self._user_interaction,
            }
            d = domains.get(domain_name.lower())
            if d:
                fact = d.get(key)
                if fact:
                    # Update freshness state on read if not already explicitly expired/stale
                    if fact.freshness not in (FreshnessState.EXPIRED, FreshnessState.STALE):
                        now = time.time()
                        elapsed = now - fact.timestamp
                        if elapsed > 60.0:
                            fact.freshness = FreshnessState.EXPIRED
                        elif elapsed > 30.0:
                            fact.freshness = FreshnessState.STALE
                        elif elapsed > 15.0:
                            fact.freshness = FreshnessState.AGING
                return fact
            return None

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns a nested dictionary snapshot of the current grounded world state."""
        with self._lock:
            def _extract_domain(d: Dict[str, GroundedFact]) -> Dict[str, Any]:
                return {k: v.value for k, v in d.items()}

            return {
                "environment": _extract_domain(self._environment),
                "application": _extract_domain(self._application),
                "window": _extract_domain(self._window),
                "screen": _extract_domain(self._screen),
                "project": _extract_domain(self._project),
                "process": _extract_domain(self._process),
                "browser": _extract_domain(self._browser),
                "device": _extract_domain(self._device),
                "task": _extract_domain(self._task),
                "temporal": _extract_domain(self._temporal),
                "user_interaction": _extract_domain(self._user_interaction),
                "last_update_time": self._last_update_time,
            }

    def get_bounded_summary(self) -> str:
        """
        Produces a concise, bounded text summary of the current grounded environment
        suitable for feeding to System 2 without causing token bloat or leaking raw binaries.
        """
        with self._lock:
            lines = ["=== GROUNDED WORLD MODEL ==="]

            # Application & Window
            active_app = self._application.get("active_application")
            focused_win = self._application.get("focused_window_title")
            if active_app or focused_win:
                lines.append(f"Active App: {active_app.value if active_app else 'None'} | Window: '{focused_win.value if focused_win else ''}'")

            # Browser
            b_active = self._browser.get("is_active")
            if b_active and b_active.value:
                b_url = self._browser.get("url")
                b_title = self._browser.get("title")
                lines.append(f"Browser: {b_title.value if b_title else ''} ({b_url.value if b_url else ''})")

            # Project
            p_branch = self._project.get("git_branch")
            p_types = self._project.get("project_types")
            if p_branch or p_types:
                lines.append(f"Project: {p_types.value if p_types else []} (branch: {p_branch.value if p_branch else 'none'})")

            # System & Health
            listening = self._device.get("listening_ports") or self._process.get("listening_ports")
            if listening and listening.value:
                lines.append(f"Listening Ports: {listening.value}")

            # Screen / OCR Errors
            ocr_errors = self._screen.get("error_snippets")
            if ocr_errors and ocr_errors.value:
                lines.append(f"On-Screen Errors: {ocr_errors.value}")

            # Active Task
            act_goal = self._task.get("active_goal")
            if act_goal:
                lines.append(f"Active Goal: {act_goal.value}")

            lines.append("============================")
            return "\n".join(lines)


# Global singleton instance
world_model = WorldModel()
