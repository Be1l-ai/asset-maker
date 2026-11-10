# Leaf Cards, Alpha Branching, and Overdraw Optimization

How to construct efficient low-poly leaf clusters, fern fronds, and foliage cards without GPU fill-rate overdraw penalties.

---

## 1. The Quad Overdraw Trap

A naive leaf card uses a simple 4-vertex rectangle $(1 \times 1)$ where the leaf sprite occupies only a small diagonal strip in the center, leaving $60\text{--}80\%$ of the quad as transparent pixels ($\alpha = 0$).

When dozens of these transparent quads overlap in a tree canopy:
- The GPU pixel shader evaluates transparent discard operations repeatedly for every overlapping pixel (catastrophic overdraw).
- In mobile or low-end rendering, frame rates plunge.

---

## 2. Tight Silhouette Trimming and Curved Quads

1. **Tight Polygon Hulls**:
   - Use a 5-point or 6-point polygon that tightly hugs the contour of the leaf cluster, eliminating large empty transparent corners.
2. **Organic Curve (Segmented Card)**:
   - Introduce a single longitudinal division down the middle of the card and displace the center ridge along $Y$:
     ```
     v0 ---- v2 ---- v4 (tip)
      \      /      /
       \    /      /
     v1 ---- v3 ---- v5
     ```
   - Center vertices `v2` and `v3` are curved outward by $0.1\text{--}0.2\times$ the card width.
   - Eliminates unnatural razor-flat edges when viewed edge-on.

---

## 3. Python Usage in `asset_pipeline`

```python
from asset_pipeline import create_leaf_card

# Create a low-poly curved alpha leaf card
leaf_card = create_leaf_card(
    width=0.6,
    height=1.2,
    curvature=0.12,
    color=[80, 180, 70, 255]
)
```
