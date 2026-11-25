"""Tests for asset-maker V3 upgrade (Phases 1-3):
- Phase 1: SceneBuilder, SceneSpec, MaterialSpec (UVs + embedded PNG PBR textures), 3d_scene & 3d_hero_package templates
- Phase 2: Gallery WebGL Inspector controls (shading modes, lighting presets, scene hierarchy drawer) & build_html
- Phase 3: Curated prompt benchmarks (benchmarks/prompts.json) & CLI benchmarks command
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_pipeline import audit_recipe, init_asset, list_templates
from asset_pipeline.scene3d import SceneBuilder, SceneSpec


def _parse_glb_json(glb_path: Path) -> dict:
    raw = glb_path.read_bytes()
    magic, version, total_len = struct.unpack("<III", raw[:12])
    assert magic == 0x46546C67 and version == 2 and total_len == len(raw)
    json_len, json_type = struct.unpack("<II", raw[12:20])
    assert json_type == 0x4E4F534A
    return json.loads(raw[20:20 + json_len].decode("utf-8"))


class TestAssetMakerV3Upgrade(unittest.TestCase):
    def test_templates_registered(self) -> None:
        templates = list_templates()
        self.assertIn("3d_scene", templates)
        self.assertIn("3d_hero_package", templates)

    def test_phase1_3d_scene_scaffold_build_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "meadow_demo"
            init_asset("3d_scene", dst)
            spec = SceneSpec.from_file(dst / "spec.json")
            self.assertEqual(spec.name, "meadow_demo")

            subprocess.run(
                [sys.executable, str(dst / "generate.py"), "--seed", "7", "--out", str(dst)],
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                capture_output=True,
                text=True,
                check=True,
            )

            gltf = _parse_glb_json(dst / "meadow_demo.glb")
            self.assertEqual([n["name"] for n in gltf["nodes"]], ["Terrain_Ground", "Hero_Tree", "Sun"])
            tree_node = next(n for n in gltf["nodes"] if n["name"] == "Hero_Tree")
            self.assertAlmostEqual(tree_node["translation"][2], -1.5, places=4)
            self.assertEqual(len(gltf["materials"]), 3)

            report = audit_recipe(dst)
            self.assertTrue(report.ok, report.format())

    def test_phase1_3d_hero_package_embedded_pbr_textures_and_per_asset_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "arcane_shrine"
            init_asset("3d_hero_package", dst)
            self.assertTrue((dst / "parts" / "base.py").is_file())
            self.assertTrue((dst / "textures.py").is_file())
            self.assertTrue((dst / "materials.py").is_file())
            self.assertTrue((dst / "rig.py").is_file())

            env = {**os.environ, "PYTHONPATH": str(ROOT)}
            subprocess.run([sys.executable, str(dst / "generate.py"), "--seed", "7", "--out", str(dst)], env=env, check=True, capture_output=True)
            subprocess.run([sys.executable, str(dst / "test_asset.py")], env=env, check=True, capture_output=True)

            gltf = _parse_glb_json(dst / "arcane_shrine.glb")
            self.assertEqual([n["name"] for n in gltf["nodes"]], ["Plinth_Base", "Timber_Frame", "Crystal_Core"])
            # Embedded PNG albedo + normal maps for stone and wood (4 textures total)
            self.assertEqual(len(gltf.get("textures", [])), 4)
            self.assertEqual(len(gltf.get("images", [])), 4)
            self.assertIn("TEXCOORD_0", gltf["meshes"][0]["primitives"][0]["attributes"])

            inspector = json.loads((dst / "inspector.json").read_text(encoding="utf-8"))
            self.assertEqual(inspector["node_count"], 3)
            self.assertTrue(inspector["nodes"][0]["has_textures"])

            report = audit_recipe(dst)
            self.assertTrue(report.ok, report.format())

    def test_phase1_spec_validation_catches_missing_part(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps({
                "name": "incomplete",
                "max_triangles": 500,
                "parts": [{"name": "RequiredPart", "material": "matte", "max_triangles": 100}],
            }), encoding="utf-8")
            scene = SceneBuilder.from_spec(spec_path, seed=1)
            with self.assertRaises(ValueError):
                scene.validate()

    def test_phase2_gallery_inspector_and_html_build(self) -> None:
        index_html = (ROOT / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "gallery" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="dialog-nodes"', index_html)
        self.assertIn("shadeMode", app_js)
        self.assertIn("lightPreset", app_js)

    def test_phase3_benchmarks_suite_and_cli(self) -> None:
        bpath = ROOT / "benchmarks" / "prompts.json"
        self.assertTrue(bpath.is_file())
        data = json.loads(bpath.read_text(encoding="utf-8"))
        self.assertEqual(data["count"], 20)
        valid_templates = set(list_templates())
        for row in data["benchmarks"]:
            self.assertIn(row["recommended_template"], valid_templates)
            self.assertTrue(row["prompt_excerpt"])

        res = subprocess.run(
            [sys.executable, "-m", "asset_pipeline", "benchmarks", "--template", "3d_hero_package"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("3d_hero_package", res.stdout)


    def test_phase4_triple_track_templates_style_profiles_and_critique_gate(self) -> None:
        from asset_pipeline import CritiqueLog, STYLE_PROFILES
        self.assertIn("3d_threejs_hero", list_templates())
        self.assertIn("2d_web_ui", list_templates())
        self.assertIn("hand_painted_hero", STYLE_PROFILES)
        self.assertFalse(STYLE_PROFILES["stylized_lowpoly"]["require_uv_textures"])
        self.assertTrue(STYLE_PROFILES["hand_painted_hero"]["require_uv_textures"])

        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "galleon_hero"
            init_asset("3d_threejs_hero", dst)
            (dst / "manifest.json").write_text(json.dumps({
                "asset": "galleon_hero.glb", "parameters": {}, "versions": {}, "sha256": {},
                "vault_refs": {"techniques/art_styles/production_critique_loop.md": ["CritiqueLog"]},
            }), encoding="utf-8")

            # A rushed 2,192-tri single-part ship with 3 critique rounds STILL FAILS hand_painted_hero floors!
            clog = CritiqueLog(asset="galleon_hero.glb", min_rounds=3)
            for idx in range(1, 4):
                img = dst / f"v{idx}.png"
                img.write_bytes(f"fake-png-bytes-round-{idx}".encode("utf-8"))
                clog.add_round(img, defects_found=[f"Defect {idx}"], fixes_applied=[f"Fix {idx}"])
            clog.save(dst)
            (dst / "inspector.json").write_text(json.dumps({
                "scene": "galleon_hero", "total_triangles": 2192, "node_count": 8,
                "nodes": [{"name": "Hull", "material_key": "m1", "has_textures": False}],
            }), encoding="utf-8")
            slop_report = audit_recipe(dst)
            self.assertFalse(slop_report.ok)
            self.assertTrue(any("subsystem modules" in e for e in slop_report.errors))
            self.assertTrue(any("concept reference" in e for e in slop_report.errors))
            self.assertTrue(any("floor is >= 10000" in e for e in slop_report.errors))

            # Satisfy all hand_painted_hero floors (>=4 part modules, concept.png, >=10k tris, >=12 nodes, >=3 mats, UV textures) -> PASSES!
            for extra in ("hullBuilder.ts", "deckBuilder.ts", "sailsBuilder.ts"):
                (dst / "src" / "parts" / extra).write_text("export {};\n", encoding="utf-8")
            (dst / "concept.png").write_bytes(b"concept-art")
            (dst / "inspector.json").write_text(json.dumps({
                "scene": "galleon_hero", "total_triangles": 24500, "node_count": 14,
                "nodes": [
                    {"name": f"Node_{i}", "material_key": f"mat_{i % 3}", "has_textures": True}
                    for i in range(14)
                ],
            }), encoding="utf-8")
            ok_report = audit_recipe(dst)
            self.assertTrue(ok_report.ok, ok_report.format())


    def test_phase5_sculpt_primitives_and_rubric_critique(self) -> None:
        from asset_pipeline import (
            CritiqueLog, array_along_curve, catenary_cloth, catmull_rom_tube,
            extrude_beveled_2d, loft_cross_sections,
        )
        tube = catmull_rom_tube([[0, 0, 0], [0.5, 0.4, 0.5], [1.0, 0.0, 1.0]], radii=[0.1, 0.04], sections=8)
        self.assertGreater(len(tube.faces), 40)

        bracket = extrude_beveled_2d([[0, 0], [1, 0], [0.8, 0.6], [0, 0.4]], depth=0.2, bevel=0.03)
        self.assertGreater(len(bracket.faces), 20)

        sail = catenary_cloth([0, 0, 1], w_top=2.0, w_bot=2.4, height=1.5, billow=0.4, nx=8, nz=8)
        self.assertIsNotNone(sail.uvs)
        self.assertIsNotNone(sail.vertex_normals)
        # Split double-sided normals must NOT cancel to zero
        self.assertGreater(float((sail.vertex_normals ** 2).sum(axis=1).min()), 0.9)

        rivets = array_along_curve([[0, 0, 0], [1, 0, 0], [2, 0.5, 0]], count=5, builder_fn=lambda p, t, i: extrude_beveled_2d([[p[0]-0.05, p[1]-0.05], [p[0]+0.05, p[1]-0.05], [p[0]+0.05, p[1]+0.05], [p[0]-0.05, p[1]+0.05]], depth=0.05, bevel=0.01))
        self.assertGreater(len(rivets.faces), 80)

        # Rubric validation rejects low final score (< 8/10) and accepts >= 8/10
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            clog = CritiqueLog(asset="hero.glb", min_rounds=3)
            for idx in range(1, 4):
                p = d / f"r{idx}.png"
                p.write_bytes(f"img-{idx}".encode("utf-8"))
                scores = {"silhouette": 6, "proportions": 8, "surface_materials": 8, "secondary_detail": 8, "lighting_read": 8} if idx == 3 else {}
                clog.add_round(p, defects_found=[f"d{idx}"], fixes_applied=[f"f{idx}"], subsystem=f"sub_{idx}", rubric_scores=scores)
            clog.save(d)
            errs = CritiqueLog.validate_file(d / "critique_log.json", min_rounds=3, min_final_score=8)
            self.assertTrue(any("silhouette" in e for e in errs))

        # Worked example exists and passes its own structure
        self.assertTrue((ROOT / "examples" / "sky_galleon_hero" / "parts" / "hull.py").is_file())

    def test_phase6_baking_and_two_tier_cross_modality_critique(self):
        import tempfile
        import numpy as np
        from PIL import Image
        from asset_pipeline.baking import (
            build_metallic_roughness_map,
            compute_sprite_alpha_efficiency,
            generate_cloth_normal_map,
            generate_fur_normal_map,
            generate_wood_grain_normal_map,
        )
        from asset_pipeline.critique import CritiqueLog, DETAIL_RUBRIC_AXES

        # Baking helpers produce valid RGBA maps & alpha efficiency
        fur_n = generate_fur_normal_map(size=64)
        cloth_n = generate_cloth_normal_map(size=64)
        wood_n = generate_wood_grain_normal_map(size=64)
        mr = build_metallic_roughness_map(np.full((64, 64), 0.85, dtype=np.float32), metallic=0.1)
        self.assertEqual(fur_n.size, (64, 64))
        self.assertEqual(cloth_n.size, (64, 64))
        self.assertEqual(wood_n.size, (64, 64))
        self.assertEqual(mr.size, (64, 64))

        sprite = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        for y in range(8, 24):
            for x in range(8, 24):
                sprite.putpixel((x, y), (255, 255, 255, 255))
        self.assertAlmostEqual(compute_sprite_alpha_efficiency(sprite), 0.25, places=2)

        # Cross-modality outer 0-10 detail critique re-loop validation
        self.assertEqual(set(DETAIL_RUBRIC_AXES.keys()), {"3d", "2d", "vfx", "sfx"})
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            imgs = []
            for i in range(5):
                p = tdp / f"p{i}.png"
                p.write_bytes(f"frame-bytes-{i}".encode("utf-8"))
                imgs.append(p)

            log = CritiqueLog(asset="fx_slash.png", modality="vfx", min_rounds=3, max_detail_passes=5, target_detail_score=9.0)
            log.add_round(imgs[0], ["weak arc"], ["curved slash"], rubric_scores={"silhouette": 7, "proportions": 7, "surface_materials": 7, "secondary_detail": 7, "lighting_read": 7})
            log.add_round(imgs[1], ["flat glow"], ["added hot core"], rubric_scores={"silhouette": 8, "proportions": 8, "surface_materials": 8, "secondary_detail": 8, "lighting_read": 8})
            log.add_round(imgs[2], [], ["finalized flipbook"], rubric_scores={"silhouette": 9, "proportions": 9, "surface_materials": 9, "secondary_detail": 9, "lighting_read": 9})

            # Outer pass 1 scores 7.8 (< 9.0) -> must fail validation if we stop here!
            vfx_low = {ax: 7.8 for ax in DETAIL_RUBRIC_AXES["vfx"]}
            log.add_detail_pass(imgs[3], 7.8, vfx_low, ["alpha edge popping on frame 12"], ["feather dissolve tail"], modality="vfx")
            out_json = log.save(tdp)
            errs_low = CritiqueLog.validate_file(out_json, min_rounds=3, require_detail_pass=True)
            self.assertTrue(any("must re-loop" in e for e in errs_low), f"Expected re-loop error, got {errs_low}")

            # Outer pass 2 starts from Final 1, fixes flaw, scores 9.2 -> PASS!
            vfx_hi = {ax: 9.2 for ax in DETAIL_RUBRIC_AXES["vfx"]}
            log.add_detail_pass(imgs[4], 9.2, vfx_hi, [], ["verified feathered dissolve"], modality="vfx")
            log.save(tdp)
            errs_hi = CritiqueLog.validate_file(out_json, min_rounds=3, require_detail_pass=True)
            self.assertEqual(errs_hi, [], f"Expected clean pass, got {errs_hi}")


if __name__ == "__main__":
    unittest.main()
