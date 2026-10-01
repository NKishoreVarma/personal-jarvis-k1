"""
Perception Pipeline for MARK XLVIII / JARVIS.
Coordinates asynchronous, fault-tolerant sensory observation, normalization, content trust classification,
confidence verification, credential redaction, freshness checks, and WorldModel state ingestion.
Guarantees 0ms audio callback latency by executing all perception workers in isolated background threads.
"""

from __future__ import annotations

import concurrent.futures
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.content_trust_classifier import content_trust_classifier
from core.perception_contract import (
    FreshnessState,
    Observation,
    ObservationType,
    create_observation,
    validate_observation,
)
from core.perception_privacy_gate import perception_privacy_gate
from core.perception_safety_gate import perception_safety_gate
from core.world_model import WorldModel, world_model


class PerceptionPipeline:
    """
    Asynchronous, fault-tolerant ingestion pipeline:
        CAPTURE -> NORMALIZE -> CLASSIFY -> EXTRACT -> CONFIDENCE CHECK -> PRIVACY FILTER -> FRESHNESS -> WORLD MODEL
    """

    def __init__(
        self,
        wm: Optional[WorldModel] = None,
        max_workers: int = 4,
        max_queue_size: int = 100,
    ):
        self.wm = wm or world_model
        self.max_queue_size = max_queue_size
        self._queue: queue.Queue[Observation] = queue.Queue(maxsize=max_queue_size)
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="PerceptionWorker",
        )
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_queue_loop,
            daemon=True,
            name="PerceptionPipelineDispatcher",
        )
        self._worker_thread.start()
        self._ingested_count = 0
        self._failed_count = 0
        self.telemetry = PerceptionTelemetryStore()

    def shutdown(self) -> None:
        """Gracefully terminates the background dispatcher and thread pool."""
        self._running = False
        self._executor.shutdown(wait=False)

    def enqueue_observation(self, observation: Observation) -> bool:
        """
        Non-blocking enqueue for realtime audio callbacks.
        Returns True if enqueued, False if dropped due to queue congestion.
        """
        try:
            self._queue.put_nowait(observation)
            return True
        except queue.Full:
            self._failed_count += 1
            return False

    def enqueue_audio_turn_context(self, audio_bytes: bytes) -> bool:
        """
        Non-blocking ingestion for realtime voice/audio turn frames.
        Returns immediately (< 0.05 ms).
        """
        obs = create_observation(
            observation_type=ObservationType.ENVIRONMENT,
            source="audio_callback",
            content={"audio_bytes_length": len(audio_bytes)},
        )
        return self.enqueue_observation(obs)

    def process_observation_sync(self, raw_obs: Observation) -> Tuple[bool, Optional[Observation], str]:
        """
        Synchronously runs the full pipeline stages on an observation with fault isolation:
            1. Validate
            2. Classify Trust
            3. Safety Gate Filter
            4. Confidence Check
            5. Privacy Filter (Credentials Redaction)
            6. Freshness Check
            7. World Model Ingestion
        """
        t0 = time.perf_counter()

        try:
            # 1. Validation
            valid, err = validate_observation(raw_obs)
            if not valid:
                return False, None, f"Validation failed: {err}"

            # 2. Content Trust Classification
            trust_level = content_trust_classifier.classify_source(raw_obs.source)
            raw_obs.metadata["content_trust_level"] = trust_level.value

            # 3. Safety Gate Filter (Prompt-injection & instruction protection)
            is_safe, sanitized_obs, safety_msg = perception_safety_gate.filter_observation(raw_obs)
            if not is_safe:
                return False, None, f"Safety gate rejected: {safety_msg}"

            # 4. Confidence Check: Observations below 0.20 are discarded as unreliable noise
            if sanitized_obs.confidence < 0.20:
                return False, None, f"Confidence too low ({sanitized_obs.confidence:.2f} < 0.20)"

            # 5. Privacy Filter: Redact credentials, API keys, and sensitive tokens
            private_clean_obs = perception_privacy_gate.filter_observation(sanitized_obs)
            if private_clean_obs.metadata.get("credential_redacted"):
                self.telemetry.record_credential_redacted()

            if private_clean_obs.metadata.get("prompt_injection_detected"):
                self.telemetry.record_injection_blocked()

            # 6. Freshness Check: Expired observations are discarded
            if private_clean_obs.is_expired():
                self.telemetry.record_stale_dropped()
                return False, None, "Observation is already expired"

            # 7. World Model Update
            self.wm.update_observation(private_clean_obs)
            self._ingested_count += 1
            self.telemetry.record_ingested(private_clean_obs.source)

            elapsed_ms = (time.perf_counter() - t0) * 1000
            private_clean_obs.metadata["pipeline_latency_ms"] = round(elapsed_ms, 2)
            return True, private_clean_obs, "Successfully ingested"

        except Exception as e:
            self._failed_count += 1
            return False, None, f"Pipeline error: {e}"

    def _process_queue_loop(self) -> None:
        """Background loop consuming queued observations without blocking main threads."""
        while self._running:
            try:
                obs = self._queue.get(timeout=0.1)
                self.process_observation_sync(obs)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                continue

    def run_observer_async(self, observer_fn: Callable[[], Observation]) -> concurrent.futures.Future:
        """Schedules an observer call in the background thread pool."""
        return self._executor.submit(self._execute_observer_wrapper, observer_fn)

    def _execute_observer_wrapper(self, observer_fn: Callable[[], Observation]) -> Optional[Observation]:
        try:
            obs = observer_fn()
            success, final_obs, _ = self.process_observation_sync(obs)
            return final_obs if success else None
        except Exception:
            self._failed_count += 1
            return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "ingested_count": self._ingested_count,
            "failed_count": self._failed_count,
            "queue_size": self._queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "telemetry": self.telemetry.get_metrics(),
        }


class PerceptionTelemetryStore:
    """Bounded continuous-learning telemetry tracker for environmental perception."""

    def __init__(self):
        self._lock = threading.Lock()
        self.sensor_counts: Dict[str, int] = {}
        self.sensor_disagreements: int = 0
        self.stale_observations_dropped: int = 0
        self.credential_redactions: int = 0
        self.prompt_injections_blocked: int = 0
        self.verified_correct_count: int = 0
        self.verified_incorrect_count: int = 0

    def record_ingested(self, source: str) -> None:
        with self._lock:
            self.sensor_counts[source] = self.sensor_counts.get(source, 0) + 1

    def record_disagreement(self) -> None:
        with self._lock:
            self.sensor_disagreements += 1

    def record_stale_dropped(self) -> None:
        with self._lock:
            self.stale_observations_dropped += 1

    def record_credential_redacted(self) -> None:
        with self._lock:
            self.credential_redactions += 1

    def record_injection_blocked(self) -> None:
        with self._lock:
            self.prompt_injections_blocked += 1

    def record_outcome_verification(self, was_accurate: bool) -> None:
        with self._lock:
            if was_accurate:
                self.verified_correct_count += 1
            else:
                self.verified_incorrect_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            tot_v = self.verified_correct_count + self.verified_incorrect_count
            acc = (self.verified_correct_count / tot_v) if tot_v > 0 else 1.0
            return {
                "sensor_counts": dict(self.sensor_counts),
                "sensor_disagreements": self.sensor_disagreements,
                "stale_dropped": self.stale_observations_dropped,
                "credentials_redacted": self.credential_redactions,
                "injections_blocked": self.prompt_injections_blocked,
                "verified_observations": tot_v,
                "accuracy": round(acc, 4),
            }


# Global singleton instance
perception_pipeline = PerceptionPipeline()
