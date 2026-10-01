# ⚡ MARK XLVIII — Personal J.A.R.V.I.S.

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![AI Engine](https://img.shields.io/badge/Gemini_Live-Bidirectional_WebSocket-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![GUI](https://img.shields.io/badge/Interface-PyQt6_Holographic_HUD-00d4ff)](https://riverbankcomputing.com/software/pyqt/)
[![Audio](https://img.shields.io/badge/Audio-24kHz_Raw_PCM_Streaming-00ff88)](https://python-sounddevice.readthedocs.io/)
[![Architecture](https://img.shields.io/badge/System-Dual--Process_Cognitive_Engine-ff6b00)](#-cognitive-architecture-dual-process-intelligence)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**An ultra-fast, autonomous, multimodal desktop AI companion inspired by Tony Stark's J.A.R.V.I.S.**  
*Speaks in real-time, sees your display, operates your OS, codes autonomously, and evolves with you.*

[Explore Features](#-the-cool-stuff) • [Quick Start](#-getting-started) • [Architecture](#-cognitive-architecture-dual-process-intelligence) • [Command Showcase](#-voice--chat-showcase)

</div>

---

## 🚀 Overview

**MARK XLVIII (JARVIS)** is not another wrapper around an LLM chatbox. It is an **autonomous, full-duplex desktop agent** powered by the **Google Gemini Live API (Bidirectional WebSocket Streaming)** coupled with a custom-engineered **Dual-Process Cognitive Architecture** and **PyQt6 Arc-Reactor Holographic HUD**.

JARVIS runs continuously on your desktop. He listens with sub-100ms adaptive turn-taking, analyzes your screen in real time, manages your windows and files, writes and tests code, searches the web, and proactively assists you with everyday desktop workflows.

---

## ✨ The Cool Stuff

### 🎙️ Zero-Wait Full-Duplex Voice Engine
- **Native Gemini Live WebSocket Streaming**: Direct 24kHz raw int16 PCM audio streaming with natural, low-latency, interruptions-aware vocal exchanges.
- **Speculative & Predictive Execution**: Starts dispatching and executing OS actions *while you are still mid-sentence*, yielding an instantaneous response the moment you finish speaking.
- **Adaptive Endpointing**: Machine-tuned voice activity and silence detection that eliminates the awkward delay of traditional voice assistants.
- **Dynamic Jarvis Personality**: Witty, concise, British-accented Stark-style assistant that delivers punchy status updates without rambling.

### 👁️ Observe-Act-Verify Vision Loop
- **Instant Screen & Camera Perception**: Equipped with high-speed screen capture (`mss`) and webcam integration with Gemini multimodal vision.
- **Live Visual Grounding**: Tell JARVIS *"Look at this error on my screen and fix it"* or *"Where is the download button?"*, and he locates UI elements and resolves problems visually.

### 🦾 Autonomous Desktop & OS Control
- **Full Mouse & Keyboard Mastery**: Precision clicks, hotkeys, typing, window minimization/switching, and terminal execution.
- **Automated Browser Control**: Opens web links, launches tabs, navigates sites, and pulls real-time information.
- **System Settings Manager**: Adjusts volume, display brightness, Bluetooth, WiFi, and system toggles on the fly.

### 🧠 Cognitive Architecture (Dual-Process Intelligence)
- **⚡ System 1 (Laya — Instant Reflexes)**:
  - 0.00s deterministic local intent router for instant system commands.
  - Learned repair reflexes that resolve recurrent errors (like clearing port conflicts or restarting dev servers) without waiting for a full cloud cycle.
- **🔬 System 2 (Deep Reasoning Orchestrator)**:
  - Complex multi-step task decomposition and dynamic task graph scheduling.
  - Decision calibration and arbitration engine with safety gating to ensure actions are verified before execution.

### 💻 Autonomous Developer Agent
- **In-flight Code Editor**: Reads, inspects, modifies, and patches codebases directly from spoken instructions.
- **Self-Healing Workflows**: Discovers failing tests, analyzes terminal errors, applies fixes, and verifies outcomes automatically.

### 🧬 Self-Evolving Long-Term Memory
- **Persistent Semantic & Episodic Store**: Remembers your name, preferences, favorite projects, recurring workflows, and previous interactions across sessions.
- **Skill Evolution Engine**: Automatically derives generalizable skills from successful problem resolutions and saves them to `data/learned_skills.json`.

### 🔮 Holographic Arc Reactor Interface
- **Cyberpunk HUD**: Futuristic PyQt6 interface with glowing cyan/arc-orange neon styling.
- **Real-Time Visualizer**: Audio waveform pulsing, dynamic state indicators (Listening, Thinking, Speaking, Sleeping), and live camera/screen HUD.
- **Direct Hardware Telemetry**: Live CPU, RAM, battery, thermal, and NVIDIA GPU telemetry (via direct C-types NVML DLL integration, zero console flicker).

### 🌐 Encrypted Mobile Dashboard Server
- Built-in lightweight companion web server (`dashboard/server.py`) with TLS and AES-CBC encryption.
- Monitor metrics, send remote commands, and check on JARVIS from your phone or any local browser.

---

## 🛠️ Architecture Map

```
                             🎤 Microphone Audio Stream (24kHz Raw PCM)
                                              │
                                              ▼
                                 [ Gemini Live WebSocket ]
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
         [ Direct Voice Playback ]                          [ Local Intent Router ]
        (Raw Audio Dispatch Queue)                           (0.00s Deterministic)
                    │                                                   │
                    ▼                                                   ▼
            🔊 Speakers Out                                 [ Cognitive Orchestrator ]
                                                            (System 1 & System 2 ReAct)
                                                                        │
                                             ┌──────────────────────────┴──────────────────────────┐
                                             ▼                                                     ▼
                                     [ Vision Engine ]                                     [ Action Registry ]
                                 (Screen Capture & Camera)                             (25+ Sandboxed Modules)
                                             │                                                     │
                                             ▼                                                     ▼
                                    Observe-Act-Verify                                 Desktop / Code / Browser / OS
                                                                                                   │
                                                                                                   ▼
                                                                                         [ Holographic PyQt6 HUD ]
```

---

## 📦 Getting Started

### 📋 Prerequisites
- **Operating System**: macOS, Windows 10/11, or Linux
- **Python**: Version 3.10 or higher
- **Microphone & Speakers**: For live voice interactions
- **Gemini API Key**: Free key from [Google AI Studio](https://aistudio.google.com/)

---

### ⚡ Installation Step-by-Step

#### 1. Clone the Repository
```bash
git clone --recurse-submodules https://github.com/NKishoreVarma/personal-jarvis-k1.git
cd personal-jarvis-k1
```

#### 2. Create and Activate Virtual Environment
- **macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- **Windows**:
  ```bash
  python -m venv .venv
  .venv\Scripts\activate
  ```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note for macOS Users**: On macOS, grant Accessibility and Screen Recording permissions to your Terminal / IDE in `System Settings > Privacy & Security` so JARVIS can interact with your display and keyboard.

#### 4. Configure Your API Key
Copy the template and insert your Gemini API Key:
```bash
cp config/api_keys.example.json config/api_keys.json
```
Edit `config/api_keys.json`:
```json
{
    "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
    "os_system": "mac"
}
```
*(Replace `"mac"` with `"windows"` or `"linux"` according to your operating system).*

---

### 🚀 Launching JARVIS

To fire up the system and holographic HUD:
```bash
python main.py
```

Upon launch:
1. The **Holographic HUD** will illuminate and run hardware diagnostics.
2. Say the wake word **"Jarvis"** or click the central **Arc Reactor** to start speaking.
3. Speak naturally in full duplex — you can interrupt him at any moment!

---

## 🎙️ Voice & Chat Showcase

Try giving JARVIS commands like:

| Category | Example Command |
| :--- | :--- |
| **Vision & Screen** | *"Jarvis, look at my screen. What's causing this compiler error?"* |
| **Developer Copilot** | *"Inspect the tests in `tests/` and run the failed ones."* |
| **Desktop Control** | *"Switch over to VS Code and maximize the window."* |
| **Media & Entertainment** | *"Play interstellar soundtrack on YouTube."* |
| **Web & Intelligence** | *"Search the web for the latest updates on Artemis II and give me a 3-bullet summary."* |
| **Travel & Logistics** | *"Find flights from San Francisco to Tokyo for next month."* |
| **System Diagnostics** | *"What's my current CPU load and memory usage?"* |
| **Proactive Memory** | *"Remember that my favorite project directory is inside `~/projects/ai`."* |

---

## 📂 Repository Layout

```
.
├── actions/                  # 25+ Sandboxed Action & Skill Modules
│   ├── app_control.py        # Application launcher and process management
│   ├── browser_control.py    # Automated browser tabs & web interactions
│   ├── code_editor.py        # Code parsing, AST search, and automated patching
│   ├── computer_control.py   # Mouse, keyboard, and display automation
│   ├── dev_agent.py          # Autonomous coding agent
│   ├── screen_processor.py   # Multimodal vision (camera + screen capture)
│   ├── system_monitor.py     # Real-time hardware telemetry
│   └── ...
├── config/                   # Configuration & Credentials
│   ├── api_keys.example.json # Safe configuration template
│   └── jarvis.ico            # System icon assets
├── core/                     # Core Intelligence & Low-Latency Engine
│   ├── adaptive_endpoint.py  # Sub-100ms voice turn-taking
│   ├── cognitive_orchestrator.py # System 2 deep reasoning
│   ├── predictive_execution.py   # Speculative mid-sentence execution
│   ├── system1_decision_engine.py # System 1 fast reflexes
│   ├── voice_personality_engine.py # Conversational persona
│   └── ...
├── dashboard/                # Encrypted Companion Web App
│   ├── server.py             # TLS / AES-CBC encrypted HTTP & WebSocket server
│   └── static/               # Web client UI
├── data/                     # Persistent Knowledge & Memory
│   ├── learned_skills.json   # Dynamically learned workflow repair skills
│   └── long_term_memory.json # Semantic & episodic user knowledge
├── docs/                     # Comprehensive architectural specifications & audit logs
├── memory/                   # Hierarchical Memory Management
├── tests/                    # Unit, integration, and certification test suites
├── main.py                   # Master entrypoint & Gemini Live event loop
├── ui.py                     # PyQt6 Holographic Cyberpunk Interface
└── requirements.txt          # Python dependencies
```

---

## 🔒 Security & Privacy First

- **Zero Secret Leaks**: Credentials, keys, and tokens are stored in local configuration files (`config/api_keys.json`) which are strictly ignored by version control.
- **Fail-Safe Desktop Control**: PyAutoGUI fail-safe is enabled by default (slamming mouse cursor to screen corners immediately halts execution).
- **Sandboxed Execution**: Subprocess and file operations run through guarded controllers with path validation.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to fork the repository, open a pull request, or submit issues.

```bash
git checkout -b feature/amazing-feature
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

<div align="center">
  <sub>Built with ❤️ and powered by Google Gemini. Inspired by the ingenuity of Tony Stark.</sub>
</div>
