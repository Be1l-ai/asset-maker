# Hermite Smoothstep and Interpolation Functions

Used for procedural beveling, ambient occlusion crevices, animation easing, and smooth field blending.

---

## 1. Mathematical Formulation

### Standard Hermite Smoothstep ($C^1$ Continuity)
Clamps $x$ to the range $[a, b]$, normalizes to $t = \text{clamp}\left(\frac{x - a}{b - a}, 0, 1\right)$, and applies the cubic polynomial:
$$S_1(t) = 3t^2 - 2t^3$$

Properties:
- $S_1(0) = 0$, $S_1(1) = 1$
- $S_1'(0) = 0$, $S_1'(1) = 0$ (zero velocity at boundaries)
- Second derivative $S_1''(0) = 6 \neq 0$ (acceleration discontinuity at boundaries)

### Ken Perlin's Smootherstep ($C^2$ Continuity)
Eliminates second-derivative jerk artifacts:
$$S_2(t) = 6t^5 - 15t^4 + 10t^3$$

Properties:
- $S_2(0) = 0$, $S_2(1) = 1$
- $S_2'(0) = 0$, $S_2'(1) = 0$
- $S_2''(0) = 0$, $S_2''(1) = 0$ (continuous acceleration across boundaries)

---

## 2. Python Implementation

```python
import numpy as np

def smoothstep(x, edge0=0.0, edge1=1.0) -> np.ndarray:
    """Evaluate standard C1 Hermite smoothstep over an array."""
    t = np.clip((x - edge0) / max(1e-6, edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def smootherstep(x, edge0=0.0, edge1=1.0) -> np.ndarray:
    """Evaluate Ken Perlin's C2 smootherstep (zero jerk at boundaries)."""
    t = np.clip((x - edge0) / max(1e-6, edge1 - edge0), 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
```

## 3. Practical Asset Applications
- **Tile Beveling**: Apply `smoothstep(dist_to_mortar, 0.0, 0.2)` to compute rounded corner bevels on flagstones.
- **VFX Shockwaves**: Modulate shockwave ring thickness by `smoothstep(phase, 0.0, 0.3) * (1.0 - phase)`.
- **Vertex Lighting**: Map height $z$ to a smooth ambient ground gradient without sharp geometric cutoff bands.
