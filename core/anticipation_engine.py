"""
Anticipation Engine for MARK XLVIII / JARVIS.
Predicts probable next user intents and operational workflows based on verified context.
Enforces the safety invariant: PREDICTION != EXECUTION (Predictions are strictly non-mutating).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.context_contract import ContextContract, ContextTaskState


@dataclass
class Prediction:
    prediction_id: str
    predicted_next_action: str
    target_project: str
    confidence: float
    expected_value: str  # low, medium, high, critical
    risk_level: str = "low_risk"
    preparation_allowed: bool = True
    expires_at: float = field(default_factory=lambda: time.time() + 45.0)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "predicted_next_action": self.predicted_next_action,
            "target_project": self.target_project,
            "confidence": self.confidence,
            "expected_value": self.expected_value,
            "risk_level": self.risk_level,
            "preparation_allowed": self.preparation_allowed,
            "expires_at": self.expires_at,
            "parameters": self.parameters,
            "is_expired": self.is_expired(),
        }


class AnticipationEngine:
    """
    Generates predictive next-action candidates from verified operational context.
    """

    def predict_next_need(self, context: ContextContract) -> Optional[Prediction]:
        """
        Predicts probable user need without performing any side-effects.
        """
        if context.is_expired():
            return None

        proj = context.active_project or "FLOW"

        # Scenario 1: Project Running -> Predict browser access
        if context.task_state == ContextTaskState.RUNNING:
            port = 3000
            for a in context.recent_verified_actions:
                if a.get("port"):
                    port = a.get("port")
                    break

            return Prediction(
                prediction_id=f"pred_open_{uuid.uuid4().hex[:6]}",
                predicted_next_action="open_browser",
                target_project=proj,
                confidence=0.94,
                expected_value="high",
                risk_level="low_risk",
                preparation_allowed=True,
                parameters={"url": f"http://localhost:{port}", "port": port},
            )

        # Scenario 2: Project Failed -> Predict diagnostic repair
        if context.task_state == ContextTaskState.FAILED:
            return Prediction(
                prediction_id=f"pred_repair_{uuid.uuid4().hex[:6]}",
                predicted_next_action="diagnose_and_repair",
                target_project=proj,
                confidence=0.91,
                expected_value="high",
                risk_level="low_risk",
                preparation_allowed=True,
                parameters={"project": proj},
            )

        # Scenario 3: Starting / Waiting -> Predict monitoring
        if context.task_state in [ContextTaskState.STARTING, ContextTaskState.WAITING]:
            return Prediction(
                prediction_id=f"pred_mon_{uuid.uuid4().hex[:6]}",
                predicted_next_action="monitor_startup",
                target_project=proj,
                confidence=0.89,
                expected_value="medium",
                risk_level="read_only",
                preparation_allowed=True,
                parameters={"project": proj},
            )

        return None


# Global singleton instance
anticipation_engine = AnticipationEngine()
