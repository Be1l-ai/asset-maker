# Physically-Based Rendering (PBR) Channel Standards

Defines mathematical ranges, color spaces, channel definitions, and ORM packing formulas for game-ready PBR texture maps.

---

## 1. PBR Texture Map Specification

| Texture Channel | Dimensions / Channels | Value Range | Gamma / Color Space | Role in Shading |
|---|---|---|---|---|
| **Albedo / BaseColor** | RGB or RGBA | $[0, 255]$ | sRGB ($\gamma \approx 2.2$) | Surface diffuse reflectance without baked directional lighting or hard shadows. |
| **Roughness** | Grayscale (1 channel) | $[0, 255] \to [0.0, 1.0]$ | Linear | Perceptual microfacet roughness $r$, mapped to GGX $\alpha = r^2$ in Cook-Torrance specular distribution. |
| **Metallic** | Grayscale (1 channel) | $\{0, 255\}$ (Binary) | Linear | Conductor vs. dielectric indicator. $0.0$ = stone, wood, glass, cloth ($F_0 \approx 0.04$); $1.0$ = raw gold, brass, iron. |
| **Normal Map** | RGB (3 channels) | $[0, 255] \to [-1, 1]$ | Linear | Encodes tangent-space unit normal $(N_x, N_y, N_z)$ via $\mathbf{C} = \lfloor 127.5 (\mathbf{N} + 1) \rfloor$. |
| **Ambient Occlusion (AO)**| Grayscale (1 channel) | $[0, 255] \to [0.0, 1.0]$ | Linear | Attenuates indirect ambient irradiance in mortar joints, crevices, and contact cavities. |
| **Height / Displacement** | Grayscale (1 channel) | $[0, 255] \to [0.0, 1.0]$ | Linear | Scalar surface elevation $h(x, y) \in [0, 1]$ for Sobel normal derivation or parallax occlusion. |

---

## 2. glTF 2.0 / Engine ORM Channel Packing

To minimize GPU texture sampler lookups, glTF 2.0, Unreal Engine, and Godot pack three linear scalar maps into a single RGB texture (**ORM Map**):
- **R (Red)**: Ambient Occlusion $\text{AO}(x, y) \in [0, 255]$
- **G (Green)**: Perceptual Roughness $R(x, y) \in [0, 255]$
- **B (Blue)**: Metallic $M(x, y) \in [0, 255]$

---

## 3. Typical Material Parameter Matrix

| Material Type | BaseColor (sRGB) | Roughness | Metallic | Typical Height / Normal Detail |
|---|---|---|---|---|
| **Polished Gold** | `(255, 215, 60)` | $0.15\text{--}0.25$ | $1.0$ | Smooth bevels with fine hairline scratches |
| **Forged Iron / Steel**| `(190, 195, 205)`| $0.35\text{--}0.50$ | $1.0$ | Micro-pitting, hammer indentations |
| **Dungeon Slate Stone**| `(90, 95, 105)` | $0.75\text{--}0.90$ | $0.0$ | Chiseled fracture bevels, Worley edge spalling |
| **Antique Oak Wood** | `(140, 95, 55)` | $0.60\text{--}0.80$ | $0.0$ | Concentric annual growth rings (`procedural_wood_grain`) |
| **Wool / Linen Fabric**| `(180, 50, 60)` | $0.85\text{--}0.95$ | $0.0$ | Interlaced warp/weft textile weave (`procedural_fabric_weave`) |
| **Glass / Quartz** | `(220, 245, 255)`| $0.05\text{--}0.15$ | $0.0$ | Smooth spherical dome (`inside_depth` $\to$ `heightmap_to_normal_map`) |

---

## 4. Python Derivation of Height, Normal, and ORM Channels

```python
import numpy as np
from asset_pipeline import heightmap_to_normal_map, worley_noise

# 1. Generate scalar heightfield in [0, 1]
cells = worley_noise(256, 256, grid_x=8, grid_y=8, seed=7, periodic=True)
height = np.clip(1.0 - cells, 0.0, 1.0)

# 2. Derive tangent-space normal map (OpenGL +Y up convention)
normal_rgb = heightmap_to_normal_map(height, strength=3.0, tileable=True)

# 3. Pack linear ORM (R=AO, G=Roughness, B=Metallic)
ao_u8 = np.clip((0.45 + 0.55 * height) * 255.0, 0, 255).astype(np.uint8)
rough_u8 = np.clip((0.88 - 0.18 * height) * 255.0, 0, 255).astype(np.uint8)
metal_u8 = np.zeros_like(ao_u8, dtype=np.uint8)
orm_rgb = np.dstack([ao_u8, rough_u8, metal_u8])
```
