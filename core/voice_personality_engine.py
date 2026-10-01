"""
Voice Personality Engine for MARK XLVIII / JARVIS.
Transforms structured intent and execution state into natural, concise spoken responses.
Enforces the personality: Calm, Precise, Confident, Concise, Context-Aware, Not overly talkative.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.response_length_policy import ResponseVerbosity, response_length_policy


class VoicePersonalityEngine:
    """
    Renders structured response intents into natural, bounded English without chatbot verbosity.
    """

    def render_response(
        self,
        response_type: str,
        task_type: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        verbosity: ResponseVerbosity = ResponseVerbosity.SHORT,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Synthesizes a clean, natural spoken string in < 1ms.
        """
        data = {**(entities or {}), **(context or {})}
        project = data.get("project") or data.get("project_name")
        app_name = data.get("app_name") or data.get("application")
        target = project or app_name or data.get("target") or "Task"
        port = data.get("port")

        resp_type_upper = response_type.upper()

        # 1. SILENT
        if resp_type_upper == "SILENT":
            return ""

        # 2. ACKNOWLEDGEMENT
        if resp_type_upper in ("ACKNOWLEDGEMENT", "SHORT_ACK"):
            if task_type in ("OPEN_APP", "LAUNCH_APP") and app_name:
                return f"Opening {app_name}."
            if task_type in ("CLOSE_APP", "QUIT_APP") and app_name:
                return f"Closing {app_name}."
            if task_type in ("RUN_PROJECT", "PROJECT_OPERATION") and project:
                return f"Starting {project}."
            if verbosity == ResponseVerbosity.MINIMAL:
                return "Okay."
            return "On it."

        # 3. VERIFIED COMPLETION
        if resp_type_upper == "COMPLETION":
            if task_type in ("RUN_PROJECT", "PROJECT_OPERATION") and project:
                if port:
                    return f"{project} is running on port {port}."
                return f"{project} is running."

            if task_type in ("OPEN_APP", "LAUNCH_APP") and app_name:
                return f"{app_name} is now open."

            if task_type in ("CLOSE_APP", "QUIT_APP") and app_name:
                return f"{app_name} closed."

            return f"{target} is complete."

        # 4. REDUNDANCY / STATE UPDATE
        if resp_type_upper in ("REDUNDANCY", "STATE_UPDATE", "ALREADY_ACTIVE"):
            if task_type in ("RUN_PROJECT", "PROJECT_OPERATION") and project:
                return f"{project} is already running."
            if task_type in ("OPEN_APP", "LAUNCH_APP") and app_name:
                return f"{app_name} is already open."
            return f"{target} is already active."

        # 5. CLARIFICATION
        if resp_type_upper == "CLARIFICATION":
            choices = data.get("choices") or []
            if len(choices) >= 2:
                choices_str = f"{choices[0]} and {choices[1]}"
                return f"I found {choices_str}. Which one?"
            question = data.get("question")
            if question:
                return str(question)
            return f"Which {target} would you like me to open?"

        # 6. PROGRESS
        if resp_type_upper == "PROGRESS":
            if project:
                return f"Still starting {project}."
            return f"Still working on {target}."

        # 7. FAILURE
        if resp_type_upper == "FAILURE":
            clean_err = self._sanitize_error(error)
            if clean_err:
                return f"{target} didn't start. {clean_err}."
            return f"{target} didn't start."

        return "Okay."

    def _sanitize_error(self, raw_error: Optional[str]) -> Optional[str]:
        """Strips stack traces and technical jargon from spoken error output."""
        if not raw_error:
            return None
        err_lower = raw_error.lower()
        if "already in use" in err_lower or "address already in use" in err_lower or "eaddrinuse" in err_lower:
            return "Port is already in use"
        if "not found" in err_lower or "no such file" in err_lower:
            return "Project files not found"
        if "permission" in err_lower:
            return "Permission was denied"
        if "timeout" in err_lower:
            return "Operation timed out"

        # If it's a short 1-sentence explanation, keep it
        sentences = raw_error.split(".")
        if sentences and len(sentences[0].split()) <= 8:
            return sentences[0].strip()

        return None


# Global singleton instance
voice_personality_engine = VoicePersonalityEngine()
