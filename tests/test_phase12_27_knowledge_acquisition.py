"""
Phase 12.27 — Autonomous Knowledge Acquisition, Research Governance & Evidence Synthesis Test Suite.
Verifies all 30 core requirements:
1. Knowledge gap contract validation
2. Empty question rejection
3. Invalid TTL rejection
4. Low-confidence knowledge gap detection
5. Blocking gap detection
6. Research task creation
7. Research scope bounding
8. Maximum source limit
9. Research depth limit
10. Source reliability ranking
11. Official source outranks weak source
12. Recency affects source evaluation
13. Provenance is preserved
14. Evidence extraction structure
15. External claim does not become verified fact
16. Conflicting evidence detection
17. Conflict audit preservation
18. Live observation overrides research
19. Unresolved conflict remains unresolved
20. Evidence synthesis includes uncertainty
21. Verification requirement detection
22. Research finding promotion to candidate knowledge
23. Verified finding promotion to durable project knowledge
24. Contradicted knowledge rejection
25. Cross-project knowledge isolation
26. Duplicate research knowledge consolidation
27. Research cannot expand authority
28. Research cannot bypass approval requirements
29. Multi-agent evidence exchange remains bounded
30. Voice callback remains non-blocking
"""

from __future__ import annotations

import time
import unittest

from core.evidence_conflict_resolver import ConflictResolutionState, evidence_conflict_resolver
from core.evidence_extraction_engine import ClaimType, evidence_extraction_engine
from core.evidence_synthesis_engine import evidence_synthesis_engine
from core.intent_router import router
from core.knowledge_gap_contract import (
    KnowledgeGapContract,
    KnowledgeGapState,
    KnowledgeGapType,
    create_knowledge_gap,
)
from core.knowledge_gap_detector import KnowledgeGapSeverity, knowledge_gap_detector
from core.knowledge_promotion_manager import (
    KnowledgePromotionManager,
    PromotionState,
    knowledge_promotion_manager,
)
from core.research_governor import ResearchDecision, research_governor
from core.research_planning_engine import research_planning_engine
from core.research_task_contract import (
    ResearchTaskContract,
    ResearchTaskState,
    create_research_task,
)
from core.research_verification_engine import (
    ResearchVerificationResult,
    research_verification_engine,
)
from core.source_evaluation_contract import (
    SourceEvaluationContract,
    SourceReliabilityState,
    SourceType,
    create_source_evaluation,
)
from core.source_reliability_engine import source_reliability_engine


