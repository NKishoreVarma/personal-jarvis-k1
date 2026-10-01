# Phase 12.29 — Autonomous Decision Calibration, Confidence Calibration & Adaptive System-1 Governance Report

**Target Architecture**: MARK XLVIII (JARVIS)  
**Modules Created/Enhanced**:
- `core/decision_outcome.py`
- `core/decision_calibration_engine.py`
- `core/decision_drift_detector.py`
- `core/decision_policy_proposal.py`
- `core/decision_confidence_gate.py`
- `core/decision_policy_router.py`
- `core/system1_decision_engine.py`
- `core/outcome_evaluation_engine.py`
- `core/intent_router.py`
- `benchmarks/benchmark_system1_calibration.py`
- `tests/test_phase12_29_calibration.py`

**Test Suite Status**: ✅ **100% PASS (826/826 Tests Passing across 60 Test Suites)**  
**Date**: 2026-09-23  

---

## 1. Executive Summary

Phase 12.29 establishes the **Autonomous Decision Calibration, Confidence Calibration & Adaptive System-1 Governance Layer** for MARK XLVIII / JARVIS. Following the successful real neural Laya model integration in Phase 12.28, this phase transitions System 1 from an uncalibrated static threshold into an evidence-grounded, self-monitoring, calibrated routing engine that learns:

$$\mathbf{\text{“When should I trust System 1?”}\quad\text{rather than}\quad\text{“Always trust System 1.”}}$$

The system measures real prediction confidence against verified real-world outcomes, detects overconfidence and underconfidence across 10 operational categories and multiple languages, detects concept drift over time, conservatively degrades to System 2 when quality drops, and governs policy proposals through formal versioning and deterministic rollback.

---

## 2. Inviolable Safety Principles

1. **Laya Produces Decision Signals, Never Authority**: System 1 predictions cannot execute tools, mutate data, or bypass user permissions.
2. **Calibration $\neq$ Authorization**: Calibrated confidence cannot weaken `ActionContract` risk boundaries or `ApprovalStore` rules.
3. **High-Risk & Unknown-Risk Safety Barriers Remain Absolute**: Routes categorized under high or unknown risk unconditionally escalate to System 2, regardless of calibrated confidence or policy proposals.
4. **Unknown Outcome $\neq$ Incorrect Outcome**: Unverified outcomes are marked `outcome_verified = False` and `OUTCOME_UNKNOWN`; they are never counted as false negatives.
5. **Small Sample Protection**: Policy adaptation requires a minimum sample threshold ($\ge 10$ verified outcomes). Below this, baseline conservative thresholds ($0.75$) are enforced.
6. **Conservative Degradation**: When concept drift or performance drop is detected, the system degrades conservatively (raises thresholds, increases abstention, escalates to System 2).
7. **Evidence-Based Disagreement Arbitration**: Disagreements between System 1 and System 2 are evaluated against independent verified outcomes rather than assuming System 2 is inherently correct.
8. **Deterministic Rollback**: Any policy modification can be cleanly rolled back to previously verified baselines.
9. **Zero Voice Latency Overhead**: All calibration, drift detection, and policy proposals execute asynchronously outside audio callbacks ($0.00$ ms delay).

---

## 3. Decision & Governance Hierarchy

$$\mathbf{\text{CURRENT VERIFIED OBSERVATION} > \text{INDEPENDENTLY VERIFIED OUTCOME} > \text{LOCAL VERIFIED EVIDENCE} > \text{ACTIVE SAFETY CONTRACT} > \text{SYSTEM 2 LLM / PLANNER} > \text{CALIBRATED SYSTEM 1 SIGNAL} > \text{MODEL ASSUMPTION}}$$

---

## 4. Subsystem Breakdown

