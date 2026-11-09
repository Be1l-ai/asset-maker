#!/usr/bin/env python3
"""Procedural 2D seamless tile generator template.

Usage:
    python generate.py [--size 256] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image
from asset_pipeline import AssetValidator, Manifest, SeamlessTile, sprite2d

ASSET_NAME = "tile"


def draw_tile(size: int = 256, seed: int = 7) -> Image.Image:
    """Agent edits this function to design a seamlessly repeating texture tile."""
    tile_gen = SeamlessTile(size=size, seed=seed)
    theta, phi = tile_gen.generate_toroidal_grid()

    # Periodic basis functions guarantee seamless boundary continuity
    n1 = np.sin(theta) + np.cos(phi)
    n2 = np.sin(2 * theta + 0.5) * np.cos(2 * phi)
    pattern = (n1 + 0.5 * n2) / 1.5

    t = (pattern - pattern.min()) / (pattern.max() - pattern.min())
    r = np.clip(60 + t * 40 + tile_gen.rng.uniform(-5, 5, (size, size)), 0, 255).astype(np.uint8)
    g = np.clip(80 + t * 50 + tile_gen.rng.uniform(-5, 5, (size, size)), 0, 255).astype(np.uint8)
    b = np.clip(65 + t * 30 + tile_gen.rng.uniform(-5, 5, (size, size)), 0, 255).astype(np.uint8)
    a = np.full((size, size), 255, dtype=np.uint8)

    rgba = np.dstack([r, g, b, a])
    return Image.fromarray(rgba, mode="RGBA")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--size", type=int, default=256, help="Tile size in pixels")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    image = draw_tile(size=args.size, seed=args.seed)

    asset_file = args.out / f"{ASSET_NAME}.png"
    preview_file = args.out / "preview.png"

    image.save(asset_file)
    sprite2d.create_tiled_preview(image, grid=(3, 3)).save(preview_file)

    AssetValidator.validate_png(asset_file, require_alpha=False)

    manifest = Manifest(
        asset=asset_file.name,
        parameters={"size": args.size, "seed": args.seed, "seamless": True},
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out).save(args.out)
    print(f"✓ Generated seamless {asset_file} and 3x3 tiled preview.png (passed validation)")


if __name__ == "__main__":
    main()
