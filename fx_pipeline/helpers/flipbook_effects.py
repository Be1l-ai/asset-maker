"""
flipbook_effects.py — classic gameplay VFX as flipbooks: fireball, lightning,
waterfall, dust.

Architecture:
  Every effect is a pure function  frame_fn(size, t, style, seed) -> RGBA Image
  and any flipbook builder can drive it. `style` is an artstyles dict
  (see helpers/artstyles.py) — the same effect can render cel, painterly,
  neon, etc. without touching this module.

  build_flipbook(...) is the generic sheet assembler (AA, soft edges, style
  passes, seamless-loop support).

Effects here are designed as loops when marked seamless=True:
  - frame 0 and frame N-1 are visually identical (wrap-around motion),
    so Loop-mode ParticleEmitters don't pop.
"""

import math
import random
import os

from PIL import Image, ImageDraw, ImageFilter

try:
    from .artstyles import (merge_style, style_color, progress_ease, aa_surface,
                            from_aa, apply_style_passes, soft_edges)
    from .vfx_stylize_helpers import screen_blend_rgba, make_radial_glow
    from .organic_vfx_helpers import make_petal_lobe, make_gradient_blob
except ImportError:  # pragma: no cover
    from helpers.artstyles import (merge_style, style_color, progress_ease, aa_surface,
                                   from_aa, apply_style_passes, soft_edges)
    from helpers.vfx_stylize_helpers import screen_blend_rgba, make_radial_glow
    from helpers.organic_vfx_helpers import make_petal_lobe, make_gradient_blob


# ── Generic sheet assembler ──────────────────────────────────

def _pick_background(frames, mode):
    """Decide an opaque background colour for a set of frames.

    mode: 'black' | 'white' | 'auto'. Auto picks per the effect's dominant
    luminance: bright/airy effects (water, dust) sit on white; vivid/dark
    ones (fire, lightning) sit on black. Returns (RGB colour, keep_alpha).
    """
    if mode == "white":
        return (255, 255, 255), False
    if mode == "black":
        return (0, 0, 0), False
    # auto: average perceived luminance over all frames, alpha-weighted
    tot = 0
    n = 0
    for f in frames:
        a = f.split()[3]
        rgb = f.convert("RGB")
        for (r, g, b), av in zip(rgb.getdata(), a.getdata()):
            if av:
                tot += 0.299 * r + 0.587 * g + 0.114 * b
                n += 1
    if n == 0:
        return (0, 0, 0), False
    lum = tot / n
    if lum > 150:           # bright pastel effect -> white card
        return (255, 255, 255), False
    return (0, 0, 0), False


def build_flipbook(name, frame_fn, style, output_dir, sheet_size=512, grid=4,
                   seed=0, seamless=False, background=None):
    """frame_fn(size, t, style, seed) -> RGBA Image. Composites a grid sheet.

    `background` overrides the style's `background` key ('black'/'white'/'auto').
    When set, the baked sheet is opaque (alpha dropped) so the flipbook works in
    ParticleEmitter sorted rendering without a transparent checkerboard.
    """
    st = merge_style(style)
    os.makedirs(output_dir, exist_ok=True)
    frame_size = sheet_size // grid

    n = grid * grid
    step = 1.0 / n if seamless else 1.0 / (n - 1)
    frames = []
    for idx in range(n):
        row, col = divmod(idx, grid)
        x, y = col * frame_size, row * frame_size
        t = idx * step
        frame = frame_fn(frame_size, t, st, seed)
        if st.get("alpha_mode", "hard") == "soft":
            frame = soft_edges(frame, st.get("edge_softness", 1.0))
        frame = apply_style_passes(frame, st)
        frames.append((frame, x, y))

    bg_mode = background if background else st.get("background", "auto")
    if bg_mode and str(bg_mode).lower() != "none":
        bg_color, keep_alpha = _pick_background([f for f, _, _ in frames], bg_mode)
        sheet = Image.new("RGBA", (sheet_size, sheet_size), bg_color + (255,) if keep_alpha else bg_color)
        for frame, x, y in frames:
            sheet.alpha_composite(frame, (x, y))
        sheet = sheet.convert("RGB")
    else:
        sheet = Image.new("RGBA", (sheet_size, sheet_size), (0, 0, 0, 0))
        for frame, x, y in frames:
            sheet.alpha_composite(frame, (x, y))

    path = os.path.join(output_dir, f"{name}.png")
    sheet.save(path)
    print(f"  Generated effect: {name}.png" + (f"  (bg: {'white' if bg_color == (255,255,255) else 'black'})" if bg_mode and str(bg_mode).lower() != 'none' else ""))
    return path


