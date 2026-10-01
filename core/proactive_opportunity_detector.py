"""
Proactive Opportunity Detector for MARK XLVIII / JARVIS.
Detects operational moments where anticipatory assistance or suggestions create real value
without intrusive interruption or unwanted side-effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.context_contract import ContextContract, ContextTaskState


class OpportunityValue(str, Enum):
    NO_OPPORTUNITY = "NO_OPPORTUNITY"
    LOW_VALUE = "LOW_VALUE"
    USEFUL = "USEFUL"
    HIGH_VALUE = "HIGH_VALUE"
    CRITICAL = "CRITICAL"


class OpportunityType(str, Enum):
    PROJECT_STARTED_OPEN_BROWSER = "PROJECT_STARTED_OPEN_BROWSER"
    REPEATED_FAILURE_APPLY_SKILL = "REPEATED_FAILURE_APPLY_SKILL"
    WAITING_STATE_MONITOR = "WAITING_STATE_MONITOR"
    MISSING_DEPENDENCY_REPAIR = "MISSING_DEPENDENCY_REPAIR"
    RELATED_TASK_SUGGESTION = "RELATED_TASK_SUGGESTION"
    NONE = "NONE"


@dataclass
class ProactiveOpportunity:
    opportunity_id: str
    opportunity_type: OpportunityType
    value_tier: OpportunityValue
    project_name: str
    description: str
    suggested_action: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.90
    requires_voice_prompt: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_type": self.opportunity_type.value,
            "value_tier": self.value_tier.value,
            "project_name": self.project_name,
            "description": self.description,
            "suggested_action": self.suggested_action,
            "arguments": self.arguments,
            "confidence": self.confidence,
            "requires_voice_prompt": self.requires_voice_prompt,
        }


class ProactiveOpportunityDetector:
    """
    Evaluates current ContextContract to detect actionable proactive opportunities.
    """

    def detect_opportunity(self, context: ContextContract) -> ProactiveOpportunity:
        """
        Evaluates operational context and returns classified ProactiveOpportunity.
        """
        if context.is_expired():
            return ProactiveOpportunity(
                opportunity_id="opp_none",
                opportunity_type=OpportunityType.NONE,
                value_tier=OpportunityValue.NO_OPPORTUNITY,
                project_name=context.active_project,
                description="Context expired",
                suggested_action="",
                confidence=0.0,
            )

        proj = context.active_project or "FLOW"

        # 1. Check for PROJECT_STARTED_SUCCESSFULLY
        if context.task_state == ContextTaskState.RUNNING:
            recent_acts = [a.get("action", "") for a in context.recent_verified_actions]
            if "server_started" in recent_acts or "process_running" in recent_acts:
                port = 3000
                for a in context.recent_verified_actions:
                    if a.get("port"):
                        port = a.get("port")
                        break
                return ProactiveOpportunity(
                    opportunity_id=f"opp_open_{proj.lower()}",
                    opportunity_type=OpportunityType.PROJECT_STARTED_OPEN_BROWSER,
                    value_tier=OpportunityValue.HIGH_VALUE,
                    project_name=proj,
                    description=f"{proj} is running on port {port}",
                    suggested_action="open_browser",
                    arguments={"url": f"http://localhost:{port}", "project": proj, "port": port},
                    confidence=0.95,
                    requires_voice_prompt=True,
                )

        # 2. Check for REPEATED_FAILURE
        if context.task_state == ContextTaskState.FAILED:
            return ProactiveOpportunity(
                opportunity_id=f"opp_fix_{proj.lower()}",
                opportunity_type=OpportunityType.REPEATED_FAILURE_APPLY_SKILL,
                value_tier=OpportunityValue.HIGH_VALUE,
                project_name=proj,
                description=f"{proj} failed during execution",
                suggested_action="apply_learned_skill",
                arguments={"project": proj, "skill_hint": "port_conflict"},
                confidence=0.92,
                requires_voice_prompt=True,
            )

        # 3. Check for WAITING_STATE
        if context.task_state == ContextTaskState.WAITING or context.task_state == ContextTaskState.STARTING:
            return ProactiveOpportunity(
                opportunity_id=f"opp_wait_{proj.lower()}",
                opportunity_type=OpportunityType.WAITING_STATE_MONITOR,
                value_tier=OpportunityValue.USEFUL,
                project_name=proj,
                description=f"Waiting for {proj} server startup",
                suggested_action="monitor_completion",
                arguments={"project": proj},
                confidence=0.88,
                requires_voice_prompt=False,
            )

        # 4. Low-value or No Opportunity
        return ProactiveOpportunity(
            opportunity_id="opp_none",
            opportunity_type=OpportunityType.NONE,
            value_tier=OpportunityValue.NO_OPPORTUNITY,
            project_name=proj,
            description="No immediate proactive action required",
            suggested_action="",
            confidence=0.50,
            requires_voice_prompt=False,
        )

    def detect_opportunity_from_world_model(self, wm: Optional[Any] = None) -> ProactiveOpportunity:
        """
        Evaluates WorldModel facts and multimodal fusion diagnostics to detect proactive opportunities.
        Enforces: TIME + OBSERVATION != AUTHORIZATION (suggestions require explicit user authorization).
        """
        try:
            from core.multimodal_fusion_engine import multimodal_fusion_engine
            fusion = multimodal_fusion_engine.fuse()
            state = fusion.get("state")
            cause = fusion.get("cause")

            if state == "BUILD_FAILURE":
                return ProactiveOpportunity(
                    opportunity_id="opp_perception_build_failure",
                    opportunity_type=OpportunityType.REPEATED_FAILURE_APPLY_SKILL,
                    value_tier=OpportunityValue.HIGH_VALUE,
                    project_name="WORKSPACE",
                    description=f"Perception detected build failure: {cause}",
                    suggested_action="diagnose_build_failure",
                    arguments={"cause": cause, "evidence": fusion.get("evidence", [])},
                    confidence=fusion.get("confidence", 0.90),
                    requires_voice_prompt=True,
                )
            elif state == "APPLICATION_CRASH":
                return ProactiveOpportunity(
                    opportunity_id="opp_perception_app_crash",
                    opportunity_type=OpportunityType.REPEATED_FAILURE_APPLY_SKILL,
                    value_tier=OpportunityValue.HIGH_VALUE,
                    project_name="APPLICATION",
                    description=f"Perception detected crash: {cause}",
                    suggested_action="investigate_crash",
                    arguments={"cause": cause},
                    confidence=fusion.get("confidence", 0.95),
                    requires_voice_prompt=True,
                )
        except Exception:
            pass

        return ProactiveOpportunity(
            opportunity_id="opp_none",
            opportunity_type=OpportunityType.NONE,
            value_tier=OpportunityValue.NO_OPPORTUNITY,
            project_name="WORKSPACE",
            description="Environment is healthy",
            suggested_action="",
            confidence=0.50,
            requires_voice_prompt=False,
        )


# Global singleton instance
proactive_opportunity_detector = ProactiveOpportunityDetector()
