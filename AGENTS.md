# AGENTS.md

Instructions and guidelines for AI agents and harnesses working in this repository.

## Overview

This repository develops procedural, deterministic, and code-only game assets across four core categories:
- **SFX**: Modal and additive audio synthesis exported as measured WAV files (`numpy`, `scipy`).
- **VFX**: Looping and one-shot sprite flipbook atlases with transparency (`Pillow`, `numpy`).
- **3D**: Watertight, low-poly solid geometry exported to GLB and OBJ (`trimesh`, `manifold3d`).
- **2D**: Vector-like raster icons, UI panels, and seamless tiles (`Pillow`, `aggdraw`, `numpy`).

## Agent Skills Architecture

Skills are maintained canonically in `skills/` and exposed via symlinks to all supported agent harnesses (`.agent/skills/`, `.agents/skills/`, `.claude/skills/`, `.cursor/skills/`, `.qoder/skills/`):

- [`create-game-assets`](skills/create-game-assets/SKILL.md): Master workflow, verification loop, manifest provenance, and Knowledge Vault index.
- [`create-sfx`](skills/create-sfx/SKILL.md): Physical modal synthesis, strike transients, Haas stereo panning, and `-3 dBFS` headroom.
- [`create-vfx`](skills/create-vfx/SKILL.md): Pre-rolled emitter stacks, buoyant plumes, cellular alpha erosion, and atlas packing.
- [`create-3d-assets`](skills/create-3d-assets/SKILL.md): Watertight Manifold CSG, subdivided lathe profiles, multiplicative ground AO, and Y-up export.
- [`create-2d-assets`](skills/create-2d-assets/SKILL.md): Mask-first SDF compositing, premultiplied alpha downsampling, and toroidal seamless tiling.

Consult [`skills/create-game-assets/references/libraries.md`](skills/create-game-assets/references/libraries.md) for pinned dependency versions and upstream API notes.

## Environment & Tooling

The project uses Python 3.12+ managed in `.venv-code-assets`:

```sh
# Setup virtual environment
python3 -m venv .venv-code-assets
.venv-code-assets/bin/python -m pip install -r requirements-code-assets.txt

# Run full test suite
.venv-code-assets/bin/python -m unittest discover -s tests -v

# Rebuild index.html after editing src/styles.css, src/body.html, or src/app.js
.venv-code-assets/bin/python build_html.py
```

## Creating & Auditing Assets

```sh
# 1. Scaffold from template (2d_icon, 2d_tile, 3d_prop, vfx_flipbook, sfx_sound)
.venv-code-assets/bin/python -m asset_pipeline new <template> <target_dir>

# 2. Customize generate.py using asset_pipeline and vault/, then run:
.venv-code-assets/bin/python <target_dir>/generate.py

# 3. Validate exported files and audit recipe/vault provenance:
.venv-code-assets/bin/python -m asset_pipeline validate <asset-file>
.venv-code-assets/bin/python -m asset_pipeline audit <target_dir>

# 4. Compare V1 and V2 asset folders when upgrading an existing asset:
.venv-code-assets/bin/python -m asset_pipeline compare <old_dir> <new_dir>
```

## Commit Convention & Git Hooks

All commits must follow the **Conventional Commits** standard (enforced via `.githooks/commit-msg`):
- Format: `<type>(<optional scope>): <description>`
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Pre-commit hook (`.githooks/pre-commit`) verifies Python syntax across staged files.
- See [`CONTRIBUTING.md`](CONTRIBUTING.md) for complete guidelines.

## Repository Structure

- `asset_pipeline/`: Modular Python SDK, validators, recipe auditor, CLI, and gallery generators.
- `vault/`: Curated Knowledge Vault of mathematical formulas, acoustic modal ratios, and material/VFX techniques.
- `templates/`: Starter templates for 2D icons, seamless tiles, 3D props, VFX flipbooks, and SFX.
- `skills/`: Project-local agent skills and starter scripts.
- `gallery/`: Interactive web catalog (`catalog.json`, `expansion/catalog.json`), pre-rendered assets, and reproducible ZIP archives.
- `src/` & `build_html.py`: Modular frontend source files (`styles.css`, `body.html`, `app.js`) and bundler for `index.html`.
- `index.html`: Self-contained responsive gallery browser frontend.
- `tests/`: Unit, verification layer, vault integrity, and Playwright browser tests.
- `NOTES.md`: Measured V1 vs. V2 asset comparisons and engineering log.
