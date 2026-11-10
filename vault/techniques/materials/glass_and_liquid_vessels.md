# Glass Vessels, Refracted Liquids, and Subsurface Glow

Mathematical formulations and procedural 2D SDF layer recipes for thick-walled blown glass flasks, refracted potions, meniscus capillary rims, and normal-map height domes.

---

## 1. Schlick Fresnel Rim Opacity & Wall Thickness

In physical optics, a dielectric sphere or cylinder viewed at angle $\theta$ between the surface normal $\mathbf{N}$ and view vector $\mathbf{V}$ exhibits Fresnel reflectance approximated by **Schlick's (1994) formula**:

$$F(\theta) = F_0 + (1 - F_0)(1 - \cos\theta)^5, \quad F_0 = \left(\frac{\eta_1 - \eta_2}{\eta_1 + \eta_2}\right)^2$$

For crown or borosilicate potion glass ($\eta_2 \approx 1.50\text{--}1.52$ in air $\eta_1 = 1.0$), normal-incidence reflectance is $F_0 \approx 0.04$ ($4\%$), climbing toward $1.0$ at grazing silhouettes ($\cos\theta \to 0$). Simultaneously, the optical path length through a hollow glass shell of outer radius $R$ and inner radius $R - \tau_{\text{wall}}$ peaks at the inner wall tangency.

### 2D SDF Depth Approximation (`inside_depth`)
In a 2D supersampled mask pipeline, let $d(\mathbf{p}) = \operatorname{inside\_depth}(\text{glass\_mask})$ be the Euclidean pixel distance from the outer vessel silhouette. Defining the rim wall thickness $\tau_{\text{rim}} \approx 0.09\,R$:

$$r_{\text{rim}}(\mathbf{p}) = \operatorname{clamp}\!\left(\frac{d(\mathbf{p})}{\tau_{\text{rim}}}, 0, 1\right)$$

The glass body opacity and Fresnel rim brightness are modeled as:

$$\alpha_{\text{glass}}(\mathbf{p}) = \alpha_{\min} + (\alpha_{\max} - \alpha_{\min})(1 - r_{\text{rim}}(\mathbf{p}))^2$$

| Parameter | Physical / Stylized Range | Description |
| :--- | :--- | :--- |
| $\alpha_{\min}$ | $0.25\text{--}0.35$ (`int: 72–90`) | Center-cavity transmission alpha (clear view into interior) |
| $\alpha_{\max}$ | $0.82\text{--}0.92$ (`int: 210–235`) | Grazing Fresnel rim alpha (thick refractive glass wall) |
| $\tau_{\text{rim}} / R$ | $0.08\text{--}0.12$ | Apparent glass wall thickness ratio |

---

## 2. Beer-Lambert Absorption & Converging Lens Core Glow

Light traversing an absorbing dye solution of concentration-dependent extinction coefficient $\boldsymbol{\sigma}_a = (\sigma_R, \sigma_G, \sigma_B)$ attenuates exponentially via the **Beer-Lambert Law**:

$$\mathbf{T}(s) = \exp(-\boldsymbol{\sigma}_a s)$$

Because a spherical flask Filled with liquid ($\eta_{\text{liquid}} \approx 1.33\text{--}1.36$) acts as a **converging ball lens**, incident key-light is refracted and focused through the interior toward the opposite inner hemisphere, while the peripheral liquid contact zone undergoes longer absorption paths and total internal reflection (TIR).

In 2D distance-field space using `inside_depth(liquid_mask)`:
1. **Peripheral Edge Darkening (Absorption + Contact Shadow)**:
   $$\mathbf{C}_{\text{body}}(\mathbf{p}) = \operatorname{lerp\_color}\!\left(\mathbf{C}_{\text{deep}}, \mathbf{C}_{\text{mid}}, \operatorname{clamp}\!\left(\frac{d_{\text{liq}}(\mathbf{p})}{\tau_{\text{absorb}}}, 0, 1\right)\right)$$
2. **Focused Subsurface Core Glow**:
   Offsetting an interior ellipse toward the lower-right focal zone $\mathbf{c}_{\text{glow}} = \mathbf{c}_{\text{bulb}} + (0.04\,R, 0.08\,R)$ produces the luminous caustic heart:
   $$I_{\text{core}}(\mathbf{p}) = \operatorname{clamp}\!\left(\frac{d_{\text{core}}(\mathbf{p})}{0.55\,R}, 0, 1\right)$$
   $$\mathbf{C}_{\text{liq}}(\mathbf{p}) = \operatorname{lerp\_color}\!\left(\mathbf{C}_{\text{body}}(\mathbf{p}), \mathbf{C}_{\text{core}}, 0.85 \cdot I_{\text{core}}(\mathbf{p})\right)$$

For crimson health potions:
- $\mathbf{C}_{\text{deep}} = (78, 8, 28)$ (violet-shifted carmine edge)
- $\mathbf{C}_{\text{mid}} = (195, 22, 52)$ (saturated ruby body)
- $\mathbf{C}_{\text{core}} = (255, 115, 75)$ (warm orange-vermilion subsurface focus)

