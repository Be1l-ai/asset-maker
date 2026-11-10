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
