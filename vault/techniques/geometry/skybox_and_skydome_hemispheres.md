# Skybox and Skydome Hemispheres

Geometric construction and atmospheric color gradients for procedural skies, distant horizons, and ambient world environments.

---

## 1. Geometric Formulations

1. **Inverted Skydome Hemisphere**:
   - A hemisphere centered at $(0, 0, 0)$ with radius $R$ ($R \gg 100$) where face winding is inverted so triangles face **inward** toward the origin:
     $$\mathbf{P}(\theta, \phi) = \begin{pmatrix} R \cos(\theta) \sin(\phi) \\ R \sin(\theta) \sin(\phi) \\ R \cos(\phi) \end{pmatrix}$$
     where $\theta \in [0, 2\pi]$ (azimuth) and $\phi \in [0, \pi/2]$ (zenith angle).
2. **Infinite Z-Buffer Trick**:
   - In modern game engines, the skydome is rendered with depth-test enabled but depth-write disabled (`depthWrite = false`), ensuring the sky never clips foreground props.

---

## 2. Atmospheric Rayleigh / Mie Scattering Color Ramp

The color of the sky changes as zenith angle $\phi$ sweeps from the horizon ($\phi = \pi/2$, elevation $z = 0$) to the zenith ($\phi = 0$, apex $z = R$):

1. **Zenith Apex ($z = R$)**: Deep indigo or royal blue (`[30, 60, 140]`).
2. **Mid-Sky ($z = 0.5R$)**: Azure cyan (`[90, 160, 230]`).
3. **Horizon ($z = 0$)**: Warm golden/peach haze (`[240, 190, 130]`) or sunset crimson (`[250, 110, 70]`).
4. **Ground Baseline ($z < 0$)**: Desaturated ambient haze (`[60, 70, 85]`).

---

## 3. Vertex Color Sky Baking in Python

```python
import numpy as np
import trimesh

def create_procedural_skydome(radius: float = 50.0, subdivisions: int = 2):
    """Generate an inward-facing low-poly skydome with atmospheric height gradient."""
    sphere = trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius)
    # Filter to upper hemisphere (z >= -0.1)
    mask = sphere.vertices[:, 2] >= -radius * 0.1
    # Flip face normals inward
    sphere.faces = np.fliplr(sphere.faces)

    # Gradient from horizon to zenith
    z = sphere.vertices[:, 2]
    t = np.clip(z / radius, 0.0, 1.0)[:, None]
    horizon = np.array([240, 190, 140, 255])
    zenith = np.array([35, 75, 170, 255])
    v_colors = (horizon + t * (zenith - horizon)).astype(np.uint8)

    sphere.visual = trimesh.visual.ColorVisuals(mesh=sphere, vertex_colors=v_colors)
    return sphere
```
