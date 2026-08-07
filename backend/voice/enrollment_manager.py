"""
AYO AI — Enrollment Manager
============================
Handles enrolling new voice profiles for authorised users.
Works both interactively (command-line guided) and via API call
from the Electron dashboard ("Ayo, register this voice as John").

Enrollment requires 5 voice samples per person for good accuracy.
"""

import logging
import time
import numpy as np
from .speaker_verifier import SpeakerVerifier

log = logging.getLogger("ayo.enrollment")

NUM_SAMPLES = 5          # Number of recordings needed per person
SAMPLE_DURATION = 3.0    # Seconds per recording


class EnrollmentManager:
    def __init__(self, verifier: SpeakerVerifier):
        self.verifier = verifier

    # ── Interactive (CLI) enrollment ──────────────────────────────────────────

    def enroll_interactive(self, name: str, tts=None, stt=None) -> bool:
        """
        Walk a person through recording N voice samples.
        tts: TTSEngine (for audio prompts)
        stt: STTEngine (for recording)
        If tts/stt are None, falls back to print/input prompts.
        """
        log.info(f"📝 Starting enrollment for '{name}'…")
        samples_recorded = 0

        for i in range(NUM_SAMPLES):
            prompt = (
                f"Sample {i+1} of {NUM_SAMPLES}. "
                "Please say: 'Hey Ayo, I am ready to assist you.'"
            )
            if tts:
                tts.speak(prompt)
            else:
                print(f"\n🎙️  {prompt}")
                input("   Press Enter when ready…")

            time.sleep(0.3)   # Small pause before recording

            if stt:
                audio = stt.record_sample(duration=SAMPLE_DURATION)
            else:
                # Fallback: use sounddevice directly
                import sounddevice as sd
                log.info("Recording…")
                audio = sd.rec(int(SAMPLE_DURATION * 16000),
                               samplerate=16000, channels=1, dtype="float32")
                sd.wait()
                audio = audio.flatten()

            ok = self.verifier.add_sample(name, audio)
            if ok:
                samples_recorded += 1
                confirm_msg = f"Sample {i+1} saved." if i < NUM_SAMPLES - 1 else "Enrollment complete!"
                if tts:
                    tts.speak(confirm_msg)
                else:
                    print(f"   ✅ {confirm_msg}")
            else:
                warn = "That sample wasn't clear enough. Let's try again."
                if tts:
                    tts.speak(warn)
                else:
                    print(f"   ⚠️  {warn}")

        success = samples_recorded >= 3  # Need at least 3 good samples
        if success:
            msg = f"I have successfully registered {name}. I will recognise their voice from now on."
        else:
            msg = f"Enrollment for {name} failed — not enough clear samples. Please try again."

        if tts:
            tts.speak(msg)
        else:
            print(f"\n{'✅' if success else '❌'} {msg}")

        return success

    # ── API-driven enrollment ─────────────────────────────────────────────────

    def add_sample_api(self, name: str, audio: np.ndarray) -> dict:
        """
        Used by the Electron dashboard to submit a single audio sample.
        Returns: { "success": bool, "count": int, "done": bool }
        """
        ok = self.verifier.add_sample(name, audio)
        count = len(self.verifier._profiles.get(name, []))
        return {
            "success": ok,
            "count": count,
            "done": count >= NUM_SAMPLES,
        }

    # ── Management ────────────────────────────────────────────────────────────

    def list_users(self) -> list[dict]:
        """Return enrolled users with sample counts."""
        result = []
        for name in self.verifier.list_users():
            samples = self.verifier._profiles.get(name, [])
            result.append({"name": name, "samples": len(samples)})
        return result

    def revoke_user(self, name: str) -> bool:
        """Remove a user's voice access."""
        return self.verifier.delete_user(name)
