# Color Ramps, Cel Shading, and Color Temperature

Techniques from *Guilty Gear*, *Genshin Impact*, and anime production for vibrant stylized lighting without dull, muddy shadows.

---

## 1. The Muddy Shadow Trap

A common beginner mistake in procedural asset authoring is darkening colors by scaling RGB toward black:
$$\mathbf{C}_{\text{shadow}} = \mathbf{C}_{\text{base}} \times 0.5$$

This produces **dead, desaturated, grey-black shadows** that ruin stylized vibrancy. Real light and stylized anime art always incorporate **color temperature contrast**:
- **Lit Surfaces**: Warm tint (shifted toward golden yellow, amber, or warm peach).
- **Shadow Surfaces**: Cool tint (shifted toward rich purple, ultramarine, indigo, or ambient teal).

---

## 2. 1D Color Ramps (Toon Mapping)

Instead of continuous linear lambertian lighting $I = \max(0, \mathbf{N} \cdot \mathbf{L})$, stylized shading samples a 1D color gradient ramp $R(t)$ where $t = \mathbf{N} \cdot \mathbf{L} \in [-1, 1]$:

```
[ Deep Indigo/Purple ] ----(Step)----> [ Rich Midtone ] ----(Step)----> [ Warm Golden Highlight ]
     t = -1.0..0.0                         t = 0.0..0.7                    t = 0.7..1.0
```

### Quantized Cel Thresholds
In 2-band or 3-band anime cel shading:
$$C(t) = \begin{cases} C_{\text{highlight}} & \text{if } t > 0.70 \\ C_{\text{midtone}} & \text{if } 0.15 \le t \le 0.70 \\ C_{\text{shadow}} & \text{if } t < 0.15 \end{cases}$$

Hard or slightly smoothed step thresholds eliminate the muddy grey midtones of realistic shading, producing graphic, posterized anime frames.

---

## 3. Python Helper in `asset_pipeline`

```python
from asset_pipeline import sprite2d

def make_stylized_palette(base_hue: float = 210.0):
    """Generate harmonious warm-lit and cool-shadow RGB colors."""
    # Lit: Warm hue shift (-20 deg), high value
    lit = sprite2d.hsv_to_rgb(base_hue - 20.0, 0.65, 0.95)
    # Mid: True hue
    mid = sprite2d.hsv_to_rgb(base_hue, 0.75, 0.70)
    # Shadow: Cool hue shift (+25 deg), deep saturation
    shadow = sprite2d.hsv_to_rgb(base_hue + 25.0, 0.85, 0.35)
    return lit, mid, shadow
```
