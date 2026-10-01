"""
Predictive Execution & Safe Parallel Agent Preparation for MARK XLVIII / JARVIS.
Predicts probable user intents from streaming partial transcripts and executes
side-effect-free prefetching tasks (project discovery, framework profiling, app verification)
in the background to eliminate startup latency upon command finalization.
"""

from __future__ import annotations

import asyncio
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from core.application_controller import app_controller
from core.preparation_contract import (
    PreparationContract,
    PreparationRisk,
    create_preparation_contract,
)
from core.project_discovery import project_discovery
from core.project_profiler import project_profiler
from core.window_manager import window_manager


class PredictiveState(str, Enum):
    IDLE = "IDLE"
    PREDICTING = "PREDICTING"
    PREPARING = "PREPARING"
    READY = "READY"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    CANCELLED = "CANCELLED"


class PredictiveExecutionManager:
    """
    Coordinates safe, turn-bound, parallel preparation tasks during active speech streaming.
    """

    CONFIDENCE_THRESHOLD_LIGHT = 0.60
    CONFIDENCE_THRESHOLD_FULL = 0.80

    def __init__(self):
        self.state = PredictiveState.IDLE
        self._contracts: Dict[str, PreparationContract] = {}  # prep_id -> contract
        self._turn_contracts: Dict[str, List[str]] = {}       # turn_id -> list of prep_ids
        self._async_tasks: Dict[str, asyncio.Task] = {}       # prep_id -> asyncio.Task
        self._active_predictions: Dict[str, Dict[str, Any]] = {}  # turn_id -> prediction info

    def on_partial_transcript(self, partial_text: str, turn_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyzes incoming partial transcript and triggers safe background preparation if confidence permits.
        """
        clean = partial_text.strip().lower()
        if not clean:
            return None

        prediction = self._classify_partial_intent(clean)
        if not prediction or prediction["confidence"] < self.CONFIDENCE_THRESHOLD_LIGHT:
            return None

        # Invalidate prior incompatible predictions for this turn
        self._reconcile_prediction_compatibility(prediction, turn_id)

        # Trigger safe background preparation if not already prepared
        self._trigger_safe_preparation(prediction, turn_id)
        return prediction

    def _classify_partial_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Linguistic classifier for streaming partial phrases."""
        # 1. Project Operation: "open flow", "run flow from desktop", "open mark xlviii"
        m_proj = re.search(
            r"(?:open\s+([a-zA-Z0-9\._-]+)(?:\s+from\s+(?:my\s+)?([a-zA-Z0-9\._-]+))?|"
            r"(?:run|start)\s+(?:the\s+)?(?:project\s+)?([a-zA-Z0-9\._-]+))",
            text,
        )
        if m_proj:
            p_name = m_proj.group(1) or m_proj.group(3)
            loc = m_proj.group(2)
            if p_name and p_name.lower() not in ("chrome", "safari", "whatsapp", "slack", "spotify", "vscode", "visual studio code"):
                conf = 0.88 if loc else 0.78
                return {
                    "task_type": "PROJECT_OPERATION",
                    "operation": "prefetch_project",
                    "project_name": p_name,
                    "location_hint": loc,
                    "confidence": conf,
                }

        # 2. Application Operation: "open whatsapp", "open chrome", "switch to spotify"
        m_app = re.search(r"(?:open|launch|switch\s+to|start)\s+([a-zA-Z0-9\._-]+)", text)
        if m_app:
            app_name = m_app.group(1)
            if app_name.lower() in ("chrome", "safari", "whatsapp", "slack", "spotify", "vscode", "finder", "notes"):
                return {
                    "task_type": "APPLICATION_OPERATION",
                    "operation": "prefetch_application",
                    "app_name": app_name,
                    "confidence": 0.92,
                }

        # 3. UI / Window Operation: "switch to flow in vs code", "find john in whatsapp"
        m_ui = re.search(r"(?:switch\s+to|find)\s+([a-zA-Z0-9\._-]+)\s+in\s+([a-zA-Z0-9\._-]+)", text)
        if m_ui:
            target = m_ui.group(1)
            container = m_ui.group(2)
            return {
                "task_type": "UI_OPERATION",
                "operation": "prefetch_ui_element",
                "target": target,
                "container_app": container,
                "confidence": 0.85,
            }

        return None

    def _trigger_safe_preparation(self, prediction: Dict[str, Any], turn_id: str) -> None:
        """Launches side-effect-free prefetching tasks asynchronously."""
        op = prediction["operation"]
        args = {k: v for k, v in prediction.items() if k not in ("task_type", "operation", "confidence")}

        # Check if already preparing or prepared
        existing_prep = self.get_prepared_contract(op, turn_id, args)
        if existing_prep:
            return

        contract = create_preparation_contract(
            turn_id=turn_id,
            operation=op,
            arguments=args,
            confidence=prediction["confidence"],
            side_effect_free=True,
        )

        if not contract.can_execute_predictively():
            print(f"[PREDICTIVE] ⚠️ Prohibited mutating operation for predictive execution: {op}")
            return

        self._contracts[contract.preparation_id] = contract
        if turn_id not in self._turn_contracts:
            self._turn_contracts[turn_id] = []
        self._turn_contracts[turn_id].append(contract.preparation_id)
        self.state = PredictiveState.PREPARING

        # Launch async prefetch task
        async def _worker():
            try:
                if op == "prefetch_project":
                    res = await self._async_prepare_project(contract.arguments)
                elif op == "prefetch_application":
                    res = await self._async_prepare_application(contract.arguments)
                elif op == "prefetch_ui_element":
                    res = await self._async_prepare_ui(contract.arguments)
                else:
                    res = None

                contract.result = res
                self.state = PredictiveState.READY
                print(f"[PREDICTIVE] ✅ Ready: {op} (prep_id={contract.preparation_id}) -> {res}")
            except Exception as e:
                print(f"[PREDICTIVE] Error preparing {op}: {e}")
                contract.is_valid = False

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(_worker())
            self._async_tasks[contract.preparation_id] = task
        except RuntimeError:
            pass

    async def _async_prepare_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Discovers project path and framework profile non-blockingly."""
        p_name = args.get("project_name", "")
        loc = args.get("location_hint")
        find_res = await asyncio.to_thread(project_discovery.find_project, p_name, location_hint=loc)
        if not find_res.get("found") or not find_res.get("path"):
            return {"found": False, "project_name": p_name}

        path = find_res["path"]
        profile = await asyncio.to_thread(project_profiler.profile_project, str(path))
        if isinstance(profile, dict):
            return {
                "found": True,
                "project_name": p_name,
                "path": str(path),
                "framework": profile.get("framework", "unknown"),
                "command": profile.get("startup_command", []),
                "port": profile.get("port"),
            }
        return {
            "found": True,
            "project_name": p_name,
            "path": str(path),
            "framework": getattr(profile, "framework", "unknown"),
            "command": getattr(profile, "startup_command", []),
            "port": getattr(profile, "port", None),
        }

    async def _async_prepare_application(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validates canonical application bundle and process state."""
        app_name = args.get("app_name", "")
        canonical = app_controller.get_canonical_name(app_name)
        is_running = app_controller.is_running(canonical)
        return {
            "application": canonical,
            "installed": True,
            "running": is_running,
        }

    async def _async_prepare_ui(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Inspects visible windows without focusing."""
        target = args.get("target", "")
        container = args.get("container_app", "")
        windows = await asyncio.to_thread(window_manager.list_windows)
        matching = [w for w in windows if container.lower() in w.get("app", "").lower()]
        return {
            "container": container,
            "target": target,
            "windows_count": len(matching),
            "matching_windows": matching,
        }

    def get_prepared_result(self, operation: str, turn_id: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieves prepared result if contract is valid, unexpired, and argument-compatible.
        """
        contract = self.get_prepared_contract(operation, turn_id, arguments)
        if contract and contract.is_valid and not contract.is_expired():
            self.state = PredictiveState.CONFIRMED
            return contract.result
        return None

    def get_prepared_contract(self, operation: str, turn_id: str, arguments: Dict[str, Any]) -> Optional[PreparationContract]:
        prep_ids = self._turn_contracts.get(turn_id, [])
        for pid in prep_ids:
            c = self._contracts.get(pid)
            if c and c.operation == operation and c.is_valid and not c.is_expired():
                # Verify core argument compatibility (case-insensitive for string tokens)
                compat = True
                for k, v in arguments.items():
                    if k in c.arguments:
                        c_val = c.arguments[k]
                        if isinstance(v, str) and isinstance(c_val, str):
                            if v.strip().lower() != c_val.strip().lower():
                                compat = False
                                break
                        elif c_val != v:
                            compat = False
                            break
                if compat:
                    return c
        return None

    def _reconcile_prediction_compatibility(self, new_prediction: Dict[str, Any], turn_id: str) -> None:
        """Cancels conflicting past preparation tasks for this turn if meaning shifted."""
        prep_ids = self._turn_contracts.get(turn_id, [])
        for pid in prep_ids:
            c = self._contracts.get(pid)
            if c and c.operation != new_prediction["operation"]:
                print(f"[PREDICTIVE] 🔄 Meaning shifted: Invalidating {c.operation} for {new_prediction['operation']}")
                c.is_valid = False
                task = self._async_tasks.get(pid)
                if task and not task.done():
                    task.cancel()

    def invalidate_turn(self, turn_id: str) -> None:
        """Discards all prepared contracts and cancels running tasks for a turn."""
        prep_ids = self._turn_contracts.pop(turn_id, [])
        for pid in prep_ids:
            c = self._contracts.pop(pid, None)
            if c:
                c.is_valid = False
            task = self._async_tasks.pop(pid, None)
            if task and not task.done():
                task.cancel()
        self.state = PredictiveState.IDLE

    def cleanup_expired(self) -> None:
        """Maintains bounded cache size."""
        now = time.monotonic()
        for pid, c in list(self._contracts.items()):
            if c.is_expired() or not c.is_valid:
                self._contracts.pop(pid, None)
                self._async_tasks.pop(pid, None)


# Global singleton instance
predictive_manager = PredictiveExecutionManager()
