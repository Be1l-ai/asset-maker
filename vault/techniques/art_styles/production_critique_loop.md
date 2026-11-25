# Production Critique Loop, Style Profiles & Triple-Track Routing

How `asset-maker` enforces consistent production quality across Python, Three.js, and Web UI assets—even when driven by smaller models.

---

## 1. Style-Profile Governance (`STYLE_PROFILES`)

Polygon counts and surface treatments depend on the target art style, declared in `spec.json` via `style_profile`:

- **`stylized_lowpoly`** (`500-8,000` tris): Clean silhouettes, spherical normals, vertex-color ramps, ground AO (textures optional).
- **`hand_painted_hero`** (`10,000-60,000` tris): Lofted silhouettes, `TEXCOORD_0` painted albedo/roughness/normal maps, ≥3 materials, secondary trim/rigging.
- **`voxel`**: Grid-snapped voxel chunks, palette discipline, baked crevice AO.
- **`volumetric_shader`**: GLSL volumetric/atmospheric shaders, presets, interactive controls.
- **`web_ui_2d`**: React + HTML + CSS/Tailwind + SVG captured via headless Playwright to transparent PNG/atlas.

---

## 2. Triple-Track Routing

1. **Python Track** (`3d_prop`, `3d_scene`, `3d_hero_package`, `2d_*`, `vfx_*`, `sfx_*`): Watertight CSG booleans, terrain/math, procedural normal maps, acoustic SFX.
2. **Three.js / GLSL Track** (`3d_threejs_hero`): Rigged/animated characters, curved lofted vehicles, real-time volumetric shaders, verified via `studio/scripts/verify_glb.mjs` (`GLTFLoader` round-trip).
3. **Web UI / 2D Track** (`2d_web_ui`): Game HUDs, 9-slice panels, icons, badges captured via `studio/scripts/capture_web_ui.mjs`.

---

## 3. Mandatory Multi-Round Critique Gate (`CritiqueLog`)

Hero packages (`"quality_tier": "hero"`) must log **at least 3 visual inspection rounds** in `critique_log.json` with concrete defects, applied fixes, and **distinct preview SHA-256 hashes** between rounds:

```python
from asset_pipeline import CritiqueLog

log = CritiqueLog(asset="hero.glb", min_rounds=3)
log.add_round("v1_preview.png", defects_found=["Flat top silhouette"], fixes_applied=["Added asymmetrical crown lobes"])
log.save(".")
```

---

## 4. Anti-Slop Floors & No Fake Loops

- Never fake multi-round iteration with a single-pass `--stage 1/2/3` script. Inspect actual renders against `concept.png`, identify real defects, and rewrite the failing subsystem module in `parts/`.
- `asset_pipeline audit` mechanically enforces style-profile minimum floors (`min_triangles`, `min_nodes`, `min_part_modules`, `min_materials`, `require_uv_textures`, and `concept.png`) on `"quality_tier": "hero"` assets.
