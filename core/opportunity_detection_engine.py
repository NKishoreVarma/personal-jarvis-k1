"""
Opportunity Detection Engine for Proactive Task Orchestration in MARK XLVIII / JARVIS.
Inspects active goals, milestones, runtime health, regressions, and memory to detect high-value opportunities.
Enforces rule: EVIDENCE > PREDICTION (Opportunities must cite supporting evidence references).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.action_contract import RiskLevel
from core.opportunity_dismissal_manager import opportunity_dismissal_manager
from core.proactive_opportunity_contract import (
    OpportunityState,
    OpportunityType,
    ProactiveOpportunityContract,
    create_proactive_opportunity,
)


class OpportunityDetectionEngine:
    """
    Scans system telemetry and active context to discover actionable proactive opportunities.
    """

    def detect_opportunities(
        self,
        active_goals: Optional[List[Dict[str, Any]]] = None,
        runtime_health: Optional[Dict[str, Any]] = None,
        regression_signals: Optional[List[Dict[str, Any]]] = None,
        knowledge_gaps: Optional[List[Dict[str, Any]]] = None,
        project_id: str = "GLOBAL",
    ) -> List[ProactiveOpportunityContract]:
        """
        Synthesizes active observations into candidate proactive opportunities.
        """
        opportunities: List[ProactiveOpportunityContract] = []

        # 1. Inspect incomplete milestones from active goals
        if active_goals:
            for goal in active_goals:
                for milestone in goal.get("milestones", []):
                    if not milestone.get("completed", False):
                        opp = create_proactive_opportunity(
                            opportunity_type=OpportunityType.NEXT_STEP,
                            title=f"Continue Next Step: {milestone.get('name')}",
                            description=f"Next logical milestone for goal '{goal.get('title')}'.",
                            project_id=project_id,
                            source_goal_id=goal.get("goal_id", ""),
                            evidence_references=[f"goal:{goal.get('goal_id')}"],
                            confidence=0.90,
                            importance=0.85,
                            urgency=0.60,
                        )
                        if not opportunity_dismissal_manager.is_suppressed(opp):
                            opportunities.append(opp)
                        break  # Next logical step only

        # 2. Inspect runtime health & stale verifications
        if runtime_health:
            if runtime_health.get("stale_verification"):
                opp = create_proactive_opportunity(
                    opportunity_type=OpportunityType.VERIFICATION_REQUIRED,
                    title="Reverify Service Health",
                    description=f"Service {project_id} is active but verification is stale.",
                    project_id=project_id,
                    evidence_references=["health:stale_verification"],
                    confidence=0.95,
                    importance=0.80,
                    urgency=0.75,
                    required_authority="READ_ONLY",
                )
                if not opportunity_dismissal_manager.is_suppressed(opp):
                    opportunities.append(opp)

        # 3. Inspect regression signals
        if regression_signals:
            for reg in regression_signals:
                opp = create_proactive_opportunity(
                    opportunity_type=OpportunityType.REGRESSION,
                    title=f"Address Capability Regression: {reg.get('skill_name')}",
                    description=f"Skill '{reg.get('skill_name')}' degraded due to {reg.get('reason')}.",
                    project_id=project_id,
                    evidence_references=[f"reg:{reg.get('skill_name')}"],
                    confidence=0.90,
                    importance=0.80,
                    urgency=0.70,
                )
                if not opportunity_dismissal_manager.is_suppressed(opp):
                    opportunities.append(opp)

        # 4. Inspect knowledge gaps
        if knowledge_gaps:
            for gap in knowledge_gaps:
                opp = create_proactive_opportunity(
                    opportunity_type=OpportunityType.KNOWLEDGE_GAP,
                    title=f"Retrieve Knowledge: {gap.get('topic')}",
                    description=f"Documentation missing for {gap.get('topic')}.",
                    project_id=project_id,
                    evidence_references=[f"gap:{gap.get('topic')}"],
                    confidence=0.80,
                    importance=0.60,
                    urgency=0.40,
                )
                if not opportunity_dismissal_manager.is_suppressed(opp):
                    opportunities.append(opp)

        return opportunities


# Global singleton instance
opportunity_detection_engine = OpportunityDetectionEngine()
