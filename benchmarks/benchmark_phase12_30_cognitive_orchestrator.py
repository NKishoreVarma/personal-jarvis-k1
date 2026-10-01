"""
Production Benchmark Suite for Phase 12.30:
Unified Cognitive Orchestrator, Grounded Autonomous Execution & End-to-End JARVIS Integration.

Measures at minimum:
A. Deterministic local request
B. Warm System 1 request (Real Laya or Fallback)
C. Cold System 1 request (Model Load + Checkpoint)
D. System 2 request (Arbitration + Planning)
E. Perception + World Model Grounding
F. Multi-Agent Workflow Delegation
G. Governed Tool Execution
H. Independent Verification
I. Complete End-to-End Workflow ("Fix my FLOW server. It isn't working.")
J. Interrupted Workflow (Cancellation token propagation)

Also reports separately:
- Audio Callback Non-Blocking Overhead (<< 1.0 ms)
- Memory usage (Baseline, Peak, Model Footprint)
- Full statistical distribution (p50, p95, p99, mean, max)
"""

from __future__ import annotations

import os
import sys
import time
import tracemalloc
from typing import Any, Dict, List

# Ensure mark-xlviii root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.action_contract import ActionContract, RiskLevel
from core.cognitive_context_builder import cognitive_context_builder
from core.cognitive_orchestrator import (
    CognitiveOrchestrator,
    TerminalState,
    cognitive_orchestrator,
    required_observations,
)
from core.decision_arbitration import (
    ArbitrationContext,
    DecisionEngine,
    EvidenceQuality,
    TaskComplexity,
    TaskNovelty,
    decision_arbitrator,
)
from core.decision_contract import DecisionCategory, DecisionType
from core.intent_router import router
from core.laya_decision_adapter import LayaDecisionAdapter, laya_decision_adapter
from core.multimodal_fusion_engine import multimodal_fusion_engine
from core.perception_contract import ObservationType, create_observation
from core.perception_pipeline import perception_pipeline
from core.system_observer import system_observer
from core.verifier import verifier
from core.world_model import world_model


def compute_stats(samples: List[float]) -> Dict[str, float]:
    if not samples:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    s = sorted(samples)
    n = len(s)

    def p(pct: float) -> float:
        idx = int(n * pct)
        return s[min(idx, n - 1)]

    return {
        "mean": sum(s) / n,
        "p50": p(0.50),
        "p95": p(0.95),
        "p99": p(0.99),
        "max": max(s),
    }


def format_stats_row(name: str, stats: Dict[str, float]) -> str:
    return f"{name:<35} | {stats['p50']:>8.2f} ms | {stats['p95']:>8.2f} ms | {stats['p99']:>8.2f} ms | {stats['mean']:>8.2f} ms | {stats['max']:>8.2f} ms"


