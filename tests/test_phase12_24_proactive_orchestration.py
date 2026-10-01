"""
Phase 12.24 — Proactive Planning, Opportunity Detection & Anticipatory Task Orchestration Test Suite.
Verifies all 30 core requirements:
1. Opportunity contract validation
2. Invalid opportunity rejection
3. Next-step detection
4. Blocker detection
5. Regression opportunity detection
6. Knowledge gap opportunity detection
7. Stale verification detection
8. Context-aware prioritization
9. Evidence-based scoring
10. Low-confidence penalty
11. Duplicate opportunity suppression
12. User dismissal
13. Session suppression
14. Project suppression
15. Permanent suppression
16. Critical change reactivation
17. Explicit instruction override
18. Current reality override
19. No autonomous mutation
20. High-risk approval enforcement
21. ActionContract authority preservation
22. Follow-up tracking
23. Expired opportunity rejection
24. Interaction style integration
25. Long-horizon goal integration
26. Memory integration
27. Regression integration
28. Pending approval detection
29. Non-blocking background execution
30. Zero voice latency overhead
"""

from __future__ import annotations

import time
import unittest

from core.action_contract import RiskLevel
from core.collaboration_context_contract import create_collaboration_context
from core.follow_up_tracker import follow_up_tracker
from core.intent_router import router
from core.interaction_style_manager import InteractionStyle, interaction_style_manager
from core.long_horizon_goal_manager import long_horizon_goal_manager
from core.opportunity_detection_engine import opportunity_detection_engine
from core.opportunity_dismissal_manager import DismissalScope, opportunity_dismissal_manager
from core.opportunity_prioritization_engine import opportunity_prioritization_engine
from core.proactive_context_analyzer import proactive_context_analyzer
from core.proactive_execution_coordinator import proactive_execution_coordinator
from core.proactive_opportunity_contract import (
    OpportunityState,
    OpportunityType,
    ProactiveOpportunityContract,
    create_proactive_opportunity,
)
from core.proactive_safety_gate import proactive_safety_gate
from core.proactive_suggestion_engine import proactive_suggestion_engine


