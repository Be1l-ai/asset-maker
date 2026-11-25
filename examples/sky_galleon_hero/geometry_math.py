"""High-craft parametric lofting, catenary/triangular sails, rings, and tube sweeps."""

from __future__ import annotations

import math
from typing import Sequence
import numpy as np
from asset_pipeline.scene3d import MeshGeometry


def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n < 1e-12, 1.0, n)


def signed_vol(v: np.ndarray, f: np.ndarray) -> float:
    return float(np.sum(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]]))) / 6.0)


def smooth_normals(v: np.ndarray, f: np.ndarray) -> np.ndarray:
    vn = np.zeros_like(v, dtype=np.float64)
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    for k in range(3):
        np.add.at(vn, f[:, k], fn)
    return normalize(vn)


def hull_beam_sheer_keel(t: float) -> tuple[float, float, float]:
    """Parametric galleon hull curves along t in [0=stern (-3.4), 1=bow (+3.8)]."""
    t = float(np.clip(t, 0.0, 1.0))
    # Full rounded bow, broad midships, high tucked stern castle
    beam = 1.42 * (max(0.0, math.sin(math.pi * (t ** 0.72))) ** 0.72) + 0.34 * ((1.0 - t) ** 1.2)
    beam = max(0.05, beam)
    sheer = 1.05 + 0.92 * ((1.0 - t) ** 2.4) + 0.44 * (t ** 2.6)
    keel = -0.82 + 0.65 * (t ** 2.4) + 0.32 * ((1.0 - t) ** 2.2)
    return beam, sheer, keel


