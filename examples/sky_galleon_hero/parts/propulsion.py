"""Subsystem 5: Twin port/starboard aether-jet turbines, dorsal fins, brass rings & 3 stern lanterns."""

from __future__ import annotations

import numpy as np
from asset_pipeline.scene3d import MeshGeometry
from geometry_math import hull_beam_sheer_keel, make_box, make_tube, merge_geometries


def build_propulsion_and_lanterns() -> tuple[MeshGeometry, MeshGeometry, MeshGeometry, MeshGeometry, MeshGeometry]:
    iron = [64, 72, 86, 255]
    brass = [234, 192, 84, 255]
    cyan = [84, 236, 255, 255]
    amber = [255, 212, 102, 255]

    nacelles, rings, cores, l_frames, l_flames = [], [], [], [], []

    # 2 side jet turbines per side (4 total!) matching concept.jpg
    for side in (-1.0, 1.0):
        for ty, tz, rad in [(-0.45, 0.12, 0.34), (-2.15, 0.32, 0.31)]:
            beam, _, _ = hull_beam_sheer_keel((ty + 3.4) / 7.2)
            tx = side * (beam + rad * 0.72)
            # Intake cone, main iron barrel, exhaust bell & hull pylon strut
            nacelles.append(make_tube([tx, ty + 0.62, tz], [tx, ty + 0.42, tz], rad * 0.75, rad * 1.02, 14, iron))
            nacelles.append(make_tube([tx, ty + 0.42, tz], [tx, ty - 0.58, tz], rad * 1.02, rad * 0.96, 14, iron))
            nacelles.append(make_tube([tx, ty - 0.58, tz], [tx, ty - 0.82, tz], rad * 0.96, rad * 0.78, 14, iron))
            nacelles.append(make_box([side * (beam - 0.05), ty, tz + 0.04], [rad * 1.6, 0.72, 0.22], iron))
            # Swept dorsal stabilizer fin on top of each turbine
            nacelles.append(make_box([tx, ty - 0.08, tz + rad + 0.14], [0.09, 0.56, 0.34], iron))
            # Twin burnished brass compression rings around barrel + intake nosecone
            rings.append(make_tube([tx, ty + 0.44, tz], [tx, ty + 0.32, tz], rad * 1.09, rad * 1.09, 14, brass))
            rings.append(make_tube([tx, ty - 0.48, tz], [tx, ty - 0.60, tz], rad * 1.05, rad * 1.05, 14, brass))
            rings.append(make_tube([tx, ty + 0.60, tz], [tx, ty + 0.76, tz], rad * 0.38, 0.06, 10, brass))
            # Glowing cyan aether thruster exhaust core + plume cone!
            cores.append(make_tube([tx, ty - 0.76, tz], [tx, ty - 1.18, tz], rad * 0.62, rad * 0.18, 12, cyan))

    # 3 ornate glowing golden stern lanterns along the curved taffrail
    for lx, lz in [(-0.56, 2.48), (0.0, 2.66), (0.56, 2.48)]:
        ly = -3.55
        l_frames.append(make_tube([lx, ly, lz - 0.24], [lx, ly, lz - 0.02], 0.04, 0.04, 6, brass))
        l_frames.append(make_tube([lx, ly, lz + 0.26], [lx, ly, lz + 0.42], 0.16, 0.03, 8, brass))
        l_frames.append(make_box([lx, ly, lz - 0.02], [0.22, 0.22, 0.05], brass))
        l_flames.append(make_tube([lx, ly, lz], [lx, ly, lz + 0.26], 0.11, 0.13, 8, amber))

    return merge_geometries(nacelles), merge_geometries(rings), merge_geometries(cores), merge_geometries(l_frames), merge_geometries(l_flames)
