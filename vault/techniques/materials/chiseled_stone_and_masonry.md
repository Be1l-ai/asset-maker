# Procedural Stone Masonry, Chiseled Ashlar, and Architectural Plinths

Mathematical formulations and procedural recipes for running-bond masonry, Hermite bevel distance fields, edge-localized Worley chipping, Fourier granite grain, and turned 3D stone plinths.

---

## 1. Running-Bond Ashlar Grid & Pixel-Space SDF

In running-bond stonework (`assets/dungeon_bricks_v2`), alternate horizontal courses are staggered by half a block width ($W / 2$) to break continuous vertical mortar fault lines while preserving toroidal wrap periodicity across canvas size $S \times S$:

Given $N_{\text{rows}}$ courses and $N_{\text{cols}}$ blocks per course ($H = S / N_{\text{rows}}$, $W = S / N_{\text{cols}}$):
1. **Course & Staggered Column Coordinates**:
   $$r = \left\lfloor \frac{y}{H} \right\rfloor \bmod N_{\text{rows}}, \quad x_s = \left(x + (r \bmod 2)\frac{W}{2}\right) \bmod S, \quad c = \left\lfloor \frac{x_s}{W} \right\rfloor \bmod N_{\text{cols}}$$
2. **Local Intra-Block Pixel Coordinates** $(u, v) \in [0, W) \times [0, H)$:
   $$u = x_s - c W, \quad v = y - r H$$
3. **Signed Distance to Nearest Mortar Joint**:
   For mortar groove width $g_{\text{mortar}}$:
   $$d_{\text{edge}}(u, v) = \min(u, W - u, v, H - v) - \frac{g_{\text{mortar}}}{2}$$
   - $d_{\text{edge}} < 0$: recessed mortar bed.
   - $d_{\text{edge}} \ge 0$: interior stone ashlar face, increasing inward toward the block center.

---

## 2. Chiseled Bevel Profiles & Edge-Localized Worley Chipping

To avoid flat razor-cut blocks or uniform sponge-like noise across the entire stone face, combine a smooth bevel transfer function with **edge-masked cellular erosion**:

1. **Hermite Smoothstep Bevel** over bevel width $w_{\text{bevel}}$:
   $$t_b = \operatorname{clamp}\!\left(\frac{d_{\text{edge}}}{w_{\text{bevel}}}, 0, 1\right), \quad h_{\text{bevel}}(t_b) = 3 t_b^2 - 2 t_b^3$$
2. **Edge-Localized Worley Spalling**:
   Mechanical impacts fracture stone predominantly along exposed arrises and corners ($0 \le d_{\text{edge}} \le w_{\text{chip}}$). Using a tileable cellular distance field $W_1(x, y) = \operatorname{worley\_noise}(S, S, g_x, g_y, \text{periodic=True})$:
   $$m_{\text{edge}}(d_{\text{edge}}) = \operatorname{clamp}\!\left(1 - \frac{d_{\text{edge}}}{w_{\text{chip}}}, 0, 1\right)$$
   $$h_{\text{chip}}(x, y) = -\alpha_{\text{chip}} \cdot m_{\text{edge}}(d_{\text{edge}}) \cdot \left(1 - W_1(x, y)\right)^2$$
3. **Toroidal Integer-Harmonic Mineral Grain**:
   Superimpose continuous periodic trigonometry $\sin(2\pi k_x X)\cos(2\pi k_y Y)$ with $k_x, k_y \in \mathbb{Z}^+$ via [`SeamlessTile.generate_toroidal_grid`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/sprite2d.py) so micro-crystalline granite speckles wrap with zero boundary seams.

---

## 3. Per-Block Hash Variation & Mortar Contact AO

Natural quarry stone exhibits block-to-block mineral variance and deep crevice darkening:
- **Deterministic Per-Block Value & Warm/Cool Shift**:
  Hash integer indices $(r, c)$ to a reproducible float $h_{r,c} \in [-1, 1]$ to Perturb each block's base albedo by $\pm 12\%$ and shift warm sandstone vs. cool slate undertones.
- **Mortar Crevice Ambient Occlusion**:
  $$\text{AO}(d_{\text{edge}}) = 1 - \beta_{\text{ao}} \exp\!\left(-\frac{\max(d_{\text{edge}}, 0)}{\sigma_{\text{ao}}}\right), \quad \beta_{\text{ao}} \approx 0.45$$

