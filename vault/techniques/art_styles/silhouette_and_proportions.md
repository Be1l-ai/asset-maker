# Silhouette, Readability, and Proportions

Principles from stylized game art (*Overwatch*, *Genshin Impact*, *Zelda: Breath of the Wild*) for readable 3D props and 2D icons (`assets/health_potion_v2`, `assets/mana_obelisk_v2`).

---

## 1. The 70/30 Rule of Detail Distribution

Human visual perception tires quickly when bombarded with uniform high-frequency noise. In stylized art:
- **70% Rest Areas**: Broad, clean, smooth planes and uninterrupted silhouettes that give the eye a place to rest.
- **30% Concentrated Detail**: High-contrast, sharply defined focal regions (carved runes, gilded collars, potion bubbles, meniscus catch-lights).

Never scatter micro-scratches or random noise across an entire surface. Keep 70% of the surface clean and focus detail strictly around functional or visual anchors.

---

## 2. The Solid Silhouette Test & Connected Components

If an asset is filled with pure solid black ($\alpha > 16 \to 1$) against a white background:
1. **Single Connected Component (`max_components = 1`)**:
   - A 2D icon must form **one unified silhouette** (`AssetValidator.validate_silhouette(path, max_components=1)`). Disjoint floating parts or accidental transparent erasures fail readability.
2. **Instant Sub-200 ms Recognition**:
   - A potion bottle must clearly distinguish cork stopper, lip flange, narrow neck, filleted shoulder, and spherical bulb.
   - An obelisk must distinguish stepped plinth, tapered shaft, and pyramidion apex.
3. **Fill Ratio Bounds**:
   - Target canvas coverage $\text{fill\_ratio} = \frac{\|\alpha > 16\|}{W \times H} \in [0.18, 0.58]$ so the icon neither drowns in empty margin nor crowds the $1\text{ px}$ transparent border gutter.

---

## 3. Multi-Resolution Thumbnail Verification

Assets must retain semantic clarity across scale tiers:
- **32×32 px**: Small inventory icon or distant screen footprint. Only primary silhouette and dominant value contrast survive.
- **64×64 px**: Medium UI slot. Secondary details (gold collars, bevel highlights, liquid fill line) become legible.
- **256×256 px**: High-res inspection modal. Surface grain, subsurface glow, and rim highlights appear.

---

## 4. Constructing Unified 2D Silhouettes in `asset_pipeline`

Build the outer silhouette first by uniting boolean/float masks (`ellipse_mask`, `polygon_mask`, `ring_mask`) and smoothing concavities with `fillet_mask`:

```python
from asset_pipeline import AssetValidator, ellipse_mask, fillet_mask, polygon_mask

S = 256
bulb = ellipse_mask(S, S, cx=128, cy=156, rx=66, ry=64)
neck = polygon_mask(S, S, [(108, 62), (148, 62), (152, 104), (104, 104)])
vessel_silhouette = fillet_mask(bulb | neck, radius=8)

# After exporting the composited icon, enforce single-component silhouette health:
# AssetValidator.validate_silhouette("health_potion_v2.png", max_components=1, min_fill=0.15, max_fill=0.60)
```
