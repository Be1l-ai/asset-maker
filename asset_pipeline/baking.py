"""Cross-modality procedural baking & optimization helpers (Normal/Roughness maps + 2D/VFX alpha efficiency).

Enforces the silhouette-vs-surface optimization rule:
- Use 3D geometry for silhouette-defining forms (body, limbs, unified paws, hull, wings).
- Use painted albedo maps for color markings (stripes, emblems, seams).
- Use tangent-space normal maps & metallic-roughness maps for micro-relief (fur strands, wood grain, cloth weave).
"""

from __future__ import annotations

import math
import numpy as np
from PIL import Image


def _value_noise(h: int, w: int, scale: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    gh, gw = max(2, h // scale), max(2, w // scale)
    grid = rng.random((gh, gw), dtype=np.float32)
    img = Image.fromarray((grid * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR)
    return np.asarray(img, dtype=np.float32) / 255.0


def height_to_normal_map(height: np.ndarray, strength: float = 2.0) -> Image.Image:
    """Convert a 2D float heightfield [0..1] into a glTF OpenGL tangent-space RGB normal map."""
    h = np.asarray(height, dtype=np.float32)
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * float(strength)
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * float(strength)
    nx = -dx
    ny = -dy
    nz = np.ones_like(h)
    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    rgb = np.stack([
        (nx * inv_len * 0.5 + 0.5) * 255.0,
        (ny * inv_len * 0.5 + 0.5) * 255.0,
        (nz * inv_len * 0.5 + 0.5) * 255.0,
    ], axis=-1)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")


def build_metallic_roughness_map(
    roughness: np.ndarray,
    metallic: np.ndarray | float = 0.0,
) -> Image.Image:
    """Pack glTF 2.0 metallicRoughnessTexture (G = roughness, B = metallic)."""
    r_arr = np.clip(np.asarray(roughness, dtype=np.float32), 0.0, 1.0)
    if isinstance(metallic, (int, float)):
        m_arr = np.full_like(r_arr, float(np.clip(metallic, 0.0, 1.0)))
    else:
        m_arr = np.clip(np.asarray(metallic, dtype=np.float32), 0.0, 1.0)
    rgb = np.stack([
        np.full_like(r_arr, 255.0),
        r_arr * 255.0,
        m_arr * 255.0,
    ], axis=-1)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")


def generate_fur_normal_map(
    size: int = 512,
    direction_deg: float = 90.0,
    strength: float = 1.8,
    seed: int = 42,
) -> Image.Image:
    """Generate an anisotropic directional fur-strand tangent-space normal map (0 extra polygons)."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    rad = math.radians(direction_deg)
    u = x * math.cos(rad) + y * math.sin(rad)
    v = -x * math.sin(rad) + y * math.cos(rad)
    # Stretched anisotropic noise simulating layered fur tufts & fine strands
    n_broad = _value_noise(size, size, 18, seed)
    n_fine = _value_noise(size, size, 5, seed + 13)
    strands = 0.5 + 0.5 * np.sin(v * 0.38 + n_broad * 6.5) * np.cos(u * 0.06 + n_fine * 2.0)
    height = 0.55 * strands + 0.30 * n_broad + 0.15 * n_fine
    return height_to_normal_map(height, strength=strength)


def generate_cloth_normal_map(size: int = 512, weave_scale: float = 1.0, strength: float = 1.4) -> Image.Image:
    """Generate a subtle woven cloth/canvas tangent-space normal map."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    k = 0.85 * float(weave_scale)
    weave = 0.5 + 0.25 * np.sin(x * k) + 0.25 * np.sin(y * k)
    fold = _value_noise(size, size, 32, 99)
    return height_to_normal_map(0.45 * weave + 0.55 * fold, strength=strength)


def generate_wood_grain_normal_map(size: int = 512, plank_h: int = 32, strength: float = 2.2, seed: int = 7) -> Image.Image:
    """Generate a wooden plank + grain fiber tangent-space normal map."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    grain = 0.5 + 0.5 * np.sin(y * 0.28 + _value_noise(size, size, 16, seed) * 6.0)
    seam = ((y % plank_h) < 2.5).astype(np.float32)
    height = np.clip(0.70 * grain + 0.30 * _value_noise(size, size, 6, seed + 5) - 0.65 * seam, 0.0, 1.0)
    return height_to_normal_map(height, strength=strength)


def compute_sprite_alpha_efficiency(img: Image.Image, alpha_threshold: int = 10) -> float:
    """Return fraction of non-transparent pixels in a 2D sprite or VFX frame (overdraw optimization metric)."""
    rgba = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    alpha = rgba[:, :, 3]
    return float(np.mean(alpha > alpha_threshold))
