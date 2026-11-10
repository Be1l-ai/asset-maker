# The Four-Stage Emitter Stack Architecture

The industry-standard composite layer structure for production-quality explosive and magical effects.

---

## 1. The Four Chronological Layers

A convincing explosion, magic burst, or physical impact is never a single monolithic particle emitter. It is composed of four distinct layers firing with precise relative timing:

```
Time:   0.00s ---------------- 0.15s ---------------- 0.40s ---------------- 1.00s
Layer 1: [ Flash / Glow ]
Layer 2:        [ Core Blast / Expanding Shockwave ]
Layer 3:                 [ Volumetric Flipbook Plume / Billow ]
Layer 4:                                [ Lingering Sparks / Smoke Drift ]
```

### Stage 1: The Ignition Flash (Anticipation)
- **Duration**: 1 to 2 frames ($0.05\text{--}0.10\text{ s}$).
- **Visual**: Blinding white-hot central starburst or expanding lens glow.
- **Role**: Sells the instantaneous release of kinetic/magical energy.

### Stage 2: The Core Blast & Shockwave Ring
- **Duration**: $0.10\text{--}0.35\text{ s}$.
- **Visual**: Fast-expanding circular shockwave ring (billboard quad or mesh disc) tearing outward.
- **Dynamics**: Highly non-linear explosive deceleration (`Easing.ease_out`).

### Stage 3: The Main Volumetric Plume
- **Duration**: $0.25\text{--}0.70\text{ s}$.
- **Visual**: The primary flipbook sprite atlas (e.g. 16 frames of turbulent smoke billows or arcane flame).
- **Role**: Carries the bulk of the art-directed silhouette and character identity.

### Stage 4: Lingering Dissipation & Sparks
- **Duration**: $0.50\text{--}1.20\text{ s}$.
- **Visual**: Tiny tumbling embers, spark trails, and thin dissipating smoke clouds drifting upward.
- **Extinction**: Hard alpha cutoff or cellular dissolve rather than fading to muddy grey.

---

## 2. Using `EmitterStack` in `asset_pipeline`

```python
from PIL import Image
from asset_pipeline import EmitterStack

stack = EmitterStack(size=128)

# Layer 1: Central Flash (only active in early phase)
def flash_layer(phase: float, size: int):
    if phase < 0.2:
        return Image.new("RGBA", (size, size), (255, 255, 255, int(255 * (1.0 - phase / 0.2))))
    return None

# Layer 2: Shockwave Ring
def ring_layer(phase: float, size: int):
    return Image.new("RGBA", (size, size), (100, 200, 255, 50))

# Layer 3: Particles
def sparks_layer(phase: float, size: int):
    return Image.new("RGBA", (size, size), (255, 200, 50, 40))

stack.add_layer(flash_layer).add_layer(ring_layer).add_layer(sparks_layer)

# Generate composite frame at phase 0.35
frame_img = stack.composite_frame(phase=0.35)
```
