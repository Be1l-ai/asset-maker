# Cubic and Quadratic Bezier Curves

Used for organic 2D vector silhouettes, potion bottle outlines, blade curvatures, and motion path easing.

---

## 1. Mathematical Formulation

### Quadratic Bezier Curve (3 Control Points)
Given control points $P_0, P_1, P_2 \in \mathbb{R}^2$ and parameter $t \in [0, 1]$:
$$B(t) = (1-t)^2 P_0 + 2(1-t)t P_1 + t^2 P_2$$

The first derivative (tangent velocity vector):
$$B'(t) = 2(1-t)(P_1 - P_0) + 2t(P_2 - P_1)$$

### Cubic Bezier Curve (4 Control Points)
Given control points $P_0, P_1, P_2, P_3 \in \mathbb{R}^2$:
$$B(t) = (1-t)^3 P_0 + 3(1-t)^2 t P_1 + 3(1-t) t^2 P_2 + t^3 P_3$$

The first derivative:
$$B'(t) = 3(1-t)^2(P_1 - P_0) + 6(1-t)t(P_2 - P_1) + 3t^2(P_3 - P_2)$$

The normal unit vector at parameter $t$:
$$\vec{T}(t) = \frac{B'(t)}{\|B'(t)\|}, \quad \vec{N}(t) = (-T_y(t), T_x(t))$$

---

## 2. Python Implementation Example

```python
import numpy as np

def sample_cubic_bezier(p0, p1, p2, p3, num_points: int = 32) -> np.ndarray:
    """Sample a 2D cubic Bezier curve into an (N, 2) array of coordinates."""
    t = np.linspace(0.0, 1.0, num_points)[:, None]
    curve = (
        (1.0 - t) ** 3 * p0
        + 3.0 * (1.0 - t) ** 2 * t * p1
        + 3.0 * (1.0 - t) * t ** 2 * p2
        + t ** 3 * p3
    )
    return curve
```

## 3. aggdraw Usage in 2D Sprites

When using `SpriteCanvas`, Bezier curves are drawn natively using `aggdraw.Path`:

```python
import aggdraw
from asset_pipeline import SpriteCanvas

canvas = SpriteCanvas(size=256, super_sample=2)
path = aggdraw.Path()
path.moveto(100, 50)
# curveto takes (cp1_x, cp1_y, cp2_x, cp2_y, end_x, end_y)
path.curveto(180, 50, 220, 120, 200, 200)
canvas.draw_path(path, pen_color=(255, 255, 255, 255), pen_width=4.0)
```
