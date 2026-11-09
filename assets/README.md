# Assets Directory

This directory is where new game assets are created and organized.

## How to Create a New Asset

As an agent or developer, creating a new asset is a simple 3-step workflow:

### Option A: Using the Scaffolding CLI (Fastest)

Run `python -m asset_pipeline new <template> assets/<asset_name>`:

```sh
# For a 3D model:
.venv-code-assets/bin/python -m asset_pipeline new 3d_prop assets/wooden_chest

# For a 2D icon:
.venv-code-assets/bin/python -m asset_pipeline new 2d_icon assets/magic_potion

# For a seamless tile:
.venv-code-assets/bin/python -m asset_pipeline new 2d_tile assets/stone_cobble

# For an animated VFX flipbook:
.venv-code-assets/bin/python -m asset_pipeline new vfx_flipbook assets/fire_spark

# For a sound effect:
.venv-code-assets/bin/python -m asset_pipeline new sfx_sound assets/sword_clash
```

### Option B: Copying Template Manually

1. Choose a template folder from [`templates/`](../templates):
   - `templates/2d_icon/`: Vector-like raster icons and badges
   - `templates/2d_tile/`: Seamless repeating ground/wall textures
   - `templates/3d_prop/`: Watertight 3D solids (GLB/OBJ)
   - `templates/vfx_flipbook/`: Looping animated sprite sheets
   - `templates/sfx_sound/`: Synthesized audio WAVs
2. Copy the template folder into `assets/<your_asset_name>/`:
   ```sh
   cp -r templates/3d_prop assets/my_asset
   ```
3. Open `assets/my_asset/generate.py` and customize the generator function (`build`, `draw`, `render_frame`, or `synthesize`).
4. Run the script:
   ```sh
   cd assets/my_asset && python generate.py
   ```
   The asset, preview, and verified manifest will be created in that folder automatically.

## Python API

All procedural asset generators can import the unified `asset_pipeline` library:

```python
from asset_pipeline import sfx, vfx, mesh3d, sprite2d, validator, manifest
```
