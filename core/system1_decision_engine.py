"""
System 1 Decision Engine for MARK XLVIII / JARVIS.
Integrates Laya fast typed decisions with confidence gating, health monitoring,
policy routing, deterministic fallback, continuous outcome tracking, and calibration governance.
Enforces rule: System 1 produces a decision signal, NOT execution authority.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.decision_confidence_gate import decision_confidence_gate
from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionType,
)
from core.decision_fallback_engine import decision_fallback_engine
from core.decision_outcome import (
    DecisionOutcomeRecord,
    OutcomeQuality,
    create_decision_outcome_record,
    decision_outcome_store,
)
from core.decision_policy_router import RoutingMode, decision_policy_router
from core.decision_question_builder import decision_question_builder
from core.laya_decision_adapter import laya_decision_adapter
from core.laya_health_monitor import HealthState, laya_health_monitor


class System1DecisionEngine:
    """
    Central coordinator for System 1 fast decision processing and calibration lifecycle.
    """

    def __init__(self):
        self.enabled: bool = True

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def decide(
        self,
        context: str,
        category: DecisionCategory = DecisionCategory.INTENT,
        options: Optional[List[str]] = None,
        language: str = "en",
        trace_id: Optional[str] = None,
    ) -> DecisionResult:
        """
        Executes a typed decision through System 1 with confidence gating, policy versioning,
        and outcome store registration.
        """
        tid = trace_id or f"tr_{uuid.uuid4().hex[:8]}"
        active_policy_ver = decision_policy_router.policy_version

        # 1. If System 1 is disabled or Laya is unhealthy, route to fallback immediately
        if not self.enabled:
            laya_health_monitor.record_fallback()
            fb_res = decision_fallback_engine.resolve_fallback(
                category=category,
                context=context,
                options=options,
                reason="SYSTEM1_DISABLED",
                trace_id=tid,
            )
            fb_res.metadata["policy_version"] = active_policy_ver
            self._register_initial_outcome(fb_res, fallback_used=True)
            return fb_res

        if laya_health_monitor.metrics.health_state == HealthState.UNHEALTHY:
            laya_health_monitor.record_fallback()
            fb_res = decision_fallback_engine.resolve_fallback(
                category=category,
                context=context,
                options=options,
                reason="HEALTH_UNHEALTHY",
                trace_id=tid,
            )
            fb_res.metadata["policy_version"] = active_policy_ver
            self._register_initial_outcome(fb_res, fallback_used=True)
            return fb_res

        # 2. Build typed question
        dec_type, question_text, candidate_opts = decision_question_builder.build_question(
            category=category,
            context=context,
            custom_options=options,
        )

        # 3. Execute decision via Laya Adapter
        try:
            if dec_type == DecisionType.CHOICE:
                raw_decision = laya_decision_adapter.decide_choice(
                    context=context,
                    options=candidate_opts,
                    category=category,
                    language=language,
                    trace_id=tid,
                )
            elif dec_type == DecisionType.SCORE:
                raw_decision = laya_decision_adapter.decide_score(
                    context=context,
                    category=category,
                    language=language,
                    trace_id=tid,
                )
            else:
                raw_decision = laya_decision_adapter.decide_noul(
                    context=context,
                    category=category,
                    language=language,
                    trace_id=tid,
                )

            laya_health_monitor.record_success(raw_decision.latency_ms)

        except Exception as e:
            laya_health_monitor.record_failure()
            laya_health_monitor.record_fallback()
            fb_res = decision_fallback_engine.resolve_fallback(
                category=category,
                context=context,
                options=candidate_opts,
                reason=f"INFERENCE_EXCEPTION_{type(e).__name__}",
                trace_id=tid,
            )
            fb_res.metadata["policy_version"] = active_policy_ver
            self._register_initial_outcome(fb_res, fallback_used=True)
            return fb_res

        # 4. Stamp active policy version
        raw_decision.metadata["policy_version"] = active_policy_ver

        # 5. Evaluate through confidence gate (incorporates route-specific thresholds & drift penalty)
        passed_gate, rationale = decision_confidence_gate.evaluate_decision(raw_decision)
        if not passed_gate:
            raw_decision.abstained = True
            laya_health_monitor.record_fallback()

        # 6. Register decision in outcome store
        self._register_initial_outcome(raw_decision, fallback_used=False)

        return raw_decision

    def _register_initial_outcome(
        self,
        decision: DecisionResult,
        fallback_used: bool,
    ) -> None:
        try:
            record = create_decision_outcome_record(
                decision_result=decision,
                system1_used=not fallback_used and not decision.abstained,
                system2_used=fallback_used or decision.abstained,
                fallback_used=fallback_used,
                policy_version=decision.metadata.get("policy_version", "system1-policy-v1"),
            )
            decision_outcome_store.add_record(record)
        except Exception:
            pass

    def record_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        outcome_quality: OutcomeQuality,
        outcome_verified: bool = True,
        final_decision: Optional[str] = None,
        governance_result: Optional[str] = None,
    ) -> bool:
        """
        Updates the outcome record for a completed decision with verified ground truth.
        """
        res = decision_outcome_store.update_outcome(
            decision_id=decision_id,
            actual_outcome=actual_outcome,
            outcome_quality=outcome_quality,
            outcome_verified=outcome_verified,
            final_decision=final_decision,
            governance_result=governance_result,
        )

        # If verified correct decision provided, update disagreement tracking
        if final_decision:
            decision_policy_router.update_disagreement_outcome(
                decision_id=decision_id,
                actual_outcome=actual_outcome,
                verified_correct_choice=final_decision,
            )

        return res

    def get_calibration_status(self, category: Optional[DecisionCategory] = None) -> Dict[str, Any]:
        try:
            from core.decision_calibration_engine import decision_calibration_engine

            if category:
                report = decision_calibration_engine.calibrate_category(category)
            else:
                report = decision_calibration_engine.calibrate_global()
            return report.to_dict()
        except Exception as e:
            return {"error": str(e)}

    def get_drift_status(self, category: Optional[DecisionCategory] = None) -> Dict[str, Any]:
        try:
            from core.decision_drift_detector import decision_drift_detector

            assessment = decision_drift_detector.assess_route(category)
            return assessment.to_dict()
        except Exception as e:
            return {"error": str(e)}

    def rollback_policy(self, target_version: Optional[str] = None) -> Tuple[bool, str]:
        try:
            from core.decision_policy_proposal import decision_policy_manager

            return decision_policy_manager.rollback_policy(target_version)
        except Exception as e:
            return False, f"Rollback error: {e}"

    def arbitrate(
        self,
        context: str,
        category: DecisionCategory = DecisionCategory.INTENT,
        options: Optional[List[str]] = None,
        system2_option: Optional[str] = None,
        risk_level: str = "low",
        requires_research: bool = False,
        memory_conflict: bool = False,
        user_preference: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        from core.decision_arbitration import (
            ArbitrationContext,
            decision_arbitrator,
        )

        laya_dec = self.decide(context=context, category=category, options=options, trace_id=trace_id)
        ctx = ArbitrationContext(
            context_text=context,
            category=category,
            laya_decision=laya_dec,
            system2_option=system2_option,
            risk_level=risk_level,
            requires_research=requires_research,
            memory_conflict=memory_conflict,
            user_preference=user_preference,
        )
        return decision_arbitrator.arbitrate(ctx)

    def decide_grounded(
        self,
        query: str,
        category: DecisionCategory = DecisionCategory.INTENT,
        world_model_instance: Optional[Any] = None,
        language: str = "en",
        trace_id: Optional[str] = None,
    ) -> DecisionResult:
        """
        Executes a grounded decision using WorldModel evidence.
        Abstains to System 2 when facts are missing, stale, ambiguous, or novel.
        """
        wm = world_model_instance
        if wm is None:
            try:
                from core.world_model import world_model
                wm = world_model
            except Exception:
                wm = None

        tid = trace_id or f"tr_{uuid.uuid4().hex[:8]}"

        # If WorldModel is unavailable, fall back to standard ungrounded decide
        if wm is None:
            return self.decide(context=query, category=category, language=language, trace_id=tid)

        q_lower = query.lower()
        grounded_fact = None

        if "app" in q_lower or "using" in q_lower:
            grounded_fact = wm.get_fact("application", "active_application")
        elif "window" in q_lower or "file" in q_lower:
            grounded_fact = wm.get_fact("application", "focused_window_title")
        elif "server" in q_lower or "running" in q_lower or "port" in q_lower:
            grounded_fact = wm.get_fact("device", "listening_ports") or wm.get_fact("process", "listening_ports")
        elif "screen" in q_lower or "see" in q_lower:
            grounded_fact = wm.get_fact("screen", "error_snippets") or wm.get_fact("screen", "extracted_text")
        elif "build" in q_lower or "fail" in q_lower:
            try:
                from core.multimodal_fusion_engine import multimodal_fusion_engine
                fusion = multimodal_fusion_engine.fuse()
                if fusion.get("state") == "BUILD_FAILURE":
                    grounded_context = f"Build failure detected: {fusion.get('cause')} with evidence {fusion.get('evidence')}"
                    return self.decide(context=grounded_context, category=category, language=language, trace_id=tid)
            except Exception:
                pass

        # If fact is missing, ambiguous, or stale, abstain and escalate to System 2
        fresh_state = getattr(grounded_fact, "freshness", "")
        fresh_val = fresh_state.value if hasattr(fresh_state, "value") else str(fresh_state)
        if grounded_fact is None or getattr(grounded_fact, "is_ambiguous", False) or fresh_val not in ("FRESH", "AGING"):
            res = self.decide(context=query, category=category, language=language, trace_id=tid)
            res.abstained = True
            res.abstention_reason = "GROUNDED_FACT_MISSING_OR_STALE"
            return res

        enriched_context = f"{query} [Evidence: {grounded_fact.key}={grounded_fact.value} (conf={grounded_fact.confidence:.2f})]"
        res = self.decide(context=enriched_context, category=category, language=language, trace_id=tid)
        res.metadata["grounded_fact_key"] = grounded_fact.key
        res.metadata["grounded_fact_value"] = str(grounded_fact.value)
        return res

    def get_arbitration_status(self) -> Dict[str, Any]:
        try:
            from core.decision_arbitration import decision_arbitrator

            return decision_arbitrator.get_status()
        except Exception as e:
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "system1_enabled": self.enabled,
            "mode": decision_policy_router.mode.value,
            "policy_version": decision_policy_router.policy_version,
            "health": laya_health_monitor.get_status(),
            "telemetry": decision_policy_router.get_telemetry_summary(),
            "outcomes_summary": decision_outcome_store.get_summary(),
            "drift_assessment": self.get_drift_status(),
            "arbitration": self.get_arbitration_status(),
        }


# Global singleton instance
system1_decision_engine = System1DecisionEngine()
