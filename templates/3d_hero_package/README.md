# 3D Hero Asset Package (`Asset-as-a-Package`)

Multi-module starter template for production 3D props, characters, vehicles, and environments.

- `spec.json` — PARSE contract (dimensions, parts, pivots, PBR materials, per-part triangle budgets)
- `geometry_math.py` — Reusable math, lofting, and watertight primitives
- `textures.py` & `materials.py` — Procedural albedo/normal/roughness maps embedded directly in `.glb`
- `parts/` — One focused geometry builder per structural subsystem
- `rig.py` — Named node pivots and joint origins
- `generate.py` — Master assembler exporting `.glb`, `.obj`, `inspector.json`, `preview.png`, and `manifest.json`
- `test_asset.py` — Per-asset unit tests
