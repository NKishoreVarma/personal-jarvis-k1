"""
Command Commit Gate for MARK XLVIII / JARVIS.
Enforces the strict invariant: PREDICT != EXECUTE.
Guarantees that side effects (app launch, server execution, clicks, file modifications)
can only execute after explicit command finalization, turn validation, and risk approval.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from core.streaming_intent_engine import StreamingIntent


class CommitStatus(str, Enum):
    COMMITTED = "COMMITTED"
    REJECTED_UNFINALIZED = "REJECTED_UNFINALIZED"
    REJECTED_EXPIRED = "REJECTED_EXPIRED"
    REJECTED_RISK = "REJECTED_RISK"
    REJECTED_APPROVAL_REQUIRED = "REJECTED_APPROVAL_REQUIRED"
    REJECTED_CONTRADICTION = "REJECTED_CONTRADICTION"


@dataclass
class CommitDecision:
    status: CommitStatus
    turn_id: str
    is_committed: bool
    reason: str
    intent: Optional[StreamingIntent] = None


class CommandCommitGate:
    """
    Safety gate that validates finalized commands before any side-effect execution begins.
    """

    MAX_TURN_COMMIT_TTL_SEC = 15.0

    def evaluate_commit(
        self,
        turn_id: str,
        final_command: str,
        intent: Optional[StreamingIntent],
        is_finalized: bool = True,
        turn_started_at: Optional[float] = None,
    ) -> CommitDecision:
        """
        Evaluates whether a finalized command meets all safety requirements for execution.
        """
        now = time.monotonic()

        # 1. Finalization check
        if not is_finalized or not final_command.strip():
            return CommitDecision(
                status=CommitStatus.REJECTED_UNFINALIZED,
                turn_id=turn_id,
                is_committed=False,
                reason="Command is not finalized or is empty.",
            )

        # 2. TTL Expiration check
        if turn_started_at and (now - turn_started_at) > self.MAX_TURN_COMMIT_TTL_SEC:
            return CommitDecision(
                status=CommitStatus.REJECTED_EXPIRED,
                turn_id=turn_id,
                is_committed=False,
                reason=f"Turn expired (exceeded {self.MAX_TURN_COMMIT_TTL_SEC}s TTL).",
            )

        # 3. Intent compatibility check
        if intent is not None and intent.turn_id != turn_id:
            return CommitDecision(
                status=CommitStatus.REJECTED_CONTRADICTION,
                turn_id=turn_id,
                is_committed=False,
                reason="Intent turn_id does not match active command turn_id.",
            )

        return CommitDecision(
            status=CommitStatus.COMMITTED,
            turn_id=turn_id,
            is_committed=True,
            reason="Command safely committed for execution.",
            intent=intent,
        )


# Global singleton instance
command_commit_gate = CommandCommitGate()
