"""
Observation Engine for MARK XLVIII / JARVIS.
Gathers fresh, verified environmental evidence across projects, ports, processes, and logs
before generating hypotheses or planning actions.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.process_manager import process_manager
from core.project_discovery import project_discovery
from core.project_profiler import project_profiler


class ObservationCategory(str, Enum):
    PROJECT_STATE = "PROJECT_STATE"
    PROCESS_STATE = "PROCESS_STATE"
    PORT_STATE = "PORT_STATE"
    LOG_STATE = "LOG_STATE"
    TEST_STATE = "TEST_STATE"
    FILE_STATE = "FILE_STATE"
    APPLICATION_STATE = "APPLICATION_STATE"
    SYSTEM_STATE = "SYSTEM_STATE"


@dataclass
class Observation:
    observation_id: str
    category: ObservationCategory
    source: str
    data: Dict[str, Any]
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.monotonic)

    def is_fresh(self, max_age_sec: float = 15.0) -> bool:
        return (time.monotonic() - self.timestamp) <= max_age_sec


class ObservationEngine:
    """
    Collects fresh, verified environmental evidence.
    """

    def observe_project(self, project_name: str, location_hint: Optional[str] = None) -> Observation:
        """Inspects project existence, directory structure, and framework."""
        disc = project_discovery.find_project(project_name, location_hint=location_hint)
        found = disc.get("found", False)
        path = disc.get("path", "")

        profiling_data = {}
        if found and path:
            profiling_data = project_profiler.profile_project(path)

        return Observation(
            observation_id=f"obs_{uuid.uuid4().hex[:8]}",
            category=ObservationCategory.PROJECT_STATE,
            source="project_discovery",
            data={
                "project_name": project_name,
                "found": found,
                "path": path,
                "profile": profiling_data,
            },
        )

    def observe_port(self, port: int) -> Observation:
        """Inspects port responsiveness and socket state."""
        is_responsive = process_manager.verify_http(port, path="/", timeout=0.5)
        return Observation(
            observation_id=f"obs_{uuid.uuid4().hex[:8]}",
            category=ObservationCategory.PORT_STATE,
            source="process_manager",
            data={
                "port": port,
                "is_responsive": is_responsive,
            },
        )

    def observe_process(self, process_id: str) -> Observation:
        """Inspects process status, pid, exit code, and log output."""
        status = process_manager.get_process_status(process_id)
        return Observation(
            observation_id=f"obs_{uuid.uuid4().hex[:8]}",
            category=ObservationCategory.PROCESS_STATE,
            source="process_manager",
            data=status or {"status": "NOT_FOUND"},
        )

    def gather_diagnostic_evidence(self, project_name: str, target_port: int = 3000) -> Dict[str, Any]:
        """Collects holistic multi-category evidence for a target project."""
        proj_obs = self.observe_project(project_name)
        port_obs = self.observe_port(target_port)

        # Check if any active process matches project name
        running_procs = [p for p in process_manager.list_processes() if p.get("project_name", "").lower() == project_name.lower()]

        return {
            "project_state": proj_obs.data,
            "port_state": port_obs.data,
            "active_processes": running_procs,
            "timestamp": time.monotonic(),
        }


# Global singleton instance
observation_engine = ObservationEngine()
