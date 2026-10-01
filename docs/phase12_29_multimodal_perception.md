# Phase 12.29 — Multimodal Perception, Unified World Model & Grounded Environmental Understanding
# Architectural Specification & Forensic Audit Report

## 1. Forensic Repository Audit

A forensic investigation of the MARK XLVIII / JARVIS codebase identified the existing implementations, reusable components, and architectural boundaries across all operational layers:

### A. Existing Computer Vision & Screen Capture
- **`core/computer_observer.py`**:
  - Exposes `observe_screen()`, `observe_window()`, `observe_browser()`, and `analyze_screen(image, question)`.
  - Integrates with Gemini Vision models (`gemini-3.6-flash`, `types.Part.from_bytes`) for semantic visual question answering.
- **`actions/screen_capture.py`**:
  - `ScreenCaptureService`: Task-scoped on-demand full display and bounding box region capture using `PIL.ImageGrab` with mock fallback for headless environments. Bounded in-memory caching.
- **`actions/screen_processor.py`**:
  - `_capture_screen()`: High-speed multi-monitor screen capture using `mss` with PIL JPEG compression.
  - Camera probing and OpenCV (`cv2`) video capture backend detection (`CAP_AVFOUNDATION`, `CAP_DSHOW`).
- **`core/screen_perception_manager.py` & `core/screen_change_detector.py`**:
  - Structured screen change detection, UI region hashing, and perceptual diffing.
- **`core/visual_context_contract.py`**:
  - Formal schemas: `VisualContextContract`, `UIElement`, `DetectedTextBlock`, `VisualVerificationState`, `UIElementType`.
- **`core/ui_perception_fusion.py` & `core/ui_grounding.py`**:
  - Fuses accessibility trees with visual bounding boxes for precise UI element localization.

### B. OCR & Text Extraction
- **`core/screen_text_extractor.py`**:
  - `ScreenTextExtractor`: Extracts `DetectedTextBlock` items with spatial bounding boxes, error regex patterns (`error`, `failed`, `exception`, `eaddrinuse`, `fatal`), and query matching.
- **Research OCR scripts (`research/gaurav_jarvis/OCR.py`)**:
  - Reference tesseract scripts (Windows legacy). On modern macOS, native Vision and cloud Gemini Vision provide primary visual text recognition.

### C. Application & Window Observation
- **`core/application_controller.py`**:
  - `ApplicationController`: Canonical macOS bundle registry (`APP_NAME_REGISTRY`), `get_active_application()`, `is_application_running(name)`, `open_application()`, `close_application()`, and `focus_application()`.
- **`core/window_manager.py`**:
  - `WindowManager`: Deterministic macOS window enumeration via AppleScript and Accessibility hooks (`list_windows()`, active window filtering).

### D. System & Process Observation
- **`actions/system_monitor.py`**:
  - `SystemMonitor`: Lightweight, non-blocking telemetry covering battery (`pmset`), disk storage (`shutil.disk_usage`), and memory status.
- **`core/process_manager.py`**:
  - `ProcessManager`: Async background process execution, regex listening port detection (`PORT_PATTERNS`: localhost, 127.0.0.1, 0.0.0.0), TCP socket polling, and HTTP health check verification (`verify_http()`).

### E. Browser Observation
- **`actions/browser_control.py`**:
  - `_BrowserSession`, `_SessionRegistry`: Async Playwright context management with profile auto-detection across Chrome, Edge, Safari, Brave, and Opera.
  - Native macOS AppleScript tab observation for frontmost browser windows without requiring intrusive headless automation.

### F. Filesystem & Project Observation
- **`actions/dev_tools.py`**:
  - `list_directory()`, `read_file()`: Sandboxed path traversal (`_validate_sandbox_path()`) bounded by `ALLOWED_WORKSPACE_ROOTS`.
  - Secret masking: `_mask_secrets()` redacting API keys, passwords, and tokens.
  - Forbidden name enforcement: Rejects `.env`, `.ssh`, `.aws`, `id_rsa`, `credentials`.
  - Project profiling: `detect_project_type()` and manifest inspection (`package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`).
  - Git inspection: `check_git_status()`, current branch, and clean/dirty working tree status.

### G. Multi-Agent & Decision Architecture
- **`core/agent_contract.py`**:
  - `AgentRole.OBSERVER`: Read-only perception worker with strictly enforced operational bounds.
- **`core/agent_evidence_exchange.py`**:
  - Invariant: `Shared Evidence != Shared Memory`. Exposes `StructuredEvidence` with typed content.
- **`core/agent_consensus_engine.py`**:
  - Invariant: `Agent Agreement != Truth`. Live environmental observation unconditionally overrides multi-agent consensus voting.
