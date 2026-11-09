# 2D Icon Template

Template for procedural vector-raster icons and badges.

## Quick Start

1. Edit `draw(size, seed)` in `generate.py` to customize the shape, palette, and details.
2. Run generation:
   ```sh
   python generate.py [--size 256] [--seed 7]
   ```
3. Artifacts generated:
   - `<asset_name>.png`: RGBA icon with transparent background.
   - `preview.png`: Side-by-side dark/light preview.
   - `manifest.json`: Checksums, parameters, and environment versions.
