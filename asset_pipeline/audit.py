"""Verification layer: does a recipe really use what it claims, and does the output look sane?

The structural :class:`~asset_pipeline.validator.AssetValidator` only proves a file is
well-formed. This module adds the checks that catch the failures a well-formed file can
hide: dead imports posing as technique usage, vault references that do not exist or are
never called, broken silhouettes, flat shading, and v1-vs-v2 regressions.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VAULT_DIR = ROOT / "vault"
PACKAGE = "asset_pipeline"


# ---------------------------------------------------------------------------
# Recipe / vault provenance audit
# ---------------------------------------------------------------------------

@dataclass
class AuditReport:
    """Result of a recipe audit; ``ok`` is False if any error was found."""
    asset_dir: Path
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def format(self) -> str:
        lines = [f"audit {self.asset_dir.name}: {'OK' if self.ok else 'FAIL'}"]
        lines += [f"  error: {e}" for e in self.errors]
        lines += [f"  warn:  {w}" for w in self.warnings]
        return "\n".join(lines)


def _pipeline_imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == PACKAGE:
            names.update(a.asname or a.name for a in node.names)
    return names


def used_names(source: str) -> set[str]:
    """Names (plain or attribute) that are *referenced* outside import statements."""
    tree = ast.parse(source)
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    return used


def unused_pipeline_imports(recipe: Path | str) -> List[str]:
    """Names imported from ``asset_pipeline`` that the recipe never uses."""
    source = Path(recipe).read_text()
    imported = _pipeline_imports(ast.parse(source))
    used = used_names(source)
    return sorted(n for n in imported if n not in used)


def audit_recipe(asset_dir: Path | str, vault_dir: Path | str = VAULT_DIR) -> AuditReport:
    """Audit one asset folder: unused pipeline imports and manifest ``vault_refs``.

    Errors:
      * a pipeline function is imported but never called (dead "technique" claim);
      * a declared vault doc does not exist;
      * a declared symbol is not used by ``generate.py``;
      * the manifest hashes files that belong to a different asset version.
    """
    adir = Path(asset_dir)
    report = AuditReport(asset_dir=adir)
    recipe = adir / "generate.py"
    manifest_path = adir / "manifest.json"

    spec_path = adir / "spec.json"
    spec_data_pre: Dict[str, Any] = {}
    if spec_path.is_file():
        try:
            spec_data_pre = json.loads(spec_path.read_text(encoding="utf-8"))
        except Exception:
            spec_data_pre = {}
    track = str(spec_data_pre.get("track", "python"))
    report.info["track"] = track
    report.info["style_profile"] = spec_data_pre.get("style_profile", "stylized_lowpoly")

    source = ""
    used: set[str] = set()
    if track == "python":
        if not recipe.is_file():
            report.errors.append("generate.py is missing")
            return report
        source = recipe.read_text()
        used = used_names(source)
        for name in unused_pipeline_imports(recipe):
            report.errors.append(f"'{name}' is imported from {PACKAGE} but never used")
    elif track == "threejs":
        ts_entry = adir / "src" / "buildAsset.ts"
        if not ts_entry.is_file():
            report.errors.append("src/buildAsset.ts is missing for threejs track")
            return report
        source = ts_entry.read_text(encoding="utf-8")
    elif track == "web_ui":
        ui_entry = adir / "AssetView.tsx"
        if not ui_entry.is_file():
            report.errors.append("AssetView.tsx is missing for web_ui track")
            return report
        source = ui_entry.read_text(encoding="utf-8")

    if not manifest_path.is_file():
        report.errors.append("manifest.json is missing")
        return report

    manifest = json.loads(manifest_path.read_text())
    refs: Dict[str, List[str]] = manifest.get("vault_refs", {})
    report.info["vault_refs"] = refs
    if not refs:
        report.warnings.append("manifest declares no vault_refs (recipe does not cite the vault)")

    for doc, symbols in refs.items():
        if not (Path(vault_dir) / doc).is_file():
            report.errors.append(f"vault doc '{doc}' does not exist")
        for sym in symbols:
            if track == 'python' and sym not in used:
                report.errors.append(f"vault doc '{doc}' claims '{sym}' but generate.py never uses it")

    prefix_underscore = adir.name.replace("-", "_")
    stale = [
        name for name in manifest.get("sha256", {})
        if name not in ("generate.py", "spec.json", "inspector.json", "critique_log.json", "geometry_math.py", "textures.py", "materials.py", "rig.py", "test_asset.py", "README.md", "preview.png", "preview.gif",
                        "image.png", "normal.png", "atlas.png", "model.glb", "model.obj", "mesh.json",
                        "sound.wav", "sound_stereo.wav")
        and not name.startswith(adir.name)
        and not name.startswith(prefix_underscore)
    ]
    if stale:
        report.errors.append(f"manifest hashes files from another asset/version: {', '.join(stale)}")

    spec_path = adir / "spec.json"
    if spec_path.is_file():
        try:
            spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
            spec_parts = spec_data.get("parts", [])
            report.info["spec_parts"] = [p.get("name") for p in spec_parts if isinstance(p, dict)]
            if not spec_parts:
                report.errors.append("spec.json declares no parts")
            for sp in spec_parts:
                pname = sp.get("name") if isinstance(sp, dict) else None
                if pname and f'"{pname}"' not in source and f"'{pname}'" not in source:
                    report.warnings.append(f"spec.json part '{pname}' is not explicitly referenced in generate.py")
            if spec_data.get("quality_tier") == "hero":
                from .critique import CritiqueLog
                from .scene3d import STYLE_PROFILES
                profile_name = str(spec_data.get("style_profile", "stylized_lowpoly"))
                prof = STYLE_PROFILES.get(profile_name, {})

                # CROSS-MODALITY DETAIL CRITIQUE & OPTIMIZATION GATE
                c_errors = CritiqueLog.validate_file(adir / "critique_log.json", min_rounds=3, require_detail_pass=False)
                report.errors.extend(c_errors)

                if track == "python" and not (adir / "test_asset.py").is_file():
                    report.errors.append("hero python package must include test_asset.py")
                if track == "threejs" and not (adir / "src" / "asset.test.ts").is_file():
                    report.errors.append("hero threejs package must include src/asset.test.ts")

                # Enforce subsystem decomposition (parts/ module count)
                min_mods = int(prof.get("min_part_modules", 0))
                if min_mods > 0 and track in ("python", "threejs"):
                    parts_dir = (adir / "parts") if track == "python" else (adir / "src" / "parts")
                    ext = ".py" if track == "python" else ".ts"
                    mods = [f for f in parts_dir.glob(f"*{ext}") if f.name != "__init__.py"] if parts_dir.is_dir() else []
                    if len(mods) < min_mods:
                        report.errors.append(
                            f"style_profile '{profile_name}' requires >= {min_mods} subsystem modules in {parts_dir.name}/; found {len(mods)}"
                        )

                # Enforce concept reference anchor for high-craft hero profiles
                if prof.get("require_concept_ref") and not spec_data.get("skip_concept_ref"):
                    has_concept = any((adir / fn).is_file() for fn in ("concept.png", "concept.jpg", "concept.webp"))
                    if not has_concept:
                        report.errors.append(
                            f"style_profile '{profile_name}' requires a concept reference image (concept.png/.jpg/.webp) before modeling"
                        )

                # Enforce minimum geometric/material craft floors from inspector.json when present
                insp_path = adir / "inspector.json"
                if insp_path.is_file() and track in ("python", "threejs"):
                    insp = json.loads(insp_path.read_text(encoding="utf-8"))
                    tris = int(insp.get("total_triangles", 0))
                    ncount = int(insp.get("node_count", 0))
                    nodes_meta = insp.get("nodes", [])
                    mat_count = len({n.get("material_key", n.get("material")) for n in nodes_meta})
                    has_tex = any(n.get("has_textures") for n in nodes_meta)

                    min_t = int(prof.get("min_triangles", 0))
                    if min_t > 0 and tris < min_t:
                        report.errors.append(f"hero asset has only {tris} triangles; '{profile_name}' floor is >= {min_t}")
                    min_n = int(prof.get("min_nodes", 0))
                    if min_n > 0 and ncount < min_n:
                        report.errors.append(f"hero asset has only {ncount} named nodes; '{profile_name}' floor is >= {min_n}")
                    min_m = int(prof.get("min_materials", 0))
                    if min_m > 0 and mat_count < min_m:
                        report.errors.append(f"hero asset uses only {mat_count} material(s); '{profile_name}' floor is >= {min_m}")
                    if prof.get("require_uv_textures") and not has_tex:
                        report.errors.append(f"style_profile '{profile_name}' requires embedded PBR UV textures")
        except Exception as exc:
            report.errors.append(f"spec.json is invalid JSON: {exc}")

    # Cross-modality critique_log.json validation (2D, VFX, SFX, Web UI)
    if (adir / "critique_log.json").is_file() and not (adir / "spec.json").is_file():
        from .critique import CritiqueLog as _CL
        for err in _CL.validate_file(adir / "critique_log.json", min_rounds=1, require_detail_pass=False):
            report.errors.append(err)

    # 3D Hero optimization advisory: encourage baked normal maps for micro-relief
    if (adir / "spec.json").is_file():
        try:
            _sp = json.loads((adir / "spec.json").read_text(encoding="utf-8"))
            if _sp.get("style_profile") == "hand_painted_hero":
                _code_blob = ""
                for _fn in ("generate.py", "materials.py", "textures.py"):
                    if (adir / _fn).is_file():
                        _code_blob += (adir / _fn).read_text(encoding="utf-8", errors="ignore")
                if "normal_texture" not in _code_blob:
                    report.warnings.append(
                        "hand_painted_hero asset does not wire any normal_texture; consider baking fur/grain/cloth micro-relief into normal maps via asset_pipeline.baking"
                    )
        except Exception:
            pass

    return report


# ---------------------------------------------------------------------------
# Visual / perceptual metrics
# ---------------------------------------------------------------------------

def silhouette_report(image: Image.Image | Path | str, alpha_threshold: int = 32) -> Dict[str, Any]:
    """Connected-component analysis of an RGBA sprite's opaque region."""
    from scipy.ndimage import label

    img = image if isinstance(image, Image.Image) else Image.open(image)
    alpha = np.asarray(img.convert("RGBA"))[:, :, 3]
    solid = alpha >= alpha_threshold
    labels, count = label(solid)
    sizes = np.bincount(labels.ravel())[1:] if count else np.array([], dtype=int)
    total = int(solid.sum())
    return {
        "components": int(count),
        "fill_ratio": total / solid.size,
        "largest_fraction": float(sizes.max() / total) if total else 0.0,
        "bbox": list(map(int, Image.fromarray(solid.astype(np.uint8) * 255).getbbox() or (0, 0, 0, 0))),
    }


