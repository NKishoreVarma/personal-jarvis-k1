"""
Checkpoint Manager for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Coordinates atomic checkpoint creation, version validation, corruption recovery,
and sensitive data filtering (rejects audio buffers, screenshots, and credentials).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.durable_task_contract import DurableTaskContract
from core.runtime_state_store import runtime_state_store

# Sensitive token pattern to sanitize
SECRET_REGEX = re.compile(
    r"(bearer\s+[a-zA-Z0-9_\-\.]{16,}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{20,}|password\s*=\s*\S+|api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


@dataclass
class CheckpointSnapshot:
    checkpoint_id: str
    goal_id: str
    version: int
    created_at: float
    task_data: Dict[str, Any]
    plan_data: Dict[str, Any]
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "goal_id": self.goal_id,
            "version": self.version,
            "created_at": self.created_at,
            "task_data": self.task_data,
            "plan_data": self.plan_data,
            "checksum": self.checksum,
            "metadata": self.metadata,
        }


class CheckpointManager:
    """
    Manages crash-safe, sanitized, versioned execution snapshots.
    """

    def __init__(self):
        self._latest_snapshots: Dict[str, CheckpointSnapshot] = {}  # goal_id -> snapshot

    def _compute_checksum(self, data_str: str) -> str:
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()[:16]

    def sanitize_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively scrubs audio packets, raw screenshots, and secrets from checkpoint data.
        """
        sanitized = {}
        for k, v in data.items():
            # Filter forbidden keys
            if k in ["audio_frames", "audio_buffer", "raw_screenshot", "screenshot_buffer", "mic_frames", "chain_of_thought"]:
                continue

            if isinstance(v, dict):
                sanitized[k] = self.sanitize_payload(v)
            elif isinstance(v, list):
                sanitized[k] = [self.sanitize_payload(item) if isinstance(item, dict) else item for item in v]
            elif isinstance(v, str):
                if SECRET_REGEX.search(v):
                    sanitized[k] = "[REDACTED_SECRET]"
                else:
                    sanitized[k] = v
            else:
                sanitized[k] = v
        return sanitized

    def create_checkpoint(
        self,
        goal_id: str,
        task: DurableTaskContract,
        plan_data: Optional[Dict[str, Any]] = None,
        reason: str = "milestone",
    ) -> Optional[CheckpointSnapshot]:
        """
        Creates, sanitizes, checksums, and atomically persists a checkpoint snapshot.
        """
        task_dict = self.sanitize_payload(task.to_dict())
        plan_dict = self.sanitize_payload(plan_data or {})

        payload_str = json.dumps({"task": task_dict, "plan": plan_dict}, sort_keys=True)
        checksum = self._compute_checksum(payload_str)

        now = time.time()
        ckpt_id = f"ckpt_{goal_id}_{int(now)}_{task.checkpoint_version}"

        snapshot = CheckpointSnapshot(
            checkpoint_id=ckpt_id,
            goal_id=goal_id,
            version=task.checkpoint_version,
            created_at=now,
            task_data=task_dict,
            plan_data=plan_dict,
            checksum=checksum,
            metadata={"reason": reason},
        )

        ok = runtime_state_store.save_checkpoint(ckpt_id, snapshot.to_dict())
        if ok:
            self._latest_snapshots[goal_id] = snapshot
            # Update task record in store
            runtime_state_store.save_task(task)
            return snapshot
        return None

    def validate_checkpoint(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates structure and checksum integrity of a checkpoint dict.
        """
        if not isinstance(data, dict):
            return False, "Checkpoint is not a dictionary"

        required = ["checkpoint_id", "goal_id", "version", "task_data", "checksum"]
        if not all(k in data for k in required):
            return False, "Missing required checkpoint fields"

        task_dict = data.get("task_data", {})
        plan_dict = data.get("plan_data", {})
        expected_checksum = data.get("checksum", "")

        payload_str = json.dumps({"task": task_dict, "plan": plan_dict}, sort_keys=True)
        computed = self._compute_checksum(payload_str)

        if computed != expected_checksum:
            return False, f"Corruption detected: checksum mismatch ({computed} != {expected_checksum})"

        return True, "Checkpoint valid"

    def load_latest_valid_checkpoint(self, goal_id: str) -> Optional[CheckpointSnapshot]:
        """
        Loads the most recent verified checkpoint, rejecting any corrupted snapshots.
        """
        raw = runtime_state_store.load_latest_checkpoint(goal_id)
        if not raw:
            return self._latest_snapshots.get(goal_id)

        valid, _ = self.validate_checkpoint(raw)
        if not valid:
            return None

        return CheckpointSnapshot(
            checkpoint_id=raw["checkpoint_id"],
            goal_id=raw["goal_id"],
            version=raw["version"],
            created_at=raw.get("created_at", time.time()),
            task_data=raw["task_data"],
            plan_data=raw.get("plan_data", {}),
            checksum=raw["checksum"],
            metadata=raw.get("metadata", {}),
        )

    def clear_all(self) -> None:
        self._latest_snapshots.clear()


# Global singleton instance
checkpoint_manager = CheckpointManager()
