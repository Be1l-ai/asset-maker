# Code-first game asset libraries

Research checked on 2026-11-06 using GitHub metadata, license text, and upstream implementations/examples, not star counts. Use this as a source map, not as a promise that every upstream release remains compatible. Tested pins live in `requirements-code-assets.txt`; Python 3.12+ is required by the selected NumPy/SciPy versions. No third-party source is vendored here.

## Selected default stack

| Library / upstream | Tested pin | License checked | Role and boundaries |
| --- | --- | --- | --- |
| [NumPy](https://github.com/numpy/numpy) | `numpy==2.5.1` | BSD-3-Clause, `LICENSE.txt` | Seeded arrays, waves, scalar fields, and coordinates; not an asset generator by itself. |
| [SciPy](https://github.com/scipy/scipy) | `scipy==1.18.0` | BSD-3-Clause, `LICENSE.txt` | Offline DSP and WAV export; no audio device or DAW. Build timbre and envelopes in the recipe. |
| [Pillow](https://github.com/python-pillow/Pillow) | `Pillow==12.3.0` | MIT-CMU, `LICENSE` | RGBA drawing, compositing, atlas/animation export. No automatic style, seamlessness, or UV baking. |
| [Trimesh](https://github.com/mikedh/trimesh) | `trimesh==5.2.0` | MIT, `LICENSE.md` | Mesh construction, transforms, validation, GLB/OBJ. Avoid application-backed rendering and optional triangulators by default. |
| [Manifold](https://github.com/elalish/manifold) | `manifold3d==3.5.4` | Apache-2.0, `LICENSE` | Headless solid booleans, extrusion, revolution, implicit geometry. Native library wheel, not a modeling application. |
| [aggdraw](https://github.com/pytroll/aggdraw) | `aggdraw==1.4.1` | MIT-style interface and permissive bundled AGG2 notices, `LICENSE.txt` | Antialiased Bezier paths directly onto Pillow images. Not an SVG parser or document editor. |

All six selected repositories were unarchived when checked. Upstream research found SciPy 1.18.1 and Pillow 13.0.0; the local examples intentionally use the existing environment's 1.18.0/12.3.0 versions in a separate virtual environment and verify their APIs. Do not confuse latest upstream releases with tested versions.

GitHub reports `NOASSERTION` for some repositories; inspect the actual license text instead of interpreting that as no license. Retain applicable notices when redistributing library code or binaries. This catalog is technical research, not legal advice; it does not establish a license for this project's own code.

## Audio source map

- NumPy `numpy/random/_generator.pyx`: `default_rng`, `Generator.standard_normal`, `Generator.uniform`. Use a local generator, not global seeding. Checked against default-branch revision `f4f0ee67378a1173112ce0176922ce2286e939ac`.
- SciPy [`scipy/signal/_waveforms.py`](https://github.com/scipy/scipy/blob/v1.18.1/scipy/signal/_waveforms.py): `chirp`; `square` and `sawtooth` are explicitly not band-limited.
- SciPy [`scipy/signal/_filter_design.py`](https://github.com/scipy/scipy/blob/v1.18.1/scipy/signal/_filter_design.py): `butter(..., fs=rate, output="sos")`.
- SciPy [`scipy/signal/_signaltools.py`](https://github.com/scipy/scipy/blob/v1.18.1/scipy/signal/_signaltools.py): `sosfilt`, with time axis defaulting to the last dimension. Stereo `(frames, channels)` filtering therefore normally needs `axis=0`.
- SciPy [`scipy/io/wavfile.py`](https://github.com/scipy/scipy/blob/v1.18.1/scipy/io/wavfile.py): `read`, `write`; dtype selects PCM/float encoding, stereo uses `(frames, channels)`.

Use these primitives for modal synthesis, filtered-noise textures, physically motivated layers, parameter sweeps, and deterministic variations. SciPy supplies no finished explosion, footstep, or creature model.

## Raster and VFX source map

- Pillow [`src/PIL/Image.py`](https://github.com/python-pillow/Pillow/blob/13.0.0/src/PIL/Image.py): `new`, `fromarray`, `alpha_composite`, `paste`, `save`. Use `paste(frame, xy)` for nonoverlapping atlas cells; passing the same RGBA frame as its mask changes alpha.
- Pillow [`src/PIL/ImageDraw.py`](https://github.com/python-pillow/Pillow/blob/13.0.0/src/PIL/ImageDraw.py): `polygon`, `ellipse`, `rounded_rectangle`.
- Pillow [`src/PIL/ImageFilter.py`](https://github.com/python-pillow/Pillow/blob/13.0.0/src/PIL/ImageFilter.py): `GaussianBlur`, `Kernel`.
- Pillow [`docs/handbook/image-file-formats.rst`](https://github.com/python-pillow/Pillow/blob/13.0.0/docs/handbook/image-file-formats.rst): APNG `save_all`, `append_images`, `duration`, `loop`, `disposal`, `blend`. Use replacement blending for independent full frames. GIF has palette and timing limitations; keep the PNG atlas as the deliverable.
- aggdraw [`aggdraw.cxx`](https://github.com/pytroll/aggdraw/blob/v1.4.1/aggdraw.cxx): `Draw`, `Path`, `Pen`, `Brush`, `moveto`, `curveto`, `close`, `path`, `flush`. Read the release-specific file; current-main paths can differ.

For deterministic textures use seeded NumPy fields rather than Pillow `effect_noise`, which has no seed parameter. For loops and tiling, construct periodic functions rather than assuming an export option makes arbitrary content seamless. Build art direction independently of sampling and export.

## Geometry source map

- Trimesh [`trimesh/creation.py`](https://github.com/mikedh/trimesh/blob/5.2.0/trimesh/creation.py): `box`, `cylinder`, `icosphere`, `revolve`, `extrude_triangulation`, `sweep_polygon`. Some polygon functions require optional triangulators; do not silently add `triangle` given its distinct licensing constraints.
- Trimesh [`trimesh/base.py`](https://github.com/mikedh/trimesh/blob/5.2.0/trimesh/base.py): `Trimesh(vertices, faces)`, `is_volume`, `is_watertight`, `export`.
- Trimesh [`trimesh/boolean.py`](https://github.com/mikedh/trimesh/blob/5.2.0/trimesh/boolean.py): `difference`, `union`, `intersection`. Set `engine="manifold"` explicitly. The adapter transfers positions/indices, not appearance; apply colors, materials, and UVs afterward.
- Trimesh [`trimesh/exchange/gltf/__init__.py`](https://github.com/mikedh/trimesh/blob/5.2.0/trimesh/exchange/gltf/__init__.py): `export_glb`, `export_gltf`. Reload the actual export and check axes, materials, and bounds.
- Manifold [`bindings/python/manifold3d.cpp`](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/manifold3d.cpp): `CrossSection`, `Manifold.cube`, `cylinder`, `extrude`, `revolve`, `level_set`, `warp`, `to_mesh`. Operators `+`, `-`, `^` mean union, difference, intersection.
- Manifold [`bindings/python/examples/extrude.py`](https://github.com/elalish/manifold/blob/v3.5.4/bindings/python/examples/extrude.py): profile/extrusion construction to adapt after an API probe.

Require watertight, consistently wound positive-volume inputs for solid booleans. Manifold is not arbitrary damaged-mesh repair. Its implicit `level_set` convention is positive inside, unlike many SDF examples found elsewhere.

Treat UVs, rigging, colliders, and LODs as additional deliverables, not automatic side effects. `unwrap` needs optional xatlas; quadric decimation needs fast-simplification and does not transfer visuals in the wrapper; convex decomposition needs vhacdx; collision queries may need python-fcl. None is installed by the base requirements. Avoid `show()` / `Scene.save_image()` in headless workers because they require graphical infrastructure. The starter's Pillow preview is diagnostic, not a PBR renderer.

## Optional or retained libraries

| Library | Evidence and decision |
| --- | --- |
| [pyo](https://github.com/belangeo/pyo) | Retain the existing pipeline only. LGPL-3.0 with source headers allowing later versions, not a permissive default. `pyo/lib/server.py` supports blocking offline rendering and a global seed API, but the local notes record unseeded legacy `Noise` behavior. Do not assume newer upstream seeding changes local output. Native audio dependencies can complicate installation. |
| [chr15m/jsfxr](https://github.com/chr15m/jsfxr) | Optional retro SFX specialist, Unlicense. Studied `sfxr.js` at `b7b6aa27d62f8f356db267276bf54b451555c49d` plus `sfxr-to-wav`: CommonJS `Params`, `generate`, `toWave`; write `Buffer.from(toWave(params).wav)` from Node without a browser. Noise and presets use unseeded `Math.random`; request PCM16, prefer 44.1 kHz, and do not mistake `toBuffer()` PCM bytes for floats. Not installed/tested here. |
| [OpenSimplex](https://github.com/lmas/opensimplex) | MIT; GitHub snapshot archived and README announces migration. Studied `opensimplex/api.py` at `ba5cf7faca5f1bde8e322c90d9c1244458551ce1`. `noise4array(x,y,z,w)` returns `(len(w),len(z),len(y),len(x))`, a Cartesian product, not paired coordinates. For periodic time use singleton `z=[cos(theta)]`, `w=[sin(theta)]` per frame, then `[0,0]`. Global seed and optional Numba/cache behavior need care. Pin/review separately; not installed/tested here. |
| [drawsvg](https://github.com/cduck/drawsvg) | MIT, surveyed version 2.4.2. Useful when editable SVG is required. SVG construction itself does not need a renderer; PNG conversion adds CairoSVG/native Cairo. Prefer aggdraw for raster-only work. Not installed/tested here. |
| [svgwrite](https://github.com/mozman/svgwrite) | Archived/unmaintained; do not choose it for new work over the supported alternatives. |

Do not use `pillow/Pillow` or `fonttools/aggdraw`; both candidate URLs returned 404. The verified upstreams are the links in the selected table. The older grumdrig/jsfxr repository recommends chr15m's fork.

## Recheck an API before using it

Use the same interpreter that runs the recipe:

```sh
.venv-code-assets/bin/python -c "import inspect; from scipy import signal; print(inspect.signature(signal.butter)); print(inspect.getsource(signal.butter))"
gh api repos/mikedh/trimesh --jq '{archived: .archived, license: .license.spdx_id, default_branch: .default_branch}'
```

Read one relevant function and one upstream example/test; do not load entire repositories into context. For extension functions without inspectable Python source, read their docstrings and the binding implementation linked above. Run a tiny local probe. Recheck maintenance and licensing before adding or upgrading optional dependencies, and record exactly which version was exercised.
