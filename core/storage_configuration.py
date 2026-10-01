"""
Storage Configuration & Health Manager for Persistent Memory in MARK XLVIII / JARVIS.
Handles external SSD data storage path resolution, environment variable overrides,
disk write validation, and graceful degradation when external storage fails.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class StorageHealthStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    READ_ONLY = "READ_ONLY"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class StorageConfiguration:
    data_root: str
    postgres_data_path: str
    database_url: str
    status: StorageHealthStatus = StorageHealthStatus.ACTIVE
    error_message: Optional[str] = None

    @classmethod
    def from_env(cls) -> StorageConfiguration:
        data_root = os.getenv("JARVIS_DATA_ROOT", "data")
        pg_path = os.getenv("JARVIS_POSTGRES_DATA_PATH", os.path.join(data_root, "postgres"))
        db_url = os.getenv("JARVIS_MEMORY_DATABASE_URL", "postgresql://localhost/jarvis_memory")
        config = cls(
            data_root=data_root,
            postgres_data_path=pg_path,
            database_url=db_url,
        )
        config.validate_storage()
        return config

    def validate_storage(self) -> Tuple[StorageHealthStatus, str]:
        """
        Validates directory existence, writability, and free space.
        """
        try:
            os.makedirs(self.data_root, exist_ok=True)
            # Test writability
            test_file = os.path.join(self.data_root, ".write_test")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_file)

            # Check disk space
            total, used, free = shutil.disk_usage(self.data_root)
            if free < 10 * 1024 * 1024:  # Less than 10MB
                self.status = StorageHealthStatus.DEGRADED
                self.error_message = "Low disk space (< 10MB available)."
                return self.status, self.error_message

            self.status = StorageHealthStatus.ACTIVE
            self.error_message = None
            return self.status, "Storage is active and writable."

        except PermissionError:
            self.status = StorageHealthStatus.READ_ONLY
            self.error_message = "Storage root is read-only."
            return self.status, self.error_message

        except Exception as e:
            self.status = StorageHealthStatus.DEGRADED
            self.error_message = f"Storage validation error: {e}"
            return self.status, self.error_message

    def is_degraded(self) -> bool:
        return self.status in [StorageHealthStatus.DEGRADED, StorageHealthStatus.UNAVAILABLE]


# Global singleton instance
storage_configuration = StorageConfiguration.from_env()
