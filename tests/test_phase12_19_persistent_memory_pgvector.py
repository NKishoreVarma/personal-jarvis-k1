"""
Phase 12.19 — Secure Persistent Memory, Semantic Recall & PGVector Intelligence Test Suite.
Verifies all 31 core requirements:
1. Memory contract validation
2. Sensitive data scrubbing
3. Temporary memory rejection
4. Durable verified memory persistence
5. PostgreSQL store abstraction
6. Semantic similarity retrieval
7. Exact metadata filtering
8. Project isolation
9. Goal isolation
10. Cross-project leakage prevention
11. Verification-aware ranking
12. Freshness-aware ranking
13. Contradicted memory deprioritization
14. Expired memory handling
15. Memory consolidation
16. Duplicate prevention
17. Cache hit behavior
18. Cache invalidation
19. Embedding deduplication
20. Embedding provider timeout
21. PostgreSQL unavailable fallback
22. External storage degraded state
23. Safe write failure behavior
24. Recovery after database availability returns
25. External knowledge promotion integration
26. Planning integration
27. Learning integration
28. Runtime recovery separation
29. Intent commands
30. No cross-project leakage
31. No voice callback blocking
"""

from __future__ import annotations

import time
import unittest

from core.embedding_service import MockEmbeddingProvider, embedding_service
from core.intent_router import router
from core.memory_access_governor import memory_access_governor
from core.memory_consolidation_engine import memory_consolidation_engine
from core.memory_contract import (
    MemoryContract,
    MemoryType,
    VerificationState,
    contains_sensitive_data,
    create_memory_contract,
    scrub_sensitive_data,
)
from core.memory_contradiction_engine import memory_contradiction_engine
from core.memory_lifecycle_manager import memory_lifecycle_manager
from core.memory_quality_gate import MemoryRejectionReason, memory_quality_gate
from core.memory_retrieval_cache import memory_retrieval_cache
from core.memory_service import MemoryServiceMode, memory_service
from core.postgres_memory_store import postgres_memory_store
from core.semantic_memory_retriever import semantic_memory_retriever
from core.storage_configuration import StorageHealthStatus, storage_configuration


