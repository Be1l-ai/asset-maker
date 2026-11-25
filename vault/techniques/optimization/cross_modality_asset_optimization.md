# Cross-Modality Asset Optimization (3D, 2D, VFX, SFX)

Production-ready game assets maximize visual and audio impact per byte and per draw call. Never spend raw polygons, redundant pixels, or excessive overdraw on details that belong in a cheaper representation.

## 1. 3D Assets: Silhouette vs. Albedo vs. Normal Maps
* **Geometry = Silhouette Only**: Spend triangles on forms that change the 3D outline (body anatomy, unified paws, ears, curved hull strakes, rigging, collar, bell).
* **Albedo Texture = Color Markings**: Paint tabby stripes, forehead M-marks, cheek blush, plank seams, cloth stripes, and emblems directly onto clean UVs — **never model surface markings as floating 3D tubes or cones**.
* **Tangent-Space Normal & Roughness Maps = Micro-Relief**: Use `asset_pipeline.baking.height_to_normal_map`, `generate_fur_normal_map`, `generate_cloth_normal_map`, and `generate_wood_grain_normal_map` to convey fur directionality, cloth weave, and wood grain at zero extra polygon cost.
* **Merge Redundant Sub-Meshes**: Group same-material details into unified named nodes (e.g., all brass hardware or all paws) to minimize draw calls while preserving logical part separation.

## 2. 2D Sprites, Icons & Web UI
* **Alpha Overdraw Efficiency**: Keep non-transparent fill ratio high (check with `compute_sprite_alpha_efficiency()`) — tight bounding crops eliminate wasted transparent fragment shading.
* **Value Hierarchy Before Micro-Noise**: Readability at 64×64 and 128×128 comes from 3 clear value tiers (highlight, midtone, shadow) and bold silhouettes, not high-frequency noise that muddies under mipmapping.
* **Power-of-Two Dimensions**: Export textures at 256, 512, 1024, or 2048 px so GPU compression (BC7/ASTC) works cleanly.

## 3. VFX Flipbooks & Shaders
* **Frame Budget & Atlas Packing**: Prefer 4×4 (16 frames) or 6×6 (36 frames) atlases with tight per-frame alpha bounds; never leave huge empty margins around particles.
* **Channel-Packed Masks**: Pack noise, erosion gradient, and emissive core into R/G/B channels of a single texture to cut texture samples by 3×.

## 4. SFX Audio Assets
* **Headroom & Loudness**: Normalize peaks to `-1.0 dBFS` (never clip at `0.0 dBFS`), apply a subtle high-pass filter around `30–40 Hz` to remove inaudible DC/sub-rumble mud.
* **Clean Loops & Tails**: Trim trailing silence below `-60 dBFS` and crossfade looping ambience at zero-crossings to prevent clicks.
