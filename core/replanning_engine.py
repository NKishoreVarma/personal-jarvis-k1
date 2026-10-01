"""
Replanning Engine for MARK XLVIII / JARVIS.
Handles recovery and replanning when verification fails:
- Records failure evidence.
- Marks disproven hypotheses.
- Selects the next most likely explanation.
- Ensures the next plan differs materially from prior failed sequences.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.diagnostic_planner import diagnostic_planner
from core.reasoning_state import HypothesisStatus, ReasoningState
from core.repair_planner import repair_planner


class ReplanningEngine:
    """
    Coordinates self-correction and plan generation after execution or verification failure.
    """

    def replan(
        self,
        state: ReasoningState,
        failed_action: str,
        error_details: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Generates a new, non-identical execution sequence or returns None if reasoning limits are exceeded.
        """
        state.cycle_count += 1
        if state.cycle_count > state.max_cycles:
            print(f"[REPLANNER] 🛑 Maximum reasoning cycles ({state.max_cycles}) reached for goal '{state.goal.goal_id}'.")
            return None

        # 1. Invalidate current hypothesis with failure evidence
        if state.selected_hypothesis:
            state.selected_hypothesis.add_contradiction(f"Action '{failed_action}' failed: {error_details}")
            print(f"[REPLANNER] ⚠️ Invalided hypothesis: '{state.selected_hypothesis.description}' (conf={state.selected_hypothesis.confidence:.2f})")

        # 2. Select next active hypothesis
        next_hyp = state.select_best_hypothesis()
        if not next_hyp:
            print(f"[REPLANNER] ❌ No remaining valid hypotheses for goal '{state.goal.goal_id}'.")
            return None

        print(f"[REPLANNER] 🔄 Next hypothesis selected: '{next_hyp.description}' (cat={next_hyp.category}, conf={next_hyp.confidence:.2f})")

        # 3. Create fresh diagnostic and repair steps
        target_project = state.goal.target_project or "Project"
        diag_steps = diagnostic_planner.create_diagnostic_plan(next_hyp, target_project)
        repair_steps = repair_planner.create_repair_plan(next_hyp, target_project, {"error": error_details})

        new_plan = diag_steps + repair_steps
        state.plan = new_plan
        return new_plan


# Global singleton instance
replanning_engine = ReplanningEngine()
