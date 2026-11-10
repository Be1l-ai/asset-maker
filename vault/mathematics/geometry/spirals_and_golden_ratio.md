# Spirals, Phyllotaxis, and the Golden Section

Used for organic 3D horns, nautilus shells, sunflower seed distributions, magic circle runes, and swirling vortex geometries.

---

## 1. Mathematical Formulation

### The Golden Ratio ($\phi$)
$$\phi = \frac{1 + \sqrt{5}}{2} \approx 1.6180339887$$
Golden angle:
$$\theta_{\text{gold}} = 2\pi \left(1 - \frac{1}{\phi}\right) \approx 2.399963\text{ rad} \approx 137.5077^\circ$$

### Logarithmic (Equiangular) Spiral
A curve where the angle between the tangent and radial line is constant:
$$r(\theta) = a \cdot e^{b\theta}$$
In Cartesian coordinates:
$$x(\theta) = a e^{b\theta} \cos(\theta), \quad y(\theta) = a e^{b\theta} \sin(\theta)$$
- $b = \frac{\ln(\phi)}{\pi / 2} \approx 0.3063$ yields the Golden Spiral.

### Archimedean Spiral
Uniform spacing between successive turnings:
$$r(\theta) = a + b\theta$$

### Vogel's Phyllotaxis Model
Distributes $N$ points uniformly across a circular disc with no clumping:
$$r_n = c \sqrt{n}, \quad \theta_n = n \cdot \theta_{\text{gold}}$$
for $n = 0, 1, \dots, N-1$.

---

## 2. Python Implementation

```python
import numpy as np

def generate_phyllotaxis_points(num_points: int = 64, radius: float = 1.0) -> np.ndarray:
    """Generate uniformly packed points on a disc using the golden angle (Vogel model)."""
    golden_angle = 2.399963229728653
    n = np.arange(num_points)
    r = radius * np.sqrt(n / float(num_points))
    theta = n * golden_angle
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.column_stack([x, y])
```

## 3. Practical Asset Applications
- **3D Magic Runes**: Placing floating runes or orbiting crystals around a staff or portal using phyllotaxis coordinates.
- **3D Revolved Horns**: Sweeping an octagonal profile along a logarithmic spiral path.
- **VFX Vortex**: Spawning spiral arms for galaxy portals and black hole accretions.
