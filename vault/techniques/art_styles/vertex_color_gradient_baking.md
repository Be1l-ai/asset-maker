# Vertex Color Baking and Ground Contact Ambient Occlusion

How low-poly game models bake ambient occlusion, grounding shadows, and material masks directly into vertex data without UV unwrapping (`assets/mana_obelisk_v2`).

---

## 1. Why Vertex Colors are Essential in Procedural Assets

For code-generated low-poly props (under 3000 triangles):
- Generating full UV unwrap charts and baking image textures in pure Python is computationally heavy.
- In contrast, storing colors and ambient occlusion in **vertex attributes** (`mesh.visual.vertex_colors`) is zero-overhead, highly performant, and supported natively by GLB/glTF in all modern game engines.

---

## 2. Multiplicative Ground Contact AO (`bake_ground_ao`) vs. Full Gradient (`bake_vertex_gradient_ao`)

Unanchored models look like they are floating in mid-air. Baking vertical occlusion into the lower portion of a mesh anchors the object firmly to the floor:

1. **Multiplicative Ground AO (`bake_ground_ao`)**:
   Preserves existing per-part material colors $\mathbf{C}_v^{\text{base}}$ (e.g., dark stone pedestal, glowing cyan rune rings, obsidian obelisk shaft) while darkening vertices within the lower height fraction $h_f \in [0.20, 0.40]$ of the model's vertical bounding box:
   $$t_z = \operatorname{clamp}\!\left(\frac{z - z_{\min}}{h_f \cdot (z_{\max} - z_{\min})}, 0, 1\right), \quad s_{\text{ao}}(t_z) = (1 - \alpha_{\text{ao}}) + \alpha_{\text{ao}}\,t_z$$
   $$\mathbf{C}_v = s_{\text{ao}}(t_z) \cdot \mathbf{C}_v^{\text{base}}$$

2. **Full Two-Tone Vertical Gradient (`bake_vertex_gradient_ao`)**:
   Replaces vertex colors across a single-material mesh with a smooth linear interpolation between $\mathbf{C}_{\text{ground}}$ and $\mathbf{C}_{\text{top}}$ over normalized height $t_z \in [0, 1]$:
   $$\mathbf{C}_v = \mathbf{C}_{\text{ground}} + t_z \cdot (\mathbf{C}_{\text{top}} - \mathbf{C}_{\text{ground}})$$

---

## 3. Vertex Channel Masking for Game Shaders

In real-time engine shaders, the 4 vertex channels (RGBA) can also serve as functional masks:
- **Red (R)**: Ground contact ambient occlusion.
- **Green (G)**: Secondary material blend mask (moss on stone, rust on metal).
- **Blue (B)**: Emissive glow intensity (glowing runes, crystal cores).
- **Alpha (A)**: Wind vertex animation weight (tree branches, swaying grass).

---

## 4. Python Usage in `asset_pipeline`

```python
from asset_pipeline import MeshBuilder, bake_ground_ao, bake_vertex_gradient_ao

builder = MeshBuilder()
obelisk = builder.box(size=[0.6, 0.6, 2.4], center=[0, 0, 1.2], color=[72, 78, 95, 255])

# 1. Multiplicatively darken bottom 30% of existing vertex colors by up to 45%
bake_ground_ao(obelisk, strength=0.45, height_fraction=0.30)

# 2. Or bake a full two-color vertical gradient across a single-material mesh
bake_vertex_gradient_ao(
    mesh=obelisk,
    ground_z=0.0,
    top_color=(240, 245, 255),
    ground_color=(45, 48, 60),
)
```
