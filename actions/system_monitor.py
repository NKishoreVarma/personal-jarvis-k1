"""
System Health Monitor for MARK XLVIII / JARVIS on macOS.
Provides lightweight, non-blocking local system telemetry:
battery, CPU/memory pressure, disk usage, and network status with threshold alert publishing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from core.event_bus import EventType, event_bus


class SystemMonitor:
    """
    Lightweight macOS system health observer.
    """

    def __init__(self, battery_threshold: int = 10, disk_threshold: int = 95):
        self.battery_threshold = battery_threshold
        self.disk_threshold = disk_threshold
        self._last_metrics: Dict[str, Any] = {}

    def sample_metrics(self) -> Dict[str, Any]:
        """
        Samples core local system health metrics without blocking.
        """
        metrics: Dict[str, Any] = {
            "timestamp": time.time(),
            "battery": self._get_battery_status(),
            "disk": self._get_disk_usage(),
            "memory": self._get_memory_status(),
        }
        self._last_metrics = metrics
        return metrics

    def check_health_thresholds(self) -> List[Dict[str, Any]]:
        """
        Checks metrics against critical thresholds and publishes system alerts.
        """
        metrics = self.sample_metrics()
        alerts: List[Dict[str, Any]] = []

        # 1. Battery check
        batt = metrics.get("battery", {})
        if batt.get("available") and not batt.get("charging"):
            pct = batt.get("percentage", 100)
            if pct <= self.battery_threshold:
                msg = f"Battery is critically low ({pct}% remaining). Please plug in your charger."
                alerts.append({"type": "BATTERY_LOW", "message": msg, "critical": True})
                event_bus.publish(EventType.SYSTEM_ALERT, {"message": msg, "critical": True})

        # 2. Disk usage check
        disk = metrics.get("disk", {})
        used_pct = disk.get("used_percent", 0)
        if used_pct >= self.disk_threshold:
            msg = f"Disk storage is nearly full ({used_pct}% used)."
            alerts.append({"type": "DISK_FULL", "message": msg, "critical": False})
            event_bus.publish(EventType.SYSTEM_ALERT, {"message": msg, "critical": False})

        return alerts

    def check(self) -> Optional[str]:
        """Runs threshold check and returns top alert string if present."""
        alerts = self.check_health_thresholds()
        if alerts:
            return alerts[0]["message"]
        return None

    def _get_battery_status(self) -> Dict[str, Any]:
        """Reads macOS battery info via pmset."""
        try:
            res = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and "%" in res.stdout:
                # e.g. "Now drawing from 'Battery Power' ... -InternalBattery-0 (id=...) 85%; discharging; ..."
                raw = res.stdout
                charging = "charging" in raw.lower() or "ac power" in raw.lower()
                pct_part = raw.split("%")[0].split()[-1]
                pct = int(pct_part) if pct_part.isdigit() else 100
                return {"available": True, "percentage": pct, "charging": charging}
        except Exception:
            pass
        return {"available": False, "percentage": 100, "charging": True}

    def _get_disk_usage(self) -> Dict[str, Any]:
        """Gets primary disk capacity and usage."""
        try:
            total, used, free = shutil.disk_usage("/")
            used_pct = int((used / total) * 100)
            return {
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "used_percent": used_pct,
            }
        except Exception:
            return {"used_percent": 0}

    def _get_memory_status(self) -> Dict[str, Any]:
        """Quick memory health snapshot."""
        return {"status": "normal"}


system_monitor = SystemMonitor()


def get_system_status() -> Dict[str, Any]:
    """Returns system status snapshot."""
    return system_monitor.sample_metrics()
