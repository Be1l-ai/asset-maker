# AssetMaking

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-87%20Passed-2ea44f?logo=github-actions&logoColor=white)]()
[![Pipelines](https://img.shields.io/badge/Pipelines-2D%20%7C%203D%20%7C%20VFX%20%7C%20SFX-blueviolet)]()
[![Formats](https://img.shields.io/badge/Formats-GLB%20%7C%20OBJ%20%7C%20PNG%20%7C%20WAV-orange)]()
[![Engine](https://img.shields.io/badge/Workflow-Deterministic%20%26%20Code--Only-blue)]()

`procedural-generation` · `game-assets` · `gamedev` · `3d-mesh` · `csg-booleans` · `vfx-flipbook` · `sfx-synthesis` · `python` · `trimesh` · `manifold3d` · `knowledge-vault` · `agent-skills`

---

Procedural game asset generation in pure Python (`numpy`, `scipy`, `Pillow`, `aggdraw`, `trimesh`, `manifold3d`). Every 2D sprite, seamless tile, watertight 3D mesh, VFX flipbook, and SFX audio file in this repository is built from a deterministic, seeded Python script—no Blender, DAW, external renderer, or hosted API.

## Setup

Requires Python 3.12+.

```sh
python3 -m venv .venv-code-assets
.venv-code-assets/bin/python -m pip install -r requirements-code-assets.txt
```

Run the test suite:

```sh
.venv-code-assets/bin/python -m unittest discover -s tests -v
```

## Web Gallery

The browser catalog in `index.html` loads [`gallery/catalog.json`](gallery/catalog.json) (12 seed-7 baseline assets) and [`gallery/expansion/catalog.json`](gallery/expansion/catalog.json) (18 expansion studies, including side-by-side V1 vs. V2 Knowledge Vault comparisons).

```sh
python3 -m http.server 8000
# open http://localhost:8000
```

`index.html` is compiled from [`src/styles.css`](src/styles.css), [`src/body.html`](src/body.html), and [`src/app.js`](src/app.js). After editing files in `src/`, rebuild `index.html`:

```sh
.venv-code-assets/bin/python build_html.py
```

## CLI (`asset_pipeline`)

All asset scaffolding, structural/perceptual validation, recipe auditing, and V1-vs-V2 metric comparisons run through `asset_pipeline`:

```sh
# 1. Scaffold a new asset from templates/ (2d_icon, 2d_tile, 3d_prop, vfx_flipbook, sfx_sound)
.venv-code-assets/bin/python -m asset_pipeline new 3d_prop path/to/my_prop

# 2. Run the generator script to export the asset, preview, and manifest.json
.venv-code-assets/bin/python path/to/my_prop/generate.py --seed 7

# 3. Validate a specific output file (PNG, GLB, OBJ, WAV)
.venv-code-assets/bin/python -m asset_pipeline validate path/to/my_prop/model.glb

# 4. Audit a recipe for unused pipeline imports, missing vault refs, or stale hashes
.venv-code-assets/bin/python -m asset_pipeline audit path/to/my_prop

# 5. Compare two asset versions with measured geometry/image/audio metrics
.venv-code-assets/bin/python -m asset_pipeline compare gallery/expansion/assets/mana-obelisk gallery/expansion/assets/mana-obelisk-v2
```

### Example Recipe

```python
from pathlib import Path
from asset_pipeline import AssetValidator, Manifest, MeshBuilder, SolidMesh, bake_ground_ao

ASSET_NAME = "pillar"

def build(seed: int = 7) -> SolidMesh:
    builder = MeshBuilder(seed=seed)
    builder.lathe(
        [[0.0, 0.0], [0.45, 0.0], [0.40, 0.25], [0.0, 0.25]],
        sections=8,
        color=[65, 70, 80, 255],
        subdivide=3,
    )
    builder.pyramid(base_radius=0.30, height=1.10, sections=6, offset=[0, 0, 0.25], color=[100, 200, 255, 255])
    mesh = builder.build()
    bake_ground_ao(mesh, height=0.45, strength=0.45)
    mesh.ensure_watertight()
    return mesh

def main(out: Path = Path(".")):
    mesh = build(seed=7)
    glb = out / f"{ASSET_NAME}.glb"
    mesh.export_glb(glb, apply_y_up=True)
    mesh.export_obj(out / f"{ASSET_NAME}.obj")
    mesh.render_preview(out / "preview.png")

    AssetValidator.validate_mesh(glb, max_triangles=3000, watertight=True)
    AssetValidator.validate_mesh_shading(mesh, max_ground_ratio=0.85)

    manifest = Manifest(asset=glb.name, parameters={"seed": 7}, recipe="generate.py")
    manifest.declare_vault("techniques/art_styles/bevels_and_edge_weight.md", "lathe")
    manifest.declare_vault("techniques/art_styles/vertex_color_gradient_baking.md", "bake_ground_ao")
    manifest.scan_directory(out, only=[ASSET_NAME]).save(out)
```

## Knowledge Vault & Agent Skills

- **[`vault/`](vault/README.md)**: Atomic reference notes covering acoustic modal ratios, Haas stereo panning, SDF bevels, Schlick Fresnel glass rims, running-bond stone masonry, buoyant smoke plumes, spherical foliage normals, and known procedural failure modes.
- **[`skills/`](skills/)**: Agent skill definitions (`create-game-assets`, `create-2d-assets`, `create-3d-assets`, `create-vfx`, `create-sfx`), symlinked across `.agent/`, `.agents/`, `.claude/`, `.cursor/`, and `.qoder/`.
- **[`skills/create-game-assets/references/libraries.md`](skills/create-game-assets/references/libraries.md)**: Pinned dependency versions, licenses, and upstream source map.

## Repository Layout

```
├── asset_pipeline/             # Core Python SDK, CLI, validators, recipe auditor, and gallery builders
├── vault/                      # Math formulations, acoustic ratios, material recipes, and failure modes
├── skills/                     # Canonical agent skills (symlinked to .agent, .agents, .claude, .cursor, .qoder)
├── templates/                  # Starter templates used by `python -m asset_pipeline new`
├── gallery/                    # Pre-rendered catalogs, asset folders, manifests, and reproducible ZIPs
│   ├── assets/                 # Original 12 seed-7 baseline assets (and symlink to expansion/)
│   └── expansion/              # 8 seed-19 studies + 10 V1 vs. V2 Knowledge Vault comparison assets
├── src/                        # Modular frontend sources (styles.css, body.html, app.js)
├── build_html.py               # Compiles src/* into index.html
├── index.html                  # Self-contained gallery browser
├── tests/                      # Unit, recipe audit, vault integrity, and Playwright browser tests
├── AGENTS.md                   # Harness instructions and commit conventions
├── CONTRIBUTING.md             # Conventional Commits specification and git hook setup
└── NOTES.md                    # Measured V1 vs. V2 comparisons and engineering notes
```
