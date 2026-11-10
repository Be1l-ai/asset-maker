# Spherical Normal Bending and Curved Alpha Cards for Foliage

The industry-standard techniques used in *The Legend of Zelda: Breath of the Wild*, *Ghibli*, and *Unreal Engine* foliage pipelines to give low-poly leaf cards lush, volumetric 3D lighting without overdraw.

---

## 1. The "Flat Paper" Foliage & Overdraw Problems

When building trees, bushes, or fern fronds out of low-poly planes:
- **Flat Planar Normals**: Each flat card has a single normal vector perpendicular to its surface. Directional lighting hits each card abruptly—one card is bright white while the adjacent card is in pitch-black shadow, making the canopy look like jagged paper origami.
- **Quad Overdraw**: A flat 4-vertex square quad where the leaf occupies only a narrow strip leaves $60\text{--}80\%$ transparent pixels ($\alpha = 0$), causing severe GPU alpha-discard overdraw and razor-thin silhouettes when viewed edge-on.

---

## 2. Curved Segmented Alpha Cards (`create_leaf_card`)

Instead of a flat 4-vertex quad, introduce a longitudinal spine down the center of the card and displace the center ridge along $Y$ by curvature ratio $\kappa \in [0.10, 0.20]$:

```
v0 ---- v2 ---- v4 (tip)
 \      /      /
  \    /      /
v1 ---- v3 ---- v5
```

- Eliminates razor-flat vanishing silhouettes when viewed from grazing camera angles.
- Tightly bounds the organic leaf cluster contour to minimize empty transparent corners.

---

## 3. Spherical Normal Projection (`apply_spherical_normals`)

Instead of retaining each card's native perpendicular normal, **project the vertex normals radially outward from the canopy center** as if the entire tree crown were a continuous sphere:

Given tree canopy bounding center $\mathbf{C} = (c_x, c_y, c_z)$ and vertex position $\mathbf{P}_v$:
$$\vec{N}_v = \frac{\mathbf{P}_v - \mathbf{C}}{\|\mathbf{P}_v - \mathbf{C}\|}$$

### The Visual Result
- Directional sunlight sweeps smoothly across the top of the canopy, creating a unified spherical highlight across hundreds of individual leaf cards.
- The underside of the canopy falls off gracefully into ambient shade with zero extra polygon cost.

---

## 4. Python Usage in `asset_pipeline`

```python
from asset_pipeline import apply_spherical_normals, create_leaf_card

# 1. Create a curved low-poly leaf card with natural spine camber
leaf_card = create_leaf_card(
    width=0.6,
    height=1.2,
    curvature=0.12,
    color=[80, 180, 70, 255],
)

# 2. Project normals radially outward from the foliage crown center
apply_spherical_normals(
    mesh=leaf_card,
    center=[0.0, 0.0, 0.5],
)
```
