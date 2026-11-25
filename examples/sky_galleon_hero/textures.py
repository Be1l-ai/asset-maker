"""512x512 hand-painted procedural PBR textures matching concept.jpg."""

from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw


def _h2n(h: np.ndarray, strength: float = 2.0) -> Image.Image:
    gx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * strength
    n = np.stack([-gx, -gy, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(np.clip((n * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8), mode="RGB")


def build_cedar_plank_textures(size: int = 512) -> dict[str, Image.Image]:
    """Rich dark-cedar hull planking with caulked plank seams, wood grain, and staggered butt joints."""
    yy, xx = np.mgrid[0:size, 0:size] / float(size)
    plank_row = np.floor(yy * 12.0)
    seams = np.clip(np.abs(np.sin(np.pi * yy * 12.0)) ** 0.22, 0.0, 1.0)
    grain = 0.5 + 0.5 * np.sin(2 * np.pi * (xx * 7.0 + 0.04 * np.sin(2 * np.pi * yy * 24.0) + plank_row * 0.37))
    plank_var = 0.86 + 0.14 * np.sin(plank_row * 2.1)
    h = np.clip(seams * (0.65 + 0.35 * grain) * plank_var, 0.0, 1.0)
    rgb = np.stack([112 + 86 * h, 72 + 56 * h, 46 + 34 * h], axis=-1).clip(0, 255).astype(np.uint8)
    return {"albedo": Image.fromarray(rgb, mode="RGB"), "normal": _h2n(h, 2.4)}


def build_sail_textures(size: int = 512, with_emblem: bool = False) -> dict[str, Image.Image]:
    """Crisp bright cream sailcloth with bold magenta racing stripes & optional teal/gold winged compass emblem."""
    yy, xx = np.mgrid[0:size, 0:size] / float(size)
    weave = 0.94 + 0.06 * np.sin(2 * np.pi * xx * 48.0) * np.sin(2 * np.pi * yy * 48.0)
    base = np.stack([252 * weave, 248 * weave, 242 * weave], axis=-1).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(base, mode="RGB")
    draw = ImageDraw.Draw(img)

    # Stitched sailcloth panel seams
    for x in range(size // 5, size, size // 5):
        draw.line([(x, 0), (x, size)], fill=(224, 218, 208), width=2)

    if with_emblem:
        # Bold vertical/flared magenta racing stripes flanking the center + teal/gold winged compass!
        draw.polygon([(int(size * 0.20), 0), (int(size * 0.28), 0), (int(size * 0.18), size), (int(size * 0.08), size)], fill=(196, 46, 134))
        draw.polygon([(int(size * 0.72), 0), (int(size * 0.80), 0), (int(size * 0.92), size), (int(size * 0.82), size)], fill=(196, 46, 134))
        cx, cy = size // 2, int(size * 0.46)
        # Teal stylized wings
        for side in (-1, 1):
            for fi, (ox, oy, w_len) in enumerate([(44, -22, 118), (48, 2, 102), (42, 24, 80)]):
                pts = [
                    (cx + side * ox, cy + oy - 12),
                    (cx + side * (ox + w_len), cy + oy - 34 + fi * 14),
                    (cx + side * (ox + w_len - 18), cy + oy + 8 + fi * 8),
                    (cx + side * ox, cy + oy + 14),
                ]
                draw.polygon(pts, fill=(84, 198, 196), outline=(44, 118, 126), width=3)
        # Golden compass ring & 4-point star
        draw.ellipse([cx - 58, cy - 58, cx + 58, cy + 58], fill=(236, 194, 78), outline=(148, 104, 34), width=5)
        draw.ellipse([cx - 42, cy - 42, cx + 42, cy + 42], fill=(96, 206, 198), outline=(148, 104, 34), width=3)
        star = [
            (cx, cy - 72), (cx + 14, cy - 14), (cx + 68, cy), (cx + 14, cy + 14),
            (cx, cy + 72), (cx - 14, cy + 14), (cx - 68, cy), (cx - 14, cy - 14),
        ]
        draw.polygon(star, fill=(246, 214, 96), outline=(142, 98, 30), width=3)
    else:
        # Twin vertical-curving magenta racing stripes + lower crossband matching concept.jpg
        draw.polygon([(int(size * 0.24), 0), (int(size * 0.34), 0), (int(size * 0.26), size), (int(size * 0.16), size)], fill=(202, 52, 140))
        draw.polygon([(int(size * 0.64), 0), (int(size * 0.74), 0), (int(size * 0.78), size), (int(size * 0.68), size)], fill=(202, 52, 140))
        draw.polygon([(0, int(size * 0.68)), (size, int(size * 0.78)), (size, int(size * 0.87)), (0, int(size * 0.77))], fill=(216, 68, 156))

    return {"albedo": img, "normal": _h2n(weave, 0.8)}
