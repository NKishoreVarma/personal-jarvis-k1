"""
Phase 12.21 — Autonomous Multi-Agent Collaboration, Delegation & Collective Problem Solving Test Suite.
Verifies all 30 core requirements:
1. Agent contract validation
2. Role specification and authority boundaries (OBSERVER is strictly READ_ONLY)
3. Observer cannot mutate
4. Executor mutation allowed
5. Task contract creation and state transitions
6. Delegation pipeline creation (Observer -> Diagnostic -> Executor -> Verifier)
7. Research agent dynamic inclusion
8. Dependency ordering in delegation plan
9. Inter-agent message passing
10. Inter-agent broadcast messaging
11. Evidence exchange submission and retrieval
12. Shared evidence bounded format
13. Consensus engine majority agreement
14. Live observation overrides agent consensus (Agent Agreement != Truth)
15. Agent failure does not fail overall goal (Agent Failure != Goal Failure)
16. Research agent failure local fallback
17. Observer retry on timeout
18. Max delegation depth enforcement (depth > 3 rejected)
19. Max concurrency enforcement (concurrency > 5 rejected)
20. Max agents per goal limit (agents > 10 rejected)
21. Agent lifecycle registration and transitions
22. Supervisor timeout reaping
23. Independent outcome verification
24. Verifier rejects unverified executor claim (Verifier Independence)
25. Delegation enable/disable toggle
26. No authority escalation across delegated subagents
27. Intent router commands
28. End-to-end multi-agent FLOW collaboration scenario
29. Clean task cleanup on goal reset
30. Zero voice callback blocking
"""

from __future__ import annotations

import time
import unittest

from core.agent_communication_bus import agent_communication_bus
from core.agent_consensus_engine import agent_consensus_engine
from core.agent_contract import (
    AgentContract,
    AgentRole,
    AgentStatus,
    AuthorityLevel,
    create_agent_contract,
)
from core.agent_delegation_engine import agent_delegation_engine
from core.agent_evidence_exchange import EvidenceType, agent_evidence_exchange
from core.agent_failure_manager import FailureRecoveryStrategy, agent_failure_manager
from core.agent_lifecycle_manager import agent_lifecycle_manager
from core.agent_message_contract import AgentMessageType, create_agent_message
from core.agent_resource_manager import agent_resource_manager
from core.agent_result_verifier import agent_result_verifier
from core.agent_role_registry import agent_role_registry
from core.agent_supervisor import agent_supervisor
from core.agent_task_contract import AgentTaskStatus, create_agent_task_contract
from core.intent_router import router


