# Domain Warping and Coordinate Distortion

Used for fluid turbulence, marble veining, fire distortion, and organic twisting.

---

## 1. Mathematical Formulation

Introduced by Inigo Quilez, domain warping evaluates a base scalar noise function $f(\mathbf{p})$ not at rigid coordinates $\mathbf{p} = (x, y)$, but at distorted coordinates offset by another vector-valued noise function $\mathbf{g}(\mathbf{p})$:
$$\mathbf{q}(\mathbf{p}) = \mathbf{g}(\mathbf{p}) = \begin{pmatrix} f(\mathbf{p} + \mathbf{c}_1) \\ f(\mathbf{p} + \mathbf{c}_2) \end{pmatrix}$$
$$W(\mathbf{p}) = f(\mathbf{p} + \alpha \cdot \mathbf{q}(\mathbf{p}))$$

### Recursive (Second-Order) Warping
For hyper-organic swirls, clouds, and plasma:
$$\mathbf{r}(\mathbf{p}) = \mathbf{h}(\mathbf{p} + \beta \mathbf{q}(\mathbf{p}))$$
$$W_2(\mathbf{p}) = f(\mathbf{p} + \gamma \mathbf{r}(\mathbf{p}))$$

---

## 2. Python Implementation

```python
import numpy as np

def domain_warp_2d(base_fn, x, y, strength: float = 0.25):
    """Distort 2D coordinates using vector offsets from base_fn."""
    # Compute vector offset field
    offset_x = base_fn(x + 5.2, y + 1.3)
    offset_y = base_fn(x + 1.7, y + 9.2)

    # Sample base field at warped coordinates
    warped_x = x + strength * offset_x
    warped_y = y + strength * offset_y
    return base_fn(warped_x, warped_y)
```

## 3. Practical Asset Applications
- **Marble Tiles**: Distorting linear parallel bands $y$ with low-frequency noise yields natural metamorphic marble veins.
- **VFX Shockwaves**: Warping radial distance $r = \sqrt{x^2 + y^2} + \alpha \cdot \text{noise}(\theta)$ creates irregular ragged shockwave boundaries rather than rigid circles.
