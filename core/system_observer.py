"""
System & Process Observer for MARK XLVIII / JARVIS.
Integrates with SystemMonitor and ProcessManager to observe CPU, RAM, disk, battery,
listening ports, background services, and application health metrics.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from actions.system_monitor import SystemMonitor
from core.perception_contract import (
    Observation,
    ObservationType,
    PrivacyClassification,
    create_observation,
)
from core.process_manager import ProcessManager


class SystemObserver:
    """
    Samples host resource consumption and network/port state without blocking audio callbacks.
    """

    def __init__(
        self,
        sys_monitor: Optional[SystemMonitor] = None,
        process_mgr: Optional[ProcessManager] = None,
    ):
        self.sys_monitor = sys_monitor or SystemMonitor()
        self.process_mgr = process_mgr or ProcessManager()

    def observe(
        self,
        ports_to_probe: Optional[List[int]] = None,
        correlation_id: Optional[str] = None,
    ) -> Observation:
        """
        Samples system metrics, tests active ports, and packages into a normalized Observation record.
        """
        t0 = time.perf_counter()

        try:
            metrics = self.sys_monitor.sample_metrics()
            alerts = self.sys_monitor.check_health_thresholds()

            # Probe listening ports if specified (e.g. 3000, 8000, 8080)
            port_states: Dict[str, bool] = {}
            if ports_to_probe:
                for port in ports_to_probe:
                    is_open = self.process_mgr.verify_port_open(port, timeout=0.5)
                    port_states[str(port)] = is_open

            elapsed_ms = (time.perf_counter() - t0) * 1000

            content = {
                "battery": metrics.get("battery", {}),
                "disk": metrics.get("disk", {}),
                "memory": metrics.get("memory", {}),
                "alerts": alerts,
                "listening_ports": port_states,
                "is_healthy": len(alerts) == 0,
                "sampling_latency_ms": round(elapsed_ms, 2),
            }

            return create_observation(
                observation_type=ObservationType.SYSTEM,
                source="system_observer",
                content=content,
                confidence=0.99,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=20.0,
                correlation_id=correlation_id,
                is_verified=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return create_observation(
                observation_type=ObservationType.SYSTEM,
                source="system_observer",
                content={
                    "error": str(e),
                    "status": "SYSTEM_OBSERVE_FAILED",
                    "sampling_latency_ms": round(elapsed_ms, 2),
                },
                confidence=0.0,
                privacy_classification=PrivacyClassification.INTERNAL,
                ttl_seconds=5.0,
                correlation_id=correlation_id,
                is_verified=False,
            )


# Global singleton instance
system_observer = SystemObserver()
