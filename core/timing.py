import time

class LatencyTracker:
    def __init__(self):
        self.t0 = None
        self.active = False
        self.current_label = ""
        self._first_audio_played = False

    def now(self) -> float:
        return time.monotonic()

    def start(self, label: str):
        self.t0 = time.monotonic()
        self.active = True
        self.current_label = label
        self._first_audio_played = False
        print(f"\n⏱️  [TIMING] [0.00s] Request received: '{label}'")

    def log(self, stage: str):
        if not self.active or self.t0 is None:
            return
        elapsed = time.monotonic() - self.t0
        print(f"⏱️  [TIMING] [{elapsed:5.2f}s] {stage}")

    def finish(self, label: str = "Request completed"):
        if not self.active or self.t0 is None:
            return
        elapsed = time.monotonic() - self.t0
        print(f"⏱️  [TIMING] [{elapsed:5.2f}s] {label}\n")
        self.active = False

timer = LatencyTracker()