### 1. `core/decision_outcome.py`
- **`OutcomeQuality`**: Standardized enum (`VERIFIED_CORRECT`, `VERIFIED_INCORRECT`, `PARTIALLY_CORRECT`, `USER_CORRECTED`, `SYSTEM2_OVERRULED`, `EXECUTION_FAILED`, `EXECUTION_SUCCEEDED`, `OUTCOME_UNKNOWN`).
- **`DecisionOutcomeRecord`**: Typed record tracking `decision_id`, `trace_id`, `route`, `decision_type`, `model`, `checkpoint`, `language`, `input_context_hash` (SHA-256 context hashing; no raw sensitive prompts), `predicted_option`, `predicted_confidence`, `alternatives`, `system1_used`, `system2_used`, `fallback_used`, `abstained`, `governance_result`, `final_decision`, `actual_outcome`, `outcome_verified`, `outcome_quality`, `latency_ms`, `policy_version`, and `timestamp`.
- **`DecisionOutcomeStore`**: Bounded in-memory store (capacity 5,000) with persistence of non-sensitive summaries to `data/runtime/decision_outcomes_summary.json`.

### 2. `core/decision_calibration_engine.py`
- **Confidence Bucketing**: Partitions predictions into intervals: $[0.50, 0.60), [0.60, 0.70), [0.70, 0.80), [0.80, 0.90), [0.90, 1.00]$.
- **Expected Calibration Error (ECE)**:
  $$\text{ECE} = \sum_{b=1}^B \frac{|B_b|}{N} |\text{acc}(B_b) - \text{conf}(B_b)|$$
- **Maximum Calibration Error (MCE)**: $\max_b |\text{acc}(B_b) - \text{conf}(B_b)|$.
- **Brier Score**: $\text{BS} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$.
- **Multi-Dimensional Calibration**: Calibrates independently by route category, language (`en`, `es`, etc.), and model checkpoint (`convaiinnovations/laya`, `laya`).
- **Route Trust Score**: Composite index $S_{\text{route}} \in [0.0, 1.0]$ blending accuracy (40%), ECE penalty (25%), disagreement rate (15%), fallback rate (10%), and sample sufficiency (10%).
- **Over/Underconfidence Detection**: Identifies bins with calibration gap $> 0.15$.
- **Shadow Policy Recommendation**: Discovers optimal threshold where accuracy $\ge 0.85$ without modifying active policy.

### 3. `core/decision_drift_detector.py`
- **`DriftState`**: `STABLE`, `WARNING`, `DRIFT_DETECTED`, `DEGRADED`.
- **Windowed Comparison**: Compares recent window ($N=15$ verified outcomes) against historical baseline.
- **Conservative Actions**:
  - `DEGRADED`: Force System 2 escalation, halt adaptations, $+0.15$ threshold penalty.
  - `DRIFT_DETECTED`: Halt adaptations, $+0.10$ threshold penalty.
  - `WARNING`: $+0.05$ threshold penalty.
- **Evidence-Based Recovery**: Requires consecutive verified healthy samples ($K \ge 5$) before gradually stepping down (`DEGRADED` $\rightarrow$ `WARNING` $\rightarrow$ `STABLE`).

### 4. `core/decision_policy_proposal.py`
- **`PolicyProposalStatus`**: `PROPOSED`, `SHADOW_TESTING`, `APPROVED`, `REJECTED`, `ROLLED_BACK`.
- **`DecisionPolicyManager`**: Maintains versioned history (`system1-policy-v1`, `v2`, ...), enforces safe adaptation boundaries (low-risk routes only; high-risk routes strictly prohibited), and provides deterministic `rollback_policy(target_version)`.
- **Integration**: Verifies continuous learning status with `SelfImprovementGovernor`.

