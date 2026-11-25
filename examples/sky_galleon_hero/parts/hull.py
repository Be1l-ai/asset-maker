"""Subsystem 1: High-res curved galleon hull, brass wales/keel, winged figurehead & stern gallery."""

from __future__ import annotations

import math
import numpy as np
from asset_pipeline.scene3d import MeshGeometry
from geometry_math import hull_beam_sheer_keel, make_box, make_curved_tube, make_tube, merge_geometries, signed_vol


def build_hull_subsystems() -> tuple[MeshGeometry, MeshGeometry, MeshGeometry]:
    # 1. High-res 32-station x 18-point parametric lofted hull (~2,100 tris)
    stations, prof = 32, 11
    ys = np.linspace(-3.4, 3.8, stations)
    verts = []
    ring_n = prof * 2 - 2
    for y in ys:
        t = float(np.clip((y + 3.4) / 7.2, 0.0, 1.0))
        beam, sheer, keel = hull_beam_sheer_keel(t)
        half = []
        for k in range(prof):
            u = k / (prof - 1)
            if u < 0.78:
                s = u / 0.78
                x = beam * (math.sin(s * math.pi * 0.5) ** 0.80)
                z = keel + (sheer - keel) * (s ** 1.30)
            else:
                s = (u - 0.78) / 0.22
                x = beam * (1.0 - s)
                z = sheer + 0.03 * (1.0 - (1.0 - s) ** 2)
            half.append((x, z))
        for x, z in list(half) + [(-x, z) for x, z in reversed(half[1:-1])]:
            verts.append([x, float(y), z])

    sc, bc = len(verts), len(verts) + 1
    verts.extend([[0.0, -3.4, 0.65], [0.0, 3.8, 1.15]])
    v = np.array(verts, dtype=np.float64)
    faces = []
    for s in range(ring_n):
        faces.append([sc, (s + 1) % ring_n, s])
    for i in range(stations - 1):
        for s in range(ring_n):
            s2 = (s + 1) % ring_n
            a, b, c, d = i * ring_n + s, i * ring_n + s2, (i + 1) * ring_n + s2, (i + 1) * ring_n + s
            faces.extend([[a, b, c], [a, c, d]])
    last = (stations - 1) * ring_n
    for s in range(ring_n):
        faces.append([bc, last + s, last + (s + 1) % ring_n])
    f = np.array(faces, dtype=np.int32)
    if signed_vol(v, f) < 0:
        f = f[:, [0, 2, 1]]

    hull_parts = [MeshGeometry(v, f, np.tile(np.array([224, 214, 206, 255], dtype=np.uint8), (len(f), 1)))]
    # Stern cabin overhang & rudder
    hull_parts.append(make_box([0.0, -3.35, 1.65], [1.45, 0.75, 0.95], [198, 184, 174, 255]))
    hull_parts.append(make_box([0.0, -3.55, 0.15], [0.16, 0.65, 1.15], [138, 96, 68, 255]))

    # 2. Golden brass keel, twin curved rub-rails (wales), stern taffrail crest & winged figurehead!
    brass = [234, 192, 84, 255]
    brass_parts = []
    keel_pts = [[0.0, float(y), hull_beam_sheer_keel((y + 3.4) / 7.2)[2] - 0.04] for y in np.linspace(-3.3, 3.65, 20)] + [[0.0, 3.82, 0.22], [0.0, 3.96, 0.68], [0.0, 4.02, 1.15]]
    brass_parts.append(make_curved_tube(keel_pts, [0.10] * len(keel_pts), 8, brass))

    for side in (-1.0, 1.0):
        for z_off, rad in [(0.02, 0.075), (-0.42, 0.055)]:
            rail_pts = []
            for y in np.linspace(-3.35, 3.70, 22):
                b, sh, _ = hull_beam_sheer_keel((y + 3.4) / 7.2)
                rail_pts.append([side * (b + 0.03), float(y), sh + z_off])
            brass_parts.append(make_curved_tube(rail_pts, [rad] * len(rail_pts), 8, brass))

    # Winged golden figurehead sweeping back along prow (matching concept.jpg!)
    brass_parts.append(make_tube([0.0, 3.72, 0.78], [0.0, 4.18, 1.38], 0.18, 0.12, 10, brass))
    for side in (-1.0, 1.0):
        for fi in range(3):
            wing_pts = [
                [side * 0.14, 3.92, 1.24 - fi * 0.14],
                [side * (0.48 + fi * 0.05), 3.35, 1.32 - fi * 0.16],
                [side * (0.72 + fi * 0.04), 2.55, 1.18 - fi * 0.18],
            ]
            brass_parts.append(make_curved_tube(wing_pts, [0.09, 0.07, 0.03], 7, brass))

    # Ornate curved stern taffrail arch
    taff_pts = [[0.82 * math.cos(a), -3.55, 2.15 + 0.42 * math.sin(a)] for a in np.linspace(0.0, math.pi, 13)]
    brass_parts.append(make_curved_tube(taff_pts, [0.075] * len(taff_pts), 8, brass))

    # 3. Glowing arched captain's stern cabin windows (port, starboard, and rear!)
    amber = [255, 206, 94, 255]
    win_parts = []
    for side in (-1.0, 1.0):
        for wy in (-3.10, -3.38, -3.62):
            win_parts.append(make_box([side * 0.76, wy, 1.48], [0.08, 0.20, 0.36], amber))
    for wx in (-0.42, 0.0, 0.42):
        win_parts.append(make_box([wx, -3.74, 1.52], [0.24, 0.08, 0.38], amber))

    for side in (-1.0, 1.0):
        for wy in (-3.10, -3.38, -3.62):
            brass_parts.append(make_box([side * 0.78, wy, 1.48], [0.04, 0.24, 0.04], [92, 62, 42, 255]))
            brass_parts.append(make_box([side * 0.78, wy, 1.67], [0.05, 0.24, 0.05], brass))
    for side in (-1.0, 1.0):
        for py in (-1.2, -0.2, 0.8, 1.8):
            b, sh, _ = hull_beam_sheer_keel((py + 3.4) / 7.2)
            brass_parts.append(make_tube([side * (b - 0.04), py, sh - 0.22], [side * (b + 0.14), py, sh - 0.22], 0.11, 0.10, 8, brass))
    return merge_geometries(hull_parts), merge_geometries(brass_parts), merge_geometries(win_parts)
