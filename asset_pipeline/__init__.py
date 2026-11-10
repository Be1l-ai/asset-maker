"""AssetMaking procedural asset generation library."""

try:
    from .cli import init_asset, list_templates
    from .manifest import Manifest, get_installed_versions, save_manifest, sha256
    from .mesh3d import (
        MeshBuilder,
        SolidMesh,
        apply_spherical_normals,
        bake_ground_ao,
        bake_vertex_gradient_ao,
        create_leaf_card,
        revolve_profile,
    )
    from .sfx import Sound, SoundSynthesizer, spatial_stereo_pan
    from .sprite2d import (
        SeamlessTile,
        SpriteCanvas,
        ellipse_mask,
        fillet_mask,
        heightmap_to_normal_map,
        inside_depth,
        lerp_color,
        new_layer,
        nine_slice,
        over,
        polygon_mask,
        procedural_fabric_weave,
        procedural_wood_grain,
        worley_noise,
    )
    from .validator import AssetValidator, ValidationReport
    from .vfx import (
        Easing,
        EmitterStack,
        Flipbook,
        ParticleEmitter,
        create_expanding_mesh_explosion,
        dissolve_alpha_mask,
    )
    from .audit import audit_recipe, compare_assets, asset_metrics
    from . import audit, manifest, mesh3d, sfx, sprite2d, validator, vfx
except ModuleNotFoundError:  # pragma: no cover - standalone extracted gallery archive
    pass

__all__ = [
    # Core domain classes
    "SolidMesh",
    "MeshBuilder",
    "SpriteCanvas",
    "SeamlessTile",
    "Flipbook",
    "ParticleEmitter",
    "EmitterStack",
    "Easing",
    "Sound",
    "SoundSynthesizer",
    "AssetValidator",
    "ValidationReport",
    "Manifest",
    # 2D & Texture procedural generators
    "heightmap_to_normal_map",
    "worley_noise",
    "procedural_fabric_weave",
    "procedural_wood_grain",
    # 3D & Geometry helpers
    "revolve_profile",
    "apply_spherical_normals",
    "bake_vertex_gradient_ao",
    "bake_ground_ao",
    # 2D layer/mask helpers
    "ellipse_mask",
    "polygon_mask",
    "fillet_mask",
    "inside_depth",
    "new_layer",
    "nine_slice",
    "over",
    "lerp_color",
    # Verification
    "audit_recipe",
    "compare_assets",
    "asset_metrics",
    "audit",
    "create_leaf_card",
    # VFX procedural generators
    "dissolve_alpha_mask",
    "create_expanding_mesh_explosion",
    # SFX helpers
    "spatial_stereo_pan",
    # CLI / scaffolding
    "init_asset",
    "list_templates",
    # Submodules
    "mesh3d",
    "sprite2d",
    "vfx",
    "sfx",
    "validator",
    "manifest",
]

