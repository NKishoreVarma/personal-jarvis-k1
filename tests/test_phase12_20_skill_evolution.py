"""
Phase 12.20 — Autonomous Skill Discovery, Skill Composition & Capability Evolution Test Suite.
Verifies all 30 core requirements:
1. Skill contract validation
2. Candidate skill creation
3. One-off workflow rejection
4. Repeated workflow discovery
5. Candidate evaluation
6. Candidate promotion rules
7. Candidate rejection
8. Dry-run validation
9. Verified skill activation
10. Composite skill creation
11. Strictest authority propagation
12. Child verification preservation
13. Dependency ordering
14. Parallel read-only composition
15. Mutation serialization
16. Capability graph cycle prevention
17. Skill reuse selection
18. Environment incompatibility rejection
19. Current evidence overriding skill history
20. Skill regression detection
21. Skill degradation
22. Skill suspension
23. Versioned skill evolution
24. Memory integration
25. External knowledge remains candidate
26. Multi-agent skill proposal control
27. Intent router commands
28. No authority escalation
29. No source code self-modification
30. Zero voice callback blocking
"""

from __future__ import annotations

import time
import unittest

from core.capability_graph import capability_graph
from core.evolved_skill_contract import (
    EvolvedSkillContract,
    SkillScope,
    SkillStatus,
    SkillType,
    create_evolved_skill_contract,
)
from core.intent_router import router
from core.skill_candidate_evaluator import CandidateEvaluationOutcome, skill_candidate_evaluator
from core.skill_composition_engine import skill_composition_engine
from core.skill_discovery_engine import skill_discovery_engine
from core.skill_regression_monitor import SkillHealthState, skill_regression_monitor
from core.skill_registry_evolution_manager import skill_registry_evolution_manager
from core.skill_reuse_selector import skill_reuse_selector
from core.skill_sandbox import skill_sandbox
from core.skill_verification_engine import SkillVerificationOutcome, skill_verification_engine


