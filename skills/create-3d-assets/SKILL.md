---
name: create-3d-assets
description: Deep procedural 3D modeling skill. Build watertight low-poly props, solids, and modular geometry using Trimesh and Manifold3D booleans, with Y-up coordinate conversion, triangle budgets, and headless multi-view previews.
---

# Procedural 3D Mesh Construction

Build game-ready 3D solids in code using `trimesh` and `manifold3d`. Follow [`create-game-assets`](../create-game-assets/SKILL.md) for the master verification loop.

## Architectural Guidelines

### 1. Watertight Solid CSG & Topology
- **Manifold Booleans**: All input meshes for boolean operations (`union`, `difference`, `intersection`) must be watertight, consistently wound, and have positive volume. Extend cutting solids $0.001\text{--}0.01$ past target faces to avoid coplanar slivers.
- **Subdivided Lathe Profiles**: When revolving architectural plinths or vessels with `MeshBuilder.lathe(..., subdivide=3)`, subdivide profile segments so boolean and vertex-color operations have sufficient vertex density.

### 2. Coordinate System & Triangle Budget
- **Internal Z-Up $\to$ glTF Y-Up**: Model in Z-up with ground plane at $Z = 0$. Export GLB with `apply_y_up=True` ($-90^\circ$ X-axis rotation) and OBJ in native Z-up.
- **Polygon Budget**: Enforce $\le 3000$ triangles (typical prop: 200–1200 triangles; 8–16 radial segments).
- **Multiplicative Ground AO**: Apply `bake_ground_ao(mesh, height=..., strength=...)` after assigning per-part face colors so base darkening preserves upper material palettes.

### 3. Knowledge Vault References
- **Stylized Bevels & Turned Profiles**: [`vault/techniques/art_styles/bevels_and_edge_weight.md`](../../vault/techniques/art_styles/bevels_and_edge_weight.md) & [`vault/techniques/materials/chiseled_stone_and_masonry.md`](../../vault/techniques/materials/chiseled_stone_and_masonry.md) (`MeshBuilder.lathe`).
- **Golden Ratio & Tapered Monuments**: [`vault/mathematics/geometry/spirals_and_golden_ratio.md`](../../vault/mathematics/geometry/spirals_and_golden_ratio.md) (`MeshBuilder.pyramid`).
- **Vertex Color & Ground Contact AO**: [`vault/techniques/art_styles/vertex_color_gradient_baking.md`](../../vault/techniques/art_styles/vertex_color_gradient_baking.md) (`bake_ground_ao`, `bake_vertex_gradient_ao`).
- **Foliage Normal Bending & Impostors**: [`vault/techniques/geometry/foliage_spherical_normal_bending.md`](../../vault/techniques/geometry/foliage_spherical_normal_bending.md), [`vault/techniques/geometry/leaf_cards_and_alpha_branching.md`](../../vault/techniques/geometry/leaf_cards_and_alpha_branching.md), [`vault/techniques/geometry/billboards_and_impostors.md`](../../vault/techniques/geometry/billboards_and_impostors.md).
- **Out of Scope (3D Skeletal Animation)**: [`vault/future_scope/3d_skeletal_animation.md`](../../vault/future_scope/3d_skeletal_animation.md).

## Code Example: `MeshBuilder`

```python
from asset_pipeline import MeshBuilder, SolidMesh, bake_ground_ao

def build_crystal_pillar(seed: int = 7) -> SolidMesh:
    builder = MeshBuilder(seed=seed)
    builder.lathe([[0.0, 0.0], [0.45, 0.0], [0.40, 0.25], [0.0, 0.25]], sections=8, color=[65, 70, 80, 255], subdivide=3)
    builder.pyramid(base_radius=0.30, height=1.10, sections=6, offset=[0, 0, 0.25], color=[100, 200, 255, 255])
    mesh = builder.build()
    bake_ground_ao(mesh, height=0.45, strength=0.45)
    mesh.ensure_watertight()
    return mesh
```

## Domain Acceptance Checks

