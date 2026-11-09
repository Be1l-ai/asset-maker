"""
artstyles.py — style-profile architecture for the flipbook pipeline.

A "style" is a plain dict: every visual decision is a key in that dict.
No style is hardcoded inside any drawing code — layers read the merged dict
and decide how to render. The pipeline ships with ONE baseline dict
(STYLE_CEL) that reproduces the original cel-shaded look byte-for-byte,
so existing callers keep identical output unless they opt into a style.

Defining a custom style (example, put this in your own generator):

    my_style = {
        "name": "softwash",
        "color_curve": "continuous",   # "continuous" | "cel" | int(steps) | callable(a, b, t) -> rgb
        "alpha_mode": "soft",          # "hard" | "soft" (soft = feathered edges)
        "edge_softness": 1.2,          # gaussian blur radius on alpha (px @ 128 frame)
        "easing": "ease_out",          # "linear" | "ease_out" | "ease_in" | "ease_in_out" | callable(t) -> t
        "supersample": 2,              # polygon/core AA: draw at this scale, downscale LANCZOS
        "glow_intensity": 1.0,         # multiplier the glow layers read
        "glow_falloff": "quadratic",   # "quadratic" | "exponential" | float exponent
        "grain": 0.0,                  # 0..1 alpha dither (breaks banding, adds texture)
        "outline": False,              # False or dict(color=(r,g,b), alpha=200, threshold=32)
        "saturation": 1.0,             # ImageEnhance.Color multiplier
        "contrast": 1.0,               # ImageEnhance.Contrast multiplier
    }

Then pass it anywhere the pipeline accepts `style=`:
    generate_flipbook(..., style=my_style)
    generate_stylized_flipbook(..., style=my_style)
    build_flipbook(..., style=my_style)

Missing keys fall back to STYLE_CEL behaviour via merge_style(), so a style
dict can override just one or two fields.
"""

from PIL import Image, ImageFilter, ImageEnhance, ImageChops
import math


# ── Baseline dict: reproduces the original hard-coded cel look ────────────

STYLE_CEL = {
    "name": "cel",
    "color_curve": "cel",
    "alpha_mode": "hard",
    "edge_softness": 0.0,
    "easing": "linear",
    "supersample": 2,
    "glow_intensity": 1.0,
    "glow_falloff": "quadratic",
    "grain": 0.0,
    "outline": False,
    "saturation": 1.0,
    "contrast": 1.0,
    "volume": None,
    "background": None,
}


def merge_style(style):
    """Fill in every missing key from STYLE_CEL. Accepts None/dict/Falsy."""
    if not style:
        style = {}
    return {**STYLE_CEL, **style}


# ── Progress / colour curves ──────────────────────────────────────────────

def progress_ease(style, t):
    """Apply the style's easing curve to a progress value in [0, 1]."""
    e = merge_style(style).get("easing", "linear")
    if callable(e):
        t = e(t)
    elif e == "ease_out":
        t = 1 - (1 - t) ** 2
    elif e == "ease_in":
        t = t * t
    elif e == "ease_in_out":
        t = (1 - math.cos(t * math.pi)) / 2
    return max(0.0, min(1.0, t))


def _step(t, steps):
    return int(t * steps) / steps


def style_color(style, color_a, color_b, t):
    """Interpolate color_a -> color_b honoring the style's color_curve."""
    st = merge_style(style)
    curve = st.get("color_curve", "continuous")
    if callable(curve):
        return curve(color_a, color_b, t)
    if curve == "cel":
        t = _step(t, 4)
    elif isinstance(curve, int):
        t = _step(t, max(1, curve))
    return tuple(int(color_a[i] + (color_b[i] - color_a[i]) * t) for i in range(3))


def shade_band(style, t):
    """Quantized progress for size/position curves (cel used 4 bands)."""
    st = merge_style(style)
    curve = st.get("color_curve", "continuous")
    if curve == "cel" or isinstance(curve, int):
        return _step(t, 4 if curve == "cel" else max(1, curve))
    return t


# ── Supersampling (anti-aliasing) ─────────────────────────────────────────

def aa_surface(size, style):
    """Returns (hi-res RGBA canvas, scale) so callers can draw at 2x+."""
    ss = max(1, int(merge_style(style).get("supersample", 2)))
    hi = size * ss
    return Image.new("RGBA", (hi, hi), (0, 0, 0, 0)), ss


def from_aa(hi_img, size, style):
    """Downscale an aa_surface() canvas back to the target size (LANCZOS)."""
    ss = max(1, int(merge_style(style).get("supersample", 2)))
    if ss <= 1:
        return hi_img
    return hi_img.resize((size, size), Image.LANCZOS)


def soft_edges(img, radius):
    """Feather only the alpha channel (keeps RGB crisp)."""
    if not radius:
        return img
    alpha = img.split()[3].filter(ImageFilter.GaussianBlur(radius))
    out = img.copy()
    out.putalpha(alpha)
    return out


# ── Post passes: enhance -> outline -> grain ──────────────────────────────

def _enhance(img, st):
    sat = st.get("saturation", 1.0)
    cont = st.get("contrast", 1.0)
    if sat == 1.0 and cont == 1.0:
        return img
    alpha_ch = img.split()[3]
    rgb = img.convert("RGB")
    if sat != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(sat)
    if cont != 1.0:
        rgb = ImageEnhance.Contrast(rgb).enhance(cont)
    out = rgb.convert("RGBA")
    out.putalpha(alpha_ch)
    return out


