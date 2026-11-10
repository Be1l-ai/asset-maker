#!/usr/bin/env python3
"""Procedural 2D icon generator: Health Potion.

Generates a vector-like glass flask with glowing crimson liquid, cork stopper, and specular highlights.
Usage:
    python generate.py [--size 256] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import aggdraw
import numpy as np
from PIL import Image
from asset_pipeline import AssetValidator, Manifest, SpriteCanvas, sprite2d

ASSET_NAME = "health_potion"


def draw(size: int = 256, seed: int = 7) -> SpriteCanvas:
    """Draws a vector-styled fantasy health potion icon."""
    rng = np.random.default_rng(seed)
    canvas = SpriteCanvas(size=size, super_sample=2)
    s = canvas.scale

    # 1. Cork Stopper
    cork_path = aggdraw.Path()
    cork_path.moveto(0.42 * s, 0.12 * s)
    cork_path.lineto(0.58 * s, 0.12 * s)
    cork_path.lineto(0.55 * s, 0.22 * s)
    cork_path.lineto(0.45 * s, 0.22 * s)
    cork_path.close()
    canvas.draw_path(cork_path, brush_color=(190, 135, 85, 255), pen_color=(125, 80, 45, 255), pen_width=s * 0.015)

    # Cork horizontal grain lines
    canvas.draw.line([(0.43 * s, 0.15 * s), (0.57 * s, 0.15 * s)], fill=(155, 105, 60, 220), width=max(1, round(s * 0.008)))
    canvas.draw.line([(0.44 * s, 0.18 * s), (0.56 * s, 0.18 * s)], fill=(155, 105, 60, 220), width=max(1, round(s * 0.008)))

    # 2. Outer Glass Flask Contour (Spherical Body + Cylindrical Neck + Flared Lip)
    body_cx, body_cy = 0.50 * s, 0.62 * s
    body_r = 0.28 * s

    # Base shadow behind flask
    canvas.draw.ellipse([body_cx - 0.22 * s, 0.88 * s, body_cx + 0.22 * s, 0.94 * s],
                        fill=(0, 0, 0, 70))

    # Glass flask background volume (dark tinted glass)
    canvas.draw.ellipse([body_cx - body_r, body_cy - body_r, body_cx + body_r, body_cy + body_r],
                        fill=(35, 15, 25, 120))
    canvas.draw.rectangle([0.43 * s, 0.22 * s, 0.57 * s, 0.44 * s],
                          fill=(35, 15, 25, 120))

    # 3. Crimson Liquid Filling
    # Bottom circle of liquid
    liq_r = body_r - 0.025 * s
    canvas.draw.ellipse([body_cx - liq_r, body_cy - liq_r, body_cx + liq_r, body_cy + liq_r],
                        fill=(180, 20, 50, 235))
    # Liquid surface meniscus / wave
    liquid_top_y = body_cy - 0.04 * s
    canvas.draw.rectangle([body_cx - liq_r, 0.20 * s, body_cx + liq_r, liquid_top_y],
                          fill=(0, 0, 0, 0))  # Clear top above meniscus

    # Re-draw lower liquid arc with aggdraw path for clean boundary
    liq_path = aggdraw.Path()
    liq_path.moveto(body_cx - liq_r * 0.92, liquid_top_y)
    liq_path.curveto(body_cx - 0.20 * s, liquid_top_y + 0.03 * s,
                     body_cx + 0.20 * s, liquid_top_y - 0.02 * s,
                     body_cx + liq_r * 0.92, liquid_top_y)
    liq_path.curveto(body_cx + liq_r * 1.05, body_cy + liq_r * 0.95,
                     body_cx - liq_r * 1.05, body_cy + liq_r * 0.95,
                     body_cx - liq_r * 0.92, liquid_top_y)
    liq_path.close()
    canvas.draw_path(liq_path, brush_color=(205, 25, 60, 245), pen_color=(235, 50, 85, 220), pen_width=s * 0.01)

    # Inner glowing liquid core
    canvas.draw.ellipse([body_cx - liq_r * 0.65, body_cy - liq_r * 0.35, body_cx + liq_r * 0.65, body_cy + liq_r * 0.70],
                        fill=(245, 60, 95, 190))

    # Bubbles inside potion
    for bx_rel, by_rel, br_rel in [(0.44, 0.68, 0.022), (0.55, 0.74, 0.028), (0.49, 0.58, 0.018), (0.58, 0.63, 0.015)]:
        b_cx = bx_rel * s + rng.uniform(-0.01, 0.01) * s
        b_cy = by_rel * s
        b_r = br_rel * s
        canvas.draw.ellipse([b_cx - b_r, b_cy - b_r, b_cx + b_r, b_cy + b_r],
                            fill=(255, 160, 180, 230),
                            outline=(255, 220, 230, 255),
                            width=max(1, round(s * 0.006)))

    # 4. Glass Outer Silhouette & Rim
    glass_neck = aggdraw.Path()
    # Flared lip
    glass_neck.moveto(0.39 * s, 0.21 * s)
    glass_neck.lineto(0.61 * s, 0.21 * s)
    glass_neck.lineto(0.58 * s, 0.25 * s)
    glass_neck.lineto(0.56 * s, 0.40 * s)
    glass_neck.lineto(0.44 * s, 0.40 * s)
    glass_neck.lineto(0.42 * s, 0.25 * s)
    glass_neck.close()
    canvas.draw_path(glass_neck, brush_color=None, pen_color=(220, 240, 255, 210), pen_width=s * 0.02)

    # Gold neck collar ring
    canvas.draw.rounded_rectangle([0.41 * s, 0.24 * s, 0.59 * s, 0.28 * s],
                                  radius=round(s * 0.015),
                                  fill=(235, 185, 55, 255),
                                  outline=(160, 115, 30, 255),
                                  width=max(1, round(s * 0.008)))

    # Outer glass sphere perimeter stroke
    canvas.draw.ellipse([body_cx - body_r, body_cy - body_r, body_cx + body_r, body_cy + body_r],
                        outline=(220, 240, 255, 220),
                        width=max(1, round(s * 0.022)))

    # 5. Specular Glint & Highlights
    # Curved rim highlight on left flank
    hl_path = aggdraw.Path()
    hl_path.moveto(body_cx - body_r * 0.75, body_cy - body_r * 0.20)
    hl_path.curveto(body_cx - body_r * 0.88, body_cy + body_r * 0.10,
                    body_cx - body_r * 0.70, body_cy + body_r * 0.55,
                    body_cx - body_r * 0.40, body_cy + body_r * 0.75)
    canvas.draw_path(hl_path, brush_color=None, pen_color=(255, 255, 255, 175), pen_width=s * 0.024)

    # Top-left gleam star/circle
    gleam_cx, gleam_cy = body_cx - 0.14 * s, body_cy - 0.14 * s
    canvas.draw.ellipse([gleam_cx - 0.025 * s, gleam_cy - 0.025 * s, gleam_cx + 0.025 * s, gleam_cy + 0.025 * s],
                        fill=(255, 255, 255, 240))
    canvas.draw.ellipse([gleam_cx - 0.05 * s, gleam_cy - 0.01 * s, gleam_cx + 0.05 * s, gleam_cy + 0.01 * s],
                        fill=(255, 255, 255, 130))

    return canvas


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--size", type=int, default=256, help="Icon size in pixels")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    canvas = draw(size=args.size, seed=args.seed)

    png_file = args.out / f"{ASSET_NAME}.png"
    preview_file = args.out / "preview.png"

    canvas.export(png_file)
    canvas.export_dual_preview(preview_file)

    AssetValidator.validate_png(png_file, require_alpha=True)

    manifest = Manifest(
        asset=png_file.name,
        parameters={"size": args.size, "seed": args.seed},
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out).save(args.out)
    print(f"✓ Generated {png_file} and preview.png (passed validation)")


if __name__ == "__main__":
    main()
