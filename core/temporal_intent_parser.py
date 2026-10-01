"""
Temporal Intent Parser for Temporal Task Intelligence in MARK XLVIII / JARVIS.
Extracts scheduling, deadlines, delays, reminders, and recurrence rules from natural language user instructions.
Preserves safe ambiguity for terms like 'later' (mapped to DEFERRED) without inventing false timestamps.
"""

from __future__ import annotations

import re
import time
from typing import Optional, Tuple

from core.temporal_contract import (
    TemporalContract,
    TemporalType,
    create_temporal_contract,
)


class TemporalIntentParser:
    """
    Parses conversational time expressions into structured temporal contracts.
    """

    def parse_temporal_instruction(
        self,
        text: str,
        default_project: str = "GLOBAL",
        current_time: Optional[float] = None,
    ) -> Tuple[Optional[TemporalContract], str]:
        """
        Parses time expressions from user request string.
        """
        now = current_time if current_time is not None else time.time()
        t_lower = text.strip().lower()

        # 1. "later" -> DEFERRED task
        if re.search(r"\b(later|postpone|handle (this )?later|do (this )?later)\b", t_lower):
            contract, msg = create_temporal_contract(
                title=f"Deferred Task: {text}",
                description=text,
                temporal_type=TemporalType.DEFERRED,
                project_id=default_project,
            )
            return contract, "Parsed as deferred task without arbitrary clock time."

        # 2. "in X minutes" / "in X hours" / "in X seconds"
        min_match = re.search(r"in\s+(\d+)\s+min(ute)?s?", t_lower)
        if min_match:
            mins = int(min_match.group(1))
            scheduled = now + (mins * 60)
            return create_temporal_contract(
                title=f"Scheduled Task: {text}",
                description=text,
                temporal_type=TemporalType.SCHEDULED,
                scheduled_at=scheduled,
                project_id=default_project,
            )

        hour_match = re.search(r"in\s+(\d+)\s+hour?s?", t_lower)
        if hour_match:
            hrs = int(hour_match.group(1))
            scheduled = now + (hrs * 3600)
            return create_temporal_contract(
                title=f"Scheduled Task: {text}",
                description=text,
                temporal_type=TemporalType.SCHEDULED,
                scheduled_at=scheduled,
                project_id=default_project,
            )

        if "in an hour" in t_lower:
            scheduled = now + 3600
            return create_temporal_contract(
                title=f"Scheduled Task: {text}",
                description=text,
                temporal_type=TemporalType.SCHEDULED,
                scheduled_at=scheduled,
                project_id=default_project,
            )

        # 3. "tomorrow" -> scheduled 24 hours ahead
        if "tomorrow" in t_lower:
            scheduled = now + 86400
            t_type = TemporalType.REMINDER if "remind" in t_lower else TemporalType.SCHEDULED
            return create_temporal_contract(
                title=f"Reminder: {text}" if t_type == TemporalType.REMINDER else f"Scheduled: {text}",
                description=text,
                temporal_type=t_type,
                scheduled_at=scheduled,
                due_at=scheduled + 3600,
                project_id=default_project,
            )

        # 4. "next week" -> scheduled 7 days ahead
        if "next week" in t_lower:
            scheduled = now + (7 * 86400)
            return create_temporal_contract(
                title=f"Scheduled Task: {text}",
                description=text,
                temporal_type=TemporalType.SCHEDULED,
                scheduled_at=scheduled,
                project_id=default_project,
            )

        # 5. "every day" / "daily"
        if "every day" in t_lower or "daily" in t_lower:
            return create_temporal_contract(
                title=f"Daily Recurring Task: {text}",
                description=text,
                temporal_type=TemporalType.RECURRING,
                recurrence_rule="daily",
                scheduled_at=now + 86400,
                project_id=default_project,
            )

        # 6. "every X hours"
        rec_match = re.search(r"every\s+(\d+)\s+hour?s?", t_lower)
        if rec_match:
            hrs = int(rec_match.group(1))
            interval = hrs * 3600
            return create_temporal_contract(
                title=f"Recurring Task ({hrs}h): {text}",
                description=text,
                temporal_type=TemporalType.RECURRING,
                recurrence_rule=f"interval:{interval}",
                scheduled_at=now + interval,
                project_id=default_project,
            )

        return None, "No recognizable temporal expression found."


# Global singleton instance
temporal_intent_parser = TemporalIntentParser()
