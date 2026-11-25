"""High-craft procedural sculpting & kitbash primitives for 3D hero assets.

Provides curved, beveled, and parametric geometry builders so agents never need
to fall back to raw boxes and straight cylinders:
- ``catmull_rom_points`` & ``catmull_rom_tube`` (scrollwork, ropes, tails, pipes, trim)
- ``extrude_beveled_2d`` (chamfered brackets, dorsal fins, shields, arched frames, figureheads)
- ``loft_cross_sections`` (curved ship hulls, dresses, organic limbs, fuselages)
- ``catenary_cloth`` (split-normal double-sided billowing sails, capes, banners with planar UVs)
- ``array_along_curve`` (even placement of rivets, balusters, bells, ratlines along any 3D curve)
"""

from __future__ import annotations

import math
from typing import Callable, List, Sequence, Tuple
import numpy as np

from .scene3d import MeshGeometry, _compute_smooth_normals, _normalize


def _signed_volume(v: np.ndarray, f: np.ndarray) -> float:
    return float(np.sum(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]]))) / 6.0)


def merge_parts(items: Sequence[MeshGeometry]) -> MeshGeometry:
    """Merge multiple ``MeshGeometry`` pieces while preserving smooth normals and UVs."""
    vs, fs, cs, ns, uvs = [], [], [], [], []
    has_uv = all(g.uvs is not None for g in items)
    off = 0
    for g in items:
        vs.append(g.vertices)
        fs.append(g.faces + off)
        cs.append(g.face_colors)
        ns.append(g.vertex_normals if g.vertex_normals is not None else _compute_smooth_normals(g.vertices, g.faces))
        if has_uv:
            uvs.append(g.uvs)
        off += len(g.vertices)
    return MeshGeometry(
        vertices=np.vstack(vs),
        faces=np.vstack(fs),
        face_colors=np.vstack(cs),
        vertex_normals=np.vstack(ns),
        uvs=np.vstack(uvs) if has_uv else None,
    )


def catmull_rom_points(control_pts: Sequence[Sequence[float]], samples_per_seg: int = 8) -> np.ndarray:
    """Evaluate a smooth centripetal-style Catmull-Rom 3D spline through ``control_pts``."""
    pts = np.asarray(control_pts, dtype=np.float64)
    if len(pts) < 2:
        raise ValueError("catmull_rom_points requires at least 2 control points")
    if len(pts) == 2:
        ts = np.linspace(0.0, 1.0, samples_per_seg + 1)[:, None]
        return pts[0] * (1.0 - ts) + pts[1] * ts

    # Pad endpoints linearly so the spline passes cleanly through first and last points
    p_ext = np.vstack([2.0 * pts[0] - pts[1], pts, 2.0 * pts[-1] - pts[-2]])
    out = []
    for i in range(1, len(p_ext) - 2):
        p0, p1, p2, p3 = p_ext[i - 1], p_ext[i], p_ext[i + 1], p_ext[i + 2]
        steps = samples_per_seg if i < len(p_ext) - 3 else samples_per_seg + 1
        for k in range(steps):
            t = k / samples_per_seg
            t2, t3 = t * t, t * t * t
            pt = 0.5 * (
                (2.0 * p1)
                + (-p0 + p2) * t
                + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
            )
            out.append(pt)
    return np.asarray(out, dtype=np.float64)


