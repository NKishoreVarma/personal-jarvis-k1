"""
Research Governor for Autonomous Knowledge Acquisition in MARK XLVIII / JARVIS.
Enforces the central safety boundary: Research does not expand authority, trigger mutations, or bypass ActionContract / ApprovalStore.
Decision outputs: ALLOW_RESEARCH, LIMIT_RESEARCH, REQUIRE_VERIFICATION, REQUIRE_APPROVAL, REJECT_RESEARCH, STOP_RESEARCH.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from core.research_task_contract import ResearchTaskContract


class ResearchDecision(str, Enum):
    ALLOW_RESEARCH = "ALLOW_RESEARCH"
    LIMIT_RESEARCH = "LIMIT_RESEARCH"
    REQUIRE_VERIFICATION = "REQUIRE_VERIFICATION"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REJECT_RESEARCH = "REJECT_RESEARCH"
    STOP_RESEARCH = "STOP_RESEARCH"


class ResearchGovernor:
    """
    Evaluates research task proposals to enforce scope bounds and safety invariants.
    """

    def __init__(self):
        self.research_enabled: bool = True

    def set_research_enabled(self, enabled: bool) -> None:
        self.research_enabled = enabled

    def evaluate_research_task(
        self,
        task: ResearchTaskContract,
        user_explicit_approval: bool = False,
    ) -> Tuple[ResearchDecision, str]:
        """
        Validates safety invariants before research execution begins.
        """
        if not self.research_enabled:
            return ResearchDecision.REJECT_RESEARCH, "Autonomous research is disabled by user policy."

        # 1. Invariant: Authority expansion rejection
        if task.authority_level != "READ_ONLY":
            return ResearchDecision.REJECT_RESEARCH, "Rejected: Research cannot request elevated or mutating authority."

        # 2. Scope & budget bounding
        if task.max_sources > 10 or task.time_budget_seconds > 60.0:
            return ResearchDecision.LIMIT_RESEARCH, "Research scope exceeds standard limits; throttling to bounded constraints."

        # 3. If task requests action execution based on findings, require approval
        if task.metadata.get("triggers_system_mutation", False):
            if not user_explicit_approval:
                return ResearchDecision.REQUIRE_APPROVAL, "Mutating actions following research require explicit human approval."

        return ResearchDecision.ALLOW_RESEARCH, "Research task approved for execution."


# Global singleton instance
research_governor = ResearchGovernor()
