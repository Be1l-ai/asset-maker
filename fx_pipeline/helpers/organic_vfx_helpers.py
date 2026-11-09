"""
organic_vfx_helpers.py

Two independent tool groups + one utility:
  Group A — Blob helpers:      noise-perturbed irregular shapes for dust/debris.
  Group B — Hero helpers:      deliberate shape-identity VFX via named archetypes
                               (burst, flame, crown, impact).
  Group C — Ripple helper:     wobbled geometric ring for water-surface effects.

ALL functions produce RGBA images on TRANSPARENT background.
Callers should composite onto opaque black via onto_black_bg() for Roblox
additive blending.
"""

from PIL import Image, ImageDraw, ImageFilter, ImageChops
import math
import random

try:
    from .artstyles import merge_style, apply_style_passes
except ImportError:  # pragma: no cover
    from helpers.artstyles import merge_style, apply_style_passes


# ── Shared helpers ──────────────────────────────────────────────

def screen_blend_rgba(base, top):
    base_rgb = base.convert("RGB")
    top_rgb = top.convert("RGB")
    blended_rgb = ImageChops.screen(base_rgb, top_rgb)
    base_a = base.split()[3]
    top_a = top.split()[3]
    combined_a = ImageChops.lighter(base_a, top_a)
    out = blended_rgb.convert("RGBA")
    out.putalpha(combined_a)
    return out


def onto_black_bg(img):
    bg = Image.new("RGB", img.size, (0, 0, 0))
    bg.paste(img, (0, 0), img)
    return bg.convert("RGBA")


def radial_noise(t, seed, octaves=2, base_freq=6):
    rng = random.Random(seed)
    val = 0.0
    total = 0.0
    for i in range(octaves):
        freq = base_freq * (i + 1) + rng.uniform(-0.5, 0.5)
        phase = rng.uniform(0, 2 * math.pi)
        amp = 1.0 / (i + 1)
        val += amp * math.sin(t * freq + phase)
        total += amp
    return val / total


# ── Group A: Blob helpers (dust / debris — no shape identity) ──

def make_jagged_polygon(size, cx, cy, avg_radius, color, jaggedness=0.2,
                        seed=0, num_vertices=16, alpha=255):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    pts = []
    for i in range(num_vertices):
        angle = (2 * math.pi / num_vertices) * i
        n = radial_noise(angle, seed + i, octaves=3, base_freq=4)
        r2 = avg_radius * (1 + n * jaggedness)
        pts.append((cx + r2 * math.cos(angle), cy + r2 * math.sin(angle)))
    d.polygon(pts, fill=(r, g, b, alpha))
    return layer


def make_gradient_blob(size, cx, cy, avg_radius, colors, jaggedness=0.2, seed=0):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    n = len(colors)
    for i, color in enumerate(colors):
        t = i / max(n - 1, 1)
        r2 = avg_radius * (1 - t * 0.7)
        blob = make_jagged_polygon(size, cx, cy, r2, color,
                                    jaggedness=jaggedness * (1 - t * 0.5),
                                    seed=seed + i, num_vertices=14,
                                    alpha=int(255 * (1 - t * 0.3)))
        layer = Image.alpha_composite(layer, blob)
    return layer


# ── Group B: Hero helpers (deliberate shape identity per archetype) ──

def make_petal_lobe(cx, cy, angle, length, width, seed,
                    segments=10, edge_noise=0.06):
    perp = angle + math.pi / 2
    left = []
    right = []
    for i in range(segments):
        t = i / (segments - 1)
        dist = length * (t ** 0.85)
        w_profile = width * ((1 - t) ** 1.2) * (0.65 + 0.5 * math.sin(t * math.pi * 0.85 + 0.2))
        n = radial_noise(t, seed + i) * edge_noise * width
        bx = cx + dist * math.cos(angle)
        by = cy + dist * math.sin(angle)
        left.append((bx + (w_profile + n) * math.cos(perp),
                     by + (w_profile + n) * math.sin(perp)))
        right.append((bx - (w_profile + n) * math.cos(perp),
                      by - (w_profile + n) * math.sin(perp)))
    tip = (cx + length * math.cos(angle), cy + length * math.sin(angle))
    return left + [tip] + right[::-1]


ARCHETYPES = {
    "burst": dict(major_count=(3, 4), angle_mode="radial", angle_jitter=0.3,
                  length_range=(0.9, 1.3), width_range=(0.28, 0.4)),
    "flame": dict(major_count=(2, 3), angle_mode="upward", angle_jitter=0.45,
                  length_range=(1.0, 1.5), width_range=(0.18, 0.28)),
    "crown": dict(major_count=(4, 6), angle_mode="top_arc", angle_jitter=0.12,
                  length_range=(0.8, 1.0), width_range=(0.14, 0.2)),
    "impact": dict(major_count=(1, 1), angle_mode="single", angle_jitter=0.0,
                   length_range=(1.2, 1.6), width_range=(0.35, 0.45)),
}


