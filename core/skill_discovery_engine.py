"""
Skill Discovery Engine for Autonomous Skill Discovery in MARK XLVIII / JARVIS.
Analyzes completed execution traces, identifies repeated successful workflow patterns,
and formulates CANDIDATE EvolvedSkillContracts without executing actions directly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.evolved_skill_contract import (
    EvolvedSkillContract,
    SkillScope,
    SkillStatus,
    SkillType,
    create_evolved_skill_contract,
)


@dataclass
class WorkflowTrace:
    trace_id: str
    goal: str
    project_id: str
    steps: List[Dict[str, Any]]
    success: bool
    verified: bool
    timestamp: float = 0.0


class SkillDiscoveryEngine:
    """
    Discovers candidate skills from recurring verified execution workflows.
    """

    def __init__(self, repetition_threshold: int = 2):
        self.repetition_threshold = repetition_threshold
        self._trace_history: List[WorkflowTrace] = []

    def record_workflow_execution(
        self,
        trace_id: str,
        goal: str,
        project_id: str,
        steps: List[Dict[str, Any]],
        success: bool,
        verified: bool,
    ) -> Optional[EvolvedSkillContract]:
        """
        Records verified workflow and triggers discovery if repeated pattern reaches threshold.
        """
        if not (success and verified):
            return None

        trace = WorkflowTrace(
            trace_id=trace_id,
            goal=goal,
            project_id=project_id,
            steps=steps,
            success=success,
            verified=verified,
            timestamp=time.time(),
        )
        self._trace_history.append(trace)

        return self._evaluate_for_candidate_skill(project_id, steps, goal)

    def _evaluate_for_candidate_skill(
        self,
        project_id: str,
        steps: List[Dict[str, Any]],
        goal: str,
    ) -> Optional[EvolvedSkillContract]:
        """
        Checks if identical sequence of operations has occurred >= repetition_threshold times.
        """
        step_signatures = [s.get("operation") or s.get("tool") or s.get("name", "") for s in steps]
        matching_count = 0

        for t in self._trace_history:
            if t.project_id.lower() == project_id.lower() and t.verified:
                t_sigs = [s.get("operation") or s.get("tool") or s.get("name", "") for s in t.steps]
                if t_sigs == step_signatures:
                    matching_count += 1

        if matching_count < self.repetition_threshold:
            return None

        # Build Candidate Skill
        skill_name = f"DISCOVERED_{project_id.upper()}_{'_'.join(step_signatures[:3]).upper()}"
        description = f"Autonomous workflow discovered from {matching_count} verified executions of goal: {goal}."

        candidate = create_evolved_skill_contract(
            skill_name=skill_name,
            description=description,
            skill_type=SkillType.WORKFLOW,
            scope=SkillScope.PROJECT,
            execution_steps=steps,
            required_tools=list(set(step_signatures)),
            authority_required="LOCAL_MUTATION" if any("kill" in s or "restart" in s for s in step_signatures) else "READ_ONLY",
            verification_requirements=["verify_http_response", "verify_process_alive"],
            metadata={"project_id": project_id, "discovered_from_traces": matching_count},
        )
        candidate.status = SkillStatus.CANDIDATE
        return candidate

    def clear_all(self) -> None:
        self._trace_history.clear()


# Global singleton instance
skill_discovery_engine = SkillDiscoveryEngine()
