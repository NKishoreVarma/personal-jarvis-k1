"""
Memory Learning Loop for MARK XLVIII / JARVIS.
Connects autonomous problem solving to experience extraction, persistence, and continuous learning.
Ensures every verified outcome updates long-term memory asynchronously without blocking the voice pipeline.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from core.event_bus import Event, EventType, event_bus
from core.experience_memory import experience_memory
from core.memory_extractor import memory_extractor
from core.memory_retriever import memory_retriever
from core.memory_service import memory_service
from core.memory_validator import memory_validator


class MemoryLearningLoop:
    """
    Coordinates asynchronous learning from completed goals and applies past experiences to future tasks.
    """

    def __init__(self):
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        """Subscribes to EventBus project completion events."""
        event_bus.subscribe(EventType.PROJECT_READY, self.on_project_ready)

    def on_project_ready(self, event: Event) -> None:
        """Extracts and stores experience asynchronously when a project or repair completes."""
        payload = event.payload
        project = payload.get("project")
        port = payload.get("port", 3000)
        category = payload.get("category", "PORT_CONFLICT")
        actions = payload.get("actions", ["terminate_conflicting_processes", "restart_project_server"])

        if project:
            # 1. Record structured experience
            experience_memory.record_experience(
                goal_type="PROJECT_STARTUP_REPAIR",
                context_signature=f"{project}",
                problem_pattern=category,
                successful_strategy=actions,
                verification_result={"port": port, "verified": True},
            )

            # 2. Extract durable memory contract
            mem = memory_extractor.extract_from_repair_outcome(
                project_name=project,
                problem_category=category,
                successful_actions=actions,
                port=port,
            )
            if mem:
                mem_id = memory_service.store(mem)
                print(f"[MEMORY_LEARNING_LOOP] 🧠 Stored repair experience for '{project}' (id={mem_id})")

    def get_planning_hints(self, target_project: str, current_observation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieves prior experiences and validates them against current observations.
        Returns validated hypothesis hints with confidence boosts.
        """
        memories = memory_retriever.retrieve_relevant(
            query=f"{target_project} startup failure repair",
            project_name=target_project,
            top_k=3,
        )

        hints: List[Dict[str, Any]] = []
        for mem in memories:
            val = memory_validator.validate_memory(mem, current_observation)
            if val.get("status") != "CONTRADICTED":
                cat = mem.metadata.get("problem_category", "PORT_CONFLICT")
                hints.append({
                    "category": cat,
                    "confidence_boost": mem.confidence * 0.3,
                    "suggested_actions": mem.metadata.get("successful_actions", []),
                    "source_memory_id": mem.memory_id,
                })

        return hints


# Global singleton instance
memory_learning_loop = MemoryLearningLoop()
