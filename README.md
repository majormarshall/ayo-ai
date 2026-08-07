# 🤖 Ayo AI — Personal AI Operating System

> A fully offline, voice-first personal AI assistant that controls your Windows PC and Android phone.
> Built by **Major Marshall**.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎙️ **Multi Wake Word** | Say "Hey Ayo", "Hello Ayo", "Hi Ayo", or "Ayo" |
| 🔐 **Voice Biometrics** | Only responds to enrolled, authorised voices |
| 👥 **Multi-User** | Register any person — Ayo learns their voice |
| 🧠 **100% Offline AI** | Powered by Ollama (Llama 3.2 / Mistral) — no internet needed |
| 🎤 **Local Speech-to-Text** | Whisper AI runs entirely on your machine |
| 🗣️ **Natural Voice** | pyttsx3 offline TTS |
| 💻 **PC Control** | Open apps, control volume, take screenshots, manage files |
| ⌨️ **Command Prompt** | Run CMD/PowerShell commands by voice (with safety checks) |
| 📱 **Android Control** | Control your Android phone over Wi-Fi (ADB) |
| 🔍 **Web Research** | Search DuckDuckGo, scrape and AI-summarise results |
| 📄 **PDF Creator** | Generate styled PDF documents from voice |
| 📊 **PowerPoint Creator** | Build full slide decks from a voice prompt |
| 💻 **Vibe Code** | Generate HTML/CSS/JS/Python snippets and preview instantly |
| 🖥️ **Desktop App** | Premium Electron dashboard with dark glassmorphism UI |
| 🗂️ **System Tray** | Runs in background, always listening. `Ctrl+Shift+A` to open |

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+ 
- Node.js 18+
- [Ollama](https://ollama.ai) installed and running
- (Optional) Android phone with USB Debugging enabled

### 2. Clone & Install

```bash
git clone https://github.com/majormarshall/ayo-ai.git
cd ayo-ai

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies (for dashboard)
npm install

# Pull the AI model (first time only)
ollama pull llama3.2
```

### 3. First Run

```bash
# Start the Python backend
python main.py
```

On first run, Ayo will guide you through enrolling your voice (5 quick recordings).

### 4. Launch Dashboard

```bash
npm start
```

Or use `Ctrl+Shift+A` at any time to show/hide the dashboard.

---

## 📱 Android Phone Setup (One-Time)

1. **Settings → About Phone** → tap *Build Number* 7 times to enable Developer Mode
2. **Settings → Developer Options** → enable *USB Debugging*
3. Connect phone via USB to PC, then run in CMD:
   ```
   adb tcpip 5555
   ```
4. Disconnect USB cable
5. Open Ayo dashboard → **Phone** tab → enter your phone's Wi-Fi IP → Connect

---

## 🗣️ Voice Commands Examples

| Say this... | Ayo does... |
|-------------|-------------|
| "Hey Ayo, open Chrome" | Opens Google Chrome |
| "Ayo, take a screenshot" | Screenshots your screen |
| "Hi Ayo, what's the weather?" | Searches and reads out the weather |
| "Ayo, create a PDF about climate change" | Generates a styled PDF |
| "Hey Ayo, make a PowerPoint about marketing" | Creates a full slide deck |
| "Ayo, run ipconfig" | Runs ipconfig in CMD, reads back your IP |
| "Hello Ayo, call +2348000000000 on my phone" | Dials number on your Android phone |
| "Ayo, register this voice as John" | Enrolls John's voice |
| "Hey Ayo, search Nigeria latest news" | Searches, scrapes, summarises |
| "Ayo, build me a todo app" | Generates HTML/CSS/JS, opens in browser |

---

## 🏗️ Project Structure

```
ayo-ai/
├── main.py                     # Entry point
├── requirements.txt
├── package.json
├── .env.example
│
├── backend/
│   ├── core/
│   │   ├── llm_brain.py        # Ollama AI reasoning
│   │   ├── stt_engine.py       # Whisper speech-to-text
│   │   ├── tts_engine.py       # pyttsx3 text-to-speech
│   │   └── memory_store.py     # SQLite conversation memory
│   ├── wake/
│   │   └── wake_detector.py    # Multi-phrase wake word listener
│   ├── voice/
│   │   ├── speaker_verifier.py # Voice biometric verification
│   │   └── enrollment_manager.py
│   ├── tools/
│   │   ├── system_control.py   # Windows PC control
│   │   ├── cmd_runner.py       # CMD/PowerShell runner
│   │   ├── phone_bridge.py     # Android ADB control
│   │   ├── research_agent.py   # DuckDuckGo web research
│   │   ├── document_creator.py # PDF + PPTX + Vibe Code
│   │   └── dispatcher.py       # Routes actions to tools
│   └── api/
│       └── server.py           # Flask + SocketIO API
│
├── frontend/
│   ├── electron/
│   │   ├── main.js             # Electron main process
│   │   └── preload.js          # Secure context bridge
│   └── src/
│       ├── index.html          # Dashboard UI
│       ├── style.css           # Glassmorphism styling
│       └── app.js              # Dashboard logic
│
└── data/
    ├── voice_profiles/         # Voice embeddings (local only)
    ├── documents/              # Generated PDFs, PPTXs, code
    └── db/
        └── ayo.db              # SQLite memory database
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Brain | Ollama (Llama 3.2 3B) — 100% offline |
| Speech-to-Text | faster-whisper (local Whisper) |
| Text-to-Speech | pyttsx3 (Windows SAPI) |
| Voice Biometrics | Resemblyzer (speaker embeddings) |
| Wake Word | SpeechRecognition + fuzzy matching |
| PC Control | pyautogui, subprocess, psutil |
| Phone Control | ADB + ppadb |
| PDF | ReportLab |
| PowerPoint | python-pptx |
| Web Research | DuckDuckGo + BeautifulSoup |
| Database | SQLite |
| Dashboard | Electron + HTML/CSS/JS |
| Backend API | Flask + Flask-SocketIO |

---

## 📝 License

MIT © Major Marshall
