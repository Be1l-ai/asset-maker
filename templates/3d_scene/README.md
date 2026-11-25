# 3D Scene Template (`PARSE -> MASS -> RIG -> SKIN -> PACK`)

Starter template for multi-part 3D environments and rigged/articulated props using `SceneBuilder` and `spec.json`.

## Workflow

1. Edit `spec.json` first to declare parts, real-world dimensions, pivots, PBR materials, and per-part triangle budgets.
2. Implement modular part generators in `generate.py` and register them with `scene.add_part(...)`.
3. Run `python generate.py --seed 7` to export `<name>.glb` (Y-up, named nodes, PBR materials), `<name>.obj` (Z-up, named groups), `preview.png` (shadow-mapped Z-buffer render), and `manifest.json`.
4. Run `python -m asset_pipeline audit <folder>` to verify `spec.json`, `vault_refs`, and artifact hashes.
