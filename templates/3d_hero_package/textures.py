"""Procedural PBR texture synthesis (albedo + tangent-space normal maps)."""

from __future__ import annotations

import numpy as np
from PIL import Image


def _height_to_normal(height: np.ndarray, strength: float = 2.0) -> Image.Image:
    gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5 * strength
    nz = np.ones_like(height)
    n = np.stack([-gx, -gy, nz], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rgb = np.clip((n * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def build_stone_textures(size: int = 128, seed: int = 7) -> dict[str, Image.Image]:
    """Generate tileable chiseled-stone albedo and normal map."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size] / float(size)
    # Periodic multi-harmonic stone micro-relief
    h = (
        0.50
        + 0.18 * np.sin(2 * np.pi * (xx * 3.0 + yy * 2.0))
        + 0.12 * np.cos(2 * np.pi * (xx * 5.0 - yy * 4.0))
        + rng.normal(0.0, 0.04, size=(size, size))
    )
    h = np.clip(h, 0.0, 1.0)
    rgb = np.stack([92 + 44 * h, 98 + 42 * h, 108 + 40 * h], axis=-1).clip(0, 255).astype(np.uint8)
    return {"albedo": Image.fromarray(rgb, mode="RGB"), "normal": _height_to_normal(h, strength=2.4)}


def build_wood_textures(size: int = 128, seed: int = 7) -> dict[str, Image.Image]:
    """Generate tileable warm timber grain albedo and normal map."""
    yy, xx = np.mgrid[0:size, 0:size] / float(size)
    warp = 0.06 * np.sin(2 * np.pi * yy * 2.0)
    rings = 0.5 + 0.5 * np.sin(2 * np.pi * ((xx + warp) * 8.0))
    fibers = 0.5 + 0.5 * np.sin(2 * np.pi * (xx * 24.0 + yy * 2.0))
    h = np.clip(0.65 * rings + 0.35 * fibers, 0.0, 1.0)
    rgb = np.stack([110 + 48 * h, 76 + 34 * h, 50 + 24 * h], axis=-1).clip(0, 255).astype(np.uint8)
    return {"albedo": Image.fromarray(rgb, mode="RGB"), "normal": _height_to_normal(h, strength=1.8)}
