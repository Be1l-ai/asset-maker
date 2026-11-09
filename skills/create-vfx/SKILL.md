---
name: create-vfx
description: Deep procedural VFX skill. Generate animated particle fields, energy bursts, magic effects, and transparent looping sprite sheet atlases using Pillow and NumPy.
---

# Procedural VFX Flipbook Generation

Generate animated visual effects and sprite sheet atlases entirely in code using `Pillow` and `numpy`.

## Architectural Guidelines

### 1. Loop Parameterization & Phase Math
- **The $N$-Frame Rule**: For an $N$-frame loop, evaluate normalized phase $t_i = \frac{i}{N}$ for $i = 0, 1, \dots, N-1$. NEVER evaluate $t_i = \frac{i}{N-1}$, which repeats the start frame at the end and causes a visual stutter.
- **Continuous Periodic Fields**: For infinite loops, sample 4D noise or construct periodic basis functions: $\theta(t) = 2\pi t$ with $\cos(\theta)$ and $\sin(\theta)$ harmonics.
- **One-Shot Bursts**: For non-looping one-shot effects (explosions, impacts), map $t \in [0, 1]$ such that the effect is completely extinguished (alpha = 0) at $t = 1.0$.

### 2. Motion Easing & Particle Dynamics
- **Hermite Smoothstep**: Use $S(t) = 3t^2 - 2t^3$ (`Easing.ease_in_out`) for balanced organic expansion and contraction.
- **Explosive Deceleration**: Use $D(t) = 1 - (1 - t)^2$ (`Easing.ease_out`) for fast initial shockwave propagation followed by lingering dissipation.
- **Particle Decay**: Modulate particle opacity by $\alpha(t) = (1 - t)$ and shrink radius $r(t) = r_0 (1 - t)$ as particles travel outward from the emission center.

### 3. Atlas Layout & Packing
- Pack frames in row-major order into a rectangular grid ($C$ columns by $R = \lceil N / C \rceil$ rows), typically $4 \times 4$ for 16 frames.
- Ensure total atlas dimensions are powers of two or divisible by cell dimensions (e.g. 16 frames of $128 \times 128 \to 512 \times 512$ atlas).
- Keep a 1-pixel transparent gutter around cell boundaries to prevent bilinear texture bleed across atlas frames in game engines.

## Code Example: `Flipbook` & `ParticleEmitter`

```python
from asset_pipeline import Easing, Flipbook, ParticleEmitter

def make_burst_flipbook(frames: int = 16, size: int = 128, fps: int = 16, seed: int = 7) -> Flipbook:
    emitter = ParticleEmitter(seed=seed)
    flipbook = Flipbook(fps=fps)
    
    flipbook.generate_frames(
        count=frames,
        frame_generator=lambda phase: emitter.radial_burst(
            size=size,
            phase=phase,
            color_rgb=(100, 200, 255),
        ),
    )
    return flipbook
```

## Scaffolding & Generation

```sh
# Scaffold a new VFX flipbook:
.venv-code-assets/bin/python -m asset_pipeline new vfx_flipbook assets/<asset_name>

# Execute generator and produce atlas PNG, looping preview.gif, and contact preview.png:
cd assets/<asset_name> && python generate.py
```

## Validation & Quality Checklist

1. **Atlas Grid Divisibility**: Confirm atlas width and height divide evenly by columns and rows with `AssetValidator.validate_png(path, require_alpha=True, columns=C, rows=R)`.
2. **Timing & Playback**: Review `preview.gif` at target FPS to verify smooth motion pacing and zero duplicate boundary frames.
3. **Alpha Consistency**: Verify frame boundaries have transparent gutters to avoid cross-frame bleeding.
