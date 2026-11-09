"""
Drop-in additions for the vfx_pipeline.
These don't replace draw_shape() / cel_shade_gradient() — they LAYER on top
of them so a frame becomes: glow -> ring -> rays -> core shape -> particles,
instead of just one hard-edged primitive.

Import into your existing file, then call generate_stylized_flipbook(...)
instead of generate_flipbook(...) for effects that should look like VFX
instead of icons.

Every function here accepts `style` (see helpers/artstyles.py) so the whole
composer is artstyle-agnostic — cel, painterly, neon etc. are all decisions
in the style dict, not in the drawing code.
"""

from PIL import Image, ImageDraw, ImageFilter, ImageChops
import math
import random

try:
    from .artstyles import (merge_style, style_color, shade_band, progress_ease,
                            aa_surface, from_aa, apply_style_passes, soft_edges,
                            STYLE_CEL)
except ImportError:  # pragma: no cover
    from helpers.artstyles import (merge_style, style_color, shade_band, progress_ease,
                                   aa_surface, from_aa, apply_style_passes, soft_edges,
                                   STYLE_CEL)


# ── Blend helper ──────────────────────────────────────────────

def screen_blend_rgba(base, top):
    """Additive-ish 'screen' blend of two RGBA images of the same size."""
    base_rgb = base.convert("RGB")
    top_rgb = top.convert("RGB")
    blended_rgb = ImageChops.screen(base_rgb, top_rgb)

    base_a = base.split()[3]
    top_a = top.split()[3]
    combined_a = ImageChops.lighter(base_a, top_a)

    out = blended_rgb.convert("RGBA")
    out.putalpha(combined_a)
    return out


# ── Radial glow with true falloff (not flat blur halo) ───────

def make_radial_glow(size, cx, cy, radius, color, max_alpha, style=None,
                     intensity=None):
    """Pixel radial glow. falloff: 'quadratic' | 'exponential' | float exponent.

    A flat blurred ellipse reads as a halo blob; a quadratic/exponential
    falloff reads as light. Intensity is read from the style unless given.
    """
    st = merge_style(style)
    if intensity is None:
        intensity = st.get("glow_intensity", 1.0)
    falloff = st.get("glow_falloff", "quadratic")

    if falloff == "quadratic":
        t = 2.0
    elif falloff == "exponential":
        t = 3.0
    else:
        t = float(falloff)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()
    r, g, b = color
    a_max = max(0, min(255, int(max_alpha * intensity)))
    r2 = radius * radius
    cyi, cxi = int(cy), int(cx)
    ri = int(radius)
    for py in range(max(0, cyi - ri), min(size, cyi + ri + 1)):
        dy = py - cy
        for px in range(max(0, cxi - ri), min(size, cxi + ri + 1)):
            dx = px - cx
            d2 = dx * dx + dy * dy
            if d2 > r2:
                continue
            n = (1 - math.sqrt(d2 / r2)) ** t
            if n > 0.002:
                pixels[px, py] = (r, g, b, int(a_max * n))
    return img


# ── Layer builders ───────────────────────────────────────────

def make_glow_layer(size, cx, cy, radius, color, style=None, blur_radius=None,
                    intensity=255):
    """Soft blurred core fallback — kept for back-compat; prefer make_radial_glow."""
    if blur_radius is None:
        blur_radius = radius * 0.6
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
              fill=(r, g, b, intensity))
    return layer.filter(ImageFilter.GaussianBlur(blur_radius))


def make_rays_layer(size, cx, cy, count, length, width, color, rotation=0, taper=True):
    """Radiating streaks — reads as 'energy' instead of 'sticker'."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    for i in range(count):
        angle = math.radians(rotation + (360 / count) * i)
        tip_x = cx + length * math.cos(angle)
        tip_y = cy + length * math.sin(angle)
        perp = angle + math.pi / 2
        w = width * (0.4 if taper else 1.0)
        base1 = (cx + w * math.cos(perp), cy + w * math.sin(perp))
        base2 = (cx - w * math.cos(perp), cy - w * math.sin(perp))
        d.polygon([base1, base2, (tip_x, tip_y)], fill=(r, g, b, 220))
    return layer


def make_particles_layer(size, cx, cy, count, max_spread, color, progress, seed=0, base_particle_size=6):
    """Small sparks flying outward and fading — gives motion instead of one static blob.
    seed: keep this FIXED per-effect so particles travel consistent paths frame to frame."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    rng = random.Random(seed)
    for i in range(count):
        base_angle = rng.uniform(0, 2 * math.pi)
        speed = rng.uniform(0.6, 1.0)
        dist = max_spread * progress * speed
        px = cx + dist * math.cos(base_angle)
        py = cy + dist * math.sin(base_angle)
        life = max(0, 1 - progress * rng.uniform(0.8, 1.3))
        if life <= 0:
            continue
        psize = base_particle_size * life * rng.uniform(0.5, 1.2)
        if psize < 1:
            continue
        alpha = int(255 * life)
        d.ellipse([px - psize, py - psize, px + psize, py + psize],
                  fill=(r, g, b, alpha))
    return layer


