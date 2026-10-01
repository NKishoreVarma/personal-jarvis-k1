"""
Agent Failure Manager for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Enforces the safety invariant: Agent Failure != Goal Failure.
Handles subagent errors, timeouts, retries, and strategic bypasses to preserve overall goal completion.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.agent_contract import AgentContract, AgentRole, AgentStatus


class FailureRecoveryStrategy(str, Enum):
    RETRY_AGENT = "RETRY_AGENT"
    REPLACE_AGENT = "REPLACE_AGENT"
    BYPASS_OPTIONAL = "BYPASS_OPTIONAL"
    FALLBACK_LOCAL = "FALLBACK_LOCAL"
    FAIL_GOAL = "FAIL_GOAL"


class AgentFailureManager:
    """
    Evaluates failed subagents and determines adaptive recovery strategies.
    """

    def handle_agent_failure(
        self,
        agent: AgentContract,
        error_reason: str,
        retry_count: int = 0,
    ) -> Tuple[FailureRecoveryStrategy, str]:
        """
        Determines whether to retry, replace, or bypass a failed subagent.
        """
        # 1. Research Agent failures can be bypassed with local reasoning
        if agent.role == AgentRole.RESEARCHER:
            return FailureRecoveryStrategy.FALLBACK_LOCAL, "Researcher failed; falling back to local diagnostics and project evidence."

        # 2. Observer Agent failures can be retried once
        if agent.role == AgentRole.OBSERVER and retry_count < 1:
            return FailureRecoveryStrategy.RETRY_AGENT, "Observer timed out; retrying inspection once."

        # 3. Verifier failures can be replaced with direct probe
        if agent.role == AgentRole.VERIFIER and retry_count < 2:
            return FailureRecoveryStrategy.REPLACE_AGENT, "Verifier failed; dispatching fallback direct probe."

        # 4. Critical executor failures after retries fail the step safely
        if agent.role == AgentRole.EXECUTOR:
            return FailureRecoveryStrategy.FAIL_GOAL, f"Executor mutation failed ({error_reason}); halting for safety."

        return FailureRecoveryStrategy.BYPASS_OPTIONAL, "Optional agent task failed; bypassing to preserve goal."


# Global singleton instance
agent_failure_manager = AgentFailureManager()