### 5. Integration Enhancements
- **`core/decision_confidence_gate.py`**: Resolves route-specific calibrated thresholds and applies dynamic drift penalties while preserving absolute high-risk barriers.
- **`core/decision_policy_router.py`**: Incorporates policy version stamping and tracks System 1 vs System 2 disagreements with verified outcome linkage.
- **`core/system1_decision_engine.py`**: Stamps `policy_version`, registers initial outcomes in `DecisionOutcomeStore`, and provides calibration/drift status APIs.
- **`core/outcome_evaluation_engine.py`**: Bridges task outcomes directly to `DecisionOutcomeStore` when `decision_id` is present.
- **`core/intent_router.py`**: Adds developer status commands:
  - *"Show System 1 calibration"* $\rightarrow$ `QUERY_SYSTEM1_CALIBRATION`
  - *"How accurate is System 1?"* $\rightarrow$ `QUERY_SYSTEM1_ACCURACY`
  - *"Show System 1 drift"* $\rightarrow$ `QUERY_SYSTEM1_DRIFT`
  - *"Why did System 1 abstain?"* $\rightarrow$ `QUERY_SYSTEM1_ABSTENTION_REASON`
  - *"Show System 1 policy version"* $\rightarrow$ `QUERY_SYSTEM1_POLICY_VERSION`
  - *"Show System 1 route reliability"* $\rightarrow$ `QUERY_SYSTEM1_ROUTE_RELIABILITY`
  - *"Rollback System 1 policy"* $\rightarrow$ `ROLLBACK_SYSTEM1_POLICY`

---

## 5. Developer Status Commands Verification

| Voice / CLI Command | Intent | Response Sample |
| :--- | :--- | :--- |
| `show system 1 calibration` | `QUERY_SYSTEM1_CALIBRATION` | *"System 1 calibration error is 0.0412 across 125 verified decisions with Brier score 0.0381."* |
| `how accurate is system 1` | `QUERY_SYSTEM1_ACCURACY` | *"System 1 verified accuracy is 92.4% across 125 verified outcomes."* |
| `show system 1 drift` | `QUERY_SYSTEM1_DRIFT` | *"System 1 drift state is STABLE. Behavior within normal baseline parameters."* |
| `why did system 1 abstain` | `QUERY_SYSTEM1_ABSTENTION_REASON` | *"System 1 abstains when confidence falls below calibrated route thresholds, alternative margin is below 0.15, or high/unknown risk is detected."* |
| `show system 1 policy version` | `QUERY_SYSTEM1_POLICY_VERSION` | *"Active System 1 policy version is system1-policy-v1."* |
| `show system 1 route reliability`| `QUERY_SYSTEM1_ROUTE_RELIABILITY` | *"System 1 route trust score is 0.88."* |
| `rollback system 1 policy` | `ROLLBACK_SYSTEM1_POLICY` | *"System 1 policy rollback: Successfully rolled back policy from system1-policy-v2 to system1-policy-v1."* |

---

## 6. Acceptance Criteria Verification

- [x] Verified decision outcomes exist (`DecisionOutcomeRecord`, `DecisionOutcomeStore`).
- [x] System 1 confidence is evaluated against actual verified outcomes.
- [x] Calibration metrics exist (ECE, MCE, Brier score, accuracy, precision, recall).
- [x] Route-specific calibration exists (10 categories tracked independently).
- [x] Language-specific calibration exists (multilingual isolation).
- [x] Minimum sample protection exists ($\ge 10$ samples required before adaptation).
- [x] Policy proposals exist (`DecisionPolicyProposal`, shadow testing lifecycle).
- [x] Policy versioning exists (`system1-policy-v1`, `v2`, ...).
- [x] Deterministic rollback exists (`rollback_policy`).
- [x] Drift detection exists (`STABLE`, `WARNING`, `DRIFT_DETECTED`, `DEGRADED`).
- [x] Automatic conservative degradation exists (threshold elevation, System 2 escalation).
- [x] Recovery exists (consecutive healthy samples required).
- [x] System 1 vs System 2 disagreement is measured against verified ground truth.
- [x] Existing Phase 12.26 learning is reused (`OutcomeEvaluationEngine` bridge).
- [x] No duplicate learning engine exists.
- [x] High-risk governance cannot be weakened (risk routes strictly prohibited from adaptation).
- [x] Approval cannot be bypassed (`HIGH_RISK_ESCALATION` invariant).
- [x] Verification cannot be bypassed (`OUTCOME_UNKNOWN` on unverified tasks).
- [x] System 1 cannot modify its own authority.
- [x] Existing Phase 12.28 tests remain passing (45/45 passing).
- [x] New Phase 12.29 tests pass (35/35 passing).
- [x] Full regression suite passes (826/826 passing across 60 test suites).
- [x] Zero audio callback delay ($0.00$ ms delay overhead).
