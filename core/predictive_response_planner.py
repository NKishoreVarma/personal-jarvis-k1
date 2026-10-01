"""
Predictive Response Planner for MARK XLVIII / JARVIS.
Synthesizes speculative acknowledgements, success templates, and failure templates
in parallel with user speech and background execution.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.response_contract import ResponseContract, create_response_contract
from core.streaming_intent_engine import StreamingIntent


class PredictiveResponsePlanner:
    """
    Plans speculative verbal responses ahead of execution completion.
    """

    COMPLETION_REQUEST_KEYWORDS = {
        "tell me when", "notify me", "let me know", "when it's ready",
        "when it finishes", "alert me", "ping me", "report back",
    }

    def plan_response(
        self,
        intent: StreamingIntent,
        prep_context: Optional[Dict[str, Any]] = None,
    ) -> ResponseContract:
        """
        Constructs a structured ResponseContract tailored to the streaming intent and prepared context.
        """
        task_type = intent.intent_type
        entities = dict(intent.entities)
        if prep_context:
            entities.update(prep_context)

        raw_lower = intent.raw_text.lower()
        explicit_completion_requested = any(kw in raw_lower for kw in self.COMPLETION_REQUEST_KEYWORDS)
        quiet_requested = any(kw in raw_lower for kw in {"quietly", "silently", "in the background", "silent", "no audio", "don't speak", "dont speak", "shh"})

        if quiet_requested:
            return create_response_contract(
                turn_id=intent.turn_id,
                task_type=task_type,
                entities=entities,
                ack_response=None,
                success_template="",
                failure_template="Failed: {error}.",
                requires_completion_announcement=False,
            )

        # 1. Project Execution (e.g. "open FLOW and run the server")
        if task_type in ("RUN_PROJECT", "PROJECT_OPERATION"):
            proj = entities.get("project") or "Project"
            return create_response_contract(
                turn_id=intent.turn_id,
                task_type=task_type,
                entities=entities,
                ack_response="Starting " + proj + "." if proj else "Okay.",
                success_template="{project} is running successfully on port {port}." if "port" in entities else "{project} is running successfully.",
                failure_template="Failed to run {project}: {error}.",
                requires_completion_announcement=True,  # Background servers always announce when ready
            )

        # 2. Application Launch (e.g. "open WhatsApp")
        if task_type in ("OPEN_APP", "LAUNCH_APP"):
            app_name = entities.get("app_name") or "Application"
            return create_response_contract(
                turn_id=intent.turn_id,
                task_type=task_type,
                entities=entities,
                ack_response=f"Opening {app_name}.",
                success_template=f"{app_name} is now open.",
                failure_template=f"Could not open {app_name}: {{error}}.",
                requires_completion_announcement=explicit_completion_requested,  # Intelligent silence unless asked
            )

        # 3. Application Close (e.g. "close Chrome")
        if task_type in ("CLOSE_APP", "QUIT_APP"):
            app_name = entities.get("app_name") or "Application"
            return create_response_contract(
                turn_id=intent.turn_id,
                task_type=task_type,
                entities=entities,
                ack_response=f"Closing {app_name}.",
                success_template=f"{app_name} closed.",
                failure_template=f"Could not close {app_name}: {{error}}.",
                requires_completion_announcement=explicit_completion_requested,
            )

        # 4. Complex Agent Tasks
        if task_type in ("COMPLEX_AGENT", "COMPLEX_QUERY"):
            return create_response_contract(
                turn_id=intent.turn_id,
                task_type=task_type,
                entities=entities,
                ack_response="On it, I'll take care of that.",
                success_template="Task completed successfully.",
                failure_template="Task encountered an issue: {error}.",
                requires_completion_announcement=True,
            )

        # 5. Default Fallback
        return create_response_contract(
            turn_id=intent.turn_id,
            task_type=task_type,
            entities=entities,
            ack_response="Okay.",
            success_template="Done.",
            failure_template="Failed: {error}.",
            requires_completion_announcement=explicit_completion_requested,
        )


# Global singleton instance
predictive_response_planner = PredictiveResponsePlanner()
