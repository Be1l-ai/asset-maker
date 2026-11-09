# VFX Flipbook Template

Template for procedural animated sprite sheet atlases, energy bursts, and particle effects.

## Quick Start

1. Edit `render_frame(size, phase, seed)` in `generate.py` to create your frame visual at normalized time `0.0 <= phase < 1.0`.
2. Run generation:
   ```sh
   python generate.py [--frames 16] [--size 128] [--fps 16] [--seed 7]
   ```
3. Artifacts generated:
   - `<asset_name>.png`: Packed RGBA flipbook texture atlas.
   - `preview.gif`: Looping preview for immediate playback review.
   - `preview.png`: Frame-by-frame contact sheet.
   - `manifest.json`: FPS, frame count, grid layout, and checksums.
