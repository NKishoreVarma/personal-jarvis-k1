"""
Improvement Regression Monitor for Autonomous Continuous Learning in MARK XLVIII / JARVIS.
Monitors the runtime health of activated improvements and automatically triggers rollbacks upon regression.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.improvement_opportunity_contract import ImprovementOpportunityContract, ImprovementState
from core.improvement_promotion_manager import improvement_promotion_manager


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class ImprovementRegressionMonitor:
    """
    Monitors live metrics of active improvements to trigger health degradation alerts and automatic rollbacks.
    """

    def __init__(self):
        self._component_health: Dict[str, HealthStatus] = {}

    def record_execution_metric(
        self,
        component: str,
        success: bool,
        duration: float,
        safety_violation: bool = False,
    ) -> Tuple[HealthStatus, Optional[str]]:
        """
        Updates telemetry for active component improvement.
        If degradation or safety violation occurs, initiates rollback.
        """
        active_imp = improvement_promotion_manager.get_active_improvement(component)
        if not active_imp:
            return HealthStatus.HEALTHY, None

        if safety_violation:
            self._component_health[component] = HealthStatus.CRITICAL
            improvement_promotion_manager.rollback_improvement(
                active_imp.opportunity_id, reason="Safety violation detected during execution."
            )
            return HealthStatus.CRITICAL, "Critical safety violation. Automatic rollback executed."

        if not success:
            self._component_health[component] = HealthStatus.DEGRADED
            improvement_promotion_manager.rollback_improvement(
                active_imp.opportunity_id, reason="Success rate regression detected."
            )
            return HealthStatus.DEGRADED, "Regression detected. Automatic rollback executed."

        self._component_health[component] = HealthStatus.HEALTHY
        return HealthStatus.HEALTHY, "Component operating normally."

    def get_status(self, component: str) -> HealthStatus:
        return self._component_health.get(component, HealthStatus.HEALTHY)

    def clear(self) -> None:
        self._component_health.clear()


# Global singleton instance
improvement_regression_monitor = ImprovementRegressionMonitor()
