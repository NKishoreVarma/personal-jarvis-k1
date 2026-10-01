"""
Graceful Shutdown Manager for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Coordinates controlled shutdown sequences, checkpoints active tasks without marking them failed,
and cleanly stops background monitors and heartbeat threads.
Enforces rule: GRACEFUL SHUTDOWN MUST NOT MARK ACTIVE TASKS AS FAILED (Marks them RECOVERY_REQUIRED).
"""

from __future__ import annotations

import signal
import sys
from typing import Callable, List, Optional

from core.checkpoint_manager import checkpoint_manager
from core.durable_task_contract import DurableTaskStatus
from core.heartbeat_manager import heartbeat_manager
from core.runtime_contract import RuntimeStatus
from core.runtime_state_store import runtime_state_store


class GracefulShutdownManager:
    """
    Executes staged shutdown and preserves active task state for post-restart recovery.
    """

    def __init__(self):
        self._shutting_down = False
        self._custom_cleanup_hooks: List[Callable[[], None]] = []

    def register_cleanup_hook(self, hook: Callable[[], None]) -> None:
        self._custom_cleanup_hooks.append(hook)

    def attach_signal_handlers(self) -> None:
        """Attaches handlers for SIGINT and SIGTERM."""
        try:
            signal.signal(signal.SIGINT, lambda s, f: self.execute_shutdown("SIGINT"))
            signal.signal(signal.SIGTERM, lambda s, f: self.execute_shutdown("SIGTERM"))
        except Exception:
            # Signal handling might be restricted in non-main threads
            pass

    def execute_shutdown(self, reason: str = "User request") -> None:
        """
        Executes complete graceful shutdown sequence.
        """
        if self._shutting_down:
            return
        self._shutting_down = True

        runtime = heartbeat_manager.current_runtime
        if runtime:
            runtime.runtime_status = RuntimeStatus.SHUTTING_DOWN
            runtime.shutdown_requested = True
            runtime_state_store.save_runtime(runtime)

        print(f"[SHUTDOWN] 🛑 Initiating graceful shutdown ({reason})...")

        # 1. Checkpoint active tasks as RECOVERY_REQUIRED (never FAILED)
        active_tasks = runtime_state_store.load_active_tasks()
        for t in active_tasks:
            if t.status in [DurableTaskStatus.RUNNING, DurableTaskStatus.PENDING, DurableTaskStatus.WAITING, DurableTaskStatus.VERIFYING]:
                t.status = DurableTaskStatus.RECOVERY_REQUIRED
                t.touch()
                checkpoint_manager.create_checkpoint(t.goal_id, t, reason=f"shutdown:{reason}")
                runtime_state_store.save_task(t)

        # 2. Run custom cleanup hooks
        for hook in self._custom_cleanup_hooks:
            try:
                hook()
            except Exception as e:
                print(f"[SHUTDOWN] Warning running cleanup hook: {e}")

        # 3. Stop Heartbeat Loop
        heartbeat_manager.stop_heartbeat()

        # 4. Mark Runtime STOPPED
        if runtime:
            runtime.runtime_status = RuntimeStatus.STOPPED
            runtime.touch_heartbeat()
            runtime_state_store.save_runtime(runtime)

        print("[SHUTDOWN] ✅ Graceful shutdown complete.")


# Global singleton instance
graceful_shutdown_manager = GracefulShutdownManager()
