import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.io import wavfile


def inspect_wav(path):
    rate, pcm = wavfile.read(path)
    if pcm.ndim not in (1, 2) or not pcm.size or rate <= 0:
        raise ValueError("WAV must contain audio samples at a positive sample rate")
    if pcm.dtype.kind == "u":
        midpoint = (np.iinfo(pcm.dtype).max + 1) / 2
        samples = (pcm.astype(np.float64) - midpoint) / midpoint
    elif pcm.dtype.kind == "i":
        samples = pcm.astype(np.float64) / -np.iinfo(pcm.dtype).min
    else:
        samples = pcm.astype(np.float64)
    if not np.isfinite(samples).all():
        raise ValueError("WAV contains non-finite samples")
    peak = float(np.abs(samples).max())
    if peak == 0:
        raise ValueError("WAV is silent")
    if peak >= 0.999:
        raise ValueError("WAV reaches full scale; inspect clipping and leave headroom")
    return {
        "sample_rate": rate,
        "channels": 1 if samples.ndim == 1 else samples.shape[1],
        "duration_seconds": len(samples) / rate,
        "peak_dbfs": float(20 * np.log10(peak)),
        "rms_dbfs": float(20 * np.log10(np.sqrt(np.mean(samples ** 2)))),
        "dc_offset": np.mean(samples, axis=0).tolist(),
        "endpoint_delta": float(np.max(np.abs(samples[0] - samples[-1]))),
    }


def inspect_png(path, require_alpha=False, columns=1, rows=1):
    if columns < 1 or rows < 1:
        raise ValueError("Atlas columns and rows must be positive")
    with Image.open(path) as image:
        image.load()
        width, height = image.size
        if width % columns or height % rows:
            raise ValueError("Image dimensions must be divisible by the atlas grid")
        rgba = np.asarray(image.convert("RGBA"))
        alpha = rgba[:, :, 3]
        if not alpha.any():
            raise ValueError("Image is entirely transparent")
        if require_alpha and (image.mode != "RGBA" or not np.any(alpha == 0)):
            raise ValueError("Expected RGBA pixels with a transparent background")
        return {
            "size": [width, height], "mode": image.mode,
            "frame_size": [width // columns, height // rows],
            "grid": [columns, rows],
            "alpha_range": [int(alpha.min()), int(alpha.max())],
        }


def inspect_mesh(path, max_triangles=None, watertight=False):
    import trimesh

    scene = trimesh.load_scene(path, process=False)
    mesh = scene.to_mesh()
    if not len(mesh.vertices) or not len(mesh.faces):
        raise ValueError("Mesh contains no geometry")
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Mesh contains non-finite vertices")
    if not mesh.nondegenerate_faces().all():
        raise ValueError("Mesh contains degenerate triangles")
    if max_triangles is not None and len(mesh.faces) > max_triangles:
        raise ValueError(f"Mesh has {len(mesh.faces)} triangles; budget is {max_triangles}")
    topology = mesh.copy()
    topology.merge_vertices()
    if watertight and not topology.is_watertight:
        raise ValueError("Mesh is not watertight after merging coincident vertices")
    return {
        "vertices": len(mesh.vertices), "triangles": len(mesh.faces),
        "bounds": mesh.bounds.tolist(), "extents": mesh.extents.tolist(),
        "watertight": bool(topology.is_watertight),
        "winding_consistent": bool(topology.is_winding_consistent),
    }


def main():
    parser = argparse.ArgumentParser(description="Check export structure, not artistic quality.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-alpha", action="store_true")
    parser.add_argument("--columns", type=int, default=1)
    parser.add_argument("--rows", type=int, default=1)
    parser.add_argument("--max-triangles", type=int)
    parser.add_argument("--watertight", action="store_true")
    args = parser.parse_args()
    try:
        suffix = args.path.suffix.lower()
        if suffix == ".wav":
            metrics = inspect_wav(args.path)
        elif suffix == ".png":
            metrics = inspect_png(args.path, args.require_alpha, args.columns, args.rows)
        elif suffix in (".glb", ".obj", ".ply", ".stl"):
            metrics = inspect_mesh(args.path, args.max_triangles, args.watertight)
        else:
            raise ValueError("Supported formats: WAV, PNG, GLB, OBJ, PLY, STL")
        print(json.dumps({"path": str(args.path), "structural_checks": "passed",
                          "sha256": hashlib.sha256(args.path.read_bytes()).hexdigest(),
                          "metrics": metrics}, indent=2))
    except (OSError, ValueError, ImportError) as error:
        parser.exit(1, f"Validation failed: {error}\n")


if __name__ == "__main__":
    main()
