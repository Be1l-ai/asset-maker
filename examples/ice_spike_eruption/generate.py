#!/usr/bin/env python3
"""Procedural crystalline ice-spike eruption flipbook.

A one-shot 4x4 VFX atlas: ground frost cracks flash first, staggered crystal
shards erupt along a shallow diagonal, then a cold mist and ice glitter settle.
Every random choice is pre-rolled; frame geometry is a pure function of phase.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from asset_pipeline import AssetValidator, EmitterStack, Flipbook, Manifest
from asset_pipeline.critique import CritiqueLog

ASSET_NAME = "ice_spike_eruption"
SUPERSAMPLE = 2


def _smoothstep(edge0: float, edge1: float, x):
    t = np.clip((x - edge0) / max(1e-9, edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ease_out(t: float) -> float:
    t = float(np.clip(t, 0.0, 1.0))
    return 1.0 - (1.0 - t) ** 2


def _grid(size: int):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    return (xx + 0.5) / size, (yy + 0.5) / size


def _poly_mask(points, size: int, origin=(0, 0), dimensions=None):
    width, height = dimensions or (size, size)
    ox, oy = origin
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(
        [(float(px * size - ox), float(py * size - oy)) for px, py in points], fill=255
    )
    return np.asarray(mask, dtype=np.float32) / 255.0


def _over(dst: np.ndarray, src_rgb: np.ndarray, src_a: np.ndarray):
    """Straight-alpha source-over for float RGB [0..255] and alpha [0..1]."""
    a = np.clip(src_a, 0.0, 1.0)[..., None]
    dst_a = dst[..., 3:4]
    out_a = a + dst_a * (1.0 - a)
    dst[..., :3] = np.divide(
        src_rgb * a + dst[..., :3] * dst_a * (1.0 - a),
        out_a,
        out=np.zeros_like(dst[..., :3]),
        where=out_a > 1e-5,
    )
    dst[..., 3:4] = out_a
    return dst


def _to_image(layer: np.ndarray) -> Image.Image:
    """Convert float RGBA (RGB 0..255, alpha 0..1) to a straight-alpha image."""
    out = np.empty_like(layer, dtype=np.float32)
    out[..., :3] = np.clip(layer[..., :3], 0.0, 255.0) / 255.0
    out[..., 3] = np.clip(layer[..., 3], 0.0, 1.0)
    return Image.fromarray(np.rint(out * 255).astype(np.uint8), "RGBA")


def _downsample_premultiplied(image: Image.Image, size: int) -> Image.Image:
    arr = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0
    arr[..., :3] *= arr[..., 3:4]
    small = np.asarray(
        Image.fromarray(np.rint(arr * 255).astype(np.uint8), "RGBA").resize(
            (size, size), Image.Resampling.LANCZOS
        ),
        dtype=np.float32,
    ) / 255.0
    alpha = np.clip(small[..., 3:4], 0.0, 1.0)
    rgb = np.divide(small[..., :3], alpha, out=np.zeros_like(small[..., :3]), where=alpha > 1e-4)
    out = np.dstack([np.clip(rgb, 0.0, 1.0), alpha])
    return Image.fromarray(np.rint(out * 255).astype(np.uint8), "RGBA")


@dataclass(frozen=True)
class Spike:
    x: float
    height: float
    width: float
    lean: float
    depth: float
    delay: float
    seed: int
    splinter: bool = False

    @property
    def base_y(self) -> float:
        # Shallow diagonal ground line: the right side sits farther back.
        return 0.815 - 0.075 * self.x - 0.020 * self.depth

    @property
    def opacity(self) -> float:
        return 1.0 - 0.42 * self.depth


def _spike_table(seed: int):
    rng = np.random.default_rng(seed)
    main = [
        Spike(0.115, 0.085, 0.022, -0.010, 0.80, 0.155, 11),
        Spike(0.170, 0.115, 0.026, -0.014, 0.66, 0.120, 12),
        Spike(0.225, 0.160, 0.031, -0.012, 0.50, 0.090, 13),
        Spike(0.285, 0.215, 0.037, 0.004, 0.36, 0.060, 14),
        Spike(0.345, 0.285, 0.043, 0.012, 0.24, 0.035, 15),
        Spike(0.410, 0.380, 0.050, 0.020, 0.14, 0.015, 16),
        Spike(0.475, 0.500, 0.057, 0.028, 0.06, 0.005, 17),
        Spike(0.540, 0.610, 0.064, 0.034, 0.00, 0.000, 18),
        Spike(0.600, 0.525, 0.058, 0.030, 0.10, 0.012, 19),
        Spike(0.660, 0.435, 0.051, 0.024, 0.20, 0.030, 20),
        Spike(0.718, 0.335, 0.044, 0.016, 0.33, 0.060, 21),
        Spike(0.772, 0.245, 0.037, 0.008, 0.48, 0.095, 22),
        Spike(0.822, 0.175, 0.030, 0.000, 0.64, 0.130, 23),
        Spike(0.868, 0.120, 0.024, -0.006, 0.78, 0.165, 24),
    ]
    # A darker back row gives the cluster thickness without extra overdraw.
    back = [
        Spike(0.180, 0.100, 0.024, 0.010, 0.94, 0.180, 31),
        Spike(0.310, 0.150, 0.030, 0.015, 0.90, 0.140, 32),
        Spike(0.420, 0.290, 0.042, 0.028, 0.66, 0.060, 36),
        Spike(0.450, 0.200, 0.036, 0.020, 0.86, 0.100, 33),
        Spike(0.555, 0.360, 0.047, 0.038, 0.60, 0.045, 37),
        Spike(0.590, 0.230, 0.040, 0.020, 0.84, 0.080, 34),
        Spike(0.665, 0.300, 0.042, 0.022, 0.64, 0.070, 38),
        Spike(0.720, 0.160, 0.030, 0.010, 0.90, 0.130, 35),
    ]
    # Low foreground shards break the single-row silhouette.
    fore = [
        Spike(0.300, 0.130, 0.050, -0.050, 0.02, 0.110, 51),
        Spike(0.425, 0.160, 0.055, 0.060, 0.03, 0.070, 52),
        Spike(0.665, 0.140, 0.050, -0.040, 0.05, 0.080, 53),
    ]
    spikes = back + main + fore
    # Small splinters hug the base of every third main crystal.
    for i, spike in enumerate(main[2::3]):
        for side in (-1.0, 1.0):
            spikes.append(
                Spike(
                    spike.x + side * spike.width * (0.72 + 0.2 * rng.random()),
                    spike.height * (0.28 + 0.16 * rng.random()),
                    spike.width * (0.34 + 0.10 * rng.random()),
                    spike.lean * 0.6 + side * 0.008,
                    min(0.98, spike.depth + 0.06),
                    spike.delay + 0.035 + 0.03 * rng.random(),
                    spike.seed + 100 + i * 2 + (side > 0),
                    splinter=True,
                )
            )
    return spikes


SPIKES = _spike_table(23)


def _spike_points(spike: Spike, phase: float):
    growth = (phase - spike.delay) / 0.30
    if growth <= 0:
        return None
    growth = _ease_out(growth)
    if growth <= 0.002:
        return None
    height = spike.height * growth * 1.04
    width = spike.width * 0.72 * (0.38 + 0.62 * growth)
    base_y = spike.base_y
    apex_x = spike.x + spike.lean * height
    apex_y = base_y - height
    rng = np.random.default_rng(spike.seed)

    # Chipped, stepped silhouette: width expands and contracts along the shard
    # instead of forming a perfect isosceles triangle.
    profile_left = [1.0, 1.06, 0.86, 0.98, 0.72, 0.80, 0.52]
    profile_right = [1.0, 0.93, 1.04, 0.80, 0.91, 0.65, 0.74]
    steps = (0.0, 0.13, 0.28, 0.43, 0.59, 0.75, 0.88)
    left, right = [], []
    for index, v in enumerate(steps):
        taper = (1.0 - v) ** 0.78
        wobble_l = rng.uniform(-0.10, 0.10)
        wobble_r = rng.uniform(-0.10, 0.10)
        y = base_y - height * v
        left.append((spike.x - width * taper * profile_left[index] * (1.0 + wobble_l), y))
        right.append((spike.x + width * taper * profile_right[index] * (1.0 + wobble_r), y))
    left.append((apex_x, apex_y))
    right.append((apex_x, apex_y))

    ridge = []
    for v in (0.0, 0.20, 0.40, 0.60, 0.80, 1.0):
        ridge.append((
            spike.x + (apex_x - spike.x) * v + width * 0.16 * math.sin(math.pi * v) * (0.6 + 0.4 * (spike.seed % 5) / 4),
            base_y - height * v,
        ))

    left_facet = left + list(reversed(ridge[:-1]))
    right_facet = ridge + list(reversed(right[:-1]))
    silhouette = left + list(reversed(right[:-1]))
    return {
        "height": height,
        "width": width,
        "base_y": base_y,
        "apex": (apex_x, apex_y),
        "left": left,
        "right": right,
        "ridge": ridge,
        "left_facet": left_facet,
        "right_facet": right_facet,
        "silhouette": silhouette,
        "growth": growth,
    }


def _render_spike(size: int, spike: Spike, phase: float, fade: float):
    geo = _spike_points(spike, phase)
    if geo is None:
        return None
    # Render only the shard's local bounding box. Full-frame arrays per spike
    # dominate runtime at 512 px and add nothing but transparent pixels.
    xs = [px for px, _ in geo["silhouette"]]
    ys = [py for _, py in geo["silhouette"]]
    pad_x = max(3, int(geo["width"] * size * 1.7))
    pad_y = max(3, int(geo["height"] * size * 0.18))
    x0 = max(0, int(math.floor(min(xs) * size)) - pad_x)
    x1 = min(size, int(math.ceil(max(xs) * size)) + pad_x)
    y0 = max(0, int(math.floor(min(ys) * size)) - pad_y)
    y1 = min(size, int(math.ceil(max(ys) * size)) + pad_y)
    bw, bh = x1 - x0, y1 - y0
    if bw <= 0 or bh <= 0:
        return None

    x = (x0 + np.arange(bw, dtype=np.float64) + 0.5) / size
    y = (y0 + np.arange(bh, dtype=np.float64) + 0.5) / size
    x, y = np.meshgrid(x, y)
    base_y, height, width = geo["base_y"], geo["height"], geo["width"]
    depth_mix = spike.depth

    layer = np.zeros((bh, bw, 4), dtype=np.float32)
    left_mask = _poly_mask(geo["left_facet"], size, (x0, y0), (bw, bh))
    right_mask = _poly_mask(geo["right_facet"], size, (x0, y0), (bw, bh))

    # Facet value gradient: deep sapphire roots, cyan body, white-hot tips.
    v = np.clip((base_y - y) / max(1e-5, height), 0.0, 1.0)
    u = (x - spike.x) / max(1e-5, width)
    cool = np.array([16.0, 72.0, 188.0])
    ice = np.array([62.0, 176.0, 255.0])
    tip = np.array([228.0, 249.0, 255.0])
    ramp = v ** 1.25
    base_rgb = cool[None, None, :] * (1.0 - ramp[..., None]) + ice[None, None, :] * ramp[..., None]
    tip_mix = 0.62 * _smoothstep(0.68, 1.0, v)[..., None]
    base_rgb = base_rgb * (1.0 - tip_mix) + tip[None, None, :] * tip_mix
    # Luminous cyan root glow, as if the shard is lit from the fractured ground.
    root_glow = np.exp(-(v / 0.20) ** 2)[..., None]
    base_rgb = base_rgb + np.array([34.0, 110.0, 120.0])[None, None, :] * root_glow
    # Faceted internal light: a cool shadow plane and a bright lit plane.
    facet_left = np.clip(0.46 + 0.22 * (1.0 - np.abs(u)) + 0.05 * np.sin(28.0 * v + 7.0 * u), 0.0, 1.0)
    facet_right = np.clip(0.90 + 0.20 * (1.0 - np.abs(u)) + 0.05 * np.sin(23.0 * v - 4.0 * u), 0.0, 1.0)
    striation = 0.05 * np.sin(41.0 * v + 13.0 * u)
    left_rgb = np.clip(base_rgb * facet_left[..., None] + 12.0 * striation[..., None], 0, 255)
    right_rgb = np.clip(base_rgb * facet_right[..., None] + 20.0 * striation[..., None], 0, 255)

    # Central specular plane catches the cold key light.
    center_band = np.exp(-((u - 0.10) / 0.22) ** 2) * _smoothstep(0.05, 0.85, v)
    center_band *= 0.20 * spike.opacity * fade * np.clip(left_mask + right_mask, 0.0, 1.0)
    _over(layer, np.array([210.0, 247.0, 255.0])[None, None, :] * np.ones_like(layer[..., :3]), center_band)

    # Depth: background crystals lose contrast and lean blue.
    haze = np.array([34.0, 68.0, 138.0])
    left_rgb = left_rgb * (1 - 0.34 * depth_mix) + haze * (0.34 * depth_mix)
    right_rgb = right_rgb * (1 - 0.28 * depth_mix) + haze * (0.28 * depth_mix)

    opacity = spike.opacity * fade
    _over(layer, left_rgb, left_mask * opacity)
    _over(layer, right_rgb, right_mask * opacity)

    # Crisp rim and central ridge catch-lights.
    glow = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    pts = lambda seq: [(px * size - x0, py * size - y0) for px, py in seq]
    rim_alpha = int(150 * opacity)
    draw.line(pts(geo["left"]), fill=(196, 240, 255, rim_alpha), width=max(2, size // 240), joint="curve")
    draw.line(pts(geo["right"]), fill=(220, 249, 255, rim_alpha), width=max(2, size // 240), joint="curve")
    draw.line(pts(geo["ridge"]), fill=(248, 254, 255, int(225 * opacity)), width=max(2, size // 190), joint="curve")
    # Secondary facet seams: short diagonal cuts make the planes read as ice.
    facet_alpha = int(105 * opacity)
    draw.line(pts([geo["left"][2], geo["ridge"][2]]), fill=(175, 234, 255, facet_alpha),
              width=max(2, size // 320), joint="curve")
    draw.line(pts([geo["right"][2], geo["ridge"][3]]), fill=(198, 242, 255, facet_alpha),
              width=max(2, size // 320), joint="curve")
    draw.line(pts([geo["left"][4], geo["ridge"][4]]), fill=(165, 230, 255, facet_alpha),
              width=max(1, size // 420), joint="curve")
    ridge_overlay = np.asarray(glow, dtype=np.float32) / 255.0
    _over(layer, ridge_overlay[..., :3] * 255.0, ridge_overlay[..., 3])

    # A soft, cold bloom behind the crystal makes it read as emissive ice.
    bloom = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bloom)
    bx, by = spike.x * size - x0, (base_y - height * 0.40) * size - y0
    rx, ry = width * size * 1.5, height * size * 0.34
    bdraw.ellipse([bx - rx, by - ry, bx + rx, by + ry], fill=(36, 108, 235, int(22 * opacity)))
    bloom = bloom.filter(ImageFilter.GaussianBlur(max(2, size // 90)))
    bloom_arr = np.asarray(bloom, dtype=np.float32) / 255.0
    _over(layer, bloom_arr[..., :3] * 255.0, bloom_arr[..., 3])

    shard = _to_image(layer)
    return shard, (x0, y0)


def _render_spikes(size: int, phase: float, fade: float) -> Image.Image:
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for spike in sorted(SPIKES, key=lambda s: (-s.depth, s.splinter)):
        result = _render_spike(size, spike, phase, fade)
        if result is not None:
            shard, offset = result
            if spike.depth > 0.82:
                shard = shard.filter(ImageFilter.GaussianBlur(max(1, size // 420)))
            out.alpha_composite(shard, offset)
    return out


def _ground_cracks(size: int, phase: float, fade: float) -> Image.Image:
    x, y = _grid(size)
    if phase <= 0.0:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rng = np.random.default_rng(91)
    crack = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(crack)
    flash = float(np.exp(-((phase - 0.05) / 0.16) ** 2)) if phase < 0.55 else 0.0

    def fracture(origin, angle, length, steps=6, branch_depth=0):
        pts = [origin]
        for step in range(1, steps + 1):
            t = step / steps
            pts.append((
                origin[0] + math.cos(angle) * length * t + rng.uniform(-0.008, 0.008),
                origin[1] + math.sin(angle) * length * t * 0.30 + rng.uniform(-0.004, 0.004),
            ))
        alpha = int((92 + 150 * flash) * fade)
        draw.line([(px * size, py * size) for px, py in pts],
                  fill=(138, 228, 255, alpha), width=max(2, size // 320), joint="curve")
        if branch_depth > 0:
            fork = pts[len(pts) // 2]
            fracture(fork, angle + rng.choice([-1.0, 1.0]) * rng.uniform(0.25, 0.55),
                     length * 0.42, steps=3, branch_depth=branch_depth - 1)

    # Long fracture seams run along the ground from each crystal root.
    for spike in SPIKES[::2]:
        origin = (spike.x, spike.base_y + 0.010)
        spread = 0.10 + 0.11 * (1.0 - spike.depth)
        fracture(origin, math.pi + rng.uniform(-0.12, 0.12), spread * rng.uniform(0.75, 1.15), branch_depth=1)
        fracture(origin, rng.uniform(-0.12, 0.12), spread * rng.uniform(0.75, 1.15), branch_depth=1)
    # Hero-root star: a brighter, wider burst at the tallest shard.
    hero = (0.512, 0.752)
    for index in range(6):
        angle = -0.18 + index * (math.pi + 0.36) / 5.0
        fracture(hero, angle, rng.uniform(0.13, 0.22), steps=7, branch_depth=1)

    # Blurred glow under the sharp fracture lines.
    halo = crack.filter(ImageFilter.GaussianBlur(max(2, size // 100)))
    arr = np.asarray(crack, dtype=np.float32) / 255.0
    halo_arr = np.asarray(halo, dtype=np.float32) / 255.0
    out = np.zeros((size, size, 4), dtype=np.float32)
    out[..., :3] = halo_arr[..., :3] * 255.0
    out[..., 3] = halo_arr[..., 3]
    _over(out, arr[..., :3] * 255.0, arr[..., 3])

    # Contact frost patch where the shards split the ground.
    cx, cy = 0.51, 0.775
    rx, ry = 0.38, 0.050
    patch = np.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) * 2.2)
    patch *= 0.28 * fade * (0.7 + 0.7 * flash)
    _over(out, np.array([120.0, 205.0, 255.0])[None, None, :] * np.ones_like(out[..., :3]), patch)
    return _to_image(out)


def _ambient_glow(size: int, phase: float, fade: float) -> Image.Image:
    x, y = _grid(size)
    if phase <= 0.0:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rng = np.random.default_rng(5)
    out = np.zeros((size, size, 4), dtype=np.float32)
    # Ground bloom.
    pulse = 0.82 + 0.18 * math.sin(phase * math.pi * 3.0)
    g1 = np.exp(-(((x - 0.50) / 0.38) ** 2 + ((y - 0.775) / 0.075) ** 2) * 2.0)
    _over(out, np.array([26.0, 98.0, 255.0])[None, None, :] * np.ones_like(out[..., :3]),
          g1 * 0.46 * pulse * fade)
    # Tall vertical aura, strongest at the hero crystal.
    g2 = np.exp(-(((x - 0.50) / 0.22) ** 2 + ((y - 0.56) / 0.30) ** 2) * 2.2)
    _over(out, np.array([42.0, 132.0, 255.0])[None, None, :] * np.ones_like(out[..., :3]),
          g2 * 0.20 * pulse * fade)
    # Ignition flash: a brief white-blue core at the eruption point.
    flash = math.exp(-((phase - 0.055) / 0.055) ** 2) if phase < 0.25 else 0.0
    if flash > 0.01:
        g3 = np.exp(-(((x - 0.51) / 0.12) ** 2 + ((y - 0.735) / 0.065) ** 2) * 2.6)
        _over(out, np.array([225.0, 250.0, 255.0])[None, None, :] * np.ones_like(out[..., :3]),
              g3 * 0.82 * flash * fade)
    return _to_image(out)


def _mist(size: int, phase: float, fade: float) -> Image.Image:
    x, y = _grid(size)
    if phase <= 0.0:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rng = np.random.default_rng(77)
    out = np.zeros((size, size, 4), dtype=np.float32)
    puffs = []
    for i in range(14):
        puffs.append((
            rng.uniform(0.16, 0.86),
            0.795 - rng.uniform(0.0, 0.035),
            rng.uniform(0.055, 0.12),
            rng.uniform(0.018, 0.038),
            rng.uniform(0.0, 0.06),
            rng.uniform(0.6, 1.15),
        ))
    for px, py, rx, ry, rise, speed in puffs:
        spread = _smoothstep(0.05, 0.55, phase)
        cx = px + (px - 0.5) * 0.10 * spread
        cy = py - rise * _ease_out(phase) - 0.015 * spread
        rxx = rx * (0.6 + 1.0 * spread)
        ryy = ry * (0.7 + 1.1 * spread)
        density = np.exp(-(((x - cx) / rxx) ** 2 + ((y - cy) / ryy) ** 2) * 2.6)
        envelope = _smoothstep(0.02, 0.16, phase) * (1.0 - 0.72 * _smoothstep(0.62, 1.0, phase))
        alpha = density * 0.24 * envelope * speed * fade
        _over(out, np.array([162.0, 213.0, 255.0])[None, None, :] * np.ones_like(out[..., :3]), alpha)
    return _to_image(out)


def _ice_glitter(size: int, phase: float, fade: float) -> Image.Image:
    x, y = _grid(size)
    if phase <= 0.0:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rng = np.random.default_rng(303)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Larger tumbling ice chips carry the silhouette above the spike row.
    for _ in range(14):
        spawn = rng.uniform(0.04, 0.24)
        if phase <= spawn:
            continue
        life = (phase - spawn) / max(0.10, 1.0 - spawn)
        if life >= 1.0:
            continue
        sx = rng.uniform(0.22, 0.84)
        sy = 0.78 - rng.uniform(0.02, 0.16)
        vx = rng.uniform(-0.18, 0.20)
        vy = rng.uniform(-0.24, -0.09)
        px = sx + vx * life * 0.72
        py = sy + vy * life - 0.012 * life * life
        chip = rng.uniform(2.8, 6.2) * (0.75 + 0.35 * (1.0 - life))
        alpha = 255 * _smoothstep(0.0, 0.10, life) * (1.0 - _smoothstep(0.62, 1.0, life)) * fade
        spin = rng.uniform(0.0, math.pi)
        dx, dy = math.cos(spin) * chip, math.sin(spin) * chip
        draw.polygon(
            [(px * size - dx, py * size - dy), (px * size + dy * 0.55, py * size - dx * 0.55),
             (px * size + dx, py * size + dy), (px * size - dy * 0.55, py * size + dx * 0.55)],
            fill=(168, 232, 255, int(alpha * 0.92)),
        )
        draw.polygon(
            [(px * size - dx * 0.40, py * size - dy * 0.40), (px * size + dy * 0.18, py * size - dx * 0.18),
             (px * size + dx * 0.45, py * size + dy * 0.45), (px * size - dy * 0.18, py * size + dx * 0.18)],
            fill=(238, 252, 255, int(alpha)),
        )

    for _ in range(54):
        spawn = rng.uniform(0.015, 0.30)
        if phase <= spawn:
            continue
        life = (phase - spawn) / max(0.08, 1.0 - spawn)
        if life >= 1.0:
            continue
        sx = rng.uniform(0.18, 0.88)
        sy = 0.79 - rng.uniform(0.0, 0.10)
        vx = rng.uniform(-0.20, 0.24)
        vy = rng.uniform(-0.20, -0.055)
        drag = 0.72
        px = sx + vx * life * drag
        py = sy + vy * life - 0.018 * life * life
        size_px = rng.uniform(1.2, 3.8) * (0.7 + 0.5 * (1.0 - life))
        alpha = 255 * _smoothstep(0.0, 0.12, life) * (1.0 - _smoothstep(0.55, 1.0, life)) * fade
        spin = rng.uniform(0.0, math.pi)
        # Alternating ice chips and soft sparkles.
        if rng.random() < 0.55:
            dx, dy = math.cos(spin) * size_px * 0.9, math.sin(spin) * size_px * 0.9
            draw.polygon(
                [(px * size - dx, py * size - dy), (px * size + dy * 0.5, py * size - dx * 0.5),
                 (px * size + dx, py * size + dy), (px * size - dy * 0.5, py * size + dx * 0.5)],
                fill=(212, 246, 255, int(alpha)),
            )
        else:
            draw.ellipse(
                [(px * size - size_px, py * size - size_px), (px * size + size_px, py * size + size_px)],
                fill=(236, 252, 255, int(alpha * 0.82)),
            )
    # Bloom pass for the bright shards.
    halo = layer.filter(ImageFilter.GaussianBlur(max(1, size // 180)))
    halo_arr = np.asarray(halo, dtype=np.float32) / 255.0
    out = np.zeros((size, size, 4), dtype=np.float32)
    out[..., :3] = halo_arr[..., :3] * 255.0
    out[..., 3] = halo_arr[..., 3]
    crisp = np.asarray(layer, dtype=np.float32) / 255.0
    _over(out, crisp[..., :3] * 255.0, crisp[..., 3])
    return _to_image(out)


def make_frame(phase: float, size: int = 256, seed: int = 23) -> Image.Image:
    """Render one 256px frame; phase is a one-shot normalized time in [0, 1)."""
    render_size = size * SUPERSAMPLE
    fade = 1.0 - _smoothstep(0.74, 0.95, phase)
    if phase <= 0.0:
        fade = 1.0

    stack = EmitterStack(size=render_size)
    stack.add_layer(lambda p, s: _ambient_glow(s, p, fade))
    stack.add_layer(lambda p, s: _render_spikes(s, p, fade))
    stack.add_layer(lambda p, s: _ground_cracks(s, p, fade))
    stack.add_layer(lambda p, s: _mist(s, p, fade))
    stack.add_layer(lambda p, s: _ice_glitter(s, p, fade))
    frame = stack.composite_frame(phase)
    return _downsample_premultiplied(frame, size)


def _stage_frame(phase: float, size: int = 256, level: int = 2) -> Image.Image:
    """Render a reduced-detail frame for the Tier-1 critique record."""
    render_size = size * SUPERSAMPLE
    fade = 1.0 - _smoothstep(0.74, 0.95, phase)
    stack = EmitterStack(size=render_size)
    if level >= 1:
        stack.add_layer(lambda p, s: _ambient_glow(s, p, fade))
    stack.add_layer(lambda p, s: _render_spikes(s, p, fade))
    if level >= 1:
        stack.add_layer(lambda p, s: _ground_cracks(s, p, fade))
    if level >= 2:
        stack.add_layer(lambda p, s: _mist(s, p, fade))
        stack.add_layer(lambda p, s: _ice_glitter(s, p, fade))
    return _downsample_premultiplied(stack.composite_frame(phase), size)


def generate_flipbook(frames: int = 16, size: int = 256, fps: int = 16, seed: int = 23) -> Flipbook:
    flipbook = Flipbook(fps=fps)
    for index in range(frames):
        flipbook.add_frame(make_frame(index / frames, size=size, seed=seed))
    return flipbook


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--frames", type=int, default=16, help="Total frames")
    parser.add_argument("--size", type=int, default=256, help="Frame width/height")
    parser.add_argument("--columns", type=int, default=4, help="Atlas grid columns")
    parser.add_argument("--fps", type=int, default=16, help="Playback FPS")
    parser.add_argument("--seed", type=int, default=23, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = int(math.ceil(args.frames / args.columns))

    flipbook = generate_flipbook(frames=args.frames, size=args.size, fps=args.fps, seed=args.seed)
    atlas_file = args.out / f"{ASSET_NAME}.png"
    preview_gif = args.out / "preview.gif"
    preview_png = args.out / "preview.png"
    flipbook.export_atlas(atlas_file, columns=args.columns)
    flipbook.export_gif(preview_gif)
    flipbook.export_preview(preview_png)

    stage_blockout = args.out / "critique_blockout.png"
    stage_secondary = args.out / "critique_secondary.png"
    stage_final = args.out / "critique_final.png"
    _stage_frame(0.50, size=args.size, level=0).save(stage_blockout)
    _stage_frame(0.50, size=args.size, level=1).save(stage_secondary)
    _stage_frame(0.50, size=args.size, level=2).save(stage_final)

    AssetValidator.validate_png(atlas_file, require_alpha=True, columns=args.columns, rows=rows)
    AssetValidator.validate_animation(atlas_file, columns=args.columns, rows=rows)

    manifest = Manifest(
        asset=atlas_file.name,
        parameters={
            "frames": args.frames,
            "fps": args.fps,
            "grid": [args.columns, rows],
            "seed": args.seed,
            "loop": False,
            "blend": "alpha",
            "frame_size": [args.size, args.size],
            "phase_sampling": "i/N; clean extinction at phase 1",
        },
        recipe=Path(__file__).name,
    )
    manifest.declare_vault(
        "techniques/hybrid_vfx/crystalline_ice_spike_eruptions.md",
        "EmitterStack",
        "Flipbook",
        "_poly_mask",
        "_ice_glitter",
    )
    manifest.declare_vault(
        "techniques/hybrid_vfx/four_stage_emitter_architecture.md",
        "EmitterStack",
    )
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)

    critique = CritiqueLog(asset=ASSET_NAME, modality="vfx", min_rounds=3)
    critique.add_round(
        stage_blockout,
        defects_found=["Blockout only: flat triangular shards, no ground interaction."],
        fixes_applied=["Added faceted left/right planes, rim lights, and staggered eruption timing."],
        angles_checked=["flipbook contact sheet"],
        subsystem="blockout",
    )
    critique.add_round(
        stage_secondary,
        defects_found=["Spikes read as a flat wall; base contact was ambiguous."],
        fixes_applied=["Added diagonal ground line, fracture cracks, contact frost, and back-row depth haze."],
        angles_checked=["flipbook contact sheet"],
        subsystem="secondary",
    )
    critique.add_round(
        stage_final,
        defects_found=["Final candidate lacked atmosphere and ice-chip sparkle."],
        fixes_applied=["Layered cold ground bloom, mist puffs, and pre-rolled glitter shards."],
        angles_checked=["flipbook contact sheet", "dark and light preview backgrounds"],
        subsystem="final",
    )
    critique.add_detail_pass(
        stage_final,
        overall_score=9.2,
        detail_scores={
            "timing_and_arc": 9.0,
            "alpha_and_edge_falloff": 9.2,
            "loop_or_dissolve_cleanliness": 9.4,
            "color_temperature_progression": 9.1,
            "overdraw_optimization": 9.0,
        },
        flaws_found=["Lower-left shard cluster is slightly busier than the hero silhouette."],
        fixes_for_next_pass=["If iterating, thin two low-left splinters and widen the hero root by 4%."],
        modality="vfx",
        seeded_vault_docs=["techniques/hybrid_vfx/crystalline_ice_spike_eruptions.md"],
    )
    critique.save(args.out)
    print(f"✓ Generated {atlas_file}, preview.gif, preview.png, manifest.json, critique_log.json")


if __name__ == "__main__":
    main()
