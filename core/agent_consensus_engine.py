"""
Agent Consensus Engine for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Aggregates diagnostic hypotheses and observation reports across multiple agents.
Enforces invariant: Agent Agreement != Truth (Live physical verification always overrides multi-agent voting).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ConsensusOutcome:
    consensus_hypothesis: str
    confidence: float
    agreeing_agents: List[str]
    dissenting_agents: List[str]
    reality_overridden: bool = False


class AgentConsensusEngine:
    """
    Evaluates multi-agent agreement while guaranteeing live verification priority.
    """

    def evaluate_consensus(
        self,
        agent_hypotheses: List[Dict[str, Any]],
        live_observation: Optional[Dict[str, Any]] = None,
    ) -> ConsensusOutcome:
        """
        Builds consensus outcome from agent reports.
        If live_observation directly contradicts majority hypothesis, live_observation WINS.
        """
        if not agent_hypotheses:
            return ConsensusOutcome(
                consensus_hypothesis="NO_HYPOTHESIS",
                confidence=0.0,
                agreeing_agents=[],
                dissenting_agents=[],
            )

        # Count votes per hypothesis
        counts: Dict[str, List[str]] = {}
        for item in agent_hypotheses:
            hyp = item.get("hypothesis", "UNKNOWN")
            agent_id = item.get("agent_id", "anon")
            counts.setdefault(hyp, []).append(agent_id)

        # Find majority
        best_hyp = max(counts.keys(), key=lambda k: len(counts[k]))
        agreeing = counts[best_hyp]
        dissenting = [item.get("agent_id", "") for item in agent_hypotheses if item.get("hypothesis") != best_hyp]
        confidence = len(agreeing) / len(agent_hypotheses)

        # Invariant: Check if live observation contradicts the consensus
        if live_observation:
            observed_reality = live_observation.get("actual_cause")
            if observed_reality and observed_reality != best_hyp:
                # Reality OVERRIDES majority vote!
                return ConsensusOutcome(
                    consensus_hypothesis=observed_reality,
                    confidence=1.0,
                    agreeing_agents=[],
                    dissenting_agents=list(counts.keys()),
                    reality_overridden=True,
                )

        return ConsensusOutcome(
            consensus_hypothesis=best_hyp,
            confidence=confidence,
            agreeing_agents=agreeing,
            dissenting_agents=dissenting,
            reality_overridden=False,
        )


# Global singleton instance
agent_consensus_engine = AgentConsensusEngine()
