"""
Runtime State Store for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Provides durable, crash-resilient file persistence for RuntimeContract, active DurableTaskContracts,
versioned checkpoints, and recovery audit history.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional

from core.durable_task_contract import DurableTaskContract
from core.runtime_contract import RuntimeContract


class RuntimeStateStore:
    """
    Storage engine for runtime lifecycle states, active task manifests, and recovery logs.
    """

    def __init__(self, base_dir: str = "data/runtime"):
        self.base_dir = base_dir
        self.runtime_file = os.path.join(self.base_dir, "runtime_state.json")
        self.tasks_file = os.path.join(self.base_dir, "active_tasks.json")
        self.checkpoints_dir = os.path.join(self.base_dir, "checkpoints")
        self.history_file = os.path.join(self.base_dir, "recovery_history.json")
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.checkpoints_dir, exist_ok=True)

    def _atomic_write_json(self, filepath: str, data: Any) -> bool:
        """Writes JSON atomically via temporary file and rename."""
        try:
            self._ensure_directories()
            dir_name = os.path.dirname(filepath)
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(data, tf, indent=2)
                tf.flush()
                os.fsync(tf.fileno())
                temp_name = tf.name
            os.replace(temp_name, filepath)
            return True
        except Exception as e:
            print(f"[RUNTIME_STORE] Error writing {filepath}: {e}")
            return False

    def save_runtime(self, runtime: RuntimeContract) -> bool:
        return self._atomic_write_json(self.runtime_file, runtime.to_dict())

    def load_runtime(self) -> Optional[RuntimeContract]:
        if not os.path.exists(self.runtime_file):
            return None
        try:
            with open(self.runtime_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return RuntimeContract.from_dict(data)
        except Exception as e:
            print(f"[RUNTIME_STORE] Warning loading runtime state: {e}")
            return None

    def save_task(self, task: DurableTaskContract) -> bool:
        tasks = self.load_active_tasks()
        # Replace or append
        updated = [t for t in tasks if t.durable_task_id != task.durable_task_id]
        updated.append(task)
        data = [t.to_dict() for t in updated]
        return self._atomic_write_json(self.tasks_file, data)

    def load_active_tasks(self) -> List[DurableTaskContract]:
        if not os.path.exists(self.tasks_file):
            return []
        try:
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                return [DurableTaskContract.from_dict(item) for item in raw]
        except Exception as e:
            print(f"[RUNTIME_STORE] Warning loading active tasks: {e}")
            return []

    def remove_task(self, durable_task_id: str) -> bool:
        tasks = self.load_active_tasks()
        remaining = [t for t in tasks if t.durable_task_id != durable_task_id]
        data = [t.to_dict() for t in remaining]
        return self._atomic_write_json(self.tasks_file, data)

    def save_checkpoint(self, checkpoint_id: str, data: Dict[str, Any]) -> bool:
        ckpt_path = os.path.join(self.checkpoints_dir, f"{checkpoint_id}.json")
        return self._atomic_write_json(ckpt_path, data)

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        ckpt_path = os.path.join(self.checkpoints_dir, f"{checkpoint_id}.json")
        if not os.path.exists(ckpt_path):
            return None
        try:
            with open(ckpt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def load_latest_checkpoint(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Finds most recent checkpoint file for target goal."""
        if not os.path.exists(self.checkpoints_dir):
            return None
        files = [f for f in os.listdir(self.checkpoints_dir) if f.startswith(f"ckpt_{goal_id}") and f.endswith(".json")]
        if not files:
            return None
        files.sort(key=lambda fn: os.path.getmtime(os.path.join(self.checkpoints_dir, fn)), reverse=True)
        return self.load_checkpoint(files[0].replace(".json", ""))

    def record_recovery(self, record: Dict[str, Any]) -> bool:
        history = self.load_recovery_history()
        history.append(record)
        if len(history) > 50:
            history.pop(0)
        return self._atomic_write_json(self.history_file, history)

    def load_recovery_history(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def clear_all(self) -> None:
        """Cleans up runtime directory for testing / reset."""
        try:
            if os.path.exists(self.base_dir):
                shutil.rmtree(self.base_dir)
            self._ensure_directories()
        except Exception:
            pass


# Global singleton instance
runtime_state_store = RuntimeStateStore()