class TestPhase1227KnowledgeAcquisition(unittest.TestCase):
    def setUp(self):
        knowledge_promotion_manager.clear()
        research_governor.set_research_enabled(True)

    # 1. Knowledge gap contract validation
    def test_01_knowledge_gap_contract_validation(self):
        gap, msg = create_knowledge_gap(
            KnowledgeGapType.TECHNICAL_GAP,
            "Why is FLOW failing?",
            context="Startup error on port 3000",
        )
        self.assertIsNotNone(gap)
        self.assertEqual(gap.gap_type, KnowledgeGapType.TECHNICAL_GAP)
        self.assertEqual(gap.state, KnowledgeGapState.DETECTED)

    # 2. Empty question rejection
    def test_02_empty_question_rejection(self):
        gap, err = create_knowledge_gap(KnowledgeGapType.FACTUAL_GAP, "")
        self.assertIsNone(gap)
        self.assertIn("cannot be empty", err)

    # 3. Invalid TTL rejection
    def test_03_invalid_ttl_rejection(self):
        gap, err = create_knowledge_gap(
            KnowledgeGapType.FACTUAL_GAP, "Question?", ttl_seconds=-10.0
        )
        self.assertIsNone(gap)
        self.assertIn("TTL must be a positive number", err)

    # 4. Low-confidence knowledge gap detection
    def test_04_low_confidence_knowledge_gap_detection(self):
        sev, gap = knowledge_gap_detector.detect_gap(
            question="What is the new FLOW routing API?",
            retrieved_memory_confidence=0.30,
        )
        self.assertEqual(sev, KnowledgeGapSeverity.RESEARCH_WORTHY_GAP)
        self.assertIsNotNone(gap)
        self.assertEqual(gap.gap_type, KnowledgeGapType.TECHNICAL_GAP)

    # 5. Blocking gap detection
    def test_05_blocking_gap_detection(self):
        sev, gap = knowledge_gap_detector.detect_gap(
            question="Why is unknown dependency X crashing on boot?",
            is_unknown_dependency=True,
        )
        self.assertEqual(sev, KnowledgeGapSeverity.BLOCKING_GAP)
        self.assertIsNotNone(gap)
        self.assertEqual(gap.gap_type, KnowledgeGapType.DEPENDENCY_GAP)

    # 6. Research task creation
    def test_06_research_task_creation(self):
        task, msg = create_research_task(
            gap_id="gap_123",
            question="What changed in Next.js 15 routing?",
        )
        self.assertIsNotNone(task)
        self.assertEqual(task.state, ResearchTaskState.PLANNED)

    # 7. Research scope bounding
    def test_07_research_scope_bounding(self):
        task, _ = create_research_task(
            gap_id="gap_1",
            question="Question?",
            max_sources=50,  # exceeds max bound
            time_budget_seconds=500.0,  # exceeds max bound
        )
        self.assertLessEqual(task.max_sources, 20)
        self.assertLessEqual(task.time_budget_seconds, 120.0)

    # 8. Maximum source limit
    def test_08_maximum_source_limit(self):
        task, _ = create_research_task(gap_id="g1", question="Q", max_sources=5)
        self.assertEqual(task.max_sources, 5)

    # 9. Research depth limit
    def test_09_research_depth_limit(self):
        task, _ = create_research_task(gap_id="g1", question="Q", max_depth=10)
        self.assertEqual(task.max_depth, 3)

    # 10. Source reliability ranking
    def test_10_source_reliability_ranking(self):
        src_official = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.nextjs.org")
        src_forum = create_source_evaluation(SourceType.FORUM, "https://forum.example.com")

        rel_off = source_reliability_engine.evaluate_source(src_official)
        rel_forum = source_reliability_engine.evaluate_source(src_forum)
        self.assertGreater(rel_off, rel_forum)

    # 11. Official source outranks weak source
    def test_11_official_source_outranks_weak_source(self):
        src_changelog = create_source_evaluation(SourceType.OFFICIAL_CHANGELOG, "https://github.com/repo/releases")
        src_search = create_source_evaluation(SourceType.SEARCH_RESULT, "search_snippet")

        source_reliability_engine.evaluate_source(src_changelog)
        source_reliability_engine.evaluate_source(src_search)
        self.assertEqual(src_changelog.evaluation_state, SourceReliabilityState.VERY_HIGH)
        self.assertEqual(src_search.evaluation_state, SourceReliabilityState.LOW)

    # 12. Recency affects source evaluation
    def test_12_recency_affects_source_evaluation(self):
        src_fresh = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "url1", recency_score=1.0)
        src_stale = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "url2", recency_score=0.2)

        rel_fresh = source_reliability_engine.evaluate_source(src_fresh)
        rel_stale = source_reliability_engine.evaluate_source(src_stale)
        self.assertGreater(rel_fresh, rel_stale)

    # 13. Provenance is preserved
    def test_13_provenance_is_preserved(self):
        src = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.nextjs.org/v15")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.DOCUMENTATION_FACT, "Async params required in v15")
        self.assertIn("OFFICIAL_DOCUMENTATION", ev.provenance)
        self.assertIn("https://docs.nextjs.org/v15", ev.provenance)

    # 14. Evidence extraction structure
    def test_14_evidence_extraction_structure(self):
        src = create_source_evaluation(SourceType.PRIMARY, "local://FLOW/package.json")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.OBSERVATION, "package.json version is 15.0.1", is_direct_observation=True)
        self.assertTrue(ev.is_direct_observation)
        self.assertEqual(ev.claim_type, ClaimType.OBSERVATION)

    # 15. External claim does not become verified fact
    def test_15_external_claim_does_not_become_verified_fact(self):
        src = create_source_evaluation(SourceType.COMMUNITY, "https://community.com/post")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.COMPATIBILITY_CLAIM, "Unverified claim")

        synthesis = evidence_synthesis_engine.synthesize("gap_1", "Is X compatible?", [ev])
        verif, is_corrob, msg = research_verification_engine.verify_synthesis_against_reality(synthesis, local_environment_facts=None)
        self.assertEqual(verif, ResearchVerificationResult.EXTERNAL_CLAIM)
        self.assertFalse(is_corrob)

    # 16. Conflicting evidence detection
    def test_16_conflicting_evidence_detection(self):
        src1 = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "url1", authority_score=0.90)
        src2 = create_source_evaluation(SourceType.FORUM, "url2", authority_score=0.40)
        source_reliability_engine.evaluate_source(src1)
        source_reliability_engine.evaluate_source(src2)

        ev1 = evidence_extraction_engine.extract_evidence(src1, ClaimType.VERSION_CHANGE, "Requires Python 3.11")
        ev2 = evidence_extraction_engine.extract_evidence(src2, ClaimType.VERSION_CHANGE, "Supports Python 3.10")

        state, winner, losers, msg = evidence_conflict_resolver.resolve_conflicts([ev1, ev2])
        self.assertEqual(state, ConflictResolutionState.RESOLVED_BY_EVIDENCE)
        self.assertEqual(winner.evidence_id, ev1.evidence_id)

    # 17. Conflict audit preservation
    def test_17_conflict_audit_preservation(self):
        src1 = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "url1")
        src2 = create_source_evaluation(SourceType.COMMUNITY, "url2")
        source_reliability_engine.evaluate_source(src1)
        source_reliability_engine.evaluate_source(src2)

        ev1 = evidence_extraction_engine.extract_evidence(src1, ClaimType.COMPATIBILITY_CLAIM, "Claim A")
        ev2 = evidence_extraction_engine.extract_evidence(src2, ClaimType.COMPATIBILITY_CLAIM, "Claim B")

        synthesis = evidence_synthesis_engine.synthesize("gap_1", "Conflict Q", [ev1, ev2])
        self.assertEqual(len(synthesis.contradicting_evidence), 1)

    # 18. Live observation overrides research
    def test_18_live_observation_overrides_research(self):
        src_ext = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.ext.org")
        src_live = create_source_evaluation(SourceType.PRIMARY, "local://probe")
        source_reliability_engine.evaluate_source(src_ext)
        source_reliability_engine.evaluate_source(src_live)

        ev_ext = evidence_extraction_engine.extract_evidence(src_ext, ClaimType.COMPATIBILITY_CLAIM, "Claim X is true", is_direct_observation=False)
        ev_live = evidence_extraction_engine.extract_evidence(src_live, ClaimType.OBSERVATION, "Direct probe shows X is false", is_direct_observation=True)

        state, winner, _, _ = evidence_conflict_resolver.resolve_conflicts([ev_ext, ev_live])
        self.assertEqual(state, ConflictResolutionState.RESOLVED_BY_LIVE_OBSERVATION)
        self.assertEqual(winner.evidence_id, ev_live.evidence_id)

    # 19. Unresolved conflict remains unresolved
    def test_19_unresolved_conflict_remains_unresolved(self):
        src1 = create_source_evaluation(SourceType.COMMUNITY, "url1", authority_score=0.50, recency_score=0.50)
        src2 = create_source_evaluation(SourceType.COMMUNITY, "url2", authority_score=0.50, recency_score=0.50)
        source_reliability_engine.evaluate_source(src1)
        source_reliability_engine.evaluate_source(src2)

        ev1 = evidence_extraction_engine.extract_evidence(src1, ClaimType.COMPATIBILITY_CLAIM, "Claim Alpha")
        ev2 = evidence_extraction_engine.extract_evidence(src2, ClaimType.COMPATIBILITY_CLAIM, "Claim Beta")

        state, winner, _, _ = evidence_conflict_resolver.resolve_conflicts([ev1, ev2])
        self.assertEqual(state, ConflictResolutionState.UNRESOLVED)
        self.assertIsNone(winner)

    # 20. Evidence synthesis includes uncertainty
    def test_20_evidence_synthesis_includes_uncertainty(self):
        src = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.org")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.DOCUMENTATION_FACT, "Docs state parameter is required", is_direct_observation=False)

        syn = evidence_synthesis_engine.synthesize("gap_1", "Is param required?", [ev])
        self.assertIn("local environment verification", syn.uncertainty_description)
        self.assertIn("Evidence suggests:", syn.conclusion)

    # 21. Verification requirement detection
    def test_21_verification_requirement_detection(self):
        src = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.org")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.DOCUMENTATION_FACT, "Hypothesis", is_direct_observation=False)

        syn = evidence_synthesis_engine.synthesize("gap_1", "Question", [ev])
        self.assertTrue(len(syn.verification_requirements) > 0)

    # 22. Research finding promotion to candidate knowledge
    def test_22_research_finding_promotion_to_candidate_knowledge(self):
        src = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.org")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.DOCUMENTATION_FACT, "Candidate finding", is_direct_observation=False)

        syn = evidence_synthesis_engine.synthesize("gap_1", "Q", [ev])
        rec, msg = knowledge_promotion_manager.promote_synthesis(syn, ResearchVerificationResult.EXTERNAL_CLAIM, project_id="FLOW")
        self.assertEqual(rec.knowledge_category, "RETRIEVAL_KNOWLEDGE")
        self.assertEqual(rec.state, PromotionState.CANDIDATE)

    # 23. Verified finding promotion to durable project knowledge
    def test_23_verified_finding_promotion_to_durable_project_knowledge(self):
        src = create_source_evaluation(SourceType.PRIMARY, "local://inspection")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.OBSERVATION, "Verified finding on port 3000", is_direct_observation=True)

        syn = evidence_synthesis_engine.synthesize("gap_1", "Port question", [ev])
        rec, msg = knowledge_promotion_manager.promote_synthesis(syn, ResearchVerificationResult.LIVE_VERIFIED_RESULT, project_id="FLOW")
        self.assertEqual(rec.knowledge_category, "PROJECT_KNOWLEDGE")
        self.assertEqual(rec.state, PromotionState.DURABLE)

    # 24. Contradicted knowledge rejection
    def test_24_contradicted_knowledge_rejection(self):
        src = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.org")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.COMPATIBILITY_CLAIM, "Hypothesis X")

        syn = evidence_synthesis_engine.synthesize("gap_1", "Q", [ev])
        local_facts = {"contradicts_research": True}
        verif, ok, _ = research_verification_engine.verify_synthesis_against_reality(syn, local_facts)
        self.assertFalse(ok)

    # 25. Cross-project knowledge isolation
    def test_25_cross_project_knowledge_isolation(self):
        src = create_source_evaluation(SourceType.PRIMARY, "local://FLOW")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.OBSERVATION, "FLOW secret knowledge", is_direct_observation=True)

        syn = evidence_synthesis_engine.synthesize("gap_1", "Q", [ev])
        knowledge_promotion_manager.promote_synthesis(syn, ResearchVerificationResult.LIVE_VERIFIED_RESULT, project_id="FLOW")

        flow_kn = knowledge_promotion_manager.get_project_knowledge("FLOW")
        other_kn = knowledge_promotion_manager.get_project_knowledge("OTHER_PROJECT")
        self.assertEqual(len(flow_kn), 1)
        self.assertEqual(len(other_kn), 0)

    # 26. Duplicate research knowledge consolidation
    def test_26_duplicate_research_knowledge_consolidation(self):
        src = create_source_evaluation(SourceType.PRIMARY, "local://FLOW")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.OBSERVATION, "Duplicate finding", is_direct_observation=True)

        syn = evidence_synthesis_engine.synthesize("gap_1", "Q", [ev])
        rec1, _ = knowledge_promotion_manager.promote_synthesis(syn, ResearchVerificationResult.LIVE_VERIFIED_RESULT, project_id="FLOW")
        rec2, msg = knowledge_promotion_manager.promote_synthesis(syn, ResearchVerificationResult.LIVE_VERIFIED_RESULT, project_id="FLOW")
        self.assertEqual(rec1.record_id, rec2.record_id)
        self.assertIn("consolidated", msg)

    # 27. Research cannot expand authority
    def test_27_research_cannot_expand_authority(self):
        # Attempt to create research task requesting mutating authority must be rejected
        task, err = create_research_task(
            gap_id="gap_1",
            question="Dangerous task",
            authority_level="MUTATING_ADMIN",
        )
        self.assertIsNone(task)
        self.assertIn("cannot request mutating or elevated authority", err)

    # 28. Research cannot bypass approval requirements
    def test_28_research_cannot_bypass_approval_requirements(self):
        task, _ = create_research_task(
            gap_id="gap_1",
            question="Mutating follow-up",
            metadata={"triggers_system_mutation": True},
        )
        dec, msg = research_governor.evaluate_research_task(task, user_explicit_approval=False)
        self.assertEqual(dec, ResearchDecision.REQUIRE_APPROVAL)

    # 29. Multi-agent evidence exchange remains bounded
    def test_29_multi_agent_evidence_exchange_remains_bounded(self):
        src = create_source_evaluation(SourceType.OFFICIAL_DOCUMENTATION, "https://docs.org")
        source_reliability_engine.evaluate_source(src)
        ev = evidence_extraction_engine.extract_evidence(src, ClaimType.DOCUMENTATION_FACT, "Bounded exchange claim")
        d = ev.to_dict()
        self.assertIn("evidence_id", d)
        self.assertNotIn("raw_cot", d)

    # 30. Voice callback remains non-blocking
    def test_30_voice_callback_remains_non_blocking(self):
        t0 = time.perf_counter()
        match = router.match("what don't you know about this")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_KNOWLEDGE_GAP")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
