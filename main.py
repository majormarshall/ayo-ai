"""
AYO AI — Main Entry Point
==========================
Boots the Flask/SocketIO backend, starts the wake-word listener,
and connects all modules together.
"""

import threading
import logging
import sys
import os
from pathlib import Path

# ── Make sure backend is on the path ──────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from backend.core.memory_store import MemoryStore
from backend.core.llm_brain import LLMBrain
from backend.core.tts_engine import TTSEngine
from backend.core.stt_engine import STTEngine
from backend.wake.wake_detector import WakeDetector
from backend.voice.speaker_verifier import SpeakerVerifier
from backend.voice.enrollment_manager import EnrollmentManager
from backend.api.server import create_app, socketio

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ayo")

# ── Global State ──────────────────────────────────────────────────────────────
memory   = MemoryStore()
brain    = LLMBrain()
tts      = TTSEngine()
stt      = STTEngine()
verifier = SpeakerVerifier()
enroller = EnrollmentManager(verifier)


def on_wake_word_detected(audio_segment):
    """Called by WakeDetector when a wake phrase is heard."""
    log.info("🔔 Wake word detected — verifying speaker…")

    # 1. Speaker verification
    speaker = verifier.identify(audio_segment)
    if not speaker:
        log.warning("🚫 Unknown voice — ignoring.")
        tts.speak("I'm sorry, I don't recognise that voice. Ask the owner to register you.")
        return

    log.info(f"✅ Verified speaker: {speaker}")
    tts.speak(f"Yes {speaker}?")
    socketio.emit("ayo_listening", {"speaker": speaker})

    # 2. Listen for the actual command
    command_audio = stt.listen_for_command()
    if not command_audio:
        tts.speak("I didn't catch that, try again.")
        return

    command_text = stt.transcribe(command_audio)
    log.info(f"📝 Command: {command_text}")
    socketio.emit("user_message", {"text": command_text, "speaker": speaker})

    # 3. Send to brain
    response = brain.think(command_text, speaker=speaker)
    log.info(f"🤖 Response: {response.get('text','')}")

    socketio.emit("ayo_response", response)
    tts.speak(response.get("text", ""))


def start_wake_listener():
    detector = WakeDetector(callback=on_wake_word_detected)
    detector.start()


def main():
    log.info("🚀 Starting Ayo AI…")

    # First-run: enroll owner if no profiles exist
    if verifier.enrolled_count() == 0:
        log.info("👤 No voice profiles found — running first-time enrollment…")
        enroller.enroll_interactive(name="Marshall")

    # Start wake-word listener in background thread
    t = threading.Thread(target=start_wake_listener, daemon=True)
    t.start()

    # Start Flask/SocketIO API server (used by Electron dashboard)
    app = create_app(brain=brain, memory=memory, tts=tts,
                     verifier=verifier, enroller=enroller)
    log.info("🌐 API server starting on http://localhost:5050")
    socketio.run(app, host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
