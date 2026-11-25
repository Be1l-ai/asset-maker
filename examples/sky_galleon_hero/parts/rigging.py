"""Subsystem 4: Taut stays, shrouds, and full rope ratline ladders."""

from __future__ import annotations

import numpy as np
from asset_pipeline.scene3d import MeshGeometry
from geometry_math import make_tube, merge_geometries


def build_rigging_and_ratlines() -> MeshGeometry:
    rope = [164, 138, 108, 255]
    parts = [
        # Forestays, jib stays & backstays
        make_tube([0.0, 2.15, 5.40], [0.0, 6.38, 2.50], 0.020, 0.020, 5, rope),
        make_tube([0.0, 2.15, 4.40], [0.0, 4.95, 2.04], 0.018, 0.018, 5, rope),
        make_tube([0.0, 0.15, 6.10], [0.0, 2.15, 5.40], 0.020, 0.020, 5, rope),
        make_tube([0.0, 0.15, 6.10], [0.0, -1.95, 4.95], 0.020, 0.020, 5, rope),
        make_tube([0.0, -1.95, 4.95], [0.0, -3.52, 2.38], 0.018, 0.018, 5, rope),
        # Bowsprit bobstay under prow
        make_tube([0.0, 6.38, 2.48], [0.0, 3.72, 0.86], 0.022, 0.022, 5, rope),
    ]

    # Full rope ratline ladders on both sides of Fore, Main, and Mizzen masts!
    for my, z_bot, z_top, x_bot in [(2.15, 1.38, 4.10, 1.15), (0.15, 1.25, 4.35, 1.36), (-1.95, 1.75, 4.05, 0.98)]:
        for side in (-1.0, 1.0):
            # 3 vertical shroud ropes fanning from hull chainplates to masthead
            s_top = np.array([side * 0.18, my, z_top])
            p_fore = np.array([side * x_bot, my + 0.34, z_bot])
            p_mid  = np.array([side * x_bot, my,        z_bot])
            p_aft  = np.array([side * x_bot, my - 0.34, z_bot])
            for pb in (p_fore, p_mid, p_aft):
                parts.append(make_tube(pb, s_top, 0.016, 0.014, 4, rope))
            # 10 horizontal ratline ladder rungs!
            for r_i in range(1, 10):
                u = r_i / 10.5
                a = p_fore * (1.0 - u) + s_top * u
                b = p_aft  * (1.0 - u) + s_top * u
                parts.append(make_tube(a, b, 0.011, 0.011, 4, rope))

    return merge_geometries(parts)
