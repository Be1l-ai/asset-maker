#!/usr/bin/env python3
"""Procedural 3D solid model generator: Mana Obelisk (V2).

Recreated using Vault techniques:
- Revolved lathe profile pedestal and chalice basin
- Baked ground-contact ambient occlusion gradient
- Dual-faceted mana crystal apex with orbiting phyllotaxis resonance shards
- Stylized warm-lit gold collars and cool-shadow slate stone

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

from asset_pipeline import (
    AssetValidator,
    Manifest,
    MeshBuilder,
    SolidMesh,
    bake_ground_ao,
)

ASSET_NAME = "mana_obelisk_v2"

STONE = [88, 98, 116, 255]
STONE_DARK = [58, 64, 78, 255]
GOLD = [235, 185, 55, 255]
CRYSTAL = [80, 225, 255, 255]


def build(seed: int = 7) -> SolidMesh:
    """Watertight obelisk: lathed plinth, tapered monolith, gilded collars, tilted crystal halo."""
    rng = np.random.default_rng(seed)
    builder = MeshBuilder(seed=seed)

    # 1. Lathed plinth: [radius, z] contour with scotia recess and torus ring (subdivided for AO)
    plinth = np.array([
        [0.0, 0.0], [0.70, 0.0], [0.70, 0.10], [0.58, 0.16],
        [0.54, 0.24], [0.62, 0.29], [0.50, 0.36], [0.0, 0.36],
    ])
    builder.lathe(plinth, sections=16, color=STONE_DARK, subdivide=3)

    # 2. Tapered 4-sided monolith with pyramidion cap, built as one revolved profile
    shaft_base, shaft_top, shaft_h = 0.42, 0.25, 1.40
    z0 = 0.36
    shaft = np.array([
        [0.0, 0.0], [shaft_base, 0.0], [shaft_top, shaft_h],
        [0.0, shaft_h + 0.30], [0.0, 0.0],
    ])[:-1]
    builder.lathe(shaft, sections=4, offset=[0, 0, z0], color=STONE, subdivide=4)

    # 3. Gilded runic collars, radius follows the taper so they always clear the shaft
    def collar(z_world: float, extra: float, height: float) -> None:
        t = (z_world - z0) / shaft_h
        r = (shaft_base + (shaft_top - shaft_base) * t) + extra
        prof = np.array([[0.0, 0.0], [r, 0.0], [r + 0.03, height * 0.5], [r, height], [0.0, height]])
        builder.lathe(prof, sections=12, offset=[0, 0, z_world], color=GOLD, subdivide=2)

    collar(0.78, 0.07, 0.08)
    collar(1.36, 0.07, 0.06)

    # 4. Floating crystal apex: upper and inverted lower facets
    apex_z = z0 + shaft_h + 0.55
    builder.pyramid(base_radius=0.19, height=0.52, sections=6, offset=[0, 0, apex_z], color=CRYSTAL)
    builder.pyramid(base_radius=0.17, height=0.24, sections=6, offset=[0, 0, apex_z + 0.02],
                    direction=[0, 0, -1], color=[35, 165, 225, 255])

    # 5. Resonance shards on a golden-angle (phyllotaxis) spiral, tilted outward from the axis
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(7):
        theta = i * golden_angle + rng.uniform(-0.05, 0.05)
        radius = 0.50 + 0.07 * np.sqrt(i)
        z = z0 + 0.95 + 0.17 * i
        outward = np.array([np.cos(theta), np.sin(theta), 0.0])
        direction = outward * 0.55 + np.array([0.0, 0.0, 1.0])
        builder.pyramid(base_radius=0.05, height=0.24, sections=4,
                        offset=[radius * np.cos(theta), radius * np.sin(theta), z],
                        direction=direction, color=[120, 240, 255, 255])

    mesh = builder.build()
    bake_ground_ao(mesh, height=0.55, strength=0.55)   # multiplies into existing palette
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

    mesh.export_glb(glb_file, apply_y_up=True)
    mesh.export_obj(obj_file)
    mesh.render_preview(preview_file)

    AssetValidator.validate_mesh(glb_file, max_triangles=3000, watertight=True)
    AssetValidator.validate_mesh_shading(mesh, max_ground_ratio=0.85)

    manifest = Manifest(
        asset=glb_file.name,
        parameters={"seed": args.seed, "version": "v2_vault"},
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("techniques/art_styles/vertex_color_gradient_baking.md", "bake_ground_ao")
    manifest.declare_vault("mathematics/geometry/spirals_and_golden_ratio.md", "pyramid")
    manifest.declare_vault("techniques/art_styles/bevels_and_edge_weight.md", "lathe")
    manifest.declare_vault("techniques/materials/chiseled_stone_and_masonry.md", "lathe", "bake_ground_ao")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {glb_file}, {obj_file}, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
