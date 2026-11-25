#!/usr/bin/env python3
"""Master assembler for a multi-module 3D hero asset package.

Usage:
    python generate.py [--seed 7]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in HERE.parents if (p / "asset_pipeline").is_dir()), None)
for p in (HERE, ROOT):
    if p and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from asset_pipeline.manifest import Manifest
from asset_pipeline.scene3d import SceneBuilder
from materials import build_materials
from parts.accent import build_crystal_core
from parts.base import build_plinth_base
from parts.hero_body import build_timber_frame
from rig import PIVOTS

ASSET_NAME = "hero_asset"


def build(spec_path: Path, seed: int = 7) -> SceneBuilder:
    scene = SceneBuilder.from_spec(spec_path, seed=seed)
    for key, mspec in build_materials(seed=seed).items():
        scene.materials[key] = mspec

    scene.add_part("Plinth_Base", build_plinth_base(), pivot=PIVOTS["Plinth_Base"])
    scene.add_part("Timber_Frame", build_timber_frame(), pivot=PIVOTS["Timber_Frame"])
    scene.add_part("Crystal_Core", build_crystal_core(), pivot=PIVOTS["Crystal_Core"])
    scene.validate()
    return scene


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=f"Build hero package {ASSET_NAME}")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=HERE)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    scene = build(args.out / "spec.json", seed=args.seed)
    glb_file = args.out / f"{ASSET_NAME}.glb"
    obj_file = args.out / f"{ASSET_NAME}.obj"
    inspector_file = args.out / "inspector.json"
    preview_file = args.out / "preview.png"

    scene.export_glb(glb_file, apply_y_up=True)
    scene.export_obj(obj_file)
    scene.export_inspector_json(inspector_file)
    scene.render_preview(preview_file)

    manifest = Manifest(
        asset=glb_file.name,
        parameters={"seed": args.seed, "nodes": len(scene.nodes), "triangles": scene.triangle_count},
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("techniques/geometry/staged_scene_assembly.md", "SceneBuilder")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Built {glb_file} ({scene.triangle_count} tris, {len(scene.nodes)} nodes, embedded PBR textures)")


if __name__ == "__main__":
    main()
