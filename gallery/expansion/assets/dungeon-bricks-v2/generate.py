#!/usr/bin/env python3
"""Procedural 2D seamless tile generator: Dungeon Bricks (V2).

Vault techniques applied (declared in the manifest and audited):
- Running-bond brick layout with a pixel-space distance field and smoothstep bevel
  (vault/techniques/materials/chiseled_stone_and_masonry.md)
- Periodic Worley cellular noise for edge chipping and pitting
  (vault/mathematics/noise_and_fields/worley_cellular_noise.md)
- Integer-frequency Fourier grain, seamless by construction
  (vault/mathematics/noise_and_fields/toroidal_periodic_harmonics.md)
- Tangent-space normal map from the height field, wrapped at borders
  (vault/mathematics/materials/height_to_normal_sobel.md)

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
from asset_pipeline import (
    AssetValidator,
    Manifest,
    SeamlessTile,
    heightmap_to_normal_map,
    sprite2d,
    worley_noise,
)

ASSET_NAME = "dungeon_bricks_v2"
ROWS, COLS = 6, 3


def smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def draw_tile(size: int = 256, seed: int = 7) -> tuple[Image.Image, np.ndarray]:
    """Returns (albedo RGBA image, height field in [0, 1]); both tile seamlessly."""
    rng = np.random.default_rng(seed)
    theta, phi = SeamlessTile(size=size, seed=seed).generate_toroidal_grid()
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)

    brick_h = size / ROWS
    brick_w = size / COLS
    row = np.floor(y / brick_h).astype(int)
    shift = np.where(row % 2 == 1, brick_w / 2.0, 0.0)
    xs = (x + shift) % size
    col = np.floor(xs / brick_w).astype(int) % COLS
    u = (xs % brick_w)
    v = (y % brick_h)

    # Distance (px) to the nearest brick edge, minus half the mortar joint (negative = mortar)
    mortar = size * 0.022
    d = np.minimum.reduce([u, brick_w - u, v, brick_h - v]) - mortar / 2.0
    bevel_px = size * 0.030
    bevel = smoothstep(d / bevel_px)

    # Periodic noise fields: coarse chips near edges, fine pitting, and Fourier grain
    chips = worley_noise(size, size, grid_x=10, grid_y=10, seed=seed, periodic=True)
    pits = worley_noise(size, size, grid_x=36, grid_y=36, seed=seed + 1, periodic=True)
    grain = (0.5 * np.sin(5 * theta + 0.7) * np.cos(4 * phi)
             + 0.3 * np.sin(11 * theta) * np.sin(9 * phi + 1.3)
             + 0.2 * np.cos(23 * theta + 2.0) * np.cos(19 * phi))
    fine = rng.uniform(-1, 1, (size, size))
    fine = (fine + np.roll(fine, 1, 0) + np.roll(fine, 1, 1) + np.roll(fine, (1, 1), (0, 1))) / 4.0

    # Edge chipping: erode the bevel where cell-noise is low and we are close to the edge
    edge_zone = 1.0 - smoothstep(d / (size * 0.06))
    chip_cut = smoothstep((0.42 - chips) / 0.25) * edge_zone
    stone_h = bevel * (1.0 - 0.55 * chip_cut) + 0.06 * grain + 0.05 * (1.0 - pits) + 0.02 * fine
    is_stone = d > 0

    # Each brick gets its own tone and warm/cool lean (hash is wrap-safe: col is taken mod COLS)
    ids = (row * COLS + col).astype(np.int64)
    tone = rng.uniform(-14, 14, ROWS * COLS)[ids]
    lean = rng.uniform(-6, 6, ROWS * COLS)[ids]

    height = np.where(is_stone, 0.38 + 0.55 * stone_h, 0.10 + 0.05 * (grain * 0.5 + 0.5) + 0.03 * fine)
    height = np.clip(height, 0.0, 1.0)

    base = 118.0 + tone + 16.0 * grain + 9.0 * (1.0 - pits) + 10.0 * fine
    base = base * (0.78 + 0.22 * bevel) * (1.0 - 0.28 * chip_cut)       # edge occlusion + chip darkening
    stone = np.dstack([base + lean + 4, base + 2, base - lean + 10])
    mortar_base = 46.0 + 10.0 * grain + 8.0 * fine
    mortar_rgb = np.dstack([mortar_base + 4, mortar_base + 2, mortar_base + 6])
    # Soft AO into mortar next to stone edges
    mortar_rgb *= (0.7 + 0.3 * smoothstep(-d / (size * 0.02)))[..., None]

    rgb = np.where(is_stone[..., None], stone, mortar_rgb).clip(0, 255).astype(np.uint8)
    alpha = np.full((size, size, 1), 255, dtype=np.uint8)
    return Image.fromarray(np.concatenate([rgb, alpha], axis=2), mode="RGBA"), height.astype(np.float32)


def lit_preview(albedo: Image.Image, normal_rgb: np.ndarray, light=(-0.5, -0.6, 0.62)) -> Image.Image:
    """Albedo shaded by its normal map under a fixed key light (for visual QA only)."""
    n = normal_rgb.astype(np.float32) / 127.5 - 1.0
    l = np.asarray(light, dtype=np.float32)
    l /= np.linalg.norm(l)
    ndl = np.clip((n * l).sum(axis=2), 0.0, 1.0)
    rgb = np.asarray(albedo.convert("RGB"), dtype=np.float32) * (0.35 + 0.95 * ndl)[..., None]
    return Image.fromarray(rgb.clip(0, 255).astype(np.uint8))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--size", type=int, default=256, help="Tile size in pixels")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    image, height_map = draw_tile(size=args.size, seed=args.seed)

    asset_file = args.out / f"{ASSET_NAME}.png"
    normal_file = args.out / f"{ASSET_NAME}_normal.png"
    preview_file = args.out / "preview.png"

    image.save(asset_file)

    # Generate tangent-space normal map
    normal_rgb = heightmap_to_normal_map(height_map, strength=3.5, tileable=True)
    Image.fromarray(normal_rgb).save(normal_file)

    # Preview: 2x2 tiled albedo | 2x2 tiled normal-lit albedo (reveals bevels/chips and any seams)
    lit = lit_preview(image, normal_rgb)
    tiled = sprite2d.create_tiled_preview(image.convert("RGB"), grid=(2, 2))
    tiled_lit = sprite2d.create_tiled_preview(lit, grid=(2, 2))
    preview = Image.new("RGB", (tiled.width * 2, tiled.height))
    preview.paste(tiled, (0, 0))
    preview.paste(tiled_lit, (tiled.width, 0))
    preview.save(preview_file)

    AssetValidator.validate_png(asset_file, require_alpha=False)
    AssetValidator.validate_seamless(asset_file, max_ratio=2.0)
    AssetValidator.validate_seamless(normal_file, max_ratio=2.0)

    manifest = Manifest(
        asset=asset_file.name,
        parameters={"size": args.size, "seed": args.seed, "version": "v2_vault", "rows": ROWS, "cols": COLS},
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("techniques/materials/chiseled_stone_and_masonry.md", "smoothstep")
    manifest.declare_vault("mathematics/noise_and_fields/worley_cellular_noise.md", "worley_noise")
    manifest.declare_vault("mathematics/noise_and_fields/toroidal_periodic_harmonics.md", "generate_toroidal_grid")
    manifest.declare_vault("mathematics/materials/height_to_normal_sobel.md", "heightmap_to_normal_map")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {asset_file}, {normal_file}, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
