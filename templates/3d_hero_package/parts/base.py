"""Plinth_Base subsystem builder."""

from __future__ import annotations

from asset_pipeline.scene3d import MeshGeometry
from geometry_math import make_revolved_solid


def build_plinth_base() -> MeshGeometry:
    profile = [
        [0.00, 0.00],
        [0.62, 0.00],
        [0.60, 0.14],
        [0.52, 0.18],
        [0.48, 0.40],
        [0.42, 0.45],
        [0.00, 0.45],
    ]
    return make_revolved_solid(profile, sections=8, color=[210, 214, 220, 255])
