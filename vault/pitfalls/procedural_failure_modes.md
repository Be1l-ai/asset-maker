# Procedural Asset Failure Modes & Acceptance Checks

Every item below was observed in a real generated asset that passed structural validation but was visibly wrong. Each has a detection rule; the repo enforces most of them in `asset_pipeline.validator` / `asset_pipeline.audit`.

## 2D (Pillow / aggdraw)

| Failure | Cause | Fix | Check |
|---|---|---|---|
| Shape "erased" with a transparent fill still shows | aggdraw and `ImageDraw` composite *over*; `fill=(0,0,0,0)` does nothing | Build coverage **masks** (`ellipse_mask`, `polygon_mask`) and composite with `over` | `AssetValidator.validate_silhouette` (components, fill ratio) |
| Flask neck floats apart from body | Parts drawn separately and never unioned | Union masks then `fillet_mask` to round the join | `validate_silhouette(max_components=1)` |
| Tile seam visible when repeated | Non-periodic noise (`worley_noise` default) or Sobel with reflected borders | `worley_noise(..., periodic=True)`, `heightmap_to_normal_map(..., tileable=True)`, integer-frequency Fourier grain | `AssetValidator.validate_seamless` |
| Bevel "invisible" in albedo preview | Relief only shows under lighting | Render a normal-lit preview next to albedo | Look at the preview |

```python
from asset_pipeline import ellipse_mask, polygon_mask, fillet_mask, new_layer, over
import numpy as np

shape = (512, 512)
glass = fillet_mask(np.maximum(ellipse_mask(shape, 256, 330, 130, 130),
                               polygon_mask(shape, [(220, 100), (292, 100), (292, 230), (220, 230)])), 6.0)
layer = new_layer(shape)
over(layer, (200, 225, 250), glass * 0.4)          # tinted glass
over(layer, (230, 40, 80), glass * (np.mgrid[0:512, 0:512][0] > 300))  # liquid below a line
```

## 3D (trimesh)

| Failure | Cause | Fix | Check |
|---|---|---|---|
| Preview shows prop lying on its side | Z-up mesh projected with a top-down camera | `render_multi_view_preview` uses a Z-up orbit camera with 3/4, front, side views | Eyeball all three views |
| "AO" claimed but never applied | Function imported, never called; or it overwrote the palette | `bake_ground_ao` multiplies into existing face colors | `audit_recipe` (unused import), `validate_mesh_shading` |
| Not watertight after union of crystal halves | Two parts share an identical coplanar base polygon, so merged edges have 4 faces | Offset or resize one part so the base rings differ | `AssetValidator.validate_mesh(watertight=True)` |
| Collars vanish into a tapered shaft | Fixed collar radius smaller than the shaft at that height | Derive collar radius from the taper function | Eyeball front view |
| Gradients look banded | Few rings in a lathe profile | `lathe(..., subdivide=3)` | Eyeball |

## VFX (flipbooks)

| Failure | Cause | Fix | Check |
|---|---|---|---|
| Sparks jitter frame to frame | `rng` called inside the per-frame callback, so every frame re-rolls | Pre-roll particle tables once outside the callbacks | `validate_animation` (abrupt jump) |
| Claimed "plume" stage missing | Only flash, ring and sparks were drawn | One layer per stage in the stack; confirm in the contact sheet | Look at frames 3-11 |
| Non-looping / popping start | First/last frames not near-empty | End near alpha 0; start from flash | `frame_motion_profile` |

## SFX

| Failure | Cause | Fix | Check |
|---|---|---|---|
| README numbers disagree with audio | Numbers typed by hand | Keep recipe constants at module level and write them into `manifest.json` parameters | Compare manifest to README |
| Stereo file unchecked | Only the mono WAV was validated | Validate every exported WAV | `validate_wav` on each |

## Process rules

1. **Look at the output.** Render the preview, open it, name one concrete defect, fix it, re-render. Do this at least once before declaring done.
2. **Declare vault usage in code.** `manifest.declare_vault("techniques/...md", "symbol")`; `python -m asset_pipeline audit assets/<name>` fails if the symbol is never used or the doc does not exist.
3. **Hash only your own artifacts**: `scan_directory(out, only=[ASSET_NAME])`.
4. **Compare to the baseline with numbers**: `python -m asset_pipeline compare assets/a/a.png assets/b/b.png`.
