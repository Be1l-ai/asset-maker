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

    def bell_resonator(self, f0: float = 440.0, duration: float = 2.0) -> Sound:
        """Synthesize a bronze bell using acoustic ratios (Hum 0.5, Prime 1.0, Tierce 1.2, Quint 1.5, Nominal 2.0)."""
        freqs = [f0 * 0.5, f0 * 1.0, f0 * 1.2, f0 * 1.5, f0 * 2.0]
        decays = [2.5, 4.0, 5.5, 7.0, 9.0]
        amps = [0.85, 1.0, 0.6, 0.45, 0.35]
        return self.modal_resonator(duration, freqs, decays, amps)

    def wood_resonator(self, f0: float = 520.0, duration: float = 0.4) -> Sound:
        """Synthesize an undercut wooden bar/marimba using tuned octave ratios (1.0, 4.0, 10.0)."""
        freqs = [f0 * 1.0, f0 * 4.0, f0 * 10.0]
        decays = [28.0, 45.0, 65.0]
        amps = [1.0, 0.4, 0.15]
        return self.modal_resonator(duration, freqs, decays, amps)

    def glass_resonator(self, f0: float = 880.0, duration: float = 1.5) -> Sound:
        """Synthesize a glass bowl/chime using circumferential flexural ratios (1.0, 2.32, 4.15, 6.70)."""
        freqs = [f0 * 1.0, f0 * 2.32, f0 * 4.15, f0 * 6.70]
        decays = [3.5, 6.0, 9.5, 14.0]
        amps = [1.0, 0.5, 0.25, 0.12]
        return self.modal_resonator(duration, freqs, decays, amps)

    def tubular_chime_resonator(self, f0: float = 600.0, duration: float = 1.8) -> Sound:
        """Synthesize a hollow metal tubular bell chime using ratios (1.0, 4.2, 9.7)."""
        freqs = [f0 * 1.0, f0 * 4.2, f0 * 9.7]
        decays = [4.0, 7.5, 12.0]
        amps = [1.0, 0.55, 0.25]
        return self.modal_resonator(duration, freqs, decays, amps)


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


def spatial_stereo_pan(
    sound: Sound,
    pan: float = 0.0,
    haas_delay_ms: float = 0.0,
) -> np.ndarray:
    """Apply constant-power panning and optional Haas psychoacoustic delay to a mono Sound.

    Parameters:
        sound: Mono Sound object.
        pan: Panning position from -1.0 (hard left) to +1.0 (hard right). 0.0 is center.
        haas_delay_ms: Inter-aural time difference delay in milliseconds (typically 1.0 to 15.0 ms).

    Returns:
        2D float64 array of shape (N, 2) where column 0 is Left and column 1 is Right.
    """
    pan_clamped = float(np.clip(pan, -1.0, 1.0))
    # Constant power panning angles (0 to pi/2)
    theta = (pan_clamped + 1.0) * (np.pi / 4.0)
    left_gain = np.cos(theta)
    right_gain = np.sin(theta)

    mono = sound.samples
    left_chan = mono * left_gain
    right_chan = mono * right_gain

    # Apply Haas delay if requested
    if haas_delay_ms > 0:
        delay_samples = int(round((haas_delay_ms / 1000.0) * sound.rate))
        if delay_samples > 0:
            if pan_clamped >= 0:
                # Sound pans right -> left ear receives delayed signal
                delayed = np.zeros_like(left_chan)
                delayed[delay_samples:] = left_chan[:-delay_samples]
                left_chan = delayed
            else:
                # Sound pans left -> right ear receives delayed signal
                delayed = np.zeros_like(right_chan)
                delayed[delay_samples:] = right_chan[:-delay_samples]
                right_chan = delayed

    return np.column_stack([left_chan, right_chan])

