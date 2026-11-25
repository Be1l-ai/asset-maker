---
name: create-vfx
description: Deep procedural VFX skill. Generate animated particle fields, energy bursts, magic effects, and transparent looping sprite sheet atlases using Pillow and NumPy.
---

# Procedural VFX Flipbook Generation

Generate animated visual effects and sprite sheet atlases in code using `Pillow` and `numpy`. Follow [`create-game-assets`](../create-game-assets/SKILL.md) for the master verification loop.

## Architectural Guidelines

### 1. Phase Math & Pre-Rolled Determinism
- **The $N$-Frame Rule**: Evaluate normalized phase $t_i = \frac{i}{N}$ for $i = 0, \dots, N-1$ (never $\frac{i}{N-1}$ on loops). For one-shot explosions, ensure alpha extinguishes cleanly by the final frame.
- **No Per-Frame RNG**: Pre-roll all random particle angles, speeds, radii, and noise maps **outside** the frame callback so trajectories move smoothly instead of teleporting each frame.

### 2. Multi-Layer Emitter Stack & Atlas Packing
- Compose distinct temporal stages (`Flash` $\to$ `Shockwave Core` $\to$ `Buoyant Smoke Plume` $\to$ `Ember Sparks`) with `EmitterStack` using `"add"` for incandescent energy and `"alpha"` for dark occluding smoke.
- Pack frames in row-major order ($C \times R$) with a 1-pixel transparent gutter around every cell to prevent bilinear texture bleed.

### 3. Knowledge Vault References
- **Four-Stage Emitter Stack**: [`vault/techniques/hybrid_vfx/four_stage_emitter_architecture.md`](../../vault/techniques/hybrid_vfx/four_stage_emitter_architecture.md) (`EmitterStack`).
- **Buoyant Smoke & Pyroclastic Plumes**: [`vault/techniques/hybrid_vfx/smoke_and_pyroclastic_plumes.md`](../../vault/techniques/hybrid_vfx/smoke_and_pyroclastic_plumes.md) (`Easing.ease_out`, pre-rolled puff tables, temperature cooling).
- **Cellular Alpha Erosion & Dissolve**: [`vault/techniques/hybrid_vfx/dissolve_and_alpha_erosion.md`](../../vault/techniques/hybrid_vfx/dissolve_and_alpha_erosion.md) (`dissolve_alpha_mask`, `worley_noise`).
- **3D Expanding Mesh Explosions & Ribbons**: [`vault/techniques/hybrid_vfx/mesh_particle_explosions.md`](../../vault/techniques/hybrid_vfx/mesh_particle_explosions.md) (`create_expanding_mesh_explosion`) & [`vault/techniques/hybrid_vfx/ribbon_trails_and_vortex_cones.md`](../../vault/techniques/hybrid_vfx/ribbon_trails_and_vortex_cones.md).

## Code Example: `Flipbook` & `EmitterStack`

```python
from asset_pipeline import EmitterStack, Flipbook, ParticleEmitter

def make_burst_flipbook(frames: int = 16, size: int = 128, fps: int = 16, seed: int = 7) -> Flipbook:
    emitter = ParticleEmitter(seed=seed)
    stack = EmitterStack(size=size)
    stack.add_layer("core", lambda p: emitter.radial_burst(size=size, phase=p, color_rgb=(100, 200, 255)), blend="add")

    flipbook = Flipbook(fps=fps)
    flipbook.generate_frames(count=frames, frame_generator=stack.composite_frame)
    return flipbook
```

## Domain Acceptance Checks

1. **Atlas Grid & Alpha**: `AssetValidator.validate_png(atlas_path, require_alpha=True, columns=C, rows=R)`.
2. **Temporal Coherence**: `AssetValidator.validate_animation(atlas_path, columns=C, rows=R)` (no static frames, no single-frame RNG pop spikes) and inspect `preview.png` contact sheet to confirm every emitter stage is visible.

## V6 Production Discipline (Mandatory Across All Modalities)
1. **Research-First & Seed the Vault**: Before writing code for any domain, silhouette, shader, or audio synthesis technique not already documented in `vault/`, research authoritative references (or `benchmarks/prompts.json`) and **seed a reusable `vault/techniques/...` guide** (and register it in `vault/README.md` + `manifest.json` `vault_refs`). Never improvise complex anatomy or DSP math without checking/seeding the vault.
2. **Optimize Representation (`vault/techniques/optimization/cross_modality_asset_optimization.md`)**:
   - **3D**: Use geometry strictly for silhouette; paint markings (stripes, emblems, seams) in albedo UVs and bake micro-relief (fur, wood grain, cloth weave) into tangent-space normal maps via `asset_pipeline.baking`.
   - **2D / UI**: Maximize alpha fill efficiency (`compute_sprite_alpha_efficiency`), clean value hierarchy, and power-of-two sizing.
   - **VFX**: Tight per-frame alpha bounds, channel-packed noise masks, and minimal overdraw.
   - **SFX**: Normalize to `-1.0 dBFS` headroom, high-pass sub-30 Hz mud, and ensure zero-crossing loop/tail cleanliness.
3. **Two-Tier Critique Loop (`asset_pipeline.critique.CritiqueLog`)**:
   - **Tier 1 (Inner Build Loop, min 3 rounds)**: Blockout -> Secondary -> Final candidate.
   - **Tier 2 (Outer 0-10 Detail-Critique Re-Loop, up to 5 outer passes)**: Score the Final 0-10 on hard modality-specific details (`add_detail_pass`). If the score is `< 9.0/10`, treat that Final as the **new starting point**, fix every identified detail flaw, and re-loop up to **5 outer passes** until it passes `>= 9.0/10`.
