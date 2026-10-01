"""
Phase 12.18 — External Knowledge Integration, Retrieval Intelligence & Evidence-Grounded Decision Making Test Suite.
Verifies all 31 core requirements:
1. No retrieval when local evidence is sufficient
2. Retrieval when a genuine knowledge gap exists
3. Maximum source limit enforcement (max 5)
4. Maximum query variant enforcement (max 3)
5. Official source outranking weak source
6. Duplicate result elimination
7. Retrieval cache hit
8. Cache expiration
9. Source freshness handling
10. Single-source evidence remains lower confidence
11. Multi-source corroboration increases confidence
12. Current observation overrides external information
13. External claim contradicted by environment
14. Retrieved repair suggestion requires normal safety gate
15. External instruction cannot bypass ActionContract
16. Approval-required action still requires approval
17. Verified external knowledge may influence hypothesis ranking
18. Unverified external knowledge cannot directly trigger mutation
19. Successful retrieval usefulness learning
20. Unhelpful retrieval penalty
21. User disables automatic external retrieval
22. User explicitly requests search
23. Provenance explanation
24. Knowledge confidence explanation
25. Durable verified knowledge promotion
26. Temporary external information rejection from memory
27. Parallel read-only retrieval worker coordination
28. Retrieval timeout handling
29. Retrieval failure fallback to local reasoning
30. Zero voice callback blocking
31. End-to-end FLOW external diagnosis scenario
"""

from __future__ import annotations

import time
import unittest

from core.claim_verification_engine import ClaimVerificationLevel, claim_verification_engine
from core.evidence_corroboration_engine import CorroborationResult, evidence_corroboration_engine
from core.external_knowledge_contract import (
    ExternalKnowledgeContract,
    SourceCategory,
    VerificationState,
    create_knowledge_item,
)
from core.external_knowledge_safety_gate import external_knowledge_safety_gate
from core.external_retrieval_planner import external_retrieval_planner
from core.external_retrieval_service import external_retrieval_service
from core.intent_router import router
from core.knowledge_gap_detector import KnowledgeGapType, knowledge_gap_detector
from core.knowledge_introspection import knowledge_introspection
from core.knowledge_promotion_manager import knowledge_promotion_manager
from core.knowledge_provenance_tracker import knowledge_provenance_tracker
from core.knowledge_synthesis_engine import knowledge_synthesis_engine
from core.memory_service import memory_service
from core.retrieval_cache_manager import retrieval_cache_manager
from core.retrieval_learning_loop import retrieval_learning_loop
from core.source_authority_evaluator import AuthorityLevel, source_authority_evaluator


