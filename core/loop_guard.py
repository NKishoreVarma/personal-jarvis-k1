"""
LoopGuard — Agent Safety, Repeat Detection, and Loop Prevention for MARK XLVIII.
Tracks action fingerprints, detects identical repeats, ping-pong cycles, and failure loops.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LoopDecision:
    """Decision returned by LoopGuard before executing an action."""
    allowed: bool
    reason: Optional[str] = None
    action_count: int = 0
    consecutive_failures: int = 0
    loop_type: Optional[str] = None  # 'identical_action', 'ping_pong', 'max_failures', 'destructive_retry'


@dataclass
class LoopGuardConfig:
    """Configuration for LoopGuard thresholds."""
    max_identical_actions: int = 3
    ping_pong_window: int = 6
    max_consecutive_failures: int = 3
    max_global_consecutive_failures: int = 5


def _canonicalize_value(val: Any) -> Any:
    """Normalize values recursively for deterministic hashing."""
    if isinstance(val, dict):
        return {str(k).strip().lower(): _canonicalize_value(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [_canonicalize_value(item) for item in val]
    elif isinstance(val, str):
        return val.strip()
    return val


def compute_fingerprint(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a deterministic SHA-256 fingerprint for a tool call.
    Dictionary keys are sorted and canonicalized so argument order does not affect the hash.
    """
    normalized_tool = tool_name.strip().lower()
    normalized_args = _canonicalize_value(arguments or {})
    
    payload = {
        "tool": normalized_tool,
        "arguments": normalized_args,
    }
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]


class LoopGuard:
    """
    Guards the agent from running into infinite loops, repeating identical failing actions,
    or cycling between ping-pong states.
    """

    def __init__(self, config: Optional[LoopGuardConfig] = None):
        self.config = config or LoopGuardConfig()
        self._action_counts: Dict[str, int] = {}
        self._action_history: deque[str] = deque(maxlen=self.config.ping_pong_window * 2)
        self._failure_counts: Dict[str, int] = {}
        self._global_consecutive_failures: int = 0
        self._last_fingerprint: Optional[str] = None

    def register_action(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        permission_level: str = "low_risk",
    ) -> LoopDecision:
        """
        Check and register an action before execution.
        Returns a LoopDecision indicating whether the action is permitted.
        """
        fp = compute_fingerprint(tool_name, arguments)
        self._last_fingerprint = fp

        # 1. Guard destructive actions from automatic retries after failure
        if permission_level == "destructive" and self._failure_counts.get(fp, 0) > 0:
            print(f"[LOOPGUARD] Action '{tool_name}' blocked: Destructive action failed previously.")
            return LoopDecision(
                allowed=False,
                reason="Destructive action failed previously; automatic repeat is blocked for safety.",
                loop_type="destructive_retry",
                consecutive_failures=self._failure_counts.get(fp, 0),
            )

        # 2. Check consecutive failure threshold for this specific action
        if self._failure_counts.get(fp, 0) >= self.config.max_consecutive_failures:
            print(f"[LOOPGUARD] Action '{tool_name}' blocked: Reached max consecutive failures ({self.config.max_consecutive_failures}).")
            return LoopDecision(
                allowed=False,
                reason=f"Action '{tool_name}' exceeded maximum consecutive failure limit ({self.config.max_consecutive_failures}).",
                loop_type="max_failures",
                consecutive_failures=self._failure_counts.get(fp, 0),
            )

        # 3. Check identical action repeat count
        current_count = self._action_counts.get(fp, 0) + 1
        if current_count > self.config.max_identical_actions:
            print(f"[LOOPGUARD] Action '{tool_name}' blocked: Exceeded identical limit ({self.config.max_identical_actions}).")
            return LoopDecision(
                allowed=False,
                reason=f"Action '{tool_name}' exceeded maximum identical execution threshold ({self.config.max_identical_actions}).",
                loop_type="identical_action",
                action_count=current_count,
            )

        # 4. Check global consecutive failures
        if self._global_consecutive_failures >= self.config.max_global_consecutive_failures:
            print(f"[LOOPGUARD] Global failure threshold ({self.config.max_global_consecutive_failures}) reached.")
            return LoopDecision(
                allowed=False,
                reason=f"Agent reached global consecutive failure limit ({self.config.max_global_consecutive_failures}).",
                loop_type="max_failures",
                consecutive_failures=self._global_consecutive_failures,
            )

        # 5. Check Ping-Pong loops in sliding window
        projected_history = list(self._action_history) + [fp]
        if self._detect_ping_pong(projected_history):
            print(f"[LOOPGUARD] Ping-pong cycle detected across recent actions.")
            return LoopDecision(
                allowed=False,
                reason="Ping-pong cycling pattern detected across recent actions.",
                loop_type="ping_pong",
                action_count=current_count,
            )

        # Action is allowed: update tracking state
        self._action_counts[fp] = current_count
        self._action_history.append(fp)
        print(f"[LOOPGUARD] Action '{tool_name}' registered (count {current_count}/{self.config.max_identical_actions}, fp={fp})")
        return LoopDecision(
            allowed=True,
            action_count=current_count,
            consecutive_failures=self._failure_counts.get(fp, 0),
        )

    def register_result(
        self,
        fingerprint: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record the outcome of a tool execution."""
        fp = fingerprint or self._last_fingerprint
        if not fp:
            return

        if success:
            self._failure_counts[fp] = 0
            self._global_consecutive_failures = 0
        else:
            self._failure_counts[fp] = self._failure_counts.get(fp, 0) + 1
            self._global_consecutive_failures += 1
            print(f"[LOOPGUARD] Failure recorded for fp={fp} (consecutive failures: {self._failure_counts[fp]})")

    def _detect_ping_pong(self, history: List[str]) -> bool:
        """
        Detect repeating cycles in the history.
        Detects A-B-A-B (period 2) and A-B-C-A-B-C (period 3).
        """
        n = len(history)
        # Period 2: A-B-A-B (requires at least 4 items)
        if n >= 4:
            if history[-1] == history[-3] and history[-2] == history[-4] and history[-1] != history[-2]:
                return True

        # Period 3: A-B-C-A-B-C (requires at least 6 items)
        if n >= 6:
            if history[-6:-3] == history[-3:] and len(set(history[-3:])) >= 2:
                return True

        return False

    def reset(self) -> None:
        """Reset all tracking counters and history for a new agent run."""
        self._action_counts.clear()
        self._action_history.clear()
        self._failure_counts.clear()
        self._global_consecutive_failures = 0
        self._last_fingerprint = None


# Global singleton instance for easy import
loop_guard = LoopGuard()
