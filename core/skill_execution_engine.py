"""
Skill Execution Engine for MARK XLVIII / JARVIS.
Safely executes adapted learned skill workflows with ActionContract safety boundaries,
ApprovalStore gating, and mandatory multi-tiered outcome verification.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from actions.project_runner import run_project_async
from core.action_contract import ActionContract, ApprovalState, RiskLevel
from core.approval_manager import approval_store
from core.process_manager import process_manager
from core.skill_adapter import skill_adapter
from core.skill_contract import SkillContract
from core.skill_precondition_checker import skill_precondition_checker
from core.verification_engine import VerificationLevel, verification_engine


class SkillExecutionEngine:
    """
    Executes learned skill workflows safely and verifies real-world outcomes.
    """

    async def execute_skill_async(
        self,
        skill: SkillContract,
        context: Dict[str, Any],
        observation: Dict[str, Any],
        target_port: int = 3000,
        verify_tests: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes a skill end-to-end with safety gating and outcome verification.
        """
        # 1. Precondition verification
        precond_ok, precond_err = skill_precondition_checker.check_preconditions(skill, context, observation)
        if not precond_ok:
            return {
                "success": False,
                "error": f"Preconditions failed: {precond_err}",
                "skill_id": skill.skill_id,
                "outcome_verified": False,
            }

        # 2. Parameter adaptation
        adapted_steps = skill.adapter_steps if hasattr(skill, "adapter_steps") else skill_adapter.adapt_skill(skill, context, observation)
        project_name = context.get("project") or skill.project_scope or "Project"

        print(f"[SKILL_EXECUTION] ⚡ Executing skill '{skill.skill_name}' ({len(adapted_steps)} steps) for '{project_name}'")

        executed_actions: List[str] = []

        # 3. Step execution with ActionContract safety checks
        for step in adapted_steps:
            action_name = step.get("action", "")
            risk_str = step.get("risk_level", "LOW")

            # Risk classification
            risk_enum = RiskLevel.HIGH_RISK if risk_str == "HIGH" else RiskLevel.DESTRUCTIVE if risk_str == "DESTRUCTIVE" else RiskLevel.LOW_RISK
            contract = ActionContract(
                connector="skill_execution",
                operation=action_name,
                arguments={"target": project_name},
                risk_level=risk_enum,
            )

            if contract.approval_required:
                print(f"[SKILL_EXECUTION] 🛡️ Action '{action_name}' requires approval.")
                approval_store.create_proposal(contract)
                if contract.approval_state != ApprovalState.APPROVED:
                    return {
                        "success": False,
                        "error": f"Action '{action_name}' rejected or pending approval.",
                        "skill_id": skill.skill_id,
                        "outcome_verified": False,
                    }

            # Execute real operations
            if action_name == "terminate_conflicting_processes":
                procs = process_manager.list_processes()
                for p in procs:
                    if p.get("project_name", "").lower() == project_name.lower():
                        process_manager.stop_process(p["process_id"])
                await asyncio.sleep(0.1)

            elif action_name == "restart_project_server":
                await run_project_async(project_name, location_hint="desktop", startup_wait_seconds=4.0)

            executed_actions.append(action_name)
            await asyncio.sleep(0.05)

        # 4. Multi-tiered outcome verification
        verif = verification_engine.verify_outcome(
            project_name=project_name,
            target_port=target_port,
            verify_tests=verify_tests,
        )

        outcome_ok = verif.get("outcome_verified", False)
        print(f"[SKILL_EXECUTION] Verification result for '{skill.skill_name}': outcome_verified={outcome_ok}")

        return {
            "success": outcome_ok,
            "outcome_verified": outcome_ok,
            "skill_id": skill.skill_id,
            "skill_name": skill.skill_name,
            "project": project_name,
            "port": target_port,
            "executed_actions": executed_actions,
            "verification": verif,
        }


# Global singleton instance
skill_execution_engine = SkillExecutionEngine()
