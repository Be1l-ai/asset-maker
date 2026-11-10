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

    if not recipe.is_file():
        report.errors.append("generate.py is missing")
        return report

    source = recipe.read_text()
    used = used_names(source)

    for name in unused_pipeline_imports(recipe):
        report.errors.append(f"'{name}' is imported from {PACKAGE} but never used")

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
            if sym not in used:
                report.errors.append(f"vault doc '{doc}' claims '{sym}' but generate.py never uses it")

    stale = [
        name for name in manifest.get("sha256", {})
        if name not in ("generate.py", "README.md", "preview.png", "preview.gif")
        and not name.startswith(adir.name)
    ]
    if stale:
        report.errors.append(f"manifest hashes files from another asset/version: {', '.join(stale)}")

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
