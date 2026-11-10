#!/usr/bin/env python3
"""Procedural VFX flipbook generator: Arcane Burst.

Generates a 16-frame magical radial burst with expanding shockwaves, core flash, and particle sparks.
Usage:
    python generate.py [--frames 16] [--size 128] [--fps 16] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image, ImageDraw
from asset_pipeline import AssetValidator, Easing, Flipbook, Manifest

ASSET_NAME = "arcane_burst"


def render_arcane_frame(phase: float, size: int = 128, seed: int = 7) -> Image.Image:
    """Renders a single frame of the arcane burst at normalized phase [0..1)."""
    rng = np.random.default_rng(seed)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    t = float(np.clip(phase, 0.0, 1.0))
    cx, cy = size / 2.0, size / 2.0

    # 1. Central Energy Flash (peaks early at t ~ 0.05..0.20, then fades)
    flash_t = np.clip(t / 0.35, 0.0, 1.0)
    flash_alpha = int(round(255 * (1.0 - flash_t)))
    flash_r = (0.25 - 0.15 * flash_t) * size
    if flash_alpha > 0 and flash_r > 1:
        # Outer cyan glow
        draw.ellipse([cx - flash_r, cy - flash_r, cx + flash_r, cy + flash_r],
                     fill=(80, 210, 255, int(flash_alpha * 0.7)))
        # Inner white-hot core
        core_r = flash_r * 0.5
        draw.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r],
                     fill=(240, 250, 255, flash_alpha))

    # 2. Primary Expanding Shockwave Ring
    ring_t = Easing.ease_out(t)
    ring_r = ring_t * (size * 0.44)
    ring_alpha = int(round(240 * (1.0 - t**1.3)))
    ring_width = max(1, round((1.0 - t) * size * 0.035))
    if ring_alpha > 0 and ring_r > 2:
        draw.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                     outline=(100, 225, 255, ring_alpha),
                     width=ring_width)

    # 3. Secondary Inner Echo Ring (delayed expansion)
    if t > 0.12:
        echo_t = (t - 0.12) / 0.88
        echo_r = Easing.ease_out(echo_t) * (size * 0.32)
        echo_alpha = int(round(180 * (1.0 - echo_t)))
        if echo_alpha > 0 and echo_r > 2:
            draw.ellipse([cx - echo_r, cy - echo_r, cx + echo_r, cy + echo_r],
                         outline=(180, 120, 255, echo_alpha),
                         width=max(1, round((1.0 - echo_t) * size * 0.02)))

    # 4. Radiating Arcane Sparks & Streaks (24 particles)
    particle_count = 24
    for i in range(particle_count):
        base_angle = (2.0 * np.pi / particle_count) * i
        jitter_angle = base_angle + rng.uniform(-0.15, 0.15)
        speed = rng.uniform(0.65, 1.40)
        p_dist = Easing.ease_out(t) * (size * 0.46) * speed
        
        # Particle positions
        px = cx + np.cos(jitter_angle) * p_dist
        py = cy + np.sin(jitter_angle) * p_dist

        # Trail start position (slightly behind particle)
        trail_dist = max(0.0, p_dist - (size * 0.06 * (1.0 - t * 0.5)))
        tx = cx + np.cos(jitter_angle) * trail_dist
        ty = cy + np.sin(jitter_angle) * trail_dist

        p_life = max(0.0, 1.0 - t * rng.uniform(0.85, 1.15))
        p_alpha = int(round(255 * (p_life ** 1.5)))

        if p_alpha > 0 and (0 <= px < size) and (0 <= py < size):
            # Choose between electric cyan and arcane violet
            if i % 3 == 0:
                p_color = (200, 130, 255, p_alpha)
            else:
                p_color = (90, 235, 255, p_alpha)

            # Spark trail line
            draw.line([(tx, ty), (px, py)], fill=p_color, width=max(1, round(size * 0.015 * p_life)))
            # Spark tip
            p_radius = max(1.0, p_life * size * 0.022)
            draw.ellipse([px - p_radius, py - p_radius, px + p_radius, py + p_radius],
                         fill=(255, 255, 255, p_alpha))

    # Clean 1-pixel transparent boundary gutter
    draw.rectangle([0, 0, size - 1, size - 1], outline=(0, 0, 0, 0))
    return img


def generate_flipbook(frames: int = 16, size: int = 128, fps: int = 16, seed: int = 7) -> Flipbook:
    """Generates the 16-frame arcane burst flipbook."""
    flipbook = Flipbook(fps=fps)
    for i in range(frames):
        phase = i / max(1, frames)
        frame = render_arcane_frame(phase=phase, size=size, seed=seed)
        flipbook.add_frame(frame)
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

    manifest = Manifest(
        asset=atlas_file.name,
        parameters={
            "frames": args.frames,
            "size": args.size,
            "columns": args.columns,
            "rows": rows,
            "fps": args.fps,
            "seed": args.seed,
        },
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out).save(args.out)
    print(f"✓ Generated {atlas_file}, preview.gif, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
