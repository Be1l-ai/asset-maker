#!/usr/bin/env python3
"""Master assembler for sky_galleon_hero built with hardened asset-maker V4."""

from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in HERE.parents if (p / "asset_pipeline").is_dir()), None)
for p in (HERE, ROOT):
    if p and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from asset_pipeline.manifest import Manifest
from asset_pipeline.scene3d import SceneBuilder
from materials import build_materials
from parts.deck import build_deck_and_rails
from parts.hull import build_hull_subsystems
from parts.masts_sails import build_masts_and_sails
from parts.propulsion import build_propulsion_and_lanterns
from parts.rigging import build_rigging_and_ratlines
from rig import PIVOTS

ASSET_NAME = "sky_galleon_hero"


def build(spec_path: Path, seed: int = 7) -> SceneBuilder:
    scene = SceneBuilder.from_spec(spec_path, seed=seed)
    for k, m in build_materials().items():
        scene.materials[k] = m

    hull_m, brass_m, win_m = build_hull_subsystems()
    deck_m = build_deck_and_rails()
    masts_m, main_sail_m, sq_sails_m, tri_sails_m = build_masts_and_sails()
    rig_m = build_rigging_and_ratlines()
    nac_m, ring_m, core_m, lf_m, lfl_m = build_propulsion_and_lanterns()

    scene.add_part("Hull_Planking", hull_m, pivot=PIVOTS["Hull_Planking"])
    scene.add_part("Hull_Brass_Trim", brass_m, pivot=PIVOTS["Hull_Brass_Trim"])
    scene.add_part("Stern_Cabin_Windows", win_m, pivot=PIVOTS["Stern_Cabin_Windows"], cast_shadow=False, receive_shadow=False)
    scene.add_part("Deck_And_Rails", deck_m, pivot=PIVOTS["Deck_And_Rails"])
    scene.add_part("Masts_And_Bowsprit", masts_m, pivot=PIVOTS["Masts_And_Bowsprit"])
    scene.add_part("Main_Emblem_Sail", main_sail_m, pivot=PIVOTS["Main_Emblem_Sail"])
    scene.add_part("Racing_Square_Sails", sq_sails_m, pivot=PIVOTS["Racing_Square_Sails"])
    scene.add_part("Jib_And_Spanker_Sails", tri_sails_m, pivot=PIVOTS["Jib_And_Spanker_Sails"])
    scene.add_part("Rigging_And_Ratlines", rig_m, pivot=PIVOTS["Rigging_And_Ratlines"])
    scene.add_part("Turbine_Nacelles", nac_m, pivot=PIVOTS["Turbine_Nacelles"])
    scene.add_part("Turbine_Brass_Rings", ring_m, pivot=PIVOTS["Turbine_Brass_Rings"])
    scene.add_part("Thruster_Glow_Cores", core_m, pivot=PIVOTS["Thruster_Glow_Cores"], cast_shadow=False, receive_shadow=False)
    scene.add_part("Stern_Lantern_Frames", lf_m, pivot=PIVOTS["Stern_Lantern_Frames"])
    scene.add_part("Stern_Lantern_Flames", lfl_m, pivot=PIVOTS["Stern_Lantern_Flames"], cast_shadow=False, receive_shadow=False)
    scene.validate()
    return scene


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--preview-name", type=str, default="preview.png")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    scene = build(HERE / "spec.json", seed=args.seed)
    glb = args.out / f"{ASSET_NAME}.glb"
    obj = args.out / f"{ASSET_NAME}.obj"
    insp = args.out / "inspector.json"
    prev = args.out / args.preview_name

    scene.export_glb(glb, apply_y_up=True)
    scene.export_obj(obj)
    scene.export_inspector_json(insp)

    sky = ([86, 102, 124], [66, 82, 104], [48, 62, 82])
    fog = [72, 88, 110]
    lights = [
        ((0.0, -3.55, 2.65), (1.10, 0.78, 0.30), 4.5, 0.95),
        ((1.8, -2.50, 0.25), (0.25, 0.88, 1.10), 4.2, 0.90),
        ((-1.8, -2.50, 0.25), (0.25, 0.88, 1.10), 4.2, 0.90),
    ]
    # 2-panel studio render: 3/4 Hero Port View + 3/4 Rear-Starboard View
    p1 = scene.render_preview(args.out / "_p1.png", cam_pos=(-10.8, 5.6, 4.1), target=(0.0, 0.9, 2.5), fov_deg=44.0, size=(760, 520), sun_dir=(-0.55, 0.45, 0.70), sky_colors=sky, fog_color=fog, point_lights=lights)
    p2 = scene.render_preview(args.out / "_p2.png", cam_pos=(10.4, -7.2, 3.9), target=(0.0, 0.4, 2.3), fov_deg=44.0, size=(760, 520), sun_dir=(0.55, -0.35, 0.72), sky_colors=sky, fog_color=fog, point_lights=lights)
    strip = Image.new("RGB", (760 * 2 + 4, 520), (24, 30, 42))
    strip.paste(p1, (0, 0))
    strip.paste(p2, (764, 0))
    strip.save(prev)
    (args.out / "_p1.png").unlink(missing_ok=True)
    (args.out / "_p2.png").unlink(missing_ok=True)

    manifest = Manifest(
        asset=glb.name,
        parameters={"seed": args.seed, "nodes": len(scene.nodes), "triangles": scene.triangle_count},
        recipe=Path(__file__).name,
    )
    manifest.declare_vault("techniques/geometry/staged_scene_assembly.md", "SceneBuilder")
    manifest.declare_vault("techniques/art_styles/production_critique_loop.md", "SceneBuilder")
    manifest.scan_directory(args.out, only=[ASSET_NAME]).save(args.out)
    print(f"✓ Built {glb.name}: {scene.triangle_count} tris, {len(scene.nodes)} nodes, 8 embedded 512x512 PBR textures")


if __name__ == "__main__":
    main()
