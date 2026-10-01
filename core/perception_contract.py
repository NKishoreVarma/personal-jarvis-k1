"""
Perception Contract — Unified Observation Schemas & Invariants for MARK XLVIII / JARVIS.
Defines strongly typed, bounded observation contracts, freshness lifecycles,
and privacy classifications across all sensory modalities.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ObservationType(str, Enum):
    SCREEN = "SCREEN"
    WINDOW = "WINDOW"
    APPLICATION = "APPLICATION"
    OCR = "OCR"
    IMAGE = "IMAGE"
    VIDEO_FRAME = "VIDEO_FRAME"
    AUDIO_CONTEXT = "AUDIO_CONTEXT"
    PROCESS = "PROCESS"
    NETWORK = "NETWORK"
    FILESYSTEM = "FILESYSTEM"
    BROWSER = "BROWSER"
    DEVICE = "DEVICE"
    SYSTEM = "SYSTEM"
    ENVIRONMENT = "ENVIRONMENT"
    USER_INTERFACE = "USER_INTERFACE"


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class PrivacyClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


# Default TTL thresholds in seconds by observation type
DEFAULT_OBSERVATION_TTL: Dict[ObservationType, float] = {
    ObservationType.SCREEN: 10.0,
    ObservationType.WINDOW: 15.0,
    ObservationType.APPLICATION: 30.0,
    ObservationType.OCR: 20.0,
    ObservationType.IMAGE: 30.0,
    ObservationType.VIDEO_FRAME: 5.0,
    ObservationType.AUDIO_CONTEXT: 8.0,
    ObservationType.PROCESS: 15.0,
    ObservationType.NETWORK: 30.0,
    ObservationType.FILESYSTEM: 60.0,
    ObservationType.BROWSER: 20.0,
    ObservationType.DEVICE: 60.0,
    ObservationType.SYSTEM: 20.0,
    ObservationType.ENVIRONMENT: 30.0,
    ObservationType.USER_INTERFACE: 15.0,
}


@dataclass
class Observation:
    """
    Normalized, structured environmental observation record.
    Never stores unrestricted raw binary streams or unsanitized credentials by default.
    """
    observation_id: str
    observation_type: ObservationType
    source: str
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    freshness: FreshnessState = FreshnessState.FRESH
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    evidence_references: List[str] = field(default_factory=list)
    privacy_classification: PrivacyClassification = PrivacyClassification.INTERNAL
    ttl_seconds: float = 30.0
    expiration: float = 0.0
    correlation_id: str = ""
    is_verified: bool = False

    def __post_init__(self):
        if not self.observation_id:
            self.observation_id = f"obs_{uuid.uuid4().hex[:8]}"
        if not self.correlation_id:
            self.correlation_id = f"corr_{uuid.uuid4().hex[:8]}"
        if self.expiration <= 0.0:
            self.expiration = self.timestamp + self.ttl_seconds
        # Clamp confidence to [0.0, 1.0]
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        self.update_freshness()

    def update_freshness(self, current_time: Optional[float] = None) -> FreshnessState:
        """Computes current freshness state based on elapsed time vs TTL."""
        now = current_time if current_time is not None else time.time()
        elapsed = now - self.timestamp

        if elapsed > self.ttl_seconds:
            self.freshness = FreshnessState.EXPIRED
        elif elapsed > (self.ttl_seconds * 0.70):
            self.freshness = FreshnessState.STALE
        elif elapsed > (self.ttl_seconds * 0.40):
            self.freshness = FreshnessState.AGING
        else:
            self.freshness = FreshnessState.FRESH

        return self.freshness

    def is_fresh(self, current_time: Optional[float] = None) -> bool:
        """Returns True if observation is FRESH or AGING (usable), False if STALE or EXPIRED."""
        st = self.update_freshness(current_time)
        return st in (FreshnessState.FRESH, FreshnessState.AGING)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return now >= self.expiration or self.freshness == FreshnessState.EXPIRED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "observation_type": self.observation_type.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "freshness": self.freshness.value,
            "content": self.content,
            "metadata": self.metadata,
            "evidence_references": self.evidence_references,
            "privacy_classification": self.privacy_classification.value,
            "ttl_seconds": self.ttl_seconds,
            "expiration": self.expiration,
            "correlation_id": self.correlation_id,
            "is_verified": self.is_verified,
        }


def create_observation(
    observation_type: ObservationType,
    source: str = "",
    content: Optional[Dict[str, Any]] = None,
    confidence: float = 1.0,
    privacy_classification: PrivacyClassification = PrivacyClassification.INTERNAL,
    ttl_seconds: Optional[float] = None,
    evidence_references: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    is_verified: bool = False,
    observation_id: Optional[str] = None,
    source_observer: Optional[str] = None,
    **kwargs: Any,
) -> Observation:
    """Helper to instantiate validated Observation objects with type-specific default TTLs."""
    actual_source = source or source_observer or kwargs.get("observer", "unknown")
    actual_content = content if content is not None else {}
    actual_ttl = ttl_seconds if ttl_seconds is not None else DEFAULT_OBSERVATION_TTL.get(observation_type, 30.0)
    now = time.time()
    return Observation(
        observation_id=observation_id or f"obs_{uuid.uuid4().hex[:8]}",
        observation_type=observation_type,
        source=actual_source,
        timestamp=now,
        confidence=confidence,
        freshness=FreshnessState.FRESH,
        content=actual_content,
        metadata=metadata or {},
        evidence_references=evidence_references or [],
        privacy_classification=privacy_classification,
        ttl_seconds=actual_ttl,
        expiration=now + actual_ttl,
        correlation_id=correlation_id or f"corr_{uuid.uuid4().hex[:8]}",
        is_verified=is_verified,
    )


def validate_observation(obs: Observation) -> Tuple[bool, str]:
    """Validates structural constraints and size bounds on an observation."""
    if not isinstance(obs, Observation):
        return False, "Not an Observation instance"
    if not obs.observation_id:
        return False, "Missing observation_id"
    if not isinstance(obs.observation_type, ObservationType):
        return False, "Invalid observation_type"
    if not obs.source:
        return False, "Missing observation source"
    if not (0.0 <= obs.confidence <= 1.0):
        return False, "Confidence must be within [0.0, 1.0]"
    
    # Bounded payload check: prevent unbounded memory consumption
    import sys
    content_size = sys.getsizeof(str(obs.content))
    if content_size > 1_000_000:  # 1 MB soft cap for structured content
        return False, f"Content payload too large ({content_size} bytes > 1MB)"

    return True, "Valid"
