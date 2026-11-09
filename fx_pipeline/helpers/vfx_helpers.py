from PIL import Image, ImageDraw, ImageFilter
import math
import os

try:
    from .artstyles import (STYLE_CEL, merge_style, style_color, shade_band,
                            progress_ease, aa_surface, from_aa, apply_style_passes,
                            soft_edges)
except ImportError:  # pragma: no cover - runner adds fx_pipeline to sys.path
    from helpers.artstyles import (STYLE_CEL, merge_style, style_color, shade_band,
                                   progress_ease, aa_surface, from_aa, apply_style_passes,
                                   soft_edges)

SHEET_SIZE = 512
GRID = 4
FRAME_SIZE = SHEET_SIZE // GRID

RARITY_COLORS = {
    "common":    { "primary": (76, 217, 100),  "secondary": (139, 105, 20),   "accent": (255, 214, 10) },
    "uncommon":  { "primary": (106, 13, 173),  "secondary": (26, 0, 48),      "accent": (0, 229, 255) },
    "rare":      { "primary": (255, 45, 45),   "secondary": (204, 85, 0),     "accent": (255, 184, 0) },
    "epic":      { "primary": (0, 180, 216),   "secondary": (3, 4, 94),       "accent": (240, 248, 255) },
    "legendary": { "primary": (255, 215, 0),   "secondary": (123, 45, 142),   "accent": (255, 255, 255) },
}

WEATHER_COLORS = {
    "solar":       (255, 230, 100),
    "drought":     (255, 140, 50),
    "alien":       (100, 255, 150),
    "admin_abuse": (255, 50, 50),
    "rain":        (100, 180, 255),
}


# ── Drawing Primitives (all hard-edge, no soft alpha) ────────

def draw_shape(draw, cx, cy, radius, shape, color, angle=0):
    r, g, b = color
    if shape == "circle":
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=(r, g, b, 255))

    elif shape == "square":
        draw.regular_polygon((cx, cy, radius), 4, rotation=angle, fill=(r, g, b, 255))

    elif shape == "diamond":
        draw.regular_polygon((cx, cy, radius), 4, rotation=45 + angle, fill=(r, g, b, 255))

    elif shape == "triangle":
        draw.regular_polygon((cx, cy, radius), 3, rotation=angle, fill=(r, g, b, 255))

    elif shape == "hex":
        draw.regular_polygon((cx, cy, radius), 6, rotation=angle, fill=(r, g, b, 255))

    elif shape == "spark":
        pts = []
        for i in range(8):
            a = math.pi * i / 4 + math.radians(angle)
            r2 = radius if i % 2 == 0 else radius * 0.25
            pts.append((cx + r2 * math.cos(a), cy + r2 * math.sin(a)))
        draw.polygon(pts, fill=(r, g, b, 255))

    elif shape == "star":
        pts = []
        for i in range(10):
            a = math.pi * i / 5 - math.pi / 2 + math.radians(angle)
            r2 = radius if i % 2 == 0 else radius * 0.4
            pts.append((cx + r2 * math.cos(a), cy + r2 * math.sin(a)))
        draw.polygon(pts, fill=(r, g, b, 255))

    elif shape == "ring":
        outer_r = radius
        inner_r = radius * 0.6
        draw.ellipse([cx-outer_r, cy-outer_r, cx+outer_r, cy+outer_r], fill=(r, g, b, 255))
        draw.ellipse([cx-inner_r, cy-inner_r, cx+inner_r, cy+inner_r], fill=(0, 0, 0, 0))

    elif shape == "cross":
        w = radius * 0.3
        h = radius * 0.7
        draw.polygon([
            (cx-w, cy-h), (cx+w, cy-h), (cx+w, cy-w),
            (cx+h, cy-w), (cx+h, cy+w), (cx+w, cy+w),
            (cx+w, cy+h), (cx-w, cy+h), (cx-w, cy+w),
            (cx-h, cy+w), (cx-h, cy-w), (cx-w, cy-w),
        ], fill=(r, g, b, 255))

    elif shape == "streak":
        draw.ellipse([cx-radius, cy-radius*0.3, cx+radius, cy+radius*0.3], fill=(r, g, b, 255))

    elif shape == "hex_ring":
        outer = []
        inner = []
        for i in range(6):
            a = math.pi * i / 3 - math.pi / 6 + math.radians(angle)
            outer.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
            inner.append((cx + radius * 0.6 * math.cos(a), cy + radius * 0.6 * math.sin(a)))
        draw.polygon(outer, fill=(r, g, b, 255))
        draw.polygon(inner, fill=(0, 0, 0, 0))

    elif shape == "double_circle":
        offset = radius * 0.4
        draw.ellipse([cx-radius+offset, cy-radius, cx+radius+offset, cy+radius], fill=(r, g, b, 255))
        draw.ellipse([cx-radius-offset, cy-radius, cx+radius-offset, cy+radius], fill=(r, g, b, 255))

    elif shape == "cracked_diamond":
        import random
        rng = random.Random(hash((cx, cy, radius, angle, color)))
        pts = []
        for i in range(4):
            a = math.radians(45 + angle) + math.pi * i / 2
            crack = rng.uniform(-3, 3)
            r2 = radius + crack
            pts.append((cx + r2 * math.cos(a), cy + r2 * math.sin(a)))
        draw.polygon(pts, fill=(r, g, b, 255))
        for i in range(4):
            a = math.radians(45 + angle) + math.pi * i / 2
            a2 = a + math.pi / 8 * rng.uniform(-0.5, 0.5)
            crack = rng.uniform(-5, 3)
            extra = rng.uniform(0.15, 0.35) * radius
            r2 = radius + crack + extra
            px = cx + r2 * math.cos(a2)
            py = cy + r2 * math.sin(a2)
            a_adj = a + rng.uniform(-0.15, 0.15)
            r_adj = radius * rng.uniform(0.6, 0.9)
            adj = (cx + r_adj * math.cos(a_adj), cy + r_adj * math.sin(a_adj))
            draw.polygon([adj, pts[i], (px, py)], fill=(r, g, b, 255))


