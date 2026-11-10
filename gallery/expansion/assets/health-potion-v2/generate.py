#!/usr/bin/env python3
"""Procedural 2D icon generator: Health Potion (V2).

Vault techniques applied (each is declared in the manifest and audited):
- 70/30 silhouette hierarchy: one dominant round flask (~70% of mass), small neck/cork accents
  (vault/techniques/art_styles/silhouette_and_proportions.md)
- Warm-to-cool temperature ramp driven by distance-from-glass-edge
  (vault/techniques/art_styles/color_ramps_and_cel_steps.md)
- Woven twine wrap on the neck (vault/techniques/materials/fabric_and_weave_patterns.md)
- Tangent-space normal map from a height dome (vault/mathematics/materials/height_to_normal_sobel.md)

Implementation note: shapes are built as numpy coverage masks and composited with ``over``;
transparent aggdraw fills do NOT erase (they alpha-over), which is what broke the first V2.

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
from scipy.ndimage import gaussian_filter
from asset_pipeline import (
    AssetValidator,
    Manifest,
    SpriteCanvas,
    ellipse_mask,
    fillet_mask,
    heightmap_to_normal_map,
    inside_depth,
    lerp_color,
    new_layer,
    over,
    polygon_mask,
    procedural_fabric_weave,
)

ASSET_NAME = "health_potion_v2"

PLUM = (52, 24, 70)
RUBY = (232, 38, 78)
VIOLET = (96, 28, 128)
GLOW = (255, 120, 120)


def draw(size: int = 256, seed: int = 7) -> tuple[SpriteCanvas, np.ndarray]:
    """Draws the potion at 2x supersample and returns (canvas, height dome at target size)."""
    rng = np.random.default_rng(seed)
    canvas = SpriteCanvas(size=size, super_sample=2)
    S = canvas.scale
    shape = (S, S)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    px = lambda v: v * S  # unit coords -> pixels

    cx, cy, R = px(0.50), px(0.65), px(0.255)
    layer = new_layer(shape)

    # --- Silhouette: round flask + neck + flared lip, unioned and filleted -----------------
    body = ellipse_mask(shape, cx, cy, R, R)
    neck = polygon_mask(shape, [(px(0.43), px(0.24)), (px(0.57), px(0.24)),
                                (px(0.57), px(0.45)), (px(0.43), px(0.45))])
    lip = polygon_mask(shape, [(px(0.395), px(0.185)), (px(0.605), px(0.185)),
                               (px(0.575), px(0.25)), (px(0.425), px(0.25))])
    glass = fillet_mask(np.maximum.reduce([body, neck, lip]), px(0.012))
    depth = inside_depth(glass)
    rim = np.clip(depth / px(0.05), 0.0, 1.0)

    # --- Contact shadow -------------------------------------------------------------------
    shadow = ellipse_mask(shape, cx, px(0.93), px(0.23), px(0.04))
    over(layer, (20, 10, 30), gaussian_filter(shadow, px(0.012)) * 0.45)

    # --- Glass body tint + liquid ----------------------------------------------------------
    over(layer, (196, 220, 245), glass * (0.16 + 0.50 * (1.0 - rim) ** 2))

    meniscus_y = px(0.585) + px(0.006) * np.sin(xx / px(0.045))
    inner = (depth > px(0.016)).astype(np.float32)
    liquid = np.clip(inner * np.clip(yy - meniscus_y + 0.5, 0.0, 1.0), 0.0, 1.0)
    liq_depth = inside_depth(liquid)

    # Temperature ramp: cool violet at the glass edge -> warm ruby -> hot glow near the lit core
    t_edge = np.clip(liq_depth / px(0.14), 0.0, 1.0) ** 0.8
    liq_rgb = lerp_color(VIOLET, RUBY, t_edge)
    core = np.exp(-(((xx - (cx - px(0.045))) / px(0.12)) ** 2 + ((yy - (cy + px(0.07))) / px(0.12)) ** 2))
    liq_rgb = lerp_color(liq_rgb, GLOW, core * 0.75)
    over(layer, liq_rgb, liquid * 0.97)

    # Meniscus catch-light band
    surf = np.clip(1.0 - np.abs(yy - meniscus_y - px(0.006)) / px(0.008), 0.0, 1.0) * liquid
    over(layer, (255, 190, 200), surf * 0.85)

    # Bubbles: ring + fill, clipped to liquid
    bubbles = np.zeros(shape, dtype=np.float32)
    for bx, by, br in [(0.45, 0.70, 0.022), (0.55, 0.76, 0.028), (0.49, 0.64, 0.015),
                       (0.58, 0.67, 0.017), (0.42, 0.78, 0.013)]:
        bx += rng.uniform(-0.004, 0.004)
        disc = ellipse_mask(shape, px(bx), px(by), px(br), px(br))
        ring = np.clip(disc - ellipse_mask(shape, px(bx), px(by), px(br) - 2.0, px(br) - 2.0), 0, 1)
        bubbles = np.maximum(bubbles, np.maximum(ring, disc * 0.35))
    over(layer, (255, 225, 235), bubbles * liquid * 0.9)

    # --- Glass rim: dark plum outline, bright inner rim ------------------------------------
    outline = np.clip(glass - (depth > px(0.011)).astype(np.float32), 0.0, 1.0)
    inner_rim = np.clip((depth > px(0.011)).astype(np.float32) - (depth > px(0.024)).astype(np.float32), 0, 1)
    over(layer, (225, 242, 255), inner_rim * 0.55)
    over(layer, PLUM, outline)

    # --- Cork with horizontal grain --------------------------------------------------------
    cork = polygon_mask(shape, [(px(0.435), px(0.095)), (px(0.565), px(0.095)),
                                (px(0.552), px(0.235)), (px(0.448), px(0.235))])
    grain = gaussian_filter(rng.uniform(0, 1, size=(S, S // 8)).astype(np.float32), (1.0, 6.0))
    grain = np.asarray(Image.fromarray((grain * 255).astype(np.uint8)).resize((S, S))) / 255.0
    cork_rgb = lerp_color((150, 98, 56), (212, 158, 100), grain * 0.9 + (1 - (yy / S - 0.095) / 0.14) * 0.15)
    cork_depth = inside_depth(cork)
    cork_edge = np.clip(1.0 - cork_depth / px(0.008), 0.0, 1.0)
    over(layer, cork_rgb, cork)
    over(layer, (88, 52, 30), cork * cork_edge)

    # --- Twine wrap on the neck (woven pattern masked to a band) ----------------------------
    weave = procedural_fabric_weave(S, S, thread_density=int(S / 9), roughness=0.5, seed=seed)
    band = polygon_mask(shape, [(px(0.425), px(0.285)), (px(0.575), px(0.285)),
                                (px(0.575), px(0.355)), (px(0.425), px(0.355))]) * (depth > px(0.004))
    twine_rgb = lerp_color((150, 112, 66), (226, 196, 140), weave)
    band_edge = np.clip(1.0 - inside_depth(band) / px(0.006), 0.0, 1.0)
    over(layer, twine_rgb, band)
    over(layer, (84, 58, 30), band * band_edge * 0.8)
    # Hanging tail of the knot
    tail = polygon_mask(shape, [(px(0.48), px(0.35)), (px(0.495), px(0.35)),
                                (px(0.47), px(0.47)), (px(0.458), px(0.47))])
    over(layer, (190, 154, 100), tail)

    # --- Specular: crescent on upper-left, bounce on right, star glint ---------------------
    outer_c = ellipse_mask(shape, cx, cy, R * 0.86, R * 0.86)
    cut_c = ellipse_mask(shape, cx + px(0.03), cy + px(0.03), R * 0.80, R * 0.80)
    crescent = np.clip(outer_c - cut_c, 0, 1) * ((xx < cx - px(0.02)) & (yy < cy + px(0.05)))
    over(layer, (255, 255, 255), gaussian_filter(crescent, 1.2) * 0.85 * glass)
    bounce = np.clip(ellipse_mask(shape, cx, cy, R * 0.90, R * 0.90) - ellipse_mask(shape, cx - px(0.02), cy - px(0.02), R * 0.86, R * 0.86), 0, 1)
    bounce *= ((xx > cx + px(0.10)) & (yy > cy - px(0.02)) & (yy < cy + px(0.14)))
    over(layer, (255, 230, 245), gaussian_filter(bounce, 1.0) * 0.55 * glass)
    gx, gy = cx - px(0.12), cy - px(0.13)
    over(layer, (255, 255, 255), ellipse_mask(shape, gx, gy, px(0.022), px(0.022)) * 0.95)
    over(layer, (255, 255, 255), ellipse_mask(shape, gx, gy, px(0.07), px(0.008)) * 0.55)

    canvas.paste_layer(layer)

    # --- Height dome for normal-map derivation (target resolution) -------------------------
    dome = np.sqrt(np.clip(1.0 - (1.0 - np.clip(depth / R, 0.0, 1.0)) ** 2, 0.0, 1.0))
    dome = np.maximum(dome, cork * 0.5)
    height = np.asarray(Image.fromarray((dome * 255).astype(np.uint8)).resize((size, size), Image.Resampling.LANCZOS)) / 255.0
    return canvas, height.astype(np.float32)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--size", type=int, default=256, help="Icon size in pixels")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    canvas, height_map = draw(size=args.size, seed=args.seed)

    png_file = args.out / f"{ASSET_NAME}.png"
    normal_file = args.out / f"{ASSET_NAME}_normal.png"
    preview_file = args.out / "preview.png"

    canvas.export(png_file)
    canvas.export_dual_preview(preview_file)

    # Derive and export tangent-space normal map
    normal_rgb = heightmap_to_normal_map(height_map, strength=3.0)
    Image.fromarray(normal_rgb).save(normal_file)

    AssetValidator.validate_png(png_file, require_alpha=True)
    AssetValidator.validate_silhouette(png_file, max_components=1, min_fill=0.15, max_fill=0.60)

    manifest = Manifest(
        asset=png_file.name,
        parameters={"size": args.size, "seed": args.seed, "version": "v2_vault"},
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("techniques/art_styles/silhouette_and_proportions.md", "polygon_mask", "ellipse_mask")
    manifest.declare_vault("techniques/art_styles/color_ramps_and_cel_steps.md", "lerp_color")
    manifest.declare_vault("techniques/materials/glass_and_liquid_vessels.md", "inside_depth", "fillet_mask", "over")
    manifest.declare_vault("techniques/materials/fabric_and_weave_patterns.md", "procedural_fabric_weave")
    manifest.declare_vault("mathematics/materials/height_to_normal_sobel.md", "heightmap_to_normal_map")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {png_file}, {normal_file}, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