def make_ring_layer(size, cx, cy, radius, color, thickness=6):
    """Expanding shockwave ring, separate from the core shape."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    outer = radius
    inner = max(0, radius - thickness)
    d.ellipse([cx - outer, cy - outer, cx + outer, cy + outer], fill=(r, g, b, 200))
    if inner > 0:
        d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], fill=(0, 0, 0, 0))
    return layer


# ── Full stylized frame composer ─────────────────────────────

def generate_stylized_frame(frame_size, progress, color_a, color_b, shape_draw_fn,
                            seed=0, glow=True, rays=True, particles=True, ring=True,
                            style=None):
    """
    Composites: glow -> ring -> rays -> core shape (your existing draw_shape) -> particles.
    shape_draw_fn(draw, cx, cy, radius, color) -> should call your existing draw_shape().
    style: artstyles dict (see helpers/artstyles.py). Defaults to cel for back-compat.
    Returns a single RGBA frame image of size (frame_size, frame_size).
    """
    st = merge_style(style if style is not None else STYLE_CEL)
    cx = cy = frame_size // 2
    frame = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))

    t = progress_ease(st, progress)
    color = style_color(st, color_a, color_b, progress)

    core_radius = (frame_size * 0.28) * (1 - abs(t - 0.3) * 0.6)
    core_radius = max(core_radius, frame_size * 0.05)

    if glow:
        glow_layer = make_radial_glow(frame_size, cx, cy, core_radius * 1.9, color,
                                      int(180 * (1 - t * 0.5)), style=st)
        glow_layer = soft_edges(glow_layer, st.get("edge_softness", 0) or 0.5)
        frame = screen_blend_rgba(frame, glow_layer)

    if ring:
        ring_radius = frame_size * 0.15 + (frame_size * 0.35) * t
        ring_alpha_layer = make_ring_layer(frame_size, cx, cy, ring_radius, color,
                                           thickness=frame_size * 0.03)
        fade = int(255 * max(0, 1 - t))
        alpha_ch = ring_alpha_layer.split()[3].point(lambda a: min(a, fade))
        ring_alpha_layer.putalpha(alpha_ch)
        frame = Image.alpha_composite(frame, ring_alpha_layer)

    if rays:
        rays_layer = make_rays_layer(frame_size, cx, cy, count=8,
                                     length=frame_size * (0.2 + 0.3 * t),
                                     width=frame_size * 0.02, color=color,
                                     rotation=t * 90)
        frame = screen_blend_rgba(frame, rays_layer)

    canvas, ss = aa_surface(frame_size, st)
    core_draw = ImageDraw.Draw(canvas)
    shape_draw_fn(core_draw, cx * ss, cy * ss, core_radius * ss, color)
    core_layer = from_aa(canvas, frame_size, st)
    if st.get("alpha_mode", "hard") == "soft":
        core_layer = soft_edges(core_layer, st.get("edge_softness", 1.0))
    frame = Image.alpha_composite(frame, core_layer)

    if particles:
        particles_layer = make_particles_layer(frame_size, cx, cy, count=14,
                                               max_spread=frame_size * 0.45,
                                               color=color, progress=t,
                                               seed=seed)
        frame = screen_blend_rgba(frame, particles_layer)

    return apply_style_passes(frame, st)


def generate_stylized_flipbook(name, color_start, color_end, draw_shape_fn, shape,
                               sheet_size=512, grid=4, output_dir=None,
                               seed=None, glow=True, rays=True, particles=True, ring=True,
                               style=None):
    """
    draw_shape_fn: your existing draw_shape(draw, cx, cy, radius, shape, color, angle=0)
    shape: string like "circle" / "star" / "spark" passed through to draw_shape_fn
    seed: pass a fixed int (e.g. hash of `name`) so particle paths are stable across runs
    style: artstyles dict (see helpers/artstyles.py). None defaults to cel behaviour.
    """
    import os
    if output_dir is None:
        output_dir = "fx_pipeline/output"
    os.makedirs(output_dir, exist_ok=True)
    frame_size = sheet_size // grid
    if seed is None:
        seed = abs(hash(name)) % 10000

    sheet = Image.new("RGBA", (sheet_size, sheet_size), (0, 0, 0, 0))

    def shape_cb(draw, cx, cy, radius, color):
        draw_shape_fn(draw, cx, cy, radius, shape, color, angle=0)

    for frame_idx in range(grid * grid):
        row, col = divmod(frame_idx, grid)
        x, y = col * frame_size, row * frame_size
        progress = frame_idx / (grid * grid - 1)

        frame = generate_stylized_frame(frame_size, progress, color_start, color_end,
                                        shape_cb, seed=seed,
                                        glow=glow, rays=rays, particles=particles,
                                        ring=ring, style=style)
        sheet.alpha_composite(frame, (x, y))

    path = os.path.join(output_dir, f"{name}.png")
    sheet.save(path)
    print(f"  Generated stylized: {name}.png")
    return path