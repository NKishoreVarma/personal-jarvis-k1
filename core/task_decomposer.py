"""
Task Decomposer for MARK XLVIII / JARVIS.
Decomposes complex compound natural language commands into sequential executable steps,
resolving temporal dependencies (then, after, once, when) and negative constraints (but don't send).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

NEGATIVE_CONSTRAINTS = [
    re.compile(r"but\s+(?:don't|do\s+not)\s+(?:send|execute|run|merge)(?:\s+it)?", re.IGNORECASE),
    re.compile(r"without\s+(?:sending|executing|merging)(?:\s+it)?", re.IGNORECASE),
    re.compile(r"(?:don't|do\s+not)\s+(?:send|execute)(?:\s+it)?\s+until\s+i\s+confirm", re.IGNORECASE),
    re.compile(r"draft\s+only", re.IGNORECASE),
    re.compile(r"ask(?:\s+me)?\s+before\s+(?:sending|executing)", re.IGNORECASE),
]

CLAUSE_SPLITTERS = re.compile(
    r"(?:\s*,\s*|\s+(?:and\s+then|then|after\s+that|once\s+it(?:'s|\s+is)\s+ready|when\s+ready|and\s+also|and)\s+)",
    re.IGNORECASE,
)


class TaskDecomposer:
    """
    Deterministically breaks multi-step user instructions into ordered, dependency-aware steps.
    """

    def decompose(self, text: str) -> Dict[str, Any]:
        """
        Parses text into ordered steps, capturing negative constraints.
        """
        cleaned = text.strip()
        prohibit_send = False
        constraints: List[str] = []

        # Check negative constraints
        for pattern in NEGATIVE_CONSTRAINTS:
            if pattern.search(cleaned):
                prohibit_send = True
                constraints.append("PROHIBIT_AUTO_SEND")
                # Strip negative constraint from text for cleaner step parsing
                cleaned = pattern.sub("", cleaned).strip()

        # Split into sub-clauses
        raw_clauses = [c.strip() for c in CLAUSE_SPLITTERS.split(cleaned) if c.strip()]
        if not raw_clauses:
            raw_clauses = [cleaned]

        steps: List[Dict[str, Any]] = []
        step_id = 1

        for clause in raw_clauses:
            parsed = self._parse_clause(clause, step_id=step_id, prohibit_send=prohibit_send)
            if parsed:
                steps.extend(parsed)
                step_id = len(steps) + 1

        # Deduplicate/merge consecutive project runner steps
        merged_steps: List[Dict[str, Any]] = []
        for s in steps:
            if merged_steps and merged_steps[-1]["tool"] == "run_project" and s["tool"] == "run_project":
                if s["parameters"].get("project_name") not in ("current", ""):
                    merged_steps[-1]["parameters"]["project_name"] = s["parameters"]["project_name"]
                if s["parameters"].get("location_hint"):
                    merged_steps[-1]["parameters"]["location_hint"] = s["parameters"]["location_hint"]
            else:
                s["step"] = len(merged_steps) + 1
                merged_steps.append(s)

        return {
            "is_multi_step": len(merged_steps) > 1,
            "steps": merged_steps,
            "constraints": constraints,
            "prohibit_send": prohibit_send,
            "original_query": text,
        }

    def _parse_clause(self, clause: str, step_id: int, prohibit_send: bool) -> List[Dict[str, Any]]:
        """Maps a single natural language clause to one or more tool steps."""
        c = clause.strip().lower()
        steps: List[Dict[str, Any]] = []

        # 1. Project Runner: "open flow from desktop and run server" / "run flow" / "open flow from desktop" / "run server"
        m_proj = re.search(
            r"(?:open\s+([a-zA-Z0-9\._-]+)\s+from\s+(?:my\s+)?([a-zA-Z0-9\._-]+)|"
            r"open\s+([a-zA-Z0-9\._-]+)\s+and\s+(?:run|start)|"
            r"(?:run|start)\s+(?:the\s+)?project\s+([a-zA-Z0-9\._-]+)|"
            r"(?:run|start)\s+(?:the\s+)?(?:server|app|project)|"
            r"(?:run|start)\s+([a-zA-Z0-9\._-]+))",
            c,
        )
        if m_proj:
            p_name = m_proj.group(1) or m_proj.group(3) or m_proj.group(4) or m_proj.group(5) or "current"
            if p_name.lower() in ("server", "app", "project", "the server", "the app"):
                p_name = "current"
            loc = m_proj.group(2)
            steps.append({
                "step": step_id,
                "goal": f"Run project {p_name} server",
                "tool": "run_project",
                "parameters": {"project_name": p_name, "location_hint": loc},
                "risk": "low_risk",
                "requires_verification": True,
            })
            return steps

        # 2. WhatsApp Chat: "find john" / "open john's chat" / "open my chat with john"
        m_chat = re.search(r"(?:find\s+([a-zA-Z0-9\s]+)|open\s+(?:my\s+)?chat\s+with\s+([a-zA-Z0-9\s]+)|open\s+([a-zA-Z0-9\s]+)'s\s+chat)", c)
        if m_chat:
            contact = (m_chat.group(1) or m_chat.group(2) or m_chat.group(3) or "").strip()
            # Clean trailing words
            contact = re.sub(r"\s+(in\s+whatsapp|on\s+whatsapp)$", "", contact).strip()
            steps.append({
                "step": step_id,
                "goal": f"Open chat with {contact}",
                "tool": "open_whatsapp_chat",
                "parameters": {"contact_name": contact},
                "risk": "low_risk",
                "requires_verification": True,
            })
            return steps

        # 3. Message Drafting: "write that I'll be late" / "tell him hello" / "type message"
        m_msg = re.search(r"(?:write\s+(?:that\s+)?|type\s+|tell\s+[a-zA-Z0-9]+\s+(?:that\s+)?)(.+)", clause, re.IGNORECASE)
        if m_msg:
            msg_body = m_msg.group(1).strip().strip("'\"")
            steps.append({
                "step": step_id,
                "goal": f"Draft message '{msg_body}'",
                "tool": "execute_computer_action",
                "parameters": {
                    "action": "TYPE_TEXT",
                    "target": {},
                    "payload": {"text": msg_body},
                },
                "risk": "reversible",
                "draft_only": True,
            })
            return steps

        # 4. Open Application: "open whatsapp" / "open chrome" / "launch vscode"
        m_app = re.search(r"^(?:open|launch|start|switch\s+to)\s+([a-zA-Z0-9\s\.\-_]+)$", c)
        if m_app:
            app_name = m_app.group(1).strip()
            steps.append({
                "step": step_id,
                "goal": f"Open {app_name}",
                "tool": "open_desktop_app",
                "parameters": {"name": app_name},
                "risk": "low_risk",
            })
            return steps

        # 5. Open URL in Browser: "open it in chrome" / "navigate to localhost:3000"
        m_browser = re.search(r"(?:open\s+(?:it\s+)?in\s+([a-zA-Z0-9\s]+)|navigate\s+to\s+([a-zA-Z0-9\:\/\.\-_]+))", c)
        if m_browser:
            browser = m_browser.group(1) or "Chrome"
            url = m_browser.group(2) or "http://localhost:3000"
            steps.append({
                "step": step_id,
                "goal": f"Open {url} in {browser}",
                "tool": "open_desktop_app",
                "parameters": {"name": browser},
                "risk": "low_risk",
            })
            return steps

        # Generic step fallback
        steps.append({
            "step": step_id,
            "goal": clause.strip(),
            "tool": "generic_action",
            "parameters": {"query": clause.strip()},
            "risk": "low_risk",
        })
        return steps


task_decomposer = TaskDecomposer()
