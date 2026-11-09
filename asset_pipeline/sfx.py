"""Procedural audio synthesis classes and measured WAV export helpers."""

from pathlib import Path
from typing import Optional, Sequence, Tuple
import numpy as np
from scipy.io import wavfile


class Sound:
    """Class representing synthesized audio PCM samples."""

    def __init__(self, samples: np.ndarray, rate: int = 48000):
        self.samples = np.asarray(samples, dtype=np.float64)
        self.rate = rate

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return len(self.samples) / self.rate

    @property
    def peak(self) -> float:
        """Peak amplitude."""
        return float(np.max(np.abs(self.samples)))

    @property
    def peak_dbfs(self) -> float:
        """Peak level in dBFS relative to full scale 1.0."""
        peak = self.peak
        return float(20 * np.log10(peak)) if peak > 0 else -np.inf

    def apply_envelope(self, envelope: np.ndarray) -> "Sound":
        """Multiply samples by an amplitude envelope."""
        self.samples = self.samples * envelope[:len(self.samples)]
        return self

    def normalize(self, headroom_db: float = -3.0) -> "Sound":
        """Scale signal to specified peak headroom in dBFS."""
        peak = self.peak
        if peak > 0:
            target = 10.0 ** (headroom_db / 20.0)
            self.samples = self.samples * (target / peak)
        return self

    def to_pcm16(self, headroom_db: float = -3.0) -> np.ndarray:
        """Export normalized 16-bit signed integer PCM array."""
        return to_pcm16(self.samples, headroom_db=headroom_db)

    def export(self, path: Path | str, headroom_db: float = -3.0) -> Path:
        """Write audio to WAV file with headroom normalization."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        pcm = self.to_pcm16(headroom_db=headroom_db)
        wavfile.write(out, self.rate, pcm)
        return out


class SoundSynthesizer:
    """Procedural synthesizer for modal synthesis, transients, and envelopes."""

    def __init__(self, rate: int = 48000, seed: Optional[int] = None):
        self.rate = rate
        self.rng = np.random.default_rng(seed)

    def time_vector(self, duration: float) -> np.ndarray:
        """Return 1D array of time points."""
        return np.linspace(0, duration, int(self.rate * duration), endpoint=False)

    def modal_resonator(
        self,
        duration: float,
        frequencies: Sequence[float],
        decays: Sequence[float],
        amplitudes: Sequence[float],
    ) -> Sound:
        """Generate sum of damped sinusoidal modal resonance modes."""
        t = self.time_vector(duration)
        samples = resonator(frequencies, decays, amplitudes, t)
        return Sound(samples, rate=self.rate)

    def transient_click(self, duration: float, decay_rate: float = 60.0) -> Sound:
        """Generate an impact transient noise burst."""
        t = self.time_vector(duration)
        noise = self.rng.uniform(-1.0, 1.0, size=len(t))
        env = np.exp(-decay_rate * t)
        return Sound(noise * env, rate=self.rate)

    def adsr_envelope(
        self,
        duration: float,
        attack: float = 0.01,
        decay: float = 0.05,
        sustain: float = 0.7,
        release: float = 0.1,
    ) -> np.ndarray:
        """Generate an ADSR envelope curve."""
        n_samples = int(self.rate * duration)
        return envelope_adsr(n_samples, self.rate, attack, decay, sustain, release)


# Functional helpers for backwards-compatibility
def to_pcm16(signal: np.ndarray, headroom_db: float = -3.0) -> np.ndarray:
    sig = np.asarray(signal, dtype=np.float64)
    if not np.isfinite(sig).all():
        raise ValueError("Audio signal contains NaN or infinite values")

    peak = float(np.max(np.abs(sig)))
    if peak == 0:
        return np.zeros_like(sig, dtype=np.int16)

    target_amp = 32767.0 * (10.0 ** (headroom_db / 20.0))
    scale = target_amp / peak
    normalized = np.clip(sig * scale, -32767.0, 32767.0)

    pcm = normalized.astype(np.int16)
    if len(pcm) > 2:
        pcm[0] = 0
        pcm[-1] = 0
    return pcm


def export_wav(path: Path | str, samples: np.ndarray, rate: int = 48000) -> Path:
    out = Path(path)
    pcm = samples if samples.dtype == np.int16 else to_pcm16(samples)
    wavfile.write(out, rate, pcm)
    return out


def envelope_adsr(
    num_samples: int,
    rate: int,
    attack: float = 0.01,
    decay: float = 0.05,
    sustain: float = 0.7,
    release: float = 0.1,
) -> np.ndarray:
    total_time = num_samples / rate
    t = np.linspace(0, total_time, num_samples, endpoint=False)
    env = np.zeros(num_samples, dtype=np.float64)

    a_end = attack
    d_end = attack + decay
    r_start = max(d_end, total_time - release)

    for i, ti in enumerate(t):
        if ti < a_end:
            env[i] = ti / max(1e-6, a_end)
        elif ti < d_end:
            frac = (ti - a_end) / max(1e-6, decay)
            env[i] = 1.0 - (1.0 - sustain) * frac
        elif ti < r_start:
            env[i] = sustain
        else:
            frac = (ti - r_start) / max(1e-6, release)
            env[i] = max(0.0, sustain * (1.0 - frac))
    return env


def exponential_decay(t: np.ndarray, rate: float = 10.0) -> np.ndarray:
    return np.exp(-rate * t)


def resonator(
    frequencies: Sequence[float],
    decays: Sequence[float],
    amplitudes: Sequence[float],
    t: np.ndarray,
) -> np.ndarray:
    out = np.zeros_like(t, dtype=np.float64)
    for f, d, a in zip(frequencies, decays, amplitudes):
        out += a * np.sin(2 * np.pi * f * t) * np.exp(-d * t)
    return out
