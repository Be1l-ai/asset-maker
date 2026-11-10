# The Procedural Game Asset Knowledge Vault

A curated, modular library of mathematical formulas, acoustic ratios, procedural algorithms, and professional art direction techniques for procedural game asset engineering.

---

## How Agents Should Use This Vault

Each document in this vault is **atomic and self-contained** (typically < 300 lines). When authoring an asset, **do not read the entire vault**. Instead, navigate directly to the specific atomic document matching your current technical challenge:

### 1. Mathematics & Acoustics (`vault/mathematics/`)
- **Geometry & Curves**:
  - [`geometry/beziers_and_splines.md`](mathematics/geometry/beziers_and_splines.md) — Cubic/quadratic Bernstein polynomials, curvature, and tangent vectors.
  - [`geometry/smoothstep_and_interpolation.md`](mathematics/geometry/smoothstep_and_interpolation.md) — $C^1$ and $C^2$ Hermite smoothstep curves, easing transitions.
  - [`geometry/spirals_and_golden_ratio.md`](mathematics/geometry/spirals_and_golden_ratio.md) — Archimedean & logarithmic spirals, golden section $\phi$, phyllotaxis.
- **Acoustic Physical Modeling (Modal Ratios & Decays)**:
  - [`acoustics/uniform_bars_metal.md`](mathematics/acoustics/uniform_bars_metal.md) — Euler-Bernoulli roots ($1.0, 2.76, 5.40, 8.93$) for glockenspiels and metal bars.
  - [`acoustics/undercut_bars_wood.md`](mathematics/acoustics/undercut_bars_wood.md) — Center-undercut marimba/xylophone tuned harmonic octave modes ($1.0, 4.0, 10.0$).
  - [`acoustics/tubular_chimes.md`](mathematics/acoustics/tubular_chimes.md) — Hollow suspended tube flexural modes ($1.0, 4.2, 9.7$).
  - [`acoustics/church_bells_bronze.md`](mathematics/acoustics/church_bells_bronze.md) — Cast bronze bells: Hum ($0.5$), Prime ($1.0$), Tierce ($1.2$), Quint ($1.5$), Nominal ($2.0$).
  - [`acoustics/glass_shells.md`](mathematics/acoustics/glass_shells.md) — Circumferential flexural $(m=2)$ shell vibrations and low-damping resonance.
  - [`acoustics/spatial_haas_and_transients.md`](mathematics/acoustics/spatial_haas_and_transients.md) — Constant-power sine/cosine stereo panning, Haas precedence delay ($\Delta t \in [1, 15]\text{ ms}$), and mallet strike transients.
- **Noise & Periodic Fields**:
  - [`noise_and_fields/worley_cellular_noise.md`](mathematics/noise_and_fields/worley_cellular_noise.md) — Sparse grid $F_1, F_2$ metrics for cobblestone, cracked stone, cells.
  - [`noise_and_fields/toroidal_periodic_harmonics.md`](mathematics/noise_and_fields/toroidal_periodic_harmonics.md) — Multi-harmonic continuous Fourier sums for seamless $2\pi$ wrapping.
  - [`noise_and_fields/domain_warping.md`](mathematics/noise_and_fields/domain_warping.md) — Recursive coordinate warping $f(\mathbf{p} + \alpha \mathbf{g}(\mathbf{p}))$.
- **Materials & Tangent Space**:
  - [`materials/height_to_normal_sobel.md`](mathematics/materials/height_to_normal_sobel.md) — Deriving tangent-space normal maps from scalar heightfields using Sobel convolution.
  - [`materials/pbr_channel_standards.md`](mathematics/materials/pbr_channel_standards.md) — Mathematical encoding for Albedo, Roughness, Metallic, Normal, AO, and Height channels.

### 2. Professional Industry Techniques (`vault/techniques/`)
- **Stylized Art Direction Rules**:
  - [`art_styles/silhouette_and_proportions.md`](techniques/art_styles/silhouette_and_proportions.md) — The 70/30 rule, negative space, and 32px/64px thumbnail readability.
  - [`art_styles/bevels_and_edge_weight.md`](techniques/art_styles/bevels_and_edge_weight.md) — Wide stylized chamfers, turned lathe profiles (`MeshBuilder.lathe`), and 2D SDF morphological fillets (`fillet_mask`).
  - [`art_styles/color_ramps_and_cel_steps.md`](techniques/art_styles/color_ramps_and_cel_steps.md) — Warm lit / cool shadow temperature ramps (`hsv_to_rgb`, `lerp_color`), quantized cel thresholds.
  - [`art_styles/vertex_color_gradient_baking.md`](techniques/art_styles/vertex_color_gradient_baking.md) — Multiplicative ground contact AO (`bake_ground_ao`) and full vertical gradient baking (`bake_vertex_gradient_ao`).
