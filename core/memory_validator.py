"""
Memory Validator for MARK XLVIII / JARVIS.
Enforces the inviolable principle: CURRENT OBSERVATION > MEMORY.
Validates stored memories against fresh real-time evidence and marks stale or contradicted records.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from core.event_bus import EventType, event_bus
from core.memory_contract import MemoryContract, VerificationState
from core.memory_service import memory_service


class MemoryValidator:
    """
    Validates retrieved memories against fresh real-time environmental observations.
    """

    def validate_memory(
        self,
        memory: MemoryContract,
        observation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compares memory contents with current observation data.
        Returns validation result: 'CONFIRMED', 'CONTRADICTED', 'STALE', or 'INCONCLUSIVE'.
        """
        # Port check
        proj_state = observation.get("project_state", {})
        port_state = observation.get("port_state", {})
        current_port = port_state.get("port")

        content_lower = memory.content.lower()

        # Check for port contradiction
        port_match = re.search(r"port\s*(?:is|:|\s+equals)?\s*(\d{2,5})", content_lower)
        if port_match and current_port:
            remembered_port = int(port_match.group(1))
            if remembered_port != current_port and port_state.get("is_responsive"):
                # Real observation proves project is on a different port!
                memory_service.mark_contradicted(
                    memory.memory_id,
                    reason=f"Current observation shows active port is {current_port}, not {remembered_port}.",
                )
                event_bus.publish(EventType.TASK_PROGRESS, {
                    "event": "MEMORY_CONTRADICTED",
                    "memory_id": memory.memory_id,
                    "reason": f"Port changed from {remembered_port} to {current_port}",
                })
                print(f"[MEMORY_VALIDATOR] ⚠️ Memory contradicted: Port is {current_port} (was {remembered_port}).")
                return {
                    "status": "CONTRADICTED",
                    "current_value": current_port,
                    "remembered_value": remembered_port,
                }

        # Check for framework confirmation or contradiction
        profile = proj_state.get("profile", {})
        current_framework = profile.get("framework")
        if current_framework and current_framework.lower() in content_lower:
            memory_service.mark_verified(memory.memory_id)
            return {"status": "CONFIRMED", "field": "framework", "value": current_framework}

        return {"status": "INCONCLUSIVE"}


# Global singleton instance
memory_validator = MemoryValidator()
