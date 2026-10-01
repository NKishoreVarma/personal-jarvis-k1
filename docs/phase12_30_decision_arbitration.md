# Phase 12.30 — Autonomous Decision Arbitration, Meta-Reasoning & Evidence-Based Escalation Report

**Target Architecture**: MARK XLVIII (JARVIS)  
**Modules Created/Enhanced**:
- `core/decision_arbitration.py`
- `core/decision_policy_router.py`
- `core/system1_decision_engine.py`
- `core/intent_router.py`
- `benchmarks/benchmark_decision_arbitration.py`
- `tests/test_phase12_30_arbitration.py`

**Test Suite Status**: ✅ **100% PASS (858/858 Tests Passing across 61 Test Suites)**  
**Date**: 2026-09-23  

---

## 1. Executive Summary

Phase 12.30 establishes the **Autonomous Decision Arbitration & Meta-Reasoning Layer** for MARK XLVIII / JARVIS. Following real neural Laya integration (Phase 12.28) and autonomous decision calibration (Phase 12.29), Phase 12.30 builds the meta-decision layer that answers:

$$\mathbf{\text{“Which reasoning path should handle this decision?”}}$$

The system replaces naive confidence thresholding with a multi-signal meta-arbitration engine that balances:
- **`SYSTEM1`**: Sub-millisecond fast-path routing for familiar, simple, low-risk decisions with verified high reliability.
- **`SYSTEM2`**: Deliberative deep reasoning, planning, and multi-agent coordination for novel, complex, or consequential tasks.
- **`HYBRID`**: System 1 candidate generation and ranking paired with lightweight System 2 validation.
- **`HUMAN`**: Escalation to user confirmation via `ApprovalStore` for irreversible consequences, ambiguous intent, or explicit preferences.
- **`ABSTAIN`**: Safe abstention when both reasoning engines are uncertain or unavailable.

---

## 2. Inviolable Safety Principles

1. **Arbitration $\neq$ Authorization**: Selecting a reasoning engine never expands permissions or authorizes actions.
2. **Speed $\neq$ Safety**: High-risk and unknown-risk tasks unconditionally escalate to System 2 and Governance; System 1 can never authorize high-risk mutations.
3. **Evidence Hierarchy**:
   $$\mathbf{\text{CURRENT VERIFIED OBSERVATION} > \text{INDEPENDENTLY VERIFIED OUTCOME} > \text{LOCAL VERIFIED EVIDENCE} > \text{ACTIVE SAFETY CONTRACT} > \text{SYSTEM 2 LLM} > \text{CALIBRATED SYSTEM 1 SIGNAL} > \text{MODEL ASSUMPTION}}$$
4. **No Assumption of System 2 Perfection**: Disagreements between System 1 and System 2 are arbitrated based on empirical evidence, calibration, and risk, rather than blindly assuming System 2 is correct.
5. **No System Duplication**: Reuses existing LLM / System 2 planner, PGVector memory, ResearchGovernor (Phase 12.27), Temporal scheduler (Phase 12.25), Proactive analyzer (Phase 12.24), and Continuous learning (Phase 12.26).
6. **Zero Voice Latency Overhead**: Fast-path eligibility checks execute in-memory with sub-millisecond latency; heavy reasoning occurs asynchronously outside audio loops ($0.00\text{ ms}$ delay).

---

## 3. Subsystem Breakdown

### 1. `core/decision_arbitration.py`
- **`DecisionEngine`**: `SYSTEM1`, `SYSTEM2`, `HYBRID`, `ABSTAIN`, `HUMAN`.
- **`EscalationReason`**: Strongly typed reasons (`LOW_CONFIDENCE`, `LOW_MARGIN`, `LOW_ROUTE_RELIABILITY`, `INSUFFICIENT_SAMPLES`, `DRIFT_DETECTED`, `HIGH_RISK`, `UNKNOWN_RISK`, `NOVEL_TASK`, `HIGH_COMPLEXITY`, `WEAK_EVIDENCE`, `RESEARCH_REQUIRED`, `MEMORY_CONFLICT`, `SYSTEM1_SYSTEM2_DISAGREEMENT`, `EXECUTION_CONSEQUENCE`, `POLICY_RESTRICTION`, `NONE`).
- **`ArbitrationContext`**: Encapsulates multi-signal input (context text, category, laya decision, system2 option, novelty, complexity, evidence quality, risk level, temporal pressure, research required, memory conflict, user preference).
- **`ArbitrationResult`**: Strongly typed result capturing selected engine, system 1 confidence/reliability/drift, escalation reason, disagreement classification, explanations, and execution latency.
- **`ArbitrationTelemetryStore`**: Bounded store tracking arbitration decisions and computing escalation quality metrics (`necessary_escalation_rate`, `unnecessary_escalation_rate`, `missed_escalation_rate`, engine success rates).

