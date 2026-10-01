"""
Heartbeat Manager for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Maintains asynchronous heartbeat pulses and detects stale/crashed previous runtime sessions.
Enforces zero blocking on microphone, audio playback, or local intent routing paths.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from typing import Callable, Optional

from core.runtime_contract import RuntimeContract, RuntimeStatus, create_runtime_contract
from core.runtime_state_store import runtime_state_store


class HeartbeatManager:
    """
    Coordinates asynchronous heartbeat writing and previous crash detection.
    """

    HEARTBEAT_INTERVAL = 2.0  # seconds
    STALE_RUNTIME_THRESHOLD = 10.0  # seconds

    def __init__(self):
        self.current_runtime: Optional[RuntimeContract] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_crash_detected: Optional[Callable[[RuntimeContract], None]] = None

    def initialize_runtime(
        self,
        runtime_id: Optional[str] = None,
        on_crash_detected: Optional[Callable[[RuntimeContract], None]] = None,
    ) -> RuntimeContract:
        """
        Loads prior runtime, checks for unexpected crashes, and registers new runtime session.
        """
        self._on_crash_detected = on_crash_detected
        prior = runtime_state_store.load_runtime()

        gen = 0
        if prior:
            gen = prior.recovery_generation
            # Check if prior crashed (stale heartbeat without graceful shutdown)
            if prior.is_heartbeat_stale(self.STALE_RUNTIME_THRESHOLD) and not prior.shutdown_requested:
                prior.runtime_status = RuntimeStatus.CRASHED
                prior.crash_detected = True
                gen += 1
                if self._on_crash_detected:
                    self._on_crash_detected(prior)
                print(f"[HEARTBEAT] ⚠️ Detected crash in prior runtime '{prior.runtime_id}' (PID {prior.process_id}).")

        self.current_runtime = create_runtime_contract(runtime_id=runtime_id, recovery_generation=gen)
        self.current_runtime.runtime_status = RuntimeStatus.RUNNING
        runtime_state_store.save_runtime(self.current_runtime)

        return self.current_runtime

    def start_heartbeat_loop(self) -> None:
        """Starts asynchronous background heartbeat thread."""
        if self._running or not self.current_runtime:
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._thread.start()

    def _heartbeat_worker(self) -> None:
        while not self._stop_event.is_set():
            if self.current_runtime:
                self.current_runtime.touch_heartbeat()
                runtime_state_store.save_runtime(self.current_runtime)
            self._stop_event.wait(self.HEARTBEAT_INTERVAL)

    def pulse_heartbeat(self) -> None:
        """Manual heartbeat pulse for sync operations."""
        if self.current_runtime:
            self.current_runtime.touch_heartbeat()
            runtime_state_store.save_runtime(self.current_runtime)

    def stop_heartbeat(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None


# Global singleton instance
heartbeat_manager = HeartbeatManager()