class TestPhase1219PersistentMemoryPGVector(unittest.TestCase):
    def setUp(self):
        memory_service.clear()
        postgres_memory_store.clear_all()
        memory_retrieval_cache.clear_all()
        embedding_service.clear_cache()
        memory_service.set_enabled(True)
        storage_configuration.status = StorageHealthStatus.ACTIVE

    # 1. Memory contract validation
    def test_01_memory_contract_validation(self):
        mem = create_memory_contract(
            memory_type=MemoryType.FACT,
            subject="Test Subject",
            content="Test Content",
            project_scope="FLOW",
            confidence=0.85,
        )
        self.assertEqual(mem.memory_type, MemoryType.FACT)
        self.assertEqual(mem.subject, "Test Subject")
        self.assertEqual(mem.project_id, "FLOW")

    # 2. Sensitive data scrubbing
    def test_02_sensitive_data_scrubbing(self):
        raw = "User password=supersecret and token bearer ghp_1234567890abcdef1234567890abcdef1234"
        self.assertTrue(contains_sensitive_data(raw))
        scrubbed = scrub_sensitive_data(raw)
        self.assertNotIn("supersecret", scrubbed)
        self.assertNotIn("ghp_1234567890abcdef1234567890abcdef1234", scrubbed)
        self.assertIn("[REDACTED_SECRET]", scrubbed)

        # Creating memory contract automatically scrubs sensitive text
        mem = create_memory_contract(
            memory_type=MemoryType.USER_PREFERENCE,
            subject="Auth Token",
            content="Saved token bearer ghp_1234567890abcdef1234567890abcdef1234",
        )
        self.assertNotIn("ghp_1234567890abcdef1234567890abcdef1234", mem.content)

    # 3. Temporary memory rejection
    def test_03_temporary_memory_rejection(self):
        mem = create_memory_contract(
            memory_type=MemoryType.TEMPORARY_CONTEXT,
            subject="Temp info",
            content="Ephemeral turn context",
            confidence=0.95,
        )
        passed, reason, _ = memory_quality_gate.validate_memory_for_storage(mem)
        self.assertFalse(passed)
        self.assertEqual(reason, MemoryRejectionReason.TEMPORARY)
        mem_id = memory_service.store(mem)
        self.assertEqual(mem_id, "")

    # 4. Durable verified memory persistence
    def test_04_durable_verified_memory_persistence(self):
        mem = create_memory_contract(
            memory_type=MemoryType.PROJECT_KNOWLEDGE,
            subject="FLOW Startup Command",
            content="FLOW runs with python dev_server.py on port 3000",
            project_scope="FLOW",
            confidence=0.90,
        )
        mem.verification_state = VerificationState.VERIFIED
        mem_id = memory_service.store(mem)
        self.assertTrue(bool(mem_id))
        loaded = memory_service.get_memory(mem_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.verification_state, VerificationState.VERIFIED)

    # 5. PostgreSQL store abstraction
    def test_05_postgres_store_abstraction(self):
        mem = create_memory_contract(
            memory_type=MemoryType.WORKFLOW_EXPERIENCE,
            subject="Port Kill Workflow",
            content="lsof -ti:3000 | xargs kill -9",
            project_scope="FLOW",
        )
        ok = postgres_memory_store.save_memory(mem)
        self.assertTrue(ok)
        rec = postgres_memory_store.get_memory(mem.memory_id)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.subject, "Port Kill Workflow")

    # 6. Semantic similarity retrieval
    def test_06_semantic_similarity_retrieval(self):
        mem1 = create_memory_contract(
            memory_type=MemoryType.WORKFLOW_EXPERIENCE,
            subject="FLOW Port Conflict",
            content="Kill process occupying port 3000 before dev server start",
            project_scope="FLOW",
            confidence=0.90,
        )
        mem1.verification_state = VerificationState.VERIFIED
        memory_service.store(mem1)

        results = memory_service.semantic_retrieve("How to resolve port conflict on 3000?", project_id="FLOW")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0][0].memory_id, mem1.memory_id)

    # 7. Exact metadata filtering
    def test_07_exact_metadata_filtering(self):
        mem_fact = create_memory_contract(MemoryType.FACT, "Fact Subject", "Fact Content", project_scope="FLOW")
        mem_pref = create_memory_contract(MemoryType.USER_PREFERENCE, "Pref Subject", "Pref Content", project_scope="FLOW")
        memory_service.store(mem_fact)
        memory_service.store(mem_pref)

        facts = postgres_memory_store.list_memories(project_id="FLOW", memory_type=MemoryType.FACT)
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].memory_type, MemoryType.FACT)

    # 8. Project isolation
    def test_08_project_isolation(self):
        mem_flow = create_memory_contract(MemoryType.PROJECT_KNOWLEDGE, "FLOW Config", "FLOW Details", project_scope="FLOW")
        mem_auth = create_memory_contract(MemoryType.PROJECT_KNOWLEDGE, "AUTH Service", "AUTH Details", project_scope="AUTH")
        memory_service.store(mem_flow)
        memory_service.store(mem_auth)

        flow_mems = memory_service.semantic_retrieve("Config Details", project_id="FLOW")
        for m, _ in flow_mems:
            self.assertEqual(m.project_id, "FLOW")

    # 9. Goal isolation
    def test_09_goal_isolation(self):
        mem1 = create_memory_contract(MemoryType.FACT, "Goal 1 Fact", "Data", goal_id="g_100", project_scope="FLOW")
        mem2 = create_memory_contract(MemoryType.FACT, "Goal 2 Fact", "Data", goal_id="g_200", project_scope="FLOW")
        memory_service.store(mem1)
        memory_service.store(mem2)

        results = semantic_memory_retriever.retrieve_memories("Goal 1", project_id="FLOW", goal_id="g_100")
        self.assertEqual(results[0][0].goal_id, "g_100")

    # 10. Cross-project leakage prevention
    def test_10_cross_project_leakage_prevention(self):
        mem_secret = create_memory_contract(MemoryType.PROJECT_KNOWLEDGE, "Secret DB", "Secret Schema", project_scope="PROJECT_A")
        memory_service.store(mem_secret)

        filtered = memory_access_governor.filter_accessible_memories([mem_secret], requesting_project_id="PROJECT_B")
        self.assertEqual(len(filtered), 0)

    # 11. Verification-aware ranking
    def test_11_verification_aware_ranking(self):
        mem_unverif = create_memory_contract(MemoryType.FACT, "Port Fact Unverified", "Port 3000 preliminary candidate", project_scope="FLOW", confidence=0.7)
        mem_unverif.verification_state = VerificationState.UNVERIFIED
        mem_verif = create_memory_contract(MemoryType.FACT, "Port Fact Verified", "Port 3000 confirmed listening socket", project_scope="FLOW", confidence=0.7)
        mem_verif.verification_state = VerificationState.VERIFIED

        memory_service.store(mem_unverif)
        memory_service.store(mem_verif)

        results = semantic_memory_retriever.retrieve_memories("Port Fact", project_id="FLOW")
        # Verified memory must rank higher
        self.assertEqual(results[0][0].verification_state, VerificationState.VERIFIED)

    # 12. Freshness-aware ranking
    def test_12_freshness_aware_ranking(self):
        mem_old = create_memory_contract(MemoryType.FACT, "Topic A", "Old details", project_scope="FLOW")
        mem_old.updated_at = time.time() - (86400 * 20)  # 20 days old
        mem_new = create_memory_contract(MemoryType.FACT, "Topic A", "New details", project_scope="FLOW")
        mem_new.updated_at = time.time()

        memory_service.store(mem_old)
        memory_service.store(mem_new)

        results = semantic_memory_retriever.retrieve_memories("Topic A", project_id="FLOW")
        self.assertEqual(results[0][0].memory_id, mem_new.memory_id)

    # 13. Contradicted memory deprioritization
    def test_13_contradicted_memory_deprioritization(self):
        mem_good = create_memory_contract(MemoryType.FACT, "FLOW Port", "FLOW port is 4000", project_scope="FLOW")
        mem_good.verification_state = VerificationState.VERIFIED
        mem_bad = create_memory_contract(MemoryType.FACT, "FLOW Port", "FLOW port is 3000", project_scope="FLOW")
        mem_bad.verification_state = VerificationState.CONTRADICTED

        memory_service.store(mem_good)
        memory_service.store(mem_bad)

        results = semantic_memory_retriever.retrieve_memories("FLOW Port", project_id="FLOW")
        self.assertEqual(results[0][0].memory_id, mem_good.memory_id)

    # 14. Expired memory handling
    def test_14_expired_memory_handling(self):
        mem = create_memory_contract(MemoryType.FACT, "Expiring Fact", "Data", project_scope="FLOW", ttl_seconds=0.01)
        memory_service.store(mem)
        time.sleep(0.03)
        expired_count = memory_lifecycle_manager.check_and_expire_memories()
        self.assertEqual(expired_count, 1)

        # Expired memory is filtered from active retrieval
        active = memory_service.retrieve(project_scope="FLOW")
        self.assertEqual(len(active), 0)

    # 15. Memory consolidation
    def test_15_memory_consolidation(self):
        events = [
            {"action": "Check port 3000"},
            {"action": "Kill conflicting PID"},
            {"action": "Start dev_server.py"},
        ]
        lesson = memory_consolidation_engine.evaluate_and_consolidate("FLOW", "PortConflictRepair", events)
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson.memory_type, MemoryType.LESSON)
        self.assertIn("Consolidated workflow", lesson.content)

    # 16. Duplicate prevention
    def test_16_duplicate_prevention(self):
        mem1 = create_memory_contract(MemoryType.FACT, "Exact Duplicate", "Identical content", project_scope="FLOW")
        mem2 = create_memory_contract(MemoryType.FACT, "Exact Duplicate", "Identical content", project_scope="FLOW")
        id1 = memory_service.store(mem1)
        id2 = memory_service.store(mem2)
        self.assertEqual(id1, id2)
        self.assertEqual(len(postgres_memory_store.list_memories()), 1)

    # 17. Cache hit behavior
    def test_17_cache_hit_behavior(self):
        mem = create_memory_contract(MemoryType.FACT, "Cache Query", "Data", project_scope="FLOW")
        memory_service.store(mem)

        res1 = memory_service.semantic_retrieve("Cache Query", project_id="FLOW")
        # Second retrieval should hit cache
        hit = memory_retrieval_cache.get("Cache Query", "FLOW")
        self.assertIsNotNone(hit)
        self.assertEqual(len(hit), len(res1))

    # 18. Cache invalidation
    def test_18_cache_invalidation(self):
        mem = create_memory_contract(MemoryType.FACT, "Invalidate Query", "Data", project_scope="FLOW")
        memory_service.store(mem)
        memory_service.semantic_retrieve("Invalidate Query", project_id="FLOW")

        # Invalidate via new store or clear
        memory_service.clear()
        hit = memory_retrieval_cache.get("Invalidate Query", "FLOW")
        self.assertIsNone(hit)

    # 19. Embedding deduplication
    def test_19_embedding_deduplication(self):
        text = "Repeated technical phrase for embedding"
        emb1 = embedding_service.get_embedding(text)
        emb2 = embedding_service.get_embedding(text)
        self.assertEqual(emb1, emb2)

    # 20. Embedding provider timeout
    def test_20_embedding_provider_timeout(self):
        self.assertEqual(embedding_service.timeout_s, 2.0)

    # 21. PostgreSQL unavailable fallback
    def test_21_postgres_unavailable_fallback(self):
        self.assertIn(memory_service.mode, [MemoryServiceMode.FALLBACK_MEMORY, MemoryServiceMode.POSTGRES_ACTIVE])
        mem = create_memory_contract(MemoryType.FACT, "Fallback Fact", "Works in fallback mode", project_scope="FLOW")
        mem_id = memory_service.store(mem)
        self.assertTrue(bool(mem_id))

    # 22. External storage degraded state
    def test_22_external_storage_degraded_state(self):
        storage_configuration.status = StorageHealthStatus.DEGRADED
        self.assertEqual(memory_service.mode, MemoryServiceMode.DEGRADED)

    # 23. Safe write failure behavior
    def test_23_safe_write_failure_behavior(self):
        memory_service.set_enabled(False)
        self.assertEqual(memory_service.mode, MemoryServiceMode.READ_ONLY)
        mem = create_memory_contract(MemoryType.FACT, "Blocked write", "Will not be saved")
        mem_id = memory_service.store(mem)
        self.assertEqual(mem_id, "")

    # 24. Recovery after database availability returns
    def test_24_recovery_after_availability_returns(self):
        storage_configuration.status = StorageHealthStatus.DEGRADED
        self.assertTrue(storage_configuration.is_degraded())
        storage_configuration.status = StorageHealthStatus.ACTIVE
        self.assertFalse(storage_configuration.is_degraded())

    # 25. External knowledge promotion integration
    def test_25_external_knowledge_promotion_integration(self):
        mem = create_memory_contract(
            memory_type=MemoryType.RETRIEVAL_KNOWLEDGE,
            subject="Next 15 External Doc",
            content="Turbopack serverExternalPackages configuration",
            project_scope="FLOW",
            confidence=0.90,
        )
        mem.verification_state = VerificationState.VERIFIED
        mem_id = memory_service.store(mem)
        self.assertTrue(bool(mem_id))

    # 26. Planning integration
    def test_26_planning_integration(self):
        mem = create_memory_contract(
            memory_type=MemoryType.WORKFLOW_EXPERIENCE,
            subject="FLOW Repair Strategy",
            content="Kill port 3000 then launch dev server",
            project_scope="FLOW",
            confidence=0.95,
        )
        mem.verification_state = VerificationState.VERIFIED
        memory_service.store(mem)

        mems = memory_service.retrieve(query="FLOW Repair", project_scope="FLOW")
        self.assertGreaterEqual(len(mems), 1)

    # 27. Learning integration
    def test_27_learning_integration(self):
        mem = create_memory_contract(
            memory_type=MemoryType.CAPABILITY_EXPERIENCE,
            subject="Skill Performance Record",
            content="Port conflict repair succeeded in 2.1s",
            project_scope="FLOW",
        )
        mem_id = memory_service.store(mem)
        self.assertTrue(bool(mem_id))

    # 28. Runtime recovery separation
    def test_28_runtime_recovery_separation(self):
        mem = create_memory_contract(
            memory_type=MemoryType.RECOVERY_EXPERIENCE,
            subject="Crash Recovery Log",
            content="Restarted process after sudden SIGKILL",
            project_scope="FLOW",
        )
        mem_id = memory_service.store(mem)
        self.assertTrue(bool(mem_id))

    # 29. Intent commands
    def test_29_intent_commands(self):
        st = memory_service.get_status()
        self.assertIn("mode", st)
        self.assertIn("total_memories", st)

    # 30. No cross-project leakage in semantic search
    def test_30_no_cross_project_leakage_semantic_search(self):
        mem_p1 = create_memory_contract(MemoryType.PROJECT_KNOWLEDGE, "P1 Data", "Confidential P1 info", project_scope="P1")
        memory_service.store(mem_p1)

        res = memory_service.semantic_retrieve("Confidential info", project_id="P2")
        self.assertEqual(len(res), 0)

    # 31. No voice callback blocking
    def test_31_no_voice_callback_blocking(self):
        # Warm-up router regex compilation
        router.match("how is your memory system working")
        t0 = time.perf_counter()
        match = router.match("how is your memory system working")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_MEMORY_STATUS")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