- **Hybrid VFX Architectures**:
  - [`hybrid_vfx/mesh_particle_explosions.md`](techniques/hybrid_vfx/mesh_particle_explosions.md) — Combining 3D expanding mesh sphere clusters with particle flipbook sheets.
  - [`hybrid_vfx/ribbon_trails_and_vortex_cones.md`](techniques/hybrid_vfx/ribbon_trails_and_vortex_cones.md) — Swept mesh ribbons, vortex cones, and UV-scrolling trail geometry.
  - [`hybrid_vfx/four_stage_emitter_architecture.md`](techniques/hybrid_vfx/four_stage_emitter_architecture.md) — The Flash $\to$ Blast Core $\to$ Flipbook Plume $\to$ Dissipation stack.
  - [`hybrid_vfx/smoke_and_pyroclastic_plumes.md`](techniques/hybrid_vfx/smoke_and_pyroclastic_plumes.md) — Buoyant plume kinematics (`Easing.ease_out`), pre-rolled puff tables, temperature cooling ramps, and cellular smoke erosion.
  - [`hybrid_vfx/dissolve_and_alpha_erosion.md`](techniques/hybrid_vfx/dissolve_and_alpha_erosion.md) — Noise threshold cutoffs, step functions, and burning border edges.
- **Procedural PBR Materials**:
  - [`materials/glass_and_liquid_vessels.md`](techniques/materials/glass_and_liquid_vessels.md) — Schlick Fresnel 2D rim opacity (`inside_depth`), Beer-Lambert subsurface core glow, meniscus catch-lights, and height domes.
  - [`materials/chiseled_stone_and_masonry.md`](techniques/materials/chiseled_stone_and_masonry.md) — Running bond distance fields, Hermite bevels, edge-localized Worley chipping, mortar crevice AO, and turned 3D stone plinths.
  - [`materials/fabric_and_weave_patterns.md`](techniques/materials/fabric_and_weave_patterns.md) — Interlaced warp and weft textile patterns for characters and props.
  - [`materials/wood_grain_growth_rings.md`](techniques/materials/wood_grain_growth_rings.md) — Eccentric elliptical rings, early/latewood transitions, and ray perturbations.
- **Geometry Tricks & Impostors**:
  - [`geometry/foliage_spherical_normal_bending.md`](techniques/geometry/foliage_spherical_normal_bending.md) — Canopy vertex normal transfer $\vec{N}_v = \text{norm}(\vec{P}_v - \vec{C}_{\text{canopy}})$ for lush volumetric tree shading.
  - [`geometry/leaf_cards_and_alpha_branching.md`](techniques/geometry/leaf_cards_and_alpha_branching.md) — Overdraw optimization, cross-quads, and branch hierarchies.
  - [`geometry/skybox_and_skydome_hemispheres.md`](techniques/geometry/skybox_and_skydome_hemispheres.md) — Inverted hemisphere geometries and atmospheric scattering color ramps.
  - [`geometry/billboards_and_impostors.md`](techniques/geometry/billboards_and_impostors.md) — Camera-facing quads, cylindrical billboard math, and multi-angle impostors.

### 3. Pitfalls & Acceptance Checks (`vault/pitfalls/`)
- [`pitfalls/procedural_failure_modes.md`](pitfalls/procedural_failure_modes.md) — Real failures that passed structural validation (aggdraw erase, floating parts, tile seams, dead AO calls, per-frame RNG jitter) with the fix and the automated check for each. **Read before finishing any asset.**

### 4. Out-of-Scope Roadmap (`vault/future_scope/`)
- [`future_scope/3d_skeletal_animation.md`](future_scope/3d_skeletal_animation.md) — Explains why procedural 3D skeletal animation from scratch is out of scope and outlines the roadmap for standard skeleton rig templates and reusable motion sequence banks.
