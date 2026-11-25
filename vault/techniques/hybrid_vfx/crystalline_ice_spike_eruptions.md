# Crystalline Ice-Spike Eruptions (2D VFX)

A cold, faceted eruption built from staggered crystal shards, fracture light, and low-lying frost mist. This is the 2D flipbook counterpart to the hybrid mesh/particle explosions in [`mesh_particle_explosions.md`](mesh_particle_explosions.md).

---

## 1. Silhouette Before Sparkle

Build each shard as a **tapered, asymmetric splinter**, not a symmetric triangle:

- Ground width $w_0$ tapers as $w(v) = w_0 (1-v)^{0.72}$ toward the tip.
- Add fixed per-spike wobble to the left and right edges so the cluster never reads as a picket fence.
- Lean the apex by `lean * height`; a single shared lean vector across the row makes the eruption feel wind-driven.
- Draw a back row smaller, darker, and higher on screen before the hero row. This creates thickness without volumetric simulation.

## 2. Faceted Ice Shading

Split every shard along a central ridge into two planes:

1. **Shadow plane** — multiply the base ramp by $\approx 0.66$ and add a low-frequency sinusoidal striation.
2. **Lit plane** — keep near-white cyan and add a slightly different striation phase.

The shared vertical ramp runs from saturated cyan at the root to near-white at the tip. A thin white ridge line plus a cyan silhouette outline sells the crystal edge at small atlas sizes. Back-row crystals blend toward a dark blue haze to fake aerial perspective.

## 3. Timing: Ground First, Crystal Second

| Phase | Event |
|---|---|
| $0.00$–$0.10$ | Ignition flash and fracture lines appear on the ground plane |
| $0.05$–$0.45$ | Shards erupt in a staggered diagonal wave, each with its own delay |
| $0.45$–$0.75$ | Aura peaks; mist spreads and glitter decelerates |
| $0.80$–$1.00$ | Global alpha extinguishes cleanly for a one-shot atlas |

Growth uses `Easing.ease_out`; the tip arrives fast, then holds. Never re-randomize per frame — pre-roll spike delays, edge wobble, crack paths, mist puffs, and glitter velocities.

## 4. Layer Order with `EmitterStack`

```python
from asset_pipeline import EmitterStack

stack = EmitterStack(size=512)
stack.add_layer(ambient_glow)   # ground bloom + vertical aura + ignition flash
stack.add_layer(back_and_hero_spikes)
stack.add_layer(ground_cracks)  # sharp fracture core over blurred halo
stack.add_layer(frost_mist)
stack.add_layer(ice_glitter)
frame = stack.composite_frame(phase)
```

Render at 2× and downsample with **premultiplied alpha** to avoid dark fringes around translucent ice. Keep the atlas power-of-two (for example 4×4 cells at 256 px = 1024×1024).

## 5. Acceptance Checks

- Every shard emerges from the same ground line and has a visible contact shadow/frost patch.
- At least three value tiers: deep blue shadow plane, cyan body, white rim/ridge.
- Final frame extinguishes; no crystal pops between adjacent frames.
- Atlas alpha bounds stay tight and the effect remains readable at 64 px.