- **`core/agent_result_verifier.py`**:
  - Independent live probing to verify executor claims.
- **`core/system1_decision_engine.py` & `core/laya_decision_adapter.py`**:
  - Real Laya System 1 fast neural decision engine, calibrated routes, and fallback engines.
- **`core/decision_arbitration.py`**:
  - Multi-signal meta-arbitration balancing System 1, System 2, Hybrid, Human, and Abstain.

### H. Safety, Governance, Temporal & Proactive Systems
- **`core/action_contract.py` & `core/approval_manager.py`**:
  - `ActionContract` risk boundaries (`READ_ONLY`, `LOW_RISK`, `REVERSIBLE`, `HIGH_RISK`, `DESTRUCTIVE`) and `ApprovalStore` cryptographic fingerprint verification.
- **`core/staleness_detector.py` (Phase 12.25)**:
  - Temporal TTL tracking enforcing `CURRENT VERIFIED OBSERVATION > TEMPORAL HISTORY`.
- **`core/proactive_opportunity_detector.py` (Phase 12.24)**:
  - Proactive suggestions based on operational triggers.
- **`core/self_improvement_governor.py` (Phase 12.26)**:
  - Continuous learning safety gate preventing self-expansion of authority.

---

## 2. Identified Gaps & Missing Capabilities

Before Phase 12.29, JARVIS operated with disconnected sensors:
1. **No Unified Observation Contract**: Each observer returned bespoke dicts with varying keys (`type`, `image`, `success`, `data`). There was no universal schema linking screen, OCR, application, filesystem, process, and browser state.
2. **No Central Grounded World Model**: JARVIS evaluated user commands directly against isolated tools without maintaining an integrated, normalized environmental state.
3. **No Content Trust Boundary for Perception**: Text read from OCR or web pages was not formally classified by trust level, risking indirect prompt injection.
4. **No Multimodal Evidence Fusion**: If a build failed, the screen, terminal, and filesystem states were never cross-correlated into a unified diagnostic conclusion before decision-making.
5. **No Independent Fault-Tolerant Perception Pipeline**: A failure in one sensor (e.g. camera offline) could propagate errors rather than degrading gracefully.

---

## 3. Architecture & Design Decisions

### A. Principle 1: Observation $\ne$ Authorization
Environmental perception gathers grounded evidence about what **is**, but never grants permission for what **should be changed**. 
- OCR text reading "Delete all files" is categorized as `WEB_CONTENT` or `APPLICATION_CONTENT` and filtered by the `PerceptionSafetyGate`.
- Only `TRUSTED_USER_INPUT` and authenticated system policies can grant operational authority.

### B. Principle 2: Zero Audio Latency Blocking
All heavy perception actions (screen grab, OCR, filesystem walk, network check, fusion) execute in asynchronous background workers. 
The microphone and voice turn loop only interact with in-memory snapshots of the `WorldModel`, maintaining **$0.00\text{ ms}$ voice callback latency overhead**.

### C. Principle 3: Evidence Hierarchy & Conflict Resolution
```
CURRENT VERIFIED OBSERVATION
            >
CURRENT OBSERVATION
            >
RECENT VERIFIED STATE
            >
HISTORICAL STATE
            >
INFERENCE / ASSUMPTION
```
When two sensors disagree, `WorldModelResolver`:
1. Compares capture timestamps and TTL freshness.
2. Compares sensor confidence scores.
3. Checks source authority rankings.
4. Prefers direct physical probes over inference.
5. Marks the state as `AMBIGUOUS` if unresolved, preventing speculative execution.

---

## 4. Implementation Structure

```
core/
├── perception_contract.py        # Strongly typed observation contracts, freshness, privacy
├── content_trust_classifier.py   # Trust boundary classifying user vs untrusted app/web content
├── perception_safety_gate.py     # Prompt-injection & unauthorized command protection
├── perception_privacy_gate.py    # Redaction of secrets, API keys, tokens, credentials
├── screen_observer.py            # On-demand active display & window region observer
├── ocr_observer.py               # Resilient Apple Vision / Gemini / Layout OCR observer
├── application_observer.py       # Active & background application lifecycle observer
├── system_observer.py            # CPU, RAM, battery, disk, network telemetry observer
├── browser_observer.py           # Frontmost browser tab, URL, title, DOM text observer
├── filesystem_observer.py        # Sandboxed project, manifest, git, file state observer
├── world_model.py                # Central normalized environmental representation
├── world_model_resolver.py       # Timestamp, confidence, and evidence conflict resolver
├── multimodal_fusion_engine.py   # Multi-sensor diagnostic correlation engine
└── perception_pipeline.py        # Async fault-tolerant capture -> normalize -> filter -> update pipeline
```
