# Volumetric Smoke Plumes, Buoyant Vortices, and Cellular Erosion

Mathematical formulations and procedural flipbook techniques for rising pyroclastic smoke puffs, vortex entrainment, temperature cooling ramps, and noise-eroded alpha dissolve (`assets/arcane_burst_v2`).

---

## 1. Buoyant Plume Kinematics (Morton-Taylor-Turner Model)

By **Morton, Taylor, and Turner's (1956)** buoyant plume entrainment theory, a thermal cloud rising through an ambient fluid entrains surrounding air at a rate proportional to its vertical velocity, causing the plume radius to expand linearly with altitude while decelerating smoothly.

For a discrete ensemble of $N_{\text{puffs}}$ volumetric puffs with staggered birth times $t_{0,i} \in [0, 0.25]$ over normalized flipbook life $t \in [0, 1]$:

1. **Local Normalized Puff Lifetime**:
   $$\tau_i(t) = \operatorname{clamp}\!\left(\frac{t - t_{0,i}}{1 - t_{0,i}}, 0, 1\right)$$
2. **Decelerating Buoyant Thermal Rise (`Easing.ease_out`)**:
   $$y_i(\tau_i) = y_{\text{origin}} - H_i \cdot \operatorname{ease\_out}(\tau_i, \gamma_{\text{rise}}), \quad \gamma_{\text{rise}} \in [1.5, 2.2]$$
3. **Turbulent Entrainment Radial Expansion**:
   $$R_i(\tau_i) = R_{0,i} \cdot (0.60 + 0.90\,\tau_i)$$
4. **Curl / Vortex Swirl Advection**:
   Puffs spawned at radial distance $d_{0,i}$ and angle $\theta_{0,i}$ precess around the plume core:
   $$\theta_i(\tau_i) = \theta_{0,i} + \omega_{0,i}\,\tau_i, \quad d_i(\tau_i) = d_{0,i} \cdot \operatorname{ease\_out}(\tau_i, 1.8)$$

> [!IMPORTANT]
> **Deterministic Pre-Rolled Puff Tables**: Never call `np.random` inside a frame callback. Pre-roll all per-puff parameters $(\theta_{0,i}, d_{0,i}, R_{0,i}, H_i, \omega_{0,i}, t_{0,i})$ once before rendering the flipbook so particle trajectories remain temporally coherent across all frames.

---

## 2. Blackbody / Arcane Temperature Cooling Ramp

Pyroclastic and magical plumes cool rapidly from an incandescent inner core to dark soot or bruised indigo shadow as $\tau_i \to 1$:

$$\mathbf{C}_{\text{puff}}(\tau_i) = \begin{cases} \operatorname{lerp}\!\left(\mathbf{C}_{\text{core}}, \mathbf{C}_{\text{mid}}, \dfrac{\tau_i}{0.35}\right) & 0 \le \tau_i < 0.35 \\[6pt] \operatorname{lerp}\!\left(\mathbf{C}_{\text{mid}}, \mathbf{C}_{\text{soot}}, \dfrac{\tau_i - 0.35}{0.65}\right) & 0.35 \le \tau_i \le 1.0 \end{cases}$$

To fake **Half-Lambert volumetric self-shadowing** (Valve, 2004) on each 2D billboard puff without a 3D fluid solver, stamp a dual-circle cluster:
- **Outer Soot/Indigo Billow**: Full radius $R_i(\tau_i)$ in cool shadow tone $\mathbf{C}_{\text{soot}}$.
- **Inner Lit Billow**: Offset by $(-0.18\,R_i, -0.22\,R_i)$ toward the upper-left key-light (or inward toward the explosion core) with radius $0.65\,R_i(\tau_i)$ in warmer tone $\mathbf{C}_{\text{mid}}$.

---

## 3. Cellular Alpha Erosion Dissolve (`dissolve_alpha_mask`)

Fading smoke by linearly scaling opacity ($\alpha \leftarrow \alpha(1 - t)$) looks like a flat ghosting cross-fade. Real smoke dissipates by breaking apart into smaller turbulent eddies as thin regions drop below optical visibility.

Using [`worley_noise`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/sprite2d.py) and [`dissolve_alpha_mask`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/vfx.py):
1. Pre-compute a seamless cellular noise map $N(x, y) \in [0, 1]$ prior to the frame loop.
2. Ramp the erosion threshold across the second half of the emitter lifetime:
   $$\theta_{\text{erode}}(t) = \theta_{\min} + (\theta_{\max} - \theta_{\min}) \cdot t, \quad \theta_{\min} \approx 0.10,\; \theta_{\max} \approx 0.65$$
3. Apply `dissolve_alpha_mask(canvas, threshold=theta_erode, noise_map=N, edge_width=0.06, edge_color=...)` so cellular cavities eat into the fading smoke silhouette with a glowing ember rim.

---

## 4. Python Usage in `asset_pipeline`

```python
import numpy as np
from PIL import Image, ImageDraw
from asset_pipeline import Easing, EmitterStack, dissolve_alpha_mask, worley_noise

S = 128
rng = np.random.default_rng(42)
smoke_noise = worley_noise(S, S, grid_x=6, grid_y=6, seed=77, periodic=True)

# Pre-roll 14 deterministic smoke puffs outside the frame loop
puff_angles = rng.uniform(0, 2 * np.pi, 14)
puff_dists = rng.uniform(12.0, 42.0, 14)
puff_radii = rng.uniform(9.0, 17.0, 14)
puff_rise = rng.uniform(8.0, 22.0, 14)

def render_smoke_layer(frame_idx: int, life: float) -> Image.Image:
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if life < 0.08:
        return canvas
    draw = ImageDraw.Draw(canvas)
    t = Easing.ease_out((life - 0.08) / 0.92, 1.8)
    alpha = int(np.clip(np.sin(t * np.pi) * 195, 0, 195))

    for ang, dist, rad, rise in zip(puff_angles, puff_dists, puff_radii, puff_rise):
        r_curr = rad * (0.60 + 0.85 * t)
        px = S / 2 + np.cos(ang + 0.5 * t) * dist * t
        py = S / 2 + np.sin(ang + 0.5 * t) * dist * t - rise * t
        draw.ellipse([px - r_curr, py - r_curr, px + r_curr, py + r_curr], fill=(42, 24, 78, alpha))

    return dissolve_alpha_mask(
        canvas,
        threshold=0.10 + 0.55 * t,
        noise_map=smoke_noise,
        edge_width=0.06,
        edge_color=(165, 85, 245),
    )

stack = EmitterStack(frame_size=S, num_frames=16)
stack.add_layer("buoyant_smoke", render_smoke_layer, blend_mode="alpha")
```

---

## 5. References
- Morton, B. R., Taylor, G. I., & Turner, J. S. (1956). *Turbulent Gravitational Convection from Maintained and Instantaneous Sources*. Proceedings of the Royal Society A, 234(1196), 1–23.
- Bridson, R., Houriham, J., & Nordenstam, M. (2007). *Curl-Noise for Procedural Fluid Flow*. ACM Transactions on Graphics (SIGGRAPH 2007), 26(3), Article 46.
- Mitchell, J., McTaggart, G., & Green, C. (2006). *Shading in Valve's Source Engine (Half-Lambert Wrap Lighting)*. ACM SIGGRAPH Courses.