def mesh_ground_darkening(mesh: Any) -> float:
    """Ratio (0..1) of lowest-10%-height luminance to upper-half luminance of a mesh's face colors.

    Values well below 1 mean ground-contact occlusion is baked; ~1.0 means flat shading.
    """
    raw = mesh.raw if hasattr(mesh, "raw") else mesh
    colors = np.asarray(raw.visual.face_colors)[:, :3].astype(np.float64)
    lum = colors @ np.array([0.2126, 0.7152, 0.0722])
    z = raw.triangles_center[:, 2]
    lo = z <= z.min() + 0.1 * (z.max() - z.min())
    hi = z >= (z.min() + z.max()) / 2.0
    if not lo.any() or not hi.any() or lum[hi].mean() == 0:
        return 1.0
    return float(lum[lo].mean() / lum[hi].mean())


def seam_error(image: Image.Image | Path | str) -> float:
    """Mean abs difference between wrapped edge rows/cols vs. interior neighbours (lower = seamless)."""
    img = image if isinstance(image, Image.Image) else Image.open(image)
    a = np.asarray(img.convert("RGB"), dtype=np.float64)
    wrap_x = np.abs(a[:, 0] - a[:, -1]).mean()
    wrap_y = np.abs(a[0] - a[-1]).mean()
    interior = (np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean()) / 2.0
    return float((wrap_x + wrap_y) / 2.0 / max(interior, 1e-6))


