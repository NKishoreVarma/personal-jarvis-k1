"""
Intent Stability Manager for MARK XLVIII / JARVIS.
Tracks the confidence progression and entity consistency of streaming intents,
detecting stable intentions for instant preparation while rapidly invalidating contradictory pivots.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from core.predictive_execution import predictive_manager
from core.streaming_intent_engine import StreamingIntent


class StabilityState(str, Enum):
    UNKNOWN = "UNKNOWN"
    TENTATIVE = "TENTATIVE"
    STABLE = "STABLE"
    CHANGED = "CHANGED"
    INVALIDATED = "INVALIDATED"


class IntentStabilityManager:
    """
    Evaluates streaming intent stability and manages rapid preparation invalidation upon topic pivots.
    """

    STABILITY_CONFIDENCE_THRESHOLD = 0.85
    MIN_CONSISTENT_UPDATES = 2

    def __init__(self):
        self._turn_states: Dict[str, StabilityState] = {}
        self._latest_intents: Dict[str, StreamingIntent] = {}
        self._consistency_counts: Dict[str, int] = {}

    def evaluate_stability(self, new_intent: StreamingIntent) -> StabilityState:
        """
        Evaluates stability of incoming streaming intent against turn history.
        """
        turn_id = new_intent.turn_id
        prev_intent = self._latest_intents.get(turn_id)

        # First intent for turn
        if prev_intent is None:
            self._latest_intents[turn_id] = new_intent
            self._consistency_counts[turn_id] = 1
            state = StabilityState.STABLE if new_intent.confidence >= 0.95 else StabilityState.TENTATIVE
            self._turn_states[turn_id] = state
            return state

        # Check for contradiction / meaning shift
        is_contradiction = False

        # Intent type conflict
        if prev_intent.intent_type != "UNKNOWN" and new_intent.intent_type != "UNKNOWN":
            # Compatible promotions (e.g. PROJECT_OPERATION -> RUN_PROJECT)
            compatible_promotions = {
                ("PROJECT_OPERATION", "RUN_PROJECT"),
                ("RUN_PROJECT", "PROJECT_OPERATION"),
            }
            if prev_intent.intent_type != new_intent.intent_type and (prev_intent.intent_type, new_intent.intent_type) not in compatible_promotions:
                is_contradiction = True

        # Entity conflict (e.g. project FLOW vs app Chrome)
        for key in ["project", "app_name"]:
            if key in prev_intent.entities and key in new_intent.entities:
                if str(prev_intent.entities[key]).lower() != str(new_intent.entities[key]).lower():
                    is_contradiction = True
                    break

        if is_contradiction:
            print(f"[STABILITY] ⚠️ Contradiction detected in turn {turn_id}: '{prev_intent.intent_type}' -> '{new_intent.intent_type}'. Invalidating prior preparation.")
            self._turn_states[turn_id] = StabilityState.CHANGED
            self._consistency_counts[turn_id] = 1
            self._latest_intents[turn_id] = new_intent
            # Invalidate stale predictive preparation immediately
            predictive_manager.invalidate_turn(turn_id)
            return StabilityState.CHANGED

        # Incremental consistency
        self._consistency_counts[turn_id] = self._consistency_counts.get(turn_id, 1) + 1
        self._latest_intents[turn_id] = new_intent

        count = self._consistency_counts[turn_id]
        if new_intent.confidence >= self.STABILITY_CONFIDENCE_THRESHOLD and count >= self.MIN_CONSISTENT_UPDATES:
            state = StabilityState.STABLE
        elif new_intent.confidence >= 0.95:
            state = StabilityState.STABLE
        else:
            state = StabilityState.TENTATIVE

        self._turn_states[turn_id] = state
        return state

    def is_stable(self, turn_id: str) -> bool:
        return self._turn_states.get(turn_id) == StabilityState.STABLE

    def get_latest_intent(self, turn_id: str) -> Optional[StreamingIntent]:
        return self._latest_intents.get(turn_id)

    def get_state(self, turn_id: str) -> StabilityState:
        return self._turn_states.get(turn_id, StabilityState.UNKNOWN)

    def clear_turn(self, turn_id: str) -> None:
        self._turn_states.pop(turn_id, None)
        self._latest_intents.pop(turn_id, None)
        self._consistency_counts.pop(turn_id, None)


# Global singleton instance
intent_stability_manager = IntentStabilityManager()
