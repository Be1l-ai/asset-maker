"""PBR MaterialSpec registry wired to procedural textures for this package."""

from __future__ import annotations

from asset_pipeline.scene3d import MaterialSpec
from textures import build_stone_textures, build_wood_textures


def build_materials(seed: int = 7) -> dict[str, MaterialSpec]:
    stone = build_stone_textures(size=128, seed=seed)
    wood = build_wood_textures(size=128, seed=seed + 1)
    return {
        "stone_plinth": MaterialSpec(
            name="ChiseledStone",
            roughness=0.86,
            metallic=0.04,
            uv_scale=1.2,
            base_color_texture=stone["albedo"],
            normal_texture=stone["normal"],
        ),
        "aged_wood": MaterialSpec(
            name="AgedTimber",
            roughness=0.90,
            metallic=0.0,
            uv_scale=1.5,
            base_color_texture=wood["albedo"],
            normal_texture=wood["normal"],
        ),
        "arcane_crystal": MaterialSpec(
            name="ArcaneCrystal",
            roughness=0.22,
            metallic=0.08,
            emissive=(0.18, 0.58, 0.72),
            shading_mode="pbr",
        ),
    }
