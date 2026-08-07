"""
AYO AI — Speaker Verifier (Voice Biometrics)
=============================================
Verifies that the person speaking is an enrolled, authorised user.
Uses Resemblyzer to generate 256-dim voice embeddings and compares
them against stored profiles using cosine similarity.

Each authorised user has a profile folder with multiple .npy embeddings.
A speaker is "verified" if their voice matches any enrolled user
above a similarity threshold (default 0.82 = 82%).
"""

import logging
import numpy as np
from pathlib import Path
from resemblyzer import VoiceEncoder, preprocess_wav

log = logging.getLogger("ayo.verifier")

PROFILES_DIR = Path(__file__).parents[2] / "data" / "voice_profiles"
SIMILARITY_THRESHOLD = 0.82   # 0–1. Higher = stricter.


class SpeakerVerifier:
    def __init__(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        log.info("🔐 Loading voice encoder…")
        self.encoder = VoiceEncoder(device="cpu")
        self._profiles: dict[str, list[np.ndarray]] = {}
        self._load_all_profiles()
        log.info(f"✅ Speaker verifier ready — {len(self._profiles)} enrolled user(s)")

    # ── Public API ────────────────────────────────────────────────────────────

    def enrolled_count(self) -> int:
        return len(self._profiles)

    def list_users(self) -> list[str]:
        return list(self._profiles.keys())

    def identify(self, audio: np.ndarray) -> str | None:
        """
        Identify the speaker from audio.
        Returns the name of the matched user, or None if unknown.
        """
        if not self._profiles:
            log.warning("No profiles enrolled — cannot verify speaker.")
            return None

        embedding = self._get_embedding(audio)
        if embedding is None:
            return None

        best_name  = None
        best_score = 0.0

        for name, embeddings in self._profiles.items():
            scores = [self._cosine_sim(embedding, e) for e in embeddings]
            avg_score = float(np.mean(scores))
            log.debug(f"  Score vs {name}: {avg_score:.3f}")
            if avg_score > best_score:
                best_score = avg_score
                best_name  = name

        if best_score >= SIMILARITY_THRESHOLD:
            log.info(f"✅ Identified: {best_name} (score={best_score:.3f})")
            return best_name

        log.info(f"🚫 No match (best={best_score:.3f}, need≥{SIMILARITY_THRESHOLD})")
        return None

    def add_sample(self, name: str, audio: np.ndarray) -> bool:
        """Embed and save a voice sample for a user."""
        embedding = self._get_embedding(audio)
        if embedding is None:
            return False

        user_dir = PROFILES_DIR / name
        user_dir.mkdir(exist_ok=True)
        existing = list(user_dir.glob("*.npy"))
        idx = len(existing)
        np.save(str(user_dir / f"sample_{idx}.npy"), embedding)

        # Update in-memory cache
        if name not in self._profiles:
            self._profiles[name] = []
        self._profiles[name].append(embedding)
        log.info(f"💾 Saved sample {idx+1} for '{name}'")
        return True

    def delete_user(self, name: str) -> bool:
        """Remove all voice data for a user."""
        user_dir = PROFILES_DIR / name
        if user_dir.exists():
            import shutil
            shutil.rmtree(str(user_dir))
        if name in self._profiles:
            del self._profiles[name]
            log.info(f"🗑️ Deleted voice profile for '{name}'")
            return True
        return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_all_profiles(self):
        """Load all saved .npy embeddings from disk."""
        self._profiles = {}
        for user_dir in PROFILES_DIR.iterdir():
            if user_dir.is_dir():
                name = user_dir.name
                samples = [np.load(str(f)) for f in sorted(user_dir.glob("*.npy"))]
                if samples:
                    self._profiles[name] = samples
                    log.debug(f"  Loaded {len(samples)} samples for '{name}'")

    def _get_embedding(self, audio: np.ndarray) -> np.ndarray | None:
        """Preprocess audio and extract voice embedding."""
        try:
            # Resemblyzer expects float32 at 16kHz
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            if audio.max() > 1.0:
                audio = audio / 32768.0
            wav = preprocess_wav(audio, source_sr=16000)
            return self.encoder.embed_utterance(wav)
        except Exception as e:
            log.error(f"Embedding error: {e}")
            return None

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
