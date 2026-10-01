"""
Task Lease Manager for Persistent Agent Runtime in MARK XLVIII / JARVIS.
Coordinates distributed lease acquisition and locks on shared mutating resources
to prevent split-brain execution and duplicate mutations across concurrent runtimes.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TaskLease:
    lease_id: str
    resource_id: str
    owner_runtime_id: str
    acquired_at: float
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class TaskLeaseManager:
    """
    Manages time-bound mutual exclusion leases for mutating operations.
    """

    def __init__(self):
        self._leases: Dict[str, TaskLease] = {}  # resource_id -> TaskLease

    def acquire_lease(
        self,
        resource_id: str,
        runtime_id: str,
        ttl_seconds: float = 30.0,
    ) -> Optional[str]:
        """
        Attempts to acquire an exclusive execution lease for a resource.
        Returns lease_id if acquired, None if locked by active owner.
        """
        res_key = resource_id.lower().strip()
        now = time.time()

        existing = self._leases.get(res_key)
        if existing and not existing.is_expired():
            if existing.owner_runtime_id != runtime_id:
                # Active lease owned by another runtime
                return None
            else:
                # Same owner renewing
                existing.expires_at = now + ttl_seconds
                return existing.lease_id

        lease_id = f"lease_{uuid.uuid4().hex[:8]}"
        lease = TaskLease(
            lease_id=lease_id,
            resource_id=res_key,
            owner_runtime_id=runtime_id,
            acquired_at=now,
            expires_at=now + ttl_seconds,
        )
        self._leases[res_key] = lease
        return lease_id

    def renew_lease(self, lease_id: str, ttl_seconds: float = 30.0) -> bool:
        now = time.time()
        for lease in self._leases.values():
            if lease.lease_id == lease_id and not lease.is_expired():
                lease.expires_at = now + ttl_seconds
                return True
        return False

    def release_lease(self, lease_id: str) -> bool:
        for res_key, lease in list(self._leases.items()):
            if lease.lease_id == lease_id:
                self._leases.pop(res_key, None)
                return True
        return False

    def is_lease_active(self, resource_id: str) -> bool:
        res_key = resource_id.lower().strip()
        lease = self._leases.get(res_key)
        return bool(lease and not lease.is_expired())

    def clear_all(self) -> None:
        self._leases.clear()


# Global singleton instance
task_lease_manager = TaskLeaseManager()
