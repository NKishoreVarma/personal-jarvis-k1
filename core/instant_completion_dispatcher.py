"""
Instant Completion Dispatcher for MARK XLVIII / JARVIS.
Listens to verified events and instantly emits prepared completion responses
to the UI and TTS without cloud roundtrips or post-execution thinking delay.
Guards against duplicate announcements and checks silence and timing policies.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.completion_response_cache import completion_response_cache
from core.conversation_timing_controller import (
    ResponsePriority,
    conversation_timing_controller,
)
from core.duplicate_response_guard import duplicate_response_guard
from core.event_bus import Event, EventType, event_bus
from core.execution_response_binder import (
    BoundResponse,
    execution_response_binder,
)
from core.response_contract import ResponseContract, ResponseStage


class InstantCompletionDispatcher:
    """
    Emits instant verbal and visual feedback upon verified task completion events.
    """

    def __init__(self):
        self._registered = False

    def register_event_listeners(self) -> None:
        """Subscribes to verified lifecycle events on the EventBus."""
        if self._registered:
            return
        event_bus.subscribe(EventType.PROJECT_READY, self._on_project_ready)
        event_bus.subscribe(EventType.TASK_COMPLETED, self._on_task_completed)
        event_bus.subscribe(EventType.TASK_FAILED, self._on_task_failed)
        self._registered = True

    async def _on_project_ready(self, event: Event) -> None:
        turn_id = event.payload.get("turn_id")
        contract = completion_response_cache.get_contract(turn_id) if turn_id else None
        if contract:
            self.dispatch_completion(
                turn_id=contract.turn_id,
                success=True,
                verified_data=event.payload,
            )

    async def _on_task_completed(self, event: Event) -> None:
        turn_id = event.payload.get("turn_id")
        contract = completion_response_cache.get_contract(turn_id) if turn_id else None
        if contract:
            self.dispatch_completion(
                turn_id=contract.turn_id,
                success=True,
                verified_data=event.payload,
            )

    async def _on_task_failed(self, event: Event) -> None:
        turn_id = event.payload.get("turn_id")
        contract = completion_response_cache.get_contract(turn_id) if turn_id else None
        if contract:
            self.dispatch_completion(
                turn_id=contract.turn_id,
                success=False,
                error=event.payload.get("error", "Task execution failed"),
                verified_data=event.payload,
            )

    def dispatch_completion(
        self,
        turn_id: str,
        success: bool = True,
        error: str = "Execution failed",
        verified_data: Optional[Dict[str, Any]] = None,
        ui_callback=None,
    ) -> Optional[BoundResponse]:
        """
        Formats and releases the completion response for a given turn.
        Enforces duplicate suppression and conversation timing rules.
        """
        contract = completion_response_cache.get_contract(turn_id)
        if not contract:
            return None

        # Check if already released
        if contract.stage in (ResponseStage.SUCCESS_RELEASED, ResponseStage.FAILURE_RELEASED):
            return None

        # Check timing controller permission
        priority = ResponsePriority.VERIFIED_COMPLETION if success else ResponsePriority.FAILURE
        if not conversation_timing_controller.can_speak(priority, turn_id):
            print(f"[COMPLETION_DISPATCHER] ⏳ Speech suppressed by conversation timing controller (active_turn={conversation_timing_controller.active_turn_id})")
            return None

        if success:
            bound = execution_response_binder.bind_success(contract, verified_data)
        else:
            bound = execution_response_binder.bind_failure(contract, error=error, verified_data=verified_data)

        if not bound.spoken_text:
            return bound

        # Check Duplicate Response Guard
        resp_type = "COMPLETION" if success else "FAILURE"
        task_id = verified_data.get("task_id", "") if verified_data else ""
        if duplicate_response_guard.should_suppress(turn_id, task_id, resp_type, bound.spoken_text):
            print(f"[COMPLETION_DISPATCHER] 🛡️ Suppressed duplicate response: '{bound.spoken_text}'")
            return None

        # Record spoken response
        duplicate_response_guard.record_spoken(turn_id, task_id, resp_type, bound.spoken_text)

        if bound.requires_announcement:
            print(f"[COMPLETION_DISPATCHER] 📢 Released completion: '{bound.spoken_text}'")
            if ui_callback:
                try:
                    ui_callback(bound.spoken_text)
                except Exception as e:
                    print(f"[COMPLETION_DISPATCHER] UI callback error: {e}")

        return bound


# Global singleton instance
instant_completion_dispatcher = InstantCompletionDispatcher()