def _outline_pass(img, cfg):
    if not cfg:
        return img
    edges = img.convert("RGB").filter(ImageFilter.FIND_EDGES).convert("L")
    threshold = cfg.get("threshold", 32)
    mask = edges.point(lambda v: 255 if v > threshold else 0)
    color = cfg.get("color", (10, 8, 12))
    alpha = cfg.get("alpha", 200)
    stroke = Image.new("RGBA", img.size, (*color, alpha))
    return Image.composite(stroke, img, mask)


def _grain_pass(img, amount):
    if amount <= 0:
        return img
    a = img.split()[3]
    noise = Image.effect_noise(img.size, amount * 40)
    # shift noise upward so it can only add, then gate by the existing alpha
    # so fully transparent background pixels stay fully transparent.
    shifted = noise.point(lambda v: max(0, int(v * 0.5) + int(amount * 25)))
    with_noise = ImageChops.add(a, shifted, scale=1)
    combined = Image.composite(with_noise, a, a)
    out = img.copy()
    out.putalpha(combined)
    return out


def _volume_pass(img, cfg):
    """Painterly volume: give flat shapes a directional core/rim light so they
    stop reading as 'cut-out paper shapes glued together'.

    cfg keys (all optional):
      strength: 0..1  how strongly the volume light reads (default 0.5)
      direction: 'radial' | 'top' | 'bottom' | angle-in-degrees (default 'radial')
      core: 0..1  brightness boost toward the lit centre (default 0.35)
      rim: 0..1   darkness added toward the silhouette edge (default 0.2)

    Works on RGBA, keeps transparent background fully transparent.
    """
    st = merge_style(cfg) if False else cfg
    strength = float(cfg.get("strength", 0.5))
    core = float(cfg.get("core", 0.35))
    rim = float(cfg.get("rim", 0.2))
    direction = cfg.get("direction", "radial")

    rgb = img.split()[:3]
    alpha = img.split()[3]
    w, h = img.size

    nx, ny = 1.0 / max(1, w - 1), 1.0 / max(1, h - 1)

    # Distance field: 0 at the lit centre, 1 at the silhouette edge.
    dist = _silhouette_distance(alpha)
    # Light vector: falls off away from the light source.
    light = {
        "radial": lambda x, y: 1.0,
        "top": lambda x, y: y,
        "bottom": lambda x, y: 1.0 - y,
    }.get(direction)
    if light is None:
        angle = math.radians(float(direction))
        lx, ly = math.cos(angle), math.sin(angle)
        light = lambda x, y: max(0.0, 1.0 - (x * lx + y * ly))

    # Per-pixel lighting: lit core brightens, silhouette edge rims dark.
    def shade_pixels(ch_data):
        out = bytearray(w * h)
        i = 0
        for (x, y), v in zip(_iter_xy(w, h), ch_data):
            d = dist[i]
            l = light(x * nx, y * ny)
            out[i] = int(max(0, min(255, v * (1.0 + core * d - rim * (1 - d))
                                    * (1.0 - strength * (0.5 + 0.5 * l)))))
            i += 1
        return out

    shaded = [Image.frombytes("L", (w, h), bytes(shade_pixels(ch.getdata())))
              for ch in rgb]
    out = Image.merge("RGBA", (*shaded, alpha))
    return out


def _iter_xy(w, h):
    for y in range(h):
        for x in range(w):
            yield x, y


def _silhouette_distance(alpha, blur_radius=8.0):
    """Normalised distance from each opaque pixel to the alpha silhouette edge.

    Value 0 deep inside the shape (lit core), 1 at/outside the edge. Computed as
    alpha falloff so thin tendrils (flame licks) still get rim shading.
    """
    w, h = alpha.size
    falloff = alpha.filter(ImageFilter.GaussianBlur(blur_radius * 0.5))
    inv = ImageChops.invert(falloff).convert("L")
    d = [float(v) / 255.0 for v in inv.getdata()]
    # Invert so deep opacity (interior) -> 0, sparse/edge -> 1
    return [1.0 - v for v in d]


def apply_style_passes(img, style):
    """Run the style's post passes: volume -> enhance -> outline -> grain."""
    st = merge_style(style)
    if st.get("volume"):
        img = _volume_pass(img, st["volume"])
    img = _enhance(img, st)
    img = _outline_pass(img, st.get("outline"))
    img = _grain_pass(img, st.get("grain", 0.0))
    return img


def _bake_background(img, mode):
    """Bake a fully opaque black or white background into the frame.

    mode: 'black' | 'white' | 'auto'. 'auto' picks per-effect: bright/airy
    effects (water, dust) sit on white; vivid/dark ones (fire, lightning) sit
    on black. Returns an RGB image (alpha dropped).
    """
    if mode is None:
        mode = "auto"
    if mode == "auto":
        alpha = img.split()[3]
        rgb = img.convert("RGB")
        vals = [p[0] for p in rgb.getdata() if p != (0, 0, 0)]
        if not vals:
            mode = "black"
        else:
            mode = "white" if sum(vals) / len(vals) > 110 else "black"
    bg = (255, 255, 255) if mode == "white" else (0, 0, 0)
    base = Image.new("RGBA", img.size, bg + (255,))
    return Image.alpha_composite(base, img).convert("RGB")