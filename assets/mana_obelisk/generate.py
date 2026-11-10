#!/usr/bin/env python3
"""Procedural 3D solid model generator: Mana Obelisk.

Constructs an ancient stone obelisk with gold runic bands and a glowing mana crystal.
Usage:
    python generate.py [--seed 7]
"""
import sys
from pathlib import Path
import numpy as np
import trimesh

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_pipeline import AssetValidator, Manifest, MeshBuilder, SolidMesh

ASSET_NAME = "mana_obelisk"


def build(seed: int = 7) -> SolidMesh:
    """Constructs a watertight 3D solid ancient mana obelisk."""
    rng = np.random.default_rng(seed)
    builder = MeshBuilder(seed=seed)

    # 1. Stepped Stone Pedestal
    # Lower octagonal tier
    builder.cylinder(radius=0.62, height=0.14, sections=8, offset=[0, 0, 0.07], color=[52, 58, 64, 255])
    # Upper octagonal tier
    builder.cylinder(radius=0.48, height=0.14, sections=8, offset=[0, 0, 0.21], color=[68, 75, 84, 255])

    # 2. Four corner accent stones on the plinth
    for angle in [np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4]:
        cx = 0.44 * np.cos(angle)
        cy = 0.44 * np.sin(angle)
        builder.box(extents=(0.10, 0.10, 0.18), offset=[cx, cy, 0.23], color=[45, 50, 56, 255])

    # 3. Main Obelisk Tapered Shaft (4-sided stone pillar)
    builder.pyramid(base_radius=0.40, height=1.50, sections=4, offset=[0, 0, 0.95], color=[90, 98, 110, 255])

    # 4. Runic Gilded Metal Bands
    builder.cylinder(radius=0.30, height=0.06, sections=4, offset=[0, 0, 0.65], color=[225, 175, 55, 255])
    builder.cylinder(radius=0.20, height=0.05, sections=4, offset=[0, 0, 1.25], color=[225, 175, 55, 255])

    # 5. Floating / Capping Mana Crystal
    # Upper crystal spike
    builder.pyramid(base_radius=0.18, height=0.52, sections=6, offset=[0, 0, 1.82], color=[80, 220, 255, 255])
    # Lower crystal inverted pyramid
    lower_crystal = trimesh.creation.cone(radius=0.18, height=0.22, sections=6)
    # Flip lower crystal pointing down along Z
    rot_x = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    lower_crystal.apply_transform(rot_x)
    lower_crystal.apply_translation([0, 0, 1.56])
    color_bytes = np.array([40, 170, 230, 255], dtype=np.uint8)
    lower_crystal.visual = trimesh.visual.ColorVisuals(
        mesh=lower_crystal,
        face_colors=np.tile(color_bytes, (len(lower_crystal.faces), 1))
    )
    builder.add_mesh(lower_crystal)

    # 6. Orbiting resonance shards
    shard_count = 3
    base_orbit_r = 0.38 + 0.04 * (rng.random() - 0.5)
    for i in range(shard_count):
        theta = (2 * np.pi / shard_count) * i + rng.uniform(-0.1, 0.1)
        z_shard = 1.40 + 0.12 * np.sin(theta * 2)
        sx = base_orbit_r * np.cos(theta)
        sy = base_orbit_r * np.sin(theta)
        builder.pyramid(base_radius=0.06, height=0.20, sections=4, offset=[sx, sy, z_shard], color=[100, 235, 255, 255])

    mesh = builder.build()
    return mesh


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Generate {ASSET_NAME}")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent, help="Output folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    mesh = build(seed=args.seed)

    glb_file = args.out / f"{ASSET_NAME}.glb"
    obj_file = args.out / f"{ASSET_NAME}.obj"
    preview_file = args.out / "preview.png"

    # Export both GLB (Y-up for game engines) and OBJ
    mesh.export_glb(glb_file, apply_y_up=True)
    mesh.export_obj(obj_file)
    mesh.render_preview(preview_file)

    AssetValidator.validate_mesh(glb_file, max_triangles=3000, watertight=True)

    manifest = Manifest(
        asset=glb_file.name,
        parameters={"seed": args.seed},
        recipe=Path(__file__).name,
    )
    manifest.scan_directory(args.out).save(args.out)
    print(f"✓ Generated {glb_file}, {obj_file}, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
