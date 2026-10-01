"""
Laya Health Monitor for System 1 in MARK XLVIII / JARVIS.
Tracks inference success rates, latencies, timeouts, and memory pressure to trigger automatic degradation when unhealthy.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    REAL_MODEL_HEALTHY = "REAL_MODEL_HEALTHY"
    REAL_MODEL_UNAVAILABLE = "REAL_MODEL_UNAVAILABLE"
    REAL_MODEL_DEGRADED = "REAL_MODEL_DEGRADED"
    SIMULATOR_FALLBACK = "SIMULATOR_FALLBACK"
    DISABLED = "DISABLED"


@dataclass
class LayaHealthMetrics:
    model_loaded: bool = False
    model_available: bool = True
    is_real_model: bool = False
    inference_success_count: int = 0
    inference_failure_count: int = 0
    timeout_count: int = 0
    fallback_count: int = 0
    consecutive_failures: int = 0
    total_latency_ms: float = 0.0
    memory_pressure: bool = False
    health_state: HealthState = HealthState.HEALTHY
    updated_at: float = field(default_factory=time.time)


class LayaHealthMonitor:
    """
    Monitors Laya execution health and telemetry.
    """

    def __init__(self):
        self.metrics = LayaHealthMetrics()

    def record_success(self, latency_ms: float) -> None:
        self.metrics.inference_success_count += 1
        self.metrics.consecutive_failures = 0
        self.metrics.total_latency_ms += latency_ms
        self.metrics.model_loaded = True
        self.metrics.updated_at = time.time()
        self._evaluate_health()

    def record_failure(self, is_timeout: bool = False) -> None:
        self.metrics.inference_failure_count += 1
        self.metrics.consecutive_failures += 1
        if is_timeout:
            self.metrics.timeout_count += 1
        self.metrics.updated_at = time.time()
        self._evaluate_health()

    def record_fallback(self) -> None:
        self.metrics.fallback_count += 1
        self.metrics.updated_at = time.time()

    def set_memory_pressure(self, under_pressure: bool) -> None:
        self.metrics.memory_pressure = under_pressure
        self._evaluate_health()

    def _evaluate_health(self) -> None:
        if self.metrics.memory_pressure or self.metrics.consecutive_failures >= 5:
            self.metrics.health_state = HealthState.UNHEALTHY
            return

        total = self.metrics.inference_success_count + self.metrics.inference_failure_count
        if total == 0:
            self.metrics.health_state = HealthState.HEALTHY
            return

        fail_rate = self.metrics.inference_failure_count / total
        if fail_rate > 0.50:
            self.metrics.health_state = HealthState.UNHEALTHY
        elif self.metrics.consecutive_failures >= 2 or fail_rate > 0.20:
            self.metrics.health_state = HealthState.DEGRADED
        else:
            self.metrics.health_state = HealthState.HEALTHY

    def get_status(self) -> Dict[str, Any]:
        total = self.metrics.inference_success_count + self.metrics.inference_failure_count
        avg_lat = (self.metrics.total_latency_ms / max(1, self.metrics.inference_success_count)) if self.metrics.inference_success_count > 0 else 0.0
        return {
            "health_state": self.metrics.health_state.value,
            "model_loaded": self.metrics.model_loaded,
            "model_available": self.metrics.model_available,
            "success_count": self.metrics.inference_success_count,
            "failure_count": self.metrics.inference_failure_count,
            "fallback_count": self.metrics.fallback_count,
            "timeout_count": self.metrics.timeout_count,
            "average_latency_ms": round(avg_lat, 2),
            "memory_pressure": self.metrics.memory_pressure,
        }

    def reset(self) -> None:
        self.metrics = LayaHealthMetrics()


# Global singleton instance
laya_health_monitor = LayaHealthMonitor()