# ── Effect: classic fireball ─────────────────────────────────

FIRE_PALETTE = [(255, 60, 20), (255, 140, 30), (255, 205, 70), (255, 250, 220)]


def _flame_lick(size, cx, cy, angle, length, width, color, seed):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = make_petal_lobe(cx, cy, angle, length, width, seed=seed)
    d.polygon(pts, fill=color + (230,))
    return layer


def fireball_frame(size, t, style, seed=0):
    st = merge_style(style)
    rng = random.Random(seed + int(t * 1000))
    cx = cy = size // 2
    frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    phase = 2 * math.pi * t

    flicker = 1 + 0.12 * math.sin(phase * 6 + seed)
    fade = 1 - t * 0.55

    # 0: ambient glow
    glow_r = size * 0.38 * flicker
    glow = make_radial_glow(size, cx, cy, glow_r, (255, 90, 20),
                            int(150 * fade), style=st)
    frame = screen_blend_rgba(frame, glow)

    # 1-3: flame licks, inner layers hotter and smaller
    licks = 4 + (seed % 2)
    for i in range(licks):
        angle = -math.pi / 2 + rng.uniform(-0.7, 0.7) + 0.25 * math.sin(phase + i * 2.1)
        length = size * rng.uniform(0.30, 0.44) * flicker
        width = size * rng.uniform(0.10, 0.16)
        col = (255, 110, 30) if i % 2 == 0 else (255, 70, 20)
        lk = _flame_lick(size, cx, cy, angle, length, width, col, seed + i * 31)
        lk = lk.filter(ImageFilter.GaussianBlur(size * 0.008))
        frame = screen_blend_rgba(frame, lk)

    # mid layer
    for i in range(3):
        angle = -math.pi / 2 + rng.uniform(-0.45, 0.45) + 0.3 * math.sin(phase + i * 3.3)
        length = size * rng.uniform(0.18, 0.26) * flicker
        width = size * rng.uniform(0.09, 0.13)
        lk = _flame_lick(size, cx, cy, angle, length, width, (255, 175, 50),
                         seed + 500 + i * 13)
        frame = screen_blend_rgba(frame, lk)

    # hot core
    core_r = size * (0.09 + 0.02 * math.sin(phase * 9 + seed)) * flicker
    core = make_radial_glow(size, cx, cy, core_r, (255, 255, 235),
                            int(255 * fade), style=st)
    frame = screen_blend_rgba(frame, core)

    # embers rising
    em = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    de = ImageDraw.Draw(em)
    for i in range(9):
        rise = (t * rng.uniform(0.2, 1.0) + rng.uniform(0, 0.12)) % 1.0
        px = cx + rng.uniform(-0.12, 0.12) * size
        py = cy + (rise * 0.45) * size
        life = 1 - rise
        r = size * (0.008 + 0.014 * life)
        de.ellipse([px - r, py - r, px + r, py + r],
                   fill=(255, 190, 80, int(200 * life * fade)))
    em = em.filter(ImageFilter.GaussianBlur(size * 0.004))
    frame = screen_blend_rgba(frame, em)

    return frame


# ── Effect: lightning bolt ───────────────────────────────────

