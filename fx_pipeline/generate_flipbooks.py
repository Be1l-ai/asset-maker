#!/usr/bin/env python3
"""
generate_flipbooks.py — demo runner for the style-driven flipbook pipeline.

Renders the four classic effects (fireball, lightning, waterfall, dust)
in multiple artstyles to prove the style architecture works end-to-end.

The styles below are EXAMPLES of how to define a style, not locked presets:
copy one into your generator and tweak keys — see helpers/artstyles.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers.flipbook_effects import (build_flipbook, fireball_frame,
                                      lightning_frame, waterfall_frame, dust_frame)
from helpers.artstyles import STYLE_CEL

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "flipbooks")


# ── Example styles (artstyle versatility proof) ──────────────

# Baseline: byte-for-byte the old hard-coded cel look.
EXAMPLE_CEL = STYLE_CEL

# Soft painterly: soft volume light, feathered edges, dither to kill banding.
EXAMPLE_PAINTERLY = {
    "name": "painterly",
    "color_curve": "continuous",
    "alpha_mode": "soft",
    "edge_softness": 1.5,
    "easing": "ease_out",
    "grain": 0.12,
    "saturation": 1.12,
    "volume": {"strength": 0.45, "core": 0.4, "rim": 0.25, "direction": "top"},
    "background": "auto",
}

# Neon: strong bloom, exponential glow falloff, deeper radial volume rims.
EXAMPLE_NEON = {
    "name": "neon",
    "color_curve": "continuous",
    "alpha_mode": "soft",
    "edge_softness": 0.8,
    "easing": "ease_in_out",
    "glow_intensity": 1.7,
    "glow_falloff": "exponential",
    "saturation": 1.3,
    "contrast": 1.15,
    "volume": {"strength": 0.6, "core": 0.35, "rim": 0.4, "direction": "radial"},
    "background": "auto",
}


# ── Effect table: (name, frame_fn, style, seamless, background) ──
# background: 'black' / 'white' / 'auto' baked OPAQUE card per effect
# (cel keeps transparency for back-compat).

EFFECTS = [
    ("fireball_cel",        fireball_frame,    EXAMPLE_CEL,       False, "black"),
    ("fireball_painterly",  fireball_frame,    EXAMPLE_PAINTERLY, False, "black"),
    ("fireball_neon",       fireball_frame,    EXAMPLE_NEON,      False, "black"),
    ("lightning_cel",       lightning_frame,   EXAMPLE_CEL,       False, "black"),
    ("lightning_neon",      lightning_frame,   EXAMPLE_NEON,      False, "black"),
    ("waterfall_cel",       waterfall_frame,   EXAMPLE_CEL,       True,  "white"),
    ("waterfall_painterly", waterfall_frame,   EXAMPLE_PAINTERLY, True,  "white"),
    ("waterfall_neon",      waterfall_frame,   EXAMPLE_NEON,      True,  "white"),
    ("dust_cel",            dust_frame,        EXAMPLE_CEL,       True,  "white"),
    ("dust_painterly",      dust_frame,        EXAMPLE_PAINTERLY, True,  "white"),
    ("dust_neon",           dust_frame,        EXAMPLE_NEON,      True,  "white"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    print(f"Rendering {len(EFFECTS)} flipbooks -> {OUT}/")
    for idx, (name, fn, style, seamless, background) in enumerate(EFFECTS, 1):
        print(f"[{idx}/{len(EFFECTS)}] {name}")
        build_flipbook(name, fn, style, OUT, seed=7 * idx, seamless=seamless,
                       background=background)
    print("Done.")


if __name__ == "__main__":
    main()