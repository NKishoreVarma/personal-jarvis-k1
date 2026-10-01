"""
Proactive Preparation Manager for MARK XLVIII / JARVIS.
Safely pre-calculates URLs, diagnostic queries, and skill lookups in the background.
Enforces strict boundaries:
PROACTIVE_PREPARATION != PROACTIVE_EXECUTION (Mutations and external side-effects are forbidden).
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from core.anticipation_engine import Prediction
from core.preparation_contract import PreparationContract


class ProactivePreparationManager:
    """
    Coordinates side-effect-free background pre-computations for anticipated tasks.
    """

    def __init__(self):
        self._active_preparations: Dict[str, Dict[str, Any]] = {}

    def prepare_anticipated_action(self, prediction: Prediction) -> Optional[Dict[str, Any]]:
        """
        Executes purely read-only, side-effect-free preparatory computation.
        """
        if not prediction.preparation_allowed or prediction.is_expired():
            return None

        prep_id = f"proprep_{uuid.uuid4().hex[:8]}"
        action = prediction.predicted_next_action

        result_payload: Dict[str, Any] = {
            "prep_id": prep_id,
            "prediction_id": prediction.prediction_id,
            "target_project": prediction.target_project,
            "action": action,
            "ready": True,
            "created_at": time.time(),
            "has_side_effects": False,
        }

        # 1. URL Precomputation
        if action == "open_browser":
            port = prediction.parameters.get("port", 3000)
            url = f"http://localhost:{port}"
            result_payload["url"] = url
            result_payload["prepared_data"] = {"precomputed_url": url, "port": port}

        # 2. Diagnostic Query Preparation
        elif action == "diagnose_and_repair":
            proj = prediction.target_project
            result_payload["prepared_data"] = {"diagnostic_target": proj, "expected_port": 3000}

        # 3. Startup Monitoring Preparation
        elif action == "monitor_startup":
            result_payload["prepared_data"] = {"monitor_interval_ms": 100}

        else:
            result_payload["prepared_data"] = {}

        self._active_preparations[prep_id] = result_payload
        return result_payload

    def get_prepared_data(self, action: str, project_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves prepared data if active."""
        for prep in self._active_preparations.values():
            if prep.get("action") == action and prep.get("target_project", "").lower() == project_name.lower():
                return prep
        return None

    def invalidate_project_preparations(self, project_name: str) -> None:
        to_del = [k for k, v in self._active_preparations.items() if v.get("target_project", "").lower() == project_name.lower()]
        for k in to_del:
            self._active_preparations.pop(k, None)

    def clear_all(self) -> None:
        self._active_preparations.clear()


# Global singleton instance
proactive_preparation_manager = ProactivePreparationManager()
