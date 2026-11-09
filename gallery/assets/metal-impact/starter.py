import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


MODES = {
    "metal": [(1.0, 1.0, 1.0), (1.48, 0.55, 0.72), (2.09, 0.3, 0.48), (3.12, 0.16, 0.3)],
    "glass": [(1.0, 0.65, 0.6), (1.59, 1.0, 0.8), (2.32, 0.4, 0.4), (3.47, 0.2, 0.3)],
    "wood": [(1.0, 1.0, 0.18), (2.76, 0.35, 0.1), (5.4, 0.15, 0.06)],
}


def synthesize(seed=7, duration=1.2, rate=48000, frequency=420.0, material="metal", gain=0.5):
    rng = np.random.default_rng(seed)
    t = np.arange(round(rate * duration), dtype=np.float64) / rate
    attack = 1 - np.exp(-t / 0.0015)
    body = np.zeros_like(t)
    for ratio, amplitude, decay in MODES[material]:
        hz = frequency * ratio * rng.uniform(0.995, 1.005)
        body += amplitude * np.sin(2 * np.pi * hz * t) * np.exp(-t / decay)
    noise = rng.standard_normal(len(t))
    sos = signal.butter(2, [700, 7000], btype="bandpass", fs=rate, output="sos")
    transient = signal.sosfilt(sos, noise) * np.exp(-t / 0.014)
    samples = gain * attack * (0.36 * body + 0.13 * transient)
    samples -= samples.mean()
    fade = min(round(rate * 0.035), len(samples) // 3)
    samples[:fade] *= np.linspace(0, 1, fade) ** 0.25
    samples[-fade:] *= np.linspace(1, 0, fade) ** 2
    peak = np.abs(samples).max()
    ceiling = 10 ** (-3 / 20)
    if peak > ceiling:
        samples *= ceiling / peak
    return np.rint(samples * 32767).astype(np.int16)


def main():
    parser = argparse.ArgumentParser(description="Study and customize a seeded modal-impact recipe.")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--duration", type=float, default=1.2)
    parser.add_argument("--rate", type=int, choices=[22050, 44100, 48000, 96000], default=48000)
    parser.add_argument("--frequency", type=float, default=420)
    parser.add_argument("--material", choices=MODES, default="metal")
    parser.add_argument("--gain", type=float, default=0.5)
    args = parser.parse_args()
    if not (0.08 <= args.duration <= 30 and 0 < args.gain <= 2 and args.seed >= 0):
        parser.error("Use duration 0.08..30, gain (0, 2], and a nonnegative seed")
    if not 20 <= args.frequency < args.rate * 0.45 / max(m[0] for m in MODES[args.material]):
        parser.error("Frequency must be >=20 Hz and keep every mode below 90% of Nyquist")
    try:
        samples = synthesize(args.seed, args.duration, args.rate, args.frequency, args.material, args.gain)
        args.out.mkdir(parents=True, exist_ok=False)
        wavfile.write(args.out / "impact.wav", args.rate, samples)
        (args.out / "recipe.py").write_text(Path(__file__).read_text())
        metadata = {
            "asset": "impact.wav", "format": "PCM16 WAV", "channels": 1,
            "sample_rate": args.rate, "loop": False,
            "parameters": {k: v for k, v in vars(args).items() if k != "out"},
            "versions": {p: version(p) for p in ["numpy", "scipy"]},
            "sha256": {name: hashlib.sha256((args.out / name).read_bytes()).hexdigest()
                       for name in ["impact.wav", "recipe.py"]},
        }
        (args.out / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps({"output": str(args.out), "frames": len(samples),
                          "duration_seconds": len(samples) / args.rate}))
    except (OSError, ValueError) as error:
        parser.exit(1, f"SFX generation failed: {error}\n")


if __name__ == "__main__":
    main()