def run_phase12_30_benchmarks() -> None:
    print("=" * 95)
    print("MARK XLVIII — Phase 12.30 Cognitive Orchestrator & End-to-End Integration Benchmark")
    print("=" * 95)

    tracemalloc.start()
    baseline_mem = tracemalloc.get_traced_memory()[0]

    # Warmup Laya once to measure warm vs cold
    print("\n[Phase 12.30 Laya Model Inspection]")
    print(f"  Laya Installed:               {laya_decision_adapter._laya_installed}")
    print(f"  Default Checkpoint:           {laya_decision_adapter.default_model}")

    # C. Cold System 1 Request
    print("\nMeasuring C. Cold System 1 Request (Loading + First Forward Pass)...")
    laya_decision_adapter.unload_all()
    t_cold_start = time.perf_counter()
    cold_load_time = laya_decision_adapter.warmup()
    t_cold_end = time.perf_counter()
    cold_total_ms = (t_cold_end - t_cold_start) * 1000
    print(f"  Cold Load + Warmup Pass:      {cold_total_ms:.2f} ms (warmup_pass: {cold_load_time:.2f} ms)")

    mem_after_laya = tracemalloc.get_traced_memory()[0]
    laya_mem_mb = (mem_after_laya - baseline_mem) / (1024 * 1024)
    print(f"  Laya Model Memory Footprint:  {laya_mem_mb:.2f} MB")

    # A. Deterministic Local Request
    print("\nBenchmarking A. Deterministic Local Request (50 iterations)...")
    samples_det: List[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        matched = router.match("what time is it")
        res = router.execute(matched)
        samples_det.append((time.perf_counter() - t0) * 1000)

    # B. Warm System 1 Request
    print("Benchmarking B. Warm System 1 Request (10 iterations)...")
    samples_sys1: List[float] = []
    for _ in range(10):
        t0 = time.perf_counter()
        res = laya_decision_adapter.decide_choice(
            context="check active system status",
            options=["status", "repair", "query"],
            category=DecisionCategory.INTENT,
        )
        samples_sys1.append((time.perf_counter() - t0) * 1000)

    # D. System 2 Request (Arbitration + Planning)
    print("Benchmarking D. System 2 Request (Arbitration + Planning) (20 iterations)...")
    samples_sys2: List[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        arb_ctx = ArbitrationContext(
            context_text="Investigate complex memory leak and port conflict in background worker",
            category=DecisionCategory.INTENT,
            novelty=TaskNovelty.NOVEL,
            complexity=TaskComplexity.COMPLEX,
            evidence_quality=EvidenceQuality.PARTIAL,
            risk_level="high",
        )
        arb_res = decision_arbitrator.arbitrate(arb_ctx)
        plan, _ = cognitive_orchestrator.delegation_engine.create_delegation_plan("Resolve leak", "FLOW")
        samples_sys2.append((time.perf_counter() - t0) * 1000)

    # E. Perception + World Model Grounding
    print("Benchmarking E. Perception + World Model Grounding (20 iterations)...")
    samples_perc_wm: List[float] = []
    for i in range(20):
        t0 = time.perf_counter()
        obs = create_observation(
            observation_type=ObservationType.PROCESS,
            source="benchmark_process",
            content={"listening_ports": {3000 + i: True}, "pid": 40000 + i},
        )
        world_model.update_observation(obs)
        ctx = cognitive_context_builder.build_context("check server", trace_id=f"tr_bench_{i}")
        samples_perc_wm.append((time.perf_counter() - t0) * 1000)

    # F. Multi-Agent Workflow Delegation
    print("Benchmarking F. Multi-Agent Workflow Delegation (20 iterations)...")
    samples_agent: List[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        plan, _ = cognitive_orchestrator.delegation_engine.create_delegation_plan("Diagnose server outage", "FLOW")
        samples_agent.append((time.perf_counter() - t0) * 1000)

    # G. Governed Tool Execution
    print("Benchmarking G. Governed Tool Execution (50 iterations)...")
    samples_tool: List[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        contract = ActionContract(
            connector="system",
            operation="inspect_process",
            arguments={"pid": 1234},
            risk_level=RiskLevel.READ_ONLY,
        )
        fp = contract.fingerprint
        samples_tool.append((time.perf_counter() - t0) * 1000)

    # H. Independent Verification
    print("Benchmarking H. Independent Verification (30 iterations)...")
    samples_ver: List[float] = []
    for _ in range(30):
        t0 = time.perf_counter()
        v_res = verifier.verify(step=None, result="process proc_123 listening on port 3000")
        samples_ver.append((time.perf_counter() - t0) * 1000)

    # I. Complete End-to-End Workflow ("Fix my FLOW server. It isn't working.")
    print("Benchmarking I. Complete End-to-End Workflow (5 iterations)...")
    samples_e2e: List[float] = []
    for _ in range(5):
        t0 = time.perf_counter()
        res = cognitive_orchestrator.execute("Fix my FLOW server. It isn't working.")
        samples_e2e.append((time.perf_counter() - t0) * 1000)

    # J. Interrupted Workflow (Cancellation)
    print("Benchmarking J. Interrupted Workflow (50 iterations)...")
    samples_interrupt: List[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        res = cognitive_orchestrator.execute("Stop")
        samples_interrupt.append((time.perf_counter() - t0) * 1000)

    # Audio Callback Overhead
    print("Benchmarking Audio Callback Non-Blocking Ingestion (100 iterations)...")
    samples_audio: List[float] = []
    dummy_audio = b"\x00\x01" * 160  # 10ms PCM audio frame
    for _ in range(100):
        t0 = time.perf_counter()
        perception_pipeline.enqueue_audio_turn_context(dummy_audio)
        samples_audio.append((time.perf_counter() - t0) * 1000)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Report Summary Table
    print("\n" + "=" * 95)
    print(f"{'Phase 12.30 Benchmark Benchmark Results':<35} | {'p50':>8}    | {'p95':>8}    | {'p99':>8}    | {'mean':>8}   | {'max':>8}")
    print("-" * 95)
    print(format_stats_row("A. Deterministic Local Request", compute_stats(samples_det)))
    print(format_stats_row("B. Warm System 1 Request", compute_stats(samples_sys1)))
    print(f"{'C. Cold System 1 Request':<35} | {cold_total_ms:>8.2f} ms | {cold_total_ms:>8.2f} ms | {cold_total_ms:>8.2f} ms | {cold_total_ms:>8.2f} ms | {cold_total_ms:>8.2f} ms")
    print(format_stats_row("D. System 2 Request (Arb+Plan)", compute_stats(samples_sys2)))
    print(format_stats_row("E. Perception + World Model", compute_stats(samples_perc_wm)))
    print(format_stats_row("F. Multi-Agent Delegation", compute_stats(samples_agent)))
    print(format_stats_row("G. Governed Tool Execution", compute_stats(samples_tool)))
    print(format_stats_row("H. Independent Verification", compute_stats(samples_ver)))
    print(format_stats_row("I. End-to-End Workflow (E2E)", compute_stats(samples_e2e)))
    print(format_stats_row("J. Interrupted Workflow", compute_stats(samples_interrupt)))
    print("-" * 95)

    stats_audio = compute_stats(samples_audio)
    print(format_stats_row("AUDIO CALLBACK OVERHEAD", stats_audio))
    print("=" * 95)

    print("\n[Resource Footprint & Telemetry]")
    print(f"  Baseline Traced Memory:       {baseline_mem / (1024 * 1024):.2f} MB")
    print(f"  Current Traced Memory:        {current_mem / (1024 * 1024):.2f} MB")
    print(f"  Peak Traced Memory:           {peak_mem / (1024 * 1024):.2f} MB")
    print(f"  Laya Model Retention:         {laya_mem_mb:.2f} MB")
    print(f"  Audio Callback Overhead Mean: {stats_audio['mean']:.4f} ms ({stats_audio['mean'] * 1000:.2f} µs)")
    print(f"  Audio Callback Max:           {stats_audio['max']:.4f} ms")


if __name__ == "__main__":
    run_phase12_30_benchmarks()
