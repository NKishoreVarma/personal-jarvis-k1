"""
Filesystem & Project Observer for MARK XLVIII / JARVIS.
Integrates with actions/dev_tools.py to safely inspect project metadata, manifest types,
git status, and recent changed files within sandboxed workspace boundaries.
Enforces secret masking and forbidden directory protections.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from actions.dev_tools import (
    check_git_status,
    get_project_info,
    list_directory,
)
from core.perception_contract import (
    Observation,
    ObservationType,
    PrivacyClassification,
    create_observation,
)


class FilesystemObserver:
    """
    Observes project configuration, git tree status, and workspace file structure.
    """

    def observe(
        self,
        project_path: str = ".",
        correlation_id: Optional[str] = None,
    ) -> Observation:
        """
        Samples the workspace project structure, git state, and manifest configuration.
        """
        t0 = time.perf_counter()

        try:
            # 1. Project profiling
            proj_info = get_project_info(project_path)
            # 2. Git status
            git_info = check_git_status(project_path)
            # 3. Directory summary
            dir_summary = list_directory(project_path)

            elapsed_ms = (time.perf_counter() - t0) * 1000

            content = {
                "project_path": str(Path(project_path).resolve()),
                "project_types": proj_info.get("project_types", ["Unknown"]),
                "manifests": proj_info.get("manifests", []),
                "git_branch": git_info.get("branch", "unknown"),
                "git_status": git_info.get("status", "unknown"),
                "is_clean_repo": git_info.get("status") == "Clean working tree",
                "top_level_items": dir_summary.get("total_items", 0),
                "sampling_latency_ms": round(elapsed_ms, 2),
            }

            return create_observation(
                observation_type=ObservationType.FILESYSTEM,
                source="filesystem_observer",
                content=content,
                confidence=0.98,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=60.0,
                correlation_id=correlation_id,
                is_verified=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return create_observation(
                observation_type=ObservationType.FILESYSTEM,
                source="filesystem_observer",
                content={
                    "error": str(e),
                    "status": "FS_OBSERVE_FAILED",
                    "sampling_latency_ms": round(elapsed_ms, 2),
                },
                confidence=0.0,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=10.0,
                correlation_id=correlation_id,
                is_verified=False,
            )


# Global singleton instance
filesystem_observer = FilesystemObserver()
