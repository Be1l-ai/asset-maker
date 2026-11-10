# Toroidal Coordinates and Periodic Harmonics

Guarantees 100% mathematically seamless texture tiles across opposite boundaries without visible seams or fading seams.

---

## 1. The Toroidal Mapping Principle

A flat rectangular domain $[0, 1) \times [0, 1)$ becomes seamless if and only if opposite edges are topologically identified:
$$(0, y) \sim (1, y) \quad \text{and} \quad (x, 0) \sim (x, 1)$$

This is topologically equivalent to the 2-torus $\mathbb{T}^2 = S^1 \times S^1$. Mapping normalized image coordinates $(x, y) \in [0, 1)^2$ onto periodic angles:
$$\theta = 2\pi x, \quad \phi = 2\pi y$$

Because $\sin(k\theta)$ and $\cos(k\theta)$ have period $2\pi / k$, any function $f(\theta, \phi)$ evaluated on these angles is **identically periodic**:
$$f(0, y) \equiv f(1, y) \quad \text{and} \quad \frac{\partial f}{\partial x}\Big|_{x=0} \equiv \frac{\partial f}{\partial x}\Big|_{x=1}$$

---

## 2. Multi-Harmonic Fourier Series Formulation

To create organic textures (stone, marble, moss, plaster), compose a sum of sinusoidal harmonics with integer frequency multipliers $k$:
$$H(\theta, \phi) = \sum_{k=1}^M a_k \sin(n_k \theta + \alpha_k) \cdot \cos(m_k \phi + \beta_k)$$
where $n_k, m_k \in \mathbb{Z}^+$ are positive integers.

---

## 3. Python Usage in `asset_pipeline`

```python
import numpy as np
from PIL import Image
from asset_pipeline import SeamlessTile

def make_seamless_mineral_tile(size: int = 256, seed: int = 7) -> Image.Image:
    tile = SeamlessTile(size=size, seed=seed)
    theta, phi = tile.generate_toroidal_grid()

    # Four seamless harmonics
    n1 = np.sin(2 * theta) * np.cos(2 * phi)
    n2 = 0.5 * np.sin(5 * theta + 0.4) * np.sin(5 * phi + 0.8)
    n3 = 0.25 * np.cos(11 * theta - 0.2) * np.sin(9 * phi + 1.2)
    n4 = 0.12 * np.sin(19 * theta) * np.cos(17 * phi)

    field = (n1 + n2 + n3 + n4)
    norm = (field - field.min()) / (field.max() - field.min())
    rgba = (norm * 255).astype(np.uint8)
    return Image.fromarray(rgba, mode="L")
```
