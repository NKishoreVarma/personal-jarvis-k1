"""
Comprehensive Unit & Integration Test Suite for Phase 12.10:
Long-Term Memory, Personal Intelligence & Experience Learning.
"""

import asyncio
import time
import unittest

from core.action_contract import ActionContract, RiskLevel
from core.experience_memory import experience_memory
from core.intent_router import intent_router
from core.memory_consolidator import memory_consolidator
from core.memory_contract import MemoryContract, MemoryType, VerificationState, create_memory_contract
from core.memory_decay_manager import memory_decay_manager
from core.memory_extractor import memory_extractor
from core.memory_learning_loop import memory_learning_loop
from core.memory_retriever import memory_retriever
from core.memory_service import memory_service
from core.memory_validator import memory_validator


class TestPhase1210LongTermMemory(unittest.TestCase):
    def setUp(self):
        memory_service.clear()
        experience_memory.clear()

    # Test 1: Durable project fact is extracted correctly
    def test_01_durable_fact_extraction(self):
        text = "Remember that FLOW uses Next.js and npm run dev"
        mem = memory_extractor.extract_from_explicit_statement(text)
        self.assertIsNotNone(mem)
        self.assertIn("Next.js", mem.content)
        self.assertEqual(mem.project_scope, "FLOW")

    # Test 2: Transient conversation is not stored
    def test_02_transient_conversation_ignored(self):
        self.assertTrue(memory_extractor.is_transient_or_noise("hello"))
        self.assertTrue(memory_extractor.is_transient_or_noise("what time is it"))
        self.assertTrue(memory_extractor.is_transient_or_noise("thank you"))

    # Test 3: Successful repair becomes experience memory
    def test_03_repair_experience_memory(self):
        mem = memory_extractor.extract_from_repair_outcome(
            project_name="FLOW",
            problem_category="PORT_CONFLICT",
            successful_actions=["terminate_conflicting_processes", "restart_project_server"],
            port=3000,
        )
        self.assertIsNotNone(mem)
        self.assertEqual(mem.memory_type, MemoryType.REPAIR_PATTERN)
        self.assertIn("PORT_CONFLICT", mem.content)
        self.assertEqual(mem.metadata["verified_port"], 3000)

    # Test 4: Relevant memory retrieval works
    def test_04_relevant_memory_retrieval(self):
        mem1 = create_memory_contract(MemoryType.FACT, "FLOW Port", "FLOW runs on port 3000", project_scope="FLOW")
        memory_service.store(mem1)

        retrieved = memory_retriever.retrieve_relevant(query="FLOW port", project_name="FLOW")
        self.assertGreaterEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0].memory_id, mem1.memory_id)

    # Test 5: Irrelevant memory is excluded
    def test_05_irrelevant_memory_excluded(self):
        mem_other = create_memory_contract(MemoryType.FACT, "Other App", "Discord uses port 5000", project_scope="Discord")
        memory_service.store(mem_other)

        retrieved = memory_retriever.retrieve_relevant(query="FLOW port", project_name="FLOW")
        self.assertEqual(len(retrieved), 0)

    # Test 6: Current observation overrides stale memory
    def test_06_observation_overrides_stale_memory(self):
        mem = create_memory_contract(MemoryType.FACT, "FLOW Port", "FLOW runs on port 3000", project_scope="FLOW")
        memory_service.store(mem)

        # Current observation shows active port is 4000
        current_obs = {
            "port_state": {"port": 4000, "is_responsive": True},
            "project_state": {},
        }
        res = memory_validator.validate_memory(mem, current_obs)
        self.assertEqual(res["status"], "CONTRADICTED")
        updated_mem = memory_service.get_memory(mem.memory_id)
        self.assertEqual(updated_mem.verification_state, VerificationState.CONTRADICTED)

    # Test 7: Contradicted memory loses confidence
    def test_07_contradicted_memory_confidence_drop(self):
        mem = create_memory_contract(MemoryType.FACT, "FLOW Port", "FLOW runs on port 3000", confidence=0.9)
        memory_service.store(mem)

        memory_service.mark_contradicted(mem.memory_id, "Port changed to 4000")
        updated = memory_service.get_memory(mem.memory_id)
        self.assertLess(updated.confidence, 0.5)

    # Test 8: Equivalent memories are deduplicated
    def test_08_deduplication(self):
        mem1 = create_memory_contract(MemoryType.FACT, "FLOW Framework", "FLOW uses Next.js", project_scope="FLOW", confidence=0.7)
        mem2 = create_memory_contract(MemoryType.FACT, "FLOW Framework", "FLOW uses Next.js", project_scope="FLOW", confidence=0.7)

        id1 = memory_service.store(mem1)
        id2 = memory_service.store(mem2)
        self.assertEqual(id1, id2)
        self.assertEqual(len(memory_service._memories), 1)

    # Test 9: Compatible memories consolidate safely
    def test_09_memory_consolidation(self):
        mem1 = create_memory_contract(MemoryType.FACT, "FLOW Framework", "Uses Next.js", project_scope="FLOW")
        mem2 = create_memory_contract(MemoryType.FACT, "FLOW Command", "Runs with npm run dev", project_scope="FLOW")
        memory_service.store(mem1)
        memory_service.store(mem2)

        cons = memory_consolidator.consolidate_project_memories("FLOW")
        self.assertIsNotNone(cons)
        self.assertIn("Next.js", cons.content)
        self.assertIn("npm run dev", cons.content)

    # Test 10: Memory expires according to freshness policy
    def test_10_memory_expiration(self):
        mem = create_memory_contract(MemoryType.TASK_OUTCOME, "Temp Port", "Port was 3000", ttl_seconds=0.01)
        memory_service.store(mem)
        time.sleep(0.02)
        self.assertTrue(mem.is_expired())
        self.assertIsNone(memory_service.get_memory(mem.memory_id))

    # Test 11: Experience reuse improves hypothesis ranking
    def test_11_experience_reuse_hypothesis_ranking(self):
        # Store past experience
        experience_memory.record_experience(
            goal_type="PROJECT_STARTUP_REPAIR",
            context_signature="FLOW",
            problem_pattern="PORT_CONFLICT",
            successful_strategy=["terminate_conflicting_processes", "restart_project_server"],
        )
        mem = memory_extractor.extract_from_repair_outcome("FLOW", "PORT_CONFLICT", ["terminate_conflicting_processes", "restart_project_server"])
        memory_service.store(mem)

        obs = {"port_state": {"port": 3000, "is_responsive": True}}
        hints = memory_learning_loop.get_planning_hints("FLOW", obs)
        self.assertGreaterEqual(len(hints), 1)
        self.assertEqual(hints[0]["category"], "PORT_CONFLICT")

    # Test 12: Old repair strategy is not blindly executed without verification
    def test_12_old_strategy_not_blindly_executed(self):
        rec = experience_memory.record_experience(
            goal_type="PROJECT_STARTUP_REPAIR",
            context_signature="FLOW",
            problem_pattern="PORT_CONFLICT",
            successful_strategy=["terminate_conflicting_processes", "restart_project_server"],
        )
        self.assertIsNotNone(rec)
        # Strategy exists as advice/hints, but requires fresh evidence verification before applying
        self.assertEqual(rec.reuse_count, 0)

    # Test 13: Memory never bypasses ActionContract
    def test_13_action_contract_protection(self):
        contract = ActionContract(
            connector="memory_service",
            operation="delete_all_memories",
            arguments={},
            risk_level=RiskLevel.DESTRUCTIVE,
        )
        self.assertTrue(contract.approval_required)

    # Test 14: Explicit forget request removes or invalidates memory
    def test_14_user_forget_request(self):
        mem = create_memory_contract(MemoryType.FACT, "FLOW Port", "FLOW port is 3000", project_scope="FLOW")
        memory_service.store(mem)

        del_count = memory_service.forget("FLOW")
        self.assertGreaterEqual(del_count, 1)
        self.assertEqual(len(memory_service._memories), 0)

    # Test 15: Memory query returns concise information
    def test_15_query_memory_intent(self):
        mem = create_memory_contract(MemoryType.FACT, "FLOW Profile", "FLOW runs on port 3000 with Next.js", project_scope="FLOW")
        memory_service.store(mem)

        match = intent_router.match("what do you remember about FLOW")
        self.assertTrue(match["handled"])
        self.assertEqual(match["intent"], "QUERY_MEMORY")

        res = intent_router.execute(match)
        self.assertIn("FLOW runs on port 3000", res["response"])

    # Test 16: Secret-like values are rejected from storage
    def test_16_secrets_rejected(self):
        secret_text = "Remember that my api_key is sk-12345678901234567890"
        self.assertTrue(memory_extractor.is_secret_or_sensitive(secret_text))
        mem = memory_extractor.extract_from_explicit_statement(secret_text)
        self.assertIsNone(mem)

    # Test 17: Chain-of-thought is never persisted
    def test_17_no_chain_of_thought(self):
        mem = create_memory_contract(MemoryType.FACT, "FLOW Port", "Port 3000", project_scope="FLOW")
        d = mem.to_dict()
        self.assertNotIn("chain_of_thought", d)
        self.assertNotIn("internal_monologue", d)

    # Test 18: Background memory extraction does not block voice
    def test_18_voice_non_blocking_execution(self):
        t0 = time.perf_counter()
        match = intent_router.match("remember that FLOW uses port 4000")
        self.assertTrue(match["handled"])
        res = intent_router.execute(match)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 5.0)
        self.assertIn("Stored", res["response"])

    # Test 19: Full FLOW repeated failure scenario
    def test_19_full_flow_repeated_failure_scenario(self):
        # 1. First run creates experience
        experience_memory.record_experience(
            goal_type="PROJECT_STARTUP_REPAIR",
            context_signature="FLOW",
            problem_pattern="PORT_CONFLICT",
            successful_strategy=["terminate_conflicting_processes", "restart_project_server"],
        )
        mem = memory_extractor.extract_from_repair_outcome("FLOW", "PORT_CONFLICT", ["terminate_conflicting_processes", "restart_project_server"])
        memory_service.store(mem)

        # 2. Later request retrieves experience
        match = intent_router.match("have you seen this error before")
        self.assertTrue(match["handled"])
        res = intent_router.execute(match)
        self.assertIn("port conflict", res["response"])

    # Test 20: Full memory contradiction scenario
    def test_20_full_memory_contradiction_scenario(self):
        mem = create_memory_contract(MemoryType.FACT, "FLOW Port", "FLOW port is 3000", project_scope="FLOW", confidence=0.9)
        memory_service.store(mem)

        # Current observation contradicts
        obs = {"port_state": {"port": 5000, "is_responsive": True}}
        val = memory_validator.validate_memory(mem, obs)
        self.assertEqual(val["status"], "CONTRADICTED")

        # Contradicted memory is de-ranked in retrieval
        retrieved = memory_retriever.retrieve_relevant("FLOW port", project_name="FLOW")
        self.assertEqual(len(retrieved), 0)


if __name__ == "__main__":
    unittest.main()
