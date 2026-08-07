"""
AYO AI — Speaker Verifier (Voice Biometrics)
=============================================
Verifies that the person speaking is an enrolled, authorised user.
Uses a cosine-similarity approach over voice embeddings.

Backend priority:
  1. SpeechBrain (ECAPA-TDNN) — most accurate
  2. Resemblyzer — lightweight fallback
  3. Simple energy+pitch fingerprint — last resort

Only responds to enrolled, authorised voices. Anyone else is silently rejected.
"""

import logging
import numpy as np
from pathlib import Path

log = logging.getLogger("ayo.verifier")

PROFILES_DIR         = Path(__file__).parents[2] / "data" / "voice_profiles"
SIMILARITY_THRESHOLD = 0.80   # 0–1. Lower = more permissive.

# ── Try to load best available backend ────────────────────────────────────────
_BACKEND = None

try:
    import torchaudio
    import torch
    from speechbrain.inference.speaker import SpeakerRecognition
    _SB_MODEL = None   # Lazy-loaded on first use
    _BACKEND  = "speechbrain"
    log.info("🔐 Voice backend: SpeechBrain (ECAPA-TDNN)")
except ImportError:
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav
        _RZ_ENCODER = None   # Lazy-loaded
        _BACKEND    = "resemblyzer"
        log.info("🔐 Voice backend: Resemblyzer")
    except ImportError:
        _BACKEND = "simple"
        log.warning("🔐 Voice backend: simple energy fingerprint (install speechbrain for better accuracy)")


class SpeakerVerifier:
    def __init__(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, list[np.ndarray]] = {}
        self._encoder  = None
        self._load_backend()
        self._load_all_profiles()
        log.info(f"✅ Speaker verifier ready — {len(self._profiles)} enrolled user(s), backend={_BACKEND}")

    # ── Public API ────────────────────────────────────────────────────────────

    def enrolled_count(self) -> int:
        return len(self._profiles)

    def list_users(self) -> list[str]:
        return list(self._profiles.keys())

    def identify(self, audio: np.ndarray) -> str | None:
        """
        Identify the speaker from float32 audio at 16kHz.
        Returns the name of matched user, or None if unknown/unverified.
        """
        if not self._profiles:
            log.warning("No profiles enrolled — cannot verify speaker.")
            return None

        embedding = self._embed(audio)
        if embedding is None:
            return None

        best_name  = None
        best_score = 0.0

        for name, embeddings in self._profiles.items():
            scores = [self._cosine_sim(embedding, e) for e in embeddings]
            score  = float(np.mean(scores))
            log.debug(f"  {name}: {score:.3f}")
            if score > best_score:
                best_score = score
                best_name  = name

        if best_score >= SIMILARITY_THRESHOLD:
            log.info(f"✅ Verified: {best_name} (score={best_score:.3f})")
            return best_name

        log.info(f"🚫 No match (best={best_score:.3f} < {SIMILARITY_THRESHOLD})")
        return None

    def add_sample(self, name: str, audio: np.ndarray) -> bool:
        """Embed and persist one voice sample for a user."""
        embedding = self._embed(audio)
        if embedding is None:
            return False

        user_dir = PROFILES_DIR / name
        user_dir.mkdir(exist_ok=True)
        idx = len(list(user_dir.glob("*.npy")))
        np.save(str(user_dir / f"sample_{idx}.npy"), embedding)

        if name not in self._profiles:
            self._profiles[name] = []
        self._profiles[name].append(embedding)
        log.info(f"💾 Saved sample {idx+1} for '{name}'")
        return True

    def delete_user(self, name: str) -> bool:
        """Remove all voice data for a user."""
        import shutil
        user_dir = PROFILES_DIR / name
        if user_dir.exists():
            shutil.rmtree(str(user_dir))
        if name in self._profiles:
            del self._profiles[name]
            log.info(f"🗑️ Deleted voice profile for '{name}'")
            return True
        return False

    # ── Backend Loader ────────────────────────────────────────────────────────

    def _load_backend(self):
        global _BACKEND, _SB_MODEL, _RZ_ENCODER

        if _BACKEND == "speechbrain":
            try:
                from speechbrain.inference.speaker import SpeakerRecognition
                self._encoder = SpeakerRecognition.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="data/pretrained/spkrec-ecapa"
                )
                log.info("✅ SpeechBrain ECAPA model loaded")
            except Exception as e:
                log.warning(f"SpeechBrain load failed: {e} — falling back to simple backend")
                _BACKEND = "simple"

        elif _BACKEND == "resemblyzer":
            try:
                from resemblyzer import VoiceEncoder
                self._encoder = VoiceEncoder(device="cpu")
                log.info("✅ Resemblyzer encoder loaded")
            except Exception as e:
                log.warning(f"Resemblyzer load failed: {e} — falling back to simple backend")
                _BACKEND = "simple"

    # ── Profile Loader ────────────────────────────────────────────────────────

    def _load_all_profiles(self):
        self._profiles = {}
        for user_dir in PROFILES_DIR.iterdir():
            if user_dir.is_dir():
                samples = [np.load(str(f)) for f in sorted(user_dir.glob("*.npy"))]
                if samples:
                    self._profiles[user_dir.name] = samples

    # ── Embedding ─────────────────────────────────────────────────────────────

    def _embed(self, audio: np.ndarray) -> np.ndarray | None:
        """Extract a voice embedding from float32 16kHz audio."""
        try:
            # Normalise
            audio = audio.astype(np.float32)
            if audio.max() > 1.0:
                audio /= 32768.0

            if _BACKEND == "speechbrain" and self._encoder:
                import torch
                tensor = torch.tensor(audio).unsqueeze(0)
                emb    = self._encoder.encode_batch(tensor)
                return emb.squeeze().detach().numpy()

            elif _BACKEND == "resemblyzer" and self._encoder:
                from resemblyzer import preprocess_wav
                wav = preprocess_wav(audio, source_sr=16000)
                return self._encoder.embed_utterance(wav)

            else:
                # Simple fingerprint: MFCC-like mean energy per band
                return self._simple_fingerprint(audio)

        except Exception as e:
            log.error(f"Embedding error: {e}")
            return None

    @staticmethod
    def _simple_fingerprint(audio: np.ndarray, n_bands: int = 64) -> np.ndarray:
        """
        Fallback: compute mean spectral energy across frequency bands.
        Not speaker-specific enough for high security, but works as a demo.
        """
        fft = np.abs(np.fft.rfft(audio, n=2048))
        band_size = len(fft) // n_bands
        bands = [fft[i*band_size:(i+1)*band_size].mean() for i in range(n_bands)]
        arr = np.array(bands, dtype=np.float32)
        norm = np.linalg.norm(arr)
        return arr / (norm + 1e-9)

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
