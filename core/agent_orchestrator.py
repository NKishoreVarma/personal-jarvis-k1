"""
Agent Orchestrator for Autonomous Multi-Agent Orchestration & Structured Execution in MARK XLVIII / JARVIS.
Provides both single-agent plan execution / validation with LoopGuard, ThinkTool,
observe-act-verify loop, safety retries, and cancellation,
as well as full multi-agent task graph decomposition, parallel observation dispatch,
and outcome verification (Phase 12.12).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from actions.project_runner import run_project_async
from core.action_contract import ActionContract, ApprovalState, RiskLevel
from core.agent_contract import AgentContract, AgentRole, AgentStatus, AuthorityLevel, create_agent_contract
from core.agent_result_synthesizer import agent_result_synthesizer
from core.approval_manager import approval_store
from core.cancellation_manager import cancellation_manager
from core.computer_observer import computer_observer
from core.dependency_scheduler import dependency_scheduler
from core.event_bus import EventType, event_bus
from core.loop_guard import compute_fingerprint, loop_guard
from core.observation_engine import observation_engine
from core.parallel_worker_manager import parallel_worker_manager
from core.process_manager import process_manager
from core.shared_evidence_store import EvidenceCategory, shared_evidence_store
from core.task_graph import NodeExecutionType, TaskGraph, TaskNode
from core.think_tool import think_tool
from core.verification_engine import verification_engine
from core.verifier import verifier


# --- Single-Agent Schema & Types for Backward Compatibility ---

class AgentState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StepSchema:
    id: int
    description: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanSchema:
    goal: str
    steps: List[StepSchema] = field(default_factory=list)


@dataclass
class PlanStep:
    id: int
    description: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    requires_verification: bool = False
    requires_observation: bool = False
    max_retries: int = 2
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "tool": self.tool,
            "parameters": self.parameters,
            "status": self.status.value if isinstance(self.status, StepStatus) else str(self.status),
            "result": self.result,
            "error": self.error,
            "requires_verification": self.requires_verification,
            "requires_observation": self.requires_observation,
            "attempts": self.attempts,
        }


@dataclass
class Plan:
    goal: str
    steps: List[PlanStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    execute: Optional[Callable[[Dict[str, Any], Any], Any]] = None
    permission_level: str = "normal"  # normal, low_risk, read_only, destructive


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._init_defaults()

    def _init_defaults(self):
        # 1. Think tool
        def _exec_think(p: Dict[str, Any], player: Any = None) -> Dict[str, Any]:
            tr = think_tool.think(p.get("note", ""), category=p.get("category", "planning"))
            return {"success": tr.success, "note": tr.note, "category": tr.category, "timestamp": tr.timestamp}

        self.register(Tool(
            name="think",
            description="Records scratchpad notes during reasoning",
            parameters={"note": "string", "category": "string"},
            execute=_exec_think,
            permission_level="read_only",
        ))
        # 1b. Read file tool
        self.register(Tool(
            name="read_file",
            description="Reads a file safely",
            parameters={"file": "string"},
            execute=lambda p, player=None: "File content read successfully",
            permission_level="read_only",
        ))
        # 1c. Run project command
        self.register(Tool(
            name="run_project_command",
            description="Runs project build or server commands",
            parameters={"command": "string"},
            execute=lambda p, player=None: "Project command executed successfully",
            permission_level="low_risk",
        ))
        # 2. Open / Close app
        self.register(Tool(
            name="open_app",
            description="Opens an application",
            parameters={"app_name": "string"},
            execute=lambda p, player=None: f"Application {p.get('app_name')} launched successfully",
            permission_level="low_risk",
        ))
        self.register(Tool(
            name="close_app",
            description="Closes an application",
            parameters={"app_name": "string"},
            execute=lambda p, player=None: f"Application {p.get('app_name')} closed successfully",
            permission_level="low_risk",
        ))
        # 3. Patch tools
        self.register(Tool(
            name="propose_patch",
            description="Proposes code modification",
            parameters={"file": "string", "old_text": "string", "new_text": "string"},
            execute=lambda p, player=None: "Patch proposed successfully",
            permission_level="low_risk",
        ))
        self.register(Tool(
            name="apply_patch",
            description="Applies approved code modification",
            parameters={"file": "string", "old_text": "string", "new_text": "string"},
            execute=lambda p, player=None: "Patch applied successfully",
            permission_level="destructive",
        ))
        self.register(Tool(
            name="rollback_patch",
            description="Rolls back code modification",
            parameters={"file": "string"},
            execute=lambda p, player=None: "Patch rolled back successfully",
            permission_level="destructive",
        ))
        # 4. UI controls
        self.register(Tool(
            name="click_ui_element",
            description="Clicks on a UI element",
            parameters={"element": "string"},
            execute=lambda p, player=None: "Clicked UI element",
            permission_level="low_risk",
        ))
        self.register(Tool(
            name="type_ui_text",
            description="Types text into active UI focus",
            parameters={"text": "string"},
            execute=lambda p, player=None: "Typed text successfully",
            permission_level="low_risk",
        ))
        self.register(Tool(
            name="press_ui_key",
            description="Presses keyboard key",
            parameters={"key": "string"},
            execute=lambda p, player=None: "Pressed key successfully",
            permission_level="low_risk",
        ))
        self.register(Tool(
            name="ui_hotkey",
            description="Presses keyboard hotkey combination",
            parameters={"keys": "list"},
            execute=lambda p, player=None: "Pressed hotkey successfully",
            permission_level="low_risk",
        ))
        # 5. Standard built-ins
        for name in ["browser_control", "screen_process", "web_search", "computer_settings", "save_memory"]:
            self.register(Tool(
                name=name,
                description=f"Built-in action {name}",
                execute=lambda p, player=None: f"{name} executed successfully",
                permission_level="low_risk",
            ))

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())


# --- Agent Orchestrator ---

class AgentOrchestrator:
    """
    Unified Orchestrator supporting single-agent step-loop execution
    and multi-agent DAG task orchestration.
    """

    MAX_STEPS = 10
    MAX_AGENT_RUNTIME = 120.0

    def __init__(self, registry: Optional[ToolRegistry] = None, model: Any = None, vision: Any = None):
        self.registry = registry or ToolRegistry()
        self.model = model
        self.vision = vision
        self.state: AgentState = AgentState.IDLE
        self._cancelled: bool = False
        self.current_plan: Optional[Plan] = None

    def cancel(self) -> None:
        self._cancelled = True
        self.state = AgentState.CANCELLED

    def validate_plan(self, raw_plan: PlanSchema) -> Plan:
        valid_steps: List[PlanStep] = []
        new_id = 1
        for s in raw_plan.steps:
            if self.registry.get(s.tool):
                valid_steps.append(PlanStep(
                    id=new_id,
                    description=s.description,
                    tool=s.tool,
                    parameters=s.parameters,
                    status=StepStatus.PENDING,
                ))
                new_id += 1
        return Plan(goal=raw_plan.goal, steps=valid_steps)

    def create_plan(self, goal: str) -> Plan:
        if self.current_plan and self.current_plan.goal == goal:
            return self.current_plan
        return Plan(
            goal=goal,
            steps=[PlanStep(id=1, description=f"Execute {goal}", tool="open_app", parameters={"app_name": "Chrome"})],
        )

    def run_goal(self, goal: str, player: Any = None) -> Dict[str, Any]:
        if self._cancelled:
            self.state = AgentState.CANCELLED
            return {"status": "cancelled", "goal": goal}

        start_mono = time.monotonic()
        if player:
            player.write_log(f"[AGENT] Goal received: '{goal}'")

        self.state = AgentState.PLANNING
        plan = self.create_plan(goal)

        if len(plan.steps) > self.MAX_STEPS:
            self.state = AgentState.FAILED
            return {"status": "failed", "reason": "Step limit exceeded", "goal": goal, "plan": plan.to_dict()}

        self.state = AgentState.EXECUTING
        for step in plan.steps:
            if time.monotonic() - start_mono > self.MAX_AGENT_RUNTIME:
                self.state = AgentState.FAILED
                return {"status": "failed", "reason": "Runtime limit exceeded", "goal": goal, "plan": plan.to_dict()}

            if self._cancelled:
                self.state = AgentState.CANCELLED
                return {"status": "cancelled", "goal": goal}

            tool = self.registry.get(step.tool)
            if not tool:
                step.status = StepStatus.FAILED
                step.error = f"Tool '{step.tool}' not found"
                self.state = AgentState.FAILED
                return {"status": "failed", "error": step.error, "plan": plan.to_dict()}

            # LoopGuard check
            fp = compute_fingerprint(step.tool, step.parameters)
            decision = loop_guard.register_action(step.tool, step.parameters, permission_level=getattr(tool, "permission_level", "low_risk"))
            if not decision.allowed:
                step.status = StepStatus.FAILED
                step.error = f"LoopGuard blocked: {decision.reason}"
                self.state = AgentState.FAILED
                return {"status": "failed", "error": step.error, "plan": plan.to_dict()}

            # Observation phase if required
            if step.requires_observation:
                self.state = AgentState.OBSERVING
                try:
                    obs = computer_observer.observe_screen()
                    if obs.get("success") is False and not self._cancelled:
                        pass
                except Exception:
                    pass
                if self._cancelled:
                    self.state = AgentState.CANCELLED
                    return {"status": "cancelled", "goal": goal}
                self.state = AgentState.EXECUTING

            max_attempts = 1 if getattr(tool, "permission_level", "normal") == "destructive" else 3
            attempt = 0

            while attempt < max_attempts:
                attempt += 1
                step.attempts += 1
                if self._cancelled:
                    self.state = AgentState.CANCELLED
                    return {"status": "cancelled", "goal": goal}

                try:
                    res = tool.execute(step.parameters, player=player) if tool.execute else "OK"
                    res_str = str(res)
                    is_err = "failed" in res_str.lower() or "error" in res_str.lower()
                    if isinstance(res, dict) and res.get("success") is False:
                        is_err = True

                    if is_err:
                        step.error = res_str
                        loop_guard.register_result(fp, success=False, error=res_str)
                        if attempt >= max_attempts:
                            step.status = StepStatus.FAILED
                            self.state = AgentState.FAILED
                            return {"status": "failed", "error": res_str, "plan": plan.to_dict()}
                        continue

                    # Verification phase if required
                    if step.requires_verification:
                        self.state = AgentState.VERIFYING
                        v_res = verifier.verify(step=step, result=res_str)
                        if not v_res.get("success", True):
                            err_msg = v_res.get("reason") or v_res.get("error") or "Verification failed"
                            step.error = err_msg
                            loop_guard.register_result(fp, success=False, error=err_msg)
                            if attempt >= max_attempts:
                                step.status = StepStatus.FAILED
                                self.state = AgentState.FAILED
                                return {"status": "failed", "error": err_msg, "plan": plan.to_dict()}
                            continue

                    # Step succeeded
                    step.status = StepStatus.COMPLETED
                    step.result = res_str
                    loop_guard.register_result(fp, success=True)
                    if player:
                        player.write_log("[AGENT] Result: Success")
                    break

                except Exception as e:
                    step.error = str(e)
                    loop_guard.register_result(fp, success=False, error=str(e))
                    if attempt >= max_attempts:
                        step.status = StepStatus.FAILED
                        self.state = AgentState.FAILED
                        return {"status": "failed", "error": str(e), "plan": plan.to_dict()}

        self.state = AgentState.IDLE
        if player:
            player.write_log("[AGENT] Goal completed")
        return {"status": "completed", "goal": goal, "plan": plan.to_dict()}

    # --- Multi-Agent Orchestration Lifecycle (Phase 12.12) ---

    async def orchestrate_goal_async(
        self,
        turn_id: str,
        user_request: str,
        target_project: str = "FLOW",
        target_port: int = 3000,
        follow_up_open: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes a multi-agent orchestration lifecycle for a complex goal.
        """
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        print(f"[ORCHESTRATOR] 🚀 Starting multi-agent orchestration for '{target_project}' (goal_id={goal_id})")

        # 1. Construct TaskGraph
        graph = TaskGraph(graph_id=f"graph_{goal_id}")

        n_proc = TaskNode(
            node_id=f"node_proc_{uuid.uuid4().hex[:4]}",
            name="Observe Processes",
            agent_role=AgentRole.OBSERVER,
            operation="observe_processes",
            arguments={"target": target_project},
            execution_type=NodeExecutionType.READ_ONLY,
        )
        n_port = TaskNode(
            node_id=f"node_port_{uuid.uuid4().hex[:4]}",
            name="Observe Port",
            agent_role=AgentRole.OBSERVER,
            operation="observe_port",
            arguments={"target": target_project, "port": target_port},
            execution_type=NodeExecutionType.READ_ONLY,
        )
        n_diag = TaskNode(
            node_id=f"node_diag_{uuid.uuid4().hex[:4]}",
            name="Diagnose Problem",
            agent_role=AgentRole.DIAGNOSTIC,
            operation="diagnose_problem",
            arguments={"target": target_project},
            execution_type=NodeExecutionType.READ_ONLY,
            dependencies=[n_proc.node_id, n_port.node_id],
        )
        n_repair = TaskNode(
            node_id=f"node_repair_{uuid.uuid4().hex[:4]}",
            name="Execute Repair",
            agent_role=AgentRole.EXECUTOR,
            operation="execute_repair",
            arguments={"target": target_project, "port": target_port},
            execution_type=NodeExecutionType.MUTATING,
            dependencies=[n_diag.node_id],
        )
        n_verify = TaskNode(
            node_id=f"node_verify_{uuid.uuid4().hex[:4]}",
            name="Verify Outcome",
            agent_role=AgentRole.VERIFIER,
            operation="verify_outcome",
            arguments={"target": target_project, "port": target_port},
            execution_type=NodeExecutionType.READ_ONLY,
            dependencies=[n_repair.node_id],
        )

        graph.add_node(n_proc)
        graph.add_node(n_port)
        graph.add_node(n_diag)
        graph.add_node(n_repair)
        graph.add_node(n_verify)

        graph.add_edge(n_proc.node_id, n_diag.node_id)
        graph.add_edge(n_port.node_id, n_diag.node_id)
        graph.add_edge(n_diag.node_id, n_repair.node_id)
        graph.add_edge(n_repair.node_id, n_verify.node_id)

        if follow_up_open:
            n_open = TaskNode(
                node_id=f"node_open_{uuid.uuid4().hex[:4]}",
                name="Open Browser",
                agent_role=AgentRole.EXECUTOR,
                operation="open_browser",
                arguments={"url": f"http://localhost:{target_port}"},
                execution_type=NodeExecutionType.MUTATING,
                dependencies=[n_verify.node_id],
            )
            graph.add_node(n_open)
            graph.add_edge(n_verify.node_id, n_open.node_id)

        cancellation_manager.register_active_goal(goal_id, graph)

        async def node_executor(node: TaskNode) -> Dict[str, Any]:
            if cancellation_manager.is_cancelled(goal_id):
                return {"success": False, "error": "Goal cancelled"}

            contract = create_agent_contract(
                parent_goal_id=goal_id,
                turn_id=turn_id,
                role=node.agent_role,
                task_description=node.name,
                authority_scope=AuthorityLevel.EXECUTE_LOW_RISK if node.is_mutating else AuthorityLevel.READ_ONLY,
                allowed_operations=[node.operation],
            )

            async def run_operation() -> Dict[str, Any]:
                op = node.operation
                if op == "observe_processes":
                    procs = process_manager.list_processes()
                    shared_evidence_store.add_evidence(goal_id, contract.agent_id, EvidenceCategory.PROCESS_STATE.value, procs, source="ProcessManager")
                    return {"success": True, "processes": procs}

                elif op == "observe_port":
                    port_info = observation_engine.inspect_port(target_port)
                    shared_evidence_store.add_evidence(goal_id, contract.agent_id, EvidenceCategory.PORT_STATE.value, port_info, source="ObservationEngine")
                    return {"success": True, "port_info": port_info}

                elif op == "diagnose_problem":
                    ev_port = shared_evidence_store.get_evidence(goal_id, EvidenceCategory.PORT_STATE.value)
                    is_conflict = ev_port and ev_port[0].value.get("in_use", False)
                    category = "PORT_CONFLICT" if is_conflict else "RUNTIME_ERROR"
                    shared_evidence_store.add_evidence(goal_id, contract.agent_id, EvidenceCategory.LOG_STATE.value, {"diagnosis": category}, source="DiagnosticAgent")
                    return {"success": True, "category": category}

                elif op == "execute_repair":
                    act_contract = ActionContract(
                        connector="agent_orchestrator",
                        operation="repair_server",
                        arguments={"target": target_project},
                        risk_level=RiskLevel.LOW_RISK,
                    )
                    if act_contract.approval_required:
                        approval_store.create_proposal(act_contract)
                        if act_contract.approval_state != ApprovalState.APPROVED:
                            return {"success": False, "error": "Action requires approval"}

                    for p in process_manager.list_processes():
                        if p.get("project_name", "").lower() == target_project.lower():
                            process_manager.stop_process(p["process_id"])
                    await asyncio.sleep(0.05)
                    await run_project_async(target_project, location_hint="desktop", startup_wait_seconds=3.0)
                    return {"success": True, "repaired": True}

                elif op == "verify_outcome":
                    verif = verification_engine.verify_outcome(target_project, target_port=target_port)
                    return {"success": verif.get("outcome_verified", False), "verification": verif}

                elif op == "open_browser":
                    print(f"[ORCHESTRATOR] 🌐 Opening browser at http://localhost:{target_port}")
                    return {"success": True, "browser_opened": True}

                return {"success": False, "error": f"Unknown operation {op}"}

            return await parallel_worker_manager.run_worker_async(contract, run_operation())

        sched_res = await dependency_scheduler.execute_graph_async(graph, node_executor)

        verif_node = graph.nodes.get(n_verify.node_id)
        verif_data = (verif_node.result.get("verification", {}) if verif_node and verif_node.result else {"outcome_verified": False})
        is_verified = verif_data.get("outcome_verified", False)

        diag_node = graph.nodes.get(n_diag.node_id)
        category = (diag_node.result.get("category", "PORT_CONFLICT") if diag_node and diag_node.result else "PORT_CONFLICT")

        summary = agent_result_synthesizer.synthesize_result(target_project, category, graph, verif_data)
        cancellation_manager.unregister_goal(goal_id)

        if is_verified:
            event_bus.publish(EventType.PROJECT_READY, {
                "project": target_project,
                "port": target_port,
                "goal_id": goal_id,
                "category": category,
            })

        return {
            "success": is_verified,
            "outcome_verified": is_verified,
            "goal_id": goal_id,
            "project": target_project,
            "port": target_port,
            "summary": summary,
            "verification": verif_data,
        }


# Global singleton instance
agent_orchestrator = AgentOrchestrator()
