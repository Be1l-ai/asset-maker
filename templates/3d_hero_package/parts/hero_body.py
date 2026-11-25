"""Timber_Frame subsystem builder."""

from __future__ import annotations

from asset_pipeline.scene3d import MeshGeometry
from geometry_math import make_box, merge_geometries


def build_timber_frame() -> MeshGeometry:
    posts = []
    for sx in (-0.36, 0.36):
        for sy in (-0.36, 0.36):
            posts.append(make_box([sx, sy, 1.02], [0.11, 0.11, 1.18], [218, 198, 178, 255]))
    # Top lintel ring
    posts.append(make_box([0.0,  0.36, 1.62], [0.86, 0.12, 0.12], [214, 192, 172, 255]))
    posts.append(make_box([0.0, -0.36, 1.62], [0.86, 0.12, 0.12], [214, 192, 172, 255]))
    posts.append(make_box([ 0.36, 0.0, 1.62], [0.12, 0.84, 0.12], [214, 192, 172, 255]))
    posts.append(make_box([-0.36, 0.0, 1.62], [0.12, 0.84, 0.12], [214, 192, 172, 255]))
    return merge_geometries(posts)
