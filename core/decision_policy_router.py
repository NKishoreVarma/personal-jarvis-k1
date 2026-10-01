"""
Decision Policy Router for Hybrid System 1 / System 2 Routing in MARK XLVIII / JARVIS.
Manages operating modes (SHADOW, ADVISORY, ACTIVE), per-route policy enablement,
policy versioning integration, and evidence-grounded disagreement arbitration.
Enforces rule: System 2 and Governance remain authoritative for high-risk and novel tasks.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.decision_contract import DecisionCategory, DecisionResult


class RoutingMode(str, Enum):
    SHADOW = "SHADOW"
    ADVISORY = "ADVISORY"
    ACTIVE = "ACTIVE"


@dataclass
class DisagreementRecord:
    trace_id: str
    category: DecisionCategory
    laya_choice: Optional[str]
    system2_choice: str
    laya_confidence: float
    final_choice: str
    rationale: str
    decision_id: Optional[str] = None
    selected_system: str = "SYSTEM_2"  # "SYSTEM_1" or "SYSTEM_2"
    actual_outcome: Optional[str] = None
    verified_correct_system: Optional[str] = "UNKNOWN"  # "SYSTEM_1", "SYSTEM_2", "BOTH", "NEITHER", "UNKNOWN"
    outcome_verified: bool = False
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "decision_id": self.decision_id,
            "category": self.category.value if hasattr(self.category, "value") else str(self.category),
            "laya_choice": self.laya_choice,
            "system2_choice": self.system2_choice,
            "laya_confidence": round(self.laya_confidence, 4),
            "final_choice": self.final_choice,
            "selected_system": self.selected_system,
            "actual_outcome": self.actual_outcome,
            "verified_correct_system": self.verified_correct_system,
            "outcome_verified": self.outcome_verified,
            "rationale": self.rationale,
            "recorded_at": self.recorded_at,
        }


class DecisionPolicyRouter:
    """
    Arbitrates decisions based on configured routing mode, category enablement,
    calibrated thresholds, and risk boundaries.
    """

    def __init__(
        self,
        mode: RoutingMode = RoutingMode.SHADOW,
        enabled_routes: Optional[Dict[DecisionCategory, bool]] = None,
    ):
        self.mode = mode
        self.enabled_routes: Dict[DecisionCategory, bool] = enabled_routes or {
            DecisionCategory.INTENT: True,
            DecisionCategory.AGENT_ROUTING: True,
            DecisionCategory.SKILL_SELECTION: True,
            DecisionCategory.STRATEGY_SELECTION: True,
            DecisionCategory.URGENCY: True,
            DecisionCategory.RISK: True,
            DecisionCategory.PROACTIVE: True,
            DecisionCategory.TEMPORAL: True,
            DecisionCategory.RESEARCH: True,
            DecisionCategory.MEMORY: True,
        }
        self.disagreements: List[DisagreementRecord] = []
        self.latest_arbitration: Optional[Dict[str, Any]] = None

    def set_mode(self, mode: RoutingMode) -> None:
        self.mode = mode

    def set_route_enabled(self, category: DecisionCategory, enabled: bool) -> None:
        self.enabled_routes[category] = enabled

    def is_route_active(self, category: DecisionCategory) -> bool:
        return self.mode == RoutingMode.ACTIVE and self.enabled_routes.get(category, False)

    @property
    def policy_version(self) -> str:
        try:
            from core.decision_policy_proposal import decision_policy_manager

            return decision_policy_manager.current_version
        except Exception:
            return "system1-policy-v1"

    def arbitrate_decision(
        self,
        laya_decision: DecisionResult,
        system2_decision_option: str,
        governance_override: bool = False,
    ) -> Tuple[str, str]:
        """
        Arbitrates final decision between System 1 recommendation and System 2 baseline.
        Returns (final_selected_option, arbitration_rationale).
        """
        laya_choice = laya_decision.selected_option
        has_disagreement = laya_choice != system2_decision_option

        # Phase 12.30: Execute DecisionArbitrator meta-reasoning evaluation
        try:
            from core.decision_arbitration import (
                ArbitrationContext,
                decision_arbitrator,
            )

            risk_lvl = "high" if (governance_override or laya_decision.category == DecisionCategory.RISK) else "low"
            arb_ctx = ArbitrationContext(
                context_text=laya_decision.metadata.get("context", ""),
                category=laya_decision.category,
                laya_decision=laya_decision,
                system2_option=system2_decision_option,
                risk_level=risk_lvl,
            )
            arb_res = decision_arbitrator.arbitrate(arb_ctx)
            laya_decision.metadata["arbitration"] = arb_res.to_dict()
            self.latest_arbitration = arb_res.to_dict()
        except Exception:
            pass

        # 1. Invariant: Governance override or High Risk always requires System 2
        if governance_override or laya_decision.category == DecisionCategory.RISK:
            final_choice = system2_decision_option
            rationale = "System 2 authoritative due to governance/risk policy."
            selected_sys = "SYSTEM_2"

        # 2. In SHADOW mode: Record telemetry, return System 2
        elif self.mode == RoutingMode.SHADOW:
            final_choice = system2_decision_option
            rationale = "SHADOW mode active; System 2 authoritative (telemetry recorded)."
            selected_sys = "SYSTEM_2"

        # 3. In ADVISORY mode: Advise only, return System 2
        elif self.mode == RoutingMode.ADVISORY:
            final_choice = system2_decision_option
            rationale = f"ADVISORY mode: Laya recommended '{laya_choice}', System 2 executed."
            selected_sys = "SYSTEM_2"

        # 4. In ACTIVE mode: If route is enabled and not abstained, use Laya decision
        elif self.is_route_active(laya_decision.category) and not laya_decision.abstained and laya_choice:
            final_choice = laya_choice
            rationale = "ACTIVE mode: System 1 fast route selected."
            selected_sys = "SYSTEM_1"

        else:
            final_choice = system2_decision_option
            rationale = "System 2 fallback executed (route disabled or abstained)."
            selected_sys = "SYSTEM_2"

        # Record disagreement if options diverged
        if has_disagreement:
            disagree = DisagreementRecord(
                trace_id=laya_decision.trace_id,
                decision_id=laya_decision.decision_id,
                category=laya_decision.category,
                laya_choice=laya_choice,
                system2_choice=system2_decision_option,
                laya_confidence=laya_decision.confidence,
                final_choice=final_choice,
                selected_system=selected_sys,
                rationale=rationale,
            )
            self.disagreements.append(disagree)

        return final_choice, rationale

    def update_disagreement_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        verified_correct_choice: str,
    ) -> bool:
        """
        Updates disagreement record with verified ground truth to determine which system was correct.
        Enforces rule: Do not assume System 2 was correct; evaluate both against verified ground truth.
        """
        updated = False
        for d in self.disagreements:
            if d.decision_id == decision_id:
                d.actual_outcome = actual_outcome
                d.outcome_verified = True

                laya_correct = d.laya_choice == verified_correct_choice
                sys2_correct = d.system2_choice == verified_correct_choice

                if laya_correct and not sys2_correct:
                    d.verified_correct_system = "SYSTEM_1"
                elif sys2_correct and not laya_correct:
                    d.verified_correct_system = "SYSTEM_2"
                elif laya_correct and sys2_correct:
                    d.verified_correct_system = "BOTH"
                else:
                    d.verified_correct_system = "NEITHER"

                updated = True
        return updated

    def get_disagreement_analysis(self) -> Dict[str, Any]:
        total = len(self.disagreements)
        if total == 0:
            return {
                "total_disagreements": 0,
                "system1_correct": 0,
                "system2_correct": 0,
                "neither_correct": 0,
                "both_correct": 0,
                "unverified": 0,
            }

        s1_wins = sum(1 for d in self.disagreements if d.verified_correct_system == "SYSTEM_1")
        s2_wins = sum(1 for d in self.disagreements if d.verified_correct_system == "SYSTEM_2")
        neither = sum(1 for d in self.disagreements if d.verified_correct_system == "NEITHER")
        both = sum(1 for d in self.disagreements if d.verified_correct_system == "BOTH")
        unverified = sum(1 for d in self.disagreements if not d.outcome_verified)

        return {
            "total_disagreements": total,
            "system1_correct": s1_wins,
            "system2_correct": s2_wins,
            "neither_correct": neither,
            "both_correct": both,
            "unverified": unverified,
        }

    def get_telemetry_summary(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "policy_version": self.policy_version,
            "enabled_routes": {k.value: v for k, v in self.enabled_routes.items()},
            "disagreement_count": len(self.disagreements),
            "disagreement_analysis": self.get_disagreement_analysis(),
            "latest_arbitration": self.latest_arbitration,
        }

    def clear_telemetry(self) -> None:
        self.disagreements.clear()


# Global singleton instance
decision_policy_router = DecisionPolicyRouter()
