# Physically-Based Rendering (PBR) Channel Standards

Defines mathematical ranges, color spaces, and channel definitions for game-ready PBR texture maps.

---

## 1. PBR Texture Map Specification

| Texture Channel | Dimensions / Channels | Value Range | Gamma / Color Space | Role in Shading |
|---|---|---|---|---|
| **Albedo / BaseColor** | RGB or RGBA | $[0, 255]$ | sRGB (Gamma 2.2) | Surface diffuse reflectance without baked directional lighting or ambient shadows. |
| **Roughness** | Grayscale (1 channel) | $[0, 255] \to [0.0, 1.0]$ | Linear | Microfacet roughness $\alpha = \text{Roughness}^2$ for Cook-Torrance GGX specular distribution. 0 = mirror mirror, 1 = chalk. |
| **Metallic** | Grayscale (1 channel) | $\{0, 255\}$ (Binary) | Linear | Conductor vs. dielectric indicator. $0.0$ = stone, wood, cloth; $1.0$ = raw gold, brass, iron. Avoid mid-tones except for fine dust/rust. |
| **Normal Map** | RGB (3 channels) | $[0, 255] \to [-1, 1]$ | Linear | Encodes tangent-space surface normal vectors $(N_x, N_y, N_z)$. |
| **Ambient Occlusion (AO)**| Grayscale (1 channel) | $[0, 255] \to [0.0, 1.0]$ | Linear | Multiplies indirect ambient light in crevices and contact cavities. |
| **Height / Displacement** | Grayscale (1 channel) | $[0, 255] \to [0.0, 1.0]$ | Linear | Vertical surface displacement for parallax mapping or tessellation. |

---

## 2. Typical Material Parameter Matrix

| Material Type | BaseColor (sRGB) | Roughness | Metallic | Typical Height Texture |
|---|---|---|---|---|
| **Polished Gold** | `(255, 215, 60)` | $0.15\text{--}0.25$ | $1.0$ | Smooth with hairline scratches |
| **Forged Iron / Steel**| `(190, 195, 205)`| $0.35\text{--}0.50$ | $1.0$ | Micro-pitting, hammer indentations |
| **Dungeon Slate Stone**| `(90, 95, 105)` | $0.75\text{--}0.90$ | $0.0$ | Chiseled fracture bevels, Voronoi cracks |
| **Antique Oak Wood** | `(140, 95, 55)` | $0.60\text{--}0.80$ | $0.0$ | Concentric annual growth rings |
| **Wool / Linen Fabric**| `(180, 50, 60)` | $0.85\text{--}0.95$ | $0.0$ | Interlaced warp/weft textile weave |
| **Glass / Quartz** | `(220, 245, 255)`| $0.05\text{--}0.15$ | $0.0$ | Smooth with edge rim refraction |
