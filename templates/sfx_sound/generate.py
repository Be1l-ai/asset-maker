#!/usr/bin/env python3
"""Procedural SFX audio generator template.

Usage:
    python generate.py [--duration 0.5] [--rate 48000] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from asset_pipeline import AssetValidator, Manifest, Sound, SoundSynthesizer

ASSET_NAME = "sound"


def synthesize(duration: float = 0.5, rate: int = 48000, seed: int = 7) -> Sound:
    """Agent edits this function to synthesize audio."""
    synth = SoundSynthesizer(rate=rate, seed=seed)

    # 1. Resonant modal body
    body = synth.modal_resonator(
        duration=duration,
        frequencies=[380.0, 380.0 * 2.76, 380.0 * 5.40],
        decays=[12.0, 18.0, 24.0],
        amplitudes=[1.0, 0.5, 0.2],
    )

    # 2. Transient strike / click noise
    click = synth.transient_click(duration=duration, decay_rate=80.0)

    # 3. Combine samples into a Sound object
    combined_samples = body.samples + 0.4 * click.samples
    return Sound(combined_samples, rate=rate)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--duration", type=float, default=0.5, help="Sound duration in seconds")
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
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {wav_file} (passed validation)")


if __name__ == "__main__":
    main()
