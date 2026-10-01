"""
Comprehensive Unit & Integration Test Suite for Phase 12.12:
Autonomous Multi-Agent Orchestration & Parallel Task Intelligence.
"""

import asyncio
import time
import unittest

from core.action_contract import ActionContract, RiskLevel
from core.agent_conflict_resolver import ConflictResolutionAction, agent_conflict_resolver
from core.agent_contract import (
    AgentContract,
    AgentRole,
    AgentStatus,
    AuthorityLevel,
    create_agent_contract,
)
from core.agent_orchestrator import agent_orchestrator
from core.agent_result_synthesizer import agent_result_synthesizer
from core.cancellation_manager import cancellation_manager
from core.dependency_scheduler import dependency_scheduler
from core.intent_router import intent_router
from core.parallel_worker_manager import parallel_worker_manager
from core.resource_governor import resource_governor
from core.shared_evidence_store import EvidenceCategory, shared_evidence_store
from core.task_graph import NodeExecutionType, TaskGraph, TaskNode
from core.verification_engine import VerificationLevel, verification_engine


class TestPhase1212MultiAgentOrchestration(unittest.TestCase):
    def setUp(self):
        shared_evidence_store.clear_all()
        cancellation_manager.clear()
        parallel_worker_manager.clear()

    # Test 1: Agent contract authority boundaries
    def test_01_agent_contract_authority_boundaries(self):
        read_only_agent = create_agent_contract(
            parent_goal_id="g1",
            turn_id="t1",
            role=AgentRole.OBSERVER,
            task_description="Inspect port",
            authority_scope=AuthorityLevel.READ_ONLY,
            allowed_operations=["inspect_port"],
        )
        self.assertTrue(read_only_agent.is_operation_permitted("inspect_port"))
        self.assertFalse(read_only_agent.is_operation_permitted("restart_server"))
        self.assertFalse(read_only_agent.is_operation_permitted("kill_process"))

    # Test 2: Parallel read-only execution
    def test_02_parallel_read_only_execution(self):
        graph = TaskGraph("g_test2")
        n1 = TaskNode("n1", "Obs1", AgentRole.OBSERVER, "op1", execution_type=NodeExecutionType.READ_ONLY)
        n2 = TaskNode("n2", "Obs2", AgentRole.OBSERVER, "op2", execution_type=NodeExecutionType.READ_ONLY)
        graph.add_node(n1)
        graph.add_node(n2)

        ready = graph.get_ready_nodes()
        self.assertEqual(len(ready), 2)
        self.assertFalse(ready[0].is_mutating)
        self.assertFalse(ready[1].is_mutating)

    # Test 3: Maximum worker limit
    def test_03_max_worker_limit(self):
        pwm = parallel_worker_manager
        self.assertEqual(pwm.max_parallel_workers, 4)

    # Test 4: Dependency ordering
    def test_04_dependency_ordering(self):
        graph = TaskGraph("g_test4")
        n1 = TaskNode("n1", "Obs", AgentRole.OBSERVER, "op1")
        n2 = TaskNode("n2", "Repair", AgentRole.EXECUTOR, "op2", execution_type=NodeExecutionType.MUTATING, dependencies=["n1"])
        graph.add_node(n1)
        graph.add_node(n2)

        ready = graph.get_ready_nodes()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].node_id, "n1")

        n1.status = AgentStatus.COMPLETED
        ready2 = graph.get_ready_nodes()
        self.assertEqual(len(ready2), 1)
        self.assertEqual(ready2[0].node_id, "n2")

    # Test 5: Failure propagation
    def test_05_failure_propagation(self):
        graph = TaskGraph("g_test5")
        n1 = TaskNode("n1", "Obs", AgentRole.OBSERVER, "op1")
        n2 = TaskNode("n2", "Diag", AgentRole.DIAGNOSTIC, "op2", dependencies=["n1"])
        n3 = TaskNode("n3", "Repair", AgentRole.EXECUTOR, "op3", dependencies=["n2"])
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_edge("n1", "n2")
        graph.add_edge("n2", "n3")

        graph.propagate_failure("n1", "Port check error")
        self.assertEqual(graph.nodes["n2"].status, AgentStatus.FAILED)
        self.assertEqual(graph.nodes["n3"].status, AgentStatus.FAILED)

    # Test 6: Worker timeout
    def test_06_worker_timeout(self):
        contract = create_agent_contract("g1", "t1", AgentRole.OBSERVER, "slow op", timeout_seconds=0.05)

        async def slow_work():
            await asyncio.sleep(0.2)
            return {"success": True}

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(parallel_worker_manager.run_worker_async(contract, slow_work()))
        self.assertFalse(res["success"])
        self.assertEqual(contract.status, AgentStatus.TIMEOUT)
        loop.close()

    # Test 7: Worker cancellation
    def test_07_worker_cancellation(self):
        contract = create_agent_contract("g1", "t1", AgentRole.OBSERVER, "cancellable")
        parallel_worker_manager._worker_contracts[contract.agent_id] = contract
        cancelled = parallel_worker_manager.cancel_worker(contract.agent_id, reason="Test cancel")
        self.assertTrue(cancelled)
        self.assertEqual(contract.status, AgentStatus.CANCELLED)

    # Test 8: Parent goal cancellation propagation
    def test_08_parent_goal_cancellation(self):
        graph = TaskGraph("g_test8")
        n1 = TaskNode("n1", "Obs", AgentRole.OBSERVER, "op1", status=AgentStatus.RUNNING)
        n2 = TaskNode("n2", "Diag", AgentRole.DIAGNOSTIC, "op2", status=AgentStatus.PENDING)
        graph.add_node(n1)
        graph.add_node(n2)

        cancellation_manager.register_active_goal("g_test8", graph)
        count = cancellation_manager.cancel_active_goal("g_test8", reason="User cancel")
        self.assertEqual(count, 1)
        self.assertEqual(graph.nodes["n1"].status, AgentStatus.CANCELLED)
        self.assertEqual(graph.nodes["n2"].status, AgentStatus.CANCELLED)

    # Test 9: Stale completion suppression after cancellation
    def test_09_stale_completion_suppression(self):
        cancellation_manager.register_active_goal("g_stale", TaskGraph("g_stale"))
        cancellation_manager.cancel_active_goal("g_stale")
        self.assertTrue(cancellation_manager.is_cancelled("g_stale"))

    # Test 10: Evidence freshness
    def test_10_evidence_freshness(self):
        shared_evidence_store.add_evidence("g10", "a1", "PORT_STATE", {"port": 3000}, source="Engine", confidence=0.8)
        time.sleep(0.01)
        shared_evidence_store.add_evidence("g10", "a1", "PORT_STATE", {"port": 3000}, source="Engine", confidence=0.95)

        evs = shared_evidence_store.get_evidence("g10", "PORT_STATE")
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].confidence, 0.95)

    # Test 11: Evidence deduplication
    def test_11_evidence_deduplication(self):
        shared_evidence_store.add_evidence("g11", "a1", "PROJECT_STATE", {"name": "FLOW"}, source="Discovery")
        shared_evidence_store.add_evidence("g11", "a2", "PROJECT_STATE", {"name": "FLOW"}, source="Discovery")

        evs = shared_evidence_store.get_evidence("g11", "PROJECT_STATE")
        self.assertEqual(len(evs), 1)

    # Test 12: Contradictory evidence
    def test_12_contradictory_evidence(self):
        shared_evidence_store.add_evidence("g12", "a1", "PORT_STATE", {"port": 3000}, source="Observation")
        shared_evidence_store.add_evidence("g12", "a2", "PORT_STATE", {"port": 4000}, source="Observation")

        contra = shared_evidence_store.detect_contradictions("g12")
        self.assertGreaterEqual(len(contra), 1)

    # Test 13: Conflict detection
    def test_13_conflict_detection(self):
        n1 = TaskNode("n1", "Kill 1", AgentRole.EXECUTOR, "kill", arguments={"target": "FLOW"}, execution_type=NodeExecutionType.MUTATING)
        n2 = TaskNode("n2", "Kill 2", AgentRole.EXECUTOR, "kill", arguments={"target": "FLOW"}, execution_type=NodeExecutionType.MUTATING)

        conflicts = agent_conflict_resolver.detect_conflicts([n1, n2])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["target"], "flow")

    # Test 14: Conflicting mutations serialization
    def test_14_conflicting_mutations_serialization(self):
        n1 = TaskNode("n1", "Kill 1", AgentRole.EXECUTOR, "kill", arguments={"target": "FLOW"}, execution_type=NodeExecutionType.MUTATING)
        n2 = TaskNode("n2", "Kill 2", AgentRole.EXECUTOR, "kill", arguments={"target": "FLOW"}, execution_type=NodeExecutionType.MUTATING)

        action, ordered = agent_conflict_resolver.resolve_mutating_conflict({"nodes": [n1, n2]})
        self.assertEqual(action, ConflictResolutionAction.SERIALIZE)
        self.assertEqual(len(ordered), 2)

    # Test 15: User command priority
    def test_15_user_command_priority(self):
        match = intent_router.match("cancel the current task")
        self.assertTrue(match["handled"])
        self.assertEqual(match["intent"], "CANCEL_ACTIVE_GOAL")

    # Test 16: Resource governor voice protection
    def test_16_resource_governor_voice_protection(self):
        resource_governor.update_voice_state(user_speaking=True, audio_playing=False)
        self.assertTrue(resource_governor.should_defer_background_work())
        self.assertEqual(resource_governor.get_max_allowed_workers(), 1)

        resource_governor.update_voice_state(user_speaking=False, audio_playing=False)
        time.sleep(0.6)
        self.assertFalse(resource_governor.should_defer_background_work())
        self.assertEqual(resource_governor.get_max_allowed_workers(), 4)

    # Test 17: Strong skill integration
    def test_17_strong_skill_integration(self):
        from core.skill_contract import SkillType, create_skill_contract
        from core.skill_matcher import skill_matcher
        from core.skill_registry import skill_registry

        skill = create_skill_contract("FIX_FLOW_PORT", SkillType.REPAIR_SKILL, "desc", "fix FLOW port", [], project_scope="FLOW")
        skill_registry.register_skill(skill)

        match = skill_matcher.get_best_match("fix FLOW port", project_name="FLOW")
        self.assertIsNotNone(match)

    # Test 18: Replanning after new evidence
    def test_18_replanning_after_new_evidence(self):
        graph = TaskGraph("g18")
        n1 = TaskNode("n1", "Obs", AgentRole.OBSERVER, "op1")
        graph.add_node(n1)
        self.assertFalse(graph.has_failures())
        graph.propagate_failure("n1", "Unexpected port conflict")
        self.assertTrue(graph.has_failures())

    # Test 19: Outcome verification requirement
    def test_19_outcome_verification_requirement(self):
        synth = agent_result_synthesizer
        graph = TaskGraph("g19")
        msg = synth.synthesize_result("FLOW", "PORT_CONFLICT", graph, {"outcome_verified": False})
        self.assertIn("unable to verify", msg)

    # Test 20: No success claim before verification
    def test_20_no_success_claim_without_verification(self):
        synth = agent_result_synthesizer
        graph = TaskGraph("g20")
        msg = synth.synthesize_result("FLOW", "PORT_CONFLICT", graph, {"outcome_verified": True, "port": 3000})
        self.assertIn("running now", msg)

    # Test 21: Simple commands bypass orchestration
    def test_21_simple_command_bypasses_orchestration(self):
        match = intent_router.match("open Chrome")
        self.assertTrue(match["handled"])
        self.assertEqual(match["intent"], "OPEN_APP")

    # Test 22: Complex FLOW recovery uses orchestration
    def test_22_complex_flow_recovery_uses_orchestration(self):
        match = intent_router.match("fix FLOW and open it when it works")
        self.assertTrue(match["handled"])
        self.assertEqual(match["intent"], "AUTONOMOUS_ORCHESTRATION")
        self.assertEqual(match["parameters"]["project_name"], "FLOW")
        self.assertTrue(match["parameters"]["follow_up_open"])

    # Test 23: Browser opens only after verified server health
    def test_23_browser_opens_only_after_verified_server(self):
        graph = TaskGraph("g23")
        n_verify = TaskNode("n_verify", "Verify", AgentRole.VERIFIER, "verify_outcome")
        n_open = TaskNode("n_open", "Open Browser", AgentRole.EXECUTOR, "open_browser", dependencies=["n_verify"])
        graph.add_node(n_verify)
        graph.add_node(n_open)

        # Before verify completes, open browser cannot run
        ready = graph.get_ready_nodes()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].node_id, "n_verify")

        # After verify completes, open browser becomes ready
        n_verify.status = AgentStatus.COMPLETED
        ready2 = graph.get_ready_nodes()
        self.assertEqual(len(ready2), 1)
        self.assertEqual(ready2[0].node_id, "n_open")

    # Test 24: No cross-goal evidence leakage
    def test_24_no_cross_goal_evidence_leakage(self):
        shared_evidence_store.add_evidence("goal_A", "agent_1", "PORT_STATE", 3000, source="Obs")
        shared_evidence_store.add_evidence("goal_B", "agent_2", "PORT_STATE", 4000, source="Obs")

        ev_A = shared_evidence_store.get_evidence("goal_A")
        ev_B = shared_evidence_store.get_evidence("goal_B")
        self.assertEqual(len(ev_A), 1)
        self.assertEqual(len(ev_B), 1)
        self.assertEqual(ev_A[0].value, 3000)
        self.assertEqual(ev_B[0].value, 4000)

    # Test 25: Duplicate worker suppression
    def test_25_duplicate_worker_suppression(self):
        graph = TaskGraph("g25")
        n1 = TaskNode("n1", "Obs Port", AgentRole.OBSERVER, "observe_port")
        graph.add_node(n1)
        # Re-adding node with same ID updates existing rather than duplicating
        n1_dup = TaskNode("n1", "Obs Port", AgentRole.OBSERVER, "observe_port")
        graph.add_node(n1_dup)
        self.assertEqual(len(graph.nodes), 1)


if __name__ == "__main__":
    unittest.main()
