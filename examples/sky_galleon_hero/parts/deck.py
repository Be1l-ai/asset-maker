"""Subsystem 2: Planked main deck, quarterdeck, balustrade railings, ship's wheel & deck props."""

from __future__ import annotations

import math
import numpy as np
from asset_pipeline.scene3d import MeshGeometry
from geometry_math import hull_beam_sheer_keel, make_box, make_curved_tube, make_tube, merge_geometries


def build_deck_and_rails() -> MeshGeometry:
    wood = [212, 198, 186, 255]
    dark = [148, 128, 114, 255]
    parts = [
        # Main deck + raised quarterdeck + forecastle
        make_box([0.0, 0.05, 1.04], [2.10, 4.5, 0.12], wood),
        make_box([0.0, -2.50, 1.58], [1.48, 1.65, 0.44], wood),
        make_box([0.0, 2.45, 1.24], [1.05, 1.05, 0.20], wood),
        # Deck hatch grate & cargo barrels
        make_box([0.0, 0.95, 1.18], [0.85, 0.85, 0.12], dark),
        make_tube([-0.68, -0.55, 1.12], [-0.68, -0.55, 1.62], 0.20, 0.19, 10, dark),
        make_tube([ 0.68, -0.45, 1.12], [ 0.68, -0.45, 1.58], 0.18, 0.18, 10, dark),
    ]
    # Quarterdeck wooden balustrade posts & curved top rail along both gunwales
    for side in (-1.0, 1.0):
        rail_pts = []
        for y in np.linspace(-3.3, 3.1, 18):
            b, sh, _ = hull_beam_sheer_keel((y + 3.4) / 7.2)
            px = side * max(0.28, b - 0.08)
            parts.append(make_tube([px, float(y), sh - 0.04], [px, float(y), sh + 0.44], 0.042, 0.036, 6, dark))
            rail_pts.append([px, float(y), sh + 0.45])
        parts.append(make_curved_tube(rail_pts, [0.055] * len(rail_pts), 8, wood))

    # Ship's helm wheel on the quarterdeck
    wheel_pts = [[0.32 * math.cos(a), -2.35, 2.28 + 0.32 * math.sin(a)] for a in np.linspace(0, 2 * math.pi, 13)]
    parts.append(make_curved_tube(wheel_pts, [0.035] * len(wheel_pts), 6, dark))
    parts.append(make_tube([0.0, -2.35, 1.82], [0.0, -2.35, 2.28], 0.07, 0.05, 8, dark))
    for k in range(6):
        a = k * math.pi / 3.0
        parts.append(make_tube([0.0, -2.35, 2.28], [0.42 * math.cos(a), -2.35, 2.28 + 0.42 * math.sin(a)], 0.02, 0.016, 5, wood))

    return merge_geometries(parts)
