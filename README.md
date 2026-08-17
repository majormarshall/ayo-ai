# 🤖 Ayo AI — Personal AI Operating System

> **100% offline** · Voice-first · Windows PC + Android control  
> Built by **Major Marshall**

---

## ⚡ Quick Start

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Download the AI model (run once, auto-resumes)
Double-click **`pull_model.bat`** — it will auto-retry if your connection drops.  
The model is ~2GB and resumes from where it left off each time.

### Step 3 — Install Node dependencies (for the dashboard)
```bash
npm install
```

### Step 4 — Launch Ayo
```bash
npm start
```
This opens the Ayo AI Dashboard window. The first time, it will ask you to enroll your voice.

---

## 🎙️ Voice Enrollment (First Time)

1. Open the dashboard → click **Voices** in the sidebar
2. Type your name → click **Start Enrollment**
3. Say **"Hey Ayo, I am ready to assist you"** — 5 times when prompted
4. Done! Ayo now recognises your voice

---

## 📱 Android Phone Setup (Optional)

To control your phone with "Ayo, open WhatsApp" or "Ayo, take a screenshot":

1. On your phone: **Settings → About Phone** → tap **Build Number** 7 times
2. Go to **Settings → Developer Options** → enable **USB Debugging**
3. Connect phone via USB to your PC once
4. Open Command Prompt: `adb tcpip 5555`
5. Disconnect USB cable
6. In Ayo dashboard → **Phone** tab → enter your phone's Wi-Fi IP → **Connect**

---

## 🗣️ What Ayo Can Do

| Say this... | What happens |
|---|---|
| `Hey Ayo, open Chrome` | Opens Chrome on your PC |
| `Hey Ayo, take a screenshot` | Saves a screenshot to Pictures |
| `Hey Ayo, search for Nigeria news` | Searches DuckDuckGo, summarises results |
| `Hey Ayo, create a PDF about Climate Change` | Generates a styled PDF document |
| `Hey Ayo, make a PowerPoint about Startups` | Creates a .pptx presentation |
| `Hey Ayo, open WhatsApp on my phone` | Opens WhatsApp on your Android |
| `Hey Ayo, what's the battery on my phone?` | Reads phone battery level |
| `Hey Ayo, write a Python script for a calculator` | Generates and saves the code |
| `Hey Ayo, run ipconfig` | Runs in CMD, returns output |
| `Hey Ayo, set volume to 50` | Sets PC volume |

---

## 🏗️ Architecture

```
ayo/
├── main.py                    ← Entry point (boots everything)
├── backend/
│   ├── api/server.py          ← Flask + SocketIO API (port 5050)
│   ├── core/
│   │   ├── llm_brain.py       ← Ollama LLM (llama3.2:3b)
│   │   ├── stt_engine.py      ← Whisper speech-to-text
│   │   ├── tts_engine.py      ← pyttsx3 text-to-speech
│   │   └── memory_store.py    ← SQLite conversation memory
│   ├── tools/
│   │   ├── dispatcher.py      ← Routes AI actions to tools
│   │   ├── system_control.py  ← PC control (apps, files, volume)
│   │   ├── phone_bridge.py    ← Android control via ADB
│   │   ├── document_creator.py← PDF + PPTX generation
│   │   ├── research_agent.py  ← DuckDuckGo web search
│   │   └── cmd_runner.py      ← Safe CMD execution
│   ├── voice/
│   │   ├── speaker_verifier.py← Voice biometrics (who is speaking)
│   │   └── enrollment_manager.py← Register new voice profiles
│   └── wake/
│       └── wake_detector.py   ← "Hey Ayo" wake word listener
├── frontend/
│   ├── electron/
│   │   ├── main.js            ← Electron main process
│   │   └── preload.js         ← IPC bridge
│   └── src/
│       ├── index.html         ← Dashboard UI
│       ├── style.css          ← Premium dark theme
│       └── app.js             ← Dashboard logic + WebSocket
├── data/
│   ├── db/ayo.db              ← SQLite memory database
│   ├── documents/             ← Generated PDFs/PPTs
│   └── voices/                ← Voice profile embeddings
├── pull_model.bat             ← Auto-retry model downloader
└── start_ayo.bat              ← One-click launcher
```

---

## 🔧 Troubleshooting

**"Backend offline" shown in dashboard**  
→ Run `python main.py --no-enroll` in a terminal first, then relaunch `npm start`

**"No Ollama model found"**  
→ Double-click `pull_model.bat` and wait for download to complete

**Voice not detected**  
→ Check your microphone is set as the default input in Windows Sound Settings

**Phone won't connect**  
→ Make sure phone and PC are on the same Wi-Fi network  
→ Re-run `adb tcpip 5555` with USB connected first

---

## 📦 Requirements

- **Python** 3.10+ (tested on 3.14)
- **Node.js** 18+
- **Ollama** (installed from [ollama.com](https://ollama.com))
- **ADB** (optional, for phone control — install Android Platform Tools)

---

*Ayo AI — Always listening, never in the cloud.*
