# Procedural Fabric and Textile Weave Patterns

Formulas for procedural cloth, canvas, burlap, and wool weave textures for characters, dolls, and flags.

---

## 1. Mathematical Weave Model (Plain Weave)

In a plain textile weave, warp threads (vertical along $Y$) and weft threads (horizontal along $X$) alternately cross over and under one another in a checkerboard sequence:

Let $k_x, k_y$ be thread spatial frequencies (threads per unit length):
$$\theta_x = 2\pi k_x x, \quad \theta_y = 2\pi k_y y$$

The height modulation of the warp thread:
$$h_{\text{warp}}(x, y) = \cos(\theta_x) \cdot \sin(\theta_y)$$

The height modulation of the weft thread:
$$h_{\text{weft}}(x, y) = \sin(\theta_x) \cdot \cos(\theta_y)$$

The composite weave surface profile:
$$H_{\text{weave}}(x, y) = \frac{1}{2}\left(h_{\text{warp}}(x, y) - h_{\text{weft}}(x, y)\right) + \frac{1}{2}$$
- Values near $1.0$ indicate the top crown of an overlying thread.
- Values near $0.0$ indicate the deep crevice where threads plunge underneath.

---

## 2. Generating PBR Maps for Fabric

1. **Albedo / BaseColor**:
   - Blend base yarn dye color with slight thread shading:
     $$\mathbf{C}(x, y) = \mathbf{C}_{\text{dye}} \times (0.85 + 0.15 \cdot H_{\text{weave}})$$
2. **Normal Map**:
   - Pass $H_{\text{weave}}$ directly into `heightmap_to_normal_map(H_weave, strength=2.5)`.
   - Produces authentic micro-creased textile tangent normals.
3. **Roughness Map**:
   - Real cloth has micro-fibers (fuzz) that scatter light uniformly. Set Roughness to $0.80\text{--}0.95$. Never make cloth glossy (Roughness < 0.4) unless waxed canvas or vinyl.

---

## 3. Python Usage in `asset_pipeline`

```python
from asset_pipeline import procedural_fabric_weave, heightmap_to_normal_map

# 1. Generate height pattern
weave_height = procedural_fabric_weave(width=256, height=256, thread_density=32, roughness=0.15, seed=7)

# 2. Derive normal map
fabric_normal = heightmap_to_normal_map(weave_height, strength=2.0)
```
