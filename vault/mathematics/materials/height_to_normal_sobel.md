# Deriving Tangent-Space Normal Maps from Heightfields

Mathematical derivation and algorithm for transforming a scalar grayscale heightmap into an RGB tangent-space normal map using the discrete Sobel operator.

---

## 1. Mathematical Formulation

Let $h(x, y)$ be a 2D scalar field where $h \in [0, 1]$ represents surface height. The surface in $\mathbb{R}^3$ can be expressed as:
$$\mathbf{S}(x, y) = \begin{pmatrix} x \\ y \\ h(x, y) \end{pmatrix}$$

The tangent vectors along the $X$ and $Y$ axes:
$$\mathbf{T}_x = \frac{\partial \mathbf{S}}{\partial x} = \begin{pmatrix} 1 \\ 0 \\ \frac{\partial h}{\partial x} \end{pmatrix}, \quad \mathbf{T}_y = \frac{\partial \mathbf{S}}{\partial y} = \begin{pmatrix} 0 \\ 1 \\ \frac{\partial h}{\partial y} \end{pmatrix}$$

The unnormalized surface normal $\mathbf{N}$ is the cross product of the tangents:
$$\mathbf{N} = \mathbf{T}_x \times \mathbf{T}_y = \begin{pmatrix} 1 \\ 0 \\ \partial h / \partial x \end{pmatrix} \times \begin{pmatrix} 0 \\ 1 \\ \partial h / \partial y \end{pmatrix} = \begin{pmatrix} -\frac{\partial h}{\partial x} \\ -\frac{\partial h}{\partial y} \\ 1 \end{pmatrix}$$

Normalizing to unit magnitude:
$$\hat{\mathbf{N}} = \frac{\mathbf{N}}{\|\mathbf{N}\|} = \frac{(-\partial h / \partial x, -\partial h / \partial y, 1)}{\sqrt{(\partial h / \partial x)^2 + (\partial h / \partial y)^2 + 1}}$$

### Sobel Convolution Kernels
The discrete partial derivatives $\partial h / \partial x$ and $\partial h / \partial y$ are approximated using $3 \times 3$ convolution kernels:
$$G_x = \begin{bmatrix} -1 & 0 & +1 \\ -2 & 0 & +2 \\ -1 & 0 & +1 \end{bmatrix} * h, \quad G_y = \begin{bmatrix} -1 & -2 & -1 \\ 0 & 0 & 0 \\ +1 & +2 & +1 \end{bmatrix} * h$$

### Tangent Space to RGB Color Encoding
Because normal components range over $[-1, 1]$ and texture formats store unsigned bytes in $[0, 255]$:
$$\text{Color}_{\text{RGB}} = \left\lfloor \frac{\hat{\mathbf{N}} + 1}{2} \times 255 \right\rfloor$$
- A flat surface pointing straight out $(0, 0, 1)$ maps to RGB `(128, 128, 255)` (the classic periwinkle blue normal map color).

---

## 2. Python Implementation in `asset_pipeline`

```python
from asset_pipeline import heightmap_to_normal_map

# heightmap: 2D numpy array [0..1]
normal_map_rgb = heightmap_to_normal_map(
    heightmap=height_data,
    strength=2.0,       # Bump relief scale
    invert_y=False      # False = OpenGL (Y-up), True = DirectX (Y-down)
)
```