def _bolt_path(size, seed):
    """Jagged bolt from top-centre to bottom with x-jitter. Returns point list."""
    rng = random.Random(seed)
    x = size * 0.5
    pts = [(x, 0)]
    segs = 9
    for i in range(1, segs + 1):
        y = size * (i / segs) ** 1.1
        x += rng.uniform(-size, size) * 0.075
        x = max(size * 0.1, min(size * 0.9, x))
        pts.append((x, y))
    return pts


def _branch_pts(p1, p2, size, rng, depth=0):
    """Smaller offshoots from a segment."""
    bx = (p1[0] + p2[0]) / 2 + rng.uniform(-0.06, 0.06) * size
    by = (p1[1] + p2[1]) / 2
    side = 1 if rng.random() < 0.5 else -1
    out = [(bx, by), (bx + side * rng.uniform(0.08, 0.2) * size,
                      by + rng.uniform(0.05, 0.18) * size)]
    if depth > 0 and rng.random() < 0.6:
        out += _branch_pts(out[1], (out[1][0] + side * 0.06 * size, out[1][1] + 0.1 * size),
                           size, rng, depth - 1)
    return out


def lightning_frame(size, t, style, seed=0):
    st = merge_style(style)
    rng = random.Random(seed)
    cx = size // 2
    frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # early flash the way lightning works: bang, then linger
    raw = 1 - progress_ease(st, t)
    flash = max(0.0, 1 - t * 4.5)
    brightness = raw * raw

    # 0: cloud flash
    if flash > 0:
        ball = make_radial_glow(size, cx, size * 0.18, size * 0.32,
                                (190, 205, 255), int(90 * flash), style=st)
        frame = screen_blend_rgba(frame, ball)

    path = _bolt_path(size, seed)
    # growth: bolt draws itself top-down in the first 40% of the animation
    grow = min(1.0, t * 2.8)
    n_pts = max(2, int(len(path) * grow))

    # glow underlay (wide blur)
    glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow_layer)
    dg.line(path[:n_pts], fill=(130, 160, 255, int(120 * brightness)),
            width=int(size * 0.045) + 1, joint="curve")
    dg.line(path[:n_pts], fill=(200, 215, 255, int(180 * brightness)),
            width=int(size * 0.018) + 1, joint="curve")
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(size * 0.03))
    frame = screen_blend_rgba(frame, glow_layer)

    # branches only after main bolt shows
    if t > 0.08:
        branch_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        db = ImageDraw.Draw(branch_layer)
        for i in range(1, min(n_pts, len(path)) - 1):
            if rng.random() < 0.45:
                sub = _branch_pts(path[i - 1], path[i], size, rng)
                db.line(sub, fill=(170, 190, 255, int(110 * brightness)),
                        width=max(1, int(size * 0.008)), joint="curve")
        frame = screen_blend_rgba(frame, branch_layer)

    # white-hot core
    core_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dc = ImageDraw.Draw(core_layer)
    dc.line(path[:n_pts], fill=(255, 255, 255, int(255 * brightness)),
            width=max(1, int(size * 0.006)), joint="curve")
    frame = screen_blend_rgba(frame, core_layer)

    # ground contact flash
    if t < 0.3:
        ground = make_radial_glow(size, path[-1][0], path[-1][1], size * 0.12,
                                  (220, 235, 255), int(120 * (1 - t * 3.3)), style=st)
        frame = screen_blend_rgba(frame, ground)

    return frame


# ── Effect: waterfall (seamless loop) ────────────────────────

WATER_BASE = (150, 205, 255)
WATER_HI = (235, 248, 255)