def make_box(center: Sequence[float], extents: Sequence[float], color: Sequence[int], rot: np.ndarray | None = None) -> MeshGeometry:
    hx, hy, hz = extents[0] * 0.5, extents[1] * 0.5, extents[2] * 0.5
    v = np.array([
        [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
        [-hx, -hy,  hz], [hx, -hy,  hz], [hx, hy,  hz], [-hx, hy,  hz],
    ], dtype=np.float64)
    if rot is not None:
        v = v @ rot.T
    v += np.asarray(center, dtype=np.float64)
    f = np.array([
        [0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
        [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5],
    ], dtype=np.int32)
    return MeshGeometry(v, f, np.tile(np.array(color, dtype=np.uint8), (len(f), 1)))


def make_tube(p0: Sequence[float], p1: Sequence[float], r0: float, r1: float, sections: int, color: Sequence[int]) -> MeshGeometry:
    a, b = np.asarray(p0, dtype=np.float64), np.asarray(p1, dtype=np.float64)
    d = b - a
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return make_box(a, [r0, r0, r0], color)
    t = d / L
    ref = np.array([1.0, 0.0, 0.0]) if abs(t[0]) < 0.8 else np.array([0.0, 1.0, 0.0])
    n = normalize(np.cross(t, ref))
    bn = np.cross(t, n)

    verts = [a.copy()]
    for s in range(sections):
        ang = 2.0 * math.pi * s / sections
        verts.append(a + r0 * (math.cos(ang) * n + math.sin(ang) * bn))
    for s in range(sections):
        ang = 2.0 * math.pi * s / sections
        verts.append(b + r1 * (math.cos(ang) * n + math.sin(ang) * bn))
    tc = len(verts)
    verts.append(b.copy())
    v = np.array(verts, dtype=np.float64)
    faces = []
    for s in range(sections):
        s2 = (s + 1) % sections
        a0, a1 = 1 + s, 1 + s2
        b0, b1 = 1 + sections + s, 1 + sections + s2
        faces.extend([[0, a1, a0], [a0, a1, b1], [a0, b1, b0], [tc, b0, b1]])
    f = np.array(faces, dtype=np.int32)
    if signed_vol(v, f) < 0:
        f = f[:, [0, 2, 1]]
    return MeshGeometry(v, f, np.tile(np.array(color, dtype=np.uint8), (len(f), 1)))


def make_curved_tube(pts: Sequence[Sequence[float]], radii: Sequence[float], sections: int, color: Sequence[int]) -> MeshGeometry:
    """Multi-segment smooth swept tube along a 3D polyline."""
    arr = np.asarray(pts, dtype=np.float64)
    n_r = len(arr)
    tang = np.zeros_like(arr)
    tang[0] = arr[1] - arr[0]
    tang[-1] = arr[-1] - arr[-2]
    for i in range(1, n_r - 1):
        tang[i] = arr[i + 1] - arr[i - 1]
    tang = normalize(tang)

    ref = np.array([1.0, 0.0, 0.0]) if abs(tang[0, 0]) < 0.8 else np.array([0.0, 1.0, 0.0])
    n0 = normalize(np.cross(tang[0], ref))
    verts = [arr[0].copy()]
    cur_n = n0
    for i in range(n_r):
        if i > 0:
            v = np.cross(tang[i - 1], tang[i])
            s = float(np.linalg.norm(v))
            c = float(np.dot(tang[i - 1], tang[i]))
            if s > 1e-9:
                k = v / s
                ang = math.atan2(s, np.clip(c, -1.0, 1.0))
                cur_n = normalize(cur_n * math.cos(ang) + np.cross(k, cur_n) * math.sin(ang) + k * np.dot(k, cur_n) * (1.0 - math.cos(ang)))
        bn = np.cross(tang[i], cur_n)
        for j in range(sections):
            th = 2.0 * math.pi * j / sections
            verts.append(arr[i] + float(radii[i]) * (math.cos(th) * cur_n + math.sin(th) * bn))
    tc = len(verts)
    verts.append(arr[-1].copy())
    v = np.array(verts, dtype=np.float64)

    def ridx(r: int, s: int) -> int:
        return 1 + r * sections + (s % sections)

    faces = []
    for s in range(sections):
        faces.append([0, ridx(0, s + 1), ridx(0, s)])
    for r in range(n_r - 1):
        for s in range(sections):
            a, b, c, d = ridx(r, s), ridx(r, s + 1), ridx(r + 1, s + 1), ridx(r + 1, s)
            faces.extend([[a, b, c], [a, c, d]])
    for s in range(sections):
        faces.append([tc, ridx(n_r - 1, s), ridx(n_r - 1, s + 1)])
    f = np.array(faces, dtype=np.int32)
    if signed_vol(v, f) < 0:
        f = f[:, [0, 2, 1]]
    return MeshGeometry(v, f, np.tile(np.array(color, dtype=np.uint8), (len(f), 1)))


def make_billowing_quad_sail(
    center: Sequence[float],
    w_top: float,
    w_bot: float,
    height: float,
    billow: float,
    color: Sequence[int] = (255, 255, 255, 255),
    nx: int = 12,
    nz: int = 12,
) -> MeshGeometry:
    """High-res billowing catenary square sail with crisp [0..1] planar UVs."""
    cx, cy, cz = center
    verts, uvs = [], []
    for iz in range(nz):
        vz = iz / (nz - 1)
        w = w_bot + (w_top - w_bot) * vz
        # Gentle bottom arch (clew curve)
        arch = 0.12 * height * (1.0 - vz)
        for ix in range(nx):
            ux = ix / (nx - 1)
            x = cx + (ux - 0.5) * w
            by = billow * math.sin(math.pi * vz) * (0.35 + 0.65 * math.sin(math.pi * ux))
            z = cz + (vz - 0.5) * height + arch * math.sin(math.pi * ux)
            verts.append([x, cy + by, z])
            uvs.append([ux, 1.0 - vz])
    v_f = np.array(verts, dtype=np.float64)
    uv_f = np.array(uvs, dtype=np.float32)
    n_f = len(v_f)
    ff, fb = [], []
    for iz in range(nz - 1):
        for ix in range(nx - 1):
            a, b, c, d = iz * nx + ix, iz * nx + ix + 1, (iz + 1) * nx + ix + 1, (iz + 1) * nx + ix
            ff.extend([[a, b, c], [a, c, d]])
            fb.extend([[a + n_f, c + n_f, b + n_f], [a + n_f, d + n_f, c + n_f]])
    v_all = np.vstack([v_f, v_f])
    uv_all = np.vstack([uv_f, uv_f])
    ff_arr = np.array(ff, dtype=np.int32)
    fb_arr = np.array(fb, dtype=np.int32)
    vn_f = smooth_normals(v_f, ff_arr)
    vn_all = np.vstack([vn_f, -vn_f])
    f_all = np.vstack([ff_arr, fb_arr])
    return MeshGeometry(v_all, f_all, np.tile(np.array(color, dtype=np.uint8), (len(f_all), 1)), vertex_normals=vn_all, uvs=uv_all)


def make_triangular_sail(
    p_top: Sequence[float],
    p_front: Sequence[float],
    p_back: Sequence[float],
    billow_x: float = 0.28,
    color: Sequence[int] = (255, 255, 255, 255),
    steps: int = 10,
) -> MeshGeometry:
    """Smooth billowing triangular jib / spanker sail with clean planar UVs."""
    A = np.asarray(p_top, dtype=np.float64)
    B = np.asarray(p_front, dtype=np.float64)
    C = np.asarray(p_back, dtype=np.float64)
    verts, uvs, idx_map = [], [], {}
    for i in range(steps + 1):
        for j in range(steps + 1 - i):
            u = i / steps
            w = j / steps
            k = 1.0 - u - w
            pt = k * A + u * B + w * C
            # Smooth lateral wind billow in the interior of the triangle
            pt[0] += billow_x * (27.0 * u * w * k) * 0.55
            idx_map[(i, j)] = len(verts)
            verts.append(pt)
            uvs.append([u * 0.5 + w, 1.0 - k])
    v_f = np.array(verts, dtype=np.float64)
    uv_f = np.array(uvs, dtype=np.float32)
    n_f = len(v_f)
    ff, fb = [], []
    for i in range(steps):
        for j in range(steps - i):
            a, b, c = idx_map[(i, j)], idx_map[(i + 1, j)], idx_map[(i, j + 1)]
            ff.append([a, b, c])
            fb.append([a + n_f, c + n_f, b + n_f])
            if i + j + 1 < steps:
                d = idx_map[(i + 1, j + 1)]
                ff.append([b, d, c])
                fb.append([b + n_f, c + n_f, d + n_f])
    ff_arr, fb_arr = np.array(ff, dtype=np.int32), np.array(fb, dtype=np.int32)
    vn_f = smooth_normals(v_f, ff_arr)
    v_all = np.vstack([v_f, v_f])
    vn_all = np.vstack([vn_f, -vn_f])
    uv_all = np.vstack([uv_f, uv_f])
    f_all = np.vstack([ff_arr, fb_arr])
    return MeshGeometry(v_all, f_all, np.tile(np.array(color, dtype=np.uint8), (len(f_all), 1)), vertex_normals=vn_all, uvs=uv_all)


def merge_geometries(items: Sequence[MeshGeometry]) -> MeshGeometry:
    vs, fs, cs, ns = [], [], [], []
    uvs_list = []
    has_uv = all(g.uvs is not None for g in items)
    off = 0
    for g in items:
        vs.append(g.vertices)
        fs.append(g.faces + off)
        cs.append(g.face_colors)
        ns.append(g.vertex_normals if g.vertex_normals is not None else smooth_normals(g.vertices, g.faces))
        if has_uv:
            uvs_list.append(g.uvs)
        off += len(g.vertices)
    return MeshGeometry(np.vstack(vs), np.vstack(fs), np.vstack(cs), np.vstack(ns), uvs=np.vstack(uvs_list) if has_uv else None)
