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
