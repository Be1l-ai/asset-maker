"""PBR MaterialSpec registry for sky_galleon_hero."""

from __future__ import annotations

from asset_pipeline.scene3d import MaterialSpec
from textures import build_cedar_plank_textures, build_sail_textures


def build_materials() -> dict[str, MaterialSpec]:
    cedar = build_cedar_plank_textures(512)
    emblem = build_sail_textures(512, with_emblem=True)
    stripe = build_sail_textures(512, with_emblem=False)
    return {
        "hull_cedar": MaterialSpec("CaulkedCedarHull", roughness=0.72, metallic=0.05, uv_scale=0.35, base_color_texture=cedar["albedo"], normal_texture=cedar["normal"]),
        "deck_planks": MaterialSpec("WeatheredDeck", roughness=0.82, metallic=0.0, uv_scale=0.55, base_color_texture=cedar["albedo"], normal_texture=cedar["normal"]),
        "sail_emblem": MaterialSpec("MainEmblemSail", roughness=0.86, metallic=0.0, uv_scale=1.0, shading_mode="cloud", base_color_texture=emblem["albedo"], normal_texture=emblem["normal"]),
        "sail_stripe": MaterialSpec("StripedRacingSail", roughness=0.86, metallic=0.0, uv_scale=1.0, shading_mode="cloud", base_color_texture=stripe["albedo"], normal_texture=stripe["normal"]),
        "brass_gold": MaterialSpec("BurnishedBrass", roughness=0.26, metallic=0.90),
        "turbine_iron": MaterialSpec("RivetedTurbineIron", roughness=0.42, metallic=0.82),
        "rope_hemp": MaterialSpec("HempRigging", roughness=0.92, metallic=0.0),
        "cyan_thruster": MaterialSpec("AetherThrusterGlow", roughness=0.15, metallic=0.0, emissive=(0.22, 0.92, 1.0), shading_mode="emissive"),
        "amber_lantern": MaterialSpec("WarmLanternGlow", roughness=0.18, metallic=0.0, emissive=(1.0, 0.78, 0.28), shading_mode="emissive"),
    }
