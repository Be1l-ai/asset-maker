# Silhouette, Readability, and Proportions

Principles from stylized game art (*Overwatch*, *Genshin Impact*, *Zelda: Breath of the Wild*) for readable 3D props and 2D icons.

---

## 1. The 70/30 Rule of Detail Distribution

Human visual perception tires quickly when bombarded with uniform high-frequency noise. In stylized art:
- **70% Rest Areas**: Broad, clean, smooth planes and uninterrupted silhouettes that give the eye a place to rest.
- **30% Concentrated Detail**: High-contrast, sharply defined focal regions (carved runes, gilded collars, potion bubbles, eye catch-lights).

Never scatter micro-scratches or random noise across an entire surface. Keep 70% of the surface clean and focus detail strictly around functional or visual anchors.

---

## 2. The Solid Silhouette Test

If an asset is filled with pure solid black against a pure white background:
1. **Can you identify the object in under 200 ms?**
   - A potion bottle must clearly show cork, neck, shoulder, and base.
   - An obelisk must show stepped plinth, tapered shaft, and apex.
2. **Negative Space**:
   - Ensure critical elements (handles, shards, limbs, horns) have clean air gaps separating them from the main body.
   - Avoid tangential intersections where separate parts visually merge into a confusing clump.

---

## 3. Multi-Resolution Thumbnail Verification

Assets must retain semantic clarity across multiple scale tiers:
- **32×32 px**: Small inventory icon or distant screen footprint. Only primary silhouette and dominant color block survive.
- **64×64 px**: Medium UI slot. Secondary details (gold collars, bevel highlights) become legible.
- **256×256 px**: High-res inspection modal. Surface grain, bubble highlights, and rim strokes appear.

If an asset looks like an unrecognizable blur at 32px, simplify the primary shape before adding micro-details.