1. **Geometry & Budget**: `AssetValidator.validate_mesh(glb_path, max_triangles=3000, watertight=True)` (watertight manifold, consistent winding, positive volume).
2. **Shading & Orientation**: `AssetValidator.validate_mesh_shading(mesh, max_ground_ratio=0.85)` and inspect the 3-view `preview.png` (iso, front, side) to verify upright orientation and grounded base AO.

## Multi-Part Props & Full Scenes (`SceneBuilder` + `spec.json`)

For multi-part assets, articulated props, or full biome environments (`python -m asset_pipeline new 3d_scene <dir>`), follow the 5-stage contract in [`vault/techniques/geometry/staged_scene_assembly.md`](../../vault/techniques/geometry/staged_scene_assembly.md):

1. **PARSE (`spec.json`)**: Define `parts` (name, material, pivot, dimensions, `max_triangles`) and `materials` before writing geometry.
2. **MASS & RIG**: Build modular part geometry and register each via `scene.add_part(name, geom, material=..., pivot=...)` so glTF nodes retain clean names and rotation pivots.
3. **SKIN & PACK**: Export multi-node `.glb` (`scene.export_glb`), grouped `.obj` (`scene.export_obj`), and shadow-mapped Z-buffer preview (`scene.render_preview`).

For hero props, characters, or vehicles requiring procedural PBR textures and per-subsystem modules, scaffold `python -m asset_pipeline new 3d_hero_package <dir>` (`parts/`, `textures.py`, `materials.py`, `rig.py`, `test_asset.py`). `SceneBuilder.export_glb()` embeds PNG albedo/normal/roughness maps and `TEXCOORD_0` UVs directly inside the `.glb`.

## Sculpting Primitives & Gold-Standard Exemplar

- Use `asset_pipeline.sculpt` (`catmull_rom_tube`, `extrude_beveled_2d`, `loft_cross_sections`, `catenary_cloth`, `array_along_curve`) instead of stacking raw boxes and straight cylinders.
- Study [`examples/sky_galleon_hero/`](../../examples/sky_galleon_hero/README.md) as a concrete multi-module hero reference and follow [`vault/techniques/art_styles/production_critique_loop.md`](../../vault/techniques/art_styles/production_critique_loop.md) for subsystem-level visual critique.

## V6 Production Discipline (Mandatory Across All Modalities)
1. **Research-First & Seed the Vault**: Before writing code for any domain, silhouette, shader, or audio synthesis technique not already documented in `vault/`, research authoritative references (or `benchmarks/prompts.json`) and **seed a reusable `vault/techniques/...` guide** (and register it in `vault/README.md` + `manifest.json` `vault_refs`). Never improvise complex anatomy or DSP math without checking/seeding the vault.
2. **Optimize Representation (`vault/techniques/optimization/cross_modality_asset_optimization.md`)**:
   - **3D**: Use geometry strictly for silhouette; paint markings (stripes, emblems, seams) in albedo UVs and bake micro-relief (fur, wood grain, cloth weave) into tangent-space normal maps via `asset_pipeline.baking`.
   - **2D / UI**: Maximize alpha fill efficiency (`compute_sprite_alpha_efficiency`), clean value hierarchy, and power-of-two sizing.
   - **VFX**: Tight per-frame alpha bounds, channel-packed noise masks, and minimal overdraw.
   - **SFX**: Normalize to `-1.0 dBFS` headroom, high-pass sub-30 Hz mud, and ensure zero-crossing loop/tail cleanliness.
3. **Two-Tier Critique Loop (`asset_pipeline.critique.CritiqueLog`)**:
   - **Tier 1 (Inner Build Loop, min 3 rounds)**: Blockout -> Secondary -> Final candidate.
   - **Tier 2 (Outer 0-10 Detail-Critique Re-Loop, up to 5 outer passes)**: Score the Final 0-10 on hard modality-specific details (`add_detail_pass`). If the score is `< 9.0/10`, treat that Final as the **new starting point**, fix every identified detail flaw, and re-loop up to **5 outer passes** until it passes `>= 9.0/10`.