def frame_motion_profile(atlas: Image.Image | Path | str, columns: int, rows: int) -> List[float]:
    """Per-frame mean absolute change vs. previous frame (0 for frame 0). Flat/zero ⇒ dead animation."""
    img = atlas if isinstance(atlas, Image.Image) else Image.open(atlas)
    arr = np.asarray(img.convert("RGBA"), dtype=np.float64)
    fh, fw = arr.shape[0] // rows, arr.shape[1] // columns
    frames = [arr[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw] for r in range(rows) for c in range(columns)]
    return [0.0] + [float(np.abs(b - a).mean()) for a, b in zip(frames[:-1], frames[1:])]


def asset_metrics(path: Path | str) -> Dict[str, Any]:
    """Compact comparable metrics for a PNG, GLB/OBJ, or WAV."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".png":
        img = Image.open(p).convert("RGBA")
        arr = np.asarray(img)
        rgb = arr[:, :, :3].astype(np.float64)
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
        gy, gx = np.gradient(lum)
        opaque = arr[:, :, 3] > 0
        return {
            "size": list(img.size),
            "unique_colors": int(len(np.unique(arr.reshape(-1, 4), axis=0))),
            "luminance_std": round(float(lum[opaque].std()) if opaque.any() else 0.0, 2),
            "edge_energy": round(float(np.hypot(gx, gy)[opaque].mean()) if opaque.any() else 0.0, 3),
            "opaque_fraction": round(float(opaque.mean()), 3),
            "components": silhouette_report(img)["components"],
        }
    if ext in (".glb", ".obj"):
        import trimesh
        mesh = trimesh.load_scene(p, process=False).to_mesh()
        return {
            "triangles": int(len(mesh.faces)),
            "extents": [round(float(x), 3) for x in mesh.extents],
            "ground_darkening": round(mesh_ground_darkening(mesh), 3),
        }
    if ext == ".wav":
        from scipy.io import wavfile
        rate, pcm = wavfile.read(p)
        x = pcm.astype(np.float64)
        x = x.mean(axis=1) if x.ndim == 2 else x
        x /= max(np.abs(x).max(), 1.0)
        spec = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(len(x), 1.0 / rate)
        return {
            "rate": int(rate),
            "channels": 1 if pcm.ndim == 1 else int(pcm.shape[1]),
            "duration_s": round(len(x) / rate, 3),
            "spectral_centroid_hz": round(float((freqs * spec).sum() / max(spec.sum(), 1e-9)), 1),
            "peak_dbfs": round(float(20 * np.log10(max(np.abs(x).max(), 1e-9) * np.abs(pcm).max() / (np.iinfo(pcm.dtype).max if pcm.dtype.kind == "i" else 1.0))), 2),
        }
    raise ValueError(f"No metrics available for {p.suffix} files")


def compare_assets(a: Path | str, b: Path | str) -> str:
    """Format a side-by-side metric table for two asset files."""
    ma, mb = asset_metrics(a), asset_metrics(b)
    rows = [f"{'metric':<24}{Path(a).name:<28}{Path(b).name:<28}"]
    for key in ma:
        rows.append(f"{key:<24}{str(ma[key]):<28}{str(mb.get(key)):<28}")
    return "\n".join(rows)