# ── Style resolution ─────────────────────────────────────────

def _pick_style(style, use_cel):
    """style: dict/False/None. None falls back to use_cel (legacy flag)."""
    if style is None:
        if use_cel:
            return merge_style(STYLE_CEL)
        return merge_style({"name": "continuous", "color_curve": "continuous",
                            "glow_intensity": 0.0})
    if style is False:
        return merge_style({})
    return merge_style(style)


# ── Cel-Shaded Color Helpers (kept for back-compat, now style-based) ─

def cel_shade_gradient(color_a, color_b, t):
    st = merge_style(STYLE_CEL)
    return style_color(st, color_a, color_b, t)


def cel_shade_alpha(t, hard_cutoff=0.3):
    return 255 if t < hard_cutoff else 0


def cel_shade_size(t):
    steps = 4
    return int(t * steps) / steps


# ── Frame Generators ────────────────────────────────────────

def _render_frame_aa(frame_size, progress, color_a, color_b, shape, style,
                     angle_speed=1.0):
    """Render one frame at supersampled resolution, downscale with LANCZOS."""
    canvas, ss = aa_surface(frame_size, style)
    d = ImageDraw.Draw(canvas)
    cx = cy = frame_size * ss // 2

    t = progress_ease(style, progress)
    color = style_color(style, color_a, color_b, progress)
    margin = int(frame_size * 0.15 * (1 + shade_band(style, progress)))
    radius = (frame_size // 2) - margin
    if radius > 2:
        draw_shape(d, cx, cy, radius * ss, shape, color, angle=progress * 360 * angle_speed)

    img = from_aa(canvas, frame_size, style)
    if style.get("alpha_mode", "hard") == "soft":
        img = soft_edges(img, style.get("edge_softness", 1.0))
    return apply_style_passes(img, style)


def generate_frame(draw, x, y, frame_size, progress, color_a, color_b, shape,
                   use_cel=True, style=None):
    """Direct-draw frame (back-compat). Prefer generate_flipbook which AA-renders."""
    style = _pick_style(style, use_cel)
    cx = x + frame_size // 2
    cy = y + frame_size // 2

    color = style_color(style, color_a, color_b, progress)
    margin = int(frame_size * 0.15 * (1 + shade_band(style, progress)))
    radius = (frame_size // 2) - margin

    if radius > 2:
        draw_shape(draw, cx, cy, radius, shape, color, angle=progress * 360)


# ── Flipbook Sheet Generator ─────────────────────────────────

def generate_flipbook(name, color_start, color_end, shape, output_dir,
                      use_cel=True, style=None):
    os.makedirs(output_dir, exist_ok=True)
    style = _pick_style(style, use_cel)
    sheet = Image.new("RGBA", (SHEET_SIZE, SHEET_SIZE), (0, 0, 0, 0))

    for frame_idx in range(GRID * GRID):
        row = frame_idx // GRID
        col = frame_idx % GRID
        x = col * FRAME_SIZE
        y = row * FRAME_SIZE
        progress = frame_idx / (GRID * GRID - 1)
        frame = _render_frame_aa(FRAME_SIZE, progress, color_start, color_end,
                                 shape, style)
        sheet.alpha_composite(frame, (x, y))

    path = os.path.join(output_dir, f"{name}.png")
    sheet.save(path)
    print(f"  Generated: {name}.png")
    return path


def generate_rarity_flipbook(name, rarity_key, shape, output_dir, use_cel=True, style=None):
    colors = RARITY_COLORS[rarity_key]
    return generate_flipbook(f"{rarity_key}_{name}", colors["primary"], colors["accent"],
                             shape, output_dir, use_cel, style)


# ── Single Sprite Generators ─────────────────────────────────

def generate_sprite(name, shape, color, radius, output_dir, angle=0, style=None):
    os.makedirs(output_dir, exist_ok=True)
    style = _pick_style(style, True)
    canvas, ss = aa_surface(128, style)
    d = ImageDraw.Draw(canvas)
    draw_shape(d, 64 * ss, 64 * ss, radius * ss, shape, color, angle)
    img = from_aa(canvas, 128, style)
    img = apply_style_passes(img, style)
    path = os.path.join(output_dir, f"{name}.png")
    img.save(path)
    print(f"  Generated sprite: {name}.png")
    return path


# ── Texture Sheet Generator (for particle emitters) ──────────

def generate_texture_sheet(name, shapes_colors, output_dir, use_cel=True, style=None):
    os.makedirs(output_dir, exist_ok=True)
    style = _pick_style(style, use_cel)
    rows = len(shapes_colors)
    cell_size = 64
    sheet = Image.new("RGBA", (cell_size * 4, cell_size * rows), (0, 0, 0, 0))

    for row_idx, row_data in enumerate(shapes_colors):
        shape, color_a, color_b = row_data[0], row_data[1], row_data[2]
        blur = row_data[3] if len(row_data) > 3 else 0
        for col_idx in range(4):
            progress = col_idx / 3
            x = col_idx * cell_size
            y = row_idx * cell_size
            color = style_color(style, color_a, color_b, progress)
            canvas, ss = aa_surface(cell_size, style)
            d = ImageDraw.Draw(canvas)
            draw_shape(d, cell_size * ss // 2, cell_size * ss // 2,
                       cell_size / 3 * ss, shape, color)
            cell = from_aa(canvas, cell_size, style)
            if blur > 0:
                cell = cell.filter(ImageFilter.GaussianBlur(blur))
            cell = apply_style_passes(cell, style)
            sheet.alpha_composite(cell, (x, y))

    path = os.path.join(output_dir, f"{name}.png")
    sheet.save(path)
    print(f"  Generated texture sheet: {name}.png")
    return path