| Parameter | Recommended Value ($S = 256$) | Purpose |
| :--- | :--- | :--- |
| $N_{\text{rows}} \times N_{\text{cols}}$ | $4 \times 2$ ($W=128, H=64$) | Classic 2:1 running-bond ashlar proportions |
| $g_{\text{mortar}}$ | $6.0\text{--}8.0\text{ px}$ | Deep recessed mortar bed |
| $w_{\text{bevel}}$ | $10.0\text{--}14.0\text{ px}$ | Broad stylized highlight-catching bevel |
| $w_{\text{chip}}$ | $14.0\text{--}18.0\text{ px}$ | Perimeter zone where Worley fractures bite |

---

## 4. Turned 3D Stone Plinths & Obelisk Moldings (`MeshBuilder.lathe`)

In 3D architectural monuments (`assets/mana_obelisk_v2`), stone pedestals use classical Greco-Roman moldings spun around the vertical $Z$-axis via [`MeshBuilder.lathe`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/mesh3d.py) with `subdivide=3` (or `4` for octagonal masonry):

- **Plinth & Fillet Step**: Vertical flat band $(r = R_{\max})$ stepping inward via a $45^\circ$ chamfer collar to catch directional key-light.
- **Scotia / Gorge Undercut**: Concave recess $r(t) = R_{\text{neck}} < R_{\text{base}}$ that traps a crisp core shadow ring between pedestal tiers, separating the base from the upper obelisk shaft.
- **Ground Contact AO (`bake_ground_ao`)**: Darkens the bottom $25\text{--}35\%$ of the stone pedestal (`strength=0.50, height_fraction=0.30`) so the monument looks heavy and rooted to the floor.

---

## 5. Python Usage in `asset_pipeline`

```python
import numpy as np
from asset_pipeline import (
    MeshBuilder,
    SeamlessTile,
    bake_ground_ao,
    heightmap_to_normal_map,
    worley_noise,
)

# --- 2D Seamless Chiseled Stone Tile ---
S = 256
X, Y = SeamlessTile.generate_toroidal_grid(S, S)
worley_macro = worley_noise(S, S, grid_x=8, grid_y=8, seed=42, periodic=True)
worley_micro = worley_noise(S, S, grid_x=16, grid_y=16, seed=107, periodic=True)

yy, xx = np.mgrid[0:S, 0:S].astype(np.float64)
row = np.floor(yy / 64.0).astype(int) % 4
xx_stag = (xx + (row % 2) * 64.0) % S
u, v = xx_stag % 128.0, yy % 64.0

d_edge = np.minimum(np.minimum(u, 128.0 - u), np.minimum(v, 64.0 - v)) - 3.5
bevel_t = np.clip(d_edge / 11.0, 0.0, 1.0)
bevel = bevel_t * bevel_t * (3.0 - 2.0 * bevel_t)
chip_mask = np.clip(1.0 - d_edge / 15.0, 0.0, 1.0)
height = np.where(d_edge > 0, bevel - 0.28 * chip_mask * (1.0 - worley_macro) ** 2, 0.05 * worley_micro)
normal_img = heightmap_to_normal_map(height, strength=4.0)

# --- 3D Stepped Stone Pedestal via Lathe ---
builder = MeshBuilder()
plinth_profile = [(0.92, 0.0), (0.88, 0.22), (0.72, 0.28), (0.68, 0.52), (0.52, 0.60)]
pedestal = builder.lathe(plinth_profile, segments=4, subdivide=3)
bake_ground_ao(pedestal, strength=0.50, height_fraction=0.30)
```

---

## 6. References
- Worley, S. (1996). *A Cellular Texture Basis Function*. Proceedings of ACM SIGGRAPH '96, 291–294.
- Ebert, D. S., Musgrave, F. K., Peachey, D., Perlin, K., & Worley, S. (2003). *Texturing and Modeling: A Procedural Approach* (3rd ed.). Morgan Kaufmann.
- Chitham, R. (2005). *The Classical Orders of Architecture* (2nd ed., Moldings: Fillet, Torus, Scotia, Cyma Recta). Architectural Press.
