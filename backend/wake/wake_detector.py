"""
AYO AI — Wake Word Detector
============================
Continuously listens in the background for one of Ayo's wake phrases:
  "hey ayo" | "hello ayo" | "hi ayo" | "ayo"

Uses sounddevice + faster-whisper for fully offline wake word detection.
No PyAudio required — works on Python 3.14+.
Calls `callback(audio_segment)` when triggered.
"""

import logging
import threading
import time
import numpy as np
import sounddevice as sd
from fuzzywuzzy import fuzz
from faster_whisper import WhisperModel

log = logging.getLogger("ayo.wake")

# ── Config ────────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 16_000
CHUNK_SECS     = 2.0        # Record in 2-second chunks for wake detection
ENERGY_THRESH  = 200        # Skip very quiet chunks (silence)
WAKE_PHRASES   = ["hey ayo", "hello ayo", "hi ayo", "ayo"]
MATCH_THRESHOLD = 70        # Fuzzy score 0-100; lower = more sensitive


class WakeDetector:
    def __init__(self, callback):
        """
        callback: callable(audio_segment: np.ndarray)
            Called with float32 audio array when wake word detected.
        """
        self.callback  = callback
        self._running  = False
        self._on_cooldown = False

        log.info("🔊 Loading tiny Whisper model for wake detection…")
        self._whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
        log.info("✅ Wake detector ready")

    def start(self):
        """Blocking loop — call from a daemon thread."""
        self._running = True
        log.info("👂 Wake detector active — listening for 'Hey Ayo'…")

        chunk_size = int(SAMPLE_RATE * CHUNK_SECS)

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="float32", blocksize=chunk_size) as stream:
            while self._running:
                chunk, _ = stream.read(chunk_size)
                audio = chunk.flatten()

                # Skip silent chunks
                rms = float(np.sqrt(np.mean(audio ** 2)))
                if rms < (ENERGY_THRESH / 32768.0):
                    continue

                # Skip if already processing a command
                if self._on_cooldown:
                    continue

                # Transcribe the short chunk
                text = self._transcribe_chunk(audio)
                if text and self._is_wake_phrase(text):
                    log.info(f"🔔 Wake phrase detected: '{text}'")
                    self._on_cooldown = True
                    threading.Thread(
                        target=self._fire_callback,
                        args=(audio,),
                        daemon=True
                    ).start()

    def stop(self):
        self._running = False

    def resume(self):
        """Call after a command is processed to re-enable detection."""
        self._on_cooldown = False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fire_callback(self, audio: np.ndarray):
        try:
            self.callback(audio)
        finally:
            time.sleep(1.5)     # brief cooldown before listening again
            self._on_cooldown = False

    def _transcribe_chunk(self, audio: np.ndarray) -> str:
        try:
            segments, _ = self._whisper.transcribe(
                audio, language="en", beam_size=1, vad_filter=True
            )
            return " ".join(s.text.strip() for s in segments).lower().strip()
        except Exception as e:
            log.debug(f"Transcribe error: {e}")
            return ""

    @staticmethod
    def _is_wake_phrase(text: str) -> bool:
        for phrase in WAKE_PHRASES:
            if phrase in text:
                return True
            if fuzz.partial_ratio(phrase, text) >= MATCH_THRESHOLD:
                return True
        return False
