"""Tests for the verification layer: recipe audit, perceptual validators, and the V2 asset fixes."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

from asset_pipeline import (
    AssetValidator,
    MeshBuilder,
    Manifest,
    audit_recipe,
    bake_ground_ao,
    ellipse_mask,
    heightmap_to_normal_map,
    new_layer,
    over,
    worley_noise,
)
from asset_pipeline.audit import frame_motion_profile, mesh_ground_darkening, silhouette_report

ROOT = Path(__file__).resolve().parents[1]
V2_ASSETS = sorted((ROOT / "assets").glob("*_v2"))


def _asset(tmp: Path, recipe: str, manifest: dict) -> Path:
    (tmp / "generate.py").write_text(recipe)
    (tmp / "manifest.json").write_text(json.dumps(manifest))
    return tmp


class RecipeAuditTests(unittest.TestCase):
    def test_flags_unused_pipeline_import(self):
        with tempfile.TemporaryDirectory() as d:
            adir = Path(d)
            _asset(adir, "from asset_pipeline import worley_noise, bake_ground_ao\nworley_noise(8, 8)\n",
                   {"sha256": {}, "vault_refs": {}})
            report = audit_recipe(adir)
            self.assertFalse(report.ok)
            self.assertTrue(any("bake_ground_ao" in e for e in report.errors))

    def test_flags_missing_vault_doc_and_unused_symbol(self):
        with tempfile.TemporaryDirectory() as d:
            adir = Path(d)
            _asset(adir, "from asset_pipeline import worley_noise\nworley_noise(8, 8)\n", {
                "sha256": {},
                "vault_refs": {
                    "nope/missing.md": ["worley_noise"],
                    "mathematics/noise_and_fields/worley_cellular_noise.md": ["bake_ground_ao"],
                },
            })
            errors = " | ".join(audit_recipe(adir).errors)
            self.assertIn("does not exist", errors)
            self.assertIn("never uses it", errors)

    def test_flags_stale_hashes_from_other_versions(self):
        with tempfile.TemporaryDirectory() as d:
            adir = Path(d) / "thing_v2"
            adir.mkdir()
            _asset(adir, "x = 1\n", {"sha256": {"thing.glb": "abc", "thing_v2.glb": "def"}, "vault_refs": {}})
            self.assertTrue(any("another asset" in e for e in audit_recipe(adir).errors))

    def test_all_v2_assets_pass_audit(self):
        self.assertGreaterEqual(len(V2_ASSETS), 5)
        for adir in V2_ASSETS:
            with self.subTest(asset=adir.name):
                report = audit_recipe(adir)
                self.assertTrue(report.ok, report.format())
                self.assertTrue(report.info["vault_refs"], "v2 assets must cite the vault")

    def test_manifest_only_filter_and_declare_vault(self):
        with tempfile.TemporaryDirectory() as d:
            adir = Path(d)
            (adir / "foo_v2.png").write_bytes(b"1")
            (adir / "foo.png").write_bytes(b"2")
            m = Manifest(asset="foo_v2.png").declare_vault("a.md", "x").declare_vault("a.md", "x", "y")
            m.scan_directory(adir, only=["foo_v2"])
            self.assertEqual(sorted(m.sha256), ["foo_v2.png"])
            self.assertEqual(m.to_dict()["vault_refs"], {"a.md": ["x", "y"]})


class SilhouetteAndLayerTests(unittest.TestCase):
    def _blobs(self, centers):
        arr = np.zeros((128, 128, 4), dtype=np.uint8)
        yy, xx = np.mgrid[0:128, 0:128]
        for cx, cy in centers:
            arr[((xx - cx) ** 2 + (yy - cy) ** 2) < 22 ** 2] = (255, 0, 0, 255)
        return Image.fromarray(arr, "RGBA")

    def test_fragmented_silhouette_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.png"
            self._blobs([(30, 30), (100, 100)]).save(p)
            with self.assertRaises(ValueError):
                AssetValidator.validate_silhouette(p, max_components=1)

    def test_single_silhouette_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.png"
            self._blobs([(64, 64)]).save(p)
            self.assertEqual(silhouette_report(p)["components"], 1)
            AssetValidator.validate_silhouette(p, max_components=1)

    def test_over_with_zero_alpha_does_not_erase(self):
        layer = new_layer((8, 8))
        over(layer, (200, 10, 10), np.ones((8, 8)))
        over(layer, (0, 0, 0), np.zeros((8, 8)))        # the aggdraw "erase" attempt
        self.assertTrue(np.allclose(layer[..., 3], 1.0))
        self.assertTrue(np.allclose(layer[..., 0], 200.0))

    def test_ellipse_mask_is_antialiased_disc(self):
        m = ellipse_mask((64, 64), 32, 32, 20, 20)
        self.assertAlmostEqual(float(m[32, 32]), 1.0)
        self.assertEqual(float(m[0, 0]), 0.0)
        self.assertTrue(((m > 0) & (m < 1)).any())

    def test_v2_potion_is_one_piece(self):
        for adir in V2_ASSETS:
            if adir.name == "health_potion_v2":
                self.assertEqual(silhouette_report(adir / "health_potion_v2.png")["components"], 1)


class TileTests(unittest.TestCase):
    def test_periodic_worley_wraps(self):
        w = worley_noise(64, 64, grid_x=4, grid_y=4, seed=3, periodic=True)
        step = np.abs(np.diff(w, axis=1)).mean()
        self.assertLess(np.abs(w[:, 0] - w[:, -1]).mean(), step * 3 + 0.05)
        plain = worley_noise(64, 64, grid_x=4, grid_y=4, seed=3, periodic=False)
        self.assertGreater(np.abs(plain[:, 0] - plain[:, -1]).mean(), np.abs(w[:, 0] - w[:, -1]).mean())

    def test_tileable_normals_have_no_edge_artifact(self):
        y, x = np.mgrid[0:64, 0:64]
        h = 0.5 + 0.4 * np.sin(2 * np.pi * x / 64)
        n = heightmap_to_normal_map(h, strength=2.0, tileable=True).astype(int)
        self.assertLessEqual(int(np.abs(n[:, 0] - n[:, -1]).max()), 3)

    def test_random_noise_tile_is_not_seamless(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.png"
            a = np.random.default_rng(0).integers(0, 255, (64, 64, 3), dtype=np.uint8)
            a[:, -1] = 255 - a[:, 0]
            Image.fromarray(a).save(p)
            with self.assertRaises(ValueError):
                AssetValidator.validate_seamless(p, max_ratio=0.5)

    def test_v2_bricks_seamless(self):
        for name in ("dungeon_bricks_v2.png", "dungeon_bricks_v2_normal.png"):
            AssetValidator.validate_seamless(ROOT / "assets" / "dungeon_bricks_v2" / name, max_ratio=2.0)


class MeshTests(unittest.TestCase):
    def _tower(self):
        b = MeshBuilder(seed=1)
        b.lathe([[0.0, 0.0], [0.5, 0.0], [0.4, 1.0], [0.0, 1.0]], sections=12, color=[200, 200, 200, 255], subdivide=4)
        return b.build()

    def test_ground_ao_darkens_base_and_keeps_palette(self):
        mesh = self._tower()
        self.assertGreater(mesh_ground_darkening(mesh), 0.95)
        with self.assertRaises(ValueError):
            AssetValidator.validate_mesh_shading(mesh)
        bake_ground_ao(mesh, height=0.5, strength=0.5)
        self.assertLess(mesh_ground_darkening(mesh), 0.85)
        AssetValidator.validate_mesh_shading(mesh)
        top = np.asarray(mesh.raw.visual.face_colors)[mesh.raw.triangles_center[:, 2] > 0.9][:, :3]
        self.assertTrue((top >= 195).all(), "AO must not darken the lit top")

    def test_tilted_pyramid_points_along_direction(self):
        b = MeshBuilder()
        b.pyramid(base_radius=0.1, height=1.0, sections=4, direction=[1, 0, 0])
        verts = b.parts[0].vertices
        self.assertGreater(verts[:, 0].max(), 0.95)
        self.assertLess(abs(verts[:, 2]).max(), 0.2)

    def test_preview_is_upright_multi_view(self):
        mesh = trimesh.creation.box(extents=(0.4, 0.4, 2.0))
        mesh.apply_translation([0, 0, 1.0])
        with tempfile.TemporaryDirectory() as d:
            img = MeshBuilder().add_mesh(mesh).build().render_preview(Path(d) / "p.png", size=(200, 200))
        self.assertEqual(img.size, (600, 200))
        front = np.asarray(img.crop((200, 0, 400, 200)).convert("L"), dtype=int)
        ys, xs = np.where(np.abs(front - 18) > 12)
        self.assertGreater(ys.max() - ys.min(), 2.5 * (xs.max() - xs.min()), "tall prop must look tall, not on its side")

    def test_v2_obelisk_watertight_with_ao(self):
        glb = ROOT / "assets" / "mana_obelisk_v2" / "mana_obelisk_v2.glb"
        report = AssetValidator.validate_mesh(glb, max_triangles=3000, watertight=True)
        self.assertTrue(report.metrics["watertight"])


class AnimationTests(unittest.TestCase):
    def _atlas(self, frames):
        cols = 4
        rows = len(frames) // cols
        atlas = np.zeros((rows * 32, cols * 32, 4), dtype=np.uint8)
        for i, f in enumerate(frames):
            r, c = divmod(i, cols)
            atlas[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = f
        return Image.fromarray(atlas, "RGBA")

    def test_static_animation_fails(self):
        frame = np.full((32, 32, 4), 200, dtype=np.uint8)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.png"
            self._atlas([frame] * 8).save(p)
            with self.assertRaises(ValueError):
                AssetValidator.validate_animation(p, 4, 2)

    def test_single_frame_pop_fails(self):
        base = np.zeros((32, 32, 4), dtype=np.uint8)
        frames = []
        for i in range(8):
            f = base.copy()
            f[..., 3] = 255
            f[:, :i + 1, :3] = 120                       # gentle progression
            frames.append(f)
        frames[5][..., :3] = 255                         # sudden jump
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.png"
            self._atlas(frames).save(p)
            with self.assertRaises(ValueError):
                AssetValidator.validate_animation(p, 4, 2, max_motion_ratio=4.0)

    def test_v2_burst_animates_smoothly(self):
        atlas = ROOT / "assets" / "arcane_burst_v2" / "arcane_burst_v2.png"
        AssetValidator.validate_animation(atlas, 4, 4)
        self.assertEqual(len(frame_motion_profile(atlas, 4, 4)), 16)

    def test_v2_burst_is_deterministic_across_runs(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("burst_v2", ROOT / "assets" / "arcane_burst_v2" / "generate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        a = mod.generate_flipbook(frames=16, size=128, seed=7).pack_atlas(4)
        b = mod.generate_flipbook(frames=16, size=128, seed=7).pack_atlas(4)
        self.assertTrue(np.array_equal(np.asarray(a), np.asarray(b)))
        stack = mod.make_arcane_stack(seed=7)
        f1 = np.asarray(stack.composite_frame(0.5))
        f2 = np.asarray(stack.composite_frame(0.5))
        self.assertTrue(np.array_equal(f1, f2), "same phase must render identically (no per-call RNG)")


class SfxManifestTests(unittest.TestCase):
    def test_bell_manifest_records_measured_constants(self):
        data = json.loads((ROOT / "assets" / "crystal_bell_chime_v2" / "manifest.json").read_text())
        for key in ("haas_ms", "click_hz", "f0_hz", "pan"):
            self.assertIn(key, data["parameters"])


if __name__ == "__main__":
    unittest.main()
