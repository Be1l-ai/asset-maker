# AGENTS.md

Instructions and guidelines for AI agents and harnesses working in this repository.

## Overview

This repository develops procedural, deterministic, and code-only game assets across four core categories:
- **SFX**: Modal and additive audio synthesis exported as measured WAV files (`numpy`, `scipy`).
- **VFX**: Looping and one-shot sprite flipbook atlases with transparency (`Pillow`).
- **3D**: Watertight, low-poly solid geometry exported to GLB and OBJ (`trimesh`, `manifold3d`).
- **2D**: Vector-like raster icons, pixel art, and seamless tiles (`Pillow`, `aggdraw`).

## Agent Skills Architecture

Skills are maintained canonically in `skills/` and exposed to all standard agent harnesses:
- **`skills/`**: Canonical directory (Open Agent Skills specification)
- **`.agents/skills/`** and **`.agent/skills/`**: Antigravity, Gemini CLI, and Google Agent workflows
- **`.claude/skills/`**: Anthropic Claude Code
- **`.cursor/skills/`**: Cursor AI
- **`.qoder/skills/`**: Qoder harness

### Available Skills
- [`create-game-assets`](skills/create-game-assets/SKILL.md): Core workflow, API study, manifest provenance, and asset validation.
- [`create-sfx`](skills/create-sfx/SKILL.md): Sound design synthesis, audio metrics, and headroom guidelines.
- [`create-vfx`](skills/create-vfx/SKILL.md): Periodic animations, color ramps, alpha channels, and sprite sheets.
- [`create-3d-assets`](skills/create-3d-assets/SKILL.md): Watertight mesh CSG, coordinate transforms (Y-up vs Z-up), and triangle budgets.
- [`create-2d-assets`](skills/create-2d-assets/SKILL.md): Multi-layer 2D rendering, premultiplied alpha downsampling, and seamless tiling.

Consult [`skills/create-game-assets/references/libraries.md`](skills/create-game-assets/references/libraries.md) for approved upstreams and capabilities.

## Environment & Tooling

The project uses Python 3.12+ managed in `.venv-code-assets`:

```sh
# Setup virtual environment
python3 -m venv .venv-code-assets
.venv-code-assets/bin/python -m pip install -r requirements-code-assets.txt
```

### Running Tests
Execute the full test suite before committing changes:

```sh
.venv-code-assets/bin/python -m unittest discover -s tests -v
```

### Validating Assets
Validate exported assets against format, alpha, manifoldness, and triangle-count rules:

```sh
.venv-code-assets/bin/python skills/create-game-assets/scripts/validate_asset.py <asset-path>
```

## Commit Convention & Git Hooks

All commits must follow the **Conventional Commits** standard (enforced via `.githooks/commit-msg`):
- Format: `<type>(<optional scope>): <description>`
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Example: `feat(pipeline): add MeshBuilder class for solid CSG booleans`
- Pre-commit hook (`.githooks/pre-commit`) verifies Python syntax across staged files.
- See [`CONTRIBUTING.md`](CONTRIBUTING.md) for complete guidelines.

## Creating New Assets

When tasked with generating a new game asset:
1. **Scaffold from Template**:
   Run the scaffolding CLI:
   ```sh
   .venv-code-assets/bin/python -m asset_pipeline new <template> assets/<asset_name>
   ```
   Available templates: `2d_icon`, `2d_tile`, `3d_prop`, `vfx_flipbook`, `sfx_sound`.
   *(Or manually copy a folder from `templates/` into `assets/<asset_name>/`)*.
2. **Customize `generate.py`**:
   Import from `asset_pipeline` (`sfx`, `vfx`, `mesh3d`, `sprite2d`, `validator`, `manifest`) and implement the design.
3. **Execute & Validate**:
   ```sh
   cd assets/<asset_name> && python generate.py
   ```
   This automatically produces the asset file, preview, manifest, and runs validation.

## Repository Structure

- `asset_pipeline/`: Clean, modular Python library for procedural 2D, 3D, VFX, and SFX creation.
- `templates/`: Boilerplate starter folders for 2D icons, seamless tiles, 3D props, VFX flipbooks, and SFX.
- `assets/`: Destination directory for user and agent authored game assets.
- `skills/`: Project-local agent skills and starter scripts.
- `fx_pipeline/`: Core procedural generation scripts, helpers, and baseline flipbooks/SFX.
- `gallery/`: Interactive web catalog, pre-rendered assets, and export archives.
- `index.html`: Responsive gallery browser frontend.
- `tests/`: Unit tests verifying skill structure, recipes, and gallery functionality.
- `NOTES.md`: Historical generation log, recipes, and known-good fingerprints.
