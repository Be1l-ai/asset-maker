#!/usr/bin/env python3
"""Procedural 2D icon generator template.

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

ASSET_NAME = "icon"


def draw(size: int = 256, seed: int = 7) -> SpriteCanvas:
    """Agent edits this function to design the 2D asset."""
    canvas = SpriteCanvas(size=size, super_sample=2)
    scale = canvas.scale

    # 1. Outline path (example: shield badge)
    path = aggdraw.Path()
    path.moveto(0.50 * scale, 0.15 * scale)
    path.lineto(0.80 * scale, 0.25 * scale)
    path.curveto(0.80 * scale, 0.65 * scale, 0.55 * scale, 0.85 * scale, 0.50 * scale, 0.90 * scale)
    path.curveto(0.45 * scale, 0.85 * scale, 0.20 * scale, 0.65 * scale, 0.20 * scale, 0.25 * scale)
    path.close()

    # 2. Base fill and stroke
    fill_color = sprite2d.hsv_to_rgb(210.0, 0.70, 0.50) + (240,)
    outline_color = (220, 235, 255, 255)
    canvas.draw_path(path, brush_color=fill_color, pen_color=outline_color, pen_width=scale * 0.025)

    # 3. Interior details
    cx, cy = scale * 0.50, scale * 0.50
    r = scale * 0.12
    canvas.draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                        fill=(255, 215, 80, 230),
                        outline=(255, 255, 255, 255),
                        width=max(1, round(scale * 0.01)))
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

    asset_file = args.out / f"{ASSET_NAME}.png"
    preview_file = args.out / "preview.png"

    canvas.export(asset_file)
    canvas.export_dual_preview(preview_file)

    AssetValidator.validate_png(asset_file, require_alpha=True)

    manifest = Manifest(
        asset=asset_file.name,
        parameters={"size": args.size, "seed": args.seed},
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out).save(args.out)
    print(f"✓ Generated {asset_file} and preview.png (passed validation)")


if __name__ == "__main__":
    main()
