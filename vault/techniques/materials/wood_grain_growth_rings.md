# Procedural Wood Grain and Annual Growth Rings

Formulas for concentric cylindrical growth rings, earlywood/latewood density transitions, and medullary ray perturbations.

---

## 1. Mathematical Botanical Growth Model

A tree trunk grows radially via annual rings centered around a pith origin $(c_x, c_y)$. When sawn into planks, the cut surface intersects these concentric growth cylinders at oblique angles:

### Eccentric Radial Distance
Planks sawn off-center experience elliptical ring elongation:
$$\Delta x = x - c_x, \quad \Delta y = \alpha (y - c_y)$$
where $\alpha \approx 1.5\text{--}2.5$ represents timber cutting obliquity.

### Medullary Ray & Grain Turbulence
Real wood grain is never mathematically circular; it wobbles due to natural fiber deviations around knots:
$$\Delta r(\theta) = A_1 \sin(3\theta + \phi_1) + A_2 \sin(7\theta + \phi_2)$$
$$r_{\text{turbulent}} = \sqrt{\Delta x^2 + \Delta y^2} + \Delta r(\theta)$$

### Asymmetric Annual Ring Density
Each annual ring consists of two phases:
1. **Earlywood (Springwood)**: Wide, low-density, light colored porous wood ($70\text{--}80\%$ of ring width).
2. **Latewood (Summerwood)**: Thin, high-density, dark resinous band ($20\text{--}30\%$ of ring width).

Let $u = (r / w_{\text{ring}}) \pmod 1.0$:
$$G(u) = \begin{cases} \frac{u}{0.75} & \text{if } u < 0.75 \text{ (earlywood rise)} \\ \frac{1.0 - u}{0.25} & \text{if } u \ge 0.75 \text{ (sharp latewood drop)} \end{cases}$$

---

## 2. Python Usage in `asset_pipeline`

```python
from asset_pipeline import procedural_wood_grain, heightmap_to_normal_map

# 1. Generate scalar wood grain field
wood_field = procedural_wood_grain(width=256, height=256, ring_spacing=14.0, wobble=3.5, seed=7)

# 2. Derive normal map for carved wood relief
wood_normal = heightmap_to_normal_map(wood_field, strength=1.5)
```