def catmull_rom_tube(
    control_pts: Sequence[Sequence[float]],
    radii: float | Sequence[float] = 0.05,
    sections: int = 10,
    samples_per_seg: int = 6,
    color: Sequence[int] = (200, 180, 140, 255),
) -> MeshGeometry:
    """Sweep a watertight, parallel-transported tapered tube along a 3D Catmull-Rom spline."""
    spine = catmull_rom_points(control_pts, samples_per_seg=samples_per_seg)
    n = len(spine)
    if isinstance(radii, (int, float)):
        r_arr = np.full(n, float(radii), dtype=np.float64)
    else:
        r_in = np.asarray(radii, dtype=np.float64)
        r_arr = np.interp(np.linspace(0.0, 1.0, n), np.linspace(0.0, 1.0, len(r_in)), r_in)

    tang = np.zeros_like(spine)
    tang[0] = spine[1] - spine[0]
    tang[-1] = spine[-1] - spine[-2]
    for i in range(1, n - 1):
        tang[i] = spine[i + 1] - spine[i - 1]
    tang = _normalize(tang)

    ref = np.array([1.0, 0.0, 0.0]) if abs(tang[0, 0]) < 0.8 else np.array([0.0, 1.0, 0.0])
    cur_n = _normalize(np.cross(tang[0], ref))
    rings = []
    for i in range(n):
        if i > 0:
            v = np.cross(tang[i - 1], tang[i])
            s = float(np.linalg.norm(v))
            c = float(np.dot(tang[i - 1], tang[i]))
            if s > 1e-9:
                k = v / s
                ang = math.atan2(s, np.clip(c, -1.0, 1.0))
                cur_n = _normalize(cur_n * math.cos(ang) + np.cross(k, cur_n) * math.sin(ang) + k * np.dot(k, cur_n) * (1.0 - math.cos(ang)))
        bn = np.cross(tang[i], cur_n)
        ring = [
            spine[i] + r_arr[i] * (math.cos(2.0 * math.pi * j / sections) * cur_n + math.sin(2.0 * math.pi * j / sections) * bn)
            for j in range(sections)
        ]
        rings.append(ring)
    return loft_cross_sections(rings, close_ends=True, color=color)


def loft_cross_sections(
    rings_3d: Sequence[Sequence[Sequence[float]]],
    close_ends: bool = True,
    color: Sequence[int] = (180, 185, 195, 255),
) -> MeshGeometry:
    """Loft a smooth surface across a sequence of matching 3D cross-section rings."""
    rings = np.asarray(rings_3d, dtype=np.float64)
    if rings.ndim != 3 or rings.shape[0] < 2 or rings.shape[1] < 3:
        raise ValueError(f"rings_3d must have shape (R>=2, S>=3, 3), got {rings.shape}")
    n_r, n_s, _ = rings.shape
    verts = list(rings.reshape(-1, 3))
    faces: List[Tuple[int, int, int]] = []

    for r in range(n_r - 1):
        for s in range(n_s):
            s2 = (s + 1) % n_s
            a, b = r * n_s + s, r * n_s + s2
            c, d = (r + 1) * n_s + s2, (r + 1) * n_s + s
            faces.append((a, b, c))
            faces.append((a, c, d))

    if close_ends:
        c0 = len(verts)
        verts.append(rings[0].mean(axis=0))
        c1 = len(verts)
        verts.append(rings[-1].mean(axis=0))
        for s in range(n_s):
            s2 = (s + 1) % n_s
            faces.append((c0, s2, s))
            faces.append((c1, (n_r - 1) * n_s + s, (n_r - 1) * n_s + s2))

    v = np.asarray(verts, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int32)
    if close_ends and _signed_volume(v, f) < 0:
        f = f[:, [0, 2, 1]]
    return MeshGeometry(v, f, np.tile(np.array(color, dtype=np.uint8), (len(f), 1)))


