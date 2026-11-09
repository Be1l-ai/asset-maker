"""Asset validation classes and helpers for audio, raster, and 3D mesh files."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from PIL import Image
from scipy.io import wavfile


@dataclass
class ValidationReport:
    """Report detailing validation results and measured metrics."""
    passed: bool
    path: Path
    metrics: Dict[str, Any]
    errors: List[str]

    def raise_for_status(self) -> None:
        """Raise ValueError if validation checks failed."""
        if not self.passed:
            raise ValueError(f"Validation failed for {self.path}: {'; '.join(self.errors)}")


class AssetValidator:
    """Structural validator for exported WAV, PNG, and 3D mesh assets."""

    @classmethod
    def validate_wav(cls, path: Path | str) -> ValidationReport:
        """Inspect and validate a WAV audio file."""
        p = Path(path)
        errors = []
        metrics: Dict[str, Any] = {}

        try:
            rate, pcm = wavfile.read(p)
            if pcm.ndim not in (1, 2) or not pcm.size or rate <= 0:
                errors.append("WAV must contain audio samples at a positive sample rate")
            else:
                if pcm.dtype.kind == "u":
                    midpoint = (np.iinfo(pcm.dtype).max + 1) / 2
                    samples = (pcm.astype(np.float64) - midpoint) / midpoint
                elif pcm.dtype.kind == "i":
                    samples = pcm.astype(np.float64) / -np.iinfo(pcm.dtype).min
                else:
                    samples = pcm.astype(np.float64)

                if not np.isfinite(samples).all():
                    errors.append("WAV contains non-finite samples")
                else:
                    peak = float(np.abs(samples).max())
                    if peak == 0:
                        errors.append("WAV is silent")
                    elif peak >= 0.999:
                        errors.append("WAV reaches full scale; leaves insufficient headroom (<0.01 dBFS)")

                    metrics = {
                        "sample_rate": rate,
                        "channels": 1 if samples.ndim == 1 else samples.shape[1],
                        "duration_seconds": len(samples) / rate,
                        "peak_dbfs": float(20 * np.log10(peak)) if peak > 0 else -np.inf,
                        "rms_dbfs": float(20 * np.log10(np.sqrt(np.mean(samples ** 2)))),
                        "dc_offset": np.mean(samples, axis=0).tolist(),
                        "endpoint_delta": float(np.max(np.abs(samples[0] - samples[-1]))),
                    }
        except Exception as exc:
            errors.append(str(exc))

        report = ValidationReport(passed=len(errors) == 0, path=p, metrics=metrics, errors=errors)
        report.raise_for_status()
        return report

    @classmethod
    def validate_png(
        cls,
        path: Path | str,
        require_alpha: bool = False,
        columns: int = 1,
        rows: int = 1,
    ) -> ValidationReport:
        """Inspect and validate a PNG image or sprite sheet atlas."""
        p = Path(path)
        errors = []
        metrics: Dict[str, Any] = {}

        if columns < 1 or rows < 1:
            errors.append("Atlas columns and rows must be positive")

        try:
            with Image.open(p) as image:
                image.load()
                width, height = image.size
                if width % columns or height % rows:
                    errors.append("Image dimensions must be divisible by the atlas grid")

                rgba = np.asarray(image.convert("RGBA"))
                alpha = rgba[:, :, 3]
                if not alpha.any():
                    errors.append("Image is entirely transparent")
                if require_alpha and (image.mode != "RGBA" or not np.any(alpha == 0)):
                    errors.append("Expected RGBA pixels with a transparent background")

                metrics = {
                    "size": [width, height],
                    "mode": image.mode,
                    "frame_size": [width // columns, height // rows],
                    "grid": [columns, rows],
                    "alpha_range": [int(alpha.min()), int(alpha.max())],
                }
        except Exception as exc:
            errors.append(str(exc))

        report = ValidationReport(passed=len(errors) == 0, path=p, metrics=metrics, errors=errors)
        report.raise_for_status()
        return report

    @classmethod
    def validate_mesh(
        cls,
        path: Path | str,
        max_triangles: Optional[int] = None,
        watertight: bool = False,
    ) -> ValidationReport:
        """Inspect and validate a 3D mesh (GLB/OBJ)."""
        import trimesh

        p = Path(path)
        errors = []
        metrics: Dict[str, Any] = {}

        try:
            scene = trimesh.load_scene(p, process=False)
            mesh = scene.to_mesh()
            if not len(mesh.vertices) or not len(mesh.faces):
                errors.append("Mesh contains no geometry")
            if not np.isfinite(mesh.vertices).all():
                errors.append("Mesh contains non-finite vertices")
            if not mesh.nondegenerate_faces().all():
                errors.append("Mesh contains degenerate triangles")
            if max_triangles is not None and len(mesh.faces) > max_triangles:
                errors.append(f"Mesh has {len(mesh.faces)} triangles; budget is {max_triangles}")

            topology = mesh.copy()
            topology.merge_vertices()
            if watertight and not topology.is_watertight:
                errors.append("Mesh is not watertight after merging coincident vertices")

            metrics = {
                "vertices": len(mesh.vertices),
                "triangles": len(mesh.faces),
                "bounds": mesh.bounds.tolist(),
                "extents": mesh.extents.tolist(),
                "watertight": bool(topology.is_watertight),
                "winding_consistent": bool(topology.is_winding_consistent),
            }
        except Exception as exc:
            errors.append(str(exc))

        report = ValidationReport(passed=len(errors) == 0, path=p, metrics=metrics, errors=errors)
        report.raise_for_status()
        return report


# Functional aliases for backwards-compatibility
def inspect_wav(path: Path | str) -> Dict[str, Any]:
    return AssetValidator.validate_wav(path).metrics


def inspect_png(
    path: Path | str,
    require_alpha: bool = False,
    columns: int = 1,
    rows: int = 1,
) -> Dict[str, Any]:
    return AssetValidator.validate_png(path, require_alpha, columns, rows).metrics


def inspect_mesh(
    path: Path | str,
    max_triangles: Optional[int] = None,
    watertight: bool = False,
) -> Dict[str, Any]:
    return AssetValidator.validate_mesh(path, max_triangles, watertight).metrics
