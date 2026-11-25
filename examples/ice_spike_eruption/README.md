# Ice Spike Eruption

A one-shot 4×4 VFX flipbook of crystalline ice shards erupting along a frozen
fracture line. The effect is fully procedural: no hand-authored frames, no
external images, and no per-frame randomness.

## Reproduce

```sh
../../.venv-code-assets/bin/python generate.py
```

Artifacts:

- `ice_spike_eruption.png` — 1024×1024 RGBA atlas (16 × 256 px cells).
- `preview.gif` — 16 fps animated preview on a dark background.
- `preview.png` — contact sheet on dark and light backgrounds.
- `critique_blockout.png`, `critique_secondary.png`, `critique_final.png` — Tier-1 critique stages.
- `manifest.json` — parameters, checksums, and vault provenance.
- `critique_log.json` — three inner rounds plus the Tier-2 VFX detail pass.

## Design Notes

- **Ground first**: an ignition flash and jagged fracture seams appear before the shards.
- **Staggered eruption**: every shard has a pre-rolled delay, width profile, lean, and depth.
- **Faceted ice**: each shard is split along a central ridge into shadow/lit planes with a white rim and cyan root glow.
- **Depth**: a darker, slightly blurred back row sits behind the hero cluster.
- **Dissipation**: mist, contact frost, and pre-rolled ice chips fade out; the last sampled frame is nearly transparent.

Vault references:

- [`vault/techniques/hybrid_vfx/crystalline_ice_spike_eruptions.md`](../../vault/techniques/hybrid_vfx/crystalline_ice_spike_eruptions.md)
- [`vault/techniques/hybrid_vfx/four_stage_emitter_architecture.md`](../../vault/techniques/hybrid_vfx/four_stage_emitter_architecture.md)
