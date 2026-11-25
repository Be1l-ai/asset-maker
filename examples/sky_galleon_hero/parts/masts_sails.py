"""Subsystem 3: Three masts, yardarms, bowsprit, crow's nests, and 7 billowing painted sails."""

from __future__ import annotations

import numpy as np
from asset_pipeline.scene3d import MeshGeometry
from geometry_math import make_billowing_quad_sail, make_box, make_triangular_sail, make_tube, merge_geometries


def build_masts_and_sails() -> tuple[MeshGeometry, MeshGeometry, MeshGeometry, MeshGeometry]:
    wood = [196, 178, 162, 255]
    # 1. Masts, yardarms, crow's nests, and sweeping angled bowsprit
    masts = [
        # Main mast (center, tallest)
        make_tube([0.0,  0.15, 1.00], [0.0,  0.15, 6.25], 0.14, 0.055, 12, wood),
        make_tube([-1.85, 0.25, 2.15], [1.85, 0.25, 2.15], 0.055, 0.055, 8, wood),
        make_tube([-1.75, 0.25, 4.15], [1.75, 0.25, 4.15], 0.050, 0.050, 8, wood),
        make_tube([-1.30, 0.25, 5.75], [1.30, 0.25, 5.75], 0.042, 0.042, 8, wood),
        make_tube([0.0,  0.15, 4.28], [0.0,  0.15, 4.55], 0.34, 0.38, 12, wood),  # main crow's nest
        # Fore mast
        make_tube([0.0,  2.15, 1.15], [0.0,  2.15, 5.55], 0.12, 0.048, 12, wood),
        make_tube([-1.45, 2.24, 2.20], [1.45, 2.24, 2.20], 0.048, 0.048, 8, wood),
        make_tube([-1.35, 2.24, 3.85], [1.35, 2.24, 3.85], 0.044, 0.044, 8, wood),
        make_tube([-1.05, 2.24, 5.15], [1.05, 2.24, 5.15], 0.036, 0.036, 8, wood),
        # Mizzen mast + angled gaff spar
        make_tube([0.0, -1.95, 1.75], [0.0, -1.95, 5.05], 0.10, 0.042, 10, wood),
        make_tube([0.0, -1.95, 3.45], [0.0, -3.55, 4.55], 0.046, 0.030, 8, wood),
        make_tube([0.0, -1.95, 2.15], [0.0, -3.65, 2.25], 0.046, 0.034, 8, wood),
        # Long sweeping bowsprit
        make_tube([0.0,  3.35, 1.48], [0.0,  6.45, 2.52], 0.11, 0.042, 10, wood),
    ]

    # 2. Main Emblem Sail (huge hero sail with teal/gold winged compass emblem!)
    main_sail = make_billowing_quad_sail([0.0, 0.32, 3.16], w_top=3.05, w_bot=3.35, height=1.88, billow=0.58, nx=14, nz=14)

    # 3. Upper Main Sail + Fore Lower & Fore Upper Racing Sails
    square_sails = merge_geometries([
        make_billowing_quad_sail([0.0, 0.30, 4.96], w_top=2.25, w_bot=2.75, height=1.42, billow=0.44, nx=12, nz=12),
        make_billowing_quad_sail([0.0, 2.30, 3.04], w_top=2.35, w_bot=2.65, height=1.54, billow=0.48, nx=12, nz=12),
        make_billowing_quad_sail([0.0, 2.28, 4.52], w_top=1.75, w_bot=2.15, height=1.18, billow=0.36, nx=11, nz=11),
    ])

    # 4. Twin Triangular Bowsprit Jib Sails + Mizzen Spanker Sail!
    tri_sails = merge_geometries([
        make_triangular_sail([0.0, 2.18, 5.15], [0.0, 6.28, 2.48], [0.0, 3.95, 1.85], billow_x=0.38, steps=10),
        make_triangular_sail([0.0, 2.18, 4.35], [0.0, 4.85, 2.02], [0.0, 3.15, 1.62], billow_x=0.30, steps=9),
        make_triangular_sail([0.0, -3.50, 4.50], [0.0, -1.98, 2.18], [0.0, -3.58, 2.26], billow_x=0.28, steps=9),
    ])

    return merge_geometries(masts), main_sail, square_sails, tri_sails
