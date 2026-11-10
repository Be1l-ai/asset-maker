# Stylized Dissolve and Alpha Erosion

Techniques for dissolving effects, fire plumes, and magic shields using noise thresholds and glowing erosion borders.

---

## 1. Why Standard Alpha Blending Looks Weak

Simply scaling particle alpha linearly ($\alpha(t) = 1 - t$):
- Causes effects to turn into semi-transparent, ghost-like muddy fog before disappearing.
- In anime and stylized games, fire and smoke do not fade into transparency; they **break apart into chunks and dissolve** along crisp cellular borders.

---

## 2. Mathematical Erosion Algorithm

Given an input texture $I(x, y)$ and a grayscale dissolve noise map $N(x, y) \in [0, 1]$:

For a dissolve progress parameter $\tau \in [0, 1]$:
1. **Alpha Cutoff (Binary Clip)**:
   $$\alpha_{\text{final}}(x, y) = \begin{cases} 0 & \text{if } N(x, y) < \tau \\ \alpha_{\text{orig}}(x, y) & \text{if } N(x, y) \ge \tau \end{cases}$$
2. **Glowing Burning Edge (Band Detection)**:
   For an edge band thickness $w \in [0.03, 0.08]$:
   $$\text{is\_edge}(x, y) = (\tau \le N(x, y) < \tau + w)$$
   Edge pixels are tinted with an intense emissive burn color (e.g. `[255, 180, 40]` gold-yellow or `[120, 240, 255]` arcane cyan).

---

## 3. Python Usage in `asset_pipeline`

```python
from asset_pipeline import dissolve_alpha_mask, worley_noise

# Generate a cellular noise map for organic chunky dissolve
noise = worley_noise(width=128, height=128, grid_x=8, grid_y=8, seed=42)

# Apply dissolve at 60% progress with an intense burning gold edge
dissolved_frame = dissolve_alpha_mask(
    image=source_frame,
    threshold=0.60,
    noise_map=noise,
    edge_width=0.06,
    edge_color=(255, 200, 50)
)
```
