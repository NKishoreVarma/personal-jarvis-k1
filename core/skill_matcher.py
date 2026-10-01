"""
Skill Matcher for MARK XLVIII / JARVIS.
Ranks candidate learned skills against incoming goals, observations, and problem patterns.
Assigns match levels: NO_MATCH, WEAK_MATCH, POSSIBLE_MATCH, STRONG_MATCH.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from core.skill_contract import SkillContract, SkillMatchLevel, SkillStatus
from core.skill_registry import skill_registry


class SkillMatcher:
    """
    Evaluates and ranks learned skills for potential execution.
    """

    def score_skill(
        self,
        skill: SkillContract,
        goal_text: str,
        project_name: Optional[str] = None,
        problem_category: Optional[str] = None,
    ) -> Tuple[SkillMatchLevel, float]:
        """
        Calculates multi-dimensional match score for a skill.
        """
        if not skill.is_executable():
            return SkillMatchLevel.NO_MATCH, 0.0

        score = 0.0
        q_tokens = set(goal_text.lower().split())

        # 1. Goal Pattern & Name similarity
        corpus = f"{skill.skill_name} {skill.description} {skill.goal_pattern}".lower()
        if q_tokens:
            matches = sum(1 for tok in q_tokens if tok in corpus)
            score += (matches / len(q_tokens)) * 0.4

        # 2. Problem Pattern similarity
        if problem_category and skill.problem_pattern:
            if problem_category.lower() == skill.problem_pattern.lower():
                score += 0.4
            elif problem_category.lower() in skill.problem_pattern.lower():
                score += 0.2

        # 3. Project Match
        if project_name and skill.project_scope:
            if project_name.lower() == skill.project_scope.lower():
                score += 0.3

        # 4. Confidence & Verification history
        score += skill.confidence * 0.2
        score += min(0.2, skill.success_count * 0.05)
        score += min(0.2, skill.reuse_count * 0.05)

        # 5. Penalties
        score -= skill.failure_count * 0.25
        if skill.status == SkillStatus.DEGRADED:
            score -= 0.3

        score = max(0.0, score)

        if score >= 0.75:
            return SkillMatchLevel.STRONG_MATCH, score
        elif score >= 0.50:
            return SkillMatchLevel.POSSIBLE_MATCH, score
        elif score >= 0.25:
            return SkillMatchLevel.WEAK_MATCH, score
        else:
            return SkillMatchLevel.NO_MATCH, score

    def match_skills(
        self,
        goal_text: str,
        project_name: Optional[str] = None,
        problem_category: Optional[str] = None,
        min_level: SkillMatchLevel = SkillMatchLevel.WEAK_MATCH,
    ) -> List[Tuple[SkillMatchLevel, float, SkillContract]]:
        """
        Returns ranked candidate skills meeting or exceeding min_level.
        """
        candidates = skill_registry.list_skills()
        scored: List[Tuple[SkillMatchLevel, float, SkillContract]] = []

        level_weights = {
            SkillMatchLevel.NO_MATCH: 0,
            SkillMatchLevel.WEAK_MATCH: 1,
            SkillMatchLevel.POSSIBLE_MATCH: 2,
            SkillMatchLevel.STRONG_MATCH: 3,
        }

        for s in candidates:
            lvl, sc = self.score_skill(s, goal_text, project_name=project_name, problem_category=problem_category)
            if level_weights[lvl] >= level_weights[min_level]:
                scored.append((lvl, sc, s))

        # Sort descending by score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def get_best_match(
        self,
        goal_text: str,
        project_name: Optional[str] = None,
        problem_category: Optional[str] = None,
    ) -> Optional[SkillContract]:
        """
        Retrieves top strong matching skill if available.
        """
        matches = self.match_skills(
            goal_text=goal_text,
            project_name=project_name,
            problem_category=problem_category,
            min_level=SkillMatchLevel.STRONG_MATCH,
        )
        return matches[0][2] if matches else None


# Global singleton instance
skill_matcher = SkillMatcher()
