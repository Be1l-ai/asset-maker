# Mesh Ribbon Trails and Vortex Cones

Geometry-driven visual effects using procedural quad strips, helix ribbons, and cone funnels.

---

## 1. Why Mesh Ribbons Outperform Particles for Trails

Particles spawn as disjointed billboard circles. At high speeds, fast projectiles (arrows, magical missiles, sword slashes) leave dotted, segmented trails unless particle emission rates are cranked to thousands per second (causing severe GPU fill-rate drop).

In contrast, a **procedural mesh ribbon**:
- Connects historical position points into a continuous connected strip of quad triangles.
- Uses an additive glowing gradient texture with UV coordinates running from $U=0$ (tail) to $U=1$ (head).
- Uses only 20 to 60 triangles while remaining perfectly smooth at any speed.

---

## 2. Geometry Formulations

### Continuous Quad Strip
Given $N$ historical center positions $\mathbf{C}_k \in \mathbb{R}^3$ and normal vectors $\vec{N}_k$:
$$\mathbf{V}_{2k} = \mathbf{C}_k - \frac{w_k}{2} \vec{N}_k, \quad \mathbf{V}_{2k+1} = \mathbf{C}_k + \frac{w_k}{2} \vec{N}_k$$
Triangles connect $(2k, 2k+1, 2k+2)$ and $(2k+1, 2k+3, 2k+2)$.

### Vortex Cone / Spiral Mesh
For magical tornadoes, charging drills, and spell funnels:
$$x(t) = r(t) \cos(\omega t), \quad y(t) = r(t) \sin(\omega t), \quad z(t) = h \cdot t$$
where $r(t) = r_{\text{base}} \cdot t^2$ creates an expanding parabolic funnel.

---

## 3. Python Implementation Example

```python
import numpy as np
import trimesh

def create_helix_ribbon(num_turns: float = 3.0, height: float = 2.0, radius: float = 0.5, steps: int = 40):
    """Generate a 3D spiral ribbon mesh for swirling magic projectile trails."""
    t = np.linspace(0.0, 1.0, steps)
    theta = t * (2.0 * np.pi * num_turns)
    r = radius * (1.0 - t * 0.5)

    cx = r * np.cos(theta)
    cy = r * np.sin(theta)
    cz = height * t

    verts, faces = [], []
    half_w = 0.05
    for i in range(steps):
        verts.append([cx[i], cy[i] - half_w, cz[i]])
        verts.append([cx[i], cy[i] + half_w, cz[i]])
        if i < steps - 1:
            i0, i1 = 2 * i, 2 * i + 1
            i2, i3 = 2 * (i + 1), 2 * (i + 1) + 1
            faces.append([i0, i1, i2])
            faces.append([i1, i3, i2])

    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
```
