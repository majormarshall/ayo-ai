"""
AYO AI — Wake Word Detector
============================
Continuously listens in the background for one of Ayo's wake phrases:
  "hey ayo" | "hello ayo" | "hi ayo" | "ayo"

Uses SpeechRecognition (Google offline, then system) with fuzzy matching
so natural pronunciation variations still trigger correctly.
Calls `callback(audio_segment)` with the raw audio when triggered.
"""

import logging
import threading
import numpy as np
import speech_recognition as sr
from fuzzywuzzy import fuzz

log = logging.getLogger("ayo.wake")

# ── Wake phrase variants ───────────────────────────────────────────────────────
WAKE_PHRASES = ["hey ayo", "hello ayo", "hi ayo", "ayo"]
MATCH_THRESHOLD = 70   # Fuzzy match score (0-100). Lower = more sensitive.


class WakeDetector:
    def __init__(self, callback):
        """
        callback: callable(audio_segment: AudioData)
            Called when a wake word is confirmed.
        """
        self.callback = callback
        self._running = False
        self._recogniser = sr.Recognizer()
        self._recogniser.dynamic_energy_threshold = True
        self._recogniser.pause_threshold = 0.6
        self._recogniser.energy_threshold = 300
        self._mic = sr.Microphone(sample_rate=16000)

        # Calibrate for ambient noise once
        log.info("🎙️ Calibrating microphone for ambient noise…")
        with self._mic as source:
            self._recogniser.adjust_for_ambient_noise(source, duration=1.5)
        log.info(f"✅ Energy threshold set to {self._recogniser.energy_threshold:.0f}")

    def start(self):
        """Start listening in the current thread (blocking). Call from a daemon thread."""
        self._running = True
        log.info("👂 Wake detector active — listening for 'Ayo'…")

        def _on_audio(recogniser, audio):
            self._process(recogniser, audio)

        stop_fn = self._recogniser.listen_in_background(self._mic, _on_audio,
                                                         phrase_time_limit=4)
        # Keep the thread alive
        try:
            while self._running:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            pass
        finally:
            stop_fn(wait_for_stop=False)

    def stop(self):
        self._running = False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _process(self, recogniser, audio):
        """Attempt to recognise speech and check for wake phrase."""
        try:
            # Try offline Sphinx first, fall back to Google if available
            try:
                text = recogniser.recognize_sphinx(audio).lower().strip()
            except Exception:
                try:
                    text = recogniser.recognize_google(audio).lower().strip()
                except Exception:
                    return

            log.debug(f"Heard: '{text}'")

            if self._is_wake_phrase(text):
                log.info(f"🔔 Wake phrase matched in: '{text}'")
                # Pass raw audio bytes as numpy array for speaker verifier
                raw = np.frombuffer(audio.get_raw_data(convert_rate=16000,
                                                        convert_width=2),
                                    dtype=np.int16).astype(np.float32) / 32768.0
                # Run callback in a new thread so we don't block the listener
                threading.Thread(target=self.callback, args=(raw,), daemon=True).start()

        except Exception as e:
            log.debug(f"Wake detection error: {e}")

    @staticmethod
    def _is_wake_phrase(text: str) -> bool:
        """Fuzzy-match heard text against all wake phrases."""
        for phrase in WAKE_PHRASES:
            # Direct substring
            if phrase in text:
                return True
            # Fuzzy match (handles slight mispronunciation)
            score = fuzz.partial_ratio(phrase, text)
            if score >= MATCH_THRESHOLD:
                log.debug(f"Fuzzy match: '{phrase}' ↔ '{text}' = {score}")
                return True
        return False
