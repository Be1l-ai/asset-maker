#!/usr/bin/env python3
"""Procedural multi-part 3D scene generator template (PARSE -> MASS -> RIG -> SKIN -> PACK).

Usage:
    python generate.py [--seed 7]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_pipeline.manifest import Manifest
from asset_pipeline.scene3d import MeshGeometry, SceneBuilder

ASSET_NAME = "scene"


def _make_box_plane(width: float, depth: float, color: list[int]) -> MeshGeometry:
    hw, hd = width * 0.5, depth * 0.5
    verts = np.array([[-hw, -hd, 0.0], [hw, -hd, 0.0], [hw, hd, 0.0], [-hw, hd, 0.0]], dtype=np.float64)
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    fcols = np.tile(np.array(color, dtype=np.uint8), (len(faces), 1))
    return MeshGeometry(vertices=verts, faces=faces, face_colors=fcols)


def _make_tiered_pine(origin: tuple[float, float, float], color: list[int]) -> MeshGeometry:
    ox, oy, oz = origin
    all_v, all_f, all_c = [], [], []
    off = 0
    for z0, r, h, col in [
        (0.0, 0.22, 1.1, [112, 76, 52, 255]),
        (0.8, 1.15, 1.4, color),
        (1.8, 0.85, 1.3, [min(255, color[0] + 12), min(255, color[1] + 16), color[2], 255]),
        (2.7, 0.55, 1.2, [min(255, color[0] + 24), min(255, color[1] + 28), color[2], 255]),
    ]:
        secs = 7
        verts = [[ox, oy, oz + z0]]
        for k in range(secs):
            a = 2.0 * math.pi * k / secs
            verts.append([ox + r * math.cos(a), oy + r * math.sin(a), oz + z0])
        verts.append([ox, oy, oz + z0 + h])
        faces = []
        for k in range(secs):
            a, b = 1 + k, 1 + (k + 1) % secs
            faces.append([off, off + b, off + a])
            faces.append([off + a, off + b, off + secs + 1])
        all_v.append(np.array(verts, dtype=np.float64))
        all_f.append(np.array(faces, dtype=np.int32))
        all_c.append(np.tile(np.array(col, dtype=np.uint8), (len(faces), 1)))
        off += len(verts)
    return MeshGeometry(vertices=np.vstack(all_v), faces=np.vstack(all_f), face_colors=np.vstack(all_c))


def _make_sun_orb(center: tuple[float, float, float], radius: float) -> MeshGeometry:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    v = np.array([
        [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
        [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
        [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1],
    ], dtype=np.float64)
    v = v / np.linalg.norm(v, axis=1, keepdims=True) * radius + np.asarray(center)
    f = np.array([
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
    ], dtype=np.int32)
    c = np.tile(np.array([255, 236, 152, 255], dtype=np.uint8), (len(f), 1))
    return MeshGeometry(vertices=v, faces=f, face_colors=c)


def build(spec_path: Path, seed: int = 7) -> SceneBuilder:
    scene = SceneBuilder.from_spec(spec_path, seed=seed)
    scene.add_part("Terrain_Ground", _make_box_plane(16.0, 16.0, [186, 162, 82, 255]), cast_shadow=False)
    scene.add_part("Hero_Tree", _make_tiered_pine((0.0, 1.5, 0.0), [72, 122, 56, 255]))
    scene.add_part("Sun", _make_sun_orb((-6.0, 10.0, 8.0), 0.85), cast_shadow=False, receive_shadow=False)
    scene.validate()
    return scene


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    spec_file = args.out / "spec.json"
    scene = build(spec_file, seed=args.seed)

    glb_file = args.out / f"{ASSET_NAME}.glb"
    obj_file = args.out / f"{ASSET_NAME}.obj"
    preview_file = args.out / "preview.png"

    scene.export_glb(glb_file, apply_y_up=True)
    scene.export_obj(obj_file)
    scene.render_preview(preview_file)

    manifest = Manifest(
        asset=glb_file.name,
        parameters={"seed": args.seed, "nodes": len(scene.nodes), "triangles": scene.triangle_count},
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("techniques/geometry/staged_scene_assembly.md", "SceneBuilder")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {glb_file}, {obj_file}, and preview.png ({scene.triangle_count} tris, {len(scene.nodes)} nodes)")


if __name__ == "__main__":
    main()
