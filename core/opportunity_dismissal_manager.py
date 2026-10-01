"""
Opportunity Dismissal Manager for Proactive Task Orchestration in MARK XLVIII / JARVIS.
Tracks and enforces user dismissals across scopes (ONCE, SESSION, PROJECT, PERMANENT)
to prevent repetitive proactive suggestion spam.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Dict, Optional, Set

from core.proactive_opportunity_contract import OpportunityState, ProactiveOpportunityContract


class DismissalScope(str, Enum):
    ONCE = "ONCE"
    SESSION = "SESSION"
    PROJECT = "PROJECT"
    PERMANENT = "PERMANENT"


class OpportunityDismissalManager:
    """
    Manages suppression records for dismissed proactive opportunities.
    """

    def __init__(self):
        self._dismissed_once: Set[str] = set()
        self._dismissed_session: Set[str] = set()
        self._dismissed_projects: Dict[str, Set[str]] = {}
        self._dismissed_permanent: Set[str] = set()

    def dismiss_opportunity(
        self,
        opportunity: ProactiveOpportunityContract,
        scope: DismissalScope = DismissalScope.SESSION,
    ) -> None:
        opportunity.state = OpportunityState.DISMISSED
        title_key = opportunity.title.strip().lower()

        if scope == DismissalScope.ONCE:
            self._dismissed_once.add(title_key)
        elif scope == DismissalScope.SESSION:
            self._dismissed_session.add(title_key)
        elif scope == DismissalScope.PROJECT:
            self._dismissed_projects.setdefault(opportunity.project_id.lower(), set()).add(title_key)
        elif scope == DismissalScope.PERMANENT:
            self._dismissed_permanent.add(title_key)

    def is_suppressed(
        self,
        opportunity: ProactiveOpportunityContract,
    ) -> bool:
        title_key = opportunity.title.strip().lower()

        if title_key in self._dismissed_permanent:
            return True
        if title_key in self._dismissed_session:
            return True
        if title_key in self._dismissed_once:
            return True
        proj_set = self._dismissed_projects.get(opportunity.project_id.lower(), set())
        if title_key in proj_set:
            return True

        return False

    def clear_session(self) -> None:
        self._dismissed_once.clear()
        self._dismissed_session.clear()

    def clear_all(self) -> None:
        self._dismissed_once.clear()
        self._dismissed_session.clear()
        self._dismissed_projects.clear()
        self._dismissed_permanent.clear()


# Global singleton instance
opportunity_dismissal_manager = OpportunityDismissalManager()
