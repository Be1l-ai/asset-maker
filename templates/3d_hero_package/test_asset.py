"""Per-asset unit tests verifying spec compliance, glTF hierarchy, and embedded PBR textures."""

from __future__ import annotations

import json
import struct
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in HERE.parents if (p / "asset_pipeline").is_dir()), None)
for p in (HERE, ROOT):
    if p and str(p) not in sys.path:
        sys.path.insert(0, str(p))

import generate


class TestHeroAssetPackage(unittest.TestCase):
    def test_build_and_export_embedded_pbr_glb(self) -> None:
        scene = generate.build(HERE / "spec.json", seed=7)
        stats = scene.validate()
        self.assertEqual(stats["nodes"], 3)
        glb = HERE / f"{generate.ASSET_NAME}.glb"
        scene.export_glb(glb, apply_y_up=True)
        raw = glb.read_bytes()
        jlen, jtype = struct.unpack("<II", raw[12:20])
        self.assertEqual(jtype, 0x4E4F534A)
        gltf = json.loads(raw[20:20 + jlen].decode("utf-8"))
        self.assertEqual([n["name"] for n in gltf["nodes"]], ["Plinth_Base", "Timber_Frame", "Crystal_Core"])
        self.assertGreaterEqual(len(gltf.get("textures", [])), 2)
        self.assertIn("TEXCOORD_0", gltf["meshes"][0]["primitives"][0]["attributes"])


if __name__ == "__main__":
    unittest.main()
