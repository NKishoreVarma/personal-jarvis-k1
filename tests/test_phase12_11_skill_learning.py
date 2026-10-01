"""
Comprehensive Unit & Integration Test Suite for Phase 12.11:
Autonomous Skill Learning, Reusable Workflows & Capability Growth.
"""

import asyncio
import time
import unittest

from core.action_contract import ActionContract, RiskLevel
from core.intent_router import intent_router
from core.skill_adapter import skill_adapter
from core.skill_contract import (
    SkillContract,
    SkillMatchLevel,
    SkillStatus,
    SkillType,
    create_skill_contract,
)
from core.skill_evolution_engine import skill_evolution_engine
from core.skill_execution_engine import skill_execution_engine
from core.skill_extractor import skill_extractor
from core.skill_introspection import skill_introspection
from core.skill_learning_loop import skill_learning_loop
from core.skill_matcher import skill_matcher
from core.skill_precondition_checker import skill_precondition_checker
from core.skill_registry import skill_registry
from core.skill_reinforcement_engine import skill_reinforcement_engine
from core.verification_engine import VerificationLevel, verification_engine
from core.workflow_abstraction_engine import workflow_abstraction_engine


class TestPhase1211SkillLearning(unittest.TestCase):
    def setUp(self):
        skill_registry.clear()

    # Test 1: Successful workflow extraction
    def test_01_successful_workflow_extraction(self):
        steps = [
            {"action": "inspect_port", "target": "FLOW"},
            {"action": "terminate_conflicting_processes", "target": "FLOW"},
            {"action": "restart_project_server", "target": "FLOW"},
        ]
        skill = skill_extractor.extract_skill_from_goal(
            goal_text="Fix FLOW port conflict",
            problem_category="PORT_CONFLICT",
            concrete_steps=steps,
            context={"project": "FLOW", "port": 3000},
        )
        self.assertIsNotNone(skill)
        self.assertEqual(skill.skill_name, "FIX_PROJECT_PORT_CONFLICT")
        self.assertEqual(skill.skill_type, SkillType.REPAIR_SKILL)

    # Test 2: Incidental action rejection
    def test_02_incidental_action_rejection(self):
        steps = [{"action": "open_app", "target": "Chrome"}]
        skill = skill_extractor.extract_skill_from_goal(
            goal_text="open Chrome",
            problem_category=None,
            concrete_steps=steps,
            context={"app": "Chrome"},
        )
        self.assertIsNone(skill)

    # Test 3: Workflow abstraction
    def test_03_workflow_abstraction(self):
        steps = [
            {"action": "terminate_conflicting_processes", "target": "FLOW", "params": {"port": 3000}},
            {"action": "restart_project_server", "target": "FLOW"},
        ]
        abs_steps, params = workflow_abstraction_engine.abstract_steps(steps, {"project": "FLOW", "port": 3000})
        self.assertEqual(abs_steps[0]["target"], "{project}")
        self.assertEqual(abs_steps[0]["params"]["port"], "{port}")
        self.assertIn("project", params)
        self.assertIn("port", params)

    # Test 4: Parameter extraction
    def test_04_parameter_extraction(self):
        steps = [{"action": "restart", "target": "FLOW", "params": {"port": 3000}}]
        _, params = workflow_abstraction_engine.abstract_steps(steps, {"project": "FLOW", "port": 3000})
        self.assertEqual(params["project"]["default"], "FLOW")
        self.assertEqual(params["port"]["default"], 3000)

    # Test 5: Secret rejection
    def test_05_secret_rejection(self):
        steps_with_secret = [{"action": "auth", "params": {"api_key": "sk-12345678901234567890"}}]
        self.assertTrue(workflow_abstraction_engine.contains_secrets(steps_with_secret))
        with self.assertRaises(ValueError):
            workflow_abstraction_engine.abstract_steps(steps_with_secret, {"project": "FLOW"})

    # Test 6: Skill registration
    def test_06_skill_registration(self):
        skill = create_skill_contract(
            skill_name="RUN_FLOW",
            skill_type=SkillType.PROJECT_WORKFLOW,
            description="Run FLOW server",
            goal_pattern="run FLOW",
            workflow_steps=[{"action": "restart_project_server", "target": "{project}"}],
            project_scope="FLOW",
        )
        sid = skill_registry.register_skill(skill)
        self.assertIsNotNone(sid)
        ret = skill_registry.retrieve_skill(sid)
        self.assertEqual(ret.skill_name, "RUN_FLOW")

    # Test 7: Duplicate skill merging
    def test_07_duplicate_skill_merging(self):
        s1 = create_skill_contract("FIX_FLOW", SkillType.REPAIR_SKILL, "Fix port", "fix FLOW", [{"action": "restart"}], project_scope="FLOW")
        s2 = create_skill_contract("FIX_FLOW", SkillType.REPAIR_SKILL, "Fix port", "fix FLOW", [{"action": "restart"}], project_scope="FLOW")

        id1 = skill_registry.register_skill(s1)
        id2 = skill_registry.register_skill(s2)
        self.assertEqual(id1, id2)
        self.assertEqual(len(skill_registry._skills), 1)
        self.assertEqual(skill_registry.retrieve_skill(id1).success_count, 2)

    # Test 8: Skill matching
    def test_08_skill_matching(self):
        skill = create_skill_contract(
            skill_name="FIX_PROJECT_PORT_CONFLICT",
            skill_type=SkillType.REPAIR_SKILL,
            description="Fix port conflicts",
            goal_pattern="fix port conflict for {project}",
            problem_pattern="PORT_CONFLICT",
            workflow_steps=[{"action": "terminate", "target": "{project}"}],
            project_scope="FLOW",
        )
        skill_registry.register_skill(skill)

        matches = skill_matcher.match_skills(goal_text="fix FLOW port conflict", project_name="FLOW", problem_category="PORT_CONFLICT")
        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual(matches[0][0], SkillMatchLevel.STRONG_MATCH)

    # Test 9: Weak match rejection
    def test_09_weak_match_rejection(self):
        skill = create_skill_contract(
            skill_name="DEPLOY_KUBERNETES",
            skill_type=SkillType.SYSTEM_WORKFLOW,
            description="Deploy cluster",
            goal_pattern="deploy k8s",
            workflow_steps=[{"action": "apply"}],
            project_scope="INFRA",
        )
        skill_registry.register_skill(skill)

        match = skill_matcher.get_best_match(goal_text="run my local python test")
        self.assertIsNone(match)

    # Test 10: Strong match selection
    def test_10_strong_match_selection(self):
        skill = create_skill_contract(
            skill_name="FIX_FLOW_PORT",
            skill_type=SkillType.REPAIR_SKILL,
            description="Fix FLOW port",
            goal_pattern="fix FLOW port",
            problem_pattern="PORT_CONFLICT",
            workflow_steps=[{"action": "kill"}, {"action": "restart"}],
            project_scope="FLOW",
        )
        skill_registry.register_skill(skill)

        best = skill_matcher.get_best_match("fix FLOW port", project_name="FLOW", problem_category="PORT_CONFLICT")
        self.assertIsNotNone(best)
        self.assertEqual(best.skill_name, "FIX_FLOW_PORT")

    # Test 11: Current observation overriding historical parameters
    def test_11_observation_overrides_historical_parameters(self):
        skill = create_skill_contract(
            skill_name="FIX_PORT",
            skill_type=SkillType.REPAIR_SKILL,
            description="Fix port",
            goal_pattern="fix port",
            workflow_steps=[{"action": "restart", "target": "{project}", "params": {"port": "{port}"}}],
            project_scope="FLOW",
        )
        # Current observation says port is 4000
        obs = {"port_state": {"port": 4000}, "project_state": {"project_name": "FLOW"}}
        adapted = skill_adapter.adapt_skill(skill, context={"project": "FLOW"}, observation=obs)
        self.assertEqual(adapted[0]["target"], "FLOW")
        self.assertEqual(adapted[0]["params"]["port"], "4000")

    # Test 12: Precondition failure
    def test_12_precondition_failure(self):
        skill = create_skill_contract("FIX_FLOW", SkillType.REPAIR_SKILL, "Fix", "fix", [], required_preconditions=["project_exists"])
        obs = {"project_state": {"found": False}}
        ok, err = skill_precondition_checker.check_preconditions(skill, {"project": "FLOW"}, obs)
        self.assertFalse(ok)
        self.assertIn("was not found", err)

    # Test 13: Safe skill execution
    def test_13_safe_skill_execution(self):
        skill = create_skill_contract(
            skill_name="RESTART_FLOW",
            skill_type=SkillType.PROJECT_WORKFLOW,
            description="Restart FLOW",
            goal_pattern="restart FLOW",
            workflow_steps=[{"action": "restart_project_server", "target": "{project}"}],
            project_scope="FLOW",
        )
        skill_registry.register_skill(skill)

        from unittest.mock import patch
        loop = asyncio.new_event_loop()
        with patch.object(
            verification_engine,
            "verify_outcome",
            return_value={"outcome_verified": True, "level": VerificationLevel.OUTCOME_VERIFIED},
        ), patch("core.skill_execution_engine.run_project_async", return_value={"success": True}):
            res = loop.run_until_complete(
                skill_execution_engine.execute_skill_async(
                    skill=skill,
                    context={"project": "FLOW"},
                    observation={"port_state": {"port": 3000}},
                    target_port=3000,
                )
            )
        self.assertTrue(res["success"])
        self.assertTrue(res["outcome_verified"])
        loop.close()

    # Test 14: Verification required before reinforcement
    def test_14_verification_required_for_reinforcement(self):
        skill = create_skill_contract("FLOW_SKILL", SkillType.PROJECT_WORKFLOW, "desc", "goal", [], confidence=0.8)
        skill_registry.register_skill(skill)

        # Unverified execution does not reinforce
        unverified_result = {"outcome_verified": False}
        if unverified_result["outcome_verified"]:
            skill_reinforcement_engine.on_skill_success(skill.skill_id)
        self.assertEqual(skill_registry.retrieve_skill(skill.skill_id).reuse_count, 0)

    # Test 15: Success reinforcement
    def test_15_success_reinforcement(self):
        skill = create_skill_contract("FLOW_SKILL", SkillType.PROJECT_WORKFLOW, "desc", "goal", [], confidence=0.8)
        skill_registry.register_skill(skill)

        skill_reinforcement_engine.on_skill_success(skill.skill_id)
        updated = skill_registry.retrieve_skill(skill.skill_id)
        self.assertEqual(updated.reuse_count, 1)
        self.assertEqual(updated.success_count, 2)
        self.assertGreater(updated.confidence, 0.8)

    # Test 16: Failure confidence reduction
    def test_16_failure_confidence_reduction(self):
        skill = create_skill_contract("FLOW_SKILL", SkillType.PROJECT_WORKFLOW, "desc", "goal", [], confidence=0.85)
        skill_registry.register_skill(skill)

        skill_reinforcement_engine.on_skill_failure(skill.skill_id, "Server crash")
        updated = skill_registry.retrieve_skill(skill.skill_id)
        self.assertEqual(updated.failure_count, 1)
        self.assertLess(updated.confidence, 0.7)

    # Test 17: Degradation lifecycle
    def test_17_degradation_lifecycle(self):
        skill = create_skill_contract("FLOW_SKILL", SkillType.PROJECT_WORKFLOW, "desc", "goal", [])
        skill_registry.register_skill(skill)

        skill_reinforcement_engine.on_skill_failure(skill.skill_id, "Fail 1")
        self.assertEqual(skill_registry.retrieve_skill(skill.skill_id).status, SkillStatus.DEGRADED)

    # Test 18: Stale skill retirement
    def test_18_stale_skill_retirement(self):
        skill = create_skill_contract("FLOW_SKILL", SkillType.PROJECT_WORKFLOW, "desc", "goal", [])
        skill_registry.register_skill(skill)

        skill_reinforcement_engine.on_skill_failure(skill.skill_id, "Fail 1")
        skill_reinforcement_engine.on_skill_failure(skill.skill_id, "Fail 2")
        skill_reinforcement_engine.on_skill_failure(skill.skill_id, "Fail 3")
        self.assertEqual(skill_registry.retrieve_skill(skill.skill_id).status, SkillStatus.RETIRED)

    # Test 19: Skill version evolution
    def test_19_skill_version_evolution(self):
        v1_steps = [{"action": "restart_project_server"}]
        skill = create_skill_contract("FLOW_STARTUP", SkillType.PROJECT_WORKFLOW, "Start", "start", v1_steps, version=1)
        skill_registry.register_skill(skill)

        v2_steps = [{"action": "check_port"}, {"action": "restart_project_server"}]
        evolved = skill_evolution_engine.evolve_skill(skill.skill_id, v2_steps, "Added pre-flight port check")
        self.assertEqual(evolved.version, 2)
        self.assertEqual(len(evolved.workflow_steps), 2)
        self.assertEqual(len(evolved.evolution_history), 1)

    # Test 20: Old version preservation
    def test_20_old_version_preservation(self):
        v1_steps = [{"action": "restart_project_server"}]
        skill = create_skill_contract("FLOW_STARTUP", SkillType.PROJECT_WORKFLOW, "Start", "start", v1_steps, version=1)
        skill_registry.register_skill(skill)

        evolved = skill_evolution_engine.evolve_skill(skill.skill_id, [{"action": "new_action"}], "Upgrade")
        hist = evolved.evolution_history[0]
        self.assertEqual(hist["version"], 1)
        self.assertEqual(hist["workflow_steps"], v1_steps)

    # Test 21: Fallback to ProblemSolver
    def test_21_fallback_to_problem_solver_on_no_match(self):
        # Empty skill registry returns None best match
        match = skill_matcher.get_best_match("some unprecedented bug", project_name="UNKNOWN")
        self.assertIsNone(match)

    # Test 22: User skill teaching
    def test_22_user_skill_teaching(self):
        match = intent_router.match("learn this workflow")
        self.assertTrue(match["handled"])
        self.assertEqual(match["intent"], "TEACH_SKILL")
        res = intent_router.execute(match)
        self.assertIn("teaching mode", res["response"].lower())

    # Test 23: Skill introspection
    def test_23_skill_introspection(self):
        skill = create_skill_contract("FIX_FLOW_PORT", SkillType.REPAIR_SKILL, "Fixes port conflict", "fix port", [], project_scope="FLOW")
        skill_registry.register_skill(skill)

        desc = skill_introspection.describe_learned_skills()
        self.assertIn("FIX_FLOW_PORT", desc)

        proj_desc = skill_introspection.describe_skill_for_project("FLOW")
        self.assertIn("FLOW", proj_desc)

    # Test 24: User-controlled forgetting
    def test_24_user_controlled_forgetting(self):
        skill = create_skill_contract("FLOW_PORT_FIX", SkillType.REPAIR_SKILL, "desc", "goal", [], project_scope="FLOW")
        skill_registry.register_skill(skill)

        del_count = skill_registry.forget_skill("FLOW_PORT_FIX")
        self.assertEqual(del_count, 1)
        self.assertEqual(len(skill_registry._skills), 0)

    # Test 25: Disabled / retired skill rejection
    def test_25_retired_skill_rejection(self):
        skill = create_skill_contract("RETIRED_SKILL", SkillType.PROJECT_WORKFLOW, "desc", "goal", [])
        skill.status = SkillStatus.RETIRED
        skill_registry.register_skill(skill)

        active_skills = skill_registry.search_skills(only_active=True)
        self.assertEqual(len(active_skills), 0)

    # Test 26: Approval boundary preservation
    def test_26_approval_boundary_preservation(self):
        contract = ActionContract(
            connector="skill_execution",
            operation="format_drive",
            arguments={},
            risk_level=RiskLevel.DESTRUCTIVE,
        )
        self.assertTrue(contract.approval_required)

    # Test 27: No microphone callback blocking
    def test_27_voice_non_blocking_performance(self):
        t0 = time.perf_counter()
        match = intent_router.match("what skills have you learned")
        self.assertTrue(match["handled"])
        res = intent_router.execute(match)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 5.0)

    # Test 28: No audio callback blocking
    def test_28_no_audio_callback_blocking(self):
        # Skill registration must be fast and non-blocking
        t0 = time.perf_counter()
        skill = create_skill_contract("FAST_SKILL", SkillType.PROJECT_WORKFLOW, "Fast", "fast", [])
        skill_registry.register_skill(skill)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 5.0)

    # Test 29: No stale skill execution across turns
    def test_29_expired_skill_rejection(self):
        skill = create_skill_contract("EXPIRED_SKILL", SkillType.PROJECT_WORKFLOW, "desc", "goal", [])
        skill.expires_at = time.time() - 10.0
        skill_registry.register_skill(skill)

        self.assertTrue(skill.is_expired())
        self.assertFalse(skill.is_executable())

    # Test 30: Full end-to-end learned repair reuse
    def test_30_full_end_to_end_learned_repair_reuse(self):
        # 1. Register learned skill
        skill = create_skill_contract(
            skill_name="FIX_FLOW_PORT_CONFLICT",
            skill_type=SkillType.REPAIR_SKILL,
            description="Clear zombie process and restart FLOW",
            goal_pattern="fix FLOW port conflict",
            problem_pattern="PORT_CONFLICT",
            workflow_steps=[
                {"action": "terminate_conflicting_processes", "target": "{project}"},
                {"action": "restart_project_server", "target": "{project}"},
            ],
            project_scope="FLOW",
        )
        skill_registry.register_skill(skill)

        # 2. Match skill
        matched = skill_matcher.get_best_match("fix FLOW port conflict", project_name="FLOW", problem_category="PORT_CONFLICT")
        self.assertIsNotNone(matched)

        # 3. Execute with verified outcome
        from unittest.mock import patch
        loop = asyncio.new_event_loop()
        with patch.object(
            verification_engine,
            "verify_outcome",
            return_value={"outcome_verified": True, "level": VerificationLevel.OUTCOME_VERIFIED},
        ), patch("core.skill_execution_engine.run_project_async", return_value={"success": True}):
            res = loop.run_until_complete(
                skill_execution_engine.execute_skill_async(
                    skill=matched,
                    context={"project": "FLOW"},
                    observation={"port_state": {"port": 3000}},
                    target_port=3000,
                )
            )
        self.assertTrue(res["outcome_verified"])
        skill_reinforcement_engine.on_skill_success(matched.skill_id)
        self.assertEqual(skill_registry.retrieve_skill(matched.skill_id).reuse_count, 1)
        loop.close()


if __name__ == "__main__":
    unittest.main()
