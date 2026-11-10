# Spherical Normal Bending for Foliage and Tree Canopies

The industry standard technique used in *The Legend of Zelda: Breath of the Wild*, *Ghibli*, and *Unreal Engine* foliage pipelines to give flat leaf cards lush, volumetric 3D lighting.

---

## 1. The "Flat Paper" Foliage Problem

When building trees or bushes out of low-poly alpha cards (planes with leaf textures):
- Each flat plane polygon has a single planar normal vector perpendicular to its surface.
- In-game directional lighting hits each flat card abruptly—one card is fully bright white, while the card next to it is in pitch black shadow.
- The tree looks like an artificial cluster of flat, paper origami planes with jagged, broken lighting across the canopy.

---

## 2. The Spherical Normal Solution

Instead of retaining the card's native perpendicular normal, **the vertex normals are edited to point radially outward from the canopy center** as if the entire tree crown were a solid sphere:

Given tree canopy bounding center $\mathbf{C} = (c_x, c_y, c_z)$ and vertex position $\mathbf{P}_v$:
$$\vec{N}_v = \frac{\mathbf{P}_v - \mathbf{C}}{\|\mathbf{P}_v - \mathbf{C}\|}$$

### The Visual Result
- Directional sun light hits the top of the canopy smoothly, creating a soft, broad, spherical highlight across hundreds of disjointed leaf cards.
- The underside of the canopy gracefully falls off into ambient shade.
- The "card" nature of the geometry vanishes completely, giving the tree a lush, dense, volumetric presence with zero extra polygon cost.

---

## 3. Python Usage in `asset_pipeline`

```python
from asset_pipeline import apply_spherical_normals

# tree_mesh contains trunk plus clustered leaf cards
apply_spherical_normals(
    mesh=tree_mesh,
    center=[0.0, 0.0, 3.5]  # Center of tree foliage crown
)
```
