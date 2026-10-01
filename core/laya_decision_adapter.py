"""
Laya Decision Adapter for System 1 Fast Decision Routing in MARK XLVIII / JARVIS.
Integrates the official NandhaKishorM/laya neural decision engine with typed LayaModelHandle,
real checkpoint loading (convaiinnovations/laya), continuous neural scoring, and deterministic simulator fallback.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionSource,
    DecisionType,
    ModelLifecycleState,
    create_decision_result,
)

logger = logging.getLogger(__name__)


@dataclass
class LayaModelHandle:
    checkpoint: str
    backend: str  # "real_laya" or "laya_simulator"
    model: Any
    loaded_at: float = field(default_factory=time.time)
    device: str = "cpu"
    is_real: bool = False
    health: str = "HEALTHY"
    state: ModelLifecycleState = ModelLifecycleState.COLD
    warmup_latency_ms: float = 0.0
    last_inference_at: float = 0.0
    inference_count: int = 0


_OPTION_KEYWORDS: Dict[str, List[str]] = {
    "coder": ["code", "coding", "python", "javascript", "function", "bug", "syntax", "refactor"],
    "researcher": ["research", "search", "docs", "documentation", "lookup", "api", "find"],
    "verifier": ["verify", "verification", "check", "test", "validate", "assert"],
    "vision": ["vision", "see", "screen", "ui", "image", "window"],
    "scheduler": ["schedule", "remind", "later", "tomorrow", "calendar", "time"],
    "memory": ["memory", "remember", "recall", "history", "prior"],
    "planner": ["plan", "planning", "decompose", "strategy", "roadmap", "goal"],
    "executor": ["execute", "run", "start", "launch", "apply"],
    "browser": ["browse", "web", "url", "http", "chrome"],
    "general_reasoner": ["reason", "think", "analyze", "general"],
    "direct_answer": ["direct", "answer directly", "simple"],
    "high_risk": ["delete", "drop", "rm -rf", "destroy", "format", "wipe"],
    "billing_refund": ["refund", "payment", "charge", "duplicate", "invoice", "money"],
    "technical_support": ["bug", "error", "crash", "outage", "stack trace"],
    "general_inquiry": ["info", "question", "help", "about"],
}


class LayaDecisionAdapter:
    """
    Adapter interfacing with the official Laya decision engine or its local runtime simulator.
    Manages complete model lifecycle: COLD, WARMING, READY, DEGRADED, UNHEALTHY, UNLOADING.
    """

    def __init__(
        self,
        default_model: str = "laya",
        multilingual_model: str = "laya-multilingual",
        typed_model: str = "laya-typed-decisions",
        device: str = "cpu",
        max_loaded_models: int = 3,
        timeout_ms: float = 250.0,
    ):
        self.default_model = default_model
        self.multilingual_model = multilingual_model
        self.typed_model = typed_model
        self.device = device
        self.max_loaded_models = max_loaded_models
        self.timeout_ms = timeout_ms

        self._loaded_models: Dict[str, LayaModelHandle] = {}
        self._laya_installed: bool = False
        self._check_laya_installation()

    def _check_laya_installation(self) -> None:
        try:
            import importlib.util

            self._laya_installed = importlib.util.find_spec("laya") is not None
        except Exception:
            self._laya_installed = False

    def is_available(self) -> bool:
        return True

    def get_model_state(self, checkpoint_name: Optional[str] = None) -> ModelLifecycleState:
        """Returns the current lifecycle state of the requested or default checkpoint."""
        target = checkpoint_name or self.default_model
        handle = self._loaded_models.get(target)
        if not handle:
            return ModelLifecycleState.COLD
        return handle.state

    def load_model(self, checkpoint_name: str) -> bool:
        """
        Loads the specified Laya model checkpoint into memory while respecting max_loaded_models.
        """
        t0 = time.perf_counter()
        if checkpoint_name in self._loaded_models:
            handle = self._loaded_models[checkpoint_name]
            if handle.state == ModelLifecycleState.COLD:
                handle.state = ModelLifecycleState.READY
            return True

        # Evict least recently used if exceeding cache
        if len(self._loaded_models) >= self.max_loaded_models:
            oldest = next(iter(self._loaded_models.keys()))
            self.unload_model(oldest)

        if self._laya_installed:
            try:
                import laya  # type: ignore

                model_id = "convaiinnovations/laya"
                subfolder = None
                if "multilingual" in checkpoint_name:
                    subfolder = "multilingual"
                elif "typed" in checkpoint_name:
                    subfolder = "typed-decisions"

                agent = laya.load(model_id, device=self.device, subfolder=subfolder)
                dt = (time.perf_counter() - t0) * 1000
                logger.info("Loaded real Laya checkpoint '%s' in %.2f ms", checkpoint_name, dt)

                handle = LayaModelHandle(
                    checkpoint=checkpoint_name,
                    backend="real_laya",
                    model=agent,
                    loaded_at=time.time(),
                    device=self.device,
                    is_real=True,
                    health="REAL_MODEL_HEALTHY",
                    state=ModelLifecycleState.READY,
                )
                self._loaded_models[checkpoint_name] = handle
                return True
            except Exception as e:
                logger.warning("Failed to load real Laya model '%s': %s. Falling back to simulator.", checkpoint_name, e)
                handle = LayaModelHandle(
                    checkpoint=checkpoint_name,
                    backend="laya_simulator",
                    model=None,
                    loaded_at=time.time(),
                    device=self.device,
                    is_real=False,
                    health="SIMULATOR_FALLBACK",
                    state=ModelLifecycleState.READY,
                )
                self._loaded_models[checkpoint_name] = handle
                return True
        else:
            handle = LayaModelHandle(
                checkpoint=checkpoint_name,
                backend="laya_simulator",
                model=None,
                loaded_at=time.time(),
                device=self.device,
                is_real=False,
                health="SIMULATOR_FALLBACK",
                state=ModelLifecycleState.READY,
            )
            self._loaded_models[checkpoint_name] = handle
            return True

    def warmup(self, checkpoint_name: Optional[str] = None) -> float:
        """
        Pre-warms the model through PyTorch JIT execution so subsequent inferences are warm (<150ms).
        Returns the warmup duration in milliseconds.
        """
        target = checkpoint_name or self.default_model
        t0 = time.perf_counter()
        
        # Mark WARMING state
        if target in self._loaded_models:
            self._loaded_models[target].state = ModelLifecycleState.WARMING
        
        self.load_model(target)
        handle = self._loaded_models.get(target)
        if handle and handle.is_real and handle.model is not None:
            try:
                handle.state = ModelLifecycleState.WARMING
                dummy_state = {"request": "system initialization status check"}
                dummy_question = {
                    "intent": {
                        "type": "choice",
                        "instructions": "Classify the intent.",
                        "criteria": {"status": "status inquiry", "other": "other request"},
                    }
                }
                handle.model.predict(dummy_state, dummy_question)
            except Exception as e:
                logger.warning("Laya warmup inference warning: %s", e)
        
        dt = (time.perf_counter() - t0) * 1000
        if handle:
            handle.warmup_latency_ms = dt
            handle.state = ModelLifecycleState.READY
        return dt

    def unload_model(self, checkpoint_name: str) -> bool:
        """
        Safely unloads a checkpoint from memory and performs garbage collection.
        """
        if checkpoint_name in self._loaded_models:
            handle = self._loaded_models[checkpoint_name]
            handle.state = ModelLifecycleState.UNLOADING
            handle.model = None
            del self._loaded_models[checkpoint_name]
            try:
                import gc
                gc.collect()
            except Exception:
                pass
            return True
        return False

    def unload_all(self) -> None:
        """Unloads all active model checkpoints."""
        checkpoints = list(self._loaded_models.keys())
        for cp in checkpoints:
            self.unload_model(cp)

    def get_lifecycle_metrics(self) -> Dict[str, Any]:
        """Provides full observability over loaded models, states, and inference counters."""
        metrics: Dict[str, Any] = {}
        for cp, handle in self._loaded_models.items():
            metrics[cp] = {
                "checkpoint": handle.checkpoint,
                "backend": handle.backend,
                "is_real": handle.is_real,
                "state": handle.state.value if hasattr(handle.state, "value") else str(handle.state),
                "health": handle.health,
                "warmup_latency_ms": round(handle.warmup_latency_ms, 2),
                "inference_count": handle.inference_count,
                "last_inference_at": handle.last_inference_at,
                "device": handle.device,
            }
        return metrics

    def select_checkpoint(self, language: str = "en", decision_type: DecisionType = DecisionType.CHOICE) -> str:
        """
        Selects the most suitable checkpoint based on language and task type.
        """
        if language != "en" and language != "auto":
            return self.multilingual_model
        if decision_type in [DecisionType.SCORE, DecisionType.NOUL]:
            return self.typed_model
        return self.default_model

    def decide_choice(
        self,
        context: str,
        options: List[str],
        category: DecisionCategory = DecisionCategory.INTENT,
        language: str = "en",
        checkpoint: Optional[str] = None,
        trace_id: Optional[str] = None,
        force_simulator: bool = False,
    ) -> DecisionResult:
        """
        Executes a typed choice decision among candidate options using real Laya or simulator fallback.
        """
        t0 = time.perf_counter()
        target_model = checkpoint or self.select_checkpoint(language, DecisionType.CHOICE)
        try:
            self.load_model(target_model)
        except Exception as e:
            logger.warning("Failed to load model '%s': %s. Falling back to simulator.", target_model, e)
        handle = self._loaded_models.get(target_model)

        if not options:
            dt = (time.perf_counter() - t0) * 1000
            res, _ = create_decision_result(
                decision_type=DecisionType.CHOICE,
                category=category,
                context=context,
                selected_option=None,
                confidence=0.0,
                abstained=True,
                model_or_checkpoint=target_model,
                language=language,
                latency_ms=dt,
                reason_code="EMPTY_OPTIONS",
                source=DecisionSource.LAYA_SIMULATOR,
                trace_id=trace_id,
            )
            return res  # type: ignore

        # 1. Real Laya Neural Execution Path
        if not force_simulator and handle and handle.is_real and handle.model is not None:
            try:
                t_inf_start = time.perf_counter()
                state = {"request": context}
                questions = {
                    category.value: {
                        "type": "choice",
                        "instructions": f"Classify the {category.value} for the request.",
                        "criteria": {opt: opt.replace("_", " ") for opt in options},
                    }
                }
                preds = handle.model.predict(state, questions)
                inf_latency_ms = (time.perf_counter() - t_inf_start) * 1000

                ans = preds.get("answers", {}).get(category.value, {})
                selected = ans.get("choice", options[0])
                confidence = float(ans.get("confidence", 0.85))
                alternatives = {k: float(v) for k, v in ans.get("probabilities", {}).items()}

                if handle:
                    handle.last_inference_at = time.time()
                    handle.inference_count += 1
                    handle.state = ModelLifecycleState.READY

                res, _ = create_decision_result(
                    decision_type=DecisionType.CHOICE,
                    category=category,
                    context=context,
                    selected_option=selected,
                    confidence=confidence,
                    abstained=False,
                    model_or_checkpoint=target_model,
                    language=language,
                    latency_ms=inf_latency_ms,
                    evidence=[f"Real Laya neural forward pass selected '{selected}' (p={round(confidence, 4)})."],
                    alternatives=alternatives,
                    reason_code="REAL_LAYA_CHOICE_EVALUATED",
                    source=DecisionSource.REAL_LAYA,
                    trace_id=trace_id,
                    metadata={
                        "is_real": True,
                        "backend": "real_laya",
                        "model_checkpoint": target_model,
                        "lifecycle_state": handle.state.value if handle else "READY",
                        "inference_count": handle.inference_count if handle else 1,
                    },
                )
                return res  # type: ignore
            except Exception as e:
                logger.warning("Real Laya choice inference exception: %s. Falling back to simulator.", e)

        # 2. Deterministic Simulator Fallback Path
        if handle:
            handle.last_inference_at = time.time()
            handle.inference_count += 1

        ctx_lower = context.lower()
        selected: str = options[0]
        confidence: float = 0.88
        alternatives: Dict[str, float] = {}

        matched = False
        for opt in options:
            opt_lower = opt.lower()
            keywords = _OPTION_KEYWORDS.get(opt_lower, [opt_lower]) + opt_lower.split("_")
            if any(kw in ctx_lower for kw in keywords):
                selected = opt
                confidence = 0.92
                matched = True
                break

        if not matched and len(options) > 1:
            confidence = 0.70
            selected = options[0]

        remaining_prob = max(0.0, 1.0 - confidence)
        split_prob = remaining_prob / max(1, len(options) - 1)
        for opt in options:
            alternatives[opt] = confidence if opt == selected else split_prob

        dt = (time.perf_counter() - t0) * 1000
        res, _ = create_decision_result(
            decision_type=DecisionType.CHOICE,
            category=category,
            context=context,
            selected_option=selected,
            confidence=confidence,
            abstained=False,
            model_or_checkpoint=target_model,
            language=language,
            latency_ms=dt,
            evidence=[f"Simulator fallback option '{selected}' evaluated."],
            alternatives=alternatives,
            reason_code="LAYA_SIMULATOR_CHOICE_EVALUATED",
            source=DecisionSource.LAYA_SIMULATOR,
            trace_id=trace_id,
            metadata={
                "is_real": False,
                "backend": "laya_simulator",
                "model_checkpoint": target_model,
                "lifecycle_state": handle.state.value if handle else "READY",
            },
        )
        return res  # type: ignore

    def decide_score(
        self,
        context: str,
        category: DecisionCategory = DecisionCategory.URGENCY,
        language: str = "en",
        checkpoint: Optional[str] = None,
        trace_id: Optional[str] = None,
        force_simulator: bool = False,
    ) -> DecisionResult:
        """
        Executes a continuous score decision (0.0 to 1.0) using real Laya or simulator fallback.
        """
        t0 = time.perf_counter()
        target_model = checkpoint or self.select_checkpoint(language, DecisionType.SCORE)
        try:
            self.load_model(target_model)
        except Exception as e:
            logger.warning("Failed to load model '%s': %s. Falling back to simulator.", target_model, e)
        handle = self._loaded_models.get(target_model)

        # 1. Real Laya Neural Execution Path
        if not force_simulator and handle and handle.is_real and handle.model is not None:
            try:
                t_inf_start = time.perf_counter()
                state = {"request": context}
                criteria_list = [f"none/trivial: negligible {category.value}", f"low: minor {category.value}", f"moderate: standard {category.value}", f"critical: immediate {category.value}"]
                questions = {
                    category.value: {
                        "type": "score",
                        "instructions": f"Rate the {category.value} on a scale from 0.0 to 1.0.",
                        "criteria": criteria_list,
                    }
                }
                preds = handle.model.predict(state, questions)
                inf_latency_ms = (time.perf_counter() - t_inf_start) * 1000

                ans = preds.get("answers", {}).get(category.value, {})
                raw_score = float(ans.get("score", 0.50))
                if len(criteria_list) > 1:
                    score = raw_score / (len(criteria_list) - 1.0)
                else:
                    score = raw_score
                score = min(1.0, max(0.0, score))
                confidence = float(ans.get("confidence", 0.90))

                if handle:
                    handle.last_inference_at = time.time()
                    handle.inference_count += 1
                    handle.state = ModelLifecycleState.READY

                res, _ = create_decision_result(
                    decision_type=DecisionType.SCORE,
                    category=category,
                    context=context,
                    score=score,
                    confidence=confidence,
                    abstained=False,
                    model_or_checkpoint=target_model,
                    language=language,
                    latency_ms=inf_latency_ms,
                    evidence=[f"Real Laya neural score: {score}"],
                    reason_code="REAL_LAYA_SCORE_EVALUATED",
                    source=DecisionSource.REAL_LAYA,
                    trace_id=trace_id,
                    metadata={
                        "is_real": True,
                        "backend": "real_laya",
                        "model_checkpoint": target_model,
                        "lifecycle_state": handle.state.value if handle else "READY",
                        "inference_count": handle.inference_count if handle else 1,
                    },
                )
                return res  # type: ignore
            except Exception as e:
                logger.warning("Real Laya score inference exception: %s. Falling back to simulator.", e)

        # 2. Simulator Fallback Path
        if handle:
            handle.last_inference_at = time.time()
            handle.inference_count += 1

        ctx_lower = context.lower()
        score = 0.50
        if any(w in ctx_lower for w in ["critical", "emergency", "immediately", "urgent", "deadline", "fatal"]):
            score = 0.95
        elif any(w in ctx_lower for w in ["soon", "today", "high", "important"]):
            score = 0.75
        elif any(w in ctx_lower for w in ["later", "low", "optional", "someday"]):
            score = 0.20

        confidence = 0.90
        dt = (time.perf_counter() - t0) * 1000
        res, _ = create_decision_result(
            decision_type=DecisionType.SCORE,
            category=category,
            context=context,
            score=score,
            confidence=confidence,
            abstained=False,
            model_or_checkpoint=target_model,
            language=language,
            latency_ms=dt,
            evidence=[f"Simulator score: {score}"],
            reason_code="LAYA_SIMULATOR_SCORE_EVALUATED",
            source=DecisionSource.LAYA_SIMULATOR,
            trace_id=trace_id,
            metadata={
                "is_real": False,
                "backend": "laya_simulator",
                "model_checkpoint": target_model,
                "lifecycle_state": handle.state.value if handle else "READY",
            },
        )
        return res  # type: ignore

    def decide_noul(
        self,
        context: str,
        category: DecisionCategory = DecisionCategory.INTENT,
        language: str = "en",
        checkpoint: Optional[str] = None,
        trace_id: Optional[str] = None,
        force_simulator: bool = False,
    ) -> DecisionResult:
        """
        Executes a structured noul decision using real Laya or simulator fallback.
        """
        t0 = time.perf_counter()
        target_model = checkpoint or self.select_checkpoint(language, DecisionType.NOUL)
        try:
            self.load_model(target_model)
        except Exception as e:
            logger.warning("Failed to load model '%s': %s. Falling back to simulator.", target_model, e)
        handle = self._loaded_models.get(target_model)

        # 1. Real Laya Neural Execution Path
        if not force_simulator and handle and handle.is_real and handle.model is not None:
            try:
                t_inf_start = time.perf_counter()
                state = {"request": context}
                questions = {
                    category.value: {
                        "type": "noul",
                        "instructions": f"Does the request require {category.value}?",
                    }
                }
                preds = handle.model.predict(state, questions)
                inf_latency_ms = (time.perf_counter() - t_inf_start) * 1000

                ans = preds.get("answers", {}).get(category.value, {})
                decision_val = ans.get("action", {}).get("act", True)
                confidence = float(ans.get("confidence", 0.85))

                if handle:
                    handle.last_inference_at = time.time()
                    handle.inference_count += 1
                    handle.state = ModelLifecycleState.READY

                res, _ = create_decision_result(
                    decision_type=DecisionType.NOUL,
                    category=category,
                    context=context,
                    selected_option=str(decision_val),
                    score=1.0 if decision_val else 0.0,
                    confidence=confidence,
                    abstained=False,
                    model_or_checkpoint=target_model,
                    language=language,
                    latency_ms=inf_latency_ms,
                    evidence=[f"Real Laya noul output: {decision_val}"],
                    reason_code="REAL_LAYA_NOUL_EVALUATED",
                    source=DecisionSource.REAL_LAYA,
                    trace_id=trace_id,
                    metadata={
                        "is_real": True,
                        "backend": "real_laya",
                        "model_checkpoint": target_model,
                        "lifecycle_state": handle.state.value if handle else "READY",
                        "inference_count": handle.inference_count if handle else 1,
                    },
                )
                return res  # type: ignore
            except Exception as e:
                logger.warning("Real Laya noul inference exception: %s. Falling back to simulator.", e)

        # 2. Simulator Fallback Path
        if handle:
            handle.last_inference_at = time.time()
            handle.inference_count += 1

        dt = (time.perf_counter() - t0) * 1000
        res, _ = create_decision_result(
            decision_type=DecisionType.NOUL,
            category=category,
            context=context,
            selected_option="structured_taxonomy",
            score=0.85,
            confidence=0.85,
            abstained=False,
            model_or_checkpoint=target_model,
            language=language,
            latency_ms=dt,
            evidence=["Simulator noul matched."],
            reason_code="LAYA_SIMULATOR_NOUL_EVALUATED",
            source=DecisionSource.LAYA_SIMULATOR,
            trace_id=trace_id,
            metadata={
                "is_real": False,
                "backend": "laya_simulator",
                "model_checkpoint": target_model,
                "lifecycle_state": handle.state.value if handle else "READY",
            },
        )
        return res  # type: ignore


# Global singleton instance
laya_decision_adapter = LayaDecisionAdapter()
