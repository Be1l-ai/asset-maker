---
name: create-2d-assets
description: Deep procedural 2D rendering skill. Draw crisp vector-style raster icons, game sprites, and seamless repeating texture tiles using Pillow, aggdraw, and NumPy without drawing tools.
---

# Procedural 2D Asset Rendering

Author production-quality raster icons, UI badges, and seamless tiles using `Pillow`, `aggdraw`, and `numpy`. Follow [`create-game-assets`](../create-game-assets/SKILL.md) for the master verification loop.

## Architectural Guidelines

### 1. Antialiasing & Mask-First Compositing
- Draw onto a supersampled canvas at $2\times$ or $4\times$ target scale (`SpriteCanvas(size, super_sample=2)`).
- Build icon silhouettes and interior regions as float masks (`ellipse_mask`, `polygon_mask`, `ring_mask`, `fillet_mask`), shade via `inside_depth` and `lerp_color`, and composite with Porter-Duff `over`. Never draw alpha=0 shapes to erase.

### 2. Downsampling & Premultiplied Alpha
- **Premultiplied Downsampling**: Always convert to `"RGBa"`, resize with `Image.Resampling.LANCZOS`, and convert back to straight `"RGBA"` (`SpriteCanvas.finalize()` handles this automatically).
- **1-Pixel Gutter**: Clear a 1-pixel transparent outer border (`outline=(0, 0, 0, 0)`) to prevent Lanczos edge ringing.

### 3. Seamless Repeating Tiles
- Use toroidal angular coordinates $\theta = 2\pi x, \phi = 2\pi y$ (`SeamlessTile.generate_toroidal_grid`) and periodic cellular noise (`worley_noise(..., periodic=True)`) so opposite edges wrap with zero derivative discontinuity.
- Derive tileable normal maps via `heightmap_to_normal_map(height, strength=..., tileable=True)`.

### 4. Knowledge Vault References
- **Silhouette & 70/30 Proportions**: [`vault/techniques/art_styles/silhouette_and_proportions.md`](../../vault/techniques/art_styles/silhouette_and_proportions.md) & [`vault/techniques/art_styles/color_ramps_and_cel_steps.md`](../../vault/techniques/art_styles/color_ramps_and_cel_steps.md).
- **Glass Vessels & Refracted Liquids**: [`vault/techniques/materials/glass_and_liquid_vessels.md`](../../vault/techniques/materials/glass_and_liquid_vessels.md) (`inside_depth`, `fillet_mask`, `lerp_color`, `over`).
- **Chiseled Stone & Running-Bond Masonry**: [`vault/techniques/materials/chiseled_stone_and_masonry.md`](../../vault/techniques/materials/chiseled_stone_and_masonry.md) & [`vault/mathematics/noise_and_fields/worley_cellular_noise.md`](../../vault/mathematics/noise_and_fields/worley_cellular_noise.md).
- **Toroidal Harmonics & Normal Maps**: [`vault/mathematics/noise_and_fields/toroidal_periodic_harmonics.md`](../../vault/mathematics/noise_and_fields/toroidal_periodic_harmonics.md) & [`vault/mathematics/materials/height_to_normal_sobel.md`](../../vault/mathematics/materials/height_to_normal_sobel.md).
- **Fabrics, Wood & Beziers**: [`vault/techniques/materials/fabric_and_weave_patterns.md`](../../vault/techniques/materials/fabric_and_weave_patterns.md), [`vault/techniques/materials/wood_grain_growth_rings.md`](../../vault/techniques/materials/wood_grain_growth_rings.md), [`vault/mathematics/geometry/beziers_and_splines.md`](../../vault/mathematics/geometry/beziers_and_splines.md).

## Code Example: Mask-First Icon Rendering

```python
import numpy as np
from asset_pipeline import SpriteCanvas, ellipse_mask, fillet_mask, inside_depth, lerp_color, new_layer, over, polygon_mask

def draw_flask_icon(size: int = 256) -> SpriteCanvas:
    canvas = SpriteCanvas(size=size, super_sample=2)
    s = canvas.scale
    shape = (s, s)
    bulb = ellipse_mask(shape, 0.50 * s, 0.62 * s, 0.26 * s, 0.25 * s)
    neck = polygon_mask(shape, [(0.42 * s, 0.24 * s), (0.58 * s, 0.24 * s), (0.60 * s, 0.42 * s), (0.40 * s, 0.42 * s)])
    glass = fillet_mask(bulb | neck, radius=0.03 * s)

    depth = inside_depth(glass)
    layer = new_layer(shape)
    over(layer, lerp_color((80, 12, 30), (245, 75, 95), np.clip(depth / (0.18 * s), 0, 1)), glass)
    canvas.paste_layer(layer)
    return canvas
```

## Domain Acceptance Checks

1. **Icons**: `AssetValidator.validate_png(path, require_alpha=True)` and `AssetValidator.validate_silhouette(path, max_components=1)` (single unified silhouette, clean dark/light `preview.png`).
2. **Seamless Tiles**: `AssetValidator.validate_seamless(albedo_path)` and `AssetValidator.validate_seamless(normal_path)` (zero boundary jump on the $3 \times 3$ contact sheet and Lambertian normal preview).