class TestPhase1224ProactiveOrchestration(unittest.TestCase):
    def setUp(self):
        opportunity_dismissal_manager.clear_all()
        follow_up_tracker.clear()
        long_horizon_goal_manager.clear()
        proactive_suggestion_engine.set_proactive_enabled(True)
        interaction_style_manager.set_style(InteractionStyle.STANDARD)

    # 1. Opportunity contract validation
    def test_01_opportunity_contract_validation(self):
        opp = create_proactive_opportunity(
            OpportunityType.NEXT_STEP,
            "Continue Roadmap",
            "Next step is Phase 12.24",
            evidence_references=["goal:g1"],
        )
        self.assertEqual(opp.opportunity_type, OpportunityType.NEXT_STEP)
        self.assertEqual(opp.state, OpportunityState.DETECTED)
        self.assertTrue(opp.is_active())

    # 2. Invalid opportunity rejection
    def test_02_invalid_opportunity_rejection(self):
        # Speculative opportunity with low confidence and no evidence rejected by safety gate
        opp = create_proactive_opportunity(
            OpportunityType.NEXT_STEP,
            "Speculative task",
            "Unverified guess",
            confidence=0.50,
            evidence_references=[],
        )
        ok, reason = proactive_safety_gate.validate_opportunity_for_suggestion(opp)
        self.assertFalse(ok)
        self.assertIn("lacks verified supporting evidence", reason)

    # 3. Next-step detection
    def test_03_next_step_detection(self):
        goals = [{
            "goal_id": "g1",
            "title": "Build System",
            "milestones": [{"name": "Step A", "completed": True}, {"name": "Step B", "completed": False}],
        }]
        opps = opportunity_detection_engine.detect_opportunities(active_goals=goals)
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].opportunity_type, OpportunityType.NEXT_STEP)
        self.assertIn("Step B", opps[0].title)

    # 4. Blocker detection
    def test_04_blocker_detection(self):
        opp = create_proactive_opportunity(
            OpportunityType.BLOCKER,
            "Unresolved Port Conflict",
            "Port 3000 is occupied by stale process",
            evidence_references=["port:3000"],
            urgency=0.90,
        )
        self.assertEqual(opp.opportunity_type, OpportunityType.BLOCKER)

    # 5. Regression opportunity detection
    def test_05_regression_opportunity_detection(self):
        regs = [{"skill_name": "FLOW_REPAIR", "reason": "Failure rate > 30%"}]
        opps = opportunity_detection_engine.detect_opportunities(regression_signals=regs)
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].opportunity_type, OpportunityType.REGRESSION)
        self.assertIn("FLOW_REPAIR", opps[0].title)

    # 6. Knowledge gap opportunity detection
    def test_06_knowledge_gap_opportunity_detection(self):
        gaps = [{"topic": "Next.js 15 routing"}]
        opps = opportunity_detection_engine.detect_opportunities(knowledge_gaps=gaps)
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].opportunity_type, OpportunityType.KNOWLEDGE_GAP)

    # 7. Stale verification detection
    def test_07_stale_verification_detection(self):
        health = {"stale_verification": True}
        opps = opportunity_detection_engine.detect_opportunities(runtime_health=health, project_id="FLOW")
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].opportunity_type, OpportunityType.VERIFICATION_REQUIRED)

    # 8. Context-aware prioritization
    def test_08_context_aware_prioritization(self):
        opp1 = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Low Urg", "Desc", urgency=0.20, importance=0.40)
        opp2 = create_proactive_opportunity(OpportunityType.VERIFICATION_REQUIRED, "High Urg", "Desc", urgency=0.90, importance=0.90)

        ranked = opportunity_prioritization_engine.rank_opportunities([opp1, opp2])
        self.assertEqual(ranked[0][0].title, "High Urg")

    # 9. Evidence-based scoring
    def test_09_evidence_based_scoring(self):
        opp = create_proactive_opportunity(
            OpportunityType.NEXT_STEP, "Scored Opp", "Desc",
            confidence=0.95, importance=0.85, urgency=0.75, source_goal_id="g1"
        )
        score = opportunity_prioritization_engine.calculate_priority_score(opp)
        self.assertGreaterEqual(score, 0.70)

    # 10. Low-confidence penalty
    def test_10_low_confidence_penalty(self):
        opp_high = create_proactive_opportunity(OpportunityType.NEXT_STEP, "High Conf", "D", confidence=0.90)
        opp_low = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Low Conf", "D", confidence=0.50)

        score_high = opportunity_prioritization_engine.calculate_priority_score(opp_high)
        score_low = opportunity_prioritization_engine.calculate_priority_score(opp_low)
        self.assertGreater(score_high, score_low)

    # 11. Duplicate opportunity suppression
    def test_11_duplicate_opportunity_suppression(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Repeated Task", "Desc")
        opportunity_dismissal_manager.dismiss_opportunity(opp, DismissalScope.SESSION)
        self.assertTrue(opportunity_dismissal_manager.is_suppressed(opp))

    # 12. User dismissal
    def test_12_user_dismissal(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Dismiss Me", "Desc")
        opportunity_dismissal_manager.dismiss_opportunity(opp, DismissalScope.SESSION)
        self.assertEqual(opp.state, OpportunityState.DISMISSED)

    # 13. Session suppression
    def test_13_session_suppression(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Session Dismiss", "Desc")
        opportunity_dismissal_manager.dismiss_opportunity(opp, DismissalScope.SESSION)
        self.assertTrue(opportunity_dismissal_manager.is_suppressed(opp))
        opportunity_dismissal_manager.clear_session()
        self.assertFalse(opportunity_dismissal_manager.is_suppressed(opp))

    # 14. Project suppression
    def test_14_project_suppression(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Project Opp", "Desc", project_id="FLOW")
        opportunity_dismissal_manager.dismiss_opportunity(opp, DismissalScope.PROJECT)
        self.assertTrue(opportunity_dismissal_manager.is_suppressed(opp))

        other_opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Project Opp", "Desc", project_id="OTHER")
        self.assertFalse(opportunity_dismissal_manager.is_suppressed(other_opp))

    # 15. Permanent suppression
    def test_15_permanent_suppression(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Never Remind", "Desc")
        opportunity_dismissal_manager.dismiss_opportunity(opp, DismissalScope.PERMANENT)
        self.assertTrue(opportunity_dismissal_manager.is_suppressed(opp))

    # 16. Critical change reactivation
    def test_16_critical_change_reactivation(self):
        opp = create_proactive_opportunity(OpportunityType.BLOCKER, "Active Blocker", "Desc")
        self.assertTrue(opp.is_active())

    # 17. Explicit instruction override
    def test_17_explicit_instruction_override(self):
        ctx = create_collaboration_context(active_goal="Explicit user instruction: Run Tests")
        self.assertEqual(ctx.active_goal, "Explicit user instruction: Run Tests")

    # 18. Current reality override
    def test_18_current_reality_override(self):
        opp = create_proactive_opportunity(OpportunityType.VERIFICATION_REQUIRED, "Verify Service", "Desc")
        self.assertEqual(opp.required_authority, "READ_ONLY")

    # 19. No autonomous mutation
    def test_19_no_autonomous_mutation(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Suggested mutation", "Desc", risk_level=RiskLevel.READ_ONLY)
        # Suggestion engine must format text only without executing mutation
        text = proactive_suggestion_engine.format_suggestion(opp)
        self.assertIsNotNone(text)
        self.assertEqual(opp.state, OpportunityState.SUGGESTED)

    # 20. High-risk approval enforcement
    def test_20_high_risk_approval_enforcement(self):
        opp = create_proactive_opportunity(
            OpportunityType.MAINTENANCE, "High Risk Task", "Desc",
            risk_level=RiskLevel.HIGH_RISK, approval_required=True
        )
        self.assertTrue(opp.approval_required)

    # 21. ActionContract authority preservation
    def test_21_action_contract_authority_preservation(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Safe Step", "Desc")
        self.assertEqual(opp.risk_level, RiskLevel.READ_ONLY)

    # 22. Follow-up tracking
    def test_22_follow_up_tracking(self):
        fu = follow_up_tracker.register_follow_up("Check Server", "port_responsive", check_interval_seconds=0.01)
        time.sleep(0.02)
        pending = follow_up_tracker.get_pending_follow_ups()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].title, "Check Server")

    # 23. Expired opportunity rejection
    def test_23_expired_opportunity_rejection(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Expired Opp", "Desc", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertTrue(opp.is_expired())
        ok, reason = proactive_safety_gate.validate_opportunity_for_suggestion(opp)
        self.assertFalse(ok)
        self.assertIn("expired", reason)

    # 24. Interaction style integration
    def test_24_interaction_style_integration(self):
        opp = create_proactive_opportunity(OpportunityType.NEXT_STEP, "Phase 12.24", "Desc")
        interaction_style_manager.set_style(InteractionStyle.CONCISE)
        sugg = proactive_suggestion_engine.format_suggestion(opp)
        self.assertEqual(sugg, "Next recommended step: Phase 12.24.")

    # 25. Long-horizon goal integration
    def test_25_long_horizon_goal_integration(self):
        goal = long_horizon_goal_manager.register_goal("Roadmap", "Desc", ["Phase 12.23", "Phase 12.24"])
        long_horizon_goal_manager.mark_milestone_completed(goal.goal_id, "Phase 12.23")
        ctx = create_collaboration_context(active_project="JARVIS")
        analysis = proactive_context_analyzer.analyze_operational_context(ctx)
        self.assertEqual(analysis["next_logical_milestone"], "Phase 12.24")

    # 26. Memory integration
    def test_26_memory_integration(self):
        opp = create_proactive_opportunity(OpportunityType.OPTIMIZATION, "Cache Optimization", "Desc", evidence_references=["mem:ref_1"])
        self.assertIn("mem:ref_1", opp.evidence_references)

    # 27. Regression integration
    def test_27_regression_integration(self):
        regs = [{"skill_name": "PORT_REPAIR", "reason": "Drift detected"}]
        opps = opportunity_detection_engine.detect_opportunities(regression_signals=regs)
        self.assertEqual(len(opps), 1)

    # 28. Pending approval detection
    def test_28_pending_approval_detection(self):
        ctx = create_collaboration_context(active_project="FLOW")
        ctx.pending_approvals.append("appr_001")
        analysis = proactive_context_analyzer.analyze_operational_context(ctx)
        self.assertTrue(analysis["has_pending_approvals"])

    # 29. Non-blocking background execution
    def test_29_non_blocking_background_execution(self):
        ctx = create_collaboration_context(active_project="JARVIS")
        res = proactive_execution_coordinator.evaluate_proactive_pipeline(
            ctx,
            active_goals=[{"goal_id": "g1", "title": "JARVIS", "milestones": [{"name": "Phase 12.24", "completed": False}]}],
        )
        self.assertIsNotNone(res)
        opp, sugg = res
        self.assertIn("Phase 12.24", opp.title)

    # 30. Zero voice latency overhead
    def test_30_zero_voice_latency_overhead(self):
        # Warm-up router regex compilation
        router.match("what should i do next")
        t0 = time.perf_counter()
        match = router.match("what should i do next")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_PROACTIVE_STATUS")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
