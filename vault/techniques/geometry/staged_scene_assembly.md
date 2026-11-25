# Staged 3D Scene Assembly (`PARSE -> MASS -> RIG -> SKIN -> PACK`)

How to construct multi-part 3D props and full biome scenes that remain editable, animatable, and material-aware after glTF 2.0 export.

---

## 1. Why Flat Concatenation Breaks Down on Complex Assets

Flattening all sub-meshes into a single `Trimesh` (`MeshBuilder.build()`) works for static single-material props, but fails as soon as a human or game engine needs to:
- **Edit or toggle one part** (e.g., hide `Skydome` to use an engine's native sky, or move a single tree).
- **Animate around a real pivot** (e.g., rotate a lantern door, sway a tree crown, or hop a bunny).
- **Assign distinct PBR roughness/emissive properties** (e.g., matte bark at `roughness=0.94`, glowing crystal or sun with `emissiveFactor`).

---

## 2. The Five-Stage Construction Contract

1. **PARSE (`spec.json`)**: Declare real-world dimensions, part names, material keys, pivots, and per-part triangle budgets *before* generating geometry (`SceneSpec.from_file`).
2. **MASS**: Build clean, watertight geometry per named part using modular generators.
3. **RIG**: Store each part's local vertices relative to its physical `pivot` and write the offset into the glTF node's `translation`.
4. **SKIN**: Assign explicit `MaterialSpec` PBR slots (`roughness`, `metallic`, `emissive`) per part.
5. **PACK**: Export a multi-node `.glb` (Y-up) and grouped `.obj` (Z-up), then inspect with the shadow-mapped Z-buffer previewer (`SceneBuilder.render_preview`) and audit via `python -m asset_pipeline audit`.

---

## 3. Python Usage in `asset_pipeline`

```python
from asset_pipeline import SceneBuilder, MaterialSpec

scene = SceneBuilder.from_spec("spec.json", seed=7)
scene.add_part("Terrain_Meadow", terrain_geom, material="matte", cast_shadow=False)
scene.add_part("Hero_Pine", pine_geom, material="foliage", pivot=[0.0, 0.0, 0.0])
scene.validate()
scene.export_glb("scene.glb", apply_y_up=True)
scene.render_preview("preview.png")
```
