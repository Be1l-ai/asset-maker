#!/usr/bin/env python3
"""Procedural VFX flipbook generator template.

Usage:
    python generate.py [--frames 16] [--size 128] [--fps 16] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image
from asset_pipeline import AssetValidator, Flipbook, Manifest, ParticleEmitter

ASSET_NAME = "flipbook"


def generate_flipbook(frames: int = 16, size: int = 128, fps: int = 16, seed: int = 7) -> Flipbook:
    """Agent edits this function to compose the flipbook animation."""
    emitter = ParticleEmitter(seed=seed)
    flipbook = Flipbook(fps=fps)

    flipbook.generate_frames(
        count=frames,
        frame_generator=lambda phase: emitter.radial_burst(
            size=size,
            phase=phase,
            color_rgb=(100, 200, 255),
            particle_count=12,
        ),
    )
    return flipbook


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--frames", type=int, default=16, help="Total frames")
    parser.add_argument("--size", type=int, default=128, help="Frame width/height")
    parser.add_argument("--columns", type=int, default=4, help="Atlas grid columns")
    parser.add_argument("--fps", type=int, default=16, help="Playback FPS")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    flipbook = generate_flipbook(frames=args.frames, size=args.size, fps=args.fps, seed=args.seed)
    rows = int(np.ceil(args.frames / args.columns))

    atlas_file = args.out / f"{ASSET_NAME}.png"
    preview_gif = args.out / "preview.gif"
    preview_png = args.out / "preview.png"

    flipbook.export_atlas(atlas_file, columns=args.columns)
    flipbook.export_gif(preview_gif)
    flipbook.export_preview(preview_png)

    AssetValidator.validate_png(atlas_file, require_alpha=True, columns=args.columns, rows=rows)
    AssetValidator.validate_animation(atlas_file, columns=args.columns, rows=rows)

    manifest = Manifest(
        asset=atlas_file.name,
        parameters={"frames": args.frames, "fps": args.fps, "grid": [args.columns, rows], "seed": args.seed},
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {atlas_file}, preview.gif, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