def extrude_beveled_2d(
    polygon_2d: Sequence[Sequence[float]],
    depth: float = 0.20,
    bevel: float = 0.03,
    bevel_steps: int = 2,
    color: Sequence[int] = (210, 178, 92, 255),
) -> MeshGeometry:
    """Extrude a convex/star-shaped 2D XY polygon along Z with symmetric chamfered bevels."""
    pts = np.asarray(polygon_2d, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 3:
        raise ValueError("polygon_2d must have shape (N>=3, 2)")
    center = pts.mean(axis=0)
    rel = pts - center[None, :]
    b = min(float(bevel), depth * 0.45)

    # Build bevelled Z stations from -depth/2 to +depth/2
    stations: List[Tuple[float, float]] = []
    for k in range(bevel_steps + 1):
        ang = (math.pi * 0.5) * (k / max(1, bevel_steps))
        z = -depth * 0.5 + b * (1.0 - math.cos(ang))
        scale = 1.0 - (1.0 - math.sin(ang)) * min(0.22, b * 1.4)
        stations.append((z, scale))
    for k in range(bevel_steps, -1, -1):
        ang = (math.pi * 0.5) * (k / max(1, bevel_steps))
        z = depth * 0.5 - b * (1.0 - math.cos(ang))
        scale = 1.0 - (1.0 - math.sin(ang)) * min(0.22, b * 1.4)
        stations.append((z, scale))

    rings = []
    for z, sc in stations:
        xy = center[None, :] + rel * sc
        rings.append(np.column_stack([xy, np.full(len(pts), z)]))
    return loft_cross_sections(rings, close_ends=True, color=color)


def catenary_cloth(
    center: Sequence[float],
    w_top: float,
    w_bot: float,
    height: float,
    billow: float = 0.35,
    nx: int = 12,
    nz: int = 12,
    color: Sequence[int] = (255, 255, 255, 255),
) -> MeshGeometry:
    """Double-sided billowing cloth/sail mesh with split opposing normals and [0..1] planar UVs."""
    cx, cy, cz = center
    verts, uvs = [], []
    for iz in range(nz):
        vz = iz / (nz - 1)
        w = w_bot + (w_top - w_bot) * vz
        arch = 0.10 * height * (1.0 - vz)
        for ix in range(nx):
            ux = ix / (nx - 1)
            x = cx + (ux - 0.5) * w
            by = billow * math.sin(math.pi * vz) * (0.35 + 0.65 * math.sin(math.pi * ux))
            z = cz + (vz - 0.5) * height + arch * math.sin(math.pi * ux)
            verts.append([x, cy + by, z])
            uvs.append([ux, 1.0 - vz])

    v_f = np.asarray(verts, dtype=np.float64)
    uv_f = np.asarray(uvs, dtype=np.float32)
    nf = len(v_f)
    ff, fb = [], []
    for iz in range(nz - 1):
        for ix in range(nx - 1):
            a, b, c, d = iz * nx + ix, iz * nx + ix + 1, (iz + 1) * nx + ix + 1, (iz + 1) * nx + ix
            ff.extend([[a, b, c], [a, c, d]])
            fb.extend([[a + nf, c + nf, b + nf], [a + nf, d + nf, c + nf]])
    ff_arr, fb_arr = np.asarray(ff, dtype=np.int32), np.asarray(fb, dtype=np.int32)
    vn_f = _compute_smooth_normals(v_f, ff_arr)
    v_all = np.vstack([v_f, v_f])
    vn_all = np.vstack([vn_f, -vn_f])
    uv_all = np.vstack([uv_f, uv_f])
    f_all = np.vstack([ff_arr, fb_arr])
    return MeshGeometry(v_all, f_all, np.tile(np.array(color, dtype=np.uint8), (len(f_all), 1)), vertex_normals=vn_all, uvs=uv_all)


def array_along_curve(
    control_pts: Sequence[Sequence[float]],
    count: int,
    builder_fn: Callable[[np.ndarray, np.ndarray, int], MeshGeometry],
) -> MeshGeometry:
    """Place repeated details (rivets, balusters, bells, brackets) evenly along a 3D Catmull-Rom curve."""
    dense = catmull_rom_points(control_pts, samples_per_seg=16)
    seg_lens = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_lens)])
    total = max(float(cum[-1]), 1e-6)
    targets = np.linspace(0.0, total, max(2, count))
    items: List[MeshGeometry] = []
    for idx, dist in enumerate(targets):
        pos = np.array([np.interp(dist, cum, dense[:, ax]) for ax in range(3)], dtype=np.float64)
        d2 = min(total, dist + total * 0.01)
        pos2 = np.array([np.interp(d2, cum, dense[:, ax]) for ax in range(3)], dtype=np.float64)
        tang = _normalize(pos2 - pos) if np.linalg.norm(pos2 - pos) > 1e-9 else np.array([0.0, 1.0, 0.0])
        items.append(builder_fn(pos, tang, idx))
    return merge_parts(items)
