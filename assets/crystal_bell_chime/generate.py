#!/usr/bin/env python3
"""Procedural SFX audio generator: Crystal Bell Chime.

Synthesizes a crystalline chime using physical modal resonance, inharmonic partials, and a transient strike.
Usage:
    python generate.py [--duration 1.25] [--rate 48000] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from asset_pipeline import AssetValidator, Manifest, Sound, SoundSynthesizer

ASSET_NAME = "crystal_bell_chime"


def synthesize(duration: float = 1.25, rate: int = 48000, seed: int = 7) -> Sound:
    """Synthesizes a high-resonance crystalline bell chime."""
    synth = SoundSynthesizer(rate=rate, seed=seed)
    rng = np.random.default_rng(seed)

    f0 = 880.0  # Crystal pitch A5

    # 1. Resonant modal body (Glass / Crystal inharmonic ratios: 1.0, 2.32, 4.15, 6.70)
    modes = [
        (f0 * 1.00, 4.2, 1.00),
        (f0 * 1.41, 5.0, 0.28),   # Inharmonic chime ring
        (f0 * 2.32, 6.8, 0.52),
        (f0 * 4.15, 9.5, 0.26),
        (f0 * 6.70, 14.0, 0.14),
    ]

    frequencies = [m[0] for m in modes]
    decays = [m[1] for m in modes]
    amplitudes = [m[2] for m in modes]

    body = synth.modal_resonator(
        duration=duration,
        frequencies=frequencies,
        decays=decays,
        amplitudes=amplitudes,
    )

    # 2. Transient impact strike (sharp click from glass/metal striker)
    t = synth.time_vector(duration)
    # Bandpassed high-frequency burst
    click_noise = rng.uniform(-1.0, 1.0, size=len(t))
    click_carrier = np.sin(2 * np.pi * 3200.0 * t)
    click_env = np.exp(-120.0 * t)
    click_samples = (0.6 * click_noise + 0.4 * click_carrier) * click_env

    # 3. Combine body and transient
    combined = body.samples + 0.20 * click_samples

    # Subtle smooth fadeout at the tail to guarantee zero endpoint
    tail_len = int(0.05 * rate)
    fade_tail = np.linspace(1.0, 0.0, tail_len)
    combined[-tail_len:] *= fade_tail

    return Sound(combined, rate=rate)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--duration", type=float, default=1.25, help="Sound duration in seconds")
    parser.add_argument("--rate", type=int, default=48000, help="Sample rate in Hz")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    sound = synthesize(duration=args.duration, rate=args.rate, seed=args.seed)

    wav_file = args.out / f"{ASSET_NAME}.wav"
    sound.export(wav_file, headroom_db=-3.0)

    AssetValidator.validate_wav(wav_file)

    manifest = Manifest(
        asset=wav_file.name,
        parameters={"duration": args.duration, "rate": args.rate, "seed": args.seed},
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out).save(args.out)
    print(f"✓ Generated {wav_file} (passed validation)")


if __name__ == "__main__":
    main()
