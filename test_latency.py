import os
import sys
import time
import threading
import asyncio

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from ui import JarvisUI
from main import JarvisLive
from core.timing import timer

def run_tests():
    print("=" * 60)
    print("🚀 Starting JARVIS Latency Measurement Suite")
    print("=" * 60)

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

    print("✅ JARVIS connected! Starting command executions...\n")
    time.sleep(2)

    test_commands = [
        "What time is it?",
        "Open Chrome",
        "Take a screenshot",
        "What's on my screen?",
        "Open Chrome and go to Google",
    ]

    for cmd in test_commands:
        print(f"\n" + "─" * 50)
        print(f"👉 TESTING COMMAND: '{cmd}'")
        print("─" * 50)

        # Trigger command via JarvisLive UI handler
        ui.on_text_command(cmd)

        # Wait for the turn to complete (timer.active becomes False)
        # Timeout after 60 seconds per command guard
        t_start = time.monotonic()
        while time.monotonic() - t_start < 60:
            time.sleep(0.2)
            if not timer.active and (time.monotonic() - t_start > 2.0):
                break

        print(f"✅ Completed command: '{cmd}'")
        time.sleep(4)

    print("\n" + "=" * 60)
    print("🎉 Latency Measurement Suite Finished")
    print("=" * 60)
    os._exit(0)

if __name__ == "__main__":
    run_tests()
