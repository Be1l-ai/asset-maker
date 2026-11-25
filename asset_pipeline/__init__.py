"""AssetMaking procedural asset generation library."""

try:
    from .cli import init_asset, list_templates
except ModuleNotFoundError:  # pragma: no cover - standalone extracted gallery archive
    pass

try:
    from .manifest import Manifest, get_installed_versions, save_manifest, sha256
    from .audit import audit_recipe, compare_assets, asset_metrics
    from . import audit, manifest
except ModuleNotFoundError:  # pragma: no cover - standalone extracted gallery archive
    pass

try:
    from .scene3d import STYLE_PROFILES, MaterialSpec, MeshGeometry, PartSpec, SceneBuilder, SceneNode, SceneSpec
    from .critique import CritiqueLog, CritiqueRound, DetailCritiquePass, DETAIL_RUBRIC_AXES
    from .sculpt import array_along_curve, catenary_cloth, catmull_rom_points, catmull_rom_tube, extrude_beveled_2d, loft_cross_sections, merge_parts
    from .baking import (
        height_to_normal_map,
        build_metallic_roughness_map,
        generate_fur_normal_map,
        generate_cloth_normal_map,
        generate_wood_grain_normal_map,
        compute_sprite_alpha_efficiency,
    )
    from . import sculpt, scene3d
except ModuleNotFoundError:  # pragma: no cover - standalone extracted gallery archive
    pass

try:
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
    from . import mesh3d, sfx, sprite2d, validator, vfx
except ModuleNotFoundError:  # pragma: no cover - standalone extracted gallery archive
    pass

__all__ = [
    # Core domain classes
    "SolidMesh",
    "MeshBuilder",
    "SceneBuilder",
    "SceneSpec",
    "PartSpec",
    "MaterialSpec",
    "MeshGeometry",
    "SceneNode",
    "STYLE_PROFILES",
    "CritiqueLog",
    "CritiqueRound",
    "catmull_rom_points",
    "catmull_rom_tube",
    "extrude_beveled_2d",
    "loft_cross_sections",
    "catenary_cloth",
    "array_along_curve",
    "merge_parts",
    "sculpt",
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
    "scene3d",
    "sprite2d",
    "vfx",
    "sfx",
    "validator",
    "manifest",
]

