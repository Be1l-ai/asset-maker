# Bevels, Chamfers, and Edge Weight

How stylized 3D and 2D modeling uses exaggerated chamfers, turned lathe profiles, and morphological fillets to catch broad highlights without dense normal maps (`assets/mana_obelisk_v2`, `assets/health_potion_v2`).

---

## 1. Why Microscopic Photoreal Bevels Fail in Stylized Art

In photorealistic PBR pipelines, bevels are kept microscopic ($0.1\text{--}1.0\text{ mm}$) to simulate milled steel, relying on $4\text{K}$ normal maps to catch hair-thin reflections.

In stylized and low-poly game art (*World of Warcraft*, *Torchlight*, *Ghibli*):
- Micro-bevels vanish at gameplay camera distances, degenerating into jagged, aliased silhouettes.
- Instead, artists construct **chunky, exaggerated chamfers** ($45^\circ$ planar cuts in 3D or smooth SDF fillets in 2D) directly in the silhouette and surface geometry.

---

## 2. The Mechanics of the Stylized Bevel

A stylized bevel serves three graphic purposes:
1. **Highlight Catcher**: Broad $45^\circ$ chamfer collars reflect directional key-light into the camera, outlining 3D forms with natural rim highlights.
2. **Hand-Carved / Cast Tactility**: Softens harsh $90^\circ$ CG corners, giving solids a chiseled stone, turned wood, or blown-glass physical presence.
3. **Silhouette Break**: Breaks up monotonous straight lines with intentional stepped facets or smooth neck-to-body transitions.

---

## 3. Geometric Guidelines & `asset_pipeline` Implementation

- **3D Turned Plinths & Obelisks (`MeshBuilder.lathe`)**: Define a 2D $(r, z)$ profile with explicit $45^\circ$ chamfer steps and recessed undercuts, then revolve with `segments=4` (square/octagonal monument) or `segments=16` (cylindrical vessel) and `subdivide=3` for watertight manifold density.
- **2D Silhouette Filleting (`fillet_mask`)**: When combining primitive 2D masks (such as a rectangular flask neck and elliptical bulb), apply Euclidean morphological closing (`fillet_mask(mask, radius=16)`) to bridge sharp concavities with a smooth tangent arc.

```python
from asset_pipeline import MeshBuilder, ellipse_mask, fillet_mask, polygon_mask

# 1. 3D Chamfered Monument Profile via MeshBuilder.lathe
builder = MeshBuilder()
profile = [
    (0.85, 0.00),  # Base footprint
    (0.82, 0.18),  # Plinth wall
    (0.66, 0.26),  # 45-degree chamfer step (catches overhead key light)
    (0.62, 0.50),  # Upper tier
]
pedestal = builder.lathe(profile, segments=4, subdivide=3, color=(65, 68, 82, 255))

# 2. 2D Smooth Neck-to-Bulb Fillet via fillet_mask
bulb = ellipse_mask(512, 512, cx=256, cy=310, rx=135, ry=130)
neck = polygon_mask(512, 512, [(216, 125), (296, 125), (304, 205), (208, 205)])
smooth_vessel = fillet_mask(bulb | neck, radius=16)
```
