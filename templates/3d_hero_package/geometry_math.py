"""Reusable procedural 3D math primitives for this hero asset package."""

from __future__ import annotations

import math
from typing import Sequence
import numpy as np
from asset_pipeline.scene3d import MeshGeometry


def _signed_vol(v: np.ndarray, f: np.ndarray) -> float:
    return float(np.sum(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]]))) / 6.0)


def make_revolved_solid(profile_rz: Sequence[Sequence[float]], sections: int, color: Sequence[int]) -> MeshGeometry:
    """Revolve a closed [radius, z] profile around Z into a watertight solid."""
    pts = list(profile_rz)
    if pts[0][0] != 0.0:
        pts.insert(0, [0.0, pts[0][1]])
    if pts[-1][0] != 0.0:
        pts.append([0.0, pts[-1][1]])

    verts = [[0.0, 0.0, float(pts[0][1])]]
    ring_pts = pts[1:-1]
    for r, z in ring_pts:
        for s in range(sections):
            a = 2.0 * math.pi * s / sections
            verts.append([float(r) * math.cos(a), float(r) * math.sin(a), float(z)])
    top_idx = len(verts)
    verts.append([0.0, 0.0, float(pts[-1][1])])

    v = np.array(verts, dtype=np.float64)
    def ridx(ring: int, sec: int) -> int:
        return 1 + ring * sections + (sec % sections)

    faces = []
    for s in range(sections):
        faces.append([0, ridx(0, s + 1), ridx(0, s)])
    for r in range(len(ring_pts) - 1):
        for s in range(sections):
            a, b = ridx(r, s), ridx(r, s + 1)
            c, d = ridx(r + 1, s + 1), ridx(r + 1, s)
            faces.append([a, b, c])
            faces.append([a, c, d])
    for s in range(sections):
        faces.append([top_idx, ridx(len(ring_pts) - 1, s), ridx(len(ring_pts) - 1, s + 1)])

    f = np.array(faces, dtype=np.int32)
    if _signed_vol(v, f) < 0:
        f = f[:, [0, 2, 1]]
    fc = np.tile(np.array(color, dtype=np.uint8), (len(f), 1))
    return MeshGeometry(vertices=v, faces=f, face_colors=fc)


def make_box(center: Sequence[float], extents: Sequence[float], color: Sequence[int]) -> MeshGeometry:
    """Create a watertight axis-aligned box centered at ``center``."""
    hx, hy, hz = extents[0] * 0.5, extents[1] * 0.5, extents[2] * 0.5
    v = np.array([
        [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
        [-hx, -hy,  hz], [hx, -hy,  hz], [hx, hy,  hz], [-hx, hy,  hz],
    ], dtype=np.float64) + np.asarray(center, dtype=np.float64)
    f = np.array([
        [0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
        [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5],
    ], dtype=np.int32)
    return MeshGeometry(vertices=v, faces=f, face_colors=np.tile(np.array(color, dtype=np.uint8), (len(f), 1)))


def merge_geometries(items: Sequence[MeshGeometry]) -> MeshGeometry:
    """Combine multiple MeshGeometry objects belonging to one named part."""
    vs, fs, cs = [], [], []
    off = 0
    for g in items:
        vs.append(g.vertices)
        fs.append(g.faces + off)
        cs.append(g.face_colors)
        off += len(g.vertices)
    return MeshGeometry(vertices=np.vstack(vs), faces=np.vstack(fs), face_colors=np.vstack(cs))