---

## 3. Liquid Meniscus & Capillary Rim Catch-Light

By the **Young-Laplace capillary equation**, an aqueous liquid wets a hydrophilic silicate glass wall with contact angle $\theta_c < 90^\circ$, curving upward at the boundary over capillary length $\lambda_c = \sqrt{\gamma / (\Delta\rho g)} \approx 2.7\text{ mm}$.

In 2D orthographic/perspective-tilted icon rendering:
- Represent the free liquid surface as a shallow horizontal ellipse at fill line $y = y_{\text{fill}}$ with vertical semi-axis $r_y \approx 0.10\,R\text{--}0.14\,R$, clipped strictly to the inner cavity mask ($d_{\text{glass}} > \tau_{\text{wall}}$).
- Shade the meniscus plane one value step brighter and warmer than the bulk liquid ($\mathbf{C}_{\text{meniscus}} = (255, 95, 125)$) because overhead light strikes the horizontal interface at near-normal incidence, and add a $1\text{--}2\text{ px}$ specular rim along the front lip.

---

## 4. Dual Specular Architecture: Primary Crescent vs. Secondary Bounce

Curved dielectric vessels require two distinct reflection reads on opposite quadrants:

1. **Primary Front-Surface Specular (Upper-Left Lit Quadrant)**:
   - Driven by direct key-light reflection off the outer air-glass interface.
   - Constructed by subtracting an offset inner ellipse from an outer ellipse inside the bulb and confining to normalized radial band $u \in [0.80, 0.86]$.
   - Crisp, high-opacity achromatic white $(255, 250, 255)$ at $\alpha \approx 210\text{--}230$.
2. **Secondary Internal Bounce Highlight (Lower-Right Opposite Wall)**:
   - Unattenuated rays transmitted through the liquid reflect off the back-right inner glass-air boundary.
   - Positioned in the opposite quadrant ($u \in [0.86, 0.90]$), broader, softer ($\alpha \approx 90\text{--}120$), and tinted by the transmitted medium (e.g., rose-pink $(255, 160, 190)$ for red liquid, ice-cyan $(215, 240, 255)$ for empty glass).

---

## 5. Analytical Normal-Map Height Dome

To generate a companion tangent-space normal map (`*_normal.png`) via [`heightmap_to_normal_map`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/sprite2d.py), map the vessel's interior SDF distance $d(\mathbf{p})$ into a pseudo-spherical height dome:

$$z(\mathbf{p}) = \sqrt{\operatorname{clamp}\!\left(1 - \left(1 - \operatorname{clamp}\!\left(\frac{d(\mathbf{p})}{R_{\text{dome}}}, 0, 1\right)\right)^2, 0, 1\right)}$$

Increment $z(\mathbf{p})$ slightly across raised metallic collar bands ($\Delta z \approx +0.08$) and cork stoppers before running the $3 \times 3$ Sobel operator.

---

## 6. Python Usage in `asset_pipeline`

```python
import numpy as np
from asset_pipeline import (
    ellipse_mask,
    fillet_mask,
    heightmap_to_normal_map,
    inside_depth,
    lerp_color,
    new_layer,
    over,
    polygon_mask,
)

# 1. Construct unified glass silhouette with morphological corner filleting
S = 512
bulb = ellipse_mask(S, S, cx=256, cy=310, rx=135, ry=130)
neck = polygon_mask(S, S, [(216, 125), (296, 125), (304, 205), (208, 205)])
glass_mask = fillet_mask(bulb | neck, radius=16)

# 2. Compute SDF interior depth for Fresnel wall and inner cavity
depth = inside_depth(glass_mask)
rim_t = np.clip(depth / 18.0, 0.0, 1.0)
cavity_mask = depth > 16.0

# 3. Render Fresnel glass shell and Beer-Lambert liquid core
canvas = new_layer(S, S)
glass_alpha = np.where(glass_mask, (78 + (1.0 - rim_t) ** 2 * 142).astype(np.uint8), 0)
glass_rgb = lerp_color((140, 195, 230), (220, 245, 255), (1.0 - rim_t) ** 1.6)
canvas = over(canvas, np.dstack([glass_rgb, glass_alpha]))

# 4. Derive spherical height dome and export tangent-space normal map
height = np.where(glass_mask, np.sqrt(np.clip(1.0 - (1.0 - np.clip(depth / 110.0, 0, 1)) ** 2, 0, 1)), 0.0)
normal_map = heightmap_to_normal_map(height, strength=3.5)
```

---

## 7. References
- Schlick, C. (1994). *An Inexpensive BRDF Model for Physically-Based Rendering*. Computer Graphics Forum, 13(3), 233–246.
- Akenine-Möller, T., Haines, E., & Hoffman, N. (2018). *Real-Time Rendering* (4th ed., Ch. 9 & 14: Refraction, Beer-Lambert Absorption, and Translucency). CRC Press.
- Quilez, I. (2018). *2D Signed Distance Functions and Smooth Minimum Operations*. [iquilezles.org/articles/distfunctions2d](https://iquilezles.org/articles/distfunctions2d/)
