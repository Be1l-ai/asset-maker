#!/usr/bin/env python3
"""Procedural 3D solid model generator template.

Usage:
    python generate.py [--seed 7]
"""
import sys
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "asset_pipeline").is_dir()), None)
if ROOT and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_pipeline import AssetValidator, Manifest, MeshBuilder, SolidMesh

ASSET_NAME = "model"


def build(seed: int = 7) -> SolidMesh:
    """Agent edits this function to construct watertight 3D solid geometry."""
    return (
        MeshBuilder(seed=seed)
        .cylinder(radius=0.35, height=0.25, sections=8, color=[70, 75, 85, 255])
        .pyramid(base_radius=0.28, height=0.90, sections=6, offset=[0, 0, 0.25], color=[110, 195, 245, 255])
        .build()
    )


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
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Generated {glb_file}, {obj_file}, and preview.png (passed validation)")


if __name__ == "__main__":
    main()
