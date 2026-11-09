# 2D Seamless Tile Template

Template for procedural repeating textures, ground tiles, and materials.

## Quick Start

1. Edit `draw_tile(size, seed)` in `generate.py` to create your periodic noise or tile pattern.
2. Run generation:
   ```sh
   python generate.py [--size 256] [--seed 7]
   ```
3. Artifacts generated:
   - `<asset_name>.png`: Seamless RGBA tile.
   - `preview.png`: 3×3 tiled grid to verify invisible boundary seams.
   - `manifest.json`: Verification checksums and parameters.
