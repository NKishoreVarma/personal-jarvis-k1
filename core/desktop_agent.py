"""
Desktop Agent for MARK XLVIII / JARVIS.
Coordinates high-level desktop and project execution goals.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from actions.project_runner import run_project_async
from core.process_manager import process_manager
from core.project_discovery import project_discovery
from core.project_profiler import project_profiler
from core.task_registry import task_registry


class DesktopAgent:
    """
    Coordinates desktop and development project tasks for JARVIS.
    """

    def __init__(self):
        self.discovery = project_discovery
        self.profiler = project_profiler
        self.process_mgr = process_manager
        self.task_reg = task_registry

    async def execute_run_goal(
        self,
        project_name: str,
        location_hint: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs the complete project discovery and execution workflow."""
        return await run_project_async(project_name, location_hint=location_hint, task_id=task_id)

    def cancel_active_task(self) -> bool:
        """Cancels the active task and cleans up associated processes."""
        return self.task_reg.cancel_task()

    def get_status_summary(self) -> str:
        """Returns the natural language summary of active tasks."""
        return self.task_reg.get_active_task_summary()


# Global singleton
desktop_agent = DesktopAgent()
