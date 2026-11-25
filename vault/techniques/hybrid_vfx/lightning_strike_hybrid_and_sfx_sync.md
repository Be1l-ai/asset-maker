# Hybrid Lightning Strike VFX (3D Mesh + Flipbook + Synced SFX)

High-impact real-time spell VFX combine a **3D silhouette mesh**, a **2D additive flipbook sprite sheet**, and **frame-locked layered DSP audio** driven by a single shared timeline (`timeline.json`).

## 1. Shared 4-Stage Master Timeline (1.20 s / 16 Frames @ 75 ms/frame)
* **Stage 1 — Anticipation (`0.00–0.15 s`, Frames 0–1)**: Thin jagged leader bolt descending + static ground spark ring. Audio: rising 60 Hz electric hum + sparse high-voltage crackle.
* **Stage 2 — Peak Impact (`0.15–0.375 s`, Frames 2–4)**: Full-width blinding white-cyan main bolt + twin concentric ground shockwave rings + erupting upward plasma shards & rock debris. Audio: razor-sharp bandpass whip-crack transient at `t = 0.150 s` + sub-bass impact thump (`45–95 Hz`).
* **Stage 3 — Re-Strike & Sparks (`0.375–0.75 s`, Frames 5–9)**: Flickering violet-blue forked re-strike filaments + radial flying sparks. Audio: multi-tap progressively low-passed rolling thunder echoes + high-frequency electric sizzle.
* **Stage 4 — Embers & Ionized Smoke (`0.75–1.20 s`, Frames 10–15)**: Scorched amber-cyan glowing ground fissures + curling translucent smoke wisps dissolving cleanly to alpha 0. Audio: exponential thunder tail decay + soft crackling ember fade, high-passed above `30 Hz` and normalized to `-1.0 dBFS`.

## 2. Optimization Split (3D vs. Flipbook)
* **3D GLB Mesh (`lightning_strike_3d.glb`)**: Holds the volumetric silhouette — jagged branching bolt tubes (`catmull_rom_tube`), beveled upward energy shards (`extrude_beveled_2d`), concentric shockwave rings, and a scorched cracked-stone ground disc with baked tangent-space normal map (`asset_pipeline.baking.height_to_normal_map`).
* **4×4 Flipbook Atlas (`1024×1024` RGBA)**: Carries high-frequency flickering arcs, additive glow halos, flying sparks, and ionized smoke wisps that would cost tens of thousands of triangles in pure geometry.