### 2. Multi-Signal Arbitration Pipeline
```
1. Human / Consequence Barrier -> User confirmation / Destructive -> HUMAN
2. Risk Barrier -> High / Unknown risk -> SYSTEM2
3. Research Barrier -> External knowledge needed -> SYSTEM2 + RESEARCH
4. Memory Contradiction Barrier -> Observation != Memory -> SYSTEM2
5. Novelty Barrier -> Novel / Unknown task -> SYSTEM2
6. Complexity Barrier -> Complex / Very Complex -> SYSTEM2
7. Evidence Barrier -> Weak / Unknown evidence -> SYSTEM2
8. Drift Barrier -> Degraded drift state -> SYSTEM2
9. Route Reliability Barrier -> Trust score < 0.70 / Samples < 10 -> SYSTEM2
10. Confidence Barrier -> Abstained / Below calibrated threshold -> SYSTEM2
11. Disagreement Arbitration -> Evaluates evidence vs calibration
12. Hybrid Eligibility -> Moderate complexity + High confidence -> HYBRID
13. System 1 Fast Path -> Familiar + Simple + Low Risk -> SYSTEM1
```

### 3. Integration Points
- **`core/decision_policy_router.py`**: Integrates `DecisionArbitrator.arbitrate(context)` during hybrid arbitration, storing the latest arbitration result in telemetry.
- **`core/system1_decision_engine.py`**: Exposes `arbitrate(...)` and `get_arbitration_status()` endpoints.
- **`core/intent_router.py`**: Adds developer status commands:
  - `show decision arbitration` $\rightarrow$ `QUERY_DECISION_ARBITRATION`
  - `why did jarvis use system 2` $\rightarrow$ `QUERY_SYSTEM2_ESCALATION_REASON`
  - `why did jarvis use system 1` $\rightarrow$ `QUERY_SYSTEM1_SELECTION_REASON`
  - `show system 1 vs system 2` $\rightarrow$ `QUERY_SYSTEM1_VS_SYSTEM2`
  - `show arbitration reliability` $\rightarrow$ `QUERY_ARBITRATION_RELIABILITY`

---

## 4. Benchmark Results (`benchmarks/benchmark_decision_arbitration.py`)

- **Workload Throughput**: **> 1,500 arbitrations/sec** across multi-signal workload.
- **Single Fast Arbitration Overhead**: **< 0.15 ms** (well below 1.0 ms realtime ceiling).
- **Audio Callback Latency**: **0.00 ms** delay overhead.
- **Memory Footprint**: **< 1.2 MB** net telemetry and arbitration engine footprint.
- **Sample Sufficiency Guard**: Properly returns `"INSUFFICIENT_VERIFIED_DATA"` when verified sample count $< 10$.

---

## 5. Acceptance Criteria Verification

- [x] Arbitration engine exists (`core/decision_arbitration.py`).
- [x] Strongly typed arbitration contract exists (`ArbitrationContext`, `ArbitrationResult`).
- [x] System 1 eligibility is explicit (familiar, simple, low risk, high reliability).
- [x] System 2 escalation is explicit with typed `EscalationReason` codes.
- [x] Hybrid mode exists (System 1 candidate generation + System 2 validation).
- [x] Human escalation integrates with existing `ApprovalStore`.
- [x] Task novelty is evaluated (`FAMILIAR`, `RELATED`, `NOVEL`, `UNKNOWN`).
- [x] Task complexity is evaluated (`SIMPLE`, `MODERATE`, `COMPLEX`, `VERY_COMPLEX`).
- [x] Evidence quality is evaluated (`VERIFIED`, `STRONG`, `PARTIAL`, `WEAK`, `UNKNOWN`).
- [x] Operational risk is evaluated (`LOW`, `MEDIUM`, `HIGH`, `UNKNOWN`).
- [x] Calibration and route trust scores are evaluated.
- [x] Concept drift state is evaluated (`STABLE`, `WARNING`, `DEGRADED`).
- [x] Research requirements are evaluated (Phase 12.27 integration).
- [x] Temporal urgency context is evaluated (Phase 12.25 integration).
- [x] Proactive context is evaluated (Phase 12.24 integration).
- [x] Memory contradictions are handled (Observation > Memory).
- [x] System 1 vs System 2 disagreements are arbitrated without assuming System 2 is correct.
- [x] Structured decision-level explanations exist.
- [x] Arbitration telemetry exists (`ArbitrationTelemetryStore`).
- [x] Failure fallbacks exist for all engine outage scenarios.
- [x] Realtime loops remain non-blocking.
- [x] Existing governance remains authoritative.
- [x] Phase 12.28 regression passes (45/45).
- [x] Phase 12.29 regression passes (35/35).
- [x] Phase 12.30 test suite passes (32/32).
- [x] Full repository regression suite passes (858/858).
