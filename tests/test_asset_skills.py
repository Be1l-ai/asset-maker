import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills" if (ROOT / "skills").is_dir() else ROOT / ".qoder" / "skills"
STARTERS = {
    "sfx": ("create-sfx/scripts/synthesize.py", []),
    "vfx": ("create-vfx/scripts/render.py", ["--size", "64"]),
    "2d": ("create-2d-assets/scripts/draw.py", ["--size", "64"]),
    "3d": ("create-3d-assets/scripts/build.py", []),
}


def load_script(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, SKILLS / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_and_resources(self):
        expected = {"create-game-assets", "create-sfx", "create-vfx", "create-2d-assets", "create-3d-assets"}
        self.assertTrue(expected <= {p.name for p in SKILLS.iterdir() if p.is_dir()})
        for name in expected:
            with self.subTest(skill=name):
                path = SKILLS / name / "SKILL.md"
                text = path.read_text()
                match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
                self.assertIsNotNone(match)
                fields = dict(line.split(": ", 1) for line in match[1].splitlines())
                self.assertEqual(fields["name"], name)
                self.assertRegex(name, r"^[a-z0-9-]+$")
                self.assertTrue(0 < len(fields["description"]) <= 1024)
                self.assertLess(len(text[match.end():].splitlines()), 500)
                for target in re.findall(r"\]\(([^)]+)\)", text):
                    if "://" not in target:
                        self.assertTrue((path.parent / target.split("#")[0]).exists(), target)
                for resource in path.parent.rglob("*"):
                    if resource.is_file() and resource.suffix in (".py", ".md"):
                        self.assertNotIn("TODO:", resource.read_text())
                        self.assertNotIn(resource.name, ["README.md", "CHANGELOG.md"])


class RecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audio = load_script(STARTERS["sfx"][0])
        cls.vfx = load_script(STARTERS["vfx"][0])
        cls.raster = load_script(STARTERS["2d"][0])
        cls.validator = load_script("create-game-assets/scripts/validate_asset.py")

    def test_audio_seed_and_encoding(self):
        first = self.audio.synthesize(seed=3)
        self.assertEqual(first.dtype, np.dtype("int16"))
        self.assertEqual(first.shape, (57600,))
        np.testing.assert_array_equal(first, self.audio.synthesize(seed=3))
        self.assertFalse(np.array_equal(first, self.audio.synthesize(seed=4)))
        self.assertEqual(first[0], 0)
        self.assertEqual(first[-1], 0)

    def test_audio_headroom_and_quiet_gain(self):
        loud = self.audio.synthesize(gain=2)
        quiet = self.audio.synthesize(gain=0.05)
        self.assertLessEqual(np.max(np.abs(loud.astype(float))), 32767 * 10 ** (-3 / 20) + 1)
        self.assertLess(np.max(np.abs(quiet)), np.max(np.abs(loud)) / 4)

    def test_all_materials_and_short_audio(self):
        for material in self.audio.MODES:
            for rate in [22050, 48000]:
                pcm = self.audio.synthesize(duration=0.08, rate=rate, material=material)
                self.assertEqual(len(pcm), round(0.08 * rate))
                self.assertGreater(np.max(np.abs(pcm)), 0)

    def test_vfx_periodicity_and_seed(self):
        first = np.asarray(self.vfx.frame(64, 0, 7))
        np.testing.assert_array_equal(first, np.asarray(self.vfx.frame(64, 1, 7)))
        np.testing.assert_array_equal(first, np.asarray(self.vfx.frame(64, 0, 7)))
        self.assertFalse(np.array_equal(first, np.asarray(self.vfx.frame(64, 0, 8))))
        self.assertEqual(first[:, :, 3].min(), 0)
        self.assertEqual(first[0, :, 3].max(), 0)

    def test_vfx_wrap_change_is_not_an_outlier(self):
        frames = [np.asarray(self.vfx.frame(64, i / 16, 7), dtype=float) for i in range(16)]
        deltas = [np.mean(np.abs(frames[(i + 1) % 16] - frames[i])) for i in range(16)]
        self.assertGreater(min(deltas), 0)
        self.assertLess(deltas[-1], 2 * np.mean(deltas[:-1]))

    def test_raster_determinism_transparency_and_seed(self):
        for size in [32, 64]:
            image = self.raster.draw_icon(size, 7)
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.size, (size, size))
            pixels = np.asarray(image)
            np.testing.assert_array_equal(pixels, np.asarray(self.raster.draw_icon(size, 7)))
            self.assertFalse(np.array_equal(pixels, np.asarray(self.raster.draw_icon(size, 8))))
            self.assertEqual(pixels[0, :, 3].max(), 0)
            self.assertGreater(pixels[:, :, 3].max(), 0)

    def test_validator_rejects_silence_clipping_and_nonfinite_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.wav"
            for samples in [np.zeros(100, dtype=np.int16), np.full(100, 32767, dtype=np.int16),
                            np.full(100, np.nan, dtype=np.float32)]:
                wavfile.write(path, 48000, samples)
                with self.assertRaises(ValueError):
                    self.validator.inspect_wav(path)

    def test_stereo_duration_uses_frames_not_sample_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stereo.wav"
            wavfile.write(path, 48000, np.full((4800, 2), 100, dtype=np.int16))
            metrics = self.validator.inspect_wav(path)
            self.assertEqual(metrics["channels"], 2)
            self.assertAlmostEqual(metrics["duration_seconds"], 0.1)

    def test_validator_rejects_bad_alpha_and_grid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.png"
            Image.new("RGBA", (32, 32)).save(path)
            with self.assertRaises(ValueError):
                self.validator.inspect_png(path)
            Image.new("RGB", (32, 32), "white").save(path)
            with self.assertRaises(ValueError):
                self.validator.inspect_png(path, require_alpha=True)
            with self.assertRaises(ValueError):
                self.validator.inspect_png(path, columns=3)
            with self.assertRaises(ValueError):
                self.validator.inspect_png(path, columns=0)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name)
        cls.validator = load_script("create-game-assets/scripts/validate_asset.py")
        for kind, (script, arguments) in STARTERS.items():
            result = subprocess.run([sys.executable, str(SKILLS / script), "--out", str(cls.output / kind), *arguments],
                                    cwd=ROOT, text=True, capture_output=True, timeout=120)
            if result.returncode:
                raise AssertionError(f"{kind}: {result.stderr}")

    def test_manifests_and_recipe_provenance(self):
        for kind, (script, _) in STARTERS.items():
            with self.subTest(kind=kind):
                folder = self.output / kind
                metadata = json.loads((folder / "manifest.json").read_text())
                self.assertTrue(metadata["versions"])
                self.assertEqual(metadata["parameters"]["seed"], 7)
                self.assertEqual((folder / "recipe.py").read_bytes(), (SKILLS / script).read_bytes())
                for name, expected in metadata["sha256"].items():
                    self.assertFalse(Path(name).is_absolute())
                    self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), expected)

    def test_exports_pass_structural_validation(self):
        audio = self.validator.inspect_wav(self.output / "sfx" / "impact.wav")
        self.assertEqual(audio["sample_rate"], 48000)
        self.assertEqual(audio["channels"], 1)
        self.validator.inspect_png(self.output / "vfx" / "portal.png", True, 4, 4)
        self.validator.inspect_png(self.output / "2d" / "potion.png", True)
        for extension in ["glb", "obj"]:
            metrics = self.validator.inspect_mesh(self.output / "3d" / f"prop.{extension}", 3000, True)
            self.assertTrue(metrics["winding_consistent"])
            self.assertGreater(metrics["triangles"], 12)

    def test_atlas_metadata_and_animation(self):
        folder = self.output / "vfx"
        metadata = json.loads((folder / "manifest.json").read_text())
        self.assertEqual(metadata["grid"], [4, 4])
        self.assertEqual(metadata["frame_count"], 16)
        with Image.open(folder / "preview.gif") as preview:
            self.assertEqual(preview.n_frames, 16)
        with Image.open(folder / "portal.png") as atlas:
            for i in range(16):
                cell = atlas.crop((i % 4 * 64, i // 4 * 64, (i % 4 + 1) * 64, (i // 4 + 1) * 64))
                self.assertIsNotNone(cell.getchannel("A").getbbox())

    def test_export_axes_and_seeded_geometry(self):
        import trimesh

        model = load_script(STARTERS["3d"][0])
        source = model.build_model(seed=7)
        np.testing.assert_allclose(source.vertices, model.build_model(seed=7).vertices)
        exported = trimesh.load_scene(self.output / "3d" / "prop.glb", process=False).to_mesh()
        np.testing.assert_allclose(exported.extents, source.extents[[0, 2, 1]], rtol=1e-5, atol=1e-6)
        self.assertAlmostEqual(float(exported.bounds[0, 1]), 0, places=5)

    def test_saved_recipes_reproduce_asset_content(self):
        for kind, asset in [("sfx", "impact.wav"), ("vfx", "portal.png"), ("2d", "potion.png"), ("3d", "prop.obj")]:
            with self.subTest(kind=kind):
                folder = self.output / kind
                rerun = self.output / f"{kind}-rerun"
                arguments = STARTERS[kind][1]
                result = subprocess.run([sys.executable, str(folder / "recipe.py"), "--out", str(rerun), *arguments],
                                        text=True, capture_output=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((folder / asset).read_bytes(), (rerun / asset).read_bytes())

    def test_existing_output_is_not_overwritten(self):
        for kind, (script, arguments) in STARTERS.items():
            with self.subTest(kind=kind):
                folder = self.output / kind
                before = {p.name: p.read_bytes() for p in folder.iterdir()}
                result = subprocess.run([sys.executable, str(SKILLS / script), "--out", str(folder), *arguments],
                                        text=True, capture_output=True, timeout=120)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_invalid_seed_fails_without_output(self):
        for kind, (script, _) in STARTERS.items():
            with self.subTest(kind=kind):
                folder = self.output / f"{kind}-invalid"
                result = subprocess.run([sys.executable, str(SKILLS / script), "--out", str(folder), "--seed", "-1"],
                                        text=True, capture_output=True, timeout=120)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(folder.exists())

    def test_mesh_budget_is_enforced(self):
        with self.assertRaises(ValueError):
            self.validator.inspect_mesh(self.output / "3d" / "prop.glb", max_triangles=1)


if __name__ == "__main__":
    unittest.main()
