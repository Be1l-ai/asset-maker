---
name: create-3d-assets
description: Deep procedural 3D modeling skill. Build watertight low-poly props, solids, and modular geometry using Trimesh and Manifold3D booleans, with Y-up coordinate conversion, triangle budgets, and headless multi-view previews.
---

# Procedural 3D Mesh Construction

Build game-ready 3D solids entirely in code using `trimesh` and `manifold3d`.

## Architectural Guidelines

### 1. Watertight Solid CSG & Topology
- **Manifold Booleans**: All input meshes for boolean operations (`union`, `difference`, `intersection`) must be strictly watertight, consistently wound, and possess positive volume.
- **Avoid Coplanar Slivers**: When cutting or indenting surfaces, extend the cutting solid slightly beyond the target boundary face ($0.001$ to $0.01$ margin) to avoid non-manifold coincident edge artifacts.
- **Topological Integrity**: Always call `mesh.merge_vertices(merge_tex=True, merge_norm=True)` and assert `mesh.is_watertight` and `mesh.volume > 0`.

### 2. Coordinate System & Engine Orientation
- **Internal Modeling**: Construct geometry naturally in Z-up coordinates with the ground plane at $Z = 0$ and pivot centered at $(0, 0, 0)$.
- **glTF Y-Up Export**: Game engines (Godot, Unity, Roblox, Three.js) expect Y-up in glTF/GLB files. Apply a $-90^\circ$ rotation around the X-axis (`Z_TO_Y`) when exporting GLB.
- **OBJ Export**: Export raw geometry to OBJ as a portable baseline without baking ambiguous axis transforms.

### 3. Triangle Budget & Polygon Optimization
- Low-poly props have a hard ceiling of $\le 3000$ triangles (typical budget: 200–1200 triangles).
- Limit cylinder and cone radial subdivisions to 8–16 segments.
- Use explicit parameterized profiles and extrusions rather than stacking thousands of micro-cubes.

### 4. Color & Material Regions
- Assign uniform RGBA colors to mesh face groups using `mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, face_colors=...)`.
- Apply color assignments after boolean operations, as boolean engines reconstruct topology.

### 5. Knowledge Vault References
- **Stylized Bevels & Silhouettes**: See [`vault/techniques/art_styles/bevels_and_edge_weight.md`](../../vault/techniques/art_styles/bevels_and_edge_weight.md).
- **Foliage Normal Bending & Leaf Cards**: See [`vault/techniques/geometry/foliage_spherical_normal_bending.md`](../../vault/techniques/geometry/foliage_spherical_normal_bending.md).
- **Profile Lathe / Revolution**: Use `MeshBuilder.lathe()` or `revolve_profile()` from `asset_pipeline`.
- **Out of Scope (3D Animation)**: See [`vault/future_scope/3d_skeletal_animation.md`](../../vault/future_scope/3d_skeletal_animation.md) (never generate skeletal animations from scratch).


## Code Example: `MeshBuilder`

Use the object-oriented `MeshBuilder` and `SolidMesh` classes:

```python
from asset_pipeline import MeshBuilder, SolidMesh

def build_crystal_pillar(seed: int = 7) -> SolidMesh:
    builder = MeshBuilder(seed=seed)
    
    # Octagonal stone base
    builder.cylinder(radius=0.40, height=0.20, sections=8, color=[65, 70, 80, 255])
    
    # Faceted crystal top
    builder.pyramid(base_radius=0.30, height=1.00, sections=6, offset=[0, 0, 0.20], color=[100, 200, 255, 255])
    
    mesh = builder.build()
    mesh.ensure_watertight()
    return mesh
```

## Scaffolding & Generation

```sh
# Scaffold a new 3D prop:
.venv-code-assets/bin/python -m asset_pipeline new 3d_prop assets/<asset_name>

# Execute generator and produce GLB, OBJ, and isometric preview.png:
cd assets/<asset_name> && python generate.py
```

## Validation & Quality Checklist

1. **Volume & Winding**: Confirm `watertight=True` and consistent face winding with `AssetValidator.validate_mesh(path, watertight=True)`.
2. **Budget**: Ensure total triangle count is within budget ($\le 3000$).
3. **Software Preview**: Inspect `preview.png` rendered from multiple isometric angles with software depth sorting.

## Verification Loop (Required)

Structural validation proves a file is well-formed, not that it is good. Before declaring any asset done:

1. **Look.** Open `preview.png` (3D: three views; tile: albedo + normal-lit; VFX: contact sheet). Name one concrete defect, fix it, re-render. Read [`vault/pitfalls/procedural_failure_modes.md`](../../vault/pitfalls/procedural_failure_modes.md).
2. **Declare the vault.** For every vault doc you applied, call `manifest.declare_vault("<path under vault/>", "<pipeline symbol you call>")`. Never import a technique you do not call.
3. **Audit.** `.venv-code-assets/bin/python -m asset_pipeline audit assets/<name>` must pass (no unused pipeline imports, real vault docs, symbols actually used, no stale hashes).
4. **Domain acceptance:** `validate_mesh(..., watertight=True)` plus `validate_mesh_shading(mesh)`. Use `bake_ground_ao` (multiplicative), `lathe(..., subdivide=3)`, and check front/side previews for upright orientation.
5. **Hash only your files:** `manifest.scan_directory(out, only=[ASSET_NAME])`.
6. **Compare to the baseline with numbers** if this replaces an earlier version: `python -m asset_pipeline compare <old> <new>`. Do not state numbers in a README that are not in the manifest.
