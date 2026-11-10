import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.io import wavfile
import trimesh

from asset_pipeline import generate_gallery_expansion as expansion
from asset_pipeline import gallery_expansion_effects as effects
from asset_pipeline import gallery_expansion_visuals as visuals

ROOT = Path(__file__).resolve().parents[1]


class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix=".expansion-test-", dir=ROOT)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name) / "collection"
        expansion.generate(cls.output)
        cls.assets = json.loads((cls.output / "catalog.json").read_text())["assets"]

    def test_collection_metadata_and_provenance(self):
        self.assertEqual(len(self.assets), 8)
        self.assertEqual(len({a["id"] for a in self.assets}), 8)
        for category in ("3d", "2d", "vfx", "sfx"):
            self.assertEqual(sum(a["category"] == category for a in self.assets), 2)
        for asset in self.assets:
            manifest = json.loads((ROOT / asset["manifest"]).read_text())
            self.assertEqual(manifest["parameters"]["seed"], 19)
            self.assertTrue(manifest["review"])
            self.assertFalse(manifest["engine_import_tested"])
            for filename, digest in manifest["sha256"].items():
                path = (ROOT / asset["manifest"]).parent / filename
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            for relative, digest in manifest["source_dependencies_sha256"].items():
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
            for key in ("file", "recipe", "preview", "manifest", "model", "atlas", "panelPreview"):
                if key in asset:
                    self.assertTrue((ROOT / asset[key]).is_file())

    def test_mesh_export_axes_topology_and_budget(self):
        for asset in self.assets:
            if asset["category"] != "3d":
                continue
            directory = (ROOT / asset["manifest"]).parent
            glb = trimesh.load_scene(directory / "model.glb").to_mesh()
            obj = trimesh.load_scene(directory / "model.obj").to_mesh()
            glb.apply_transform(np.linalg.inv(expansion.base.Z_TO_Y))
            self.assertTrue(np.allclose(glb.bounds, obj.bounds, atol=1e-6))
            self.assertLess(len(glb.faces), 3000)
            self.assertGreater(np.min(glb.area_faces), 1e-10)
            glb.merge_vertices(merge_tex=True, merge_norm=True)
            self.assertTrue(glb.is_volume)
            self.assertAlmostEqual(float(glb.bounds[0, 2]), 0, places=5)

    def test_seed_changes_asset_identity(self):
        for render in (visuals.pine_tree, visuals.treasure_chest):
            a, b = render(seed=19), render(seed=20)
            self.assertFalse(np.array_equal(a.vertices, b.vertices) and np.array_equal(a.visual.face_colors, b.visual.face_colors))
        for render in (visuals.shield_icon, visuals.dialog_panel):
            self.assertFalse(np.array_equal(np.asarray(render(seed=19)), np.asarray(render(seed=20))))
        for render in (effects.dust_puff_frame, effects.lightning_frame):
            self.assertFalse(np.array_equal(np.asarray(render(128, .4, 19)), np.asarray(render(128, .4, 20))))
        for render in (effects.gravel_step, effects.charge_release):
            self.assertFalse(np.array_equal(render(seed=19), render(seed=20)))

    def test_effect_alpha_timing_and_borders(self):
        for asset in self.assets:
            if asset["category"] != "vfx":
                continue
            with Image.open(ROOT / asset["atlas"]) as image:
                pixels = np.asarray(image)
            self.assertEqual(pixels.shape, (512, 512, 4))
            self.assertEqual(asset["frames"] / asset["fps"], 1)
            manifest = json.loads((ROOT / asset["manifest"]).read_text())
            self.assertEqual(manifest["sample_phases"], [i / 15 for i in range(16)])
            for index in range(16):
                row, col = divmod(index, 4)
                alpha = pixels[row * 128:(row + 1) * 128, col * 128:(col + 1) * 128, 3]
                self.assertEqual(max(alpha[0].max(), alpha[-1].max(), alpha[:, 0].max(), alpha[:, -1].max()), 0)
                self.assertEqual(bool(alpha.max()), index not in (0, 15))

    def test_nine_slice_preserves_corners(self):
        source = visuals.dialog_panel(seed=19)
        for width, height in ((768, 256), (256, 192), (128, 128)):
            result = expansion.nine_slice(source, width, height)
            self.assertEqual(result.size, (width, height))
            for left, top in ((False, False), (True, False), (False, True), (True, True)):
                sx, sy = (0 if left else source.width - 64), (0 if top else source.height - 64)
                tx, ty = (0 if left else width - 64), (0 if top else height - 64)
                self.assertTrue(np.array_equal(np.asarray(source.crop((sx, sy, sx + 64, sy + 64))),
                                               np.asarray(result.crop((tx, ty, tx + 64, ty + 64)))))
        with self.assertRaises(ValueError):
            expansion.nine_slice(source, 100, 100)

    def test_audio_headroom_endpoints_and_duration(self):
        for asset in self.assets:
            if asset["category"] != "sfx":
                continue
            rate, samples = wavfile.read(ROOT / asset["file"])
            self.assertEqual(rate, 48000)
            self.assertEqual(samples.dtype, np.int16)
            self.assertEqual(samples.ndim, 1)
            self.assertEqual(samples[0], 0)
            self.assertEqual(samples[-1], 0)
            signal = samples.astype(float) / 32768
            self.assertLessEqual(np.abs(signal).max(), 10 ** (-3 / 20) + 1 / 32768)
            self.assertLess(abs(signal.mean()), .001)
            self.assertAlmostEqual(len(samples) / rate, asset["duration"])

    def test_output_refusal_and_invalid_seed(self):
        before = (self.output / "catalog.json").read_bytes()
        with self.assertRaises(FileExistsError):
            expansion.generate(self.output)
        self.assertEqual(before, (self.output / "catalog.json").read_bytes())
        invalid = Path(self.temp.name) / "invalid"
        with self.assertRaises(ValueError):
            expansion.generate(invalid, seed=-1)
        self.assertFalse(invalid.exists())

    def test_extracted_pack_reproduces_exports(self):
        with tempfile.TemporaryDirectory(prefix="expansion-reproduce-") as temporary:
            extracted = Path(temporary)
            with zipfile.ZipFile(self.output / "asset-collection.zip") as archive:
                self.assertIsNone(archive.testzip())
                self.assertFalse(any(".venv" in name or "output/sfx" in name for name in archive.namelist()))
                self.assertTrue(all(relative in archive.namelist() for relative in expansion.SOURCES))
                archive.extractall(extracted)
            result = subprocess.run([sys.executable, str(extracted / expansion.RECIPE), "--out", "repeat"],
                                    cwd=extracted, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            for asset in self.assets:
                original = (ROOT / asset["manifest"]).parent
                regenerated = extracted / "repeat" / "assets" / asset["id"]
                for path in original.iterdir():
                    if path.name == "manifest.json":
                        continue
                    self.assertEqual(path.read_bytes(), (regenerated / path.name).read_bytes(), f"Changed {asset['id']}/{path.name}")


if __name__ == "__main__":
    unittest.main()
