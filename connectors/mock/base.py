"""
Base Mock Connector Interface for MARK XLVIII / FLOW.
Provides state storage, simulation of network latency, auth expiry, timeouts, and false successes.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class BaseMockConnector:
    """Base class for all in-memory mock connectors."""

    def __init__(self, name: str):
        self.name = name
        self.authenticated = True
        self.simulate_timeout = False
        self.simulate_network_error = False
        self.simulate_false_success = False

    def _check_preconditions(self) -> None:
        """Enforces authentication and error simulation flags."""
        if not self.authenticated:
            raise PermissionError(f"Connector '{self.name}' authentication has expired. Please re-authenticate.")
        if self.simulate_timeout:
            raise TimeoutError(f"Connector '{self.name}' request timed out.")
        if self.simulate_network_error:
            raise ConnectionError(f"Connector '{self.name}' failed to connect to remote service.")

    def reset(self) -> None:
        """Reset state and simulation flags."""
        self.authenticated = True
        self.simulate_timeout = False
        self.simulate_network_error = False
        self.simulate_false_success = False
