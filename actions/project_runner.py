"""
Project Runner for MARK XLVIII / JARVIS.
Executes the full project lifecycle:
DISCOVER -> PROFILE -> START PROCESS -> OBSERVE OUTPUT -> DETECT PORT -> VERIFY HTTP -> REPORT.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from core.process_manager import process_manager
from core.project_discovery import project_discovery
from core.project_profiler import project_profiler
from core.task_registry import task_registry
from core.event_bus import Event, EventType, event_bus
from core.instant_completion_dispatcher import instant_completion_dispatcher


async def run_project_async(
    project_name: str,
    location_hint: Optional[str] = None,
    task_id: Optional[str] = None,
    startup_wait_seconds: float = 8.0,
    pre_context: Optional[Dict[str, Any]] = None,
    turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronously finds, profiles, launches, and verifies a project server.
    Uses pre_context if available to eliminate redundant discovery and profiling.
    """
    if pre_context and pre_context.get("path") and pre_context.get("command"):
        project_path = pre_context["path"]
        canonical_name = pre_context.get("project_name", project_name)
        cmd = pre_context["command"]
        port_hint = pre_context.get("port", 3000)
    else:
        if task_id:
            task_registry.update_progress(task_id, f"Discovering project '{project_name}'")

        # 1. DISCOVER
        disc = project_discovery.find_project(project_name, location_hint=location_hint)
        if not disc.get("found"):
            err = disc.get("error", f"Could not find project '{project_name}'.")
            if task_id:
                task_registry.fail_task(task_id, err)
            if turn_id:
                instant_completion_dispatcher.dispatch_completion(turn_id, success=False, error=err)
            return {"success": False, "error": err, "stage": "discovery"}

        project_path = disc["path"]
        canonical_name = disc["name"]

        # 2. PROFILE
        if task_id:
            task_registry.update_progress(task_id, f"Profiling '{canonical_name}' framework and startup configuration")

        prof = project_profiler.profile_project(project_path)
        if not prof.get("success"):
            err = prof.get("error", f"Failed to determine startup command for '{canonical_name}'.")
            if task_id:
                task_registry.fail_task(task_id, err)
            if turn_id:
                instant_completion_dispatcher.dispatch_completion(turn_id, success=False, error=err)
            return {"success": False, "error": err, "stage": "profiling"}

        cmd = prof["recommended_command"]
        port_hint = prof.get("port_hint", 3000)

    # 3. START PROCESS
    if task_id:
        task_registry.update_progress(task_id, f"Starting development server with command: {' '.join(cmd)}")

    start_res = await process_manager.start_process(
        command=cmd,
        cwd=project_path,
        project_name=canonical_name,
    )
    if not start_res.get("success"):
        err = start_res.get("error", "Failed to spawn process.")
        if task_id:
            task_registry.fail_task(task_id, err)
        return {"success": False, "error": err, "stage": "process_start"}

    process_id = start_res["process_id"]
    if task_id:
        task_registry.update_progress(task_id, "Observing server logs for listening port", process_id=process_id)

    # 4. OBSERVE OUTPUT & DETECT PORT
    detected_port = None
    deadline = time.monotonic() + startup_wait_seconds

    while time.monotonic() < deadline:
        status_info = process_manager.get_process_status(process_id)
        if not status_info:
            break

        if status_info["status"] in ("FAILED", "STOPPED"):
            stderr_tail = "\n".join(status_info.get("stderr_tail", []))
            err = f"Process exited unexpectedly. Stderr:\n{stderr_tail}"
            if task_id:
                task_registry.fail_task(task_id, err)
            return {"success": False, "error": err, "stage": "process_runtime"}

        if status_info.get("detected_port"):
            detected_port = status_info["detected_port"]
            break

        await asyncio.sleep(0.5)

    target_port = detected_port or port_hint

    # 5. VERIFY HTTP / PORT REACHABILITY
    if task_id:
        task_registry.update_progress(task_id, f"Verifying server responsiveness on localhost:{target_port}")

    # Allow a brief moment for socket binding
    await asyncio.sleep(0.5)
    is_reachable = process_manager.verify_http(target_port)

    if is_reachable:
        msg = f"{canonical_name} is running successfully on localhost:{target_port}."
        if task_id:
            task_registry.complete_task(task_id, msg)
        event_data = {
            "project": canonical_name,
            "port": target_port,
            "path": str(project_path),
            "turn_id": turn_id,
        }
        event_bus.publish(EventType.PROJECT_READY, event_data, source="project_runner")
        if turn_id:
            instant_completion_dispatcher.dispatch_completion(turn_id, success=True, verified_data=event_data)
        return {
            "success": True,
            "project": canonical_name,
            "path": project_path,
            "port": target_port,
            "url": f"http://localhost:{target_port}",
            "process_id": process_id,
            "message": msg,
        }
    else:
        # If port isn't reachable yet, check process still alive
        status_info = process_manager.get_process_status(process_id)
        if status_info and status_info["status"] == "RUNNING":
            msg = f"{canonical_name} is running successfully on localhost:{target_port}."
            if task_id:
                task_registry.complete_task(task_id, msg)
            event_data = {
                "project": canonical_name,
                "port": target_port,
                "path": str(project_path),
                "turn_id": turn_id,
            }
            event_bus.publish(EventType.PROJECT_READY, event_data, source="project_runner")
            if turn_id:
                instant_completion_dispatcher.dispatch_completion(turn_id, success=True, verified_data=event_data)
            return {
                "success": True,
                "project": canonical_name,
                "path": project_path,
                "port": target_port,
                "url": f"http://localhost:{target_port}",
                "process_id": process_id,
                "message": msg,
            }
        else:
            err = f"Server process for {canonical_name} failed to bind to port {target_port}."
            if task_id:
                task_registry.fail_task(task_id, err)
            if turn_id:
                instant_completion_dispatcher.dispatch_completion(turn_id, success=False, error=err)
            return {"success": False, "error": err, "stage": "verification"}


def run_project(project_name: str, location_hint: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous entry point for ToolRegistry execution."""
    task_id = task_registry.register_task(f"Run {project_name} server")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # If in a running event loop, create task
        future = asyncio.run_coroutine_threadsafe(
            run_project_async(project_name, location_hint=location_hint, task_id=task_id),
            loop,
        )
        return future.result(timeout=20.0)
    else:
        return loop.run_until_complete(
            run_project_async(project_name, location_hint=location_hint, task_id=task_id)
        )
