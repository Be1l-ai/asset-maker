# Hybrid Mesh + Flipbook Explosions

How modern stylized anime games (*Guilty Gear*, *Genshin Impact*, *Hi-Fi Rush*) construct explosions by combining 3D mesh geometry with 2D sprite flipbooks.

---

## 1. The Limitation of Pure 2D Flipbooks

A purely flat 2D sprite particle billboard:
- Looks flat and paper-thin when viewed at glancing or oblique camera angles.
- Lacks physical 3D volume, self-shadowing, and directional silhouette depth.

Professional game VFX artists solve this by pairing a **rapidly expanding 3D solid mesh cluster** at the epicenter with a **camera-facing particle flipbook** for detailed smoke and sparks.

---

## 2. Multi-Sphere Cluster Mesh Architecture

An anime explosion core is built from a cluster of low-poly icospheres (6 to 12 overlapping spheres) centered around the ignition origin:

1. **Initial Ignition ($t = 0.0\text{--}0.15$)**:
   - Single central sphere scales up aggressively using `Easing.ease_out` ($1 - (1-t)^2$).
   - Vertex colors are pure white-hot (`[255, 255, 255]`).
2. **Radial Cluster Expansion ($t = 0.15\text{--}0.60$)**:
   - 6 to 8 sub-spheres spawn along eccentric radial vectors, expanding outward while their individual radii decrease.
   - Creates the chunky, bubble-like silhouette characteristic of anime smoke clouds.
   - Vertex color shifts from hot yellow (`[255, 220, 80]`) to vibrant orange-red (`[255, 80, 40]`).
3. **Erosion & Dissolve ($t = 0.60\text{--}1.00$)**:
   - Spheres shrink rapidly to zero volume, handing off the visual trail to the particle flipbook plume.

---

## 3. Python Usage in `asset_pipeline`

```python
from asset_pipeline import create_expanding_mesh_explosion

# Generate the 3D solid explosion mesh for a specific animation phase t in [0..1]
explosion_mesh = create_expanding_mesh_explosion(
    phase=0.35,
    num_spheres=8,
    base_radius=0.5,
    seed=7
)

# Export to GLB for engine inspection or multi-frame sequence
explosion_mesh.export("explosion_core_frame_05.glb")
```
