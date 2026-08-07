"""
AYO AI — TTS Engine (pyttsx3 offline voice)
============================================
Converts Ayo's text responses into speech using the Windows SAPI
speech engine — no internet needed, no API key, instant playback.
"""

import pyttsx3
import logging
import threading

log = logging.getLogger("ayo.tts")


class TTSEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            self._engine = pyttsx3.init()
            voices = self._engine.getProperty("voices")

            # Prefer a clear female voice for Ayo if available
            preferred = [v for v in voices if "zira" in v.name.lower() or
                         "hazel" in v.name.lower() or "female" in v.name.lower()]
            if preferred:
                self._engine.setProperty("voice", preferred[0].id)
            elif voices:
                self._engine.setProperty("voice", voices[0].id)

            self._engine.setProperty("rate",   175)   # words per minute
            self._engine.setProperty("volume", 0.95)  # 0.0 – 1.0
            log.info("🔊 TTS engine ready")
        except Exception as e:
            log.error(f"TTS init error: {e}")

    def speak(self, text: str):
        """Speak text out loud. Thread-safe."""
        if not text:
            return
        with self._lock:
            try:
                log.info(f"🗣️ Speaking: {text[:80]}…")
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as e:
                log.error(f"TTS error: {e}")
                # Reinitialise on failure
                self._init_engine()

    def set_rate(self, rate: int):
        """Change speaking speed (words per minute)."""
        self._engine.setProperty("rate", rate)

    def set_volume(self, volume: float):
        """Change volume (0.0 – 1.0)."""
        self._engine.setProperty("volume", max(0.0, min(1.0, volume)))

    def list_voices(self) -> list[dict]:
        """Return list of available voices."""
        return [
            {"id": v.id, "name": v.name, "lang": v.languages}
            for v in self._engine.getProperty("voices")
        ]