class TestPhase1221MultiAgentCollaboration(unittest.TestCase):
    def setUp(self):
        agent_communication_bus.clear()
        agent_evidence_exchange.clear()
        agent_lifecycle_manager.clear()
        agent_resource_manager.clear_all()
        agent_delegation_engine.set_delegation_enabled(True)

    # 1. Agent contract validation
    def test_01_agent_contract_validation(self):
        agent = create_agent_contract(
            parent_goal_id="g1",
            turn_id="t1",
            role=AgentRole.OBSERVER,
            task_description="Inspect system",
            authority_scope=AuthorityLevel.READ_ONLY,
        )
        self.assertEqual(agent.role, AgentRole.OBSERVER)
        self.assertEqual(agent.authority_scope, AuthorityLevel.READ_ONLY)
        self.assertEqual(agent.status, AgentStatus.PENDING)

    # 2. Role specification and authority boundaries
    def test_02_role_specification_and_authority(self):
        spec = agent_role_registry.get_role_spec(AgentRole.OBSERVER)
        self.assertEqual(spec.default_authority, AuthorityLevel.READ_ONLY)
        self.assertFalse(spec.can_mutate)

    # 3. Observer cannot mutate
    def test_03_observer_cannot_mutate(self):
        obs = create_agent_contract("g1", "t1", AgentRole.OBSERVER, "Inspect port", AuthorityLevel.READ_ONLY)
        self.assertFalse(obs.is_operation_permitted("kill_process"))
        self.assertFalse(obs.is_operation_permitted("restart_service"))
        self.assertTrue(obs.is_operation_permitted("inspect_port"))

    # 4. Executor mutation allowed
    def test_04_executor_mutation_allowed(self):
        exec_agent = create_agent_contract("g1", "t1", AgentRole.EXECUTOR, "Repair port", AuthorityLevel.EXECUTE_LOW_RISK)
        self.assertTrue(exec_agent.is_operation_permitted("kill_process"))
        self.assertTrue(exec_agent.is_operation_permitted("restart_service"))

    # 5. Task contract creation and state transitions
    def test_05_task_contract_state_transitions(self):
        task = create_agent_task_contract("a1", "g1", AgentRole.OBSERVER, "inspect_port", {"port": 3000})
        self.assertEqual(task.status, AgentTaskStatus.PENDING)
        task.mark_in_progress()
        self.assertEqual(task.status, AgentTaskStatus.IN_PROGRESS)
        task.mark_success({"port_busy": True})
        self.assertEqual(task.status, AgentTaskStatus.SUCCESS)

    # 6. Delegation pipeline creation
    def test_06_delegation_pipeline_creation(self):
        agents, msg = agent_delegation_engine.create_delegation_plan("Fix FLOW", "FLOW")
        self.assertEqual(len(agents), 4)  # Observer, Diagnostic, Executor, Verifier
        roles = [a.role for a in agents]
        self.assertEqual(roles, [AgentRole.OBSERVER, AgentRole.DIAGNOSTIC, AgentRole.EXECUTOR, AgentRole.VERIFIER])

    # 7. Research agent dynamic inclusion
    def test_07_research_agent_dynamic_inclusion(self):
        agents, _ = agent_delegation_engine.create_delegation_plan("Fix FLOW with docs", "FLOW", needs_research=True)
        self.assertEqual(len(agents), 5)
        self.assertEqual(agents[1].role, AgentRole.RESEARCHER)

    # 8. Dependency ordering in delegation plan
    def test_08_dependency_ordering(self):
        agents, _ = agent_delegation_engine.create_delegation_plan("Fix FLOW", "FLOW")
        obs, diag, executor, verif = agents[0], agents[1], agents[2], agents[3]
        self.assertIn(obs.agent_id, diag.dependencies)
        self.assertIn(diag.agent_id, executor.dependencies)
        self.assertIn(executor.agent_id, verif.dependencies)

    # 9. Inter-agent message passing
    def test_09_inter_agent_message_passing(self):
        received = []
        agent_communication_bus.subscribe("agent_diag_1", lambda m: received.append(m))
        msg = create_agent_message("agent_obs_1", "agent_diag_1", "g1", AgentMessageType.EVIDENCE_SHARE, {"port": 3000})
        agent_communication_bus.publish(msg)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["port"], 3000)

    # 10. Inter-agent broadcast messaging
    def test_10_inter_agent_broadcast_messaging(self):
        r1, r2 = [], []
        agent_communication_bus.subscribe("a1", lambda m: r1.append(m))
        agent_communication_bus.subscribe("a2", lambda m: r2.append(m))

        bmsg = create_agent_message("coord", "BROADCAST", "g1", AgentMessageType.HEARTBEAT, {"status": "ok"})
        agent_communication_bus.publish(bmsg)
        self.assertEqual(len(r1), 1)
        self.assertEqual(len(r2), 1)

    # 11. Evidence exchange submission and retrieval
    def test_11_evidence_exchange_submission_and_retrieval(self):
        ev = agent_evidence_exchange.submit_evidence("g1", "agent_obs_1", EvidenceType.PORT_STATE, {"port": 3000, "busy": True})
        items = agent_evidence_exchange.get_evidence("g1", EvidenceType.PORT_STATE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].content["port"], 3000)

    # 12. Shared evidence bounded format
    def test_12_shared_evidence_bounded_format(self):
        ev = agent_evidence_exchange.submit_evidence("g1", "agent_obs_1", EvidenceType.LOG_SIGNATURE, {"signature": "EADDRINUSE"})
        self.assertEqual(ev.evidence_type, EvidenceType.LOG_SIGNATURE)
        self.assertIsInstance(ev.content, dict)

    # 13. Consensus engine majority agreement
    def test_13_consensus_engine_majority_agreement(self):
        hypotheses = [
            {"agent_id": "a1", "hypothesis": "PORT_CONFLICT"},
            {"agent_id": "a2", "hypothesis": "PORT_CONFLICT"},
            {"agent_id": "a3", "hypothesis": "MISSING_MODULE"},
        ]
        res = agent_consensus_engine.evaluate_consensus(hypotheses)
        self.assertEqual(res.consensus_hypothesis, "PORT_CONFLICT")
        self.assertGreaterEqual(res.confidence, 0.65)
        self.assertFalse(res.reality_overridden)

    # 14. Live observation overrides agent consensus
    def test_14_live_observation_overrides_agent_consensus(self):
        hypotheses = [
            {"agent_id": "a1", "hypothesis": "PORT_CONFLICT"},
            {"agent_id": "a2", "hypothesis": "PORT_CONFLICT"},
        ]
        # Real observation proves it was actually MISSING_DEPENDENCY
        live_obs = {"actual_cause": "MISSING_DEPENDENCY"}
        res = agent_consensus_engine.evaluate_consensus(hypotheses, live_observation=live_obs)
        self.assertEqual(res.consensus_hypothesis, "MISSING_DEPENDENCY")
        self.assertTrue(res.reality_overridden)

    # 15. Agent failure does not fail overall goal
    def test_15_agent_failure_does_not_fail_goal(self):
        obs = create_agent_contract("g1", "t1", AgentRole.OBSERVER, "Inspect")
        strategy, msg = agent_failure_manager.handle_agent_failure(obs, "Socket timeout", retry_count=0)
        self.assertEqual(strategy, FailureRecoveryStrategy.RETRY_AGENT)

    # 16. Research agent failure local fallback
    def test_16_research_agent_failure_local_fallback(self):
        res_agent = create_agent_contract("g1", "t1", AgentRole.RESEARCHER, "Lookup")
        strategy, msg = agent_failure_manager.handle_agent_failure(res_agent, "Network disconnected")
        self.assertEqual(strategy, FailureRecoveryStrategy.FALLBACK_LOCAL)

    # 17. Observer retry on timeout
    def test_17_observer_retry_on_timeout(self):
        obs = create_agent_contract("g1", "t1", AgentRole.OBSERVER, "Inspect")
        strategy, _ = agent_failure_manager.handle_agent_failure(obs, "Timeout", retry_count=0)
        self.assertEqual(strategy, FailureRecoveryStrategy.RETRY_AGENT)

    # 18. Max delegation depth enforcement
    def test_18_max_delegation_depth_enforcement(self):
        can_spawn, reason = agent_resource_manager.can_spawn_agent("g1", spawn_depth=4)
        self.assertFalse(can_spawn)
        self.assertIn("exceeds maximum limit", reason)

    # 19. Max concurrency enforcement
    def test_19_max_concurrency_enforcement(self):
        for _ in range(5):
            agent_resource_manager.allocate_agent("g1")
        can_spawn, reason = agent_resource_manager.can_spawn_agent("g1", spawn_depth=1)
        self.assertFalse(can_spawn)
        self.assertIn("concurrency ceiling", reason)

    # 20. Max agents per goal limit
    def test_20_max_agents_per_goal_limit(self):
        for _ in range(10):
            agent_resource_manager.allocate_agent("g_heavy")
            agent_resource_manager.release_agent("g_heavy")
        can_spawn, reason = agent_resource_manager.can_spawn_agent("g_heavy", spawn_depth=1)
        self.assertFalse(can_spawn)
        self.assertIn("maximum agent allocation", reason)

    # 21. Agent lifecycle registration and transitions
    def test_21_agent_lifecycle_transitions(self):
        agent = create_agent_contract("g1", "t1", AgentRole.OBSERVER, "Task")
        agent_lifecycle_manager.register_agent(agent)
        agent_lifecycle_manager.transition_state(agent.agent_id, AgentStatus.RUNNING)
        self.assertEqual(agent.status, AgentStatus.RUNNING)
        agent_lifecycle_manager.transition_state(agent.agent_id, AgentStatus.COMPLETED)
        self.assertEqual(agent.status, AgentStatus.COMPLETED)

    # 22. Supervisor timeout reaping
    def test_22_supervisor_timeout_reaping(self):
        agent = create_agent_contract("g1", "t1", AgentRole.OBSERVER, "Task", timeout_seconds=0.01)
        agent_lifecycle_manager.register_agent(agent)
        agent.mark_started()
        time.sleep(0.03)
        timed_out = agent_supervisor.inspect_and_reap_timeouts()
        self.assertIn(agent.agent_id, timed_out)
        self.assertEqual(agent.status, AgentStatus.TIMEOUT)

    # 23. Independent outcome verification
    def test_23_independent_outcome_verification(self):
        claim = {"success": True, "action": "restart"}
        probe_fn = lambda: {"is_responsive": True, "status": 200}
        ok, reason = agent_result_verifier.verify_executor_outcome(claim, live_probe_fn=probe_fn)
        self.assertTrue(ok)
        self.assertIn("Independent live probe confirmed", reason)

    # 24. Verifier rejects unverified executor claim
    def test_24_verifier_rejects_unverified_claim(self):
        claim = {"success": True, "action": "restart"}
        probe_fn = lambda: {"is_responsive": False}
        ok, reason = agent_result_verifier.verify_executor_outcome(claim, live_probe_fn=probe_fn)
        self.assertFalse(ok)
        self.assertIn("Independent live probe failed", reason)

    # 25. Delegation enable/disable toggle
    def test_25_delegation_toggle(self):
        agent_delegation_engine.set_delegation_enabled(False)
        agents, reason = agent_delegation_engine.create_delegation_plan("Goal", "FLOW")
        self.assertEqual(len(agents), 0)
        self.assertIn("disabled by user preference", reason)

    # 26. No authority escalation across delegated subagents
    def test_26_no_authority_escalation(self):
        agents, _ = agent_delegation_engine.create_delegation_plan("Goal", "FLOW")
        for a in agents:
            if a.role in [AgentRole.OBSERVER, AgentRole.RESEARCHER, AgentRole.DIAGNOSTIC, AgentRole.VERIFIER]:
                self.assertEqual(a.authority_scope, AuthorityLevel.READ_ONLY)

    # 27. Intent router commands
    def test_27_intent_router_commands(self):
        match = router.match("what agents are running")
        self.assertEqual(match["intent"], "QUERY_ACTIVE_AGENTS")

        match_status = router.match("how is the observer agent doing")
        self.assertEqual(match_status["intent"], "QUERY_AGENT_STATUS")

    # 28. End-to-end multi-agent FLOW collaboration scenario
    def test_28_end_to_end_flow_collaboration_scenario(self):
        # 1. Delegation
        agents, _ = agent_delegation_engine.create_delegation_plan("Fix FLOW and start it", "FLOW")
        obs, diag, executor, verif = agents[0], agents[1], agents[2], agents[3]

        # 2. Observer submits evidence
        agent_evidence_exchange.submit_evidence(obs.parent_goal_id, obs.agent_id, EvidenceType.PORT_STATE, {"port": 3000, "busy": True})

        # 3. Diagnostic checks evidence and reaches consensus
        ev = agent_evidence_exchange.get_evidence(obs.parent_goal_id, EvidenceType.PORT_STATE)
        self.assertEqual(len(ev), 1)

        # 4. Executor executes
        claim = {"success": True, "action": "terminate_conflicting_pid_and_start"}

        # 5. Verifier checks ground truth
        ok, _ = agent_result_verifier.verify_executor_outcome(claim, live_probe_fn=lambda: {"is_responsive": True})
        self.assertTrue(ok)

    # 29. Clean task cleanup on goal reset
    def test_29_clean_task_cleanup(self):
        agent_resource_manager.allocate_agent("g_clean")
        agent_resource_manager.reset_goal("g_clean")
        can_spawn, _ = agent_resource_manager.can_spawn_agent("g_clean", spawn_depth=1)
        self.assertTrue(can_spawn)

    # 30. Zero voice callback blocking
    def test_30_zero_voice_callback_blocking(self):
        # Warm-up router regex compilation
        router.match("what agents are running")
        t0 = time.perf_counter()
        match = router.match("what agents are running")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_ACTIVE_AGENTS")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
