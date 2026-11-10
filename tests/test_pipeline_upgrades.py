"""Unit tests for newly added asset_pipeline mathematical and procedural generators."""

import unittest
import numpy as np
from PIL import Image
from asset_pipeline import (
    heightmap_to_normal_map,
    worley_noise,
    procedural_fabric_weave,
    procedural_wood_grain,
    revolve_profile,
    apply_spherical_normals,
    bake_vertex_gradient_ao,
    create_leaf_card,
    dissolve_alpha_mask,
    create_expanding_mesh_explosion,
    EmitterStack,
    SoundSynthesizer,
    spatial_stereo_pan,
)


class TestPipelineUpgrades(unittest.TestCase):
    def test_heightmap_to_normal_map(self):
        # 64x64 flat plane
        flat = np.full((64, 64), 0.5, dtype=np.float32)
        nmap = heightmap_to_normal_map(flat, strength=1.0)
        self.assertEqual(nmap.shape, (64, 64, 3))
        self.assertEqual(nmap.dtype, np.uint8)
        # Flat surface normal points straight along +Z -> RGB (127/128, 127/128, 255)
        self.assertAlmostEqual(nmap[32, 32, 0], 127, delta=2)
        self.assertAlmostEqual(nmap[32, 32, 1], 127, delta=2)
        self.assertEqual(nmap[32, 32, 2], 255)

        # Sloped ramp along X
        y, x = np.mgrid[0:64, 0:64]
        ramp = x / 64.0
        nmap_ramp = heightmap_to_normal_map(ramp, strength=2.0)
        # Slope along +X means normal tilts left (-X) -> red channel < 127
        self.assertLess(nmap_ramp[32, 32, 0], 120)

    def test_worley_noise(self):
        w = worley_noise(64, 64, grid_x=4, grid_y=4, seed=42)
        self.assertEqual(w.shape, (64, 64))
        self.assertGreaterEqual(float(np.min(w)), 0.0)
        self.assertLessEqual(float(np.max(w)), 1.0)
        self.assertGreater(float(np.std(w)), 0.05)

        # Test Chebyshev and Manhattan
        w_man = worley_noise(32, 32, grid_x=2, grid_y=2, metric="manhattan")
        self.assertEqual(w_man.shape, (32, 32))

    def test_procedural_textures(self):
        fabric = procedural_fabric_weave(64, 64, thread_density=8)
        self.assertEqual(fabric.shape, (64, 64))
        self.assertGreaterEqual(float(np.min(fabric)), 0.0)
        self.assertLessEqual(float(np.max(fabric)), 1.0)

        wood = procedural_wood_grain(64, 64, ring_spacing=8.0)
        self.assertEqual(wood.shape, (64, 64))

    def test_revolve_profile(self):
        # 2D bottle profile [radius, z]
        profile = np.array([
            [0.0, 0.0],
            [0.4, 0.0],
            [0.5, 0.3],
            [0.2, 0.7],
            [0.2, 1.0],
            [0.0, 1.0],
        ])
        mesh = revolve_profile(profile, sections=16, color=[180, 120, 60, 255])
        self.assertTrue(mesh.is_watertight)
        self.assertGreater(mesh.volume, 0.0)
        self.assertGreater(len(mesh.faces), 20)

    def test_spherical_normals(self):
        import trimesh
        box = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
        apply_spherical_normals(box, center=[0.0, 0.0, 0.0])
        # Each normal must point in the direction of vertex position
        for v, n in zip(box.vertices, box.vertex_normals):
            expected = v / np.linalg.norm(v)
            np.testing.assert_allclose(n, expected, atol=1e-3)

    def test_bake_vertex_gradient_ao(self):
        import trimesh
        cyl = trimesh.creation.cylinder(radius=0.5, height=2.0)
        bake_vertex_gradient_ao(cyl, top_color=(255, 255, 255), ground_color=(0, 0, 0))
        vc = cyl.visual.vertex_colors
        self.assertEqual(len(vc), len(cyl.vertices))
        # Top vertices should be brighter than bottom vertices
        z_min_idx = np.argmin(cyl.vertices[:, 2])
        z_max_idx = np.argmax(cyl.vertices[:, 2])
        self.assertGreater(np.mean(vc[z_max_idx][:3]), np.mean(vc[z_min_idx][:3]))

    def test_leaf_card(self):
        card = create_leaf_card(width=0.8, height=1.5, curvature=0.15)
        self.assertEqual(len(card.vertices), 6)
        self.assertEqual(len(card.faces), 4)

    def test_vfx_dissolve_and_mesh(self):
        img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
        dissolved = dissolve_alpha_mask(img, threshold=0.6)
        arr = np.array(dissolved)
        # Should have transparent pixels
        self.assertTrue((arr[:, :, 3] == 0).any())

        mesh_exp = create_expanding_mesh_explosion(phase=0.5, num_spheres=6, base_radius=0.3)
        self.assertGreater(len(mesh_exp.faces), 50)

        stack = EmitterStack(size=64)
        stack.add_layer(lambda phase, size: Image.new("RGBA", (size, size), (255, 0, 0, 100)))
        frame = stack.composite_frame(0.2)
        self.assertEqual(frame.size, (64, 64))

    def test_sfx_resonators_and_stereo(self):
        synth = SoundSynthesizer(rate=48000, seed=7)
        bell = synth.bell_resonator(f0=440.0, duration=0.2)
        wood = synth.wood_resonator(f0=500.0, duration=0.2)
        glass = synth.glass_resonator(f0=800.0, duration=0.2)
        chime = synth.tubular_chime_resonator(f0=600.0, duration=0.2)

        for s in (bell, wood, glass, chime):
            self.assertAlmostEqual(s.duration, 0.2, places=2)
            self.assertFalse(np.isnan(s.samples).any())
            pcm = s.to_pcm16(headroom_db=-3.0)
            self.assertEqual(pcm[0], 0)
            self.assertEqual(pcm[-1], 0)

        stereo = spatial_stereo_pan(bell, pan=0.5, haas_delay_ms=2.0)
        self.assertEqual(stereo.shape, (len(bell.samples), 2))
        # Panned right -> right channel energy > left channel energy
        energy_l = np.sum(stereo[:, 0] ** 2)
        energy_r = np.sum(stereo[:, 1] ** 2)
        self.assertGreater(energy_r, energy_l)


if __name__ == "__main__":
    unittest.main()
