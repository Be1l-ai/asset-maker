import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PIL import Image


def frame(size, phase, seed=7):
    rng = np.random.default_rng(seed)
    axis = (np.arange(size) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(axis, axis)
    radius = np.hypot(x, y)
    angle = np.arctan2(y, x)
    turn = 2 * np.pi * phase
    warp = np.zeros_like(radius)
    for harmonic in range(2, 7):
        warp += 0.025 / harmonic * np.sin(harmonic * angle + (harmonic - 1) * turn + rng.uniform(0, 2 * np.pi))
    ring_radius = 0.58 + warp + 0.018 * np.sin(3 * angle - 2 * turn)
    distance = np.abs(radius - ring_radius)
    core = np.exp(-(distance / 0.016) ** 2)
    glow = np.exp(-(distance / 0.065) ** 2)
    arc = (0.5 + 0.5 * np.sin(5 * angle - 3 * turn + 12 * radius)) ** 5
    energy = 0.85 * core + 0.5 * glow * (0.4 + 0.6 * arc)
    inner = np.exp(-((radius - 0.47) / 0.007) ** 2) * (0.5 + 0.5 * np.sin(8 * angle + turn)) ** 3
    energy += 0.25 * inner
    for _ in range(10):
        start, orbit, speed, scale = rng.uniform(0, 2 * np.pi), rng.uniform(0.65, 0.78), rng.integers(1, 3), rng.uniform(0.012, 0.022)
        theta = start + speed * turn
        squared = (x - orbit * np.cos(theta)) ** 2 + (y - orbit * np.sin(theta)) ** 2
        energy += 0.7 * np.exp(-squared / scale ** 2)
    alpha = np.clip(energy, 0, 1) * np.clip((0.94 - radius) / 0.06, 0, 1)
    rgb = np.empty((size, size, 3))
    hot = np.clip(core + inner, 0, 1)
    rgb[:, :, 0] = 50 + 170 * hot
    rgb[:, :, 1] = 110 + 140 * hot
    rgb[:, :, 2] = 255
    rgba = np.rint(np.dstack([rgb, alpha * 255])).astype(np.uint8)
    rgba[rgba[:, :, 3] == 0, :3] = 0
    return Image.fromarray(rgba)


def main():
    parser = argparse.ArgumentParser(description="Study and customize a periodic field-based VFX recipe.")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument("--size", type=int, default=128, help="Pixels per frame")
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--fps", type=int, default=16)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if not (16 <= args.size <= 512 and 2 <= args.frames <= 64 and 1 <= args.columns <= args.frames):
        parser.error("Use size 16..512, frames 2..64, and columns 1..frames")
    if args.frames % args.columns or not 1 <= args.fps <= 60 or args.seed < 0:
        parser.error("Frames must divide evenly into columns; use fps 1..60 and a nonnegative seed")
    try:
        frames = [frame(args.size, i / args.frames, args.seed) for i in range(args.frames)]
        rows = args.frames // args.columns
        atlas = Image.new("RGBA", (args.columns * args.size, rows * args.size))
        for i, image in enumerate(frames):
            atlas.paste(image, ((i % args.columns) * args.size, (i // args.columns) * args.size))
        backgrounds = []
        for color in [(20, 24, 36), (235, 237, 242)]:
            background = Image.new("RGBA", atlas.size, color + (255,))
            backgrounds.append(Image.alpha_composite(background, atlas).convert("RGB"))
        preview = Image.new("RGB", (atlas.width, atlas.height * 2))
        for i, image in enumerate(backgrounds):
            preview.paste(image, (0, i * atlas.height))
        animation = []
        for image in frames:
            background = Image.new("RGBA", image.size, (20, 24, 36, 255))
            animation.append(Image.alpha_composite(background, image).convert("RGB"))
        args.out.mkdir(parents=True, exist_ok=False)
        atlas.save(args.out / "portal.png")
        preview.save(args.out / "preview.png")
        animation[0].save(args.out / "preview.gif", save_all=True, append_images=animation[1:],
                          duration=round(1000 / args.fps), loop=0, disposal=2)
        (args.out / "recipe.py").write_text(Path(__file__).read_text())
        metadata = {
            "asset": "portal.png", "format": "RGBA PNG", "alpha": "straight",
            "frame_size": [args.size, args.size], "grid": [args.columns, rows],
            "frame_count": args.frames, "fps": args.fps, "loop": True,
            "duration_seconds": args.frames / args.fps,
            "order": "row-major, top-left", "padding_pixels": 0,
            "preview_note": "GIF timing is quantized; use manifest fps for the atlas.",
            "parameters": {k: v for k, v in vars(args).items() if k != "out"},
            "versions": {p: version(p) for p in ["numpy", "Pillow"]},
            "sha256": {name: hashlib.sha256((args.out / name).read_bytes()).hexdigest()
                       for name in ["portal.png", "preview.png", "preview.gif", "recipe.py"]},
        }
        (args.out / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps({"output": str(args.out), "atlas_size": list(atlas.size), "frames": args.frames}))
    except (OSError, ValueError) as error:
        parser.exit(1, f"VFX generation failed: {error}\n")


if __name__ == "__main__":
    main()
