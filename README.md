# AssetMaking

A procedural, code-first game asset generation pipeline and interactive gallery. Generate deterministic 2D icons, 3D meshes, particle flipbooks (VFX), and synthesized audio (SFX) using pure Python without external DCC tools.

## Features

- **2D Asset Generation**: Antialiased icons, badges, UI elements, and tileable textures with Pillow and aggdraw.
- **3D Asset Generation**: Watertight, low-poly solid geometry with Trimesh and Manifold3D, exported as GLB (colored) and OBJ.
- **VFX Generation**: Periodic particle fields, looping energy bursts, and multi-frame transparent flipbook atlases.
- **SFX Generation**: Procedural modal, additive, and noise synthesis using NumPy and SciPy with standard headroom controls.
- **Interactive Gallery**: Browser-based catalog (`index.html`) with interactive 3D WebGL inspection, audio playback, flipbook scrubbers, and zip exports.
- **Multi-Harness Agent Skills**: Pre-configured skills compatible with Antigravity, Gemini CLI, Claude Code, Cursor, and Qoder.

## Quick Start

### 1. Environment Setup

Python 3.12+ is required. Set up the dedicated virtual environment:

```sh
python3 -m venv .venv-code-assets
.venv-code-assets/bin/python -m pip install -r requirements-code-assets.txt
```

### 2. View the Gallery

Open `index.html` in your browser or run a lightweight local HTTP server:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000/` to inspect assets, preview animations, and download asset collections.

### 3. Run Tests

Verify skill compliance, generator recipes, and gallery functionality:

```sh
.venv-code-assets/bin/python -m unittest discover -s tests -v
```

## Creating New Assets

Creating a new procedural asset takes only 3 steps:

### 1. Scaffold from a Template
Use the scaffolding CLI or copy from [`templates/`](templates/):

```sh
# Options: 2d_icon, 2d_tile, 3d_prop, vfx_flipbook, sfx_sound
.venv-code-assets/bin/python -m asset_pipeline new 3d_prop assets/my_pillar
```

### 2. Customize `generate.py`
Open `assets/my_pillar/generate.py`. Import clean primitives and operations from `asset_pipeline`:

```python
from asset_pipeline import mesh3d, validator, manifest

def build(seed: int = 7):
    # Construct watertight solids, apply colors, booleans...
    base = mesh3d.create_cylinder(radius=0.4, height=0.2, color=[80, 80, 90, 255])
    return base
```

### 3. Generate & Validate
Run `python generate.py`:

```sh
cd assets/my_pillar && python generate.py
```

This renders the export artifact (GLB/OBJ/PNG/WAV), generates a visual preview (`preview.png`/`preview.gif`), validates structure, and writes `manifest.json`.

---

## Agent Skills

Specialized agent workflows are located in [`skills/`](skills/) and mapped via symlinks for all major harnesses (`.agents`, `.claude`, `.cursor`, `.qoder`):

- **[`create-game-assets`](skills/create-game-assets/SKILL.md)**: API research, manifest provenance, and asset validation.
- **[`create-2d-assets`](skills/create-2d-assets/SKILL.md)**: Pillow / aggdraw vector-style rendering and seamless tiling.
- **[`create-3d-assets`](skills/create-3d-assets/SKILL.md)**: Trimesh / Manifold solid CSG, watertightness, and axis alignment.
- **[`create-vfx`](skills/create-vfx/SKILL.md)**: Periodic animated flipbooks, easing, and RGBA atlas packing.
- **[`create-sfx`](skills/create-sfx/SKILL.md)**: NumPy / SciPy modal synthesis, envelope shaping, and WAV metrics.

Validate any generated asset file with:

```sh
.venv-code-assets/bin/python skills/create-game-assets/scripts/validate_asset.py <path/to/asset>
```

For library information and guidelines, see [`skills/create-game-assets/references/libraries.md`](skills/create-game-assets/references/libraries.md).

## Project Structure

```
├── skills/                     # Canonical Agent Skills
├── vault/                      # Procedural Game Asset Knowledge Vault
├── asset_pipeline/             # Modular Python SDK, validators, and gallery generators
│   ├── generate_gallery.py     # Base gallery generator
│   └── generate_gallery_expansion.py
├── gallery/                    # Gallery data, assets, and collection ZIPs
├── tests/                      # Comprehensive test suite
├── index.html                  # Responsive gallery frontend
├── AGENTS.md                   # Instructions for AI harnesses
├── NOTES.md                    # Project history, generation logs, and fingerprints
└── requirements-code-assets.txt
```
