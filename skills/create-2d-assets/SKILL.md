---
name: create-2d-assets
description: Deep procedural 2D rendering skill. Draw crisp vector-style raster icons, game sprites, and seamless repeating texture tiles using Pillow, aggdraw, and NumPy without drawing tools.
---

# Procedural 2D Asset Rendering

Author production-quality raster icons, UI badges, and seamless tiles using `Pillow`, `aggdraw`, and `numpy`.

## Architectural Guidelines

### 1. Antialiasing via Super-Sampling
- Never draw directly at low resolution when authoring smooth shapes. Draw onto a canvas at $2\times$ or $4\times$ target scale (`SpriteCanvas(size, super_sample=2)`).
- Use `aggdraw.Path` with Bezier curves (`curveto`) for organic shapes, shield arches, potion flasks, and weapon blades.
- Use `PIL.ImageDraw` for crisp geometric primitives, ellipses, and interior emblem markings.

### 2. Downsampling & Premultiplied Alpha
- **The Halo Problem**: Standard bilinear/bicubic resampling on straight RGBA causes dark or grey fringing around transparent edges due to unweighted RGB interpolation.
- **Premultiplied Downsampling**: Always convert canvas to premultiplied alpha (`image.convert("RGBa")`), resize with `Image.Resampling.LANCZOS`, and convert back to straight `RGBA`.
- **1-Pixel Gutter**: Lanczos sinc ringing can deposit faint non-zero alpha along the image outer boundary. Always clear a 1-pixel border rectangle (`outline=(0, 0, 0, 0)`) to maintain clean transparent bounding boxes.

### 3. Seamless Repeating Tiles
- **Toroidal Math**: For seamless ground/wall textures, map pixel coordinates $(x, y) \in [0, 1)^2$ to periodic angles $\theta = 2\pi x$ and $\phi = 2\pi y$.
- Evaluate basis harmonic functions $f(\theta, \phi) = \sum a_k \sin(k\theta + \alpha_k) \cos(k\phi + \beta_k)$. Boundary values at $x=0$ and $x=1$ (and $y=0$ and $y=1$) are guaranteed to match identically with zero derivative discontinuity.
- Inspect every seamless tile with a $3 \times 3$ tiled contact preview (`create_tiled_preview`).

### 4. Knowledge Vault References
- **Cellular & Stone Noise**: See [`vault/mathematics/noise_and_fields/worley_cellular_noise.md`](../../vault/mathematics/noise_and_fields/worley_cellular_noise.md) (use `worley_noise()`).
- **Normal Map Derivation**: See [`vault/mathematics/materials/height_to_normal_sobel.md`](../../vault/mathematics/materials/height_to_normal_sobel.md) (use `heightmap_to_normal_map()`).
- **Procedural Fabrics & Wood**: See [`vault/techniques/materials/fabric_and_weave_patterns.md`](../../vault/techniques/materials/fabric_and_weave_patterns.md) and [`vault/techniques/materials/wood_grain_growth_rings.md`](../../vault/techniques/materials/wood_grain_growth_rings.md).


## Code Example: `SpriteCanvas`

```python
import aggdraw
from asset_pipeline import SpriteCanvas, sprite2d

def draw_shield_badge(size: int = 256, seed: int = 7) -> SpriteCanvas:
    canvas = SpriteCanvas(size=size, super_sample=2)
    scale = canvas.scale

    path = aggdraw.Path()
    path.moveto(0.50 * scale, 0.15 * scale)
    path.lineto(0.80 * scale, 0.25 * scale)
    path.curveto(0.80 * scale, 0.65 * scale, 0.55 * scale, 0.85 * scale, 0.50 * scale, 0.90 * scale)
    path.curveto(0.45 * scale, 0.85 * scale, 0.20 * scale, 0.65 * scale, 0.20 * scale, 0.25 * scale)
    path.close()

    fill = sprite2d.hsv_to_rgb(210.0, 0.70, 0.50) + (240,)
    canvas.draw_path(path, brush_color=fill, pen_color=(220, 235, 255, 255), pen_width=scale * 0.025)
    return canvas
```

## Scaffolding & Generation

```sh
# For an icon or UI badge:
.venv-code-assets/bin/python -m asset_pipeline new 2d_icon assets/<asset_name>

# For a seamless repeating texture tile:
.venv-code-assets/bin/python -m asset_pipeline new 2d_tile assets/<asset_name>

# Execute generator and produce PNG and dual dark/light preview.png:
cd assets/<asset_name> && python generate.py
```

## Validation & Quality Checklist

1. **Alpha Channel**: Confirm alpha presence and 0% transparent background with `AssetValidator.validate_png(path, require_alpha=True)`.
2. **Contrast & Edge Fidelity**: Inspect `preview.png` on both pure dark `(20, 24, 36)` and light `(235, 237, 242)` backgrounds.
3. **Seamlessness**: For tiles, inspect the 3×3 grid preview to ensure zero visible seams or tiling repetition artifacts.

## Verification Loop (Required)

Structural validation proves a file is well-formed, not that it is good. Before declaring any asset done:

1. **Look.** Open `preview.png` (3D: three views; tile: albedo + normal-lit; VFX: contact sheet). Name one concrete defect, fix it, re-render. Read [`vault/pitfalls/procedural_failure_modes.md`](../../vault/pitfalls/procedural_failure_modes.md).
2. **Declare the vault.** For every vault doc you applied, call `manifest.declare_vault("<path under vault/>", "<pipeline symbol you call>")`. Never import a technique you do not call.
3. **Audit.** `.venv-code-assets/bin/python -m asset_pipeline audit assets/<name>` must pass (no unused pipeline imports, real vault docs, symbols actually used, no stale hashes).
4. **Domain acceptance:** `AssetValidator.validate_silhouette(png, max_components=1)` for icons; `validate_seamless(png)` (and the normal map) for tiles. Build shapes as masks and composite with `over`; never draw transparent fills to erase.
5. **Hash only your files:** `manifest.scan_directory(out, only=[ASSET_NAME])`.
6. **Compare to the baseline with numbers** if this replaces an earlier version: `python -m asset_pipeline compare <old> <new>`. Do not state numbers in a README that are not in the manifest.
