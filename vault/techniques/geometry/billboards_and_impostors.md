# Billboards, Impostors, and 2D-in-3D Cards

Techniques for rendering distant trees, UI indicators, particle sparks, and volumetric impostors using 2D planes aligned with the camera.

---

## 1. Spherical vs. Cylindrical Billboarding

### Spherical (Camera-Facing) Billboarding
The quad's normal vector $\vec{N}$ tracks the camera vector $\vec{V}_{\text{cam}}$ on all 3 axes:
$$\vec{Z}_{\text{quad}} = \frac{\mathbf{P}_{\text{cam}} - \mathbf{P}_{\text{object}}}{\|\mathbf{P}_{\text{cam}} - \mathbf{P}_{\text{object}}\|}, \quad \vec{X}_{\text{quad}} = \frac{\vec{Z}_{\text{quad}} \times \vec{Y}_{\text{up}}}{\|\vec{Z}_{\text{quad}} \times \vec{Y}_{\text{up}}\|}, \quad \vec{Y}_{\text{quad}} = \vec{Z}_{\text{quad}} \times \vec{X}_{\text{quad}}$$
- Used for: particles, shockwaves, lens flares, glowing orbs.

### Cylindrical (Axis-Aligned) Billboarding
The quad rotates **only around the vertical $Z$-axis** (yaw), keeping its pitch locked parallel to gravity:
- Used for: distant trees, lampposts, fence posts, sprite characters in 2.5D games (*Doom*, *Octopath Traveler*).
- Prevents trees from tilting unnaturally when the camera looks down from high angles.

---

## 2. Multi-Angle Impostors (Octahedral / 8-Way Sprites)

For complex props (e.g. vehicles, characters, distant statues):
- The asset's appearance is pre-rendered from 8 angles around the compass ($0^\circ, 45^\circ, 90^\circ, \dots, 315^\circ$) packed into a $4 \times 2$ or $8 \times 1$ sprite sheet.
- At runtime, the shader samples the sub-frame matching:
  $$\text{frame\_idx} = \left\lfloor \frac{\theta_{\text{camera}} + 22.5^\circ}{45^\circ} \right\rfloor \pmod 8$$
- Allows a 4-triangle card to represent a 50,000-triangle asset seamlessly from across the game map.
