"""
Problem Solver Coordinator for MARK XLVIII / JARVIS.
Orchestrates deep reasoning, autonomous hypothesis evaluation, diagnostic planning,
safe repair execution, multi-tiered verification, and self-correcting replanning.
Enforces the loop: UNDERSTAND -> OBSERVE -> REASON -> PLAN -> EXECUTE -> VERIFY -> REPLAN.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from actions.project_runner import run_project_async
from core.action_contract import ActionContract, ApprovalState, RiskLevel
from core.approval_manager import approval_store
from core.diagnostic_planner import diagnostic_planner
from core.event_bus import Event, EventType, event_bus
from core.goal_contract import GoalContract, GoalStatus, create_goal_contract
from core.hypothesis_engine import hypothesis_engine
from core.loop_guard import loop_guard
from core.observation_engine import observation_engine
from core.process_manager import process_manager
from core.reasoning_state import (
    Hypothesis,
    HypothesisStatus,
    ReasoningState,
    create_reasoning_state,
)
from core.reasoning_trace import (
    ReasoningTrace,
    TraceEventType,
    reasoning_trace,
)
from core.repair_planner import repair_planner
from core.replanning_engine import replanning_engine
from core.verification_engine import VerificationLevel, verification_engine


class ProblemSolver:
    """
    Autonomous problem solver with bounded reasoning cycles and multi-tiered outcome verification.
    """

    MAX_REASONING_CYCLES = 5
    MAX_REPAIR_ATTEMPTS = 3

    async def solve_goal_async(
        self,
        turn_id: str,
        user_request: str,
        target_project: str,
        target_port: int = 3000,
        verify_tests: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes the full autonomous reasoning and recovery loop.
        """
        # 1. UNDERSTAND & CONTRACT CREATION
        goal = create_goal_contract(
            turn_id=turn_id,
            original_request=user_request,
            normalized_goal=f"Diagnose and restore '{target_project}' to verified operational state",
            desired_outcome=f"'{target_project}' is running and verified on localhost:{target_port}",
            target_project=target_project,
        )
        state = create_reasoning_state(goal=goal, max_cycles=self.MAX_REASONING_CYCLES)

        reasoning_trace.record_event(
            TraceEventType.GOAL_CREATED,
            goal.goal_id,
            {"request": user_request, "target": target_project},
        )
        event_bus.publish(EventType.TASK_STARTED, {"goal_id": goal.goal_id, "project": target_project})

        print(f"[PROBLEM_SOLVER] 🧠 Initiated autonomous solve loop for '{target_project}' (goal_id={goal.goal_id})")

        # 2. OBSERVE INITIAL STATE
        goal.update_status(GoalStatus.OBSERVING)
        obs_data = observation_engine.gather_diagnostic_evidence(target_project, target_port=target_port)
        state.add_observation(obs_data)
        reasoning_trace.record_event(TraceEventType.OBSERVATION_COLLECTED, goal.goal_id, obs_data)

        # 3. CHECK FOR STRONG MATCHING LEARNED SKILLS
        try:
            from core.skill_matcher import skill_matcher
            from core.skill_execution_engine import skill_execution_engine
            from core.skill_reinforcement_engine import skill_reinforcement_engine
            matched_skill = skill_matcher.get_best_match(
                goal_text=user_request,
                project_name=target_project,
            )
            if matched_skill:
                print(f"[PROBLEM_SOLVER] 🎯 Found strong matching skill: '{matched_skill.skill_name}' (conf={matched_skill.confidence:.2f})")
                skill_res = await skill_execution_engine.execute_skill_async(
                    skill=matched_skill,
                    context={"project": target_project, "port": target_port},
                    observation=obs_data,
                    target_port=target_port,
                    verify_tests=verify_tests,
                )
                if skill_res.get("outcome_verified"):
                    skill_reinforcement_engine.on_skill_success(matched_skill.skill_id)
                    goal.mark_completed(skill_res.get("verification", {}))
                    reasoning_trace.record_event(
                        TraceEventType.GOAL_COMPLETED,
                        goal.goal_id,
                        {"summary": f"Resolved using learned skill '{matched_skill.skill_name}'."},
                    )
                    event_bus.publish(EventType.PROJECT_READY, {
                        "project": target_project,
                        "port": target_port,
                        "goal_id": goal.goal_id,
                        "category": matched_skill.problem_pattern or "PORT_CONFLICT",
                    })
                    return {
                        "success": True,
                        "goal_id": goal.goal_id,
                        "project": target_project,
                        "port": target_port,
                        "summary": reasoning_trace.get_summary(goal.goal_id),
                        "verification": skill_res.get("verification"),
                        "used_skill": matched_skill.skill_name,
                    }
                else:
                    skill_reinforcement_engine.on_skill_failure(matched_skill.skill_id, error=skill_res.get("error", "Verification failed"))
                    print("[PROBLEM_SOLVER] ⚠️ Skill execution failed; falling back to normal diagnostic loop.")
        except Exception as e:
            print(f"[PROBLEM_SOLVER] Skill matching note: {e}")

        # 4. GENERATE & RANK HYPOTHESES WITH MEMORY ENRICHMENT
        goal.update_status(GoalStatus.PLANNING)
        hypotheses = hypothesis_engine.generate_hypotheses(target_project, obs_data)

        # Retrieve planning hints from prior experience
        try:
            from core.memory_learning_loop import memory_learning_loop
            memory_hints = memory_learning_loop.get_planning_hints(target_project, obs_data)
            for hint in memory_hints:
                cat = hint.get("category")
                boost = hint.get("confidence_boost", 0.2)
                for h in hypotheses:
                    if h.category == cat:
                        h.add_support("Supported by validated prior experience.", boost=boost)
                        print(f"[PROBLEM_SOLVER] 💡 Hypothesis '{h.category}' boosted by prior experience (+{boost:.2f})")
        except Exception as e:
            print(f"[PROBLEM_SOLVER] Memory enrichment note: {e}")

        for h in hypotheses:
            state.add_hypothesis(h)
            reasoning_trace.record_event(
                TraceEventType.HYPOTHESIS_CREATED,
                goal.goal_id,
                {"category": h.category, "description": h.description, "confidence": h.confidence},
            )

        selected_hyp = state.select_best_hypothesis()
        if not selected_hyp:
            goal.mark_failed("Unable to generate valid diagnostic hypotheses.")
            return {"success": False, "error": goal.failure_reason, "goal_id": goal.goal_id}

        reasoning_trace.record_event(
            TraceEventType.HYPOTHESIS_SELECTED,
            goal.goal_id,
            {"category": selected_hyp.category, "description": selected_hyp.description},
        )

        # 4. BOUNDED SOLVE & RECOVERY LOOP
        repair_attempts = 0

        while state.cycle_count < self.MAX_REASONING_CYCLES:
            state.cycle_count += 1
            print(f"[PROBLEM_SOLVER] 🔄 Reasoning cycle {state.cycle_count}/{self.MAX_REASONING_CYCLES} (Hypothesis: {selected_hyp.category})")

            # 4a. Execute Diagnostic Step
            diag_steps = diagnostic_planner.create_diagnostic_plan(selected_hyp, target_project, target_port)
            for step in diag_steps:
                act = step["action"]
                reasoning_trace.record_event(
                    TraceEventType.ACTION_EXECUTED,
                    goal.goal_id,
                    {"action": act, "target": target_project, "risk": step["risk_level"]},
                )
                await asyncio.sleep(0.05)

            # 4b. Execute Minimal Repair Step
            repair_steps = repair_planner.create_repair_plan(selected_hyp, target_project, obs_data)
            repair_attempts += 1

            for rep_step in repair_steps:
                action_name = rep_step["action"]
                risk_str = rep_step.get("risk_level", "LOW")

                # Action Contract & Approval Safety Check
                risk_enum = RiskLevel.HIGH_RISK if risk_str == "HIGH" else RiskLevel.DESTRUCTIVE if risk_str == "DESTRUCTIVE" else RiskLevel.LOW_RISK
                contract = ActionContract(
                    connector="problem_solver",
                    operation=action_name,
                    arguments={"target": target_project},
                    risk_level=risk_enum,
                )

                # High-risk / destructive actions require approval
                if contract.approval_required:
                    print(f"[PROBLEM_SOLVER] 🛡️ Action '{action_name}' requires user approval.")
                    approval_store.create_proposal(contract)
                    if contract.approval_state != ApprovalState.APPROVED:
                        print(f"[PROBLEM_SOLVER] ❌ Action '{action_name}' not approved.")
                        continue

                # Execute specific repair operations
                if action_name == "terminate_conflicting_processes":
                    # Terminate old processes for project
                    procs = process_manager.list_processes()
                    for p in procs:
                        if p.get("project_name", "").lower() == target_project.lower():
                            process_manager.stop_process(p["process_id"])
                    await asyncio.sleep(0.1)

                elif action_name == "restart_project_server":
                    # Restart via standard project runner
                    await run_project_async(target_project, location_hint="desktop", startup_wait_seconds=4.0)

                reasoning_trace.record_event(
                    TraceEventType.ACTION_EXECUTED,
                    goal.goal_id,
                    {"action": action_name, "target": target_project, "risk": risk_str},
                )

            # 4c. VERIFICATION STEP (Mandatory Outcome Verification)
            goal.update_status(GoalStatus.VERIFYING)
            verification = verification_engine.verify_outcome(
                project_name=target_project,
                target_port=target_port,
                verify_tests=verify_tests,
            )

            if verification["outcome_verified"]:
                goal.mark_completed(verification)
                reasoning_trace.record_event(
                    TraceEventType.VERIFICATION_PASSED,
                    goal.goal_id,
                    verification,
                )
                reasoning_trace.record_event(
                    TraceEventType.GOAL_COMPLETED,
                    goal.goal_id,
                    {"summary": reasoning_trace.get_summary(goal.goal_id)},
                )
                event_bus.publish(EventType.PROJECT_READY, {"project": target_project, "port": target_port, "goal_id": goal.goal_id})
                print(f"[PROBLEM_SOLVER] ✅ Goal '{goal.goal_id}' completed with OUTCOME_VERIFIED on port {target_port}")
                return {
                    "success": True,
                    "goal_id": goal.goal_id,
                    "project": target_project,
                    "port": target_port,
                    "summary": reasoning_trace.get_summary(goal.goal_id),
                    "verification": verification,
                }
            else:
                # 4d. REPLAN STEP
                reasoning_trace.record_event(
                    TraceEventType.VERIFICATION_FAILED,
                    goal.goal_id,
                    verification,
                )
                new_plan = replanning_engine.replan(
                    state=state,
                    failed_action="restart_project_server",
                    error_details=f"Server did not respond on localhost:{target_port}",
                )
                if not new_plan:
                    break
                selected_hyp = state.selected_hypothesis
                if not selected_hyp:
                    break

        # If loop exits without outcome verification
        goal.mark_failed("Exceeded maximum reasoning cycles without achieving OUTCOME_VERIFIED.")
        reasoning_trace.record_event(
            TraceEventType.GOAL_FAILED,
            goal.goal_id,
            {"reason": goal.failure_reason},
        )
        event_bus.publish(EventType.TASK_FAILED, {"goal_id": goal.goal_id, "error": goal.failure_reason})
        return {
            "success": False,
            "goal_id": goal.goal_id,
            "error": goal.failure_reason,
            "summary": reasoning_trace.get_summary(goal.goal_id),
        }


# Global singleton instance
problem_solver = ProblemSolver()
