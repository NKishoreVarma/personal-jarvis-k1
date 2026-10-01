"""
Agent Role Registry for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Defines role specifications, authority bounds, tool capabilities, and permissions for specialized agents.
Enforces invariant: Observer != Executor (Observer is strictly READ_ONLY).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.agent_contract import AgentRole, AuthorityLevel


@dataclass
class RoleSpecification:
    role: AgentRole
    description: str
    default_authority: AuthorityLevel
    allowed_operations: List[str] = field(default_factory=list)
    forbidden_operations: List[str] = field(default_factory=list)
    can_mutate: bool = False
    can_verify: bool = False


class AgentRoleRegistry:
    """
    Registry of specialized multi-agent roles and their default authority boundaries.
    """

    def __init__(self):
        self._roles: Dict[AgentRole, RoleSpecification] = {}
        self._register_default_roles()

    def _register_default_roles(self) -> None:
        # 1. OBSERVER
        self._roles[AgentRole.OBSERVER] = RoleSpecification(
            role=AgentRole.OBSERVER,
            description="Inspects active processes, open ports, system metrics, and local error logs.",
            default_authority=AuthorityLevel.READ_ONLY,
            allowed_operations=["inspect_port", "read_logs", "check_process", "query_status", "observe_screen"],
            forbidden_operations=["kill_process", "write_file", "restart_service", "apply_patch", "delete_file"],
            can_mutate=False,
            can_verify=False,
        )

        # 2. RESEARCHER
        self._roles[AgentRole.RESEARCHER] = RoleSpecification(
            role=AgentRole.RESEARCHER,
            description="Retrieves official documentation, packages configs, and technical articles for knowledge gaps.",
            default_authority=AuthorityLevel.READ_ONLY,
            allowed_operations=["search_documentation", "query_knowledge", "check_package_config", "query_cache"],
            forbidden_operations=["kill_process", "write_file", "restart_service", "apply_patch"],
            can_mutate=False,
            can_verify=False,
        )

        # 3. DIAGNOSTIC
        self._roles[AgentRole.DIAGNOSTIC] = RoleSpecification(
            role=AgentRole.DIAGNOSTIC,
            description="Analyzes observer and researcher evidence to isolate root causes and propose hypotheses.",
            default_authority=AuthorityLevel.READ_ONLY,
            allowed_operations=["analyze_error", "corroborate_evidence", "compare_traces", "formulate_hypothesis"],
            forbidden_operations=["kill_process", "restart_service", "write_file"],
            can_mutate=False,
            can_verify=False,
        )

        # 4. EXECUTOR
        self._roles[AgentRole.EXECUTOR] = RoleSpecification(
            role=AgentRole.EXECUTOR,
            description="Applies verified and approved repair actions through ActionContract and ApprovalStore.",
            default_authority=AuthorityLevel.EXECUTE_LOW_RISK,
            allowed_operations=["kill_process", "restart_service", "apply_patch", "start_process"],
            forbidden_operations=["delete_database", "format_drive", "override_security_policy"],
            can_mutate=True,
            can_verify=False,
        )

        # 5. VERIFIER
        self._roles[AgentRole.VERIFIER] = RoleSpecification(
            role=AgentRole.VERIFIER,
            description="Independently probes live environment to confirm verified operational outcomes.",
            default_authority=AuthorityLevel.READ_ONLY,
            allowed_operations=["probe_http", "check_port_responsiveness", "verify_output", "ping_endpoint"],
            forbidden_operations=["kill_process", "write_file", "restart_service"],
            can_mutate=False,
            can_verify=True,
        )

        # 6. COORDINATOR
        self._roles[AgentRole.COORDINATOR] = RoleSpecification(
            role=AgentRole.COORDINATOR,
            description="Synthesizes multi-agent evidence, resolves conflicts, and controls task execution DAG.",
            default_authority=AuthorityLevel.PREPARE_ONLY,
            allowed_operations=["delegate_task", "synthesize_evidence", "resolve_conflicts", "schedule_dag"],
            forbidden_operations=["kill_process", "direct_mutation"],
            can_mutate=False,
            can_verify=False,
        )

        # 7. PLANNER
        self._roles[AgentRole.PLANNER] = RoleSpecification(
            role=AgentRole.PLANNER,
            description="Decomposes high-level objectives into executable multi-agent dependency graphs.",
            default_authority=AuthorityLevel.PREPARE_ONLY,
            allowed_operations=["decompose_goal", "score_strategies", "create_task_graph"],
            forbidden_operations=["direct_mutation"],
            can_mutate=False,
            can_verify=False,
        )

    def get_role_spec(self, role: AgentRole) -> RoleSpecification:
        return self._roles[role]

    def is_mutation_allowed(self, role: AgentRole) -> bool:
        spec = self._roles.get(role)
        return spec.can_mutate if spec else False


# Global singleton instance
agent_role_registry = AgentRoleRegistry()
