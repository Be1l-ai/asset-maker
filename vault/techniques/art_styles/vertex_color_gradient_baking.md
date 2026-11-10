# Vertex Color Baking and Ground Contact Ambient Occlusion

How low-poly game models bake ambient occlusion, grounding shadows, and material masks directly into vertex data without UV unwrapping.

---

## 1. Why Vertex Colors are Essential in Procedural Assets

For code-generated low-poly props (under 3000 triangles):
- Generating full UV unwrap charts and baking image textures in pure Python is computationally heavy.
- In contrast, storing colors and ambient occlusion in **vertex attributes** (`mesh.visual.vertex_colors`) is zero-overhead, highly performant, and supported by all game engines (GLB/glTF).

---

## 2. Vertical Ground Contact Gradient

Unanchored models look like they are floating in mid-air. Baking a vertical gradient into the bottom $20\text{--}30\%$ of vertices anchors the object firmly to the ground:
$$t_z = \text{clamp}\left(\frac{z - z_{\min}}{z_{\max} - z_{\min}}, 0, 1\right)$$
$$\mathbf{C}_v = \mathbf{C}_{\text{ground}} + t_z \cdot (\mathbf{C}_{\text{top}} - \mathbf{C}_{\text{ground}})$$

Where $\mathbf{C}_{\text{ground}}$ has dark cool tones (e.g. `[50, 55, 70]`) and $\mathbf{C}_{\text{top}}$ carries full material illumination.

---

## 3. Vertex Channel Masking for Game Shaders

In advanced real-time shaders, the 4 vertex channels (RGBA) are used as functional masks:
- **Red (R)**: Ground contact ambient occlusion.
- **Green (G)**: Secondary material blend mask (moss on stone, rust on metal).
- **Blue (B)**: Emissive glow intensity (glowing runes, crystal cores).
- **Alpha (A)**: Wind vertex animation weight (tree branches, swaying grass).

---

## 4. Python Usage in `asset_pipeline`

```python
from asset_pipeline import bake_vertex_gradient_ao

# Apply vertical AO gradient to an obelisk or building mesh
bake_vertex_gradient_ao(
    mesh=my_trimesh,
    ground_z=0.0,
    top_color=(240, 245, 255),
    ground_color=(45, 48, 60),
)
```