def waterfall_frame(size, t, style, seed=0):
    st = merge_style(style)
    rng = random.Random(seed)
    cx = size // 2
    stream_w = size * 0.52
    frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # mist column (breathing)
    mist = make_radial_glow(size, cx, size * 0.45, size * 0.34,
                            (180, 220, 255), int(70 + 25 * math.sin(2 * math.pi * t)),
                            style=st)
    frame = screen_blend_rgba(frame, mist)

    # falling streaks — offsets wrap so frame0 == frameN for seamless loop
    streaks = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ds = ImageDraw.Draw(streaks)
    n = 30
    for i in range(n):
        fx = cx + rng.uniform(-0.5, 0.5) * stream_w
        travel = rng.choice((1.0, 1.0, 2.0))            # integer wraps -> seamless loop
        fy = (rng.uniform(0, 1) + t * travel) % 1.0
        sway = math.sin(2 * math.pi * t + i) * size * 0.015
        hlen = size * rng.uniform(0.10, 0.22)
        w = max(1, size * rng.uniform(0.006, 0.014))
        alpha = int(rng.uniform(90, 200) * (0.35 + 0.65 * math.sin(math.pi * fy) ** 0.8))
        ds.line([(fx + sway - w, fy * size), (fx + sway + w, fy * size)],
                fill=WATER_BASE + (alpha,), width=int(max(1, w * size * 0.02)))
        # elongated drop body
        ds.ellipse([fx + sway - w, fy * size - hlen, fx + sway + w, fy * size],
                   fill=WATER_HI + (int(alpha * 0.9),))
    streaks = streaks.filter(ImageFilter.GaussianBlur(size * 0.006))
    frame = screen_blend_rgba(frame, streaks)

    # bright core column
    core = make_radial_glow(size, cx, size * 0.42, size * 0.16,
                            WATER_HI, int(60) + int(30 * math.sin(2 * math.pi * t)),
                            style=st)
    frame = screen_blend_rgba(frame, core)

    # splash foam at the bottom
    foam = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    df = ImageDraw.Draw(foam)
    fy0 = size * 0.82
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)
    for i in range(7):
        fx = cx + (i - 3) * size * 0.07 + rng.uniform(-0.01, 0.01) * size
        r = size * (0.05 + 0.015 * i) * (0.85 + 0.3 * pulse)
        df.ellipse([fx - r, fy0 - r * 0.4, fx + r, fy0 + r * 0.4],
                   fill=WATER_HI + (int(150 * (1 - i * 0.09)),))
    foam = foam.filter(ImageFilter.GaussianBlur(size * 0.02))
    frame = frame if False else Image.alpha_composite(frame, foam)

    return frame


# ── Effect: dust puff (seamless loop) ────────────────────────

DUST_PAL = [(205, 195, 180), (165, 158, 148), (125, 120, 112)]


def dust_frame(size, t, style, seed=0):
    st = merge_style(style)
    rng = random.Random(seed)
    cx = cy = size // 2
    frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    phase = 2 * math.pi * t

    # breathing puff: contracts then expands
    breathe = 0.5 + 0.5 * math.sin(phase)
    avg_r = size * (0.12 + 0.10 * breathe)
    blob = make_gradient_blob(size, cx, cy, avg_r, DUST_PAL,
                              jaggedness=0.24 + 0.06 * math.sin(phase * 2 + seed),
                              seed=seed)
    blob = blob.filter(ImageFilter.GaussianBlur(size * 0.012))
    frame = Image.alpha_composite(frame, blob)

    # drifting debris (wraps horizontally)
    debris = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dd = ImageDraw.Draw(debris)
    for i in range(8):
        drift = rng.choice((-1.0, 0.0, 1.0))            # integer wraps -> seamless loop
        dx = (rng.uniform(-0.4, 0.4) + t * drift) % 1.0 - 0.5
        dy = rng.uniform(-0.38, 0.38) + 0.05 * math.sin(phase + i * 1.7)
        r = size * rng.uniform(0.008, 0.02)
        a = int(rng.uniform(50, 120) * (0.6 + 0.4 * math.sin(phase + i * 2.3)))
        dd.ellipse([cx + dx * size - r, cy + dy * size - r,
                    cx + dx * size + r, cy + dy * size + r],
                   fill=DUST_PAL[1] + (a,))
    frame = Image.alpha_composite(frame, debris)

    return frame