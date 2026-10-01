"""
Voice Latency Forensics & Diagnostic Benchmark for MARK XLVIII / JARVIS.
Captures timestamp-level forensics across all stages:
Wake word -> Speech -> VAD -> Endpoint -> Route -> Gemini TTFT -> Audio Queue -> Playback.
"""

import asyncio
import json
import os
import sys
import threading
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from core.timing import timer
from core.voice_metrics import VoiceEvent, voice_metrics
from main import JarvisLive
from ui import JarvisUI


def print_stage_breakdown(report: dict, title: str):
    print("\n" + "─" * 60)
    print(f"📊 LATENCY BREAKDOWN REPORT: {title}")
    print("─" * 60)
    meta = report.get("metadata", {})
    route_type = meta.get("route_type", "unknown")
    cmd_text = meta.get("command_text", "N/A")
    print(f"• Command: '{cmd_text}' | Route: {route_type}")

    deltas = report.get("stage_deltas_ms", {})
    cumul = report.get("cumulative_ms", {})

    print("\n[Cumulative Stage Timelines]")
    for stage, t_ms in cumul.items():
        print(f"  ├─ {stage:<30}: +{t_ms:>8.2f} ms")

    print("\n[Stage-by-Stage Latencies]")
    for delta_name, val_ms in deltas.items():
        if val_ms is not None:
            print(f"  ├─ {delta_name:<30}: {val_ms:>8.2f} ms ({val_ms/1000.0:>6.3f}s)")

    print("─" * 60 + "\n")


def run_diagnostics():
    print("=" * 65)
    print("🔍 RUNNING VOICE / AUDIO PIPELINE FORENSIC BENCHMARK")
    print("=" * 65)

    ui = JarvisUI("face.png")
    jarvis = JarvisLive(ui)

    def runner():
        asyncio.run(jarvis.run())

    t = threading.Thread(target=runner, daemon=True)
    t.start()

    print("⏳ Waiting for JARVIS to connect to Gemini API...")
    for _ in range(30):
        if jarvis.session is not None:
            break
        time.sleep(0.5)

    if jarvis.session is None:
        print("❌ Could not connect to Gemini API within timeout.")
        sys.exit(1)

    print("✅ JARVIS connected.\n")
    time.sleep(2)

    # 1. Benchmark: "Hello" (Gemini Live streaming route)
    print("\n" + "═" * 55)
    print("👉 TEST 1: 'Hello' (Gemini Live Stream)")
    print("═" * 55)
    t0 = time.monotonic()
    print(f"[AUDIO DEBUG] [{t0:.4f}s] audio sent to Gemini (input: 'Hello')")

    ui.on_text_command("Hello")

    # Wait for turn completion
    t_start = time.monotonic()
    while time.monotonic() - t_start < 90:
        time.sleep(0.1)
        if not timer.active and (time.monotonic() - t_start > 2.0):
            break
    print(f"[AUDIO DEBUG] [{time.monotonic():.4f}s] Turn finished for 'Hello'")

    report1 = voice_metrics.get_report()
    if report1:
        print_stage_breakdown(report1, "Test 1: Hello (Gemini Live)")

    time.sleep(2)

    # 2. Benchmark: "What time is it?" (Local Intent Router route)
    print("\n" + "═" * 55)
    print("👉 TEST 2: 'What time is it?' (Local Intent Router)")
    print("═" * 55)
    t1 = time.monotonic()
    print(f"[AUDIO DEBUG] [{t1:.4f}s] text command received (input: 'What time is it?')")

    ui.on_text_command("What time is it?")

    t_start = time.monotonic()
    while time.monotonic() - t_start < 90:
        time.sleep(0.1)
        if not timer.active and (time.monotonic() - t_start > 2.0):
            break
    print(f"[AUDIO DEBUG] [{time.monotonic():.4f}s] Turn finished for 'What time is it?'")

    report2 = voice_metrics.get_report()
    if report2:
        print_stage_breakdown(report2, "Test 2: What time is it? (Local Route)")

    print("\n" + "=" * 65)
    print("🏁 FORENSIC BENCHMARK COMPLETE")
    print("=" * 65)
    os._exit(0)


if __name__ == "__main__":
    run_diagnostics()
