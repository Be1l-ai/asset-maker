#!/usr/bin/env python3
"""Procedural 2D seamless tile generator: Dungeon Bricks.

Generates an interlocking stone masonry tile with chiseled edges, mortar crevices, and surface noise.
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

ASSET_NAME = "dungeon_bricks"


def draw_tile(size: int = 256, seed: int = 7) -> Image.Image:
    """Generates a seamless stone dungeon brick texture using periodic math."""
    tile_gen = SeamlessTile(size=size, seed=seed)
    rng = tile_gen.rng
    theta, phi = tile_gen.generate_toroidal_grid()

    # Brick grid layout: 4 rows of bricks, 2 bricks per row (running bond)
    num_rows = 4
    num_cols = 2
    y_idx, x_idx = np.mgrid[0:size, 0:size]
    norm_y = y_idx / size
    norm_x = x_idx / size

    # Identify row
    row_val = norm_y * num_rows
    row = np.floor(row_val).astype(int)
    row_frac = row_val - row

    # Offset alternate rows by half a brick
    x_shift = np.where(row % 2 == 1, 0.5 / num_cols, 0.0)
    shifted_x = (norm_x + x_shift) % 1.0
    col_val = shifted_x * num_cols
    col = np.floor(col_val).astype(int)
    col_frac = col_val - col

    # Distance to mortar lines (normalized 0..1 where 0 is center of brick, 1 is edge)
    # Horizontal distance from brick center:
    dx = np.abs(col_frac - 0.5) * 2.0  # 0 at center, 1 at vertical joint
    # Vertical distance from brick center:
    dy = np.abs(row_frac - 0.5) * 2.0  # 0 at center, 1 at horizontal joint

    # Mortar thickness mask
    mortar_width = 0.12
    is_mortar = (dx > (1.0 - mortar_width)) | (dy > (1.0 - mortar_width * 1.5))

    # Chiseled bevel distance: falloff towards edges
    edge_dist = np.maximum(dx, dy)
    bevel = np.clip((1.0 - edge_dist) / (1.0 - (1.0 - mortar_width)), 0.0, 1.0)
    bevel = 3.0 * bevel**2 - 2.0 * bevel**3  # smoothstep

    # Periodic continuous noise for stone grain (guaranteed seamless via toroidal angles)
    grain = (
        0.35 * np.sin(3 * theta) * np.cos(3 * phi)
        + 0.25 * np.sin(7 * theta + 0.4) * np.sin(7 * phi + 0.8)
        + 0.15 * np.cos(13 * theta - 0.2) * np.sin(11 * phi + 1.1)
        + 0.10 * np.sin(21 * theta) * np.cos(19 * phi)
    )

    # Per-brick subtle color variation (seeded per row and col hash)
    brick_hash = np.sin(row * 12.9898 + col * 78.233 + seed) * 43758.5453
    brick_var = (brick_hash - np.floor(brick_hash)) * 20.0 - 10.0

    # Base stone color (cool slate grey)
    stone_base = 115.0 + bevel * 45.0 + grain * 28.0 + brick_var
    mortar_color = 52.0 + grain * 12.0

    # Compose final brightness
    intensity = np.where(is_mortar, mortar_color, stone_base)
    intensity = np.clip(intensity, 0, 255)

    # RGB mapping: Stone has slight blue-grey hue, mortar has faint warm earthen tone
    r = np.where(is_mortar, intensity * 0.95, intensity * 0.92).astype(np.uint8)
    g = np.where(is_mortar, intensity * 0.92, intensity * 0.96).astype(np.uint8)
    b = np.where(is_mortar, intensity * 0.88, intensity * 1.02).astype(np.uint8)
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
        parameters={"size": args.size, "seed": args.seed},
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out).save(args.out)
    print(f"✓ Generated {asset_file} and preview.png (passed validation)")


if __name__ == "__main__":
    main()
