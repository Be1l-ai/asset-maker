# Color Ramps, Cel Shading, and Color Temperature

Techniques from *Guilty Gear*, *Genshin Impact*, and anime production for vibrant stylized lighting without dull, muddy shadows (`assets/health_potion_v2`, `assets/arcane_burst_v2`).

---

## 1. The Muddy Shadow Trap

A common mistake in procedural asset authoring is darkening colors by scaling RGB toward black:
$$\mathbf{C}_{\text{shadow}} = \mathbf{C}_{\text{base}} \times 0.5$$

This produces **dead, desaturated, grey-black shadows** that ruin stylized vibrancy. Real light and stylized art always incorporate **color temperature contrast**:
- **Lit Surfaces**: Warm tint (shifted toward golden yellow, amber, or warm vermilion).
- **Shadow Surfaces**: Cool tint (shifted toward rich purple, carmine-violet, ultramarine, or indigo).

---

## 2. 1D Color Ramps & Distance-Field Shading (`lerp_color`)

Instead of continuous greyscale Lambertian dimming, stylized shading interpolates across a temperature-shifted color ramp $R(t)$ where $t \in [0, 1]$ represents normalized light intensity or SDF interior depth (`inside_depth`):

```
[ Deep Cool Shadow ] ----(lerp_color)----> [ Saturated Midtone ] ----(lerp_color)----> [ Warm Core Highlight ]
     t = 0.0                                     t = 0.5                                     t = 1.0
```

### Quantized Cel Thresholds
In 2-band or 3-band anime cel shading:
$$C(t) = \begin{cases} C_{\text{highlight}} & \text{if } t > 0.70 \\ C_{\text{midtone}} & \text{if } 0.15 \le t \le 0.70 \\ C_{\text{shadow}} & \text{if } t < 0.15 \end{cases}$$

---

## 3. Python Helpers in `asset_pipeline`

Use [`hsv_to_rgb`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/sprite2d.py) to construct temperature-shifted palette stops and [`lerp_color`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/sprite2d.py) to blend 2D scalar fields across `(H, W, 3)` RGB arrays:

```python
import numpy as np
from asset_pipeline import hsv_to_rgb, lerp_color

def make_stylized_palette(base_hue: float = 350.0):
    """Generate harmonious warm-lit and cool-shadow RGB colors."""
    lit = hsv_to_rgb(base_hue - 20.0, 0.70, 0.98)     # Warm orange-red highlight
    mid = hsv_to_rgb(base_hue, 0.85, 0.78)            # Saturated ruby midtone
    shadow = hsv_to_rgb(base_hue + 25.0, 0.90, 0.32)  # Cool violet-crimson shadow
    return lit, mid, shadow

# Vectorized 2D field interpolation between shadow and lit stops
t_field = np.linspace(0.0, 1.0, 256)[None, :] * np.ones((256, 1))
lit_rgb, mid_rgb, shadow_rgb = make_stylized_palette()
ramp_img = lerp_color(shadow_rgb, lit_rgb, t_field)
```
