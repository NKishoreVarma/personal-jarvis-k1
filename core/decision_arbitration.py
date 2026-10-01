"""
Decision Arbitration Engine for System 1 / System 2 Meta-Reasoning in MARK XLVIII / JARVIS.
Decides: "Which reasoning path should handle this decision?"
Evaluates multi-signal context: Novelty, Complexity, Evidence Quality, Risk,
Calibration, Drift, Temporal Pressure, Research Requirements, and Disagreements.
Enforces rule: Arbitration != Authorization. Safety authority and ActionContract remain absolute.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.decision_calibration_engine import decision_calibration_engine
from core.decision_confidence_gate import decision_confidence_gate
from core.decision_contract import (
    DecisionCategory,
    DecisionResult,
    DecisionType,
)
from core.decision_drift_detector import DriftState, decision_drift_detector
from core.decision_policy_proposal import decision_policy_manager

logger = logging.getLogger(__name__)


class DecisionEngine(str, Enum):
    SYSTEM1 = "SYSTEM1"
    SYSTEM2 = "SYSTEM2"
    HYBRID = "HYBRID"
    ABSTAIN = "ABSTAIN"
    HUMAN = "HUMAN"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    LOW_MARGIN = "LOW_MARGIN"
    LOW_ROUTE_RELIABILITY = "LOW_ROUTE_RELIABILITY"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    HIGH_RISK = "HIGH_RISK"
    UNKNOWN_RISK = "UNKNOWN_RISK"
    NOVEL_TASK = "NOVEL_TASK"
    HIGH_COMPLEXITY = "HIGH_COMPLEXITY"
    WEAK_EVIDENCE = "WEAK_EVIDENCE"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    MEMORY_CONFLICT = "MEMORY_CONFLICT"
    SYSTEM1_SYSTEM2_DISAGREEMENT = "SYSTEM1_SYSTEM2_DISAGREEMENT"
    EXECUTION_CONSEQUENCE = "EXECUTION_CONSEQUENCE"
    POLICY_RESTRICTION = "POLICY_RESTRICTION"
    NONE = "NONE"


class EvidenceQuality(str, Enum):
    VERIFIED = "VERIFIED"
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"


class TaskNovelty(str, Enum):
    FAMILIAR = "FAMILIAR"
    RELATED = "RELATED"
    NOVEL = "NOVEL"
    UNKNOWN = "UNKNOWN"


class TaskComplexity(str, Enum):
    SIMPLE = "SIMPLE"
    MODERATE = "MODERATE"
    COMPLEX = "COMPLEX"
    VERY_COMPLEX = "VERY_COMPLEX"


class DisagreementType(str, Enum):
    AGREEMENT = "AGREEMENT"
    DISAGREEMENT = "DISAGREEMENT"
    SYSTEM1_ONLY = "SYSTEM1_ONLY"
    SYSTEM2_ONLY = "SYSTEM2_ONLY"
    BOTH_UNCERTAIN = "BOTH_UNCERTAIN"


class TemporalPressure(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"


@dataclass
class ArbitrationContext:
    context_text: str
    category: DecisionCategory
    laya_decision: Optional[DecisionResult] = None
    system2_option: Optional[str] = None
    novelty: TaskNovelty = TaskNovelty.FAMILIAR
    complexity: TaskComplexity = TaskComplexity.SIMPLE
    evidence_quality: EvidenceQuality = EvidenceQuality.STRONG
    risk_level: str = "low"  # "low", "medium", "high", "destructive", "unknown"
    temporal_pressure: TemporalPressure = TemporalPressure.NONE
    requires_research: bool = False
    memory_conflict: bool = False
    user_preference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArbitrationResult:
    arbitration_id: str
    trace_id: str
    route: DecisionCategory
    selected_engine: DecisionEngine
    system1_confidence: float
    system1_reliability: float
    system1_abstained: bool
    system1_drift_state: str
    system2_required: bool
    system2_reason: EscalationReason
    disagreement: DisagreementType
    evidence_quality: EvidenceQuality
    novelty: TaskNovelty
    risk: str
    complexity: TaskComplexity
    temporal_pressure: TemporalPressure
    policy_version: str
    arbitration_confidence: float
    final_decision_option: Optional[str]
    explanations: List[str]
    latency_ms: float
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arbitration_id": self.arbitration_id,
            "trace_id": self.trace_id,
            "route": self.route.value if hasattr(self.route, "value") else str(self.route),
            "selected_engine": self.selected_engine.value,
            "system1_confidence": round(self.system1_confidence, 4),
            "system1_reliability": round(self.system1_reliability, 4),
            "system1_abstained": self.system1_abstained,
            "system1_drift_state": self.system1_drift_state,
            "system2_required": self.system2_required,
            "system2_reason": self.system2_reason.value,
            "disagreement": self.disagreement.value,
            "evidence_quality": self.evidence_quality.value,
            "novelty": self.novelty.value,
            "risk": self.risk,
            "complexity": self.complexity.value,
            "temporal_pressure": self.temporal_pressure.value,
            "policy_version": self.policy_version,
            "arbitration_confidence": round(self.arbitration_confidence, 4),
            "final_decision_option": self.final_decision_option,
            "explanations": self.explanations,
            "latency_ms": round(self.latency_ms, 3),
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ArbitrationPolicy:
    enabled: bool = True
    min_confidence: float = 0.75
    min_reliability: float = 0.70
    min_sample_size: int = 10
    allow_hybrid: bool = True
    allow_human: bool = True
    max_complexity_for_system1: TaskComplexity = TaskComplexity.SIMPLE
    allowed_risks_for_system1: List[str] = field(default_factory=lambda: ["low", "read_only"])


class ArbitrationTelemetryStore:
    """
    Stores and computes escalation quality metrics from historical arbitration outcomes.
    Enforces minimum sample protections before declaring escalation rates.
    """

    MIN_SAMPLES = 10

    def __init__(self, max_records: int = 5000):
        self.max_records = max_records
        self._records: List[ArbitrationResult] = []
        self._outcomes: Dict[str, Dict[str, Any]] = {}

    def record_arbitration(self, res: ArbitrationResult) -> None:
        if len(self._records) >= self.max_records:
            self._records.pop(0)
        self._records.append(res)

    def record_outcome(
        self,
        arbitration_id: str,
        was_correct: bool,
        optimal_engine: DecisionEngine,
        actual_outcome: str,
    ) -> bool:
        self._outcomes[arbitration_id] = {
            "was_correct": was_correct,
            "optimal_engine": optimal_engine,
            "actual_outcome": actual_outcome,
            "recorded_at": time.time(),
        }
        return True

    def get_escalation_quality(self) -> Dict[str, Any]:
        verified_count = len(self._outcomes)
        if verified_count < self.MIN_SAMPLES:
            return {
                "status": "INSUFFICIENT_VERIFIED_DATA",
                "verified_samples": verified_count,
                "min_required": self.MIN_SAMPLES,
                "message": f"Insufficient verified arbitration samples ({verified_count}/{self.MIN_SAMPLES}) for escalation claim.",
            }

        necessary_count = 0
        unnecessary_count = 0
        missed_count = 0

        sys1_success = 0
        sys1_total = 0
        sys2_success = 0
        sys2_total = 0
        hybrid_success = 0
        hybrid_total = 0

        for r in self._records:
            out = self._outcomes.get(r.arbitration_id)
            if not out:
                continue

            optimal = out["optimal_engine"]
            was_correct = out["was_correct"]

            if r.selected_engine == DecisionEngine.SYSTEM1:
                sys1_total += 1
                if was_correct:
                    sys1_success += 1
                if optimal in [DecisionEngine.SYSTEM2, DecisionEngine.HUMAN]:
                    missed_count += 1

            elif r.selected_engine == DecisionEngine.SYSTEM2:
                sys2_total += 1
                if was_correct:
                    sys2_success += 1
                if optimal == DecisionEngine.SYSTEM1:
                    unnecessary_count += 1
                else:
                    necessary_count += 1

            elif r.selected_engine == DecisionEngine.HYBRID:
                hybrid_total += 1
                if was_correct:
                    hybrid_success += 1

        total_escalated = sys2_total
        return {
            "status": "SUFFICIENT_VERIFIED_DATA",
            "verified_samples": verified_count,
            "necessary_escalation_rate": (
                round(necessary_count / total_escalated, 4) if total_escalated > 0 else 0.0
            ),
            "unnecessary_escalation_rate": (
                round(unnecessary_count / total_escalated, 4) if total_escalated > 0 else 0.0
            ),
            "missed_escalation_rate": (
                round(missed_count / sys1_total, 4) if sys1_total > 0 else 0.0
            ),
            "system1_success_rate": (
                round(sys1_success / sys1_total, 4) if sys1_total > 0 else None
            ),
            "system2_success_rate": (
                round(sys2_success / sys2_total, 4) if sys2_total > 0 else None
            ),
            "hybrid_success_rate": (
                round(hybrid_success / hybrid_total, 4) if hybrid_total > 0 else None
            ),
        }

    def clear(self) -> None:
        self._records.clear()
        self._outcomes.clear()


class DecisionArbitrator:
    """
    Central meta-reasoning engine arbitrating between System 1, System 2, Hybrid, and Human.
    Evaluates multi-signal context without allowing speed to compromise safety or correctness.
    """

    def __init__(self, policy: Optional[ArbitrationPolicy] = None):
        self.policy = policy or ArbitrationPolicy()
        self.telemetry_store = ArbitrationTelemetryStore()

    def arbitrate(self, ctx: ArbitrationContext, trace_id: Optional[str] = None) -> ArbitrationResult:
        t0 = time.perf_counter()
        arb_id = f"arb_{uuid.uuid4().hex[:8]}"
        trace_id = trace_id or (ctx.laya_decision.trace_id if ctx.laya_decision else f"tr_{uuid.uuid4().hex[:8]}")
        route = ctx.category
        policy_ver = decision_policy_manager.current_version

        explanations: List[str] = []
        selected_engine = DecisionEngine.SYSTEM1
        system2_required = False
        system2_reason = EscalationReason.NONE
        arbitration_confidence = 0.90
        final_option: Optional[str] = None

        # 1. System 1 Baseline Metrics
        s1_conf = ctx.laya_decision.confidence if ctx.laya_decision else 0.0
        s1_abstained = ctx.laya_decision.abstained if ctx.laya_decision else True
        s1_choice = ctx.laya_decision.selected_option if ctx.laya_decision else None

        # 2. Calibration & Route Trust from Phase 12.29
        cal_report = decision_calibration_engine.calibrate_category(route)
        s1_reliability = cal_report.route_trust_score
        is_cal_sufficient = cal_report.is_sufficient

        # 3. Concept Drift Assessment
        drift_assessment = decision_drift_detector.assess_route(route)
        drift_state = drift_assessment.state

        # 4. Disagreement Classification
        disagreement_type = DisagreementType.SYSTEM1_ONLY
        if ctx.laya_decision and ctx.system2_option:
            if s1_choice == ctx.system2_option:
                disagreement_type = DisagreementType.AGREEMENT
            else:
                disagreement_type = DisagreementType.DISAGREEMENT
        elif not ctx.laya_decision and ctx.system2_option:
            disagreement_type = DisagreementType.SYSTEM2_ONLY
        elif not ctx.laya_decision and not ctx.system2_option:
            disagreement_type = DisagreementType.BOTH_UNCERTAIN

        # =====================================================================
        # META-REASONING EVALUATION PIPELINE
        # =====================================================================

        # Rule 1: Human Confirmation / Irreversible Execution Consequence
        if ctx.user_preference == "require_confirmation" or ctx.risk_level == "destructive":
            selected_engine = DecisionEngine.HUMAN
            system2_required = True
            system2_reason = EscalationReason.EXECUTION_CONSEQUENCE
            explanations.append("Human escalation selected due to user preference or destructive execution consequence.")
            arbitration_confidence = 0.99
            final_option = ctx.system2_option or s1_choice

        # Rule 2: High or Unknown Risk (Absolute Invariant)
        elif ctx.risk_level in ["high", "destructive"]:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.HIGH_RISK
            explanations.append(f"High risk operation ('{ctx.risk_level}') mandates System 2 reasoning and governance.")
            final_option = ctx.system2_option or s1_choice

        elif ctx.risk_level == "unknown":
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.UNKNOWN_RISK
            explanations.append("Unknown risk detected; escalating to System 2.")
            final_option = ctx.system2_option or s1_choice

        # Rule 3: External Research Required (Phase 12.27)
        elif ctx.requires_research:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.RESEARCH_REQUIRED
            explanations.append("External research required; System 1 cannot synthesize unverified external facts.")
            final_option = ctx.system2_option

        # Rule 4: Memory Contradiction / Conflict (Observation > Memory > System 1)
        elif ctx.memory_conflict:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.MEMORY_CONFLICT
            explanations.append("Memory contradiction detected; System 1 lacks authority over conflicting evidence.")
            final_option = ctx.system2_option

        # Rule 5: Task Novelty
        elif ctx.novelty in [TaskNovelty.NOVEL, TaskNovelty.UNKNOWN]:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.NOVEL_TASK
            explanations.append(f"Task novelty is {ctx.novelty.value}; unfamiliar context requires System 2 deep reasoning.")
            final_option = ctx.system2_option or s1_choice

        # Rule 6: High Task Complexity
        elif ctx.complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.HIGH_COMPLEXITY
            explanations.append(f"Task complexity is {ctx.complexity.value}; multi-step reasoning mandates System 2.")
            final_option = ctx.system2_option

        # Rule 7: Weak or Unknown Evidence
        elif ctx.evidence_quality in [EvidenceQuality.WEAK, EvidenceQuality.UNKNOWN]:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.WEAK_EVIDENCE
            explanations.append("Evidence quality is weak or unknown; System 2 verification required.")
            final_option = ctx.system2_option

        # Rule 8: Concept Drift / Route Degraded (Phase 12.29)
        elif drift_state in [DriftState.DEGRADED, DriftState.DRIFT_DETECTED] or drift_assessment.force_system2:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.DRIFT_DETECTED
            explanations.append(f"Concept drift active ({drift_state.value}) on route {route.value}; conservative degradation forces System 2.")
            final_option = ctx.system2_option

        # Rule 9: Insufficient Calibration Samples
        elif not is_cal_sufficient or cal_report.verified_sample_count < self.policy.min_sample_size:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.INSUFFICIENT_SAMPLES
            explanations.append(f"Insufficient verified calibration samples ({cal_report.verified_sample_count}/{self.policy.min_sample_size}); defaulting to System 2.")
            final_option = ctx.system2_option

        # Rule 10: Low Route Reliability
        elif s1_reliability < self.policy.min_reliability:
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.LOW_ROUTE_RELIABILITY
            explanations.append(f"Calibrated route reliability ({s1_reliability:.2f}) is below minimum threshold ({self.policy.min_reliability:.2f}).")
            final_option = ctx.system2_option

        # Rule 11: System 1 Abstention or Low Confidence
        elif s1_abstained or (ctx.laya_decision and s1_conf < decision_confidence_gate.get_effective_threshold(route)):
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.LOW_CONFIDENCE
            explanations.append(f"System 1 abstained or confidence ({s1_conf:.2f}) is below effective threshold.")
            final_option = ctx.system2_option

        # Rule 12: System 1 / System 2 Disagreement Arbitration
        elif disagreement_type == DisagreementType.DISAGREEMENT:
            system2_required = True
            system2_reason = EscalationReason.SYSTEM1_SYSTEM2_DISAGREEMENT
            # Arbitrate based on evidence quality and route trust score
            if ctx.evidence_quality == EvidenceQuality.VERIFIED and s1_reliability >= 0.85 and ctx.risk_level in ["low", "read_only"]:
                selected_engine = DecisionEngine.SYSTEM1
                final_option = s1_choice
                explanations.append("Disagreement arbitrated in favor of System 1: Verified evidence and high route reliability.")
            else:
                selected_engine = DecisionEngine.SYSTEM2
                final_option = ctx.system2_option
                explanations.append("Disagreement arbitrated in favor of System 2: Risk or evidence uncertainty requires deliberate reasoning.")

        # Rule 13: Hybrid Mode Eligibility (Moderate complexity + High confidence + Strong evidence)
        elif (
            self.policy.allow_hybrid
            and ctx.complexity == TaskComplexity.MODERATE
            and s1_conf >= 0.80
            and ctx.evidence_quality in [EvidenceQuality.STRONG, EvidenceQuality.VERIFIED]
            and ctx.risk_level in ["low", "medium"]
        ):
            selected_engine = DecisionEngine.HYBRID
            system2_required = True  # Lightweight System 2 validation
            system2_reason = EscalationReason.NONE
            explanations.append("Hybrid mode selected: System 1 provides candidate ranking; lightweight System 2 validation confirms.")
            final_option = s1_choice or ctx.system2_option

        # Rule 14: System 1 Fast Path (All eligibility checks passed)
        elif (
            s1_choice is not None
            and not s1_abstained
            and ctx.complexity == TaskComplexity.SIMPLE
            and ctx.risk_level in self.policy.allowed_risks_for_system1
            and ctx.novelty == TaskNovelty.FAMILIAR
        ):
            selected_engine = DecisionEngine.SYSTEM1
            system2_required = False
            system2_reason = EscalationReason.NONE
            explanations.append("System 1 fast path eligible: High confidence, familiar task, simple complexity, and low risk.")
            final_option = s1_choice

        else:
            # Safe Fallback to System 2
            selected_engine = DecisionEngine.SYSTEM2
            system2_required = True
            system2_reason = EscalationReason.POLICY_RESTRICTION
            explanations.append("Policy restriction or conservative fallback routed decision to System 2.")
            final_option = ctx.system2_option or s1_choice

        # Both Engines Unavailable Fallback Protection
        if not s1_choice and not ctx.system2_option and selected_engine != DecisionEngine.HUMAN:
            selected_engine = DecisionEngine.ABSTAIN
            explanations.append("Both System 1 and System 2 options unavailable; abstaining safely.")
            final_option = None

        latency_ms = (time.perf_counter() - t0) * 1000

        result = ArbitrationResult(
            arbitration_id=arb_id,
            trace_id=trace_id,
            route=route,
            selected_engine=selected_engine,
            system1_confidence=s1_conf,
            system1_reliability=s1_reliability,
            system1_abstained=s1_abstained,
            system1_drift_state=drift_state.value,
            system2_required=system2_required,
            system2_reason=system2_reason,
            disagreement=disagreement_type,
            evidence_quality=ctx.evidence_quality,
            novelty=ctx.novelty,
            risk=ctx.risk_level,
            complexity=ctx.complexity,
            temporal_pressure=ctx.temporal_pressure,
            policy_version=policy_ver,
            arbitration_confidence=arbitration_confidence,
            final_decision_option=final_option,
            explanations=explanations,
            latency_ms=latency_ms,
            metadata=ctx.metadata,
        )

        self.telemetry_store.record_arbitration(result)
        return result

    def get_status(self) -> Dict[str, Any]:
        return {
            "policy": {
                "enabled": self.policy.enabled,
                "min_confidence": self.policy.min_confidence,
                "min_reliability": self.policy.min_reliability,
                "allow_hybrid": self.policy.allow_hybrid,
                "allow_human": self.policy.allow_human,
            },
            "escalation_quality": self.telemetry_store.get_escalation_quality(),
        }


# Global singleton instance
decision_arbitrator = DecisionArbitrator()
