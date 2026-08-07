"""
AYO AI — Speech-to-Text Engine (Whisper, fully local)
======================================================
Records audio from the microphone, detects silence, and transcribes
using faster-whisper running entirely on-device.
Uses sounddevice for audio capture (no PyAudio needed).
"""

import logging
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

log = logging.getLogger("ayo.stt")

# ── Config ────────────────────────────────────────────────────────────────────
SAMPLE_RATE   = 16_000      # Hz — Whisper's native rate
CHANNELS      = 1
DTYPE         = "int16"
SILENCE_LIMIT = 1.5         # seconds of silence to end recording
ENERGY_THRESH = 500         # RMS threshold for speech vs silence
MAX_RECORD    = 30          # max seconds to record a command


class STTEngine:
    def __init__(self, model_size: str = "base"):
        """
        model_size: "tiny", "base", "small", "medium"
        "base" is the best balance of speed vs accuracy for English.
        """
        log.info(f"🎤 Loading Whisper model '{model_size}'… (first load may be slow)")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        log.info("✅ Whisper model loaded")

    # ── Public API ────────────────────────────────────────────────────────────

    def listen_for_command(self) -> np.ndarray | None:
        """
        Record until silence detected. Returns numpy audio array or None.
        """
        log.info("👂 Listening for command…")
        audio_chunks = []
        silent_frames = 0
        speaking = False

        block_size = int(SAMPLE_RATE * 0.1)  # 100ms blocks
        max_blocks  = int(MAX_RECORD / 0.1)

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype=DTYPE, blocksize=block_size) as stream:
            for _ in range(max_blocks):
                block, _ = stream.read(block_size)
                rms = self._rms(block)

                if rms > ENERGY_THRESH:
                    speaking = True
                    silent_frames = 0
                    audio_chunks.append(block)
                elif speaking:
                    audio_chunks.append(block)
                    silent_frames += 1
                    if silent_frames >= int(SILENCE_LIMIT / 0.1):
                        break   # Silence detected — done listening

        if not audio_chunks:
            return None

        return np.concatenate(audio_chunks, axis=0).flatten()

    def record_sample(self, duration: float = 3.0) -> np.ndarray:
        """Record a fixed-duration audio sample (used for enrollment)."""
        log.info(f"🎙️ Recording {duration}s sample…")
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=CHANNELS, dtype=DTYPE)
        sd.wait()
        return audio.flatten().astype(np.float32) / 32768.0  # normalise

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe numpy audio array to text using Whisper."""
        try:
            # Whisper needs float32 in [-1, 1]
            audio_f32 = audio.astype(np.float32)
            if audio_f32.max() > 1.0:
                audio_f32 = audio_f32 / 32768.0

            segments, _ = self.model.transcribe(
                audio_f32,
                language="en",
                beam_size=3,
                vad_filter=True,
            )
            text = " ".join(s.text.strip() for s in segments)
            log.info(f"📝 Transcribed: '{text}'")
            return text.strip()
        except Exception as e:
            log.error(f"Transcription error: {e}")
            return ""

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _rms(block: np.ndarray) -> float:
        """Compute root-mean-square energy of audio block."""
        return float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
