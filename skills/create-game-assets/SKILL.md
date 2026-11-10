---
name: create-game-assets
description: Master procedural game asset generation workflow. Pure Python code-only pipeline for creating, validating, and cataloging 2D sprites, 3D meshes, animated VFX flipbooks, and synthesized SFX without DCC applications.
---

# Procedural Game Asset Generation

This is the primary workflow for authoring code-only, deterministic game assets across 2D, 3D, VFX, and SFX.

## Core Philosophy

- **Code-Only**: Assets are generated strictly via Python libraries (`numpy`, `scipy`, `Pillow`, `aggdraw`, `trimesh`, `manifold3d`). No Blender, DAW, drawing apps, external renderers, or generative cloud APIs.
- **Deterministic & Seeded**: Every asset recipe takes an explicit integer `--seed` so outputs are reproducible across environments.
- **Self-Contained & Validated**: Every asset folder contains its primary export, diagnostic visual preview, reproducible generator recipe, and verified `manifest.json`.

## The Knowledge Vault

Before coding a new asset, consult the **[Knowledge Vault](../../vault/README.md)** for verified formulas, ratios, and professional art techniques:
- **Formulas & Math**: [`vault/mathematics/`](../../vault/README.md#1-mathematics--acoustics-vaultmathematics) (Acoustic modal ratios, Bezier curves, Worley noise, Sobel normal derivation).
- **Industry Techniques**: [`vault/techniques/`](../../vault/README.md#2-professional-industry-techniques-vaulttechniques) (70/30 stylized art rules, hybrid 3D+flipbook VFX, PBR channels, foliage normal bending).
- **Out of Scope (3D Animation)**: [`vault/future_scope/3d_skeletal_animation.md`](../../vault/future_scope/3d_skeletal_animation.md) (Never generate skeletal animations from scratch).

## Quick Scaffolding Workflow

To create a new asset, scaffold from standard templates into `assets/<asset_name>/`:

```sh
# Choose template: 2d_icon, 2d_tile, 3d_prop, vfx_flipbook, sfx_sound
.venv-code-assets/bin/python -m asset_pipeline new <template> assets/<asset_name>
```

Navigate to the created directory, customize the recipe in `generate.py`, and run:

```sh
cd assets/<asset_name> && python generate.py
```

This outputs the asset, generates dark/light previews, validates formatting, and writes checksums to `manifest.json`.

## Domain Specialist Matrix

Consult the specialist skill for deep mathematical, geometric, and acoustic recipes:

| Asset Type | Specialist Skill | Primary Libraries | Key Domain Rules |
|---|---|---|---|
| **3D Props & Solids** | [create-3d-assets](../create-3d-assets/SKILL.md) | `trimesh`, `manifold3d` | Watertight solids, Manifold CSG booleans, Z-to-Y export, $\le 3000$ triangles |
| **2D Icons & Tiles** | [create-2d-assets](../create-2d-assets/SKILL.md) | `Pillow`, `aggdraw`, `numpy` | Super-sampled Bezier paths, premultiplied alpha downsampling, 1px transparent gutter |
| **VFX Flipbooks** | [create-vfx](../create-vfx/SKILL.md) | `Pillow`, `numpy` | Normalized phase $t = i/N$, easing dynamics, row-major atlas packing, looping GIF |
| **SFX Audio** | [create-sfx](../create-sfx/SKILL.md) | `numpy`, `scipy` | Modal resonance modes, transient impact clicks, $-3\text{ dBFS}$ headroom, PCM16 |

Consult the [library catalog](references/libraries.md) for approved upstreams and capabilities.

## Verification & Test Suite

Verify all assets and generator code against structural constraints:

```sh
# Validate individual asset files (WAV, PNG, GLB, OBJ):
.venv-code-assets/bin/python skills/create-game-assets/scripts/validate_asset.py <asset_path>

# Run full repository test suite:
.venv-code-assets/bin/python -m unittest discover -s tests -v
```

Structural validation enforces alpha presence, atlas grid divisibility, mesh watertightness, and audio non-clipping. Always inspect visual previews and listen to audio playback before declaring an asset complete.

## Verification Loop (Required)

Structural validation proves a file is well-formed, not that it is good. Before declaring any asset done:

1. **Look.** Open `preview.png` (3D: three views; tile: albedo + normal-lit; VFX: contact sheet). Name one concrete defect, fix it, re-render. Read [`vault/pitfalls/procedural_failure_modes.md`](../../vault/pitfalls/procedural_failure_modes.md).
2. **Declare the vault.** For every vault doc you applied, call `manifest.declare_vault("<path under vault/>", "<pipeline symbol you call>")`. Never import a technique you do not call.
3. **Audit.** `.venv-code-assets/bin/python -m asset_pipeline audit assets/<name>` must pass (no unused pipeline imports, real vault docs, symbols actually used, no stale hashes).
4. **Domain acceptance:** run the domain check from the specialist skill; `python -m unittest discover -s tests` stays green.
5. **Hash only your files:** `manifest.scan_directory(out, only=[ASSET_NAME])`.
6. **Compare to the baseline with numbers** if this replaces an earlier version: `python -m asset_pipeline compare <old> <new>`. Do not state numbers in a README that are not in the manifest.
