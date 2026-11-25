---
name: create-game-assets
description: Master procedural game asset generation workflow. Pure Python code-only pipeline for creating, validating, and cataloging 2D sprites, 3D meshes, animated VFX flipbooks, and synthesized SFX without DCC applications.
---

# Procedural Game Asset Generation

Primary workflow for authoring code-only, deterministic game assets across 2D, 3D, VFX, and SFX (scaffolding, environment setup, and test commands are defined in [`AGENTS.md`](../../AGENTS.md)).

## Core Philosophy

- **Code-Only**: Assets are generated strictly via Python libraries (`numpy`, `scipy`, `Pillow`, `aggdraw`, `trimesh`, `manifold3d`)—see [library catalog](references/libraries.md). No DCC apps, external renderers, or generative cloud APIs.
- **Deterministic & Seeded**: Every asset recipe takes an explicit integer `--seed` so outputs are reproducible across environments.
- **Self-Contained & Validated**: Every asset folder contains its primary export, diagnostic visual preview, reproducible generator recipe, and verified `manifest.json`.

## The Knowledge Vault

Before coding a new asset, consult the **[Knowledge Vault](../../vault/README.md)** for verified formulas, ratios, and professional art techniques:
- **Formulas & Math**: [`vault/mathematics/`](../../vault/README.md#1-mathematics--acoustics-vaultmathematics) (Acoustic modal ratios, Haas stereo panning, Bezier curves, Worley noise, Sobel normal derivation).
- **Industry Techniques**: [`vault/techniques/`](../../vault/README.md#2-professional-industry-techniques-vaulttechniques) (70/30 stylized art rules, glass & liquid vessels, chiseled stone masonry, buoyant smoke plumes, foliage normal bending).
- **Pitfalls & Failure Modes**: [`vault/pitfalls/procedural_failure_modes.md`](../../vault/pitfalls/procedural_failure_modes.md).
- **Out of Scope (3D Animation)**: [`vault/future_scope/3d_skeletal_animation.md`](../../vault/future_scope/3d_skeletal_animation.md).

## Domain Specialist Matrix

Consult the specialist skill for domain-specific architecture and acceptance checks:

| Asset Type | Specialist Skill | Primary Libraries | Key Domain Rules |
|---|---|---|---|
| **3D Props & Solids** | [create-3d-assets](../create-3d-assets/SKILL.md) | `trimesh`, `manifold3d` | Watertight solids, Manifold CSG booleans, Z-to-Y export, $\le 3000$ triangles |
| **2D Icons & Tiles** | [create-2d-assets](../create-2d-assets/SKILL.md) | `Pillow`, `aggdraw`, `numpy` | Super-sampled SDF/Bezier masks, premultiplied alpha downsampling, 1px gutter |
| **VFX Flipbooks** | [create-vfx](../create-vfx/SKILL.md) | `Pillow`, `numpy` | Normalized phase $t = i/N$, pre-rolled RNG, row-major atlas packing, looping GIF |
| **SFX Audio** | [create-sfx](../create-sfx/SKILL.md) | `numpy`, `scipy` | Modal resonance modes, transient impact clicks, $-3\text{ dBFS}$ headroom, PCM16 |

## Verification Loop (Required for All Assets)

Structural validation proves a file is well-formed, not that it is good. Before declaring any asset done:

1. **Look.** Open `preview.png` (3D: three views; tile: albedo + normal-lit; VFX: contact sheet). Name one concrete defect, fix it, re-render. Read [`vault/pitfalls/procedural_failure_modes.md`](../../vault/pitfalls/procedural_failure_modes.md).
2. **Declare the vault.** For every vault doc you applied, call `manifest.declare_vault("<path under vault/>", "<pipeline symbol you call>")`. Never import a technique you do not call.
3. **Audit.** `.venv-code-assets/bin/python -m asset_pipeline audit assets/<name>` must pass (no unused pipeline imports, real vault docs, symbols actually used, no stale hashes).
4. **Domain acceptance.** Run the domain validator specified in the specialist skill (`validate_silhouette`, `validate_seamless`, `validate_mesh_shading`, `validate_animation`, `validate_wav`).
5. **Hash only your files.** `manifest.scan_directory(out, only=[ASSET_NAME])`.
6. **Compare to the baseline with numbers** if replacing an earlier version: `.venv-code-assets/bin/python -m asset_pipeline compare <old> <new>`. Do not state numbers in documentation that are not in the manifest.

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
