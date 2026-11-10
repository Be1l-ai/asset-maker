# Worley (Cellular / Voronoi) Noise

Used for stone cobblestone paving, cracked mud, reptile scales, dragon skin, and organic cellular textures.

---

## 1. Mathematical Formulation

Introduced by Steven Worley (1996), cellular noise partitions space into a regular grid of cells $\mathbb{Z}^2$. Inside each cell $C_{i, j}$, one or more random feature points $\mathbf{p}_k$ are placed:
$$\mathbf{p}_{i, j} = (i + \delta_x, j + \delta_y), \quad \delta_x, \delta_y \sim \mathcal{U}(0, 1)$$

For any continuous evaluation point $\mathbf{x} \in \mathbb{R}^2$, the distance to all feature points in the $3 \times 3$ neighboring cells is computed. Sorting these distances produces:
$$d_{(1)} \le d_{(2)} \le d_{(3)} \le \dots$$

### Distance Metrics
1. **$F_1$ (First Nearest)**: $F_1(\mathbf{x}) = d_{(1)}$
   - Creates smooth bubble-like cells; darkest at feature points, brightening toward borders.
2. **$F_2 - F_1$ (Cell Border Metric)**:
   - Evaluates distance difference between the two closest feature points.
   - Yields sharp, clean borders between cells (ideal for stone mortar crevices and cracked earth).
3. **Distance Metrics**:
   - Euclidean: $\|\mathbf{x} - \mathbf{p}\|_2 = \sqrt{\Delta x^2 + \Delta y^2}$ (round organic cells).
   - Manhattan: $\|\mathbf{x} - \mathbf{p}\|_1 = |\Delta x| + |\Delta y|$ (diamond/angular cells).
   - Chebyshev: $\|\mathbf{x} - \mathbf{p}\|_\infty = \max(|\Delta x|, |\Delta y|)$ (square crystalline tiles).

---

## 2. Python Usage in `asset_pipeline`

Use the vectorized helper in `asset_pipeline`:

```python
from asset_pipeline import worley_noise

# Generate 256x256 stone paving noise with 8x8 cells
stone_cells = worley_noise(width=256, height=256, grid_x=8, grid_y=8, metric="euclidean", seed=42)

# Generate crystalline geometric scales using Chebyshev
crystal_scales = worley_noise(width=256, height=256, grid_x=12, grid_y=12, metric="chebyshev", seed=7)
```