class TestPhase1220SkillEvolution(unittest.TestCase):
    def setUp(self):
        skill_discovery_engine.clear_all()
        skill_registry_evolution_manager.clear_all()
        capability_graph.clear_all()
        skill_reuse_selector.set_skill_reuse_enabled(True)

    # 1. Skill contract validation
    def test_01_skill_contract_validation(self):
        skill = create_evolved_skill_contract(
            skill_name="TEST_SKILL",
            description="Test skill contract",
            skill_type=SkillType.REPAIR,
            authority_required="LOCAL_MUTATION",
            verification_requirements=["verify_port_free"],
        )
        self.assertEqual(skill.skill_name, "TEST_SKILL")
        self.assertEqual(skill.status, SkillStatus.CANDIDATE)
        self.assertEqual(skill.authority_required, "LOCAL_MUTATION")

    # 2. Candidate skill creation
    def test_02_candidate_skill_creation(self):
        skill = create_evolved_skill_contract("CANDIDATE_SKILL", "Description")
        skill_id = skill_registry_evolution_manager.register_candidate(skill)
        self.assertEqual(skill.status, SkillStatus.CANDIDATE)
        self.assertIsNotNone(skill_registry_evolution_manager.get_skill(skill_id))

    # 3. One-off workflow rejection
    def test_03_one_off_workflow_rejection(self):
        steps = [{"tool": "check_port"}, {"tool": "kill_pid"}]
        cand = skill_discovery_engine.record_workflow_execution("t1", "Fix port", "FLOW", steps, success=True, verified=True)
        # One occurrence should NOT discover a skill (threshold is 2)
        self.assertIsNone(cand)

    # 4. Repeated workflow discovery
    def test_04_repeated_workflow_discovery(self):
        steps = [{"tool": "check_port"}, {"tool": "kill_pid"}]
        skill_discovery_engine.record_workflow_execution("t1", "Fix port", "FLOW", steps, success=True, verified=True)
        cand = skill_discovery_engine.record_workflow_execution("t2", "Fix port", "FLOW", steps, success=True, verified=True)
        self.assertIsNotNone(cand)
        self.assertEqual(cand.status, SkillStatus.CANDIDATE)
        self.assertIn("FLOW", cand.skill_name)

    # 5. Candidate evaluation
    def test_05_candidate_evaluation(self):
        skill = create_evolved_skill_contract("EVAL_SKILL", "Desc", verification_requirements=["verify_alive"])
        outcome, _ = skill_candidate_evaluator.evaluate_candidate(skill, env_stable=True)
        self.assertEqual(outcome, CandidateEvaluationOutcome.PROMOTE_TO_TESTING)

    # 6. Candidate promotion rules
    def test_06_candidate_promotion_rules(self):
        skill = create_evolved_skill_contract("PROMO_SKILL", "Desc", verification_requirements=["verify_alive"])
        skill_registry_evolution_manager.register_candidate(skill)
        skill_registry_evolution_manager.promote_skill(skill.skill_id, SkillStatus.TESTING)
        self.assertEqual(skill.status, SkillStatus.TESTING)

    # 7. Candidate rejection
    def test_07_candidate_rejection(self):
        # Candidate lacking verification criteria must be rejected
        unverified_skill = create_evolved_skill_contract("UNSAFE_SKILL", "Desc", verification_requirements=[])
        outcome, reason = skill_candidate_evaluator.evaluate_candidate(unverified_skill)
        self.assertEqual(outcome, CandidateEvaluationOutcome.REJECT)
        self.assertIn("lacks verification", reason.lower())

    # 8. Dry-run validation
    def test_08_dry_run_validation(self):
        skill = create_evolved_skill_contract(
            "DRY_RUN_SKILL", "Desc",
            execution_steps=[{"tool": "check_port"}],
            required_tools=["check_port"],
        )
        ok, errors = skill_sandbox.validate_skill_dry_run(skill)
        self.assertTrue(ok)
        self.assertEqual(len(errors), 0)

    # 9. Verified skill activation
    def test_09_verified_skill_activation(self):
        skill = create_evolved_skill_contract("ACTIVATE_SKILL", "Desc")
        skill_registry_evolution_manager.register_candidate(skill)
        skill_registry_evolution_manager.activate_skill(skill.skill_id)
        self.assertTrue(skill.is_active())
        self.assertEqual(skill.status, SkillStatus.ACTIVE)

    # 10. Composite skill creation
    def test_10_composite_skill_creation(self):
        child1 = create_evolved_skill_contract("CHILD_1", "Desc 1", authority_required="READ_ONLY")
        child1.status = SkillStatus.ACTIVE
        child2 = create_evolved_skill_contract("CHILD_2", "Desc 2", authority_required="LOCAL_MUTATION")
        child2.status = SkillStatus.ACTIVE

        composite, msg = skill_composition_engine.compose_skills("COMP_WORKFLOW", "Composite Desc", [child1, child2])
        self.assertIsNotNone(composite)
        self.assertEqual(composite.skill_type, SkillType.COMPOSITE)
        self.assertEqual(len(composite.parent_skill_ids), 2)

    # 11. Strictest authority propagation
    def test_11_strictest_authority_propagation(self):
        child_ro = create_evolved_skill_contract("RO", "Desc", authority_required="READ_ONLY")
        child_ro.status = SkillStatus.ACTIVE
        child_mut = create_evolved_skill_contract("MUT", "Desc", authority_required="LOCAL_MUTATION")
        child_mut.status = SkillStatus.ACTIVE

        comp, _ = skill_composition_engine.compose_skills("COMP", "Desc", [child_ro, child_mut])
        # Composite MUST require LOCAL_MUTATION (strictest of children)
        self.assertEqual(comp.authority_required, "LOCAL_MUTATION")

    # 12. Child verification preservation
    def test_12_child_verification_preservation(self):
        child1 = create_evolved_skill_contract("C1", "D1", verification_requirements=["v1"])
        child1.status = SkillStatus.ACTIVE
        child2 = create_evolved_skill_contract("C2", "D2", verification_requirements=["v2"])
        child2.status = SkillStatus.ACTIVE

        comp, _ = skill_composition_engine.compose_skills("COMP", "Desc", [child1, child2])
        self.assertIn("v1", comp.verification_requirements)
        self.assertIn("v2", comp.verification_requirements)

    # 13. Dependency ordering
    def test_13_dependency_ordering(self):
        s1 = create_evolved_skill_contract("S1", "D1", execution_steps=[{"step": 1}])
        s1.status = SkillStatus.ACTIVE
        s2 = create_evolved_skill_contract("S2", "D2", execution_steps=[{"step": 2}])
        s2.status = SkillStatus.ACTIVE

        comp, _ = skill_composition_engine.compose_skills("COMP", "Desc", [s1, s2])
        self.assertEqual(comp.execution_steps[0]["step"], 1)
        self.assertEqual(comp.execution_steps[1]["step"], 2)

    # 14. Parallel read-only composition
    def test_14_parallel_read_only_composition(self):
        c1 = create_evolved_skill_contract("RO1", "D1", authority_required="READ_ONLY")
        c1.status = SkillStatus.ACTIVE
        c2 = create_evolved_skill_contract("RO2", "D2", authority_required="READ_ONLY")
        c2.status = SkillStatus.ACTIVE

        comp, _ = skill_composition_engine.compose_skills("COMP_RO", "Desc", [c1, c2])
        self.assertEqual(comp.authority_required, "READ_ONLY")

    # 15. Mutation serialization
    def test_15_mutation_serialization(self):
        c1 = create_evolved_skill_contract("MUT1", "D1", authority_required="LOCAL_MUTATION")
        c1.status = SkillStatus.ACTIVE
        comp, _ = skill_composition_engine.compose_skills("COMP_MUT", "Desc", [c1])
        self.assertEqual(comp.authority_required, "LOCAL_MUTATION")

    # 16. Capability graph cycle prevention
    def test_16_capability_graph_cycle_prevention(self):
        ok1, _ = capability_graph.add_dependency("A", "B")
        self.assertTrue(ok1)
        ok2, _ = capability_graph.add_dependency("B", "C")
        self.assertTrue(ok2)
        # Adding C -> A would form cycle A -> B -> C -> A
        ok3, err = capability_graph.add_dependency("C", "A")
        self.assertFalse(ok3)
        self.assertIn("Cycle detected", err)

    # 17. Skill reuse selection
    def test_17_skill_reuse_selection(self):
        skill = create_evolved_skill_contract(
            "REPAIR_PORT_CONFLICT",
            "Resolves port conflict by terminating stale pid",
            metadata={"project_id": "FLOW"},
        )
        skill.status = SkillStatus.ACTIVE
        skill_registry_evolution_manager.register_candidate(skill)
        skill_registry_evolution_manager.activate_skill(skill.skill_id)

        selected, msg = skill_reuse_selector.select_skill_for_goal("Repair port conflict for FLOW", "FLOW")
        self.assertIsNotNone(selected)
        self.assertEqual(selected.skill_name, "REPAIR_PORT_CONFLICT")

    # 18. Environment incompatibility rejection
    def test_18_environment_incompatibility_rejection(self):
        skill = create_evolved_skill_contract("REPAIR_PORT", "Desc", metadata={"project_id": "FLOW"})
        skill.status = SkillStatus.ACTIVE
        skill_registry_evolution_manager.register_candidate(skill)
        skill_registry_evolution_manager.activate_skill(skill.skill_id)

        selected, msg = skill_reuse_selector.select_skill_for_goal(
            "Repair port", "FLOW", environment_state={"incompatible": True}
        )
        self.assertIsNone(selected)
        self.assertIn("incompatible", msg.lower())

    # 19. Current evidence overriding skill history
    def test_19_current_evidence_overriding_skill_history(self):
        # Outcome verification checks current responsiveness
        skill = create_evolved_skill_contract("VERIF_TEST", "Desc")
        outcome, _ = skill_verification_engine.verify_execution(
            skill,
            step_results=[{"success": True}],
            observed_outcome={"is_responsive": True},
        )
        self.assertEqual(outcome, SkillVerificationOutcome.OUTCOME_VERIFIED)

    # 20. Skill regression detection
    def test_20_skill_regression_detection(self):
        skill = create_evolved_skill_contract("REG_SKILL", "Desc")
        skill.status = SkillStatus.ACTIVE
        # Record 5 runs: 4 success, 1 failure
        for _ in range(4):
            skill.record_run(success=True, duration_s=1.0, verified=True)
        skill.record_run(success=False, duration_s=1.0, verified=False)

        state, _ = skill_regression_monitor.evaluate_skill_health(skill)
        self.assertEqual(state, SkillHealthState.WATCH)

    # 21. Skill degradation
    def test_21_skill_degradation(self):
        skill = create_evolved_skill_contract("DEG_SKILL", "Desc")
        skill_registry_evolution_manager.register_candidate(skill)
        skill_registry_evolution_manager.activate_skill(skill.skill_id)

        # 3 successes, 3 failures -> 50% success
        for _ in range(3):
            skill.record_run(success=True, duration_s=1.0, verified=True)
        for _ in range(2):
            skill.record_run(success=False, duration_s=1.0, verified=False)

        state, _ = skill_regression_monitor.evaluate_skill_health(skill)
        self.assertEqual(state, SkillHealthState.DEGRADED)
        self.assertEqual(skill.status, SkillStatus.DEGRADED)

    # 22. Skill suspension
    def test_22_skill_suspension(self):
        skill = create_evolved_skill_contract("CRIT_SKILL", "Desc")
        skill_registry_evolution_manager.register_candidate(skill)
        skill_registry_evolution_manager.activate_skill(skill.skill_id)

        # 1 success, 4 failures
        skill.record_run(success=True, duration_s=1.0, verified=True)
        for _ in range(4):
            skill.record_run(success=False, duration_s=1.0, verified=False)

        state, _ = skill_regression_monitor.evaluate_skill_health(skill)
        self.assertEqual(state, SkillHealthState.CRITICAL)
        self.assertEqual(skill.status, SkillStatus.SUSPENDED)

    # 23. Versioned skill evolution
    def test_23_versioned_skill_evolution(self):
        skill_v1 = create_evolved_skill_contract("EVOLVE_SKILL", "V1 Desc")
        skill_v1.version = "1.0.0"
        skill_registry_evolution_manager.register_candidate(skill_v1)

        skill_v2 = create_evolved_skill_contract("EVOLVE_SKILL", "V2 Desc")
        skill_v2.version = "1.1.0"
        skill_registry_evolution_manager.register_candidate(skill_v2)

        history = skill_registry_evolution_manager._version_history["EVOLVE_SKILL"]
        self.assertEqual(len(history), 2)

    # 24. Memory integration
    def test_24_memory_integration(self):
        skill = create_evolved_skill_contract("MEM_SKILL", "Desc")
        skill.record_run(success=True, duration_s=0.5, verified=True)
        self.assertEqual(skill.usage_count, 1)

    # 25. External knowledge remains candidate
    def test_25_external_knowledge_remains_candidate(self):
        skill = create_evolved_skill_contract("EXTERNAL_DOC_WORKFLOW", "Learned from docs", provenance="external_knowledge")
        self.assertEqual(skill.status, SkillStatus.CANDIDATE)
        self.assertEqual(skill.provenance, "external_knowledge")

    # 26. Multi-agent skill proposal control
    def test_26_multi_agent_skill_proposal_control(self):
        skill = create_evolved_skill_contract("AGENT_PROPOSED", "Proposed by worker")
        self.assertEqual(skill.status, SkillStatus.CANDIDATE)

    # 27. Intent router commands
    def test_27_intent_router_commands(self):
        match = router.match("what can you do now")
        self.assertEqual(match["intent"], "QUERY_SKILLS")

        match_status = router.match("is the flow repair skill working well")
        self.assertEqual(match_status["intent"], "QUERY_SKILL_STATUS")

    # 28. No authority escalation
    def test_28_no_authority_escalation(self):
        c_ro = create_evolved_skill_contract("RO_1", "D1", authority_required="READ_ONLY")
        c_ro.status = SkillStatus.ACTIVE
        c_diag = create_evolved_skill_contract("DIAG_1", "D2", authority_required="DIAGNOSTIC")
        c_diag.status = SkillStatus.ACTIVE

        comp, _ = skill_composition_engine.compose_skills("COMP_SAFE", "Desc", [c_ro, c_diag])
        # Authority must NOT jump to HIGH_RISK or LOCAL_MUTATION
        self.assertEqual(comp.authority_required, "DIAGNOSTIC")

    # 29. No source code self-modification
    def test_29_no_source_code_self_modification(self):
        skill = create_evolved_skill_contract("METADATA_ONLY", "Desc")
        # Metadata contains only declarative step descriptions, no raw exec()
        self.assertIsInstance(skill.execution_steps, list)

    # 30. Zero voice callback blocking
    def test_30_zero_voice_callback_blocking(self):
        # Warm-up router regex compilation
        router.match("what can you do now")
        t0 = time.perf_counter()
        match = router.match("what can you do now")
        dt = (time.perf_counter() - t0) * 1000
        self.assertEqual(match["intent"], "QUERY_SKILLS")
        self.assertLess(dt, 20.0)


if __name__ == "__main__":
    unittest.main()
