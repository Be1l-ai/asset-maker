#!/usr/bin/env python3
"""Procedural SFX audio generator: Crystal Bell Chime (V2).

Recreated using Vault techniques:
- Dual-body acoustic modal synthesis (bronze bell harmonic tierce/quint layered with glass circumferential shell modes)
- Hard transient contact impact (3.6 kHz click, ~7 ms exponential decay)
- Psychoacoustic Haas stereo spreading (4.5 ms delay, constant-power pan)
- Strict -3.0 dBFS peak headroom and zero-crossing endpoints

Usage:
    python generate.py [--duration 1.5] [--rate 48000] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.io import wavfile
from asset_pipeline import (
    AssetValidator,
    Manifest,
    Sound,
    SoundSynthesizer,
    spatial_stereo_pan,
)

ASSET_NAME = "crystal_bell_chime_v2"

# Measured recipe constants (recorded in manifest.json so docs can never drift from the code)
F0_HZ = 880.0            # glass shell fundamental (A5)
BRONZE_RATIO = 0.5       # bronze body one octave below
CLICK_HZ = 3600.0        # mallet transient tone
CLICK_DECAY = 140.0      # exp(-k t): tau = 1/k ~= 7.1 ms
HAAS_MS = 4.5            # inter-aural delay
PAN = 0.15               # constant-power pan (+ = right)


def synthesize(duration: float = 1.5, rate: int = 48000, seed: int = 7) -> tuple[Sound, np.ndarray]:
    """Synthesizes an enhanced crystal chime with spatial stereo width."""
    synth = SoundSynthesizer(rate=rate, seed=seed)
    rng = np.random.default_rng(seed)

    f0 = F0_HZ

    # 1. Glass / Quartz circumferential flexural shell body (Vault: glass_shells.md)
    glass_body = synth.glass_resonator(f0=f0, duration=duration)

    # 2. Bronze bell resonant body for deeper acoustic presence (Vault: church_bells_bronze.md)
    # Scaled an octave lower for rich foundational hum tone
    bell_body = synth.bell_resonator(f0=f0 * BRONZE_RATIO, duration=duration)

    # 3. Metallic striker transient impact click
    t = synth.time_vector(duration)
    click_noise = rng.uniform(-1.0, 1.0, size=len(t))
    click_tone = np.sin(2 * np.pi * CLICK_HZ * t)
    click_env = np.exp(-CLICK_DECAY * t)
    transient = (0.6 * click_noise + 0.4 * click_tone) * click_env

    # 4. Layer bodies together
    combined_samples = (
        glass_body.samples * 0.70
        + bell_body.samples * 0.35
        + transient * 0.22
    )

    # Tail micro-ramp to guarantee zero endpoint
    tail_len = int(0.04 * rate)
    combined_samples[-tail_len:] *= np.linspace(1.0, 0.0, tail_len)

    mono_sound = Sound(combined_samples, rate=rate)

    # 5. Psychoacoustic Haas spatial stereo field (Vault: spatial spreading)
    # Subtle right-bias with 4.5ms inter-aural time difference
    stereo_pcm = spatial_stereo_pan(mono_sound, pan=PAN, haas_delay_ms=HAAS_MS)

    return mono_sound, stereo_pcm


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--duration", type=float, default=1.5, help="Sound duration in seconds")
    parser.add_argument("--rate", type=int, default=48000, help="Sample rate in Hz")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    mono_sound, stereo_samples = synthesize(duration=args.duration, rate=args.rate, seed=args.seed)

    # Export mono WAV (standard for asset pipeline validation)
    wav_file = args.out / f"{ASSET_NAME}.wav"
    mono_sound.export(wav_file, headroom_db=-3.0)

    # Export enhanced stereo version
    stereo_file = args.out / f"{ASSET_NAME}_stereo.wav"
    # Normalize stereo to -3 dBFS
    stereo_peak = float(np.max(np.abs(stereo_samples)))
    if stereo_peak > 0:
        target = 32767.0 * (10.0 ** (-3.0 / 20.0))
        stereo_int16 = (stereo_samples * (target / stereo_peak)).clip(-32767, 32767).astype(np.int16)
        stereo_int16[0, :] = 0
        stereo_int16[-1, :] = 0
        wavfile.write(stereo_file, args.rate, stereo_int16)

    AssetValidator.validate_wav(wav_file)
    AssetValidator.validate_wav(stereo_file)

    manifest = Manifest(
        asset=wav_file.name,
        parameters={"duration": args.duration, "rate": args.rate, "seed": args.seed, "version": "v2_vault",
                    "f0_hz": F0_HZ, "bronze_ratio": BRONZE_RATIO, "click_hz": CLICK_HZ,
                    "click_decay_per_s": CLICK_DECAY, "haas_ms": HAAS_MS, "pan": PAN},
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("mathematics/acoustics/glass_shells.md", "glass_resonator")
    manifest.declare_vault("mathematics/acoustics/church_bells_bronze.md", "bell_resonator")
    manifest.declare_vault("mathematics/acoustics/spatial_haas_and_transients.md", "spatial_stereo_pan")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {wav_file} and {stereo_file} (passed validation)")


if __name__ == "__main__":
    main()
