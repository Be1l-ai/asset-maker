#!/usr/bin/env python3
"""Procedural VFX flipbook generator: Arcane Burst (V2).

Recreated using Vault techniques:
- Four-stage emitter stack architecture (Flash -> Blast Ring -> Arcane Plume -> Dissipating Sparks)
- Burning-edge alpha erosion dissolve cutoff
- Nonlinear explosive deceleration (Easing.ease_out)
- Pre-rolled particle tables (deterministic across frames) and a real rising plume stage

Usage:
    python generate.py [--frames 16] [--size 128] [--fps 16] [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from asset_pipeline import (
    AssetValidator,
    Easing,
    EmitterStack,
    Flipbook,
    Manifest,
    dissolve_alpha_mask,
    worley_noise,
)

ASSET_NAME = "arcane_burst_v2"


def make_arcane_stack(seed: int = 7) -> EmitterStack:
    """Builds a four-stage composite emitter stack.

    All randomness is drawn ONCE here (particle tables), never inside a layer callback; a
    callback that touches ``rng`` re-rolls every frame and makes the effect jitter.
    """
    rng = np.random.default_rng(seed)
    stack = EmitterStack(size=128)

    # Periodic cellular noise drives the burning-edge dissolve
    noise_cells = worley_noise(width=128, height=128, grid_x=8, grid_y=8, seed=seed, periodic=True)

    # Pre-rolled particle tables (fixed per effect)
    n_sparks = 30
    spark_angle = np.linspace(0, 2 * np.pi, n_sparks, endpoint=False) + rng.uniform(-0.12, 0.12, n_sparks)
    spark_speed = rng.uniform(0.70, 1.35, n_sparks)
    spark_life = rng.uniform(0.75, 1.0, n_sparks)
    spark_violet = (np.arange(n_sparks) % 3) == 0

    n_puffs = 16
    puff_angle = rng.uniform(0, 2 * np.pi, n_puffs)
    puff_r = rng.uniform(0.02, 0.16, n_puffs)          # starting radial offset (fraction of size)
    puff_size = rng.uniform(0.07, 0.15, n_puffs)
    puff_rise = rng.uniform(0.12, 0.30, n_puffs)       # upward travel (fraction of size)
    puff_swirl = rng.uniform(-1.0, 1.0, n_puffs)
    puff_delay = rng.uniform(0.0, 0.18, n_puffs)

    # Stage 1: ignition flash (0 -> 0.35)
    def layer_flash(phase: float, size: int) -> Image.Image | None:
        if phase > 0.35:
            return None
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        t_flash = phase / 0.35
        alpha = int(round(255 * (1.0 - t_flash) ** 0.8))
        cx = cy = size / 2.0
        r_core = (0.20 + 0.10 * np.sin(np.pi * min(1.0, t_flash * 1.2))) * size
        draw.ellipse([cx - r_core * 1.4, cy - r_core * 1.4, cx + r_core * 1.4, cy + r_core * 1.4],
                     fill=(140, 80, 255, int(alpha * 0.5)))
        draw.ellipse([cx - r_core, cy - r_core, cx + r_core, cy + r_core], fill=(80, 220, 255, int(alpha * 0.8)))
        draw.ellipse([cx - r_core * 0.45, cy - r_core * 0.45, cx + r_core * 0.45, cy + r_core * 0.45],
                     fill=(255, 255, 255, alpha))
        return img.filter(ImageFilter.GaussianBlur(size * 0.012))

    # Stage 2: expanding shockwave ring + delayed violet echo
    def layer_shockwave(phase: float, size: int) -> Image.Image | None:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx = cy = size / 2.0
        t = Easing.ease_out(phase)
        r_prim = t * (size * 0.45)
        alpha_prim = int(round(245 * (1.0 - phase ** 1.4)))
        w_prim = max(1, round((1.0 - phase) * size * 0.035))
        if alpha_prim > 0 and r_prim > 2:
            draw.ellipse([cx - r_prim, cy - r_prim, cx + r_prim, cy + r_prim],
                         outline=(100, 230, 255, alpha_prim), width=w_prim)
        if phase > 0.12:
            t_echo = (phase - 0.12) / 0.88
            r_echo = Easing.ease_out(t_echo) * (size * 0.34)
            alpha_echo = int(round(190 * (1.0 - t_echo)))
            if alpha_echo > 0 and r_echo > 2:
                draw.ellipse([cx - r_echo, cy - r_echo, cx + r_echo, cy + r_echo],
                             outline=(190, 110, 255, alpha_echo), width=max(1, round((1.0 - t_echo) * size * 0.02)))
        return img

    # Stage 3: rising arcane plume: soft swirling puffs, noise-eroded as it thins out (0.12 -> 0.85)
    def layer_plume(phase: float, size: int) -> Image.Image | None:
        if phase < 0.12 or phase > 0.90:
            return None
        life = (phase - 0.12) / 0.78
        env = np.sin(np.pi * life) ** 0.8
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for i in range(n_puffs):
            lp = np.clip((life - puff_delay[i]) / (1.0 - puff_delay[i]), 0.0, 1.0)
            ang = puff_angle[i] + puff_swirl[i] * 1.6 * lp
            rr = (puff_r[i] + 0.10 * Easing.ease_out(lp)) * size
            px = size / 2.0 + np.cos(ang) * rr
            py = size / 2.0 + np.sin(ang) * rr * 0.55 - puff_rise[i] * size * Easing.ease_out(lp)
            pr = puff_size[i] * size * (0.6 + 0.9 * lp)
            warm = 1.0 - lp
            col = (int(110 + 120 * warm), int(70 + 150 * warm), int(230 + 25 * warm))
            a = int(210 * env * (1.0 - 0.6 * lp))
            draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=col + (a,))
        img = img.filter(ImageFilter.GaussianBlur(size * 0.022))
        return dissolve_alpha_mask(img, threshold=0.10 + 0.55 * life, noise_map=noise_cells,
                                   edge_width=0.06, edge_color=(150, 245, 255))

    # Stage 4: dissipating sparks (fixed tables) with burning-edge dissolve
    def layer_sparks(phase: float, size: int) -> Image.Image | None:
        if phase < 0.10:
            return None
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx = cy = size / 2.0
        t = Easing.ease_out(phase)
        for i in range(n_sparks):
            p_dist = t * (size * 0.46) * spark_speed[i]
            sag = (phase ** 2) * size * 0.10                      # embers sink as they cool
            px = cx + np.cos(spark_angle[i]) * p_dist
            py = cy + np.sin(spark_angle[i]) * p_dist + sag
            trail = max(0.0, p_dist - size * 0.07 * (1.0 - phase * 0.5))
            tx = cx + np.cos(spark_angle[i]) * trail
            ty = cy + np.sin(spark_angle[i]) * trail + sag * 0.6
            p_life = max(0.0, 1.0 - phase / spark_life[i])
            p_alpha = int(round(255 * p_life ** 1.3))
            if p_alpha > 0 and 0 <= px < size and 0 <= py < size:
                color = (210, 120, 255, p_alpha) if spark_violet[i] else (80, 235, 255, p_alpha)
                draw.line([(tx, ty), (px, py)], fill=color, width=max(1, round(size * 0.016 * p_life)))
                r_tip = max(1.0, p_life * size * 0.022)
                draw.ellipse([px - r_tip, py - r_tip, px + r_tip, py + r_tip], fill=(255, 255, 255, p_alpha))
        if phase > 0.40:
            img = dissolve_alpha_mask(img, threshold=(phase - 0.40) / 0.60 * 0.7, noise_map=noise_cells,
                                      edge_color=(255, 220, 80))
        return img

    for fn in (layer_shockwave, layer_plume, layer_flash, layer_sparks):
        stack.add_layer(fn)
    return stack


def generate_flipbook(frames: int = 16, size: int = 128, fps: int = 16, seed: int = 7) -> Flipbook:
    """Generates the 16-frame arcane burst flipbook using the EmitterStack."""
    stack = make_arcane_stack(seed=seed)
    flipbook = Flipbook(fps=fps)
    for i in range(frames):
        phase = i / max(1, frames)
        frame = stack.composite_frame(phase)
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
    AssetValidator.validate_animation(atlas_file, columns=args.columns, rows=rows)

    manifest = Manifest(
        asset=atlas_file.name,
        parameters={
            "frames": args.frames,
            "size": args.size,
            "columns": args.columns,
            "rows": rows,
            "fps": args.fps,
            "seed": args.seed,
            "version": "v2_vault",
        },
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("techniques/hybrid_vfx/four_stage_emitter_architecture.md", "EmitterStack", "add_layer")
    manifest.declare_vault("techniques/hybrid_vfx/smoke_and_pyroclastic_plumes.md", "Easing", "ease_out", "dissolve_alpha_mask")
    manifest.declare_vault("techniques/hybrid_vfx/dissolve_and_alpha_erosion.md", "dissolve_alpha_mask")
    manifest.declare_vault("mathematics/noise_and_fields/worley_cellular_noise.md", "worley_noise")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {atlas_file}, preview.gif, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
