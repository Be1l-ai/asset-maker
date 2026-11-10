# Billboards, Impostors, and 2D-in-3D Cards

Techniques for rendering distant foliage, UI indicators, particle sparks, and volumetric impostors using 2D planes aligned with the camera.

---

## 1. Spherical vs. Cylindrical Billboarding

### Spherical (Camera-Facing) Billboarding
The quad's normal vector $\vec{N}$ tracks the camera vector $\vec{V}_{\text{cam}}$ on all 3 axes:
$$\vec{Z}_{\text{quad}} = \frac{\mathbf{P}_{\text{cam}} - \mathbf{P}_{\text{object}}}{\|\mathbf{P}_{\text{cam}} - \mathbf{P}_{\text{object}}\|}, \quad \vec{X}_{\text{quad}} = \frac{\vec{Y}_{\text{up}} \times \vec{Z}_{\text{quad}}}{\|\vec{Y}_{\text{up}} \times \vec{Z}_{\text{quad}}\|}, \quad \vec{Y}_{\text{quad}} = \vec{Z}_{\text{quad}} \times \vec{X}_{\text{quad}}$$
- **Used for**: Spherical particles, arcane burst shockwaves, lens flares, glowing mana orbs.

### Cylindrical (Axis-Aligned) Billboarding
The quad rotates **only around the vertical $Z$-axis** (yaw), keeping its vertical axis locked parallel to gravity $\vec{Z}_{\text{up}} = (0, 0, 1)$:
$$\vec{N}_{\text{horiz}} = \frac{(P_{\text{cam}, x} - P_{\text{obj}, x},\; P_{\text{cam}, y} - P_{\text{obj}, y},\; 0)}{\sqrt{\Delta x^2 + \Delta y^2}}$$
- **Used for**: Distant trees, torches, pillars, and sprite props in 2.5D worlds (*Doom*, *Octopath Traveler*).
- Prevents tall vertical props from tilting unnaturally when the camera pitches down from high elevation angles.

---

## 2. Crossed-Plane (X-Quad / Star-Quad) Impostors

When a billboard must be viewed from arbitrary angles without runtime shader rotation, intersect $K \in \{2, 3\}$ vertical alpha cards rotated at equal azimuthal intervals $\Delta\theta = \pi / K$ ($90^\circ$ for an X-quad, $60^\circ$ for a 3-plane star cluster) and bend their vertex normals radially outward via [`apply_spherical_normals`](file:///home/bel/Workspace/AssetMaking/asset_pipeline/mesh3d.py):

```python
import numpy as np
import trimesh
from asset_pipeline import apply_spherical_normals, create_leaf_card

# Construct a 3-way crossed alpha-card shrub impostor (0, 60, 120 degrees)
cards = []
for k in range(3):
    card = create_leaf_card(width=0.8, height=1.0, curvature=0.08, color=[75, 165, 65, 255])
    rot = trimesh.transformations.rotation_matrix(k * np.pi / 3.0, [0, 0, 1])
    card.apply_transform(rot)
    cards.append(card)

impostor_cluster = trimesh.util.concatenate(cards)
apply_spherical_normals(impostor_cluster, center=[0.0, 0.0, 0.4])
```

---

## 3. Multi-Angle Octahedral / 8-Way Sprite Impostors

For complex distant props (statues, towers, vehicles):
- Pre-render the 3D asset from $M = 8$ compass azimuths ($\theta_k = k \cdot 45^\circ$) into an atlas.
- At runtime, select the frame index from camera azimuth $\theta_{\text{cam}}$:
  $$\text{frame\_idx} = \left\lfloor \frac{\theta_{\text{cam}} + 22.5^\circ}{45^\circ} \right\rfloor \bmod 8$$
