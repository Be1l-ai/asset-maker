"""Per-asset unit test for sky_galleon_hero."""

import json, struct, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in HERE.parents if (p / "asset_pipeline").is_dir()), None)
for p in (HERE, ROOT):
    if p and str(p) not in sys.path:
        sys.path.insert(0, str(p))
import generate


class TestSkyGalleonHero(unittest.TestCase):
    def test_hero_floor_and_embedded_pbr(self) -> None:
        scene = generate.build(HERE / "spec.json", seed=7)
        stats = scene.validate()
        self.assertGreaterEqual(stats["triangles"], 10000)
        self.assertGreaterEqual(stats["nodes"], 12)
        glb = HERE / "sky_galleon_hero.glb"
        scene.export_glb(glb, apply_y_up=True)
        raw = glb.read_bytes()
        jlen, _ = struct.unpack("<II", raw[12:20])
        gltf = json.loads(raw[20:20 + jlen].decode("utf-8"))
        self.assertEqual(len(gltf["nodes"]), 14)
        self.assertEqual(len(gltf["textures"]), 8)


if __name__ == "__main__":
    unittest.main()
