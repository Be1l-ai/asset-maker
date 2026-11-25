"""Crystal_Core subsystem builder."""

from __future__ import annotations

from asset_pipeline.scene3d import MeshGeometry
from geometry_math import make_revolved_solid


def build_crystal_core() -> MeshGeometry:
    profile = [
        [0.00, 0.68],
        [0.24, 1.12],
        [0.18, 1.38],
        [0.00, 1.64],
    ]
    return make_revolved_solid(profile, sections=6, color=[116, 224, 246, 255])
