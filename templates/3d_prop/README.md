# 3D Prop Template

Template for procedural watertight, low-poly 3D models with vertex/face colors.

## Quick Start

1. Edit `build(seed)` in `generate.py` to construct solid parts and booleans using `asset_pipeline.mesh3d`.
2. Run generation:
   ```sh
   python generate.py [--seed 7]
   ```
3. Artifacts generated:
   - `<asset_name>.glb`: Colored glTF binary with engine-standard Y-up coordinate conversion.
   - `<asset_name>.obj`: Standard portable geometry export.
   - `preview.png`: Headless software-rendered isometric preview.
   - `manifest.json`: Triangle counts, bounds, parameters, and checksums.