def _pick_major_angles(archetype, seed):
    rng = random.Random(seed)
    cfg = ARCHETYPES[archetype]
    count = rng.randint(*cfg["major_count"])
    jitter = cfg["angle_jitter"]
    mode = cfg["angle_mode"]

    if mode == "radial":
        step = 2 * math.pi / count
        return [i * step + rng.uniform(-jitter, jitter) for i in range(count)]
    if mode == "upward":
        return [-math.pi / 2 + rng.uniform(-jitter, jitter) for _ in range(count)]
    if mode == "top_arc":
        spread = 1.6
        return [-math.pi / 2 + (i - (count - 1) / 2) * (spread / max(count - 1, 1))
                + rng.uniform(-jitter, jitter) for i in range(count)]
    if mode == "single":
        return [rng.uniform(0, 2 * math.pi)]
    return [rng.uniform(0, 2 * math.pi) for _ in range(count)]


def make_hero_silhouette(size, cx, cy, base_radius, color_stops, seed,
                         archetype="burst"):
    rng = random.Random(seed)
    cfg = ARCHETYPES[archetype]
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    hot = color_stops[-1]
    mid = color_stops[len(color_stops) // 2]

    major_angles = _pick_major_angles(archetype, seed)
    major_angles.sort(key=lambda a: -rng.random())
    for i, angle in enumerate(major_angles):
        length = base_radius * rng.uniform(*cfg["length_range"])
        width = base_radius * rng.uniform(*cfg["width_range"])
        pts = make_petal_lobe(cx, cy, angle, length, width, seed=seed + i * 31)
        d.polygon(pts, fill=mid + (235,))

    for i, angle in enumerate(major_angles):
        length = base_radius * rng.uniform(*cfg["length_range"]) * 0.6
        width = base_radius * rng.uniform(*cfg["width_range"]) * 0.55
        pts = make_petal_lobe(cx, cy, angle, length, width,
                              seed=seed + i * 31 + 500)
        d.polygon(pts, fill=hot + (255,))

    minor_count = rng.randint(3, 5)
    for _ in range(minor_count):
        angle = rng.uniform(0, 2 * math.pi)
        length = base_radius * rng.uniform(0.35, 0.6)
        width = base_radius * rng.uniform(0.04, 0.08)
        pts = make_petal_lobe(cx, cy, angle, length, width,
                              seed=seed + int(angle * 1000),
                              segments=6, edge_noise=0.1)
        alpha = rng.randint(110, 170)
        d.polygon(pts, fill=hot + (alpha,))

    return layer


def generate_hero_frame(size, progress, color_stops, seed, archetype="burst",
                        style=None):
    cx = cy = size // 2
    frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base_radius = size * 0.26 * (1 - abs(progress - 0.3) * 0.5)
    base_radius = max(base_radius, size * 0.06)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - base_radius * 1.4, cy - base_radius * 1.4,
                cx + base_radius * 1.4, cy + base_radius * 1.4],
               fill=color_stops[0] + (160,))
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.07))
    frame = screen_blend_rgba(frame, glow)

    hero = make_hero_silhouette(size, cx, cy, base_radius, color_stops,
                                seed, archetype)
    hero = hero.filter(ImageFilter.GaussianBlur(size * 0.004))
    frame = screen_blend_rgba(frame, hero)

    return apply_style_passes(frame, merge_style(style))


def generate_hero_flipbook(name, color_stops, output_dir, archetype="burst",
                           sheet_size=512, grid=4, seed=None,
                           onto_black=False, style=None):
    import os
    os.makedirs(output_dir, exist_ok=True)
    frame_size = sheet_size // grid
    if seed is None:
        seed = abs(hash(name)) % 10000

    sheet = Image.new("RGBA", (sheet_size, sheet_size), (0, 0, 0, 0))
    for frame_idx in range(grid * grid):
        row, col = divmod(frame_idx, grid)
        x, y = col * frame_size, row * frame_size
        progress = frame_idx / (grid * grid - 1)
        frame = generate_hero_frame(frame_size, progress, color_stops,
                                     seed=seed + frame_idx, archetype=archetype,
                                     style=style)
        sheet.alpha_composite(frame, (x, y))

    if onto_black:
        sheet = onto_black_bg(sheet)

    path = os.path.join(output_dir, f"{name}.png")
    sheet.save(path)
    print(f"  Generated hero ({archetype}): {name}.png")
    return path


# ── Group C: Ripple helper (geometric wobble ring for water surface) ──

def make_ripple_ring(size, cx, cy, radius, thickness, color, seed=0,
                      num_vertices=24, wobble=0.03, alpha=200):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color

    outer_pts = []
    inner_pts = []
    for i in range(num_vertices):
        angle = (2 * math.pi / num_vertices) * i
        n = radial_noise(angle, seed + i, octaves=2, base_freq=3)
        ro = radius * (1 + n * wobble)
        ri = max(0, (radius - thickness)) * (1 + n * wobble * 0.3)
        outer_pts.append((cx + ro * math.cos(angle), cy + ro * math.sin(angle)))
        inner_pts.append((cx + ri * math.cos(angle), cy + ri * math.sin(angle)))

    outer_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    od = ImageDraw.Draw(outer_layer)
    od.polygon(outer_pts, fill=(r, g, b, alpha))

    inner_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    id_ = ImageDraw.Draw(inner_layer)
    id_.polygon(inner_pts, fill=(0, 0, 0, 255))

    outer_layer.paste(inner_layer, (0, 0), inner_layer)
    return outer_layer