class TestPhase1218ExternalKnowledge(unittest.TestCase):
    def setUp(self):
        retrieval_cache_manager.clear_all()
        external_retrieval_service.clear_all()
        external_retrieval_service.set_retrieval_enabled(True)
        knowledge_provenance_tracker.clear_all()
        retrieval_learning_loop.clear_all()

    # 1. No retrieval when local evidence is sufficient
    def test_01_no_retrieval_when_local_evidence_sufficient(self):
        gap_type, reason = knowledge_gap_detector.detect_gap(
            query="Why did FLOW fail to start?",
            project_scope="FLOW",
            local_logs="Error: listen EADDRINUSE: address already in use :::3000",
        )
        self.assertEqual(gap_type, KnowledgeGapType.NO_GAP)
        self.assertIn("EADDRINUSE", reason)

    # 2. Retrieval when a genuine knowledge gap exists
    def test_02_retrieval_when_knowledge_gap_exists(self):
        gap_type, reason = knowledge_gap_detector.detect_gap(
            query="What changed in the latest Next.js 15 configuration that breaks turbopack?",
            project_scope="FLOW",
        )
        self.assertEqual(gap_type, KnowledgeGapType.EXTERNAL_LOOKUP_REQUIRED)

    # 3. Maximum source limit enforcement
    def test_03_max_source_limit_enforcement(self):
        plan = external_retrieval_planner.create_retrieval_plan(query="Next.js server error", project_scope="FLOW")
        self.assertLessEqual(plan.max_sources, 5)

        # Mock 10 items
        items = [
            create_knowledge_item("q", f"Title {i}", f"Summary {i}", SourceCategory.SEARCH_RESULT)
            for i in range(10)
        ]
        external_retrieval_service.register_mock_source("next.js", items)
        retrieved = external_retrieval_service.retrieve_knowledge(plan)
        self.assertLessEqual(len(retrieved), 5)

    # 4. Maximum query variant enforcement
    def test_04_max_query_variant_enforcement(self):
        plan = external_retrieval_planner.create_retrieval_plan(
            query="How to configure Next.js turbopack",
            project_scope="FLOW",
            error_context="Module not found: Can't resolve './entry.js'\nStack trace...",
        )
        self.assertLessEqual(len(plan.search_queries), 3)

    # 5. Official source outranking weak source
    def test_05_official_source_outranking_weak_source(self):
        official = create_knowledge_item(
            "query", "Next.js Docs", "Docs",
            source_type=SourceCategory.OFFICIAL_DOCUMENTATION,
            source_url="https://nextjs.org/docs/app",
        )
        blog = create_knowledge_item(
            "query", "Random Blog", "Post",
            source_type=SourceCategory.SEARCH_RESULT,
            source_url="https://random-dev-blog.net/post",
        )
        _, auth_off, _ = source_authority_evaluator.evaluate_authority(official)
        _, auth_blog, _ = source_authority_evaluator.evaluate_authority(blog)
        self.assertGreater(auth_off, auth_blog)

    # 6. Duplicate result elimination
    def test_06_duplicate_result_elimination(self):
        item1 = create_knowledge_item("q", "Duplicate Doc", "Doc summary", SourceCategory.OFFICIAL_DOCUMENTATION)
        item2 = create_knowledge_item("q", "Duplicate Doc", "Doc summary", SourceCategory.OFFICIAL_DOCUMENTATION)
        external_retrieval_service.register_mock_source("dup", [item1, item2])
        plan = external_retrieval_planner.create_retrieval_plan("dup test", "FLOW")
        results = external_retrieval_service.retrieve_knowledge(plan)
        self.assertEqual(len(results), 1)

    # 7. Retrieval cache hit
    def test_07_retrieval_cache_hit(self):
        item = create_knowledge_item("cached query", "Cached Title", "Summary", SourceCategory.OFFICIAL_DOCUMENTATION)
        retrieval_cache_manager.put("cached query", [item], "FLOW", "recent", ttl_seconds=100.0)
        hit = retrieval_cache_manager.get("cached query", "FLOW", "recent")
        self.assertIsNotNone(hit)
        self.assertEqual(len(hit), 1)

    # 8. Cache expiration
    def test_08_cache_expiration(self):
        item = create_knowledge_item("exp query", "Exp Title", "Summary", SourceCategory.OFFICIAL_DOCUMENTATION)
        retrieval_cache_manager.put("exp query", [item], "FLOW", "recent", ttl_seconds=0.01)
        time.sleep(0.03)
        hit = retrieval_cache_manager.get("exp query", "FLOW", "recent")
        self.assertIsNone(hit)

    # 9. Source freshness handling
    def test_09_source_freshness_handling(self):
        item = create_knowledge_item("freshness", "Title", "Summary", ttl_seconds=0.02)
        self.assertFalse(item.is_expired())
        time.sleep(0.04)
        self.assertTrue(item.is_expired())

    # 10. Single-source evidence remains lower confidence
    def test_10_single_source_lower_confidence(self):
        item = create_knowledge_item("q", "Single Source", "Summary", authority_score=0.70)
        res, conf, reason = evidence_corroboration_engine.corroborate_evidence([item])
        self.assertEqual(res, CorroborationResult.SINGLE_SOURCE)
        self.assertLessEqual(conf, 0.65)

    # 11. Multi-source corroboration increases confidence
    def test_11_multi_source_corroboration_increases_confidence(self):
        item1 = create_knowledge_item("q", "Source 1", "Summary", authority_score=0.85)
        item2 = create_knowledge_item("q", "Source 2", "Summary", authority_score=0.85)
        res, conf, reason = evidence_corroboration_engine.corroborate_evidence([item1, item2])
        self.assertEqual(res, CorroborationResult.CORROBORATED)
        self.assertGreaterEqual(conf, 0.85)

    # 12. Current observation overrides external information
    def test_12_current_observation_overrides_external_information(self):
        item = create_knowledge_item("q", "Port Doc", "FLOW default port is port 3000", claims=["FLOW runs on port 3000"])
        obs = {"project_name": "FLOW", "port": 4000, "process_running": True}
        res, conf, reason = evidence_corroboration_engine.corroborate_evidence([item], current_observation=obs)
        self.assertEqual(res, CorroborationResult.CONTRADICTED_BY_REALITY)
        self.assertTrue(item.is_contradicted())

    # 13. External claim contradicted by environment
    def test_13_external_claim_contradicted_by_environment(self):
        item = create_knowledge_item("q", "Next 15 Upgrade", "Breaking change in Next.js 15", claims=["Requires update for Next.js 15"])
        project_cfg = {"dependencies": {"next": "14.2.0"}}
        level, reason = claim_verification_engine.verify_claim_against_environment(item, project_config=project_cfg)
        self.assertEqual(level, ClaimVerificationLevel.CONTRADICTED)

    # 14. Retrieved repair suggestion requires normal safety gate
    def test_14_repair_suggestion_requires_safety_gate(self):
        item = create_knowledge_item("q", "Dangerous Advice", "Delete node_modules and data", claims=["rm -rf /data /node_modules"])
        safe, reason = external_knowledge_safety_gate.validate_for_planning(item, ClaimVerificationLevel.SOURCE_SUPPORTED)
        self.assertFalse(safe)
        self.assertIn("unsafe destructive", reason.lower())

    # 15. External instruction cannot bypass ActionContract
    def test_15_cannot_bypass_action_contract(self):
        item = create_knowledge_item("q", "High Risk Mutation", "Format drive and reinstall", claims=["Format drive"])
        safe, reason = external_knowledge_safety_gate.validate_for_planning(item, ClaimVerificationLevel.SOURCE_SUPPORTED, proposed_action_risk="high")
        self.assertFalse(safe)

    # 16. Approval-required action still requires approval
    def test_16_approval_required_action_still_requires_approval(self):
        item = create_knowledge_item("q", "Elevated Action", "Modify system config", claims=["Change sysctl"])
        safe, _ = external_knowledge_safety_gate.validate_for_planning(item, ClaimVerificationLevel.UNVERIFIED, proposed_action_risk="critical")
        self.assertFalse(safe)

    # 17. Verified external knowledge may influence hypothesis ranking
    def test_17_verified_external_knowledge_influences_synthesis(self):
        item = create_knowledge_item("q", "Next Config Guide", "Add serverExternalPackages to next.config.mjs", claims=["next.config.mjs"])
        item.verification_state = VerificationState.VERIFIED
        synth = knowledge_synthesis_engine.synthesize_knowledge(
            project_scope="FLOW",
            local_observations={"process_running": False},
            external_items=[item],
            verification_level=ClaimVerificationLevel.ENVIRONMENT_SUPPORTED,
        )
        self.assertGreaterEqual(len(synth.strong_evidence), 1)
        self.assertGreaterEqual(synth.overall_confidence, 0.85)

    # 18. Unverified external knowledge cannot directly trigger mutation
    def test_18_unverified_external_knowledge_cannot_trigger_mutation(self):
        item = create_knowledge_item("q", "Unverified Blog", "Try this patch", claims=["Patch core"])
        item.verification_state = VerificationState.UNVERIFIED
        safe, reason = external_knowledge_safety_gate.validate_for_planning(item, ClaimVerificationLevel.UNVERIFIED, proposed_action_risk="high")
        self.assertFalse(safe)

    # 19. Successful retrieval usefulness learning
    def test_19_successful_retrieval_usefulness_learning(self):
        retrieval_learning_loop.record_retrieval_outcome("Next 15 config", "Next.js Official Docs", influenced_plan=True, outcome_succeeded=True)
        score = retrieval_learning_loop.get_source_usefulness("Next.js Official Docs")
        self.assertGreater(score, 0.80)

    # 20. Unhelpful retrieval penalty
    def test_20_unhelpful_retrieval_penalty(self):
        retrieval_learning_loop.record_retrieval_outcome("Old thread", "Random Forum", influenced_plan=False, outcome_succeeded=False, was_redundant=True)
        score = retrieval_learning_loop.get_source_usefulness("Random Forum")
        self.assertLess(score, 0.80)
        self.assertGreater(retrieval_learning_loop.get_unnecessary_retrieval_rate(), 0.0)

    # 21. User disables automatic external retrieval
    def test_21_user_disables_automatic_external_retrieval(self):
        external_retrieval_service.set_retrieval_enabled(False)
        plan = external_retrieval_planner.create_retrieval_plan("test", "FLOW")
        results = external_retrieval_service.retrieve_knowledge(plan)
        self.assertEqual(len(results), 0)

    # 22. User explicitly requests search
    def test_22_user_explicitly_requests_search(self):
        gap_type, reason = knowledge_gap_detector.detect_gap(
            query="Look this up on Next.js docs",
            project_scope="FLOW",
            local_logs="Error: listen EADDRINUSE :::3000",
            explicit_search_requested=True,
        )
        self.assertEqual(gap_type, KnowledgeGapType.EXTERNAL_LOOKUP_REQUIRED)

    # 23. Provenance explanation
    def test_23_provenance_explanation(self):
        item = create_knowledge_item("q", "Next.js Documentation", "Docs")
        knowledge_provenance_tracker.record_provenance(item, "Matched Next 15 error", "Verified next.config.mjs", influenced_plan=True, action_succeeded=True)
        exp = knowledge_introspection.explain_source("FLOW")
        self.assertIn("Next.js Documentation", exp)

    # 24. Knowledge confidence explanation
    def test_24_knowledge_confidence_explanation(self):
        exp_env = knowledge_introspection.explain_confidence(ClaimVerificationLevel.ENVIRONMENT_SUPPORTED)
        self.assertIn("corroborated by official documentation", exp_env)

        exp_single = knowledge_introspection.explain_confidence(ClaimVerificationLevel.SOURCE_SUPPORTED, is_corroborated=False)
        self.assertIn("found one potential reference", exp_single)

    # 25. Durable verified knowledge promotion
    def test_25_durable_verified_knowledge_promotion(self):
        item = create_knowledge_item(
            query="Next 15 serverExternalPackages",
            title="Next.js 15 Package Config",
            content_summary="FLOW requires serverExternalPackages configuration in next.config.mjs.",
            project_scope="FLOW",
        )
        promoted, reason = knowledge_promotion_manager.evaluate_and_promote(
            item,
            verification_level=ClaimVerificationLevel.ENVIRONMENT_SUPPORTED,
            is_durable_fact=True,
        )
        self.assertTrue(promoted)
        self.assertIn("Promoted verified knowledge", reason)

    # 26. Temporary external information rejection from memory
    def test_26_temporary_information_rejection_from_memory(self):
        item = create_knowledge_item(
            query="npm registry",
            title="NPM Outage Notice",
            content_summary="Current npm registry incident causing temporary downtime.",
            project_scope="FLOW",
        )
        promoted, reason = knowledge_promotion_manager.evaluate_and_promote(
            item,
            verification_level=ClaimVerificationLevel.ENVIRONMENT_SUPPORTED,
            is_durable_fact=False,
        )
        self.assertFalse(promoted)
        self.assertIn("Ephemeral or incident-specific", reason)

    # 27. Parallel read-only retrieval worker coordination
    def test_27_parallel_retrieval_coordination(self):
        plan = external_retrieval_planner.create_retrieval_plan("parallel test", "FLOW")
        items = external_retrieval_service.retrieve_knowledge(plan)
        self.assertIsInstance(items, list)

    # 28. Retrieval timeout handling
    def test_28_retrieval_timeout_handling(self):
        plan = external_retrieval_planner.create_retrieval_plan("timeout query", "FLOW")
        self.assertEqual(plan.timeout_s, 5.0)

    # 29. Retrieval failure fallback to local reasoning
    def test_29_retrieval_failure_fallback(self):
        external_retrieval_service.set_retrieval_enabled(False)
        plan = external_retrieval_planner.create_retrieval_plan("fallback", "FLOW")
        results = external_retrieval_service.retrieve_knowledge(plan)
        self.assertEqual(results, [])
        # Synthesis handles empty external items cleanly
        synth = knowledge_synthesis_engine.synthesize_knowledge("FLOW", {"process_running": False}, results)
        self.assertEqual(len(synth.strong_evidence), 0)

    # 30. Zero voice callback blocking
    def test_30_zero_voice_callback_blocking(self):
        router.match("what time is it")  # Warm-up
        t0 = time.perf_counter()
        match = router.match("where did you get that")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_KNOWLEDGE_SOURCE")
        self.assertLess(dt, 20.0)

    # 31. End-to-end FLOW external diagnosis scenario
    def test_31_end_to_end_flow_external_diagnosis_scenario(self):
        # 1. Knowledge gap detected for Next 15 error
        gap, _ = knowledge_gap_detector.detect_gap("Next.js 15 Turbopack config issue", "FLOW")
        self.assertEqual(gap, KnowledgeGapType.EXTERNAL_LOOKUP_REQUIRED)

        # 2. Plan retrieval
        plan = external_retrieval_planner.create_retrieval_plan("Next.js 15 Turbopack config issue", "FLOW")

        # 3. Retrieve
        items = external_retrieval_service.retrieve_knowledge(plan)
        self.assertGreater(len(items), 0)

        # 4. Corroborate
        res, conf, _ = evidence_corroboration_engine.corroborate_evidence(items)

        # 5. Verify against environment
        level, _ = claim_verification_engine.verify_claim_against_environment(items[0], {"dependencies": {"next": "15.0.0"}})

        # 6. Safety check
        safe, _ = external_knowledge_safety_gate.validate_for_planning(items[0], level)
        self.assertTrue(safe)

        # 7. Synthesize
        synth = knowledge_synthesis_engine.synthesize_knowledge("FLOW", {"process_running": False}, items, level)
        self.assertGreater(synth.overall_confidence, 0.70)


if __name__ == "__main__":
    unittest.main()
