# Procedural Stone Masonry and Chiseled Flagstones

Formulas for running bond brick patterns, chiseled corner bevels, mortar crevice ambient occlusion, and mineral surface noise.

---

## 1. Running Bond Grid Mathematics

In running bond brickwork, alternate rows are staggered by half a block width to prevent vertical continuous fault lines:

Given $N_{\text{rows}}$ and $N_{\text{cols}}$:
1. Normalized vertical row index:
   $$r = \lfloor y \cdot N_{\text{rows}} \rfloor, \quad v_{\text{frac}} = (y \cdot N_{\text{rows}}) - r$$
2. Horizontal stagger offset:
   $$\text{shift} = \begin{cases} \frac{0.5}{N_{\text{cols}}} & \text{if } r \text{ is odd} \\ 0.0 & \text{if } r \text{ is even} \end{cases}$$
3. Staggered column index:
   $$x' = (x + \text{shift}) \pmod{1.0}$$
   $$c = \lfloor x' \cdot N_{\text{cols}} \rfloor, \quad u_{\text{frac}} = (x' \cdot N_{\text{cols}}) - c$$

---

## 2. Mortar Crevice and Bevel Distance Fields

Distance from brick center to edges along horizontal and vertical axes:
$$d_x = 2 \cdot |u_{\text{frac}} - 0.5|, \quad d_y = 2 \cdot |v_{\text{frac}} - 0.5|$$
Edge distance:
$$D_{\text{edge}} = \max(d_x, d_y) \in [0, 1]$$

For mortar width $w_m \approx 0.12$:
- **Mortar Mask**: $\text{is\_mortar} = (D_{\text{edge}} > 1.0 - w_m)$.
- **Chiseled Bevel**: Inside the brick, apply Hermite smoothstep to $D_{\text{edge}}$ to round the stone face toward the mortar joint.

---

## 3. Combining with Worley Noise

Multiplying the masonry distance field by a low-frequency Worley noise map creates realistic weathered stone pitting, broken corners, and chiseled fractures along mortar edges.
