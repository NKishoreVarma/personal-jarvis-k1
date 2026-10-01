"""
Zero-Wait Execution Handoff for MARK XLVIII / JARVIS.
Claims cached pre-execution context (project discovery, framework profiling, application metadata)
upon command finalization, eliminating redundant operations for instant execution start.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.intent_stability_manager import intent_stability_manager
from core.predictive_execution import predictive_manager
from core.streaming_intent_engine import StreamingIntent


class HandoffStatus(str, Enum):
    NO_PREPARATION = "NO_PREPARATION"
    PARTIAL_PREPARATION = "PARTIAL_PREPARATION"
    READY = "READY"
    CLAIMED = "CLAIMED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


@dataclass
class HandoffResult:
    status: HandoffStatus
    turn_id: str
    reused_components: List[str] = field(default_factory=list)
    execution_context: Optional[Dict[str, Any]] = None
    reason: str = ""


class ZeroWaitHandoff:
    """
    Seamlessly transfers predictive preparation results directly into the execution engine.
    """

    def claim(self, turn_id: str, final_command: str) -> HandoffResult:
        """
        Attempts to claim pre-computed context matching the finalized command.
        Safely falls back if predictive preparation is absent.
        """
        intent = intent_stability_manager.get_latest_intent(turn_id)
        if not intent:
            return HandoffResult(
                status=HandoffStatus.NO_PREPARATION,
                turn_id=turn_id,
                reused_components=[],
                execution_context=None,
                reason="No streaming intent recorded for this turn.",
            )

        # 1. Project Operation Handoff
        if intent.intent_type in ("RUN_PROJECT", "PROJECT_OPERATION"):
            proj_name = intent.entities.get("project", "")
            loc = intent.entities.get("location")
            args = {"project_name": proj_name}
            if loc:
                args["location_hint"] = loc

            prep_res = predictive_manager.get_prepared_result(
                operation="prefetch_project",
                turn_id=turn_id,
                arguments=args,
            )

            if prep_res and prep_res.get("found"):
                reused = ["project_discovery", "project_profiler"]
                context = {
                    "task_type": "RUN_PROJECT",
                    "project_name": prep_res.get("project_name", proj_name),
                    "path": prep_res.get("path"),
                    "framework": prep_res.get("framework"),
                    "command": prep_res.get("command"),
                    "port": prep_res.get("port"),
                }
                print(f"[ZERO_WAIT_HANDOFF] ⚡ Claimed prepared project context for '{proj_name}' -> path={context['path']}, framework={context['framework']}")
                return HandoffResult(
                    status=HandoffStatus.READY,
                    turn_id=turn_id,
                    reused_components=reused,
                    execution_context=context,
                    reason="Successfully claimed pre-discovered and profiled project context.",
                )

        # 2. Application Operation Handoff
        if intent.intent_type in ("OPEN_APP", "CLOSE_APP"):
            app_name = intent.entities.get("app_name", "")
            prep_res = predictive_manager.get_prepared_result(
                operation="prefetch_application",
                turn_id=turn_id,
                arguments={"app_name": app_name},
            )

            if prep_res:
                reused = ["application_lookup", "process_state_check"]
                context = {
                    "task_type": intent.intent_type,
                    "app_name": app_name,
                    "canonical_name": prep_res.get("application"),
                    "installed": prep_res.get("installed", True),
                    "running": prep_res.get("running", False),
                    "target": intent.entities.get("target"),
                }
                print(f"[ZERO_WAIT_HANDOFF] ⚡ Claimed prepared application context for '{app_name}' -> canonical={context['canonical_name']}")
                return HandoffResult(
                    status=HandoffStatus.READY,
                    turn_id=turn_id,
                    reused_components=reused,
                    execution_context=context,
                    reason="Successfully claimed pre-verified application context.",
                )

        # 3. UI Element Handoff
        if intent.intent_type == "UI_OPERATION":
            prep_res = predictive_manager.get_prepared_result(
                operation="prefetch_ui_element",
                turn_id=turn_id,
                arguments=intent.entities,
            )
            if prep_res:
                return HandoffResult(
                    status=HandoffStatus.READY,
                    turn_id=turn_id,
                    reused_components=["window_enumeration"],
                    execution_context=prep_res,
                    reason="Successfully claimed pre-enumerated UI window context.",
                )

        return HandoffResult(
            status=HandoffStatus.NO_PREPARATION,
            turn_id=turn_id,
            reused_components=[],
            execution_context=None,
            reason="No prepared context available, falling back to standard execution.",
        )


# Global singleton instance
zero_wait_handoff = ZeroWaitHandoff()
