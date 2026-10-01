"""
Regression Detector for MARK XLVIII / JARVIS.
Detects performance regressions, repeated failure spikes, and latency degradation
in previously reliable skills and strategies.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.capability_performance_tracker import CapabilityPerformance, capability_performance_tracker


class RegressionState(str, Enum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class RegressionDetector:
    """
    Evaluates CapabilityPerformance to classify regression state.
    """

    def detect_regression(self, capability_id: str) -> Tuple[RegressionState, str]:
        """
        Analyzes capability metrics and returns (RegressionState, explanation).
        """
        perf = capability_performance_tracker.get_performance(capability_id)
        if not perf or perf.total_executions == 0:
            return RegressionState.HEALTHY, "No execution history yet."

        # 1. Critical failure spike
        if perf.failure_count >= 3 and perf.success_rate < 0.50:
            return RegressionState.CRITICAL, f"Critical failure rate ({perf.failure_count} failures, {perf.success_rate:.0%} success rate)."

        # 2. Degraded state
        if perf.regression_score >= 0.5 or perf.success_rate < 0.70 or perf.retry_rate > 0.6:
            return RegressionState.DEGRADED, f"Degraded performance: retry rate={perf.retry_rate:.1f}, success rate={perf.success_rate:.0%}."

        # 3. Watch state (recent single failure or elevated retries)
        if perf.failure_count > 0 or perf.retry_rate > 0.3 or perf.average_duration > 10.0:
            return RegressionState.WATCH, f"Performance under watch: avg duration={perf.average_duration:.1f}s, failures={perf.failure_count}."

        return RegressionState.HEALTHY, "Operating normally with high reliability."

    def is_degraded(self, capability_id: str) -> bool:
        state, _ = self.detect_regression(capability_id)
        return state in [RegressionState.DEGRADED, RegressionState.CRITICAL]


# Global singleton instance
regression_detector = RegressionDetector()
